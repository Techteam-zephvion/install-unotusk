import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.models.enums import (
    DiscoveryJobStatus,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
)


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    snapshot_id: uuid.UUID
    discovery_run_id: uuid.UUID | None = None
    category: FindingCategory
    title: str
    description: str
    why_it_matters: str
    severity: FindingSeverity
    confidence: FindingConfidence
    status: FindingStatus
    score: float
    recommendation: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class FindingUpdateStatusRequest(BaseModel):
    status: FindingStatus


class DiscoveryRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    snapshot_id: uuid.UUID
    status: DiscoveryJobStatus
    progress: int
    findings_count: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None


class DiscoverSummaryResponse(BaseModel):
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    latest_run: DiscoveryRunResponse | None = None


class DiscoveryTriggerResponse(BaseModel):
    task_id: str
    discovery_run_id: uuid.UUID
    status: DiscoveryJobStatus
    message: str
