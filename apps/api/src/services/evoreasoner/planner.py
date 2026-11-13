"""
EvoReasoner Multi-Route Query Planner (T2.4 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Builds a deterministic, bounded multi-route query planner that generates alternative
graph-reasoning routes across evolving code knowledge graph entities, conditions
them on temporal query intents and semantic relations, and bounds graph exploration.
"""

from __future__ import annotations

import logging

from apps.api.src.schemas.code_atom import PropertyExclusivity, RelationType
from apps.api.src.schemas.evoreasoner import (
    EvoPlannerConfig,
    MultiRoutePlan,
    ReasoningHop,
    ReasoningRoute,
    RoutePerspective,
)
from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy
from apps.api.src.services.context_engine.memotime import (
    MemoTimeService,
    StructuredTemporalIntent,
    TemporalIntentType,
)
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery, analyze_query
from apps.api.src.services.evoreasoner.cost_estimator import RouteCostEstimator
from apps.api.src.services.evoreasoner.deduplicator import RouteDeduplicator

logger = logging.getLogger(__name__)


class EvoRoutePlanner:
    """
    Deterministic multi-route query planner for EvoReasoner.
    """

    @classmethod
    def create_hop(
        cls,
        hop_index: int,
        source: str,
        relation: RelationType | str,
        target: str,
        *,
        source_type: str = "symbol",
        target_type: str = "symbol",
        temporal_constraint: str = "CURRENT",
        is_inverse: bool = False,
        expected_branching: float | None = None,
        expected_entropy: float | None = None,
        temporal_distance: float | None = None,
    ) -> ReasoningHop:
        """Helper to create a validated ReasoningHop with taxonomy-backed defaults."""
        canon = CodeRelationTaxonomy.get_canonical_predicate(relation)
        exclusivity = (
            PropertyExclusivity.EXCLUSIVE
            if CodeRelationTaxonomy.is_exclusive(canon)
            else PropertyExclusivity.NON_EXCLUSIVE
        )

        branching = (
            expected_branching
            if expected_branching is not None
            else RouteCostEstimator.get_relation_branching(canon)
        )
        entropy = (
            expected_entropy
            if expected_entropy is not None
            else RouteCostEstimator.get_relation_entropy(canon)
        )
        temp_dist = (
            temporal_distance
            if temporal_distance is not None
            else RouteCostEstimator.compute_temporal_distance(temporal_constraint, "CURRENT")
        )

        return ReasoningHop(
            hop_index=hop_index,
            source_entity=source,
            source_type=source_type,
            relation=relation,
            canonical_relation=canon,
            target_entity=target,
            target_type=target_type,
            temporal_constraint=temporal_constraint,
            is_inverse=is_inverse,
            expected_branching=branching,
            expected_entropy=entropy,
            temporal_distance=temp_dist,
            exclusivity=exclusivity,
        )

    @classmethod
    def plan_routes(
        cls,
        query_text: str,
        analyzed_query: AnalyzedQuery | None = None,
        temporal_intent: StructuredTemporalIntent | None = None,
        config: EvoPlannerConfig | None = None,
        seed_entities: list[str] | None = None,
    ) -> MultiRoutePlan:
        """
        Generates a bounded, deterministic multi-route plan for a Code Lane query.
        """
        cfg = config or EvoPlannerConfig()

        # 1. Edge case: Empty or whitespace query
        if not query_text or not query_text.strip():
            return MultiRoutePlan(
                query_text=query_text or "",
                temporal_intent=TemporalIntentType.CURRENT,
                selected_routes=[],
                all_candidate_count=0,
                deduplicated_count=0,
                is_bounded=True,
                planning_diagnostics={"reason": "empty_query", "message": "Query text is empty"},
            )

        # 2. Synchronize query analysis
        aq = analyzed_query or analyze_query(query_text)

        # 3. Synchronize temporal intent
        intent = temporal_intent
        if intent is None:
            if aq.structured_temporal_intent and isinstance(
                aq.structured_temporal_intent, StructuredTemporalIntent
            ):
                intent = aq.structured_temporal_intent
            else:
                intent = MemoTimeService.parse_temporal_intent(
                    query_text, target_symbols=aq.symbol_candidates
                )

        intent_type = intent.intent_type if intent else TemporalIntentType.CURRENT

        # Harmonize with query temporal cues if parser defaulted to CURRENT
        if intent_type == TemporalIntentType.CURRENT:
            q_lower_check = query_text.lower()
            if any(
                k in q_lower_check
                for k in (
                    "historical",
                    "historically",
                    "superseded",
                    "previous",
                    "legacy",
                    "deprecated",
                    "introduced",
                    "introduction",
                    "initial",
                    "initially",
                    "originally",
                    "original",
                )
            ):
                intent_type = TemporalIntentType.HISTORICAL
            elif any(k in q_lower_check for k in ("evolve", "evolved", "evolution", "across releases", "across commits", "timeline")):
                intent_type = TemporalIntentType.EVOLUTION
            elif any(k in q_lower_check for k in ("what changed in commit", "in commit")):
                intent_type = TemporalIntentType.DIFF

        # 4. Edge case: Ambiguous or contradictory query
        if intent and (intent.is_ambiguous or intent.is_contradictory or intent_type == TemporalIntentType.AMBIGUOUS):
            return MultiRoutePlan(
                query_text=query_text,
                temporal_intent=TemporalIntentType.AMBIGUOUS,
                selected_routes=[],
                all_candidate_count=0,
                deduplicated_count=0,
                is_bounded=True,
                planning_diagnostics={
                    "reason": "ambiguous_or_contradictory_intent",
                    "ambiguity_reason": intent.ambiguity_reason,
                    "contradiction_reason": intent.contradiction_reason,
                },
            )

        # 5. Extract entities and relation biases
        raw_symbols = aq.symbol_candidates + (intent.target_entities if intent else []) + (seed_entities or [])
        symbols = list(dict.fromkeys(raw_symbols))
        paths = list(dict.fromkeys(aq.path_candidates))

        # Query relation keyword conditioning
        q_lower = query_text.lower()
        rel_biases = cls._detect_relation_biases(q_lower)

        # 6. Generate candidate routes conditioned on intent and entities
        raw_candidates: list[ReasoningRoute] = []

        # If we have two specific entities mentioned, generate direct relation paths between them
        if len(symbols) >= 2:
            cls._generate_multi_entity_routes(
                symbols[0], symbols[1], intent_type, rel_biases, raw_candidates, cfg
            )

        # Primary entity focus
        primary_entity = symbols[0] if symbols else (paths[0] if paths else None)

        if primary_entity:
            cls._generate_intent_conditioned_routes(
                primary_entity, intent, intent_type, rel_biases, raw_candidates, cfg
            )
        else:
            # Fallback for concept/keyword queries lacking recognized symbol names
            cls._generate_unanchored_concept_routes(
                aq, intent_type, rel_biases, raw_candidates, cfg
            )

        # 7. Bound hops and estimate costs
        bounded_candidates: list[ReasoningRoute] = []
        for cand in raw_candidates:
            if len(bounded_candidates) >= cfg.max_candidate_routes:
                break

            # Strictly enforce maximum hops
            if len(cand.hops) > cfg.max_route_hops:
                cand.hops = cand.hops[: cfg.max_route_hops]

            # Recompute cost for the route
            cost, breakdown = RouteCostEstimator.estimate_cost(cand.hops, intent_type, cfg)
            cand.estimated_cost = cost
            cand.cost_breakdown = breakdown
            cand.canonical_key = RouteDeduplicator.generate_route_canonical_key(cand)
            bounded_candidates.append(cand)

        total_candidate_count = len(bounded_candidates)

        # 8. Deduplicate candidate routes
        deduped = RouteDeduplicator.deduplicate(bounded_candidates)
        deduped_count = len(deduped)

        # 9. Top-N Selection (deterministic: deduped is already sorted by cost ascending, canonical_key ascending)
        selected = deduped[: cfg.max_selected_routes]

        return MultiRoutePlan(
            query_text=query_text,
            temporal_intent=intent_type,
            selected_routes=selected,
            all_candidate_count=total_candidate_count,
            deduplicated_count=deduped_count,
            is_bounded=True,
            planning_diagnostics={
                "candidate_routes_generated": total_candidate_count,
                "deduplicated_routes": deduped_count,
                "selected_routes_count": len(selected),
                "intent_used": intent_type.value,
                "primary_entity": primary_entity,
                "relation_biases": [r.value for r in rel_biases],
            },
        )

    @classmethod
    def _detect_relation_biases(cls, q_lower: str) -> list[RelationType]:
        """Detects relation preferences directly expressed in query text."""
        biases: list[RelationType] = []
        if any(k in q_lower for k in ("call", "invoke", "invoking", "caller", "callee")):
            biases.append(RelationType.CALLS)
        if any(k in q_lower for k in ("import", "require", "module", "dependency", "package")):
            biases.append(RelationType.IMPORTS)
        if any(k in q_lower for k in ("inherit", "subclass", "base class", "extends", "implement")):
            biases.append(RelationType.INHERITS)
        if any(k in q_lower for k in ("signature", "parameter", "params", "argument")):
            biases.append(RelationType.HAS_SIGNATURE)
        if any(k in q_lower for k in ("return", "return type", "returns")):
            biases.append(RelationType.DEFINES_RETURN_TYPE)
        if any(k in q_lower for k in ("mutate", "modify", "state", "variable", "field")):
            biases.append(RelationType.MUTATES)
        if any(k in q_lower for k in ("raise", "throw", "error", "exception")):
            biases.append(RelationType.RAISES)
        if any(k in q_lower for k in ("config", "setting", "env", "configuration")):
            biases.append(RelationType.CONFIGURES)
        if any(k in q_lower for k in ("validat", "check", "verify", "guard")):
            biases.append(RelationType.VALIDATES)
        return biases

    @classmethod
    def _generate_multi_entity_routes(
        cls,
        entity_a: str,
        entity_b: str,
        intent_type: TemporalIntentType,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Generates direct relationship routes connecting two explicit entities."""
        temp_str = intent_type.value

        # Biased or default candidates
        relations = rel_biases if rel_biases else [
            RelationType.CALLS,
            RelationType.REFERENCES,
            RelationType.IMPORTS,
            RelationType.INHERITS,
        ]

        for idx, rel in enumerate(relations):
            if len(routes) >= cfg.max_candidate_routes:
                return

            persp = (
                RoutePerspective.BEHAVIORAL_CALLGRAPH
                if rel in (RelationType.CALLS, RelationType.MUTATES, RelationType.RAISES)
                else (
                    RoutePerspective.ARCHITECTURAL_DEPENDENCY
                    if rel == RelationType.IMPORTS
                    else RoutePerspective.STRUCTURAL
                )
            )

            hop = cls.create_hop(
                hop_index=1,
                source=entity_a,
                relation=rel,
                target=entity_b,
                temporal_constraint=temp_str,
            )

            cost, breakdown = RouteCostEstimator.estimate_cost([hop], intent_type, cfg)
            route = ReasoningRoute(
                route_id=f"multi_entity_{entity_a}_{rel.value}_{entity_b}_{idx}",
                name=f"{entity_a} {rel.value} {entity_b}",
                intent=intent_type,
                perspective=persp,
                hops=[hop],
                estimated_cost=cost,
                cost_breakdown=breakdown,
                canonical_key="",
            )
            routes.append(route)

    @classmethod
    def _generate_intent_conditioned_routes(
        cls,
        entity: str,
        intent: StructuredTemporalIntent | None,
        intent_type: TemporalIntentType,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Generates alternative reasoning routes conditioned on the primary entity and temporal intent."""
        # Reference commit or temporal anchor
        ref_commit = intent.reference_commits[0] if (intent and intent.reference_commits) else "HEAD"

        if intent_type == TemporalIntentType.CURRENT:
            cls._build_current_routes(entity, rel_biases, routes, cfg)
        elif intent_type == TemporalIntentType.HISTORICAL:
            cls._build_historical_routes(entity, ref_commit, rel_biases, routes, cfg)
        elif intent_type == TemporalIntentType.BEFORE:
            cls._build_before_routes(entity, ref_commit, rel_biases, routes, cfg)
        elif intent_type == TemporalIntentType.AFTER:
            cls._build_after_routes(entity, ref_commit, rel_biases, routes, cfg)
        elif intent_type == TemporalIntentType.INTERVAL:
            cls._build_interval_routes(entity, intent, rel_biases, routes, cfg)
        elif intent_type == TemporalIntentType.DIFF:
            cls._build_diff_routes(entity, ref_commit, rel_biases, routes, cfg)
        elif intent_type == TemporalIntentType.EVOLUTION:
            cls._build_evolution_routes(entity, intent, rel_biases, routes, cfg)
        else:
            cls._build_current_routes(entity, rel_biases, routes, cfg)

    @classmethod
    def _build_current_routes(
        cls,
        entity: str,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Constructs diverse alternative routes for CURRENT intent."""
        # 1. Structural Perspective: Definition -> Signature -> Return type
        h1 = cls.create_hop(1, entity, RelationType.DEFINES, f"{entity}::body", temporal_constraint="CURRENT")
        h2 = cls.create_hop(2, f"{entity}::body", RelationType.HAS_SIGNATURE, f"{entity}::signature", temporal_constraint="CURRENT")
        h3 = cls.create_hop(3, f"{entity}::body", RelationType.DEFINES_RETURN_TYPE, f"{entity}::return_type", temporal_constraint="CURRENT")

        cost1, b1 = RouteCostEstimator.estimate_cost([h1, h2, h3], TemporalIntentType.CURRENT, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"current_structural_{entity}",
                name=f"Current structural specification for {entity}",
                intent=TemporalIntentType.CURRENT,
                perspective=RoutePerspective.STRUCTURAL,
                hops=[h1, h2, h3],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
            )
        )

        # 2. Behavioral Callgraph Perspective: Outgoing invocation & mutation
        target_rel = RelationType.CALLS if (not rel_biases or RelationType.CALLS in rel_biases) else rel_biases[0]
        h_call1 = cls.create_hop(1, entity, target_rel, f"{entity}_callee", temporal_constraint="CURRENT")
        h_call2 = cls.create_hop(2, f"{entity}_callee", RelationType.MUTATES, f"{entity}_state", temporal_constraint="CURRENT")

        cost2, b2 = RouteCostEstimator.estimate_cost([h_call1, h_call2], TemporalIntentType.CURRENT, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"current_callgraph_{entity}",
                name=f"Current outgoing behavioral path for {entity}",
                intent=TemporalIntentType.CURRENT,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_call1, h_call2],
                estimated_cost=cost2,
                cost_breakdown=b2,
                canonical_key="",
            )
        )

        # 3. Behavioral Callgraph Perspective: Incoming caller context (inverse direction)
        h_caller = cls.create_hop(
            1, f"{entity}_caller", RelationType.CALLS, entity, is_inverse=True, temporal_constraint="CURRENT"
        )
        cost3, b3 = RouteCostEstimator.estimate_cost([h_caller], TemporalIntentType.CURRENT, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"current_caller_context_{entity}",
                name=f"Current caller context for {entity}",
                intent=TemporalIntentType.CURRENT,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_caller],
                estimated_cost=cost3,
                cost_breakdown=b3,
                canonical_key="",
            )
        )

        # 4. Architectural Dependency Perspective: Module location & imports
        h_mod1 = cls.create_hop(1, entity, RelationType.MODULE_LOCATION, f"{entity}_module.py", temporal_constraint="CURRENT")
        h_mod2 = cls.create_hop(2, f"{entity}_module.py", RelationType.IMPORTS, f"{entity}_pkg_dep", temporal_constraint="CURRENT")
        cost4, b4 = RouteCostEstimator.estimate_cost([h_mod1, h_mod2], TemporalIntentType.CURRENT, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"current_arch_dep_{entity}",
                name=f"Current architectural dependencies for {entity}",
                intent=TemporalIntentType.CURRENT,
                perspective=RoutePerspective.ARCHITECTURAL_DEPENDENCY,
                hops=[h_mod1, h_mod2],
                estimated_cost=cost4,
                cost_breakdown=b4,
                canonical_key="",
            )
        )

    @classmethod
    def _build_historical_routes(
        cls,
        entity: str,
        ref_commit: str,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Constructs diverse alternative routes for HISTORICAL intent."""
        # 1. Temporal Lineage: Supersession ancestry
        h1 = cls.create_hop(1, entity, "SUPERSEDED_BY", f"{entity}_legacy", temporal_constraint="HISTORICAL")
        h2 = cls.create_hop(2, f"{entity}_legacy", RelationType.DEFINES, f"{entity}_legacy::body", temporal_constraint="HISTORICAL")
        cost1, b1 = RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.HISTORICAL, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"historical_supersession_{entity}",
                name=f"Historical supersession trace for {entity}",
                intent=TemporalIntentType.HISTORICAL,
                perspective=RoutePerspective.TEMPORAL_LINEAGE,
                hops=[h1, h2],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
            )
        )

        # 2. Historical Behavioral Invocation
        h_call1 = cls.create_hop(1, f"{entity}_legacy", RelationType.CALLS, f"{entity}_legacy_callee", temporal_constraint="HISTORICAL")
        cost2, b2 = RouteCostEstimator.estimate_cost([h_call1], TemporalIntentType.HISTORICAL, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"historical_callgraph_{entity}",
                name=f"Historical behavioral invocation for {entity}",
                intent=TemporalIntentType.HISTORICAL,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_call1],
                estimated_cost=cost2,
                cost_breakdown=b2,
                canonical_key="",
            )
        )

        # 3. Signature Spec: Legacy signature verification
        h_sig1 = cls.create_hop(1, f"{entity}_legacy", RelationType.HAS_SIGNATURE, f"{entity}_legacy::sig", temporal_constraint="HISTORICAL")
        h_sig2 = cls.create_hop(2, f"{entity}_legacy", RelationType.DEFINES_RETURN_TYPE, f"{entity}_legacy::ret", temporal_constraint="HISTORICAL")
        cost3, b3 = RouteCostEstimator.estimate_cost([h_sig1, h_sig2], TemporalIntentType.HISTORICAL, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"historical_sig_{entity}",
                name=f"Historical signature specification for {entity}",
                intent=TemporalIntentType.HISTORICAL,
                perspective=RoutePerspective.SIGNATURE_SPEC,
                hops=[h_sig1, h_sig2],
                estimated_cost=cost3,
                cost_breakdown=b3,
                canonical_key="",
            )
        )

    @classmethod
    def _build_before_routes(
        cls,
        entity: str,
        ref_commit: str,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Constructs diverse alternative routes for BEFORE intent."""
        constr = f"BEFORE:{ref_commit}"

        # 1. Temporal Lineage: Pre-anchor supersession
        h1 = cls.create_hop(1, entity, "SUPERSEDED_BY", f"{entity}_pre_anchor", temporal_constraint=constr)
        h2 = cls.create_hop(2, f"{entity}_pre_anchor", RelationType.HAS_SIGNATURE, f"{entity}_pre_sig", temporal_constraint=constr)
        cost1, b1 = RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.BEFORE, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"before_supersession_{entity}",
                name=f"Pre-anchor state for {entity} before {ref_commit}",
                intent=TemporalIntentType.BEFORE,
                perspective=RoutePerspective.TEMPORAL_LINEAGE,
                hops=[h1, h2],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
            )
        )

        # 2. Behavioral Callgraph: Pre-anchor call trace
        h_call = cls.create_hop(1, f"{entity}_pre_anchor", RelationType.CALLS, f"{entity}_prior_target", temporal_constraint=constr)
        cost2, b2 = RouteCostEstimator.estimate_cost([h_call], TemporalIntentType.BEFORE, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"before_callgraph_{entity}",
                name=f"Pre-anchor call path for {entity}",
                intent=TemporalIntentType.BEFORE,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_call],
                estimated_cost=cost2,
                cost_breakdown=b2,
                canonical_key="",
            )
        )

    @classmethod
    def _build_after_routes(
        cls,
        entity: str,
        ref_commit: str,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Constructs diverse alternative routes for AFTER intent."""
        constr = f"AFTER:{ref_commit}"

        # 1. Temporal Lineage: Post-anchor succession
        h1 = cls.create_hop(1, f"{entity}_base", "SUPERSEDES", entity, temporal_constraint=constr)
        h2 = cls.create_hop(2, entity, RelationType.HAS_SIGNATURE, f"{entity}_post_sig", temporal_constraint=constr)
        cost1, b1 = RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.AFTER, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"after_succession_{entity}",
                name=f"Post-anchor succession for {entity} after {ref_commit}",
                intent=TemporalIntentType.AFTER,
                perspective=RoutePerspective.TEMPORAL_LINEAGE,
                hops=[h1, h2],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
            )
        )

        # 2. Behavioral Callgraph: Introduced callee invocations
        h_call = cls.create_hop(1, entity, RelationType.CALLS, f"{entity}_introduced_callee", temporal_constraint=constr)
        cost2, b2 = RouteCostEstimator.estimate_cost([h_call], TemporalIntentType.AFTER, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"after_callgraph_{entity}",
                name=f"Post-anchor introduced calls for {entity}",
                intent=TemporalIntentType.AFTER,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_call],
                estimated_cost=cost2,
                cost_breakdown=b2,
                canonical_key="",
            )
        )

    @classmethod
    def _build_interval_routes(
        cls,
        entity: str,
        intent: StructuredTemporalIntent | None,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Constructs diverse alternative routes for INTERVAL intent."""
        win_str = "BOUNDED_WINDOW"
        if intent and intent.constraints:
            c0 = intent.constraints[0]
            if c0.bound:
                win_str = f"{c0.bound.start or ''}..{c0.bound.end or ''}"

        constr = f"INTERVAL:{win_str}"

        # 1. Temporal Lineage: Mutations and assertions during interval
        h1 = cls.create_hop(1, entity, RelationType.MUTATES, f"{entity}_state_delta", temporal_constraint=constr)
        h2 = cls.create_hop(2, f"{entity}_state_delta", RelationType.VALIDATES, f"{entity}_assertion", temporal_constraint=constr)
        cost1, b1 = RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.INTERVAL, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"interval_mutations_{entity}",
                name=f"Interval mutation trajectory for {entity}",
                intent=TemporalIntentType.INTERVAL,
                perspective=RoutePerspective.TEMPORAL_LINEAGE,
                hops=[h1, h2],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
            )
        )

        # 2. Behavioral Callgraph: Interval active call graph
        h_call = cls.create_hop(1, entity, RelationType.CALLS, f"{entity}_interval_callee", temporal_constraint=constr)
        cost2, b2 = RouteCostEstimator.estimate_cost([h_call], TemporalIntentType.INTERVAL, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"interval_callgraph_{entity}",
                name=f"Interval active call paths for {entity}",
                intent=TemporalIntentType.INTERVAL,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_call],
                estimated_cost=cost2,
                cost_breakdown=b2,
                canonical_key="",
            )
        )

    @classmethod
    def _build_diff_routes(
        cls,
        entity: str,
        ref_commit: str,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Constructs diverse alternative routes for DIFF intent."""
        constr = f"DIFF:{ref_commit}"

        # 1. Temporal Lineage: Delta supersession
        h1 = cls.create_hop(1, f"{entity}_before", "SUPERSEDES", f"{entity}_after", temporal_constraint=constr)
        h2 = cls.create_hop(2, f"{entity}_after", RelationType.HAS_SIGNATURE, f"{entity}_delta_sig", temporal_constraint=constr)
        cost1, b1 = RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.DIFF, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"diff_supersession_{entity}",
                name=f"Delta supersession change for {entity} at {ref_commit}",
                intent=TemporalIntentType.DIFF,
                perspective=RoutePerspective.TEMPORAL_LINEAGE,
                hops=[h1, h2],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
            )
        )

        # 2. Behavioral Callgraph: Added / modified calls
        h_call = cls.create_hop(1, f"{entity}_after", RelationType.CALLS, f"{entity}_diff_callee", temporal_constraint=constr)
        cost2, b2 = RouteCostEstimator.estimate_cost([h_call], TemporalIntentType.DIFF, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"diff_callgraph_{entity}",
                name=f"Delta invocation changes for {entity}",
                intent=TemporalIntentType.DIFF,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_call],
                estimated_cost=cost2,
                cost_breakdown=b2,
                canonical_key="",
            )
        )

        # 3. Architectural Dependency: Delta import changes
        h_imp = cls.create_hop(1, f"{entity}_after", RelationType.IMPORTS, f"{entity}_diff_import", temporal_constraint=constr)
        cost3, b3 = RouteCostEstimator.estimate_cost([h_imp], TemporalIntentType.DIFF, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"diff_arch_dep_{entity}",
                name=f"Delta import modifications for {entity}",
                intent=TemporalIntentType.DIFF,
                perspective=RoutePerspective.ARCHITECTURAL_DEPENDENCY,
                hops=[h_imp],
                estimated_cost=cost3,
                cost_breakdown=b3,
                canonical_key="",
            )
        )

    @classmethod
    def _build_evolution_routes(
        cls,
        entity: str,
        intent: StructuredTemporalIntent | None,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Constructs diverse alternative routes for EVOLUTION intent."""
        # 1. Temporal Lineage: Multi-hop supersession progression chain
        h1 = cls.create_hop(1, f"{entity}_v0", "SUPERSEDES", f"{entity}_v1", temporal_constraint="EVOLUTION:step_1")
        h2 = cls.create_hop(2, f"{entity}_v1", "SUPERSEDES", f"{entity}_v2", temporal_constraint="EVOLUTION:step_2")
        cost1, b1 = RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.EVOLUTION, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"evolution_lineage_{entity}",
                name=f"Multi-step supersession progression for {entity}",
                intent=TemporalIntentType.EVOLUTION,
                perspective=RoutePerspective.TEMPORAL_LINEAGE,
                hops=[h1, h2],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
            )
        )

        # 2. Behavioral Callgraph: Evolutionary call-graph drift
        h_call1 = cls.create_hop(1, f"{entity}_v0", RelationType.CALLS, f"{entity}_callee_v0", temporal_constraint="EVOLUTION:v0")
        h_call2 = cls.create_hop(2, f"{entity}_v2", RelationType.CALLS, f"{entity}_callee_v2", temporal_constraint="EVOLUTION:v2")
        cost2, b2 = RouteCostEstimator.estimate_cost([h_call1, h_call2], TemporalIntentType.EVOLUTION, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"evolution_drift_{entity}",
                name=f"Evolutionary call-graph drift for {entity}",
                intent=TemporalIntentType.EVOLUTION,
                perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
                hops=[h_call1, h_call2],
                estimated_cost=cost2,
                cost_breakdown=b2,
                canonical_key="",
            )
        )

    @classmethod
    def _generate_unanchored_concept_routes(
        cls,
        aq: AnalyzedQuery,
        intent_type: TemporalIntentType,
        rel_biases: list[RelationType],
        routes: list[ReasoningRoute],
        cfg: EvoPlannerConfig,
    ) -> None:
        """Fallback for queries where no specific symbol or file was extracted."""
        concept_term = (
            aq.concept_keywords[0]
            if aq.concept_keywords
            else (aq.keywords[0] if aq.keywords else "app")
        )
        temp_str = intent_type.value

        h1 = cls.create_hop(1, f"module::{concept_term}", RelationType.DEFINES, f"symbol::{concept_term}", temporal_constraint=temp_str)
        cost1, b1 = RouteCostEstimator.estimate_cost([h1], intent_type, cfg)
        routes.append(
            ReasoningRoute(
                route_id=f"concept_entry_{concept_term}",
                name=f"Conceptual entry path for {concept_term}",
                intent=intent_type,
                perspective=RoutePerspective.STRUCTURAL,
                hops=[h1],
                estimated_cost=cost1,
                cost_breakdown=b1,
                canonical_key="",
                is_fallback=True,
            )
        )

    # Class-level alias for planning
    generate_multi_route_plan = plan_routes

