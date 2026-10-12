import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CodeChangeType(str, Enum):
    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    RENAME = "RENAME"


class FactType(str, Enum):
    BEHAVIOR = "BEHAVIOR"
    VALIDATION = "VALIDATION"
    ERROR_HANDLING = "ERROR_HANDLING"
    STATE_CHANGE = "STATE_CHANGE"
    RELATIONSHIP = "RELATIONSHIP"
    REMOVAL = "REMOVAL"
    CONFIGURATION = "CONFIGURATION"
    STRUCTURAL = "STRUCTURAL"


class FactConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    UNCERTAIN = "UNCERTAIN"


class SemanticCodeFact(BaseModel):
    """
    Module 1: Atomic Fact Decomposition (Code-Lane).
    A small, self-contained, semantically meaningful fact about code behavior,
    grounded in actual source code changes.
    """

    id: str
    statement: str
    fact_type: FactType = FactType.BEHAVIOR
    confidence: FactConfidence = FactConfidence.HIGH
    is_uncertain: bool = False
    file_path: str
    symbol_name: str | None = None
    commit_sha: str
    commit_message: str | None = None
    change_type: CodeChangeType
    evidenced_lines: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str

    model_config = ConfigDict(extra="ignore")


AtomicCodeFact = SemanticCodeFact


class GitDiffHunk(BaseModel):
    """Represents an individual hunk within a file diff."""

    hunk_index: int = 0
    header: str
    section_header: str | None = None
    old_start_line: int
    old_line_count: int
    new_start_line: int
    new_line_count: int
    lines: list[str] = Field(default_factory=list)
    added_lines: list[str] = Field(default_factory=list)
    deleted_lines: list[str] = Field(default_factory=list)
    context_lines: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class GitFileDiff(BaseModel):
    """Represents the diff for a single file within a Git commit."""

    old_path: str | None = None
    new_path: str
    change_type: CodeChangeType = CodeChangeType.MODIFY
    hunks: list[GitDiffHunk] = Field(default_factory=list)
    raw_patch: str = ""

    model_config = ConfigDict(extra="ignore")


class GitCommitArtifact(BaseModel):
    """Source representation of an incoming Git commit and its diff."""

    commit_sha: str
    commit_message: str
    author_name: str | None = None
    author_email: str | None = None
    committed_at: datetime | None = None
    snapshot_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    repository_id: uuid.UUID | None = None
    file_diffs: list[GitFileDiff] = Field(default_factory=list)
    raw_diff: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class AtomicCodeChange(BaseModel):
    """
    Canonical Code-Lane ATOM unit: The smallest independently traceable,
    meaningful code modification unit with complete Git and snapshot provenance.
    """

    id: str
    commit_sha: str
    commit_message: str
    snapshot_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    repository_file_id: uuid.UUID | None = None
    file_path: str
    old_file_path: str | None = None
    change_type: CodeChangeType
    symbol_id: uuid.UUID | None = None
    symbol_name: str | None = None
    symbol_type: str | None = None
    old_start_line: int | None = None
    old_line_count: int | None = None
    new_start_line: int | None = None
    new_line_count: int | None = None
    section_header: str | None = None
    raw_content: str
    normalized_content: str
    added_lines: list[str] = Field(default_factory=list)
    deleted_lines: list[str] = Field(default_factory=list)
    context_lines: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    atomic_facts: list[SemanticCodeFact] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class CodeDecompositionResult(BaseModel):
    """Result envelope containing decomposed atomic code-change units and summary stats."""

    commit_sha: str
    changes: list[AtomicCodeChange] = Field(default_factory=list)
    change_count: int = 0
    facts: list[SemanticCodeFact] = Field(default_factory=list)
    fact_count: int = 0
    files_affected: list[str] = Field(default_factory=list)
    symbols_affected: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
