import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.src.api.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from apps.api.src.auth.security import hash_password
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    MembershipRole,
    ProjectStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.membership import OrganizationMembership, ProjectMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.user import User
from apps.api.src.schemas.project import (
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberRead,
    ProjectRead,
    ProjectUpdate,
    ServerSyncRequest,
)
from apps.api.src.schemas.repository import RepositoryRead
from apps.api.src.services.slug import slugify

logger = logging.getLogger("unotusk-api")


class ProjectService:
    @staticmethod
    async def resolve_project_id(
        session: AsyncSession,
        project_id: uuid.UUID | str,
    ) -> uuid.UUID:
        if isinstance(project_id, uuid.UUID):
            return project_id
        project_str = str(project_id).strip()
        try:
            return uuid.UUID(project_str)
        except (ValueError, AttributeError):
            pass

        # Lookup by slug or name (case-insensitive)
        result = await session.execute(
            select(Project.id).where(
                (Project.slug == project_str.lower())
                | (Project.name.ilike(project_str))
            ).limit(1)
        )
        found_id = result.scalar_one_or_none()
        if found_id is not None:
            return found_id
        raise NotFoundException(
            code="PROJECT_NOT_FOUND",
            message=f"Project '{project_id}' not found",
        )

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

        # 5. Determine Port & Data Plane
        if getattr(data, "port", None) is not None:
            project.port = data.port
        else:
            project.port = None

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
    def _get_live_docker_ports() -> dict[int, str]:
        """Returns map of host_port -> state ('running', 'stopped') for unotusk containers."""
        res: dict[int, str] = {}
        try:
            import docker
            client = docker.from_env()
            for c in client.containers.list(all=True):
                labels = c.labels or {}
                if labels.get("com.docker.compose.service") == "api":
                    state = c.status
                    ports = c.ports or {}
                    for _p_spec, host_bindings in ports.items():
                        if host_bindings:
                            for b in host_bindings:
                                hp = b.get("HostPort")
                                if hp and int(hp) != 28000:
                                    res[int(hp)] = state
        except Exception:
            pass
        return res

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

        docker_ports = ProjectService._get_live_docker_ports()

        # Query projects strictly bound to organization with repositories loaded
        if org_mem.role in (MembershipRole.OWNER, MembershipRole.ADMIN):
            # Organization OWNER / ADMIN sees all projects in the organization
            query = (
                select(Project, ProjectMembership.role)
                .options(selectinload(Project.repositories))
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
                if proj.port is not None and proj.port in docker_ports:
                    d_state = docker_ports[proj.port]
                    if d_state == "running" and proj.status != ProjectStatus.READY:
                        proj.status = ProjectStatus.READY
                    elif d_state != "running" and proj.status == ProjectStatus.READY:
                        proj.status = ProjectStatus.STOPPED

                p_read = ProjectRead.model_validate(proj)
                p_read.role = p_role or org_mem.role
                if proj.repositories:
                    p_read.repository = RepositoryRead.model_validate(proj.repositories[0])
                output.append(p_read)
            return output
        else:
            # Regular MEMBER only sees assigned projects
            query = (
                select(Project, ProjectMembership.role)
                .options(selectinload(Project.repositories))
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
                if proj.port is not None and proj.port in docker_ports:
                    d_state = docker_ports[proj.port]
                    if d_state == "running" and proj.status != ProjectStatus.READY:
                        proj.status = ProjectStatus.READY
                    elif d_state != "running" and proj.status == ProjectStatus.READY:
                        proj.status = ProjectStatus.STOPPED

                p_read = ProjectRead.model_validate(proj)
                p_read.role = p_role
                if proj.repositories:
                    p_read.repository = RepositoryRead.model_validate(proj.repositories[0])
                output.append(p_read)
            return output

    @staticmethod
    async def get_project(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID | str,
    ) -> ProjectRead:
        resolved_id = await ProjectService.resolve_project_id(session, project_id)
        query = (
            select(Project)
            .options(selectinload(Project.repositories))
            .where(Project.id == resolved_id)
        )
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
                ProjectMembership.project_id == resolved_id,
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
        if project.repositories:
            p_read.repository = RepositoryRead.model_validate(project.repositories[0])
        return p_read

    @staticmethod
    async def sync_servers(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: ServerSyncRequest,
    ) -> list[ProjectRead]:
        import urllib.parse

        # 1. Get user's primary organization
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        org_mem = mem_res.scalars().first()
        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="User has no organization memberships",
            )
        organization_id = org_mem.organization_id

        synced_ports = {s.port for s in data.servers}
        stale_slugs = {"orca", "syncguard", "unotusk-core"}

        # 2. Clean up stale mock projects not in synced servers
        existing_projects_query = (
            select(Project)
            .options(selectinload(Project.repositories))
            .where(Project.organization_id == organization_id)
        )
        existing_res = await session.execute(existing_projects_query)
        existing_projects = list(existing_res.scalars().all())

        for p in existing_projects:
            if p.slug in stale_slugs or (p.port is not None and p.port not in synced_ports):
                await session.delete(p)
        await session.flush()

        # Re-fetch remaining projects
        existing_res = await session.execute(existing_projects_query)
        existing_projects = list(existing_res.scalars().all())
        existing_by_port = {p.port: p for p in existing_projects if p.port is not None}
        existing_by_name = {p.name.lower(): p for p in existing_projects}

        for server in data.servers:
            is_running = server.state.lower() in ("running", "active", "degraded")
            target_status = ProjectStatus.READY if is_running else ProjectStatus.STOPPED

            proj = existing_by_port.get(server.port) or existing_by_name.get(server.name.lower())
            if proj is not None:
                proj.name = server.name.strip()
                proj.port = server.port
                proj.status = target_status
                if server.description:
                    proj.description = server.description
            else:
                base_slug = slugify(server.name)
                slug = base_slug
                slug_check = await session.execute(
                    select(Project).where(
                        Project.organization_id == organization_id,
                        Project.slug == slug,
                    )
                )
                if slug_check.scalar_one_or_none() is not None:
                    slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

                proj = Project(
                    organization_id=organization_id,
                    name=server.name.strip(),
                    slug=slug,
                    description=server.description or f"Server instance for {server.name}",
                    status=target_status,
                    port=server.port,
                )
                session.add(proj)
                await session.flush()

                # Membership
                mem = ProjectMembership(
                    project_id=proj.id,
                    user_id=user_id,
                    role=MembershipRole.ADMIN,
                )
                session.add(mem)

                # Integration
                integration = Integration(
                    project_id=proj.id,
                    provider=IntegrationProvider.GITHUB,
                    status=IntegrationStatus.CONNECTED if is_running else IntegrationStatus.PENDING,
                    metadata={},
                )
                session.add(integration)
                await session.flush()

            # Handle repository linking
            if server.repo_url and server.repo_url.strip():
                repo_url = server.repo_url.strip()
                path_parts = urllib.parse.urlparse(repo_url).path.strip("/").split("/")
                if len(path_parts) >= 2:
                    repo_owner = path_parts[-2]
                    repo_name = path_parts[-1]
                    if repo_name.endswith(".git"):
                        repo_name = repo_name[:-4]
                else:
                    repo_owner, repo_name = "default", server.name

                repo_full_name = f"{repo_owner}/{repo_name}"

                repo_query = select(Repository).where(Repository.project_id == proj.id)
                repo_res = await session.execute(repo_query)
                repo = repo_res.scalars().first()

                integ_query = select(Integration.id).where(Integration.project_id == proj.id)
                integ_id = (await session.execute(integ_query)).scalar_one_or_none()
                if integ_id is None:
                    integ = Integration(
                        project_id=proj.id,
                        provider=IntegrationProvider.GITHUB,
                        status=IntegrationStatus.CONNECTED,
                        metadata={},
                    )
                    session.add(integ)
                    await session.flush()
                    integ_id = integ.id

                if repo is not None:
                    repo.owner = repo_owner
                    repo.name = repo_name
                    repo.full_name = repo_full_name
                    repo.url = repo_url
                else:
                    repo = Repository(
                        project_id=proj.id,
                        integration_id=integ_id,
                        provider=IntegrationProvider.GITHUB,
                        external_id=f"{repo_owner}_{repo_name}_{uuid.uuid4().hex[:6]}",
                        owner=repo_owner,
                        name=repo_name,
                        full_name=repo_full_name,
                        default_branch="main",
                        url=repo_url,
                        is_private=False,
                    )
                    session.add(repo)

        await session.commit()
        session.expire_all()
        return await ProjectService.list_projects(session, user_id, organization_id)

    @staticmethod
    async def update_project(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID | str,
        data: ProjectUpdate,
    ) -> ProjectRead:
        resolved_id = await ProjectService.resolve_project_id(session, project_id)
        query = select(Project).where(Project.id == resolved_id)
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
                ProjectMembership.project_id == resolved_id,
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
        project_id: uuid.UUID | str,
    ) -> None:
        resolved_id = await ProjectService.resolve_project_id(session, project_id)
        query = select(Project).where(Project.id == resolved_id)
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
        project_id: uuid.UUID | str,
    ) -> list[ProjectMemberRead]:
        resolved_id = await ProjectService.resolve_project_id(session, project_id)
        query = select(Project).where(Project.id == resolved_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Caller info
        caller = await session.get(User, user_id)
        is_lead_admin = caller is not None and caller.email.lower() == "admin@acme.com"

        # Check if project belongs to Acme Corporation or if caller is Lead Admin
        org_query = select(Organization).where(Organization.id == project.organization_id)
        project_org = (await session.execute(org_query)).scalar_one_or_none()
        is_acme_org = (
            (project_org is not None and "acme" in project_org.slug.lower())
            or is_lead_admin
        )

        if is_acme_org:
            # Ensure permanent admin@acme.com exists and is always linked with OWNER/ADMIN privileges
            admin_user_res = await session.execute(
                select(User).where(func.lower(User.email) == "admin@acme.com")
            )
            admin_user = admin_user_res.scalar_one_or_none()
            if admin_user is None:
                admin_user = User(
                    email="admin@acme.com",
                    name="Lead Admin",
                    password_hash=hash_password("admin123"),
                )
                session.add(admin_user)
                await session.flush()

            admin_om_res = await session.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == project.organization_id,
                    OrganizationMembership.user_id == admin_user.id,
                )
            )
            admin_om = admin_om_res.scalar_one_or_none()
            if admin_om is None:
                session.add(OrganizationMembership(
                    organization_id=project.organization_id,
                    user_id=admin_user.id,
                    role=MembershipRole.OWNER,
                ))
            elif admin_om.role != MembershipRole.OWNER:
                admin_om.role = MembershipRole.OWNER

            admin_pm_res = await session.execute(
                select(ProjectMembership).where(
                    ProjectMembership.project_id == resolved_id,
                    ProjectMembership.user_id == admin_user.id,
                )
            )
            admin_pm = admin_pm_res.scalar_one_or_none()
            if admin_pm is None:
                session.add(ProjectMembership(
                    project_id=resolved_id,
                    user_id=admin_user.id,
                    role=MembershipRole.ADMIN,
                ))
            elif admin_pm.role != MembershipRole.ADMIN:
                admin_pm.role = MembershipRole.ADMIN

            await session.flush()

        if not is_lead_admin:
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
                        ProjectMembership.project_id == resolved_id,
                        ProjectMembership.user_id == user_id,
                    )
                )
                if proj_mem_res.scalar_one_or_none() is None:
                    raise ForbiddenException(
                        code="PROJECT_ACCESS_DENIED",
                        message="You do not have access to this project",
                    )

        # In single-tenant MVP, ensure organization users are synchronized into ProjectMembership
        # for this project so the Lead Admin can immediately see, search, and manage workspace employees.
        org_users_query = (
            select(User)
            .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
            .where(OrganizationMembership.organization_id == project.organization_id)
        )
        org_users_res = await session.execute(org_users_query)
        org_users = org_users_res.scalars().all()

        existing_pms_query = select(ProjectMembership.user_id).where(
            ProjectMembership.project_id == resolved_id
        )
        existing_pm_user_ids = set((await session.execute(existing_pms_query)).scalars().all())

        for u in org_users:
            if u.id not in existing_pm_user_ids:
                is_u_admin = u.email.lower() == "admin@acme.com"
                om_res = await session.execute(
                    select(OrganizationMembership.role).where(
                        OrganizationMembership.user_id == u.id,
                        OrganizationMembership.organization_id == project.organization_id,
                    ).limit(1)
                )
                om_role = om_res.scalar_one_or_none()
                if is_u_admin or om_role in (MembershipRole.OWNER, MembershipRole.ADMIN):
                    u_role = MembershipRole.ADMIN
                else:
                    u_role = MembershipRole.MEMBER

                session.add(ProjectMembership(
                    project_id=resolved_id,
                    user_id=u.id,
                    role=u_role,
                ))
                existing_pm_user_ids.add(u.id)

        await session.commit()

        members_query = (
            select(ProjectMembership, User.name, User.email)
            .join(User, ProjectMembership.user_id == User.id)
            .where(ProjectMembership.project_id == resolved_id)
            .order_by(ProjectMembership.created_at.asc())
        )
        members_res = await session.execute(members_query)
        rows = members_res.all()

        member_reads: list[ProjectMemberRead] = []
        for pm, user_name, user_email in rows:
            is_admin_account = (user_email or "").lower() == "admin@acme.com"
            final_role = (
                MembershipRole.ADMIN
                if is_admin_account
                else (MembershipRole.ADMIN if pm.role in (MembershipRole.OWNER, MembershipRole.ADMIN) else MembershipRole.MEMBER)
            )
            clean_name = user_name.strip() if (user_name and user_name.strip()) else (
                "Lead Admin" if is_admin_account else (user_email.split("@")[0].title() if user_email else "Member")
            )
            member_reads.append(
                ProjectMemberRead(
                    id=pm.id,
                    project_id=pm.project_id,
                    user_id=pm.user_id,
                    role=final_role,
                    created_at=pm.created_at,
                    user_name=clean_name,
                    user_email=user_email,
                )
            )

        # Sort admin@acme.com first, followed by others chronologically
        member_reads.sort(
            key=lambda item: (0 if (item.user_email or "").lower() == "admin@acme.com" else 1, item.created_at)
        )
        return member_reads

    @staticmethod
    async def add_project_member(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID | str,
        data: ProjectMemberAdd,
    ) -> ProjectMemberRead:
        resolved_id = await ProjectService.resolve_project_id(session, project_id)
        query = select(Project).where(Project.id == resolved_id)
        result = await session.execute(query)
        project = result.scalar_one_or_none()

        if project is None:
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project not found",
            )

        # Caller must be Org OWNER/ADMIN or Project ADMIN (admin@acme.com always authorized)
        caller = await session.get(User, user_id)
        is_lead_admin = caller is not None and caller.email.lower() == "admin@acme.com"

        if not is_lead_admin:
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
                    ProjectMembership.project_id == resolved_id,
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

        # Find target user by ID, email, or name (case-insensitive)
        target_user = None
        if data.user_id:
            target_user = await session.get(User, data.user_id)
        elif data.email:
            clean_identifier = data.email.lower().strip()
            if clean_identifier == "admin@acme.com":
                raise ConflictException(
                    code="PERMANENT_ADMIN_IMMUTABLE",
                    message="admin@acme.com is the permanent Lead Administrator with full repository access and cannot be re-assigned or demoted.",
                )

            # 1. Exact email match
            u_res = await session.execute(
                select(User).where(func.lower(User.email) == clean_identifier)
            )
            target_user = u_res.scalar_one_or_none()

            # 2. Exact name match
            if target_user is None:
                u_res = await session.execute(
                    select(User).where(func.lower(User.name) == clean_identifier)
                )
                target_user = u_res.scalar_one_or_none()

            # 3. Substring match on name or email
            if target_user is None:
                u_res = await session.execute(
                    select(User).where(
                        (func.lower(User.name).ilike(f"%{clean_identifier}%"))
                        | (func.lower(User.email).ilike(f"%{clean_identifier}%"))
                    ).limit(1)
                )
                target_user = u_res.scalar_one_or_none()

        if target_user is None:
            raise NotFoundException(
                code="USER_NOT_FOUND",
                message="Target user not found",
            )

        if target_user.email.lower() == "admin@acme.com":
            raise ConflictException(
                code="PERMANENT_ADMIN_IMMUTABLE",
                message="admin@acme.com is the permanent Lead Administrator with full repository access and cannot be re-assigned or demoted.",
            )

        # Target user must be part of the organization
        target_org_mem_res = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == project.organization_id,
                OrganizationMembership.user_id == target_user.id,
            )
        )
        target_org_mem = target_org_mem_res.scalar_one_or_none()
        if target_org_mem is None:
            raise ConflictException(
                code="USER_NOT_IN_ORGANIZATION",
                message="User is not a member of the organization",
            )

        # Check if already a project member - update role if existing, else add new
        existing_pm = await session.execute(
            select(ProjectMembership).where(
                ProjectMembership.project_id == resolved_id,
                ProjectMembership.user_id == target_user.id,
            )
        )
        pm = existing_pm.scalar_one_or_none()
        if pm is not None:
            if pm.role == data.role or data.user_id is not None:
                raise ConflictException(
                    code="MEMBER_ALREADY_EXISTS",
                    message="User is already a member of this project",
                )
            pm.role = data.role
            new_membership = pm
        else:
            new_membership = ProjectMembership(
                project_id=resolved_id,
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
        project_id: uuid.UUID | str,
        target_user_id: uuid.UUID,
    ) -> None:
        resolved_id = await ProjectService.resolve_project_id(session, project_id)
        query = select(Project).where(Project.id == resolved_id)
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
                ProjectMembership.project_id == resolved_id,
                ProjectMembership.user_id == target_user_id,
            )
        )
        target_membership = target_pm_res.scalar_one_or_none()
        if target_membership is None:
            raise NotFoundException(
                code="MEMBERSHIP_NOT_FOUND",
                message="User is not a member of this project",
            )

        target_user = await session.get(User, target_user_id)
        if target_user and target_user.email.lower() == "admin@acme.com":
            raise ForbiddenException(
                code="PERMANENT_ADMIN_PROTECTED",
                message="admin@acme.com is the permanent Lead Administrator and cannot be removed.",
            )

        # Permission check:
        # A user may remove themselves (leave project),
        # OR caller must be Org OWNER/ADMIN or Project ADMIN (admin@acme.com always authorized)
        caller = await session.get(User, user_id)
        is_lead_admin = caller is not None and caller.email.lower() == "admin@acme.com"

        if user_id != target_user_id and not is_lead_admin:
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
                    ProjectMembership.project_id == resolved_id,
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
