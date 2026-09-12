import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    type: str = Field(description="Type of evidence: file, symbol, chunk, dependency")
    file: str = Field(description="File relative path")
    symbol: str | None = Field(default=None, description="Symbol name if applicable")
    lines: str | None = Field(default=None, description="Line range e.g. 24-41")
    relevance: float = Field(description="Normalized relevance score 0.0-1.0")
    snippet: str | None = Field(default=None, description="Code or text snippet")


class GroundedAskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000, description="Natural language question about the project")
    conversation_id: uuid.UUID | None = Field(default=None, description="Optional conversation ID to continue a thread")


class GroundedAnswerResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    role: str = "assistant"
    content: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    confidence: str = Field(default="HIGH", description="Confidence level: HIGH, MEDIUM, LOW")
    debug_signals: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


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
