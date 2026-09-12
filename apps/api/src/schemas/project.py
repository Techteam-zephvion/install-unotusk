import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.models.enums import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectCreate(ProjectBase):
    organization_id: uuid.UUID
    slug: str | None = Field(default=None, min_length=2, max_length=100)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectRead(ProjectBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    slug: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
