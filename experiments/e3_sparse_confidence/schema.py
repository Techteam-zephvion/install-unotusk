"""
E3 Sparse-Project Confidence Scoring Schema Specification.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.

Adapted from unsupervised metric methodology in:
"Comparison of Unsupervised Metrics for Evaluating Judicial Decision Extraction" (arXiv:2510.01792).

Provides transparent confidence and evidence sufficiency assessment for:
1. E1 extracted code entities, relations, and events.
2. E2 candidate concepts and candidate relationships.
3. Multi-commit and sparse project-level evidence budgets.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConfidenceLevel(str, Enum):
    """Discrete confidence categories for software facts and proposals."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class SufficiencyLevel(str, Enum):
    """Categorical classification of evidence sufficiency for sparse software projects."""

    ABUNDANT = "ABUNDANT"
    MODERATE = "MODERATE"
    SPARSE = "SPARSE"
    CRITICALLY_INSUFFICIENT = "CRITICALLY_INSUFFICIENT"


class MetricScores(BaseModel):
    """Individual normalized unsupervised metric contributions (0.0 to 1.0)."""

    provenance_completeness: float = Field(default=1.0, ge=0.0, le=1.0)
    term_frequency_coherence: float = Field(default=1.0, ge=0.0, le=1.0)
    intra_block_coherence: float = Field(default=1.0, ge=0.0, le=1.0)
    structural_consistency: float = Field(default=1.0, ge=0.0, le=1.0)
    corroboration_score: float = Field(default=0.5, ge=0.0, le=1.0)
    redundancy_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    contradiction_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    coverage_ratio: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = ConfigDict(extra="ignore")


class EntityConfidenceAssessment(BaseModel):
    """Confidence assessment for an individual E1 extracted entity."""

    entity_id: str
    entity_name: str
    entity_type: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    is_abstention: bool = False
    metric_scores: MetricScores
    supporting_evidence_count: int = 1
    independent_sources_count: int = 1
    missing_signals: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    explanation: str = ""

    model_config = ConfigDict(extra="ignore")


class RelationConfidenceAssessment(BaseModel):
    """Confidence assessment for an individual E1 extracted relation."""

    relation_id: str
    subject: str
    relation_type: str
    object: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    is_abstention: bool = False
    metric_scores: MetricScores
    supporting_evidence_count: int = 1
    independent_sources_count: int = 1
    missing_signals: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    explanation: str = ""

    model_config = ConfigDict(extra="ignore")


class EventConfidenceAssessment(BaseModel):
    """Confidence assessment for an individual E1 extracted event."""

    event_id: str
    event_type: str
    target_component: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    is_abstention: bool = False
    metric_scores: MetricScores
    missing_signals: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    explanation: str = ""

    model_config = ConfigDict(extra="ignore")


class ConceptConfidenceAssessment(BaseModel):
    """Confidence assessment for an E2 induced candidate concept."""

    concept_id: str
    concept_name: str
    category: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    is_abstention: bool = False
    metric_scores: MetricScores
    member_entities_count: int = 1
    independent_files_count: int = 1
    missing_signals: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    explanation: str = ""

    model_config = ConfigDict(extra="ignore")


class RelationshipConfidenceAssessment(BaseModel):
    """Confidence assessment for an E2 induced candidate relationship."""

    relation_id: str
    subject_concept_id: str
    relation_type: str
    object_concept_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    is_abstention: bool = False
    metric_scores: MetricScores
    independent_evidence_count: int = 1
    missing_signals: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    explanation: str = ""

    model_config = ConfigDict(extra="ignore")


class ProjectConfidenceAssessment(BaseModel):
    """Global confidence and evidence sufficiency assessment across a commit history."""

    project_id: str = "default_project"
    commit_shas: list[str] = Field(default_factory=list)
    commit_count: int = 0
    total_entities_evaluated: int = 0
    total_relations_evaluated: int = 0
    total_events_evaluated: int = 0
    total_concepts_evaluated: int = 0
    total_relationships_evaluated: int = 0
    overall_confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_confidence_level: ConfidenceLevel = ConfidenceLevel.INSUFFICIENT_EVIDENCE
    evidence_sufficiency: SufficiencyLevel = SufficiencyLevel.CRITICALLY_INSUFFICIENT
    sparsity_index: float = Field(default=1.0, ge=0.0, le=1.0)
    aggregate_metric_averages: dict[str, float] = Field(default_factory=dict)
    abstention_rate: float = 0.0
    contradiction_count: int = 0
    evidence_budget_label: str = "full"
    explanation: str = ""

    model_config = ConfigDict(extra="ignore")


class E3AssessmentResult(BaseModel):
    """Complete envelope containing all E1 fact and E2 proposal confidence assessments."""

    assessment_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    commit_shas: list[str] = Field(default_factory=list)
    project_assessment: ProjectConfidenceAssessment
    entity_assessments: list[EntityConfidenceAssessment] = Field(default_factory=list)
    relation_assessments: list[RelationConfidenceAssessment] = Field(default_factory=list)
    event_assessments: list[EventConfidenceAssessment] = Field(default_factory=list)
    concept_assessments: list[ConceptConfidenceAssessment] = Field(default_factory=list)
    relationship_assessments: list[RelationshipConfidenceAssessment] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    ablation_active: dict[str, bool] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @field_validator("assessment_id")
    @classmethod
    def validate_assessment_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("assessment_id must not be empty")
        return v
