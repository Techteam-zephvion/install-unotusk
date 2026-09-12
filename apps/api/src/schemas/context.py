import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.models.enums import DependencyType, SymbolType
from apps.api.src.schemas.repository import RepositoryRead
from apps.api.src.schemas.snapshot import SnapshotRead


class FileRead(BaseModel):
    id: uuid.UUID
    snapshot_id: uuid.UUID
    path: str
    filename: str
    extension: str
    language: str
    size_bytes: int
    content_hash: str
    is_binary: bool
    is_generated: bool
    is_test: bool
    line_count: int
    parser_supported: bool

    model_config = ConfigDict(from_attributes=True)


class SymbolRead(BaseModel):
    id: uuid.UUID
    file_id: uuid.UUID
    name: str
    symbol_type: SymbolType
    qualified_name: str
    start_line: int
    end_line: int
    parent_symbol_id: uuid.UUID | None = None
    file_path: str | None = None
    symbol_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DependencyRead(BaseModel):
    id: uuid.UUID
    source_file_id: uuid.UUID
    target_file_id: uuid.UUID | None = None
    external_package: str | None = None
    dependency_type: DependencyType
    line_number: int
    source_path: str | None = None
    target_path: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectContextMetrics(BaseModel):
    total_files: int = 0
    languages_count: int = 0
    symbols_count: int = 0
    dependencies_count: int = 0
    language_distribution: dict[str, int] = Field(default_factory=dict)


class ProjectRepositoryContext(BaseModel):
    repository: RepositoryRead | None = None
    active_snapshot: SnapshotRead | None = None
    metrics: ProjectContextMetrics = Field(default_factory=ProjectContextMetrics)
