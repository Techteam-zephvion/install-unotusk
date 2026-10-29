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

import uuid
from datetime import UTC, datetime

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.memotime import (
    AllenIntervalRelation,
    MemoTimeService,
    ResolutionStatus,
    TemporalBound,
    TemporalConstraint,
    TemporalIntentType,
    TimeTreeNode,
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
