import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PropertyExclusivity(str, Enum):
    EXCLUSIVE = "EXCLUSIVE"
    NON_EXCLUSIVE = "NON_EXCLUSIVE"


class ScopeKeyStrategy(str, Enum):
    GLOBAL = "GLOBAL"
    OVERLOAD_INDEX = "OVERLOAD_INDEX"
    LEXICAL_SCOPE = "LEXICAL_SCOPE"
    INHERITANCE_SLOT = "INHERITANCE_SLOT"
    SYMBOL_NAME = "SYMBOL_NAME"
    CANONICAL_PATH = "CANONICAL_PATH"
    CONCURRENT = "CONCURRENT"
    UNCERTAIN = "UNCERTAIN"


class TemporalSupersessionPolicy(str, Enum):
    CONCURRENT = "CONCURRENT"
    SLOT_EXCLUSIVE = "SLOT_EXCLUSIVE"
    CONTAINER_EXCLUSIVE = "CONTAINER_EXCLUSIVE"
    PATH_EXCLUSIVE = "PATH_EXCLUSIVE"
    PRESERVE_UNCERTAIN = "PRESERVE_UNCERTAIN"


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


class RelationType(str, Enum):
    CALLS = "CALLS"
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    MUTATES = "MUTATES"
    CONFIGURES = "CONFIGURES"
    VALIDATES = "VALIDATES"
    RAISES = "RAISES"
    REFERENCES = "REFERENCES"
    # EvoKG Code Lane extensions (arXiv:2509.15464 §3.1-3.2)
    DEFINES_RETURN_TYPE = "DEFINES_RETURN_TYPE"
    HAS_SIGNATURE = "HAS_SIGNATURE"
    ASSIGNED_TYPE = "ASSIGNED_TYPE"
    MODULE_LOCATION = "MODULE_LOCATION"


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


class TemporalCodeRelation(BaseModel):
    """
    Module 2: Temporal 5-Tuple Extraction (Code-Lane).
    Represents a structured code relationship with temporal validity:
    (subject, relation, object, t_start, t_end) along with observation timestamp t_obs.
    Extended for EvoKG (arXiv:2509.15464) with exclusivity metadata, deterministic
    scope keys, and confidence separation.
    """

    id: str
    subject: str
    relation: RelationType | str
    object: str
    t_start: datetime | None = None
    t_end: datetime | None = None
    t_obs: datetime | None = None
    confidence: FactConfidence = FactConfidence.HIGH
    is_uncertain: bool = False
    source_fact_id: str | None = None
    commit_sha: str | None = None
    file_path: str | None = None
    symbol_name: str | None = None
    canonical_subject: str | None = None
    canonical_object: str | None = None
    aliases: list[str] = Field(default_factory=list)
    has_temporal_conflict: bool = False
    conflict_detail: str | None = None
    history_commit_shas: list[str] = Field(default_factory=list)
    history_fact_ids: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str

    # EvoKG Code Lane extensions (arXiv:2509.15464)
    is_exclusive: bool = False
    scope_key: str = "default"
    confidence_score: float = 0.50
    superseded_by_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _sync_evokg_metadata(cls, data: Any) -> Any:
        if isinstance(data, dict):
            rel = data.get("relation")

            # 1. Taxonomy classification lookup
            taxonomy_entry = None
            if rel:
                try:
                    from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy

                    taxonomy_entry = CodeRelationTaxonomy.classify(rel)
                except ImportError:
                    pass

            # 2. Exclusivity: if not explicitly passed, derive from taxonomy
            if "is_exclusive" not in data:
                if taxonomy_entry is not None:
                    data["is_exclusive"] = taxonomy_entry.exclusivity == PropertyExclusivity.EXCLUSIVE
                else:
                    data["is_exclusive"] = False

            # 3. Scope key: if not explicitly passed, derive from taxonomy
            scope_key_uncertain = False
            if "scope_key" not in data:
                if taxonomy_entry is not None:
                    from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy

                    key, uncertain = CodeRelationTaxonomy.generate_scope_key(
                        rel,
                        symbol_name=data.get("symbol_name"),
                    )
                    data["scope_key"] = key
                    if uncertain:
                        scope_key_uncertain = True
                else:
                    data["scope_key"] = "default"

            # 4. Unknown / unclassified relation uncertainty
            if taxonomy_entry is not None and taxonomy_entry.scope_strategy == ScopeKeyStrategy.UNCERTAIN:
                scope_key_uncertain = True

            # 5. Confidence consistency (Phase 5)
            # If scope_key couldn't be resolved or relation is unknown, force uncertainty
            if scope_key_uncertain:
                data["is_uncertain"] = True

            is_unc = data.get("is_uncertain", False)
            conf = data.get("confidence")

            if is_unc:
                # Uncertain relations must never present as HIGH confidence
                if conf is None or conf == FactConfidence.HIGH or conf == "HIGH":
                    data["confidence"] = FactConfidence.UNCERTAIN
            elif conf == FactConfidence.UNCERTAIN or conf == "UNCERTAIN":
                # UNCERTAIN confidence category must agree with uncertainty flag
                data["is_uncertain"] = True

            # 6. Numeric confidence score calibration
            if "confidence_score" not in data:
                c = data.get("confidence", FactConfidence.HIGH)
                if data.get("is_uncertain"):
                    data["confidence_score"] = 0.30
                elif c == FactConfidence.HIGH or c == "HIGH":
                    data["confidence_score"] = 0.95
                elif c == FactConfidence.MEDIUM or c == "MEDIUM":
                    data["confidence_score"] = 0.70
                else:
                    data["confidence_score"] = 0.30

        return data

    model_config = ConfigDict(extra="ignore")


AtomicCodeRelation = TemporalCodeRelation


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
    temporal_relations: list[TemporalCodeRelation] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class CodeDecompositionResult(BaseModel):
    """Result envelope containing decomposed atomic code-change units and summary stats."""

    commit_sha: str
    changes: list[AtomicCodeChange] = Field(default_factory=list)
    change_count: int = 0
    facts: list[SemanticCodeFact] = Field(default_factory=list)
    fact_count: int = 0
    relations: list[TemporalCodeRelation] = Field(default_factory=list)
    relation_count: int = 0
    files_affected: list[str] = Field(default_factory=list)
    symbols_affected: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
