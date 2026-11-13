"""
EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs.
Reference: arXiv:2509.15464 (September 2025).

Provides deterministic, bounded multi-route query planning (T2.4),
route cost estimation, beam search graph traversal, and evidence path scoring (T2.5)
for Code Lane graph reasoning.
"""

from apps.api.src.schemas.evoreasoner import (
    AggregatedProofResult,
    BeamSearchConfig,
    EvidenceEdge,
    EvidencePath,
    EvoPlannerConfig,
    GroundedProofChain,
    MultiRoutePlan,
    PathScoreBreakdown,
    PathSearchResult,
    ProofAggregationConfig,
    ProofChainHop,
    ReasoningHop,
    ReasoningRoute,
    RouteCostBreakdown,
    RoutePerspective,
)
from apps.api.src.services.evoreasoner.aggregator import ProofChainAggregator
from apps.api.src.services.evoreasoner.beam_search import EvoBeamSearchEngine
from apps.api.src.services.evoreasoner.cost_estimator import RouteCostEstimator
from apps.api.src.services.evoreasoner.deduplicator import RouteDeduplicator
from apps.api.src.services.evoreasoner.path_scorer import PathScorer
from apps.api.src.services.evoreasoner.planner import EvoRoutePlanner
from apps.api.src.services.evoreasoner.validator import ProofChainValidator

__all__ = [
    "AggregatedProofResult",
    "BeamSearchConfig",
    "EvidenceEdge",
    "EvidencePath",
    "EvoBeamSearchEngine",
    "EvoPlannerConfig",
    "EvoRoutePlanner",
    "GroundedProofChain",
    "MultiRoutePlan",
    "PathScoreBreakdown",
    "PathSearchResult",
    "PathScorer",
    "ProofAggregationConfig",
    "ProofChainAggregator",
    "ProofChainHop",
    "ProofChainValidator",
    "ReasoningHop",
    "ReasoningRoute",
    "RouteCostBreakdown",
    "RouteCostEstimator",
    "RouteDeduplicator",
    "RoutePerspective",
]
