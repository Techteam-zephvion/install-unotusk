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
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.project import Project
from apps.api.src.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from apps.api.src.services.slug import slugify


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
        if mem_res.scalar_one_or_none() is None:
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

        # 4. Create Integration placeholder (ready for Stage 1)
        integration = Integration(
            project_id=project.id,
            provider=IntegrationProvider.GITHUB,
            status=IntegrationStatus.PENDING,
            metadata={},
        )
        session.add(integration)

        await session.commit()
        await session.refresh(project)

        return ProjectRead.model_validate(project)

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
        if mem_res.scalar_one_or_none() is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not belong to this organization",
            )

        # Query projects strictly bound to organization
        query = (
            select(Project)
            .where(Project.organization_id == organization_id)
            .order_by(Project.created_at.desc())
        )
        result = await session.execute(query)
        projects = result.scalars().all()

        return [ProjectRead.model_validate(p) for p in projects]

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
        if mem_res.scalar_one_or_none() is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not have permission to access this project",
            )

        return ProjectRead.model_validate(project)

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
        membership = mem_res.scalar_one_or_none()
        if membership is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not have permission to modify this project",
            )

        if data.name is not None:
            project.name = data.name.strip()
        if data.description is not None:
            project.description = data.description.strip()
        if data.status is not None:
            project.status = data.status

        await session.commit()
        await session.refresh(project)

        return ProjectRead.model_validate(project)

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

        # Only OWNER or ADMIN may delete
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
