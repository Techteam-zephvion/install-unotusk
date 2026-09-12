import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.database import get_db
from apps.api.src.api.exceptions import UnauthorizedException
from apps.api.src.auth.security import decode_access_token
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

    return user
