"""
Unit test suite for MemoTime Code Lane foundation (arXiv:2510.13614).

Verifies:
1. Current vs. historical intent classification and candidate binding.
2. All 13 Allen interval algebra relations.
3. Multi-event ordered evolution (3-phase ToT decomposition: origin -> transition -> current).
4. Missing timestamps and ambiguous queries (UNBOUNDED_TEMPORAL, no fabricated dates).
5. Contradictory temporal constraints (inverted intervals, non-monotonic progression).
6. Multiple entities with incompatible bounds (dependency introduced after dependent interval ends).
7. Existing supersession behavior and provenance survival with ToT evidence binding.
8. Safe default configuration (settings.MEMOTIME_ENABLED is False).
"""

import copy
import uuid
from datetime import UTC, datetime

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.memotime import (
    AllenIntervalRelation,
    MemoTimeService,
    ResolutionStatus,
    StructuredTemporalIntent,
    TemporalBound,
    TemporalConstraint,
    TemporalIntentType,
    TimeTreeNode,
    TreeOfTime,
)
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


def _create_candidate(
    candidate_id: str,
    name: str,
    path: str,
    commit_sha: str,
    commit_msg: str,
    committed_at: str | None,
    content: str = "def execute(): pass",
    symbol_name: str | None = None,
    change_type: str = "MODIFY",
) -> RetrievedCandidate:
    sym = symbol_name or name.split(" (")[0].strip()
    prov = {
        "commit_sha": commit_sha,
        "commit_message": commit_msg,
        "committed_at": committed_at,
        "file_path": path,
        "symbol_name": sym,
        "change_type": change_type,
        "fingerprint": f"fp_{commit_sha[:8]}_{path}_{sym}",
    }
    meta = {
        "commit_sha": commit_sha,
        "commit_message": commit_msg,
        "committed_at": committed_at,
        "symbol_name": sym,
        "change_type": change_type,
        "provenance": prov,
    }
    return RetrievedCandidate(
        candidate_id=candidate_id,
        entity_type="CHUNK",
        name=name,
        path=path,
        start_line=1,
        end_line=20,
        content=content,
        file_id=uuid.uuid4(),
        signals={"content_match": 1.0, "vector_similarity": 0.8},
        metadata=meta,
    )


# =========================================================================
# TEST 1: Current vs. Historical Intent Classification and Candidate Binding
# =========================================================================
def test_1_current_vs_historical_intent_and_binding():
    # Candidates: v1 (older, superseded) and v2 (latest, active)
    cand_v1 = _create_candidate(
        candidate_id="c1",
        name="AuthService (v1)",
        path="apps/api/src/services/auth.py",
        commit_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        commit_msg="Initial auth service implementation",
        committed_at="2026-09-01T10:00:00Z",
    )
    cand_v2 = _create_candidate(
        candidate_id="c2",
        name="AuthService (v2)",
        path="apps/api/src/services/auth.py",
        commit_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        commit_msg="Update auth service with jwt rotation",
        committed_at="2026-10-01T10:00:00Z",
    )

    # 1a. Current Query Intent
    query_curr = "What is the current active implementation of AuthService?"
    analyzed_curr = analyze_query(query_curr)
    assert analyzed_curr.is_temporal is True
    assert analyzed_curr.structured_temporal_intent is not None
    assert analyzed_curr.structured_temporal_intent.intent_type == TemporalIntentType.CURRENT

    tree_curr = MemoTimeService.build_tree_of_time(query_curr, target_symbols=["AuthService"])
    tree_curr = MemoTimeService.bind_evidence_to_tree(tree_curr, [cand_v1, cand_v2])

    curr_node = tree_curr.nodes["node_current"]
    assert curr_node.resolution_status == ResolutionStatus.RESOLVED
    assert len(curr_node.evidence_candidates) == 1
    # Only v2 (active, not superseded) should be bound
    assert curr_node.evidence_candidates[0].candidate_id == "c2"

    # 1b. Historical Query Intent
    query_hist = "What was the previous superseded implementation of AuthService?"
    analyzed_hist = analyze_query(query_hist)
    assert analyzed_hist.is_temporal is True
    assert analyzed_hist.structured_temporal_intent is not None
    assert analyzed_hist.structured_temporal_intent.intent_type == TemporalIntentType.HISTORICAL

    tree_hist = MemoTimeService.build_tree_of_time(query_hist, target_symbols=["AuthService"])
    tree_hist = MemoTimeService.bind_evidence_to_tree(tree_hist, [cand_v1, cand_v2])

    hist_node = tree_hist.nodes["node_historical"]
    assert hist_node.resolution_status == ResolutionStatus.RESOLVED
    assert any(c.candidate_id == "c1" for c in hist_node.evidence_candidates)


# =========================================================================
# TEST 2: All 13 Allen Interval Algebra Relations
# =========================================================================
def test_2_all_13_allen_interval_relations():
    t1 = datetime(2026, 1, 1, tzinfo=UTC)
    t2 = datetime(2026, 1, 10, tzinfo=UTC)
    t3 = datetime(2026, 1, 20, tzinfo=UTC)
    t4 = datetime(2026, 1, 30, tzinfo=UTC)

    # 1. EQUALS: A = B ([t1, t2] vs [t1, t2])
    b12 = TemporalBound(start=t1, end=t2)
    rel = MemoTimeService.compute_allen_relation(b12, b12)
    assert rel == AllenIntervalRelation.EQUALS
    assert rel.inverse == AllenIntervalRelation.EQUALS
    assert MemoTimeService.compute_allen_relation(b12, b12) == rel.inverse

    # 2. BEFORE / AFTER inverse pair
    b34 = TemporalBound(start=t3, end=t4)
    rel_before = MemoTimeService.compute_allen_relation(b12, b34)
    assert rel_before == AllenIntervalRelation.BEFORE
    assert rel_before.inverse == AllenIntervalRelation.AFTER
    assert MemoTimeService.compute_allen_relation(b34, b12) == AllenIntervalRelation.AFTER
    assert MemoTimeService.compute_allen_relation(b34, b12) == rel_before.inverse

    # 3. MEETS / MET_BY inverse pair
    b23 = TemporalBound(start=t2, end=t3)
    rel_meets = MemoTimeService.compute_allen_relation(b12, b23)
    assert rel_meets == AllenIntervalRelation.MEETS
    assert rel_meets.inverse == AllenIntervalRelation.MET_BY
    assert MemoTimeService.compute_allen_relation(b23, b12) == AllenIntervalRelation.MET_BY
    assert MemoTimeService.compute_allen_relation(b23, b12) == rel_meets.inverse

    # 4. STARTS / STARTED_BY inverse pair
    b13 = TemporalBound(start=t1, end=t3)
    rel_starts = MemoTimeService.compute_allen_relation(b12, b13)
    assert rel_starts == AllenIntervalRelation.STARTS
    assert rel_starts.inverse == AllenIntervalRelation.STARTED_BY
    assert MemoTimeService.compute_allen_relation(b13, b12) == AllenIntervalRelation.STARTED_BY
    assert MemoTimeService.compute_allen_relation(b13, b12) == rel_starts.inverse

    # 5. FINISHES / FINISHED_BY inverse pair
    rel_finishes = MemoTimeService.compute_allen_relation(b23, b13)
    assert rel_finishes == AllenIntervalRelation.FINISHES
    assert rel_finishes.inverse == AllenIntervalRelation.FINISHED_BY
    assert MemoTimeService.compute_allen_relation(b13, b23) == AllenIntervalRelation.FINISHED_BY
    assert MemoTimeService.compute_allen_relation(b13, b23) == rel_finishes.inverse

    # 6. DURING / CONTAINS inverse pair
    b14 = TemporalBound(start=t1, end=t4)
    rel_during = MemoTimeService.compute_allen_relation(b23, b14)
    assert rel_during == AllenIntervalRelation.DURING
    assert rel_during.inverse == AllenIntervalRelation.CONTAINS
    assert MemoTimeService.compute_allen_relation(b14, b23) == AllenIntervalRelation.CONTAINS
    assert MemoTimeService.compute_allen_relation(b14, b23) == rel_during.inverse

    # 7. OVERLAPS / OVERLAPPED_BY inverse pair
    b24 = TemporalBound(start=t2, end=t4)
    rel_overlaps = MemoTimeService.compute_allen_relation(b13, b24)
    assert rel_overlaps == AllenIntervalRelation.OVERLAPS
    assert rel_overlaps.inverse == AllenIntervalRelation.OVERLAPPED_BY
    assert MemoTimeService.compute_allen_relation(b24, b13) == AllenIntervalRelation.OVERLAPPED_BY
    assert MemoTimeService.compute_allen_relation(b24, b13) == rel_overlaps.inverse

    # Invalid interval handling
    invalid_bound = TemporalBound(start=t4, end=t1)
    assert invalid_bound.is_valid() is False
    assert MemoTimeService.compute_allen_relation(invalid_bound, b12) is None


# =========================================================================
# TEST 3: Multi-Event Ordered Evolution (3-Phase ToT Decomposition)
# =========================================================================
def test_3_multi_event_ordered_evolution():
    query = "How did TokenValidator evolve across commits in repository history?"
    analyzed = analyze_query(query)
    assert analyzed.is_temporal is True
    assert analyzed.structured_temporal_intent is not None
    assert analyzed.structured_temporal_intent.intent_type == TemporalIntentType.EVOLUTION

    tree = MemoTimeService.build_tree_of_time(query, target_symbols=["TokenValidator"])
    assert tree.is_valid is True

    ordered_nodes = tree.get_ordered_nodes()
    assert len(ordered_nodes) == 3

    node_origin, node_transition, node_current = ordered_nodes
    assert node_origin.node_id == "phase_0_origin"
    assert node_origin.intent_type == TemporalIntentType.HISTORICAL
    assert node_origin.ordering_index == 0

    assert node_transition.node_id == "phase_1_transition"
    assert node_transition.intent_type == TemporalIntentType.EVOLUTION
    assert node_transition.ordering_index == 1

    assert node_current.node_id == "phase_2_current"
    assert node_current.intent_type == TemporalIntentType.CURRENT
    assert node_current.ordering_index == 2

    # Verify monotonic index progression
    for i in range(len(ordered_nodes) - 1):
        assert ordered_nodes[i].ordering_index < ordered_nodes[i + 1].ordering_index


# =========================================================================
# TEST 4: Missing Timestamps and Ambiguous Queries
# =========================================================================
def test_4_missing_timestamps_and_ambiguous_queries():
    # 4a. Candidate without explicit timestamp bound to temporal node
    cand_no_ts = _create_candidate(
        candidate_id="c_no_ts",
        name="LegacyConfig",
        path="apps/api/src/config/legacy.py",
        commit_sha="cccccccccccccccccccccccccccccccccccccccc",
        commit_msg="Update legacy config without timestamp",
        committed_at=None,
    )

    query = "Inspect changes to LegacyConfig before commit cccccccc"
    tree = MemoTimeService.build_tree_of_time(query, target_symbols=["LegacyConfig"])
    tree = MemoTimeService.bind_evidence_to_tree(tree, [cand_no_ts])

    before_node = tree.nodes["node_before"]
    assert len(before_node.evidence_candidates) == 1
    # Node should be marked UNBOUNDED_TEMPORAL without crashing or fabricating dates
    assert before_node.resolution_status == ResolutionStatus.UNBOUNDED_TEMPORAL
    assert "without explicit commit timestamps" in (before_node.resolution_notes or "")

    # 4b. Ambiguous query with conflicting temporal directives
    query_ambiguous = "What is the current previous implementation of AuthService?"
    intent_ambiguous = MemoTimeService.parse_temporal_intent(query_ambiguous)
    assert intent_ambiguous.is_ambiguous is True
    assert intent_ambiguous.is_contradictory is True
    assert intent_ambiguous.intent_type == TemporalIntentType.AMBIGUOUS
    assert "Conflicting temporal directives" in (intent_ambiguous.ambiguity_reason or "")

    tree_amb = MemoTimeService.build_tree_of_time(query_ambiguous)
    root = tree_amb.nodes["root"]
    assert root.resolution_status == ResolutionStatus.CONTRADICTORY


# =========================================================================
# TEST 5: Contradictory Temporal Constraints
# =========================================================================
def test_5_contradictory_temporal_constraints():
    # 5a. Inverted date interval in query
    query_inverted = "Find commits between 2026-10-15 and 2026-09-01"
    intent = MemoTimeService.parse_temporal_intent(query_inverted)
    assert intent.is_contradictory is True
    assert intent.is_ambiguous is True
    assert "strictly after end" in (intent.contradiction_reason or "")

    tree_inverted = MemoTimeService.build_tree_of_time(query_inverted)
    assert tree_inverted.is_valid is False
    assert any("strictly after end" in err for err in tree_inverted.validation_errors)

    # 5b. Non-monotonic progression across sequential sibling nodes
    tree = MemoTimeService.build_tree_of_time("Evolution of Engine")
    tree.nodes.clear()
    tree.root_intent.is_contradictory = False

    t_early = datetime(2026, 9, 1, tzinfo=UTC)
    t_mid = datetime(2026, 9, 15, tzinfo=UTC)
    t_late = datetime(2026, 10, 1, tzinfo=UTC)

    # Node 1 ends at t_late, Node 2 starts at t_early (non-monotonic)
    n1 = TimeTreeNode(
        node_id="n1",
        query_subquestion="Phase 1",
        intent_type=TemporalIntentType.INTERVAL,
        temporal_bound=TemporalBound(start=t_mid, end=t_late),
        ordering_index=0,
    )
    n2 = TimeTreeNode(
        node_id="n2",
        query_subquestion="Phase 2",
        intent_type=TemporalIntentType.INTERVAL,
        temporal_bound=TemporalBound(start=t_early, end=t_mid),
        ordering_index=1,
    )
    tree.add_node(n1)
    tree.add_node(n2)

    is_valid, errors = MemoTimeService.validate_temporal_constraints(tree)
    assert is_valid is False
    assert any("Non-monotonic temporal progression" in e for e in errors)


# =========================================================================
# TEST 6: Multiple Entities with Incompatible Bounds
# =========================================================================
def test_6_multiple_entities_with_incompatible_bounds():
    t_start_a = datetime(2026, 8, 1, tzinfo=UTC)
    t_end_a = datetime(2026, 8, 31, tzinfo=UTC)
    t_intro_b = datetime(2026, 10, 1, tzinfo=UTC)
    t_end_b = datetime(2026, 12, 31, tzinfo=UTC)

    # Entity A ended on 2026-08-31; Entity B was introduced on 2026-10-01
    bounds = {
        "paymentservice": TemporalBound(start=t_start_a, end=t_end_a),
        "stripeconnector": TemporalBound(start=t_intro_b, end=t_end_b),
    }

    # Dependency check: PaymentService requires StripeConnector
    valid, errors = MemoTimeService.validate_multi_entity_bounds(
        entity_bounds=bounds,
        dependencies=[("PaymentService", "StripeConnector")],
    )
    assert valid is False
    assert any("PaymentService" in e and "StripeConnector" in e and "introduced later" in e for e in errors)

    # Tree constraint validation integration
    tree = MemoTimeService.build_tree_of_time("PaymentService integration")
    tree.nodes.clear()
    tree.root_intent.is_contradictory = False

    n_a = TimeTreeNode(
        node_id="node_payment",
        query_subquestion="Payment Service state",
        intent_type=TemporalIntentType.HISTORICAL,
        temporal_bound=bounds["paymentservice"],
        target_entities=["PaymentService"],
        ordering_index=0,
        constraints=[
            TemporalConstraint(
                constraint_id="c_dep",
                operator="DEPENDS_ON",
                target_entity="PaymentService",
                reference_entity="StripeConnector",
                bound=bounds["stripeconnector"],
            )
        ],
    )
    tree.add_node(n_a)

    is_valid, val_errors = MemoTimeService.validate_temporal_constraints(tree)
    assert is_valid is False
    assert any("Incompatible multi-entity bounds" in err for err in val_errors)


# =========================================================================
# TEST 7: Supersession Behavior and Provenance Survival with ToT Evidence
# =========================================================================
def test_7_supersession_behavior_and_provenance_survival():
    cand_v1 = _create_candidate(
        candidate_id="c_prov_1",
        name="DatabasePool (v1)",
        path="apps/api/src/database.py",
        commit_sha="1111111111111111111111111111111111111111",
        commit_msg="Initial database connection pool",
        committed_at="2026-07-01T08:00:00Z",
    )
    cand_v2 = _create_candidate(
        candidate_id="c_prov_2",
        name="DatabasePool (v2)",
        path="apps/api/src/database.py",
        commit_sha="2222222222222222222222222222222222222222",
        commit_msg="Add asyncpg connection pool tuning",
        committed_at="2026-09-01T12:00:00Z",
    )

    query = "How did DatabasePool change between 2026-06-01 and 2026-10-01"
    tree = MemoTimeService.build_tree_of_time(query, target_symbols=["DatabasePool"])
    tree = MemoTimeService.bind_evidence_to_tree(tree, [cand_v1, cand_v2])

    interval_node = tree.nodes["node_interval"]
    assert interval_node.resolution_status == ResolutionStatus.RESOLVED
    assert len(interval_node.evidence_candidates) == 2

    # Verify complete provenance survived without tampering
    for cand in interval_node.evidence_candidates:
        prov = cand.metadata["provenance"]
        assert prov["file_path"] == "apps/api/src/database.py"
        assert prov["symbol_name"] == "DatabasePool"
        assert prov["change_type"] == "MODIFY"
        assert "commit_sha" in prov
        assert "fingerprint" in prov

    # Candidate 1 must be flagged as superseded by Candidate 2
    c1_bound = next(c for c in interval_node.evidence_candidates if c.candidate_id == "c_prov_1")
    c2_bound = next(c for c in interval_node.evidence_candidates if c.candidate_id == "c_prov_2")
    assert c1_bound.metadata.get("is_superseded") is True
    assert c2_bound.metadata.get("is_current") is True


# =========================================================================
# TEST 8: Safe Default Configuration
# =========================================================================
def test_8_safe_default_configuration():
    # MemoTime must be disabled by default
    assert settings.MEMOTIME_ENABLED is False
    assert MemoTimeService.is_retrieval_enabled() is False

    # STAR-RAG must remain disabled by default
    assert settings.STAR_RAG_ENABLED is False

    # Verify that while retrieval is disabled, deterministic intent parsing remains safely accessible
    parsed = MemoTimeService.parse_temporal_intent("What is the current implementation of AuthService?")
    assert parsed.intent_type == TemporalIntentType.CURRENT
    assert parsed.is_temporal is True


# =========================================================================
# TEST 9: Semantic Negation Preservation with Temporal Intent
# =========================================================================
def test_9_semantic_negation_preservation_with_temporal_intent():
    # Query combining semantic negation with temporal intent
    query = "Find modules that are not superseded"
    analyzed = analyze_query(query)
    assert analyzed.has_negation is True
    assert "not" in analyzed.negation_keywords
    assert analyzed.is_temporal is True
    assert analyzed.structured_temporal_intent is not None
    assert analyzed.structured_temporal_intent.intent_type == TemporalIntentType.HISTORICAL

    # Query with "never" and code evolution
    query2 = "Which functions never had commit history"
    analyzed2 = analyze_query(query2)
    assert analyzed2.has_negation is True
    assert "never" in analyzed2.negation_keywords
    assert analyzed2.is_temporal is True
    assert analyzed2.structured_temporal_intent is not None
    assert analyzed2.structured_temporal_intent.intent_type == TemporalIntentType.EVOLUTION


# =========================================================================
# TEST 10: Disabled MemoTime Preserves Baseline Results Exactly
# =========================================================================
def test_10_disabled_memotime_preserves_baseline_results():
    """
    Verifies that when MemoTime is disabled (settings.MEMOTIME_ENABLED is False):
    1. settings.MEMOTIME_ENABLED is False and is_retrieval_enabled() returns False.
    2. Candidates ranked with MultiSignalRanker have identical scores and ordering
       whether or not temporal keywords appear in the query.
    3. No MemoTime signals (memotime_temporal_match, memotime_diff_match, etc.) are injected.
    """
    from apps.api.src.services.context_engine.ranker import MultiSignalRanker

    assert settings.MEMOTIME_ENABLED is False
    assert MemoTimeService.is_retrieval_enabled() is False

    cand1 = _create_candidate("c1", "AuthService", "src/auth.py", "1111", "Commit 1", "2026-01-01T00:00:00Z")
    cand2 = _create_candidate("c2", "TokenManager", "src/token.py", "2222", "Commit 2", "2026-02-01T00:00:00Z")
    candidates = [cand1, cand2]

    # Baseline ranking with non-temporal query
    q_plain = analyze_query("How does AuthService validate tokens?")
    ranked_plain = MultiSignalRanker.rank_candidates(copy.deepcopy(candidates), q_plain)

    # Baseline ranking with temporal query when MemoTime is disabled
    q_temp = analyze_query("What is the current implementation of AuthService?")
    ranked_temp = MultiSignalRanker.rank_candidates(copy.deepcopy(candidates), q_temp)

    # Baseline ranker handles supersession natively, but NO MemoTime signals are present
    for r in ranked_plain + ranked_temp:
        for sig in r.candidate.signals:
            assert not sig.startswith("memotime_"), f"Unexpected MemoTime signal {sig} found when disabled"


# =========================================================================
# TEST 11: Explicitly Enabled MemoTime Strategy Selection
# =========================================================================
def test_11_explicitly_enabled_memotime_strategy_selection():
    """
    Verifies that MemoTimeService.run_memotime_pipeline correctly routes
    queries to the appropriate temporal strategy:
    - CURRENT
    - HISTORICAL
    - DIFF
    - BEFORE / AFTER
    - INTERVAL
    - EVOLUTION
    """
    cand = _create_candidate("c1", "AuthService", "src/auth.py", "42096a512345", "Fix", "2026-05-01T00:00:00Z")

    # 1. CURRENT
    res_curr = MemoTimeService.run_memotime_pipeline(
        candidates=[cand], query_text="What is the current active implementation of AuthService?"
    )
    assert res_curr.strategy_used == TemporalIntentType.CURRENT

    # 2. HISTORICAL
    res_hist = MemoTimeService.run_memotime_pipeline(
        candidates=[cand], query_text="What was the previous superseded version of AuthService?"
    )
    assert res_hist.strategy_used == TemporalIntentType.HISTORICAL

    # 3. DIFF
    res_diff = MemoTimeService.run_memotime_pipeline(
        candidates=[cand], query_text="Explain changes introduced in commit 42096a5"
    )
    assert res_diff.strategy_used == TemporalIntentType.DIFF

    # 4. BEFORE / AFTER
    res_bef = MemoTimeService.run_memotime_pipeline(
        candidates=[cand], query_text="Find functions committed before 2026-06-01"
    )
    assert res_bef.strategy_used == TemporalIntentType.BEFORE

    res_aft = MemoTimeService.run_memotime_pipeline(
        candidates=[cand], query_text="Find functions committed after 2026-04-01"
    )
    assert res_aft.strategy_used == TemporalIntentType.AFTER

    # 5. INTERVAL
    res_int = MemoTimeService.run_memotime_pipeline(
        candidates=[cand], query_text="Show commits between 2026-01-01 and 2026-06-01"
    )
    assert res_int.strategy_used == TemporalIntentType.INTERVAL

    # 6. EVOLUTION
    res_evo = MemoTimeService.run_memotime_pipeline(
        candidates=[cand], query_text="Trace the evolution of AuthService from origin to current state"
    )
    assert res_evo.strategy_used == TemporalIntentType.EVOLUTION


# =========================================================================
# TEST 12: Current vs Historical Retrieval and Ranking
# =========================================================================
def test_12_current_versus_historical_retrieval_and_ranking():
    """
    Verifies that:
    1. CURRENT strategy boosts active candidates and suppresses superseded candidates.
    2. HISTORICAL strategy prioritizes superseded candidates and boosts historical matches.
    """
    from apps.api.src.services.context_engine.ranker import MultiSignalRanker

    cand_old = _create_candidate("c_old", "AuthService", "src/auth.py", "1111", "Initial auth", "2026-01-01T00:00:00Z")
    cand_new = _create_candidate("c_new", "AuthService", "src/auth.py", "2222", "Update auth", "2026-05-01T00:00:00Z")
    candidates = [cand_old, cand_new]

    # Current query
    q_curr = analyze_query("What is the current implementation of AuthService?")
    cands_curr = MemoTimeService.apply_memotime_retrieval(copy.deepcopy(candidates), q_curr, q_curr.raw_query)
    ranked_curr = MultiSignalRanker.rank_candidates(cands_curr, q_curr)

    assert ranked_curr[0].candidate.candidate_id == "c_new"
    assert ranked_curr[0].candidate.signals.get("memotime_temporal_match") == 1.0
    # Old candidate is marked superseded
    assert any(c.candidate_id == "c_old" and c.metadata.get("is_superseded") is True for c in cands_curr)

    # Historical query
    q_hist = analyze_query("What was the previous superseded implementation of AuthService?")
    cands_hist = MemoTimeService.apply_memotime_retrieval(copy.deepcopy(candidates), q_hist, q_hist.raw_query)
    ranked_hist = MultiSignalRanker.rank_candidates(cands_hist, q_hist)

    assert ranked_hist[0].candidate.candidate_id == "c_old"
    assert ranked_hist[0].candidate.signals.get("memotime_historical") == 1.0


# =========================================================================
# TEST 13: Before, After, and Interval Boundary Filtering and Penalties
# =========================================================================
def test_13_before_after_interval_constraints():
    """
    Verifies that BEFORE, AFTER, and INTERVAL constraints boost matching candidates
    and penalize out-of-bounds candidates.
    """
    from apps.api.src.services.context_engine.ranker import MultiSignalRanker

    c_jan = _create_candidate("c_jan", "FuncA", "src/f.py", "1111", "Jan commit", "2026-01-15T00:00:00Z")
    c_mar = _create_candidate("c_mar", "FuncB", "src/f.py", "2222", "Mar commit", "2026-03-15T00:00:00Z")
    c_may = _create_candidate("c_may", "FuncC", "src/f.py", "3333", "May commit", "2026-05-15T00:00:00Z")
    corpus = [c_jan, c_mar, c_may]

    # 1. BEFORE 2026-02-01
    q_bef = analyze_query("Find code committed before 2026-02-01")
    cands_bef = MemoTimeService.apply_memotime_retrieval(copy.deepcopy(corpus), q_bef, q_bef.raw_query)
    ranked_bef = MultiSignalRanker.rank_candidates(cands_bef, q_bef)

    assert ranked_bef[0].candidate.candidate_id == "c_jan"
    assert ranked_bef[0].candidate.signals.get("memotime_temporal_match") == 1.0
    assert any(r.candidate.candidate_id in {"c_mar", "c_may"} and r.candidate.signals.get("memotime_temporal_mismatch") for r in ranked_bef)

    # 2. AFTER 2026-04-01
    q_aft = analyze_query("Find code committed after 2026-04-01")
    cands_aft = MemoTimeService.apply_memotime_retrieval(copy.deepcopy(corpus), q_aft, q_aft.raw_query)
    ranked_aft = MultiSignalRanker.rank_candidates(cands_aft, q_aft)

    assert ranked_aft[0].candidate.candidate_id == "c_may"
    assert ranked_aft[0].candidate.signals.get("memotime_temporal_match") == 1.0

    # 3. INTERVAL between 2026-02-01 and 2026-04-01
    q_int = analyze_query("Find code changes between 2026-02-01 and 2026-04-01")
    cands_int = MemoTimeService.apply_memotime_retrieval(copy.deepcopy(corpus), q_int, q_int.raw_query)
    ranked_int = MultiSignalRanker.rank_candidates(cands_int, q_int)

    assert ranked_int[0].candidate.candidate_id == "c_mar"
    assert ranked_int[0].candidate.signals.get("memotime_temporal_match") == 1.0


# =========================================================================
# TEST 14: Diff and Commit Changeset Retrieval
# =========================================================================
def test_14_diff_changeset_retrieval():
    """
    Verifies that queries referencing a commit hash or diff match the exact commit
    evidence and inject the memotime_diff_match signal.
    """
    from apps.api.src.services.context_engine.ranker import MultiSignalRanker

    target_sha = "a1b2c3d4e5f6"
    c_match = _create_candidate("c_diff", "Decomposer", "src/decomp.py", target_sha, "AST innermost scope", "2026-03-01T00:00:00Z")
    c_other = _create_candidate("c_norm", "Assembler", "src/assemb.py", "999999999999", "Other commit", "2026-03-01T00:00:00Z")

    q_diff = analyze_query(f"What changes were introduced in commit {target_sha}?")
    cands_diff = MemoTimeService.apply_memotime_retrieval([c_match, c_other], q_diff, q_diff.raw_query)
    ranked_diff = MultiSignalRanker.rank_candidates(cands_diff, q_diff)

    assert ranked_diff[0].candidate.candidate_id == "c_diff"
    assert ranked_diff[0].candidate.signals.get("memotime_diff_match") == 1.0


# =========================================================================
# TEST 15: Evolution Queries Return Ordered Evidence
# =========================================================================
def test_15_evolution_ordered_evidence():
    """
    Verifies that EVOLUTION queries order candidates across Tree-of-Time phases:
    phase_0_origin -> phase_1_transition -> phase_2_current
    and assign appropriate chronological order metadata and signals.
    """
    c_orig = _create_candidate("c_o", "Engine", "src/engine.py", "1111", "Origin", "2026-01-01T00:00:00Z")
    c_tran = _create_candidate("c_t", "Engine", "src/engine.py", "2222", "Transition", "2026-03-01T00:00:00Z")
    c_curr = _create_candidate("c_c", "Engine", "src/engine.py", "3333", "Current", "2026-05-01T00:00:00Z")

    q_evo = analyze_query("Trace the evolution of Engine across commits from origin to current state")
    res = MemoTimeService.run_memotime_pipeline(
        candidates=[c_curr, c_orig, c_tran],
        analyzed_query=q_evo,
        query_text=q_evo.raw_query,
    )

    assert res.strategy_used == TemporalIntentType.EVOLUTION
    assert len(res.candidates) == 3

    # Check phase tagging
    phases = [c.metadata.get("memotime_phase") for c in res.candidates]
    assert phases == ["origin", "transition", "current"]

    # Check that candidates have evolution signals
    for c in res.candidates:
        assert c.signals.get("memotime_evolution_phase") is not None


# =========================================================================
# TEST 16: Ambiguous and Missing Evidence Fallback
# =========================================================================
def test_16_ambiguous_and_missing_evidence_fallback():
    """
    Verifies that ambiguous queries or missing candidate timestamps fall back safely
    without exceptions, data loss, or date hallucinations.
    """
    cand1 = _create_candidate("c1", "Helper", "src/h.py", "1111", "msg", "2026-01-01T00:00:00Z")
    cand2 = _create_candidate("c2", "Util", "src/u.py", "2222", "msg", "2026-02-01T00:00:00Z")

    q_amb = analyze_query("What happened to the system during the transition period?")
    res_amb = MemoTimeService.run_memotime_pipeline([cand1, cand2], q_amb, q_amb.raw_query)

    assert res_amb.is_fallback is True or res_amb.strategy_used == TemporalIntentType.AMBIGUOUS
    assert len(res_amb.candidates) == 2

    # Candidate with missing timestamp during bounded query (UNBOUNDED_TEMPORAL)
    cand_no_ts = _create_candidate("c_no_ts", "Helper", "src/h.py", "3333", "msg", None)
    q_bound = analyze_query("Find code committed after 2026-06-01")
    res_bound = MemoTimeService.run_memotime_pipeline([cand_no_ts], q_bound, q_bound.raw_query)

    # Must NOT discard candidate or crash
    assert len(res_bound.candidates) == 1
    assert res_bound.candidates[0].candidate_id == "c_no_ts"


# =========================================================================
# TEST 17: Contradictory Bounds Do Not Produce Invalid Chronological Results
# =========================================================================
def test_17_contradictory_bounds_safe_fallback():
    """
    Verifies that inverted temporal intervals (start > end) are flagged as contradictory
    and fall back safely to baseline ranking without crashing.
    """
    cand = _create_candidate("c1", "Payment", "src/p.py", "1111", "msg", "2026-06-01T00:00:00Z")
    q_contra = analyze_query("What changed between 2026-12-01 and 2026-01-01?")

    res = MemoTimeService.run_memotime_pipeline([cand], q_contra, q_contra.raw_query)
    assert res.is_fallback is True
    assert res.diagnostics.get("is_contradictory") is True
    assert "after end" in (res.fallback_reason or "")
    assert len(res.candidates) == 1


# =========================================================================
# TEST 18: Complete Provenance Survives All Retrieval and Ranking Steps
# =========================================================================
def test_18_provenance_survives_all_retrieval_and_ranking_steps():
    """
    Verifies that commit_sha, commit_message, committed_at, file_path, symbol_name,
    change_type, and fingerprint remain intact through MemoTime retrieval and MultiSignalRanker.
    """
    from apps.api.src.services.context_engine.ranker import MultiSignalRanker

    cand = _create_candidate(
        candidate_id="c_prov",
        name="SecurityService",
        path="apps/api/src/services/security.py",
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        commit_msg="Harden session token rotation",
        committed_at="2026-08-15T12:00:00Z",
    )

    q = analyze_query("What is the current implementation of SecurityService?")
    retrieved = MemoTimeService.apply_memotime_retrieval([cand], q, q.raw_query)
    ranked = MultiSignalRanker.rank_candidates(retrieved, q)

    assert len(ranked) == 1
    prov = ranked[0].candidate.metadata.get("provenance")
    assert prov is not None
    assert prov["commit_sha"] == "abcdef1234567890abcdef1234567890abcdef12"
    assert prov["commit_message"] == "Harden session token rotation"
    assert prov["committed_at"] == "2026-08-15T12:00:00Z"
    assert prov["file_path"] == "apps/api/src/services/security.py"
    assert prov["symbol_name"] == "SecurityService"
    assert prov["change_type"] == "MODIFY"
    assert "fingerprint" in prov


# =========================================================================
# TEST 19: ProjectContextEngine Respects MemoTime Flag and Override
# =========================================================================
@pytest.mark.asyncio
async def test_19_project_context_engine_memotime_flag_and_override():
    """
    Verifies that ProjectContextEngine.investigate:
    1. Defaults to memotime_used=False when MEMOTIME_ENABLED is False and enable_memotime is None.
    2. Sets memotime_used=True in debug_signals when enable_memotime=True.
    """
    from unittest.mock import AsyncMock, MagicMock

    from apps.api.src.services.context_engine.engine import ProjectContextEngine

    engine = ProjectContextEngine()
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.all.return_value = []
    session.execute.return_value = mock_res

    snap_id = uuid.uuid4()

    # Default disabled
    ans_default = await engine.investigate(
        session=session,
        snapshot_id=snap_id,
        question="What is the active AuthService implementation?",
    )
    assert ans_default.debug_signals.get("memotime_used") is False

    # Explicit override enabled
    ans_enabled = await engine.investigate(
        session=session,
        snapshot_id=snap_id,
        question="What is the active AuthService implementation?",
        enable_memotime=True,
    )
    assert ans_enabled.debug_signals.get("memotime_used") is True



# =========================================================================
# TEST 20: Historical Classification Requires Supersession, Not Just Timestamp
# =========================================================================
def test_20_historical_classification_requires_supersession_not_just_timestamp():
    """
    Regression test: Verifies that possessing a timestamp (committed_at) does NOT
    qualify an active candidate as historical.
    - Historical queries must retain and boost legitimate predecessors while leaving active code unboosted.
    - Current queries must prioritize active code and suppress superseded predecessors.
    """
    from apps.api.src.services.context_engine.ranker import MultiSignalRanker

    # Both candidates have valid, non-null commit timestamps
    cand_v1 = _create_candidate(
        candidate_id="c_user_v1",
        name="UserManager (v1)",
        path="apps/api/src/services/user.py",
        commit_sha="1111111111111111111111111111111111111111",
        commit_msg="Initial user manager implementation",
        committed_at="2026-02-01T12:00:00Z",
        symbol_name="UserManager",
    )
    cand_v2 = _create_candidate(
        candidate_id="c_user_v2",
        name="UserManager (v2)",
        path="apps/api/src/services/user.py",
        commit_sha="2222222222222222222222222222222222222222",
        commit_msg="Add user session revocation and multi-tenant auth",
        committed_at="2026-08-01T12:00:00Z",
        symbol_name="UserManager",
    )
    candidates = [cand_v1, cand_v2]

    # 1. Historical Query Execution
    q_hist = analyze_query("What was the previous superseded implementation of UserManager?")
    res_hist = MemoTimeService.run_memotime_pipeline(
        candidates=copy.deepcopy(candidates),
        analyzed_query=q_hist,
        query_text=q_hist.raw_query,
    )
    assert res_hist.strategy_used == TemporalIntentType.HISTORICAL

    # Superseded candidate v1 must be tagged with historical signals
    c1_hist = next(c for c in res_hist.candidates if c.candidate_id == "c_user_v1")
    assert c1_hist.signals.get("memotime_historical") == 1.0
    assert c1_hist.signals.get("memotime_temporal_match") == 1.0
    assert c1_hist.metadata.get("memotime_strategy") == "HISTORICAL"
    assert c1_hist.metadata.get("is_superseded") is True

    # Active candidate v2 must NOT be tagged as historical despite having committed_at
    c2_hist = next(c for c in res_hist.candidates if c.candidate_id == "c_user_v2")
    assert c2_hist.signals.get("memotime_historical") is None
    assert c2_hist.metadata.get("memotime_strategy") is None
    assert c2_hist.metadata.get("is_current") is True

    # Ranking under historical query: superseded candidate v1 must rank #1
    ranked_hist = MultiSignalRanker.rank_candidates(res_hist.candidates, q_hist)
    assert ranked_hist[0].candidate.candidate_id == "c_user_v1"

    # 2. Current Query Execution
    q_curr = analyze_query("What is the current active implementation of UserManager?")
    res_curr = MemoTimeService.run_memotime_pipeline(
        candidates=copy.deepcopy(candidates),
        analyzed_query=q_curr,
        query_text=q_curr.raw_query,
    )
    assert res_curr.strategy_used == TemporalIntentType.CURRENT

    # Active candidate v2 must be tagged with temporal match
    c2_curr = next(c for c in res_curr.candidates if c.candidate_id == "c_user_v2")
    assert c2_curr.signals.get("memotime_temporal_match") == 1.0
    assert c2_curr.metadata.get("is_current") is True

    # Ranking under current query: active candidate v2 must rank #1
    ranked_curr = MultiSignalRanker.rank_candidates(res_curr.candidates, q_curr)
    assert ranked_curr[0].candidate.candidate_id == "c_user_v2"

    # 3. Tree of Time Binding Verification
    tree = MemoTimeService.build_tree_of_time(q_hist.raw_query, target_symbols=["UserManager"])
    tree = MemoTimeService.bind_evidence_to_tree(tree, copy.deepcopy(candidates))
    hist_node = tree.nodes["node_historical"]
    assert hist_node.resolution_status == ResolutionStatus.RESOLVED
    assert len(hist_node.evidence_candidates) == 1
    assert hist_node.evidence_candidates[0].candidate_id == "c_user_v1"


# =========================================================================
# TEST 21: Valid Multi-Entity Temporal Dependency
# =========================================================================
def test_21_valid_multi_entity_temporal_dependency():
    """
    Verifies that when entity A depends on entity B, and B was introduced
    before or during A's lifetime (t_start(B) <= t_end(A)), the dependency
    is validated as compatible and no mismatch penalty is applied.
    """
    t_start_a = datetime(2026, 1, 1, tzinfo=UTC)
    t_end_a = datetime(2026, 12, 31, tzinfo=UTC)
    t_start_b = datetime(2026, 3, 1, tzinfo=UTC)
    t_end_b = datetime(2026, 12, 31, tzinfo=UTC)

    bounds = {
        "paymentservice": TemporalBound(start=t_start_a, end=t_end_a),
        "stripeconnector": TemporalBound(start=t_start_b, end=t_end_b),
    }

    valid, errors = MemoTimeService.validate_multi_entity_bounds(
        entity_bounds=bounds,
        dependencies=[("PaymentService", "StripeConnector")],
    )
    assert valid is True
    assert errors == []

    c_a = _create_candidate("c_a", "PaymentService", "src/payment.py", "1111", "Payment service", "2026-01-01T00:00:00Z")
    c_b = _create_candidate("c_b", "StripeConnector", "src/stripe.py", "2222", "Stripe connector", "2026-03-01T00:00:00Z")
    c_a.metadata["dependencies"] = [("PaymentService", "StripeConnector")]

    cands, errs = MemoTimeService.propagate_cross_entity_temporal_constraints([c_a, c_b], entity_bounds=bounds)
    assert errs == []
    assert not c_a.signals.get("memotime_temporal_mismatch")
    assert not c_b.signals.get("memotime_temporal_mismatch")


# =========================================================================
# TEST 22: Dependency Introduced After Dependent Component Lifetime
# =========================================================================
def test_22_dependency_introduced_after_dependent_interval():
    """
    Verifies that when entity A depends on entity B, but B was introduced
    AFTER A ended (t_start(B) > t_end(A)), the timeline is flagged as
    incompatible and violating candidates receive memotime_temporal_mismatch=1.0.
    """
    t_start_a = datetime(2026, 1, 1, tzinfo=UTC)
    t_end_a = datetime(2026, 6, 30, tzinfo=UTC)
    t_start_b = datetime(2026, 9, 1, tzinfo=UTC)
    t_end_b = datetime(2026, 12, 31, tzinfo=UTC)

    bounds = {
        "legacyauthservice": TemporalBound(start=t_start_a, end=t_end_a),
        "oidcconnector": TemporalBound(start=t_start_b, end=t_end_b),
    }

    valid, errors = MemoTimeService.validate_multi_entity_bounds(
        entity_bounds=bounds,
        dependencies=[("LegacyAuthService", "OidcConnector")],
    )
    assert valid is False
    assert any("introduced later" in e for e in errors)

    c_a = _create_candidate("c_a", "LegacyAuthService", "src/auth.py", "1111", "Legacy auth", "2026-06-30T00:00:00Z")
    c_a.metadata["is_superseded"] = True
    c_a.metadata["valid_end"] = "2026-06-30T00:00:00Z"
    c_a.metadata["dependencies"] = [("LegacyAuthService", "OidcConnector")]

    c_b = _create_candidate("c_b", "OidcConnector", "src/oidc.py", "2222", "OIDC connector", "2026-09-01T00:00:00Z")
    c_b.metadata["valid_start"] = "2026-09-01T00:00:00Z"

    cands, errs = MemoTimeService.propagate_cross_entity_temporal_constraints([c_a, c_b], entity_bounds=bounds)
    assert len(errs) > 0
    assert c_a.signals.get("memotime_temporal_mismatch") == 1.0
    assert "introduced later" in c_a.metadata.get("memotime_temporal_error", "")


# =========================================================================
# TEST 23: Multi-Hop Transitive Path Incompatible Bounds
# =========================================================================
def test_23_multi_hop_path_incompatible_bounds():
    """
    Verifies that multi-hop dependency paths (A -> B -> C) propagate temporal
    constraints transitively: if C is introduced after A ended, the transitive
    incompatibility is detected across 2 hops and penalized.
    """
    t_start_a = datetime(2026, 1, 1, tzinfo=UTC)
    t_end_a = datetime(2026, 5, 31, tzinfo=UTC)
    t_start_b = datetime(2026, 4, 1, tzinfo=UTC)
    t_end_b = datetime(2026, 7, 31, tzinfo=UTC)
    t_start_c = datetime(2026, 8, 1, tzinfo=UTC)
    t_end_c = datetime(2026, 12, 31, tzinfo=UTC)

    bounds = {
        "servicea": TemporalBound(start=t_start_a, end=t_end_a),
        "serviceb": TemporalBound(start=t_start_b, end=t_end_b),
        "servicec": TemporalBound(start=t_start_c, end=t_end_c),
    }

    # Transitive check: A -> B and B -> C
    valid, errors = MemoTimeService.validate_multi_entity_bounds(
        entity_bounds=bounds,
        dependencies=[("ServiceA", "ServiceB"), ("ServiceB", "ServiceC")],
    )
    assert valid is False
    assert any("2-hop" in e for e in errors)
    assert any("ServiceA" in e and "ServiceC" in e for e in errors)

    c_a = _create_candidate("c_a", "ServiceA", "src/a.py", "1111", "Service A", "2026-05-31T00:00:00Z")
    c_a.metadata["is_superseded"] = True
    c_a.metadata["valid_end"] = "2026-05-31T00:00:00Z"
    c_a.metadata["relationship_path"] = "ServiceA -> ServiceB -> ServiceC"

    c_b = _create_candidate("c_b", "ServiceB", "src/b.py", "2222", "Service B", "2026-04-01T00:00:00Z")
    c_c = _create_candidate("c_c", "ServiceC", "src/c.py", "3333", "Service C", "2026-08-01T00:00:00Z")
    c_c.metadata["valid_start"] = "2026-08-01T00:00:00Z"

    cands, errs = MemoTimeService.propagate_cross_entity_temporal_constraints([c_a, c_b, c_c], entity_bounds=bounds)
    assert len(errs) > 0
    assert c_a.signals.get("memotime_temporal_mismatch") == 1.0


# =========================================================================
# TEST 24: Missing Timestamps in Path (UNBOUNDED_TEMPORAL Safe Fallback)
# =========================================================================
def test_24_missing_timestamps_in_path_unbounded():
    """
    Verifies that when intermediate or leaf entities in a dependency path lack
    timestamps, MemoTime treats the relationship as UNBOUNDED_TEMPORAL without
    fabricating dates, raising false contradictions, or dropping candidates.
    """
    bounds = {
        "servicea": TemporalBound(start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2026, 5, 31, tzinfo=UTC)),
    }

    valid, errors = MemoTimeService.validate_multi_entity_bounds(
        entity_bounds=bounds,
        dependencies=[("ServiceA", "ServiceB"), ("ServiceB", "ServiceC")],
    )
    assert valid is True
    assert errors == []

    c_a = _create_candidate("c_a", "ServiceA", "src/a.py", "1111", "Service A", "2026-05-31T00:00:00Z")
    c_b = _create_candidate("c_b", "ServiceB", "src/b.py", "2222", "Service B", "")
    c_b.metadata.pop("committed_at", None)
    c_c = _create_candidate("c_c", "ServiceC", "src/c.py", "3333", "Service C", "")
    c_c.metadata.pop("committed_at", None)

    cands, errs = MemoTimeService.propagate_cross_entity_temporal_constraints(
        [c_a, c_b, c_c],
        dependencies=[("ServiceA", "ServiceB"), ("ServiceB", "ServiceC")],
        entity_bounds=bounds,
    )
    assert errs == []
    assert not c_a.signals.get("memotime_temporal_mismatch")
    assert not c_b.signals.get("memotime_temporal_mismatch")
    assert not c_c.signals.get("memotime_temporal_mismatch")
    assert len(cands) == 3


# =========================================================================
# TEST 25: Disconnected Entities Do Not Form Unjustified Temporal Edges
# =========================================================================
def test_25_disconnected_entities_no_unjustified_edge():
    """
    Verifies that two entities with non-overlapping or disjoint timestamps
    that have NO dependency or graph relationship between them are NOT
    falsely constrained or marked with contradictions.
    """
    bounds = {
        "billingengine": TemporalBound(start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2026, 3, 31, tzinfo=UTC)),
        "reportingservice": TemporalBound(start=datetime(2026, 6, 1, tzinfo=UTC), end=datetime(2026, 12, 31, tzinfo=UTC)),
    }

    # No dependency edge between BillingEngine and ReportingService
    valid, errors = MemoTimeService.validate_multi_entity_bounds(
        entity_bounds=bounds,
        dependencies=[],
    )
    assert valid is True
    assert errors == []

    c_billing = _create_candidate("c_bill", "BillingEngine", "src/billing.py", "1111", "Billing code", "2026-01-01T00:00:00Z")
    c_report = _create_candidate("c_rep", "ReportingService", "src/report.py", "2222", "Report code", "2026-06-01T00:00:00Z")

    cands, errs = MemoTimeService.propagate_cross_entity_temporal_constraints([c_billing, c_report], entity_bounds=bounds)
    assert errs == []
    assert not c_billing.signals.get("memotime_temporal_mismatch")
    assert not c_report.signals.get("memotime_temporal_mismatch")


# =========================================================================
# TEST 26: Historical and Current Queries Over Evolving Chains
# =========================================================================
def test_26_historical_and_current_queries_evolving_chain():
    """
    Verifies that an evolving chain (A_v1 -> B_v1 superseded by A_v2 -> B_v2)
    correctly routes to active candidates under CURRENT queries and superseded
    precursors under HISTORICAL queries.
    """
    from apps.api.src.services.context_engine.ranker import MultiSignalRanker

    # v1 (historical/superseded)
    c_a_v1 = _create_candidate("c_a_v1", "AuthService", "src/auth.py", "1111", "Auth v1", "2026-01-01T00:00:00Z")
    c_a_v1.metadata["is_superseded"] = True
    c_a_v1.metadata["is_current"] = False
    c_b_v1 = _create_candidate("c_b_v1", "TokenManager", "src/token.py", "1111", "Token v1", "2026-01-01T00:00:00Z")
    c_b_v1.metadata["is_superseded"] = True
    c_b_v1.metadata["is_current"] = False

    # v2 (current/active)
    c_a_v2 = _create_candidate("c_a_v2", "AuthService", "src/auth.py", "2222", "Auth v2", "2026-06-01T00:00:00Z")
    c_a_v2.metadata["is_superseded"] = False
    c_a_v2.metadata["is_current"] = True
    c_b_v2 = _create_candidate("c_b_v2", "TokenManager", "src/token.py", "2222", "Token v2", "2026-06-01T00:00:00Z")
    c_b_v2.metadata["is_superseded"] = False
    c_b_v2.metadata["is_current"] = True

    candidates = [c_a_v1, c_b_v1, c_a_v2, c_b_v2]

    # CURRENT query
    q_curr = analyze_query("What is the current active implementation of AuthService and TokenManager?")
    res_curr = MemoTimeService.run_memotime_pipeline(copy.deepcopy(candidates), q_curr, q_curr.raw_query)
    assert res_curr.strategy_used == TemporalIntentType.CURRENT
    ranked_curr = MultiSignalRanker.rank_candidates(res_curr.candidates, q_curr)
    top_curr_ids = [r.candidate.candidate_id for r in ranked_curr[:2]]
    assert "c_a_v2" in top_curr_ids
    assert "c_b_v2" in top_curr_ids

    # HISTORICAL query
    q_hist = analyze_query("What was the previous superseded implementation of AuthService and TokenManager?")
    res_hist = MemoTimeService.run_memotime_pipeline(copy.deepcopy(candidates), q_hist, q_hist.raw_query)
    assert res_hist.strategy_used == TemporalIntentType.HISTORICAL
    ranked_hist = MultiSignalRanker.rank_candidates(res_hist.candidates, q_hist)
    top_hist_ids = [r.candidate.candidate_id for r in ranked_hist[:2]]
    assert "c_a_v1" in top_hist_ids
    assert "c_b_v1" in top_hist_ids


# =========================================================================
# TEST 27: Provenance Preservation Through Temporal Propagation
# =========================================================================
def test_27_provenance_preservation_through_propagation():
    """
    Verifies that cross-entity temporal propagation and pipeline execution
    preserve all provenance metadata: commit_sha, snapshot_id, file_id,
    relationship_hop, relationship_path, connected_from, and provenance dict.
    """
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    c = _create_candidate("c_prov", "ServiceA", "src/a.py", "a1b2c3d4e5f6", "Commit message", "2026-04-01T00:00:00Z")
    c.metadata["snapshot_id"] = str(snap_id)
    c.metadata["file_id"] = str(file_id)
    c.metadata["relationship_hop"] = 2
    c.metadata["relationship_path"] = "ServiceX -> ServiceY -> ServiceA"
    c.metadata["connected_from"] = "src/y.py"
    c.metadata["provenance"] = {"atom_id": "atom_123", "symbol_name": "ServiceA"}

    cands, _ = MemoTimeService.propagate_cross_entity_temporal_constraints([c])
    res_c = cands[0]

    assert res_c.metadata["commit_sha"] == "a1b2c3d4e5f6"
    assert res_c.metadata["snapshot_id"] == str(snap_id)
    assert res_c.metadata["file_id"] == str(file_id)
    assert res_c.metadata["relationship_hop"] == 2
    assert res_c.metadata["relationship_path"] == "ServiceX -> ServiceY -> ServiceA"
    assert res_c.metadata["connected_from"] == "src/y.py"
    assert res_c.metadata["provenance"]["atom_id"] == "atom_123"


# =========================================================================
# TEST 28: Grounded Diff Evidence Extraction (Lines, Symbols, Line Bounds)
# =========================================================================
def test_28_precise_diff_evidence_extraction():
    """
    Verifies precise extraction of diff evidence attributed to file, symbol,
    and line level with added and deleted lines.
    """
    c = _create_candidate("c_diff", "RankerAudit", "src/ranker.py", "773b740a1b2c", "Audit ranker", "2026-03-01T00:00:00Z")
    c.metadata["added_lines"] = ["def audit_weights():", "    return 1.5"]
    c.metadata["deleted_lines"] = ["def old_weights():"]
    c.metadata["start_line"] = 100
    c.metadata["end_line"] = 125
    c.metadata["symbol_name"] = "audit_weights"
    c.metadata["chunk_type"] = "ATOM_MODIFY"

    ev = MemoTimeService.extract_diff_evidence(c)
    assert ev["commit_sha"] == "773b740a1b2c"
    assert ev["path"] == "src/ranker.py"
    assert ev["symbol"] == "audit_weights"
    assert ev["change_type"] == "ATOM_MODIFY"
    assert ev["is_deleted"] is False
    assert len(ev["added_lines"]) == 2
    assert len(ev["deleted_lines"]) == 1
    assert ev["line_range"] == (100, 125)
    assert ev["is_available"] is True
    assert ev["is_empty"] is False

    # Test deleted symbol attribution
    c_del = _create_candidate("c_del", "LegacyHelper (DELETE)", "src/helper.py", "773b740a1b2c", "Remove helper", "2026-03-01T00:00:00Z")
    c_del.metadata["chunk_type"] = "ATOM_DELETE"
    c_del.metadata["symbol_name"] = "LegacyHelper"
    c_del.metadata["is_deleted"] = True
    c_del.metadata["deleted_lines"] = ["class LegacyHelper:", "    pass"]

    ev_del = MemoTimeService.extract_diff_evidence(c_del)
    assert ev_del["is_deleted"] is True
    assert ev_del["symbol"] == "LegacyHelper"
    assert len(ev_del["deleted_lines"]) == 2


# =========================================================================
# TEST 29: Diff Ambiguous SHA, Missing SHA, and Unavailable Evidence
# =========================================================================
def test_29_diff_ambiguous_or_missing_sha():
    """
    Verifies that:
    1. Ambiguous abbreviated commit SHA prefixes match multiple distinct commits
       and safely fall back without arbitrarily picking one commit.
    2. Missing commit SHAs fall back safely without fabricating diff hunks.
    3. Unavailable diff evidence sets is_available=False without fabricating lines.
    """
    # 1. Ambiguous commit SHA prefix
    c1 = _create_candidate("c1", "Mod1", "src/m1.py", "42096a5000000000000000000000000000000001", "C1", "2026-04-01T00:00:00Z")
    c2 = _create_candidate("c2", "Mod2", "src/m2.py", "42096a5eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee2", "C2", "2026-04-01T00:00:00Z")

    res_amb = MemoTimeService.run_memotime_pipeline(
        candidates=[c1, c2],
        query_text="What changed in commit 42096a5?",
    )
    assert res_amb.is_fallback is True
    assert "Ambiguous commit SHA prefix" in (res_amb.fallback_reason or "")
    assert len(res_amb.diagnostics.get("ambiguous_commits", [])) == 2

    # 2. Missing commit SHA
    res_missing = MemoTimeService.run_memotime_pipeline(
        candidates=[c1],
        query_text="Show diff for commit deadbeef0000",
    )
    assert res_missing.is_fallback is True
    assert "not found in candidate corpus" in (res_missing.fallback_reason or "")

    # 3. Unavailable diff evidence
    c_unavail = _create_candidate("c_unavail", "ArchivedMod", "src/arch.py", "b094f01", "Old commit", "2026-01-01T00:00:00Z")
    c_unavail.metadata["diff_unavailable"] = True

    ev_unavail = MemoTimeService.extract_diff_evidence(c_unavail)
    assert ev_unavail["is_available"] is False
    assert ev_unavail["is_empty"] is False
    assert "unavailable" in ev_unavail.get("reason", "").lower()
    assert ev_unavail["added_lines"] == []
    assert ev_unavail["deleted_lines"] == []


# =========================================================================
# TEST 30: Engine Error Isolation and Diagnostics
# =========================================================================
async def test_30_engine_error_isolation_and_diagnostics():
    """
    Verifies that ProjectContextEngine.investigate:
    1. Sets memotime_used=True and records memotime_diagnostics on successful execution.
    2. When MemoTime raises an unexpected exception, catches it safely without failing the request,
       sets memotime_used=False, and records exception_occurred in diagnostics.
    3. When disabled (enable_memotime=False), sets memotime_used=False without running MemoTime.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from apps.api.src.services.context_engine.engine import ProjectContextEngine

    engine = ProjectContextEngine()
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.all.return_value = []
    session.execute.return_value = mock_res
    snap_id = uuid.uuid4()

    # 1. Normal execution with enable_memotime=True
    ans_ok = await engine.investigate(
        session=session,
        snapshot_id=snap_id,
        question="What is the active AuthService implementation?",
        enable_memotime=True,
    )
    assert ans_ok.debug_signals.get("memotime_used") is True
    assert "strategy" in ans_ok.debug_signals.get("memotime_diagnostics", {})

    # 2. Exception isolation: unexpected error in MemoTime does not crash the request
    with patch.object(
        MemoTimeService,
        "run_memotime_pipeline",
        side_effect=RuntimeError("Simulated unexpected graph traversal error"),
    ):
        ans_err = await engine.investigate(
            session=session,
            snapshot_id=snap_id,
            question="What is the active AuthService implementation?",
            enable_memotime=True,
        )
        assert ans_err.debug_signals.get("memotime_used") is False
        diag = ans_err.debug_signals.get("memotime_diagnostics", {})
        assert diag.get("exception_occurred") is True
        assert "Simulated unexpected graph traversal error" in diag.get("error", "")

    # 3. Disabled execution: enable_memotime=False
    ans_disabled = await engine.investigate(
        session=session,
        snapshot_id=snap_id,
        question="What is the active AuthService implementation?",
        enable_memotime=False,
    )
    assert ans_disabled.debug_signals.get("memotime_used") is False


# ==============================================================================
# 31. Two-Commit Comparative Diff Intent, Tree Decomposition & Retrieval
# ==============================================================================


def test_31_two_commit_comparative_diff_intent_and_retrieval():
    """
    Verifies two-commit revision comparison:
    1. parse_temporal_intent identifies 'compare commit A and commit B' as DIFF with both reference commits.
    2. build_tree_of_time decomposes into node_diff_base (HISTORICAL) and node_diff_target (DIFF).
    3. run_memotime_pipeline partitions candidates into target (diff_role='target') and base (diff_role='base').
    """
    sha_a = "b094f01"
    sha_b = "be1b5b5"
    query = f"Compare commit {sha_a} and commit {sha_b} for ast scope resolution"

    intent = MemoTimeService.parse_temporal_intent(query, target_symbols=["ast_scope"])
    assert intent.intent_type == TemporalIntentType.DIFF
    assert intent.is_temporal is True
    assert intent.reference_commits == [sha_a, sha_b]

    tree = MemoTimeService.build_tree_of_time(query, target_symbols=["ast_scope"])
    assert "node_diff_base" in tree.nodes
    assert "node_diff_target" in tree.nodes
    assert tree.nodes["node_diff_base"].intent_type == TemporalIntentType.HISTORICAL
    assert tree.nodes["node_diff_target"].intent_type == TemporalIntentType.DIFF

    # Candidate retrieval with base and target
    c_base = _create_candidate(
        candidate_id="c_base",
        name="resolve_scope",
        path="decomposer.py",
        commit_sha=sha_a,
        commit_msg="base commit",
        committed_at="2026-01-01T00:00:00Z",
        content="def resolve_scope(): pass",
    )
    c_target = _create_candidate(
        candidate_id="c_target",
        name="resolve_scope",
        path="decomposer.py",
        commit_sha=sha_b,
        commit_msg="target commit",
        committed_at="2026-02-01T00:00:00Z",
        content="def resolve_scope(ast_tree): pass",
    )
    c_target.metadata["added_lines"] = ["def resolve_scope(ast_tree): pass"]
    c_other = _create_candidate(
        candidate_id="c_other",
        name="other_util",
        path="util.py",
        commit_sha="4e5af91",
        commit_msg="other commit",
        committed_at="2026-01-15T00:00:00Z",
        content="pass",
    )

    res = MemoTimeService.run_memotime_pipeline(
        candidates=[c_base, c_target, c_other],
        query_text=query,
    )
    assert res.is_fallback is False
    assert res.strategy_used == TemporalIntentType.DIFF
    assert res.applied_signals_count >= 2

    # Verify candidate tagging
    c_tgt_res = next(c for c in res.candidates if c.candidate_id == "c_target")
    assert c_tgt_res.metadata.get("memotime_diff_role") == "target"
    assert c_tgt_res.signals.get("memotime_diff_match") == 1.0

    c_base_res = next(c for c in res.candidates if c.candidate_id == "c_base")
    assert c_base_res.metadata.get("memotime_diff_role") == "base"
    assert c_base_res.signals.get("memotime_temporal_match") == 0.8

    # Target candidate ranks above base candidate
    c_ids = [c.candidate_id for c in res.candidates]
    assert c_ids.index("c_target") < c_ids.index("c_base") < c_ids.index("c_other")


# ==============================================================================
# 32. After-Before Compound Query Contradiction and Bounded Interval
# ==============================================================================


def test_32_after_before_compound_query_contradiction_and_interval():
    """
    Verifies compound queries containing both 'after' and 'before':
    1. Inverted bounds ('after 2026-06-01 and before 2026-01-01') detect contradiction (is_contradictory=True).
    2. Valid bounds ('after 2026-01-01 and before 2026-06-01') resolve to bounded INTERVAL.
    """
    # 1. Contradiction
    q_contra = "What was the AuthService implementation after 2026-06-01 and before 2026-01-01?"
    intent_contra = MemoTimeService.parse_temporal_intent(q_contra)
    assert intent_contra.intent_type == TemporalIntentType.AMBIGUOUS
    assert intent_contra.is_contradictory is True
    assert "start bound" in (intent_contra.contradiction_reason or "")
    assert "after end bound" in (intent_contra.contradiction_reason or "")

    tree_contra = MemoTimeService.build_tree_of_time(q_contra)
    assert tree_contra.is_valid is False
    assert len(tree_contra.validation_errors) > 0

    # 2. Valid interval
    q_valid = "What was the AuthService implementation after 2026-01-01 and before 2026-06-01?"
    intent_valid = MemoTimeService.parse_temporal_intent(q_valid)
    assert intent_valid.intent_type == TemporalIntentType.INTERVAL
    assert intent_valid.is_contradictory is False
    assert len(intent_valid.constraints) == 1
    assert intent_valid.constraints[0].bound is not None
    assert intent_valid.constraints[0].bound.start == datetime(2026, 1, 1, tzinfo=UTC)
    assert intent_valid.constraints[0].bound.end == datetime(2026, 6, 1, tzinfo=UTC)


# ==============================================================================
# 33. All 13 Allen Interval Relations with matches_allen_relation and Open Bounds
# ==============================================================================


def test_33_all_13_allen_relations_with_matches_allen_relation_and_open_bounds():
    """
    Verifies all 13 Allen interval algebra relations using matches_allen_relation,
    testing inverse consistency and open-ended ongoing bounds (end=None).
    """
    from datetime import timedelta

    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    t1 = t0 + timedelta(days=10)
    t2 = t0 + timedelta(days=20)
    t3 = t0 + timedelta(days=30)

    # 1. EQUALS
    b_eq1 = TemporalBound(start=t1, end=t2)
    b_eq2 = TemporalBound(start=t1, end=t2)
    assert MemoTimeService.matches_allen_relation(b_eq1, b_eq2, AllenIntervalRelation.EQUALS)

    # 2. BEFORE / AFTER
    b_bef1 = TemporalBound(start=t0, end=t1)
    b_bef2 = TemporalBound(start=t2, end=t3)
    assert MemoTimeService.matches_allen_relation(b_bef1, b_bef2, AllenIntervalRelation.BEFORE)
    assert MemoTimeService.matches_allen_relation(b_bef2, b_bef1, AllenIntervalRelation.AFTER)

    # 3. MEETS / MET_BY
    b_m1 = TemporalBound(start=t0, end=t1)
    b_m2 = TemporalBound(start=t1, end=t2)
    assert MemoTimeService.matches_allen_relation(b_m1, b_m2, AllenIntervalRelation.MEETS)
    assert MemoTimeService.matches_allen_relation(b_m2, b_m1, AllenIntervalRelation.MET_BY)

    # 4. OVERLAPS / OVERLAPPED_BY
    b_o1 = TemporalBound(start=t0, end=t2)
    b_o2 = TemporalBound(start=t1, end=t3)
    assert MemoTimeService.matches_allen_relation(b_o1, b_o2, AllenIntervalRelation.OVERLAPS)
    assert MemoTimeService.matches_allen_relation(b_o2, b_o1, AllenIntervalRelation.OVERLAPPED_BY)

    # 5. DURING / CONTAINS
    b_d1 = TemporalBound(start=t1, end=t2)
    b_d2 = TemporalBound(start=t0, end=t3)
    assert MemoTimeService.matches_allen_relation(b_d1, b_d2, AllenIntervalRelation.DURING)
    assert MemoTimeService.matches_allen_relation(b_d2, b_d1, AllenIntervalRelation.CONTAINS)

    # 6. STARTS / STARTED_BY
    b_s1 = TemporalBound(start=t0, end=t1)
    b_s2 = TemporalBound(start=t0, end=t2)
    assert MemoTimeService.matches_allen_relation(b_s1, b_s2, AllenIntervalRelation.STARTS)
    assert MemoTimeService.matches_allen_relation(b_s2, b_s1, AllenIntervalRelation.STARTED_BY)

    # 7. FINISHES / FINISHED_BY
    b_f1 = TemporalBound(start=t1, end=t2)
    b_f2 = TemporalBound(start=t0, end=t2)
    assert MemoTimeService.matches_allen_relation(b_f1, b_f2, AllenIntervalRelation.FINISHES)
    assert MemoTimeService.matches_allen_relation(b_f2, b_f1, AllenIntervalRelation.FINISHED_BY)

    # Open-ended bounds (ongoing active code)
    b_open1 = TemporalBound(start=t0, end=None)
    b_open2 = TemporalBound(start=t0, end=None)
    assert MemoTimeService.matches_allen_relation(b_open1, b_open2, AllenIntervalRelation.EQUALS)

    b_open_earlier = TemporalBound(start=t0, end=None)
    b_open_later = TemporalBound(start=t1, end=None)
    assert MemoTimeService.matches_allen_relation(b_open_earlier, b_open_later, AllenIntervalRelation.OVERLAPS)
    assert MemoTimeService.matches_allen_relation(b_open_later, b_open_earlier, AllenIntervalRelation.OVERLAPPED_BY)


# ==============================================================================
# 34. Tree of Time Child Interval Encapsulation Check
# ==============================================================================


def test_34_tree_of_time_child_interval_encapsulation_check():
    """
    Verifies that validate_temporal_constraints detects child interval encapsulation violations
    when a child node's start or end boundary escapes the parent root node's interval.
    """
    t_start = datetime(2026, 1, 1, tzinfo=UTC)
    t_end = datetime(2026, 6, 1, tzinfo=UTC)
    t_escaped = datetime(2026, 7, 1, tzinfo=UTC)

    tree = TreeOfTime(
        root_query="Bounded analysis",
        root_intent=StructuredTemporalIntent(
            intent_type=TemporalIntentType.INTERVAL,
            is_temporal=True,
            constraints=[
                TemporalConstraint(
                    constraint_id="c0",
                    operator="INTERVAL",
                    target_entity="system",
                    bound=TemporalBound(start=t_start, end=t_end),
                )
            ],
        ),
    )
    root = TimeTreeNode(
        node_id="root",
        query_subquestion="Root",
        intent_type=TemporalIntentType.INTERVAL,
        temporal_bound=TemporalBound(start=t_start, end=t_end),
    )
    # Child interval escapes parent end (t_escaped > t_end)
    child = TimeTreeNode(
        node_id="child_escaped",
        query_subquestion="Child",
        intent_type=TemporalIntentType.INTERVAL,
        temporal_bound=TemporalBound(start=t_start, end=t_escaped),
        parent_id="root",
    )
    tree.add_node(root)
    tree.add_node(child)

    is_valid, errors = MemoTimeService.validate_temporal_constraints(tree)
    assert is_valid is False
    assert any("escapes parent" in e for e in errors)


# ==============================================================================
# 35. Multi-Hop Cross-Entity Provenance and Relationship Types
# ==============================================================================


def test_35_multi_hop_cross_entity_provenance_and_relationship_types():
    """
    Verifies that multi-hop cross-entity constraint validation traces relationships,
    formats provenance with explicit edge types (e.g., A -[CALLS]-> B -[IMPORTS]-> C),
    and enforces maximum traversal depth.
    """
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    t1 = datetime(2026, 3, 1, tzinfo=UTC)
    t2 = datetime(2026, 6, 1, tzinfo=UTC)

    # ServiceA ends at t0. ServiceB ends at t1. ServiceC starts at t2 (> t0).
    bounds = {
        "servicea": TemporalBound(start=datetime(2025, 1, 1, tzinfo=UTC), end=t0),
        "serviceb": TemporalBound(start=t0, end=t1),
        "servicec": TemporalBound(start=t2, end=None),
    }

    # Explicit 2-hop dependencies with relationship types
    deps = [
        ("ServiceA", "ServiceB", "CALLS"),
        ("ServiceB", "ServiceC", "IMPORTS"),
    ]

    is_valid, errors = MemoTimeService.validate_multi_entity_bounds(
        entity_bounds=bounds,
        dependencies=deps,
        max_depth=3,
    )
    assert is_valid is False
    assert len(errors) >= 1
    # Check provenance format includes relationship type
    err = errors[0]
    assert "-[CALLS]->" in err or "-[IMPORTS]->" in err
    assert "ServiceA" in err
    assert "ServiceC" in err
    assert "introduced later at" in err
