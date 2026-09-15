import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from apps.api.src.models.enums import MembershipRole
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.organization import Organization
from apps.api.src.schemas.organization import OrganizationCreate, OrganizationRead
from apps.api.src.services.slug import slugify


class OrgService:
    @staticmethod
    async def create_organization(
        session: AsyncSession,
        user_id: uuid.UUID,
        data: OrganizationCreate,
    ) -> OrganizationRead:
        base_slug = data.slug or slugify(data.name)
        slug = base_slug

        # Ensure slug uniqueness
        existing = await session.execute(select(Organization).where(Organization.slug == slug))
        if existing.scalar_one_or_none() is not None:
            if data.slug:
                raise ConflictException(
                    code="ORG_SLUG_EXISTS",
                    message="An organization with this slug already exists",
                )
            slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

        org = Organization(name=data.name.strip(), slug=slug)
        session.add(org)
        await session.flush()

        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=user_id,
            role=MembershipRole.OWNER,
        )
        session.add(membership)
        await session.commit()
        await session.refresh(org)

        return OrganizationRead(
            id=org.id,
            name=org.name,
            slug=org.slug,
            created_at=org.created_at,
            updated_at=org.updated_at,
            role=MembershipRole.OWNER,
        )

    @staticmethod
    async def list_user_organizations(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[OrganizationRead]:
        query = (
            select(Organization, OrganizationMembership.role)
            .join(
                OrganizationMembership,
                Organization.id == OrganizationMembership.organization_id,
            )
            .where(OrganizationMembership.user_id == user_id)
            .order_by(Organization.name.asc())
        )
        result = await session.execute(query)
        rows = result.all()

        return [
            OrganizationRead(
                id=org.id,
                name=org.name,
                slug=org.slug,
                created_at=org.created_at,
                updated_at=org.updated_at,
                role=role,
            )
            for org, role in rows
        ]

    @staticmethod
    async def get_organization(
        session: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OrganizationRead:
        query = (
            select(Organization, OrganizationMembership.role)
            .join(
                OrganizationMembership,
                Organization.id == OrganizationMembership.organization_id,
            )
            .where(
                Organization.id == org_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        result = await session.execute(query)
        row = result.first()

        if row is None:
            # Check if org exists at all to return 403 vs 404
            exists = await session.execute(select(Organization.id).where(Organization.id == org_id))
            if exists.scalar_one_or_none() is None:
                raise NotFoundException(
                    code="ORGANIZATION_NOT_FOUND",
                    message="Organization not found",
                )
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not have access to this organization",
            )

        org, role = row
        return OrganizationRead(
            id=org.id,
            name=org.name,
            slug=org.slug,
            created_at=org.created_at,
            updated_at=org.updated_at,
            role=role,
        )

    @staticmethod
    async def verify_membership(
        session: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OrganizationMembership:
        query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
        )
        result = await session.execute(query)
        membership = result.scalar_one_or_none()
        if membership is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="User is not a member of the specified organization",
            )
        return membership
