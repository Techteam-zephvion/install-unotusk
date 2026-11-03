"""
Route Cost Estimator for EvoReasoner (T2.4 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Implements a transparent, deterministic cost model evaluating graph exploration paths:
Cost = w_hops * H + w_branch * B + w_entropy * E + w_temporal * Delta_T + w_complexity * C

Lower cost represents a more efficient, direct, and lower-uncertainty reasoning path.
Route cost is strictly an exploration efficiency metric, separate from evidence confidence.
"""

from __future__ import annotations

import logging

from apps.api.src.schemas.code_atom import RelationType
from apps.api.src.schemas.evoreasoner import (
    EvoPlannerConfig,
    ReasoningHop,
    RouteCostBreakdown,
)
from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy
from apps.api.src.services.context_engine.memotime import TemporalIntentType

logger = logging.getLogger(__name__)

# Heuristic base branching factors grounded in CodeRelationTaxonomy
DEFAULT_BRANCHING_FACTORS: dict[RelationType, float] = {
    RelationType.DEFINES: 1.0,
    RelationType.DEFINES_RETURN_TYPE: 1.0,
    RelationType.HAS_SIGNATURE: 1.0,
    RelationType.ASSIGNED_TYPE: 1.0,
    RelationType.MODULE_LOCATION: 1.0,
    RelationType.INHERITS: 1.0,
    RelationType.RAISES: 2.0,
    RelationType.VALIDATES: 2.0,
    RelationType.CONFIGURES: 2.5,
    RelationType.MUTATES: 3.0,
    RelationType.IMPORTS: 3.5,
    RelationType.CALLS: 4.0,
    RelationType.REFERENCES: 5.0,
}

# Heuristic branching entropy (uncertainty / fanout spread)
DEFAULT_ENTROPY_VALUES: dict[RelationType, float] = {
    RelationType.DEFINES: 0.0,
    RelationType.DEFINES_RETURN_TYPE: 0.0,
    RelationType.HAS_SIGNATURE: 0.0,
    RelationType.ASSIGNED_TYPE: 0.0,
    RelationType.MODULE_LOCATION: 0.0,
    RelationType.INHERITS: 0.0,
    RelationType.RAISES: 0.4,
    RelationType.VALIDATES: 0.4,
    RelationType.CONFIGURES: 0.5,
    RelationType.MUTATES: 0.6,
    RelationType.IMPORTS: 0.7,
    RelationType.CALLS: 0.8,
    RelationType.REFERENCES: 1.2,
}

# Conservative fallbacks for unclassified/unknown predicates
FALLBACK_BRANCHING = 5.0
FALLBACK_ENTROPY = 1.5
FALLBACK_TEMPORAL_DISTANCE = 1.0


class RouteCostEstimator:
    """
    Deterministic cost estimator for graph reasoning routes in EvoReasoner.
    """

    @classmethod
    def get_relation_branching(cls, relation: RelationType | str) -> float:
        """Determines expected branching factor using taxonomy exclusivity and predicates."""
        canon = CodeRelationTaxonomy.normalize_predicate(relation)
        if canon is None:
            raw_upper = str(relation).strip().upper()
            if "SUPERSEDE" in raw_upper:
                return 1.2
            return FALLBACK_BRANCHING

        if CodeRelationTaxonomy.is_exclusive(canon):
            return 1.0

        return DEFAULT_BRANCHING_FACTORS.get(canon, FALLBACK_BRANCHING)

    @classmethod
    def get_relation_entropy(cls, relation: RelationType | str) -> float:
        """Determines expected branching entropy using taxonomy exclusivity and predicates."""
        canon = CodeRelationTaxonomy.normalize_predicate(relation)
        if canon is None:
            raw_upper = str(relation).strip().upper()
            if "SUPERSEDE" in raw_upper:
                return 0.2
            return FALLBACK_ENTROPY

        if CodeRelationTaxonomy.is_exclusive(canon):
            return 0.0

        return DEFAULT_ENTROPY_VALUES.get(canon, FALLBACK_ENTROPY)

    @classmethod
    def compute_temporal_distance(
        cls,
        hop_temporal_constraint: str,
        query_intent: TemporalIntentType | str,
    ) -> float:
        """
        Calculates temporal distance penalty based on how well the hop's temporal
        scope aligns with the requested query intent.
        """
        intent_str = (
            query_intent.value
            if isinstance(query_intent, TemporalIntentType)
            else str(query_intent).upper()
        )
        constraint_upper = hop_temporal_constraint.strip().upper()

        # Handle unknown, missing, or unanchored temporal constraint conservatively
        if not constraint_upper or any(u in constraint_upper for u in ("UNKNOWN", "NONE", "UNSPECIFIED")):
            return FALLBACK_TEMPORAL_DISTANCE

        # Clean alignment with current active state
        if intent_str == "CURRENT":
            if constraint_upper in {"CURRENT", "LATEST", "PRESENT"}:
                return 0.0
            if "HISTORICAL" in constraint_upper or "DIFF" in constraint_upper:
                return 1.5  # Heavy penalty for navigating historical code during a CURRENT query
            return 0.5

        # Historical query intent
        if intent_str == "HISTORICAL":
            if "HISTORICAL" in constraint_upper or "SUPERSEDE" in constraint_upper:
                return 0.2  # Well-anchored historical trace
            if constraint_upper == "CURRENT":
                return 1.0  # Deviates from historical intent
            return 0.4

        # Interval, before, after, diff, evolution
        if intent_str in {"BEFORE", "AFTER", "INTERVAL", "DIFF", "EVOLUTION"}:
            if intent_str in constraint_upper:
                return 0.1  # Directly targeted constraint
            if "SUPERSEDE" in constraint_upper or "COMMIT" in constraint_upper:
                return 0.25
            return 0.8

        return FALLBACK_TEMPORAL_DISTANCE

    @classmethod
    def compute_route_complexity(
        cls,
        hops: list[ReasoningHop],
    ) -> float:
        """
        Calculates structural complexity of a route based on entity diversity,
        traversal direction changes, and relation variety.
        """
        if not hops:
            return 1.0

        entity_types = {h.source_type for h in hops} | {h.target_type for h in hops}
        entity_type_penalty = max(0, len(entity_types) - 1) * 0.2

        inverse_hops_count = sum(1 for h in hops if h.is_inverse)
        inverse_penalty = inverse_hops_count * 0.3

        # Check for mixed paradigm traversals (e.g. definition + calls)
        has_structural = any(
            CodeRelationTaxonomy.is_exclusive(h.canonical_relation) for h in hops
        )
        has_behavioral = any(
            not CodeRelationTaxonomy.is_exclusive(h.canonical_relation) for h in hops
        )
        mixed_penalty = 0.2 if (has_structural and has_behavioral) else 0.0

        base_complexity = 1.0 + entity_type_penalty + inverse_penalty + mixed_penalty
        return round(base_complexity, 4)

    @classmethod
    def estimate_cost(
        cls,
        hops: list[ReasoningHop],
        intent: TemporalIntentType | str,
        config: EvoPlannerConfig | None = None,
    ) -> tuple[float, RouteCostBreakdown]:
        """
        Computes the deterministic cost breakdown and aggregate cost for a candidate route.

        Formula:
        Total Cost = w_hops * H + w_branch * B + w_entropy * E + w_temporal * Delta_T + w_complexity * C
        """
        cfg = config or EvoPlannerConfig()
        hop_count = len(hops)
        if hop_count == 0:
            zero_breakdown = RouteCostBreakdown(
                hop_count=0,
                hop_cost=0.0,
                branching_factor=0.0,
                branching_cost=0.0,
                branching_entropy=0.0,
                entropy_cost=0.0,
                temporal_distance=0.0,
                temporal_cost=0.0,
                complexity=1.0,
                complexity_cost=round(cfg.w_complexity * 1.0, 4),
                total_cost=round(cfg.w_complexity * 1.0, 4),
            )
            return zero_breakdown.total_cost, zero_breakdown

        # 1. Hop count cost
        hop_cost = round(cfg.w_hops * float(hop_count), 4)

        # 2. Branching factor calculation
        branching_vals: list[float] = []
        for h in hops:
            val = (
                h.expected_branching
                if h.expected_branching > 0
                else cls.get_relation_branching(h.relation)
            )
            # Enforce max branching factor cap
            branching_vals.append(min(val, cfg.max_branching_factor))

        avg_branching = sum(branching_vals) / float(hop_count)
        branching_cost = round(cfg.w_branch * avg_branching, 4)

        # 3. Branching entropy calculation
        entropy_vals: list[float] = []
        for h in hops:
            e_val = (
                h.expected_entropy
                if h.expected_entropy >= 0
                else cls.get_relation_entropy(h.relation)
            )
            entropy_vals.append(e_val)

        avg_entropy = sum(entropy_vals) / float(hop_count)
        entropy_cost = round(cfg.w_entropy * avg_entropy, 4)

        # 4. Temporal distance calculation
        temporal_vals: list[float] = []
        for h in hops:
            t_dist = (
                h.temporal_distance
                if h.temporal_distance > 0
                else cls.compute_temporal_distance(h.temporal_constraint, intent)
            )
            temporal_vals.append(t_dist)

        avg_temporal = sum(temporal_vals) / float(hop_count)
        temporal_cost = round(cfg.w_temporal * avg_temporal, 4)

        # 5. Complexity calculation
        complexity_val = cls.compute_route_complexity(hops)
        complexity_cost = round(cfg.w_complexity * complexity_val, 4)

        # Aggregate total cost
        total_cost = round(
            hop_cost + branching_cost + entropy_cost + temporal_cost + complexity_cost,
            4,
        )

        breakdown = RouteCostBreakdown(
            hop_count=hop_count,
            hop_cost=hop_cost,
            branching_factor=round(avg_branching, 4),
            branching_cost=branching_cost,
            branching_entropy=round(avg_entropy, 4),
            entropy_cost=entropy_cost,
            temporal_distance=round(avg_temporal, 4),
            temporal_cost=temporal_cost,
            complexity=round(complexity_val, 4),
            complexity_cost=complexity_cost,
            total_cost=total_cost,
        )

        return total_cost, breakdown
