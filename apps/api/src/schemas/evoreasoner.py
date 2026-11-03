"""
EvoReasoner Query Planner and Route Cost Schemas (T2.4 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Defines data contracts for:
1. Reasoning hops across evolving code knowledge graph entities.
2. Multi-route query planning representations across distinct perspectives.
3. Transparent, deterministic route cost breakdown and configuration.
4. Bounded top-N plan outputs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.api.src.schemas.code_atom import PropertyExclusivity, RelationType
from apps.api.src.services.context_engine.memotime import TemporalIntentType


class RoutePerspective(str, Enum):
    """Reasoning perspective archetype for graph exploration."""

    STRUCTURAL = "STRUCTURAL"  # AST hierarchy, symbol definitions, class containment
    BEHAVIORAL_CALLGRAPH = "BEHAVIORAL_CALLGRAPH"  # Caller/callee invocation paths, mutation
    ARCHITECTURAL_DEPENDENCY = "ARCHITECTURAL_DEPENDENCY"  # Module imports, file locations, packaging
    TEMPORAL_LINEAGE = "TEMPORAL_LINEAGE"  # Supersession history, commit deltas, evolution
    SIGNATURE_SPEC = "SIGNATURE_SPEC"  # Method/function signatures, return types, contracts


class ReasoningHop(BaseModel):
    """A single step along an EvoReasoner graph reasoning path."""

    hop_index: int
    source_entity: str
    source_type: str = "symbol"  # "symbol", "function", "class", "module", "file", "assertion"
    relation: RelationType | str
    canonical_relation: RelationType
    target_entity: str
    target_type: str = "symbol"
    temporal_constraint: str = "CURRENT"
    is_inverse: bool = False
    expected_branching: float = 1.0
    expected_entropy: float = 0.0
    temporal_distance: float = 0.0
    exclusivity: PropertyExclusivity = PropertyExclusivity.NON_EXCLUSIVE
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class RouteCostBreakdown(BaseModel):
    """Detailed transparent breakdown of estimated route exploration costs."""

    hop_count: int
    hop_cost: float
    branching_factor: float
    branching_cost: float
    branching_entropy: float
    entropy_cost: float
    temporal_distance: float
    temporal_cost: float
    complexity: float
    complexity_cost: float
    total_cost: float

    model_config = ConfigDict(extra="ignore")


class ReasoningRoute(BaseModel):
    """A generated candidate or selected reasoning path for answering a query."""

    route_id: str
    name: str
    intent: TemporalIntentType
    perspective: RoutePerspective
    hops: list[ReasoningHop]
    estimated_cost: float
    cost_breakdown: RouteCostBreakdown
    canonical_key: str
    is_fallback: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class EvoPlannerConfig(BaseModel):
    """Configuration for EvoReasoner bounded multi-route query planning."""

    max_candidate_routes: int = 20
    max_selected_routes: int = 3
    max_route_hops: int = 4
    max_branching_factor: float = 10.0

    # Cost weights (w_hops * H + w_branch * B + w_entropy * E + w_temporal * Delta_T + w_complexity * C)
    w_hops: float = 1.0
    w_branch: float = 0.5
    w_entropy: float = 0.3
    w_temporal: float = 0.4
    w_complexity: float = 0.2

    model_config = ConfigDict(extra="ignore")


class MultiRoutePlan(BaseModel):
    """Deterministic, bounded plan containing alternative graph reasoning routes."""

    query_text: str
    temporal_intent: TemporalIntentType
    selected_routes: list[ReasoningRoute]
    all_candidate_count: int
    deduplicated_count: int
    is_bounded: bool = True
    planning_diagnostics: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class EvidenceEdge(BaseModel):
    """A single traversed edge grounded in an actual persisted EvoKGTriplet."""

    triplet_id: uuid.UUID
    subject_id: str
    relation: str
    canonical_relation: RelationType
    object_id: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    observation_time: datetime | None = None
    commit_sha: str | None = None
    branch: str = "main"
    confidence_score: float = 0.50
    is_uncertain: bool = False
    has_temporal_conflict: bool = False
    conflict_detail: str | None = None
    is_exclusive: bool = False
    scope_key: str = "default"
    is_inverse: bool = False
    superseded_by_id: uuid.UUID | None = None
    supersedes_id: uuid.UUID | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class PathScoreBreakdown(BaseModel):
    """Component-by-component breakdown of explainable path ranking score."""

    evidence_confidence: float
    relation_alignment: float
    entity_continuity: float
    temporal_compatibility: float
    uncertainty_penalty: float
    conflict_penalty: float
    length_penalty: float
    raw_score: float
    final_score: float

    model_config = ConfigDict(extra="ignore")


class EvidencePath(BaseModel):
    """An evidence-backed path through repository entities and relationships."""

    path_id: str
    route_id: str
    route_perspective: RoutePerspective
    source_entity: str
    target_entity: str
    edges: list[EvidenceEdge]
    repository_id: uuid.UUID
    branch: str = "main"
    commit_shas: list[str] = Field(default_factory=list)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    mean_confidence: float = 0.50
    has_uncertain_evidence: bool = False
    has_temporal_conflict: bool = False
    route_estimated_cost: float = 1.0
    path_score: float = 0.0
    score_breakdown: PathScoreBreakdown
    canonical_signature: str = ""
    is_complete: bool = True
    search_diagnostics: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class BeamSearchConfig(BaseModel):
    """Configurable limits and scoring weights for EvoReasoner beam search."""

    beam_width: int = 3
    max_path_depth: int = 4
    max_expansions_per_node: int = 5
    max_total_expansions: int = 50
    max_returned_paths: int = 5

    # Path scoring formula weights
    w_confidence: float = 0.35
    w_relation: float = 0.25
    w_continuity: float = 0.20
    w_temporal: float = 0.20
    w_uncertainty_penalty: float = 0.15
    w_conflict_penalty: float = 0.20
    w_length_penalty: float = 0.05

    model_config = ConfigDict(extra="ignore")


class PathSearchResult(BaseModel):
    """Execution output from bounded beam search over EvoKG triplets."""

    query_text: str
    temporal_intent: TemporalIntentType
    repository_id: uuid.UUID
    branch: str
    paths: list[EvidencePath] = Field(default_factory=list)
    total_paths_explored: int = 0
    total_expansions: int = 0
    search_diagnostics: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class ProofChainHop(BaseModel):
    """An individual verified hop within a grounded proof chain."""

    hop_index: int
    source_entity: str
    source_type: str = "symbol"
    relation: str
    canonical_relation: RelationType
    target_entity: str
    target_type: str = "symbol"
    is_inverse: bool = False
    triplet_id: uuid.UUID
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    observation_time: datetime | None = None
    commit_sha: str | None = None
    branch: str = "main"
    confidence: float = 0.50
    is_uncertain: bool = False
    has_conflict: bool = False
    conflict_detail: str | None = None
    is_exclusive: bool = False
    scope_key: str = "default"
    is_superseded: bool = False
    provenance: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class GroundedProofChain(BaseModel):
    """A validated, aggregated multi-hop proof chain grounding repository relationships."""

    chain_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_text: str = ""
    temporal_intent: TemporalIntentType = TemporalIntentType.CURRENT
    source_entity: str
    target_entity: str
    canonical_relation: str = ""
    direction: str = "forward"  # "forward", "inverse", "bidirectional"
    repository_id: uuid.UUID
    branch: str = "main"
    hops: list[ProofChainHop] = Field(default_factory=list)
    commit_shas: list[str] = Field(default_factory=list)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_historical: bool = False
    confidence: float = 0.50
    has_uncertain_evidence: bool = False
    uncertainty_reasons: list[str] = Field(default_factory=list)
    has_conflict: bool = False
    conflict_reasons: list[str] = Field(default_factory=list)
    original_path_scores: list[float] = Field(default_factory=list)
    proof_score: float = 0.0
    supporting_triplet_ids: list[uuid.UUID] = Field(default_factory=list)
    constituent_path_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class ProofAggregationConfig(BaseModel):
    """Configuration parameters for proof-chain validation and aggregation."""

    max_proof_chains: int = 3
    max_hops_per_chain: int = 4
    min_path_score: float = 0.10
    allow_uncertain_chains: bool = True
    uncertainty_penalty: float = 0.10
    conflict_penalty: float = 0.20
    corroboration_bonus: float = 0.05

    model_config = ConfigDict(extra="ignore")


class AggregatedProofResult(BaseModel):
    """Output of proof-chain aggregation over evidence paths."""

    query_text: str
    temporal_intent: TemporalIntentType
    repository_id: uuid.UUID
    branch: str = "main"
    chains: list[GroundedProofChain] = Field(default_factory=list)
    rejected_paths_count: int = 0
    deduplicated_chains_count: int = 0
    aggregation_diagnostics: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

