"""
Unit Tests for EvoReasoner Multi-Route Query Planner & Route Cost Estimator (T2.4 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Covers:
1. Route generation for each of the 7 supported temporal intents.
2. Query-conditioned relation selection.
3. Alternative route generation across distinct perspectives.
4. Hop-count cost calculation and monotonicity.
5. Branching-factor cost calculation and exclusivity derivation.
6. Temporal-distance cost calculation.
7. Conservative handling of missing and unknown cost inputs.
8. Deterministic route ranking and stable tie-breaking.
9. Top-N route limits enforcement.
10. Maximum-hop enforcement.
11. Semantic deduplication.
12. Preservation of meaningfully distinct routes despite identical costs.
13. Safe handling of empty, whitespace, and ambiguous/contradictory queries.
14. Compatibility with existing MemoTime and EvoKG interfaces.
"""

from apps.api.src.schemas.code_atom import PropertyExclusivity, RelationType
from apps.api.src.schemas.evoreasoner import (
    EvoPlannerConfig,
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
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.evoreasoner.cost_estimator import RouteCostEstimator
from apps.api.src.services.evoreasoner.deduplicator import RouteDeduplicator
from apps.api.src.services.evoreasoner.planner import EvoRoutePlanner

# =========================================================================
# 1. Route Generation for Each Supported Temporal Intent
# =========================================================================

def test_1_route_generation_all_temporal_intents():
    """Verify that distinct query plans with valid hops are generated for all 7 temporal intents."""
    intents = [
        (TemporalIntentType.CURRENT, "How does AuthService validate tokens currently?"),
        (TemporalIntentType.HISTORICAL, "How did AuthService handle tokens historically before the refactor?"),
        (TemporalIntentType.BEFORE, "What was the implementation of AuthService before commit a1b2c3d?"),
        (TemporalIntentType.AFTER, "How does AuthService behave after commit e4f5a6b?"),
        (TemporalIntentType.INTERVAL, "What was the behavior of AuthService between 2026-01-01 and 2026-06-01?"),
        (TemporalIntentType.DIFF, "What changed in AuthService in commit 7c8d9e0?"),
        (TemporalIntentType.EVOLUTION, "How did AuthService evolve over time across releases?"),
    ]

    for intent_type, q_text in intents:
        plan = EvoRoutePlanner.plan_routes(q_text)
        assert plan.query_text == q_text
        assert plan.temporal_intent == intent_type
        assert len(plan.selected_routes) > 0, f"Failed to generate routes for intent {intent_type}"

        # Verify every route has valid hops and proper constraints
        for route in plan.selected_routes:
            assert len(route.hops) >= 1
            assert route.estimated_cost > 0.0
            assert route.canonical_key != ""
            for hop in route.hops:
                assert hop.source_entity != ""
                assert hop.target_entity != ""
                assert isinstance(hop.canonical_relation, RelationType)


# =========================================================================
# 2. Query-Conditioned Relation Selection
# =========================================================================

def test_2_query_conditioned_relation_selection():
    """Verify that relation keywords directly influence relation selection and ranking."""
    # A. Invocation / Call queries
    call_query = "Which functions does PaymentService call?"
    plan_call = EvoRoutePlanner.plan_routes(call_query)
    call_relations = [h.canonical_relation for r in plan_call.selected_routes for h in r.hops]
    assert RelationType.CALLS in call_relations

    # B. Module Import queries
    import_query = "What modules does DatabaseClient import or require?"
    plan_import = EvoRoutePlanner.plan_routes(import_query)
    import_relations = [h.canonical_relation for r in plan_import.selected_routes for h in r.hops]
    assert (RelationType.IMPORTS in import_relations) or (RelationType.MODULE_LOCATION in import_relations)

    # C. Multi-entity relationship query biased by 'call'
    multi_call = "Does OrderController invoke BillingService?"
    plan_multi = EvoRoutePlanner.plan_routes(multi_call)
    assert any(h.canonical_relation == RelationType.CALLS for r in plan_multi.selected_routes for h in r.hops)


# =========================================================================
# 3. Alternative Route Generation
# =========================================================================

def test_3_alternative_route_generation_across_perspectives():
    """Verify that multiple complementary reasoning perspectives are generated for a single query."""
    query = "How is TokenValidator structured and what does it execute?"
    plan = EvoRoutePlanner.plan_routes(query)

    # Should generate multiple selected routes
    assert len(plan.selected_routes) >= 2
    perspectives = {r.perspective for r in plan.selected_routes}

    # Should cover at least two distinct perspectives (e.g. STRUCTURAL, BEHAVIORAL_CALLGRAPH)
    assert len(perspectives) >= 2
    assert (
        RoutePerspective.STRUCTURAL in perspectives
        or RoutePerspective.BEHAVIORAL_CALLGRAPH in perspectives
        or RoutePerspective.ARCHITECTURAL_DEPENDENCY in perspectives
    )


# =========================================================================
# 4. Hop-Count Cost Calculation & Monotonicity
# =========================================================================

def test_4_hop_count_cost_calculation():
    """Verify that estimated cost increases monotonically with hop count, holding other variables constant."""
    cfg = EvoPlannerConfig(w_hops=1.0, w_branch=0.0, w_entropy=0.0, w_temporal=0.0, w_complexity=0.0)

    hop1 = EvoRoutePlanner.create_hop(1, "A", RelationType.DEFINES, "B")
    hop2 = EvoRoutePlanner.create_hop(2, "B", RelationType.DEFINES, "C")
    hop3 = EvoRoutePlanner.create_hop(3, "C", RelationType.DEFINES, "D")

    cost1, b1 = RouteCostEstimator.estimate_cost([hop1], TemporalIntentType.CURRENT, cfg)
    cost2, b2 = RouteCostEstimator.estimate_cost([hop1, hop2], TemporalIntentType.CURRENT, cfg)
    cost3, b3 = RouteCostEstimator.estimate_cost([hop1, hop2, hop3], TemporalIntentType.CURRENT, cfg)

    assert b1.hop_count == 1
    assert b2.hop_count == 2
    assert b3.hop_count == 3
    assert cost1 < cost2 < cost3
    assert cost1 == 1.0
    assert cost2 == 2.0
    assert cost3 == 3.0


# =========================================================================
# 5. Branching-Factor Cost Calculation & Exclusivity Derivation
# =========================================================================

def test_5_branching_factor_cost_calculation():
    """Verify that exclusive relations (branching 1.0) incur strictly lower cost than high-fanout relations."""
    cfg = EvoPlannerConfig(w_hops=1.0, w_branch=1.0, w_entropy=0.0, w_temporal=0.0, w_complexity=0.0)

    # Exclusive hop: DEFINES (branching = 1.0)
    exclusive_hop = EvoRoutePlanner.create_hop(1, "Service", RelationType.DEFINES, "Method")
    cost_exclusive, b_excl = RouteCostEstimator.estimate_cost([exclusive_hop], TemporalIntentType.CURRENT, cfg)

    # Non-exclusive hop: CALLS (branching = 4.0)
    call_hop = EvoRoutePlanner.create_hop(1, "Service", RelationType.CALLS, "OtherService")
    cost_call, b_call = RouteCostEstimator.estimate_cost([call_hop], TemporalIntentType.CURRENT, cfg)

    # Non-exclusive broad: REFERENCES (branching = 5.0)
    ref_hop = EvoRoutePlanner.create_hop(1, "Service", RelationType.REFERENCES, "GlobalVar")
    cost_ref, b_ref = RouteCostEstimator.estimate_cost([ref_hop], TemporalIntentType.CURRENT, cfg)

    assert b_excl.branching_factor == 1.0
    assert b_call.branching_factor == 4.0
    assert b_ref.branching_factor == 5.0
    assert cost_exclusive < cost_call < cost_ref


# =========================================================================
# 6. Temporal-Distance Cost Calculation
# =========================================================================

def test_6_temporal_distance_cost_calculation():
    """Verify that hops matching the target temporal intent incur lower temporal cost than mismatched hops."""
    cfg = EvoPlannerConfig(w_hops=0.0, w_branch=0.0, w_entropy=0.0, w_temporal=1.0, w_complexity=0.0)

    # Hop with temporal constraint CURRENT for a CURRENT query
    hop_current = EvoRoutePlanner.create_hop(1, "A", RelationType.DEFINES, "B", temporal_constraint="CURRENT")
    cost_curr, b_curr = RouteCostEstimator.estimate_cost([hop_current], TemporalIntentType.CURRENT, cfg)

    # Hop with temporal constraint HISTORICAL for a CURRENT query
    hop_hist = EvoRoutePlanner.create_hop(1, "A", RelationType.DEFINES, "B", temporal_constraint="HISTORICAL")
    cost_mismatched, b_mismatched = RouteCostEstimator.estimate_cost([hop_hist], TemporalIntentType.CURRENT, cfg)

    assert b_curr.temporal_distance == 0.0
    assert cost_curr == 0.0
    assert b_mismatched.temporal_distance > 0.0
    assert cost_mismatched > cost_curr


# =========================================================================
# 7. Missing and Unknown Cost Inputs Handled Conservatively
# =========================================================================

def test_7_missing_and_unknown_cost_inputs():
    """Verify that unclassified/unknown predicates or empty properties default conservatively without crashing."""
    cfg = EvoPlannerConfig()

    unknown_hop = ReasoningHop(
        hop_index=1,
        source_entity="MysteryEntity",
        source_type="unknown",
        relation="UNRECOGNIZED_CUSTOM_PREDICATE_404",
        canonical_relation=CodeRelationTaxonomy.get_canonical_predicate("UNRECOGNIZED_CUSTOM_PREDICATE_404"),
        target_entity="AnotherUnknown",
        target_type="unknown",
        temporal_constraint="UNKNOWN_TIME",
        expected_branching=-1.0,  # Missing, triggers fallback
        expected_entropy=-1.0,  # Missing, triggers fallback
        temporal_distance=-1.0,  # Missing, triggers fallback
    )

    cost, breakdown = RouteCostEstimator.estimate_cost([unknown_hop], TemporalIntentType.CURRENT, cfg)

    # Must be non-negative, finite, and using conservative fallbacks
    assert cost > 0.0
    assert breakdown.branching_factor == 5.0  # FALLBACK_BRANCHING
    assert breakdown.branching_entropy == 1.5  # FALLBACK_ENTROPY
    assert breakdown.temporal_distance == 1.0  # FALLBACK_TEMPORAL_DISTANCE


# =========================================================================
# 8. Deterministic Route Ranking
# =========================================================================

def test_8_deterministic_route_ranking():
    """Verify that identical queries and configuration always generate identical route order and costs."""
    query = "How does IngestionWorker process code repositories?"

    plan1 = EvoRoutePlanner.plan_routes(query)
    plan2 = EvoRoutePlanner.plan_routes(query)

    assert len(plan1.selected_routes) == len(plan2.selected_routes)
    for r1, r2 in zip(plan1.selected_routes, plan2.selected_routes, strict=False):
        assert r1.route_id == r2.route_id
        assert r1.canonical_key == r2.canonical_key
        assert r1.estimated_cost == r2.estimated_cost
        assert r1.perspective == r2.perspective


# =========================================================================
# 9. Top-N Route Limits Enforcement
# =========================================================================

def test_9_top_n_route_limits():
    """Verify that the number of selected routes strictly adheres to max_selected_routes."""
    query = "Explain UserRepository methods and dependencies"

    cfg_1 = EvoPlannerConfig(max_selected_routes=1)
    plan_1 = EvoRoutePlanner.plan_routes(query, config=cfg_1)
    assert len(plan_1.selected_routes) == 1

    cfg_2 = EvoPlannerConfig(max_selected_routes=2)
    plan_2 = EvoRoutePlanner.plan_routes(query, config=cfg_2)
    assert len(plan_2.selected_routes) <= 2


# =========================================================================
# 10. Maximum-Hop Enforcement
# =========================================================================

def test_10_maximum_hop_enforcement():
    """Verify that no route exceeds the configured max_route_hops."""
    query = "Describe Controller dependencies and methods"
    cfg = EvoPlannerConfig(max_route_hops=2)

    plan = EvoRoutePlanner.plan_routes(query, config=cfg)
    assert len(plan.selected_routes) > 0
    for r in plan.selected_routes:
        assert len(r.hops) <= 2, f"Route {r.name} has {len(r.hops)} hops, exceeding max_route_hops=2"


# =========================================================================
# 11. Semantic Route Deduplication
# =========================================================================

def test_11_semantic_deduplication():
    """Verify that redundant routes with identical canonical trajectories are collapsed to the lower-cost variant."""
    h1 = EvoRoutePlanner.create_hop(1, "AuthService", RelationType.CALLS, "TokenManager")
    h2 = EvoRoutePlanner.create_hop(2, "TokenManager", RelationType.MUTATES, "Blacklist")

    r_expensive = ReasoningRoute(
        route_id="route_expensive",
        name="Expensive Variant",
        intent=TemporalIntentType.CURRENT,
        perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
        hops=[h1, h2],
        estimated_cost=5.5,
        cost_breakdown=RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.CURRENT)[1],
        canonical_key="",
    )

    r_cheaper = ReasoningRoute(
        route_id="route_cheaper",
        name="Cheaper Variant",
        intent=TemporalIntentType.CURRENT,
        perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH,
        hops=[h1, h2],
        estimated_cost=3.2,
        cost_breakdown=RouteCostEstimator.estimate_cost([h1, h2], TemporalIntentType.CURRENT)[1],
        canonical_key="",
    )

    deduped = RouteDeduplicator.deduplicate([r_expensive, r_cheaper])
    assert len(deduped) == 1
    assert deduped[0].route_id == "route_cheaper"
    assert deduped[0].estimated_cost == 3.2


# =========================================================================
# 12. Preservation of Meaningfully Distinct Routes
# =========================================================================

def test_12_preservation_of_meaningfully_distinct_routes():
    """Verify that different perspectives are preserved even if they share the same cost."""
    h_struct = EvoRoutePlanner.create_hop(1, "UserService", RelationType.DEFINES, "getUser")
    r_struct = ReasoningRoute(
        route_id="r_struct",
        name="Structural Definition",
        intent=TemporalIntentType.CURRENT,
        perspective=RoutePerspective.STRUCTURAL,
        hops=[h_struct],
        estimated_cost=2.0,
        cost_breakdown=RouteCostEstimator.estimate_cost([h_struct], TemporalIntentType.CURRENT)[1],
        canonical_key="",
    )

    h_arch = EvoRoutePlanner.create_hop(1, "UserService", RelationType.MODULE_LOCATION, "user.py")
    r_arch = ReasoningRoute(
        route_id="r_arch",
        name="Architectural Location",
        intent=TemporalIntentType.CURRENT,
        perspective=RoutePerspective.ARCHITECTURAL_DEPENDENCY,
        hops=[h_arch],
        estimated_cost=2.0,
        cost_breakdown=RouteCostEstimator.estimate_cost([h_arch], TemporalIntentType.CURRENT)[1],
        canonical_key="",
    )

    deduped = RouteDeduplicator.deduplicate([r_struct, r_arch])
    assert len(deduped) == 2
    perspectives = {r.perspective for r in deduped}
    assert RoutePerspective.STRUCTURAL in perspectives
    assert RoutePerspective.ARCHITECTURAL_DEPENDENCY in perspectives


# =========================================================================
# 13. Empty and Unsupported Queries
# =========================================================================

def test_13_empty_and_unsupported_queries():
    """Verify that empty, whitespace, and contradictory queries are handled safely without unhandled exceptions."""
    # A. Empty string
    plan_empty = EvoRoutePlanner.plan_routes("")
    assert plan_empty.selected_routes == []
    assert plan_empty.all_candidate_count == 0
    assert plan_empty.planning_diagnostics.get("reason") == "empty_query"

    # B. Whitespace
    plan_ws = EvoRoutePlanner.plan_routes("   \t\n  ")
    assert plan_ws.selected_routes == []

    # C. Ambiguous / contradictory temporal intent
    ambiguous_intent = StructuredTemporalIntent(
        intent_type=TemporalIntentType.AMBIGUOUS,
        is_temporal=True,
        is_ambiguous=True,
        ambiguity_reason="Contradictory time interval: 2026-05 after 2026-01",
    )
    plan_ambig = EvoRoutePlanner.plan_routes(
        "Invalid query with contradictory constraints", temporal_intent=ambiguous_intent
    )
    assert plan_ambig.selected_routes == []
    assert plan_ambig.temporal_intent == TemporalIntentType.AMBIGUOUS
    assert plan_ambig.planning_diagnostics.get("reason") == "ambiguous_or_contradictory_intent"


# =========================================================================
# 14. Compatibility with Existing MemoTime and EvoKG Interfaces
# =========================================================================

def test_14_compatibility_with_memotime_and_evokg():
    """Verify seamless interoperation with MemoTime StructuredTemporalIntent and EvoKG CodeRelationTaxonomy."""
    raw_query = "What was the previous superseded implementation of TokenValidator?"

    # 1. MemoTime compatibility: parse temporal intent directly
    temporal_intent = MemoTimeService.parse_temporal_intent(raw_query)
    assert isinstance(temporal_intent, StructuredTemporalIntent)
    assert temporal_intent.intent_type == TemporalIntentType.HISTORICAL

    # 2. QueryAnalyzer compatibility: analyze query
    analyzed = analyze_query(raw_query)

    # 3. Feed existing objects directly into EvoRoutePlanner
    plan = EvoRoutePlanner.plan_routes(
        query_text=raw_query,
        analyzed_query=analyzed,
        temporal_intent=temporal_intent,
    )
    assert plan.temporal_intent == TemporalIntentType.HISTORICAL
    assert len(plan.selected_routes) > 0

    # 4. EvoKG CodeRelationTaxonomy compatibility: every hop relation must be valid and classified
    for route in plan.selected_routes:
        for hop in route.hops:
            entry = CodeRelationTaxonomy.classify(hop.relation)
            assert entry.canonical_predicate == hop.canonical_relation
            assert isinstance(entry.exclusivity, PropertyExclusivity)
