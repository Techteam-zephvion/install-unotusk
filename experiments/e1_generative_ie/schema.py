"""
E1 Generative Information Extraction Schema Specification.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept (arXiv:2312.17617).
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidationStatus(str, Enum):
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    UNCERTAIN = "UNCERTAIN"


class ExtractionMethod(str, Enum):
    DETERMINISTIC_AST = "DETERMINISTIC_AST"
    GENERATIVE_LLM = "GENERATIVE_LLM"
    HYBRID_RECONCILED = "HYBRID_RECONCILED"


class E1EntityType(str, Enum):
    SERVICE = "SERVICE"
    MODULE = "MODULE"
    FILE = "FILE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    API = "API"
    DEPENDENCY = "DEPENDENCY"
    CONFIG_PARAM = "CONFIG_PARAM"
    TEST = "TEST"
    DATASTORE = "DATASTORE"
    OTHER = "OTHER"


class E1RelationType(str, Enum):
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    DEFINES = "DEFINES"
    INHERITS = "INHERITS"
    MUTATES = "MUTATES"
    CONFIGURES = "CONFIGURES"
    VALIDATES = "VALIDATES"
    RAISES = "RAISES"
    REFERENCES = "REFERENCES"
    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    MODIFIES = "MODIFIES"
    REPLACES = "REPLACES"
    SUPERSEDES = "SUPERSEDES"
    TESTS = "TESTS"


class E1EventType(str, Enum):
    COMPONENT_INTRODUCED = "COMPONENT_INTRODUCED"
    COMPONENT_MODIFIED = "COMPONENT_MODIFIED"
    COMPONENT_DELETED = "COMPONENT_DELETED"
    DEPENDENCY_ADDED = "DEPENDENCY_ADDED"
    DEPENDENCY_REMOVED = "DEPENDENCY_REMOVED"
    DEPENDENCY_CHANGED = "DEPENDENCY_CHANGED"
    API_CHANGED = "API_CHANGED"
    BEHAVIOR_CHANGED = "BEHAVIOR_CHANGED"
    TEST_MODIFIED = "TEST_MODIFIED"
    CONFIGURATION_UPDATED = "CONFIGURATION_UPDATED"
    IMPLEMENTATION_DEPRECATED = "IMPLEMENTATION_DEPRECATED"
    IMPLEMENTATION_REPLACED = "IMPLEMENTATION_REPLACED"


class E1SourceEvidence(BaseModel):
    """Traceable, immutable provenance evidence for extracted facts."""

    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    diff_snippet: str = ""
    grounded_tokens: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class E1Entity(BaseModel):
    """Code Lane entity identified during information extraction."""

    entity_id: str
    entity_type: str = E1EntityType.OTHER.value
    entity_name: str
    file_path: str
    symbol_scope: str | None = None
    evidence: E1SourceEvidence
    confidence: float = 1.0
    validation_status: ValidationStatus = ValidationStatus.VALIDATED

    model_config = ConfigDict(extra="ignore")


class E1Relation(BaseModel):
    """Directed semantic relationship binding two code entities."""

    relation_id: str
    subject: str
    relation_type: str = E1RelationType.REFERENCES.value
    object: str
    t_start: datetime | None = None
    t_end: datetime | None = None
    t_obs: datetime | None = None
    is_exclusive: bool = False
    evidence: E1SourceEvidence
    confidence: float = 1.0
    validation_status: ValidationStatus = ValidationStatus.VALIDATED

    model_config = ConfigDict(extra="ignore")


class E1Event(BaseModel):
    """Software evolution event representing a state transition in code."""

    event_id: str
    event_type: str = E1EventType.COMPONENT_MODIFIED.value
    trigger_statement: str
    target_component: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    t_start: datetime | None = None
    t_end: datetime | None = None
    t_obs: datetime | None = None
    evidence: E1SourceEvidence
    confidence: float = 1.0
    validation_status: ValidationStatus = ValidationStatus.VALIDATED

    model_config = ConfigDict(extra="ignore")


class E1ExtractionResult(BaseModel):
    """Complete result envelope for an E1 extraction run."""

    schema_version: str = "1.0.0"
    extraction_method: ExtractionMethod = ExtractionMethod.GENERATIVE_LLM
    repository_id: str = "default_repo"
    branch: str = "main"
    commit_sha: str
    commit_message: str
    entities: list[E1Entity] = Field(default_factory=list)
    relations: list[E1Relation] = Field(default_factory=list)
    events: list[E1Event] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    abstention_triggered: bool = False
    latency_ms: float = 0.0
    model_name: str = "offline_fallback"
    raw_llm_response: dict[str, Any] | None = None

    model_config = ConfigDict(extra="ignore")
