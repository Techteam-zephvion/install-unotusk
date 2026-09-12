import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from apps.api.src.models.enums import SnapshotStatus


class SnapshotRead(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    commit_sha: str | None = None
    branch: str
    status: SnapshotStatus
    total_files: int
    processed_files: int
    failed_files: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestTriggerResponse(BaseModel):
    snapshot_id: uuid.UUID
    status: SnapshotStatus
    message: str
