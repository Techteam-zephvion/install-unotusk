import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.database import get_db
from apps.api.src.api.exceptions import ForbiddenException, UnauthorizedException
from apps.api.src.auth.security import decode_access_token
from apps.api.src.config.settings import settings
from apps.api.src.models.enums import MembershipRole
from apps.api.src.models.membership import OrganizationMembership, ProjectMembership
from apps.api.src.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(
            code="MISSING_TOKEN",
            message="Authorization token is required",
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise UnauthorizedException(
            code="INVALID_TOKEN",
            message="Invalid or expired authentication token",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError:
        raise UnauthorizedException(
            code="INVALID_TOKEN",
            message="Malformed user identifier in token",
        ) from None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedException(
            code="USER_NOT_FOUND",
            message="User associated with token does not exist",
        )

    # Data Plane Container-Level Authorization Guardrail
    if settings.is_data_plane:
        target_org_id: uuid.UUID | None = None
        if settings.DATA_PLANE_ORG_ID:
            try:
                target_org_id = uuid.UUID(settings.DATA_PLANE_ORG_ID)
            except ValueError:
                pass

        org_stmt = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id
        )
        if target_org_id:
            org_stmt = org_stmt.where(OrganizationMembership.organization_id == target_org_id)

        org_res = await db.execute(org_stmt)
        org_mem = org_res.scalar_one_or_none()

        if org_mem is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="User does not belong to the organization hosting this data plane instance.",
            )

        # Enforce project assignment for regular members
        if org_mem.role not in (MembershipRole.OWNER, MembershipRole.ADMIN):
            try:
                data_plane_proj_id = uuid.UUID(str(settings.DATA_PLANE_PROJECT_ID))
                proj_stmt = select(ProjectMembership).where(
                    ProjectMembership.project_id == data_plane_proj_id,
                    ProjectMembership.user_id == user.id,
                )
                proj_res = await db.execute(proj_stmt)
                proj_mem = proj_res.scalar_one_or_none()
                if proj_mem is None:
                    raise ForbiddenException(
                        code="PROJECT_ACCESS_DENIED",
                        message="User is not authorized to access this project data plane.",
                    )
            except ValueError:
                pass

    return user
