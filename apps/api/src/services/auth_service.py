import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import ConflictException, UnauthorizedException
from apps.api.src.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from apps.api.src.models.enums import MembershipRole
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.user import User
from apps.api.src.schemas.auth import TokenResponse
from apps.api.src.schemas.user import UserCreate, UserLogin, UserRead
from apps.api.src.services.slug import slugify


class AuthService:
    @staticmethod
    async def signup(session: AsyncSession, data: UserCreate) -> TokenResponse:
        normalized_email = data.email.strip().lower()

        # Check existing user
        result = await session.execute(select(User).where(User.email == normalized_email))
        existing_user = result.scalar_one_or_none()
        if existing_user is not None:
            if existing_user.password_hash:
                raise ConflictException(
                    code="EMAIL_ALREADY_EXISTS",
                    message="A user with this email already exists",
                )
            # Activate invited / pre-provisioned user with chosen password
            if data.name and data.name.strip():
                existing_user.name = data.name.strip()
            existing_user.password_hash = hash_password(data.password)
            session.add(existing_user)
            await session.commit()
            await session.refresh(existing_user)

            mem_result = await session.execute(
                select(OrganizationMembership.organization_id)
                .where(OrganizationMembership.user_id == existing_user.id)
                .limit(1)
            )
            default_org_id = mem_result.scalar_one_or_none()

            token = create_access_token(
                subject=str(existing_user.id),
                extra_claims={"email": existing_user.email},
            )

            if default_org_id:
                await AuthService._auto_provision_if_needed(session, existing_user.id, default_org_id)

            return TokenResponse(
                access_token=token,
                token_type="bearer",
                user=UserRead.model_validate(existing_user),
                default_organization_id=default_org_id,
            )

        # Create user
        user = User(
            email=normalized_email,
            name=data.name.strip(),
            password_hash=hash_password(data.password),
        )
        session.add(user)
        await session.flush()

        # Create default organization for new user
        org_name = data.organization_name.strip() if data.organization_name and data.organization_name.strip() else f"{user.name}'s Org"
        base_slug = slugify(org_name)
        org_slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

        organization = Organization(
            name=org_name,
            slug=org_slug,
        )
        session.add(organization)
        await session.flush()

        # Assign user as OWNER
        membership = OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            role=MembershipRole.OWNER,
        )
        session.add(membership)
        await session.commit()
        await session.refresh(user)

        await AuthService._auto_provision_if_needed(session, user.id, organization.id)

        # Issue token
        token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserRead.model_validate(user),
            default_organization_id=organization.id,
        )

    @staticmethod
    async def login(session: AsyncSession, data: UserLogin) -> TokenResponse:
        normalized_email = data.email.strip().lower()
        result = await session.execute(select(User).where(User.email == normalized_email))
        user = result.scalar_one_or_none()

        if user is None or not verify_password(data.password, user.password_hash):
            raise UnauthorizedException(
                code="INVALID_CREDENTIALS",
                message="Invalid email or password",
            )

        # Find first org membership to populate default_organization_id
        mem_result = await session.execute(
            select(OrganizationMembership.organization_id)
            .where(OrganizationMembership.user_id == user.id)
            .limit(1)
        )
        default_org_id = mem_result.scalar_one_or_none()

        token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )

        if default_org_id:
            await AuthService._auto_provision_if_needed(session, user.id, default_org_id)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserRead.model_validate(user),
            default_organization_id=default_org_id,
        )

    @staticmethod
    async def _auto_provision_if_needed(session: AsyncSession, user_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        from apps.api.src.config.settings import settings
        if settings.TARGET_REPO_URL and settings.TARGET_REPO_URL.strip():
            # Check if project already exists
            from sqlalchemy import select

            from apps.api.src.models.project import Project

            # Simple check to see if user has any projects
            result = await session.execute(select(Project).where(Project.organization_id == organization_id))
            if result.scalars().first() is not None:
                return  # Already provisioned

            import urllib.parse

            from apps.api.src.schemas.project import ProjectCreate
            from apps.api.src.schemas.repository import RepositorySelectRequest
            from apps.api.src.services.ingestion_service import IngestionService
            from apps.api.src.services.project_service import ProjectService
            from apps.api.src.services.repository_service import RepositoryService

            repo_url = settings.TARGET_REPO_URL.strip()
            path_parts = urllib.parse.urlparse(repo_url).path.strip("/").split("/")
            if len(path_parts) >= 2:
                owner = path_parts[-2]
                name = path_parts[-1]
                if name.endswith(".git"):
                    name = name[:-4]
            else:
                owner, name = "default", "repository"

            try:
                project_data = ProjectCreate(
                    name=name,
                    organization_id=organization_id,
                    description=f"Auto-provisioned project for {repo_url}",
                )
                project = await ProjectService.create_project(session, user_id, project_data)

                repo_req = RepositorySelectRequest(
                    external_id=f"{owner}_{name}_{uuid.uuid4().hex[:6]}",
                    owner=owner,
                    name=name,
                    full_name=f"{owner}/{name}",
                    url=repo_url,
                )
                repo = await RepositoryService.select_repository(session, user_id, project.id, repo_req)
                await IngestionService.trigger_ingestion(session, user_id, project.id, repo.id)
            except Exception as e:
                import logging
                logger = logging.getLogger("unotusk-api")
                logger.error(f"Failed to auto-provision project from TARGET_REPO_URL: {e}")
