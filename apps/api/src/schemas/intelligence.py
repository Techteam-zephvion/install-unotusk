import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EvidenceItem(BaseModel):
    model_config = {"extra": "ignore"}

    type: str = Field(description="Type of evidence: file, symbol, chunk, dependency")
    file: str = Field(description="File relative path")
    symbol: str | None = Field(default=None, description="Symbol name if applicable")
    lines: str | None = Field(default=None, description="Line range e.g. 24-41")
    relevance: float = Field(description="Normalized relevance score 0.0-1.0")
    snippet: str | None = Field(default=None, description="Code or text snippet")
    commit_sha: str | None = Field(default=None, description="Git commit SHA")
    commit_message: str | None = Field(default=None, description="Git commit message")
    repository_id: str | None = Field(default=None, description="Repository identifier")
    snapshot_id: str | None = Field(default=None, description="Snapshot identifier")
    file_id: str | None = Field(default=None, description="File UUID string")
    symbol_id: str | None = Field(default=None, description="Symbol UUID string")
    fingerprint: str | None = Field(default=None, description="Chunk content or AST fingerprint")
    chunk_type: str | None = Field(default=None, description="Chunk type e.g. code, docstring")
    committed_at: str | None = Field(default=None, description="Commit timestamp")
    is_current: bool | None = Field(default=None, description="Whether this chunk reflects current state")
    is_superseded: bool | None = Field(default=None, description="Whether this chunk has been superseded")
    is_deleted: bool | None = Field(default=None, description="Whether this entity is marked deleted")
    superseded_by_sha: str | None = Field(default=None, description="SHA of commit that superseded this chunk")
    superseded_by_date: str | None = Field(default=None, description="Date when this chunk was superseded")
    renamed_from: str | None = Field(default=None, description="Original file path if renamed")
    renamed_to: str | None = Field(default=None, description="New file path if renamed")
    relationship_path: str | None = Field(default=None, description="Graph expansion relationship path")
    relationship_type: str | None = Field(default=None, description="Relationship type")
    relationship_hop: int | None = Field(default=None, description="Hop distance in graph expansion")
    connected_from: str | None = Field(default=None, description="Source entity for graph connection")
    retrieval_reason: str | None = Field(default=None, description="Reason for retrieving this entity")
    alternative_paths: list[str] | None = Field(default=None, description="Alternative graph paths")
    provenance: dict[str, Any] | str | None = Field(default=None, description="Detailed provenance metadata")
    atomic_code_facts: list[Any] | None = Field(default=None, description="Grounded atomic code facts")
    temporal_relations: list[Any] | None = Field(default=None, description="Temporal relationship tuples")



class GroundedAskRequest(BaseModel):
    question: str = Field(
        min_length=2, max_length=2000, description="Natural language question about the project"
    )
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Optional conversation ID to continue a thread"
    )
    thinking_tier: str | None = Field(
        default="warm",
        description="Reasoning thinking tier: 'hot' (fast/light), 'warm' (balanced/default), 'cold' (deep/thorough)",
    )

    @field_validator("thinking_tier")
    @classmethod
    def validate_thinking_tier(cls, v: str | None) -> str:
        if v is None:
            return "warm"
        v_clean = str(v).strip().lower()
        if v_clean not in ("hot", "warm", "cold"):
            raise ValueError(
                f"Invalid thinking_tier: '{v}'. Supported values are: 'hot', 'warm', 'cold'."
            )
        return v_clean


class GroundedAnswerResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    role: str = "assistant"
    content: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    confidence: str = Field(default="HIGH", description="Confidence level: HIGH, MEDIUM, LOW")
    debug_signals: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Specification creation timestamp"
    )


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    initial_question: str | None = Field(default=None, max_length=2000)


class ConversationRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    confidence: str | None = None
    debug_signals: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ContextSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)


class ContextCandidateDebug(BaseModel):
    name: str
    entity_type: str
    path: str
    lines: str
    score: float
    reasons: list[str]
    snippet: str


class ContextSearchResponse(BaseModel):
    query: str
    keywords: list[str]
    symbol_candidates: list[str]
    candidates_count: int
    ranked_candidates: list[ContextCandidateDebug]


class BDDScenarioItem(BaseModel):
    model_config = {"extra": "ignore"}

    id: int = Field(description="Scenario index number")
    title: str = Field(description="Scenario summary title")
    given: str = Field(description="Initial precondition or context")
    when: str = Field(description="Event or action triggered")
    then: str = Field(description="Expected outcome or assertion")
    cited_files: list[str] = Field(default_factory=list, description="Referenced source files")
    cited_symbols: list[str] = Field(default_factory=list, description="Referenced functions/classes")


class FeatureSpecRequest(BaseModel):
    feature_request: str = Field(
        min_length=3,
        max_length=3000,
        description="Natural language description of requested feature or spec requirements",
    )
    thinking_tier: str | None = Field(
        default="warm",
        description="Reasoning thinking tier: 'hot', 'warm', or 'cold'",
    )


class FeatureSpecificationResponse(BaseModel):
    model_config = {"extra": "ignore"}

    project_id: uuid.UUID
    feature_name: str
    intent: str
    confidence: str = Field(default="HIGH", description="Confidence level: HIGH, MEDIUM, LOW")
    confirmed_code_facts: list[str] = Field(
        default_factory=list, description="Verified facts grounded directly in current codebase"
    )
    inferred_requirements: list[str] = Field(
        default_factory=list, description="New requirements inferred for requested feature"
    )
    scenarios: list[BDDScenarioItem] = Field(
        default_factory=list, description="Structured BDD Given/When/Then scenarios"
    )
    evidence: list[EvidenceItem] = Field(
        default_factory=list, description="Grounded code evidence items with complete provenance"
    )
    cited_files: list[str] = Field(default_factory=list, description="List of unique source files cited")
    cited_symbols: list[str] = Field(default_factory=list, description="List of unique symbols cited")
    has_superseded_precursors: bool = Field(
        default=False, description="Whether historical/superseded code was identified"
    )
    warning: str | None = Field(
        default=None, description="Diagnostic warning if evidence is partial, empty, or unanchored"
    )
    debug_signals: dict[str, Any] = Field(
        default_factory=dict, description="Retriever and ranker telemetry signals"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Specification creation timestamp"
    )

