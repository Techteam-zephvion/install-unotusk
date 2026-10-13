import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.api.src.models.enums import MembershipRole, ProjectStatus
from apps.api.src.schemas.repository import RepositoryRead


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectCreate(ProjectBase):
    organization_id: uuid.UUID
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    port: int | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: ProjectStatus | None = None


class ServerSyncItem(BaseModel):
    name: str
    port: int
    state: str = "running"
    repo_url: str | None = None
    description: str | None = None


class ServerSyncRequest(BaseModel):
    servers: list[ServerSyncItem]


class ProjectRead(ProjectBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    slug: str
    status: ProjectStatus
    port: int | None = None
    created_at: datetime
    updated_at: datetime
    role: MembershipRole | None = None
    repository: RepositoryRead | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID | None = None
    email: str | None = None
    role: MembershipRole = MembershipRole.MEMBER

    @model_validator(mode="after")
    def check_user_identifier(self) -> "ProjectMemberAdd":
        if not self.user_id and not self.email:
            raise ValueError("Either user_id or email must be provided")
        return self


class ProjectMemberUpdateRole(BaseModel):
    role: MembershipRole


class ProjectMemberRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    role: MembershipRole
    created_at: datetime
    user_name: str | None = None
    user_email: str | None = None

    model_config = ConfigDict(from_attributes=True)
