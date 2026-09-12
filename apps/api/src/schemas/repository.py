import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.models.enums import IntegrationProvider


class GitHubConnectRequest(BaseModel):
    github_token: str | None = None


class RepositorySelectRequest(BaseModel):
    external_id: str
    owner: str
    name: str
    full_name: str
    default_branch: str = "main"
    url: str
    is_private: bool = False
    description: str | None = None


class RepositoryRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    integration_id: uuid.UUID
    provider: IntegrationProvider
    external_id: str
    owner: str
    name: str
    full_name: str
    default_branch: str
    url: str
    is_private: bool
    repo_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
