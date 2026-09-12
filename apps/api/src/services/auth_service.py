import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from apps.api.src.api.exceptions import ConflictException, UnauthorizedException
from apps.api.src.auth.security import create_access_token, hash_password, verify_password
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
        result = await session.execute(
            select(User).where(User.email == normalized_email)
        )
        if result.scalar_one_or_none() is not None:
            raise ConflictException(
                code="EMAIL_ALREADY_EXISTS",
                message="A user with this email already exists",
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
        org_name = f"{user.name}'s Org"
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
        result = await session.execute(
            select(User).where(User.email == normalized_email)
        )
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

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserRead.model_validate(user),
            default_organization_id=default_org_id,
        )
