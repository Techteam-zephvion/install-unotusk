import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    MembershipRole,
    ProjectStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.membership import OrganizationMembership, ProjectMembership
from apps.api.src.models.project import Project
from apps.api.src.models.user import User
from apps.api.src.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
)
from apps.api.src.services.slug import slugify

logger = logging.getLogger("unotusk-api")


class ProjectService:
    @staticmethod
    async def create_project(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: ProjectCreate,
    ) -> ProjectRead:
        # 1. Enforce organization membership
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == data.organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        org_mem = mem_res.scalar_one_or_none()
        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not belong to the target organization",
            )

        # 2. Slug generation & uniqueness within organization
        base_slug = data.slug or slugify(data.name)
        slug = base_slug

        existing = await session.execute(
            select(Project).where(
                Project.organization_id == data.organization_id,
                Project.slug == slug,
            )
        )
        if existing.scalar_one_or_none() is not None:
            if data.slug:
                raise ConflictException(
                    code="PROJECT_SLUG_EXISTS",
                    message="A project with this slug already exists in this organization",
                )
            slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

        from apps.api.src.services.orchestrator_service import OrchestratorService

        # 3. Create Project
        project = Project(
            organization_id=data.organization_id,
            name=data.name.strip(),
            slug=slug,
            description=data.description.strip() if data.description else None,
            status=ProjectStatus.CREATED,
        )
        session.add(project)
        await session.flush()

        # 4. Add creator as project ADMIN
        creator_membership = ProjectMembership(
            project_id=project.id,
            user_id=user_id,
            role=MembershipRole.ADMIN,
        )
        session.add(creator_membership)

        # 5. Orchestrate Data Plane
        try:
            assigned_port = await OrchestratorService.spawn_project_container(
                project_id=project.id,
                organization_id=data.organization_id,
            )
            project.port = assigned_port
        except Exception as e:
            logger.error("Failed to orchestrate project: %s", e)
            # Non-fatal for MVP, just fallback or log

        # 6. Create Integration placeholder (ready for Stage 1)
        integration = Integration(
            project_id=project.id,
            provider=IntegrationProvider.GITHUB,
            status=IntegrationStatus.PENDING,
            metadata={},
        )
        session.add(integration)

        await session.commit()
        await session.refresh(project)

        project_read = ProjectRead.model_validate(project)
        project_read.role = MembershipRole.ADMIN
        return project_read

    @staticmethod
    async def list_projects(
        session: AsyncSession,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> list[ProjectRead]:
        # Enforce organization membership
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        org_mem = mem_res.scalar_one_or_none()
        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not belong to this organization",
            )

        # Query projects strictly bound to organization
        if org_mem.role in (MembershipRole.OWNER, MembershipRole.ADMIN):
            # Organization OWNER / ADMIN sees all projects in the organization
            query = (
                select(Project, ProjectMembership.role)
                .outerjoin(
                    ProjectMembership,
                    (ProjectMembership.project_id == Project.id)
                    & (ProjectMembership.user_id == user_id),
                )
                .where(Project.organization_id == organization_id)
                .order_by(Project.created_at.desc())
            )
            result = await session.execute(query)
            rows = result.all()
            output = []
            for proj, p_role in rows:
                p_read = ProjectRead.model_validate(proj)
                p_read.role = p_role or org_mem.role
                output.append(p_read)
            return output
        else:
            # Regular MEMBER only sees assigned projects
            query = (
                select(Project, ProjectMembership.role)
                .join(
                    ProjectMembership,
                    (ProjectMembership.project_id == Project.id)
                    & (ProjectMembership.user_id == user_id),
                )
                .where(Project.organization_id == organization_id)
                .order_by(Project.created_at.desc())
            )
            result = await session.execute(query)
            rows = result.all()
            output = []
            for proj, p_role in rows:
                p_read = ProjectRead.model_validate(proj)
                p_read.role = p_role
                output.append(p_read)
            return output

    @staticmethod
    async def get_project(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ProjectRead:
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Enforce caller's membership in the project's organization
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == project.organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        org_mem = mem_res.scalar_one_or_none()
        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not have permission to access this project",
            )

        # Check project membership
        proj_mem_res = await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            )
        )
        proj_mem = proj_mem_res.scalar_one_or_none()

        # If caller is MEMBER, they must be assigned to this project
        if org_mem.role == MembershipRole.MEMBER and proj_mem is None:
            raise ForbiddenException(
                code="PROJECT_ACCESS_DENIED",
                message="You do not have permission to access this project",
            )

        p_read = ProjectRead.model_validate(project)
        p_read.role = proj_mem.role if proj_mem else org_mem.role
        return p_read

    @staticmethod
    async def update_project(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectUpdate,
    ) -> ProjectRead:
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Enforce membership & role
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == project.organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        org_mem = mem_res.scalar_one_or_none()
        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not have permission to modify this project",
            )

        proj_mem_res = await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            )
        )
        proj_mem = proj_mem_res.scalar_one_or_none()

        is_authorized = (
            org_mem.role in (MembershipRole.OWNER, MembershipRole.ADMIN)
            or (proj_mem is not None and proj_mem.role == MembershipRole.ADMIN)
        )
        if not is_authorized:
            raise ForbiddenException(
                code="INSUFFICIENT_PERMISSIONS",
                message="Only organization admins or project admins can update this project",
            )

        if data.name is not None:
            project.name = data.name.strip()
        if data.description is not None:
            project.description = data.description.strip()
        if data.status is not None:
            project.status = data.status

        await session.commit()
        await session.refresh(project)

        p_read = ProjectRead.model_validate(project)
        p_read.role = proj_mem.role if proj_mem else org_mem.role
        return p_read

    @staticmethod
    async def delete_project(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Only OWNER or ADMIN of the organization may delete
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == project.organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        membership = mem_res.scalar_one_or_none()
        if membership is None or membership.role not in (
            MembershipRole.OWNER,
            MembershipRole.ADMIN,
        ):
            raise ForbiddenException(
                code="INSUFFICIENT_PERMISSIONS",
                message="Only organization owners or admins can delete projects",
            )

        await session.delete(project)
        await session.commit()

    @staticmethod
    async def list_project_members(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> list[ProjectMemberRead]:
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Check caller's organization membership
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == project.organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        org_mem = mem_res.scalar_one_or_none()
        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not belong to the target organization",
            )

        # If caller is MEMBER, must be in project
        if org_mem.role == MembershipRole.MEMBER:
            proj_mem_res = await session.execute(
                select(ProjectMembership).where(
                    ProjectMembership.project_id == project_id,
                    ProjectMembership.user_id == user_id,
                )
            )
            if proj_mem_res.scalar_one_or_none() is None:
                raise ForbiddenException(
                    code="PROJECT_ACCESS_DENIED",
                    message="You do not have access to this project",
                )

        members_query = (
            select(ProjectMembership, User.name, User.email)
            .join(User, ProjectMembership.user_id == User.id)
            .where(ProjectMembership.project_id == project_id)
            .order_by(ProjectMembership.created_at.asc())
        )
        members_res = await session.execute(members_query)
        rows = members_res.all()

        return [
            ProjectMemberRead(
                id=pm.id,
                project_id=pm.project_id,
                user_id=pm.user_id,
                role=pm.role,
                created_at=pm.created_at,
                user_name=user_name,
                user_email=user_email,
            )
            for pm, user_name, user_email in rows
        ]

    @staticmethod
    async def add_project_member(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectMemberAdd,
    ) -> ProjectMemberRead:
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Caller must be Org OWNER/ADMIN or Project ADMIN
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == project.organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        org_mem = mem_res.scalar_one_or_none()
        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not belong to the target organization",
            )

        proj_mem_res = await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            )
        )
        proj_mem = proj_mem_res.scalar_one_or_none()

        is_authorized = (
            org_mem.role in (MembershipRole.OWNER, MembershipRole.ADMIN)
            or (proj_mem is not None and proj_mem.role == MembershipRole.ADMIN)
        )
        if not is_authorized:
            raise ForbiddenException(
                code="INSUFFICIENT_PERMISSIONS",
                message="Only organization admins or project admins can add project members",
            )

        # Find target user
        target_user = None
        if data.user_id:
            target_user = await session.get(User, data.user_id)
        elif data.email:
            u_res = await session.execute(
                select(User).where(User.email == data.email.lower().strip())
            )
            target_user = u_res.scalar_one_or_none()

        if target_user is None:
            raise NotFoundException(
                code="USER_NOT_FOUND",
                message="Target user not found",
            )

        # Target user must be part of the organization
        target_org_mem_res = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == project.organization_id,
                OrganizationMembership.user_id == target_user.id,
            )
        )
        if target_org_mem_res.scalar_one_or_none() is None:
            raise ConflictException(
                code="USER_NOT_IN_ORGANIZATION",
                message="User must belong to the organization before being added to a project",
            )

        # Check if already a project member
        existing_pm = await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == target_user.id,
            )
        )
        if existing_pm.scalar_one_or_none() is not None:
            raise ConflictException(
                code="MEMBER_ALREADY_EXISTS",
                message="User is already a member of this project",
            )

        new_membership = ProjectMembership(
            project_id=project_id,
            user_id=target_user.id,
            role=data.role,
        )
        session.add(new_membership)
        await session.commit()
        await session.refresh(new_membership)

        return ProjectMemberRead(
            id=new_membership.id,
            project_id=new_membership.project_id,
            user_id=new_membership.user_id,
            role=new_membership.role,
            created_at=new_membership.created_at,
            user_name=target_user.name,
            user_email=target_user.email,
        )

    @staticmethod
    async def remove_project_member(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        query = select(Project).where(Project.id == project_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Verify target membership exists
        target_pm_res = await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == target_user_id,
            )
        )
        target_membership = target_pm_res.scalar_one_or_none()
        if target_membership is None:
            raise NotFoundException(
                code="MEMBERSHIP_NOT_FOUND",
                message="User is not a member of this project",
            )

        # Permission check:
        # A user may remove themselves (leave project),
        # OR caller must be Org OWNER/ADMIN or Project ADMIN
        if user_id != target_user_id:
            mem_query = select(OrganizationMembership).where(
                OrganizationMembership.organization_id == project.organization_id,
                OrganizationMembership.user_id == user_id,
            )
            mem_res = await session.execute(mem_query)
            org_mem = mem_res.scalar_one_or_none()
            if org_mem is None:
                raise ForbiddenException(
                    code="ORGANIZATION_ACCESS_DENIED",
                    message="You do not belong to the target organization",
                )

            caller_pm_res = await session.execute(
                select(ProjectMembership).where(
                    ProjectMembership.project_id == project_id,
                    ProjectMembership.user_id == user_id,
                )
            )
            caller_pm = caller_pm_res.scalar_one_or_none()

            is_authorized = (
                org_mem.role in (MembershipRole.OWNER, MembershipRole.ADMIN)
                or (caller_pm is not None and caller_pm.role == MembershipRole.ADMIN)
            )
            if not is_authorized:
                raise ForbiddenException(
                    code="INSUFFICIENT_PERMISSIONS",
                    message="Only organization admins or project admins can remove other members",
                )

        await session.delete(target_membership)
        await session.commit()
