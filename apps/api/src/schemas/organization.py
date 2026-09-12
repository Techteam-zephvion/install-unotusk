import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.models.enums import MembershipRole


class OrganizationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrganizationCreate(OrganizationBase):
    slug: str | None = Field(default=None, min_length=2, max_length=100)


class OrganizationRead(OrganizationBase):
    id: uuid.UUID
    slug: str
    created_at: datetime
    updated_at: datetime
    role: MembershipRole | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationMembershipRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: MembershipRole
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
