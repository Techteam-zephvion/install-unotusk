"""
Semantic Route Deduplicator for EvoReasoner (T2.4 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Provides:
1. Deterministic canonical route fingerprinting.
2. Semantic deduplication preserving lower-cost alternatives.
3. Perspective preservation ensuring structural, behavioral, architectural, and temporal diversity.
4. Stable deterministic tie-breaking.
"""

from __future__ import annotations

import logging

from apps.api.src.schemas.evoreasoner import ReasoningHop, ReasoningRoute
from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy

logger = logging.getLogger(__name__)


class RouteDeduplicator:
    """
    Deduplicates semantically redundant reasoning paths while preserving
    meaningfully distinct perspective archetypes.
    """

    @classmethod
    def generate_hop_canonical_key(cls, hop: ReasoningHop) -> str:
        """
        Creates a normalized, canonical representation of a reasoning hop.
        Accounts for predicate normalization and inverse directions.
        """
        canon_rel = CodeRelationTaxonomy.get_canonical_predicate(hop.relation)
        src_norm = hop.source_entity.strip().lower()
        tgt_norm = hop.target_entity.strip().lower()
        temp_norm = hop.temporal_constraint.strip().upper()

        # Normalize inverse notation (e.g. B <- CALLS - A is canonically mapped with direction)
        direction_tag = "INV" if hop.is_inverse else "FWD"

        return f"[{src_norm}]--{canon_rel.value}:{direction_tag}-->[{tgt_norm}]@{temp_norm}"

    @classmethod
    def generate_route_canonical_key(cls, route: ReasoningRoute) -> str:
        """
        Constructs a complete deterministic canonical key for a reasoning route.
        Includes the route's perspective archetype to guarantee that distinct
        reasoning modes (e.g. STRUCTURAL vs BEHAVIORAL_CALLGRAPH) are preserved.
        """
        hop_keys = [cls.generate_hop_canonical_key(h) for h in route.hops]
        return f"{route.perspective.value}::" + "==>".join(hop_keys)

    @classmethod
    def deduplicate(
        cls,
        routes: list[ReasoningRoute],
    ) -> list[ReasoningRoute]:
        """
        Deduplicates candidate reasoning routes:
        - Computes canonical keys for all candidates.
        - When duplicate canonical keys are found, retains the lowest-cost variant.
        - Preserves diverse perspectives (e.g. STRUCTURAL, BEHAVIORAL, TEMPORAL).
        - Returns a deduplicated list sorted deterministically by (estimated_cost, canonical_key).
        """
        if not routes:
            return []

        # Map each canonical key to the best (lowest-cost) route
        deduped_map: dict[str, ReasoningRoute] = {}

        for route in routes:
            key = route.canonical_key or cls.generate_route_canonical_key(route)
            # Ensure route has canonical_key set
            route.canonical_key = key

            if key not in deduped_map:
                deduped_map[key] = route
            else:
                existing = deduped_map[key]
                # Keep strictly lower cost; on exact tie keep first or lexicographically stable
                if route.estimated_cost < existing.estimated_cost:
                    deduped_map[key] = route
                elif route.estimated_cost == existing.estimated_cost:
                    # Deterministic tie-break on route_id
                    if route.route_id < existing.route_id:
                        deduped_map[key] = route

        # Deterministic sort: estimated_cost ascending, canonical_key ascending
        result = list(deduped_map.values())
        result.sort(key=lambda r: (r.estimated_cost, r.canonical_key))
        return result
