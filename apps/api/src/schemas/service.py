import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-_")


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    description: str | None = None
    tier: str | None = Field(default="tier-1", max_length=50)
    service_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("slug", mode="before")
    @classmethod
    def set_slug(cls, v: str | None, info) -> str | None:
        if v and v.strip():
            return _slugify(v)
        name = info.data.get("name")
        if name:
            return _slugify(name)
        return v


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=100)
    description: str | None = None
    tier: str | None = Field(default=None, max_length=50)
    service_metadata: dict[str, Any] | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def clean_slug(cls, v: str | None) -> str | None:
        if v and v.strip():
            return _slugify(v)
        return v


class ServiceAssociateRepo(BaseModel):
    repository_id: uuid.UUID


class ServiceRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    tier: str | None = "tier-1"
    service_metadata: dict[str, Any] = Field(default_factory=dict)
    repository_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
