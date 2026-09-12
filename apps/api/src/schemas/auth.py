import uuid

from pydantic import BaseModel

from apps.api.src.schemas.user import UserRead


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    default_organization_id: uuid.UUID | None = None


class TokenData(BaseModel):
    sub: str
    email: str | None = None
