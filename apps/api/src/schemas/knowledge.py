import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.models.enums import KnowledgeCategory, KnowledgeStatus


class KnowledgeCreateRequest(BaseModel):
    category: KnowledgeCategory
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=10000)
    source_reference_type: str | None = None
    source_reference_id: str | None = None
    related_file_path: str | None = None
    related_symbol: str | None = None
    related_finding_id: uuid.UUID | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    knowledge_metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeUpdateRequest(BaseModel):
    category: KnowledgeCategory | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = Field(None, min_length=1, max_length=10000)
    status: KnowledgeStatus | None = None
    related_file_path: str | None = None
    related_symbol: str | None = None
    related_finding_id: uuid.UUID | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    knowledge_metadata: dict[str, Any] | None = None


class KnowledgeResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by: uuid.UUID | None = None
    creator_email: str | None = None
    category: KnowledgeCategory
    title: str
    content: str
    status: KnowledgeStatus
    source_type: str = "CUSTOMER"
    source_reference_type: str | None = None
    source_reference_id: str | None = None
    related_file_path: str | None = None
    related_symbol: str | None = None
    related_finding_id: uuid.UUID | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    knowledge_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeListResponse(BaseModel):
    items: list[KnowledgeResponse]
    total: int
