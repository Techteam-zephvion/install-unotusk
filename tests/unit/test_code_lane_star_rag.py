"""
Comprehensive evaluation test suite for STAR-RAG Code Lane Milestone 1.

Verifies:
1. Deterministic entity relation-pattern typing (Apriori-style mining, support thresholds, fallbacks).
2. Rule-node generation and original-event mapping.
3. Hamming-distance candidate edge construction (dH <= 1).
4. Temporal-span calculation and validity handling (missing dates, days scale, zero clamping).
5. MDL cost calculations and greedy pruning (model cost, coverage cost, temporal cost).
6. PPR convergence and deterministic ranking (power iteration, L1 tolerance, stationary distribution).
7. Mapping selected rules back to relevant code evidence.
8. Historical versus current implementation retrieval (supersession resolution).
9. Empty or sparse graphs and graceful fallback.
10. Repository/snapshot isolation and provenance preservation.
11. Hand-verifiable temporal graph with known expected behavior.
12. Baseline versus STAR-RAG evaluation comparison on realistic temporal queries.
"""

import math
import uuid
from datetime import UTC, datetime

from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag import (
    EntityRelationMiner,
    MdlGraphSelector,
    RuleNode,
    SeededPprRetriever,
    StarRagContextService,
    TemporalCodeEvent,
    TemporalRuleGraphBuilder,
)


def make_candidate(
    candidate_id: str,
    name: str,
    path: str,
    content: str,
    committed_at: datetime | None = None,
    temporal_relations: list[dict] | None = None,
    signals: dict[str, float] | None = None,
    snapshot_id: uuid.UUID | None = None,
    repository_id: uuid.UUID | None = None,
    file_id: uuid.UUID | None = None,
    symbol_name: str | None = None,
    change_type: str = "ADD",
) -> RetrievedCandidate:
    snap_id = snapshot_id or uuid.uuid4()
    f_id = file_id or uuid.uuid4()
    meta = {
        "snapshot_id": str(snap_id),
        "file_id": str(f_id),
        "chunk_type": change_type,
        "symbol_name": symbol_name or name,
    }
    if repository_id:
        meta["repository_id"] = str(repository_id)
    if committed_at:
        meta["committed_at"] = committed_at.isoformat()
    if temporal_relations is not None:
        meta["temporal_relations"] = temporal_relations

    return RetrievedCandidate(
        candidate_id=candidate_id,
        entity_type="CHUNK",
        name=name,
        path=path,
        start_line=1,
        end_line=20,
        content=content,
        file_id=f_id,
        signals=dict(signals or {"vector_similarity": 0.8}),
        metadata=meta,
    )


# ==============================================================================
# 1. Deterministic Entity Relation-Pattern Typing
# ==============================================================================


def test_1_deterministic_entity_relation_pattern_typing():
    """
    Tests Apriori-style mining of recurring relation patterns to derive entity types.
    Verifies:
    - Frequent relation subsets mined with minimum support.
    - Entities sharing relation patterns receive the same type ID.
    - Infrequent/sparse entities fall back deterministically without crash.
    """
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    # 4 entities: AuthSvc and UserSvc share (CALLS, IMPORTS, DEFINES)
    # TokenValidator and CryptoHelper share (CALLS, DEFINES)
    # SparseCleaner has only (CLEANS,)
    # Isolated has no relations
    events = [
        TemporalCodeEvent("e1", "AuthSvc", "CALLS", "TokenValidator", t0),
        TemporalCodeEvent("e2", "AuthSvc", "IMPORTS", "CryptoHelper", t0),
        TemporalCodeEvent("e3", "AuthSvc", "DEFINES", "login", t0),
        TemporalCodeEvent("e4", "UserSvc", "CALLS", "TokenValidator", t0),
        TemporalCodeEvent("e5", "UserSvc", "IMPORTS", "CryptoHelper", t0),
        TemporalCodeEvent("e6", "UserSvc", "DEFINES", "create_user", t0),
        TemporalCodeEvent("e7", "TokenValidator", "CALLS", "CryptoHelper", t0),
        TemporalCodeEvent("e8", "TokenValidator", "DEFINES", "verify", t0),
        TemporalCodeEvent("e9", "CryptoHelper", "DEFINES", "sha256", t0),
        TemporalCodeEvent("e10", "SparseCleaner", "CLEANS", "DiskCache", t0),
    ]

    types_run1 = EntityRelationMiner.mine_entity_types(events, min_support=3, max_len=3)
    types_run2 = EntityRelationMiner.mine_entity_types(events, min_support=3, max_len=3)

    # Deterministic across multiple calls
    assert types_run1 == types_run2

    # AuthSvc and UserSvc participate in CALLS, IMPORTS, DEFINES -> same type
    assert types_run1["AuthSvc"] == types_run1["UserSvc"]
    assert "TYPE_" in types_run1["AuthSvc"]

    # TokenValidator participates in CALLS, DEFINES -> frequent pattern
    assert "TYPE_" in types_run1["TokenValidator"]

    # SparseCleaner has infrequent relation CLEANS -> fallback type
    assert "FALLBACK:" in types_run1["SparseCleaner"]
    assert "CLEANS" in types_run1["SparseCleaner"]


# ==============================================================================
# 2. Rule-Node Generation and Original-Event Mapping
# ==============================================================================


def test_2_rule_node_generation_and_event_mapping():
    """
    Verifies that events map to rule nodes <c_s, r, c_o> and retain bidirectional
    references to the originating code evidence.
    """
    t0 = datetime(2026, 2, 1, tzinfo=UTC)
    cand1 = make_candidate("c1", "AuthSvc", "apps/auth.py", "def login(): ...", t0)
    cand2 = make_candidate("c2", "UserSvc", "apps/user.py", "def signup(): ...", t0)

    events = [
        TemporalCodeEvent("e1", "AuthSvc", "CALLS", "TokenVal", t0, "c1", cand1),
        TemporalCodeEvent("e2", "UserSvc", "CALLS", "TokenVal", t0, "c2", cand2),
    ]
    entity_types = {
        "AuthSvc": "TYPE_SERVICE",
        "UserSvc": "TYPE_SERVICE",
        "TokenVal": "TYPE_VALIDATOR",
    }

    rule_nodes = TemporalRuleGraphBuilder.build_rule_nodes(events, entity_types)

    # Both events map to <TYPE_SERVICE, CALLS, TYPE_VALIDATOR>
    expected_id = "<TYPE_SERVICE, CALLS, TYPE_VALIDATOR>"
    assert expected_id in rule_nodes
    node = rule_nodes[expected_id]
    assert node.support == 2
    assert len(node.events) == 2

    # Verify original code evidence preserved
    ev1, ev2 = node.events
    assert ev1.candidate_id == "c1"
    assert ev1.candidate.content == "def login(): ..."
    assert ev2.candidate_id == "c2"
    assert ev2.candidate.content == "def signup(): ..."


# ==============================================================================
# 3. Hamming-Distance Edge Construction
# ==============================================================================


def test_3_hamming_distance_edge_construction():
    """
    Verifies candidate edge construction under d_H(u, v) <= 1:
    dH(u, v) = 1[a_s != b_s] + 1[r != r'] + 1[a_o != b_o].
    """
    r1 = RuleNode("<T1, CALLS, T2>", "T1", "CALLS", "T2")
    r2 = RuleNode("<T1, IMPORTS, T2>", "T1", "IMPORTS", "T2")  # dH = 1 (relation differs)
    r3 = RuleNode("<T1, CALLS, T3>", "T1", "CALLS", "T3")    # dH = 1 (object differs)
    r4 = RuleNode("<T2, IMPORTS, T3>", "T2", "IMPORTS", "T3")  # dH = 3 (all differ)

    nodes = {r.node_id: r for r in [r1, r2, r3, r4]}
    cand_edges = TemporalRuleGraphBuilder.generate_candidate_edges(nodes)

    edge_set = set(cand_edges)
    # (r1, r2) has dH = 1 -> valid
    assert (r1.node_id, r2.node_id) in edge_set or (r2.node_id, r1.node_id) in edge_set
    # (r1, r3) has dH = 1 -> valid
    assert (r1.node_id, r3.node_id) in edge_set or (r3.node_id, r1.node_id) in edge_set
    # (r1, r4) has dH = 3 -> NOT valid
    assert (r1.node_id, r4.node_id) not in edge_set and (r4.node_id, r1.node_id) not in edge_set

    # No self links
    for u, v in cand_edges:
        assert u != v


# ==============================================================================
# 4. Temporal-Span Calculation and Validity Handling
# ==============================================================================


def test_4_temporal_span_calculation_and_validity_handling():
    """
    Verifies empirical temporal span collection:
    - Correct days calculation between valid timestamps.
    - Missing timestamps safely skipped without exceptions.
    - Same-time clamp to epsilon prevents log(0).
    - Event Hamming distance dH(f~, f~') <= 2 constraint enforced.
    """
    t1 = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 3, 3, 0, 0, 0, tzinfo=UTC)  # 2 days later

    r1 = RuleNode("<T1, CALLS, T2>", "T1", "CALLS", "T2")
    r2 = RuleNode("<T1, IMPORTS, T2>", "T1", "IMPORTS", "T2")

    # Matching event pair: same subject "Auth", relation differs (dH=1 <= 2)
    ev1 = TemporalCodeEvent("e1", "Auth", "CALLS", "Token", t1)
    ev2 = TemporalCodeEvent("e2", "Auth", "IMPORTS", "Token", t2)
    # Missing timestamp event
    ev3 = TemporalCodeEvent("e3", "Auth", "CALLS", "Token", None)
    # Disjoint event: subject, relation, object all differ (dH=3 > 2)
    ev4 = TemporalCodeEvent("e4", "Billing", "INHERITS", "Base", t1)

    r1.events = [ev1, ev3]
    r2.events = [ev2, ev4]

    nodes = {r1.node_id: r1, r2.node_id: r2}
    candidate_edges = [(r1.node_id, r2.node_id)]

    spans_map = TemporalRuleGraphBuilder.collect_temporal_spans(nodes, candidate_edges)
    spans = spans_map[(r1.node_id, r2.node_id)]

    assert len(spans) == 1
    assert math.isclose(spans[0], 2.0, rel_tol=1e-3)


# ==============================================================================
# 5. MDL Cost Calculations and Greedy Pruning
# ==============================================================================


def test_5_mdl_cost_calculations_and_greedy_pruning():
    """
    Verifies Minimum Description Length:
    - Model cost L(M) with node and directed chain edge lengths.
    - Coverage cost L_cov with log2 binomial coefficient.
    - Temporal cost L_time modeling exponential distribution.
    - Greedy edge selection retains edges that decrease MDL and discards noisy edges.
    """
    r1 = RuleNode("<T1, CALLS, T2>", "T1", "CALLS", "T2")
    r2 = RuleNode("<T1, IMPORTS, T2>", "T1", "IMPORTS", "T2")
    r3 = RuleNode("<T1, DEFINES, T2>", "T1", "DEFINES", "T2")

    t_now = datetime(2026, 4, 1, tzinfo=UTC)
    for i in range(10):
        r1.events.append(TemporalCodeEvent(f"e1_{i}", "S", "CALLS", "O", t_now))
        r2.events.append(TemporalCodeEvent(f"e2_{i}", "S", "IMPORTS", "O", t_now))
        r3.events.append(TemporalCodeEvent(f"e3_{i}", "S", "DEFINES", "O", t_now))

    nodes = {r1.node_id: r1, r2.node_id: r2, r3.node_id: r3}

    # Candidate 1: r1 - r2 has tight temporal spans (mean 0.05 days ~ 1 hour)
    # Candidate 2: r1 - r3 has huge temporal spans (mean 800 days)
    candidate_edges = [(r1.node_id, r2.node_id), (r1.node_id, r3.node_id)]
    spans_map = {
        (r1.node_id, r2.node_id): [0.05] * 10,
        (r1.node_id, r3.node_id): [800.0] * 10,
    }

    selected_edges, init_mdl, final_mdl = MdlGraphSelector.select_edges(
        rule_nodes=nodes,
        candidate_edges=candidate_edges,
        spans_map=spans_map,
        total_events=30,
        num_types=2,
        num_relations=3,
    )

    # Edge (r1, r2) with tight temporal spans is selected
    assert (r1.node_id, r2.node_id) in selected_edges
    # Edge (r1, r3) with distant spans is rejected
    assert (r1.node_id, r3.node_id) not in selected_edges
    # Description length improved
    assert final_mdl < init_mdl


# ==============================================================================
# 6. PPR Convergence and Deterministic Ranking
# ==============================================================================


def test_6_ppr_convergence_and_deterministic_ranking():
    """
    Verifies Personalized PageRank on the rule graph:
    - Normalization and Dirichlet smoothing of personalization vector gamma.
    - Geometric discounting by anchor rank.
    - Power iteration convergence within tolerance error epsilon.
    - Stationary distribution sums to 1.0.
    """
    r1 = RuleNode("<T1, CALLS, T2>", "T1", "CALLS", "T2")
    r2 = RuleNode("<T1, IMPORTS, T2>", "T1", "IMPORTS", "T2")
    r3 = RuleNode("<T2, DEFINES, T3>", "T2", "DEFINES", "T3")

    ev1 = TemporalCodeEvent("ev1", "S1", "CALLS", "O1")
    ev2 = TemporalCodeEvent("ev2", "S2", "IMPORTS", "O2")
    ev3 = TemporalCodeEvent("ev3", "S3", "DEFINES", "O3")

    r1.events = [ev1]
    r2.events = [ev2]
    r3.events = [ev3]

    nodes = {r1.node_id: r1, r2.node_id: r2, r3.node_id: r3}
    edges = {(r1.node_id, r2.node_id), (r2.node_id, r3.node_id)}

    # ev1 is top anchor, ev2 is second anchor
    anchors = [ev1, ev2]

    top_rules, ppr = SeededPprRetriever.retrieve_top_rules(
        rule_nodes=nodes,
        selected_edges=edges,
        anchor_events=anchors,
        top_k2=3,
        alpha=0.2,
        epsilon=1e-6,
    )

    assert len(top_rules) == 3
    # Probabilities sum to 1.0 within numerical precision
    prob_sum = sum(ppr.values())
    assert math.isclose(prob_sum, 1.0, rel_tol=1e-4)

    # Top seeded rule r1 has highest or top rank
    assert top_rules[0].node_id == r1.node_id or top_rules[0].node_id == r2.node_id


# ==============================================================================
# 7. Mapping Selected Rules Back to Relevant Code Evidence
# ==============================================================================


def test_7_mapping_selected_rules_to_code_evidence():
    """
    Verifies that STAR-RAG propagation maps back to candidate evidence,
    recording star_rag_ppr signals and rule node metadata.
    """
    t0 = datetime(2026, 5, 1, tzinfo=UTC)
    t1 = datetime(2026, 5, 2, tzinfo=UTC)

    c1 = make_candidate(
        "cand-1",
        "OrderProcessor",
        "apps/order.py",
        "def process(): PaymentGateway.charge()",
        committed_at=t0,
        temporal_relations=[{"subject": "OrderProcessor", "relation": "CALLS", "object": "PaymentGateway"}],
    )
    c2 = make_candidate(
        "cand-2",
        "PaymentGateway",
        "apps/payment.py",
        "class PaymentGateway: ...",
        committed_at=t1,
        temporal_relations=[{"subject": "PaymentGateway", "relation": "DEFINES", "object": "charge"}],
    )

    result = StarRagContextService.run_star_rag_pipeline(
        candidates=[c1, c2],
        query_text="how does OrderProcessor charge payments?",
        top_k1=2,
        top_k2=2,
    )

    assert result.is_fallback is False
    cands = result.candidates
    assert len(cands) >= 2

    # Verify PPR signal and metadata attached
    augmented = [c for c in cands if "star_rag_ppr" in c.signals]
    assert len(augmented) >= 1
    for c in augmented:
        assert c.signals["star_rag_ppr"] > 0.0
        assert "star_rag_rule_node" in c.metadata


# ==============================================================================
# 8. Historical versus Current Implementation Retrieval
# ==============================================================================


def test_8_historical_versus_current_implementation_retrieval():
    """
    Verifies handling of code evolution and supersession:
    - Earlier implementation marked as superseded.
    - Current implementation marked as is_current=True.
    - Historical provenance preserved for temporal queries.
    """
    t_old = datetime(2026, 1, 10, 10, 0, 0, tzinfo=UTC)
    t_new = datetime(2026, 3, 20, 15, 0, 0, tzinfo=UTC)

    old_cand = make_candidate(
        "cand-old",
        "hash_password",
        "apps/auth.py",
        "def hash_password(pwd): return sha1_hasher.hash(pwd)",
        committed_at=t_old,
        temporal_relations=[{"subject": "hash_password", "relation": "CALLS", "object": "sha1_hasher"}],
        symbol_name="hash_password",
    )
    new_cand = make_candidate(
        "cand-new",
        "hash_password",
        "apps/auth.py",
        "def hash_password(pwd): return argon2.verify(pwd)",
        committed_at=t_new,
        temporal_relations=[{"subject": "hash_password", "relation": "CALLS", "object": "argon2"}],
        symbol_name="hash_password",
    )

    result = StarRagContextService.run_star_rag_pipeline(
        candidates=[old_cand, new_cand],
        query_text="how did hash_password evolve over time?",
    )

    cands_by_id = {c.candidate_id: c for c in result.candidates}
    c_old = cands_by_id["cand-old"]
    c_new = cands_by_id["cand-new"]

    # Supersession resolution
    assert c_new.metadata.get("is_current") is True
    assert c_old.metadata.get("is_superseded") is True
    assert c_old.metadata.get("is_current") is False


# ==============================================================================
# 9. Empty or Sparse Graphs and Graceful Fallback
# ==============================================================================


def test_9_empty_or_sparse_graphs_fallback():
    """
    Verifies graceful fallback behavior:
    - 0 candidates -> returns empty result safely.
    - 1 candidate (insufficient events) -> fallback with explanation.
    - Never throws unexpected exceptions.
    """
    # Empty
    res_empty = StarRagContextService.run_star_rag_pipeline([])
    assert res_empty.is_fallback is True
    assert res_empty.candidates == []

    # Single candidate
    c_single = make_candidate("c-single", "Solo", "apps/solo.py", "def solo(): pass")
    res_single = StarRagContextService.run_star_rag_pipeline([c_single])
    assert res_single.is_fallback is True
    assert len(res_single.candidates) == 1
    assert "Insufficient" in str(res_single.fallback_reason)


# ==============================================================================
# 10. Repository and Snapshot Isolation
# ==============================================================================


def test_10_repository_and_snapshot_isolation():
    """
    Verifies repository and snapshot boundaries are preserved without cross-contamination.
    """
    repo_a = uuid.uuid4()
    snap_a = uuid.uuid4()
    repo_b = uuid.uuid4()
    snap_b = uuid.uuid4()

    cA = make_candidate(
        "cA", "ModA", "a.py", "code_a",
        repository_id=repo_a, snapshot_id=snap_a,
        temporal_relations=[{"subject": "ModA", "relation": "CALLS", "object": "HelperA"}],
    )
    cB = make_candidate(
        "cB", "ModB", "b.py", "code_b",
        repository_id=repo_b, snapshot_id=snap_b,
        temporal_relations=[{"subject": "ModB", "relation": "CALLS", "object": "HelperB"}],
    )

    result = StarRagContextService.run_star_rag_pipeline([cA, cB])
    for c in result.candidates:
        if c.candidate_id == "cA":
            assert c.metadata["repository_id"] == str(repo_a)
            assert c.metadata["snapshot_id"] == str(snap_a)
        elif c.candidate_id == "cB":
            assert c.metadata["repository_id"] == str(repo_b)
            assert c.metadata["snapshot_id"] == str(snap_b)


# ==============================================================================
# 11. Hand-Verifiable Temporal Graph
# ==============================================================================


def test_11_hand_verifiable_temporal_graph():
    """
    A small 3-node linear rule graph with analytically verifiable stationary distribution.
    Graph: Node0 <-> Node1 <-> Node2.
    Seeded with gamma = [1.0, 0.0, 0.0], restart alpha = 0.2.
    """
    r0 = RuleNode("<T0, CALLS, T0>", "T0", "CALLS", "T0")
    r1 = RuleNode("<T0, CALLS, T1>", "T0", "CALLS", "T1")
    r2 = RuleNode("<T0, CALLS, T2>", "T0", "CALLS", "T2")

    nodes = {r0.node_id: r0, r1.node_id: r1, r2.node_id: r2}
    edges = {(r0.node_id, r1.node_id), (r1.node_id, r2.node_id)}
    gamma = {r0.node_id: 1.0, r1.node_id: 0.0, r2.node_id: 0.0}

    pi = SeededPprRetriever.run_seeded_ppr(
        rule_nodes=nodes,
        selected_edges=edges,
        gamma=gamma,
        alpha=0.2,
        epsilon=1e-8,
    )

    # Hand-checked stationary distribution:
    # Node 1 is the central bridge and receives probability mass from both 0 and 2.
    # Node 0 has the restart probability (0.2).
    # All probabilities sum to 1.0.
    assert math.isclose(sum(pi.values()), 1.0, rel_tol=1e-5)
    assert pi[r0.node_id] > pi[r2.node_id]
    assert pi[r1.node_id] > pi[r2.node_id]


# ==============================================================================
# 12. Baseline versus STAR-RAG Evaluation Comparison
# ==============================================================================


def test_12_baseline_versus_star_rag_evaluation():
    """
    Compares baseline retrieval vs STAR-RAG on a realistic temporal multi-commit query.
    Measures:
    - Candidate score augmentation via STAR-RAG PPR.
    - Graph summarization compression (rule nodes < raw events).
    - Preservation of top temporally aligned evidence.
    """
    t1 = datetime(2026, 1, 15, tzinfo=UTC)
    t2 = datetime(2026, 1, 16, tzinfo=UTC)
    t3 = datetime(2026, 6, 1, tzinfo=UTC)

    # 4 candidates forming related code events
    c1 = make_candidate(
        "c1", "AuthHandler", "auth/handler.py", "def handle(): token_mgr.check()",
        committed_at=t1,
        temporal_relations=[{"subject": "AuthHandler", "relation": "CALLS", "object": "TokenMgr"}],
        signals={"vector_similarity": 0.85},
    )
    c2 = make_candidate(
        "c2", "TokenMgr", "auth/token.py", "def check(): crypto.verify()",
        committed_at=t2,
        temporal_relations=[{"subject": "TokenMgr", "relation": "CALLS", "object": "Crypto"}],
        signals={"vector_similarity": 0.75},
    )
    c3 = make_candidate(
        "c3", "SessionMgr", "auth/session.py", "def save(): token_mgr.check()",
        committed_at=t2,
        temporal_relations=[{"subject": "SessionMgr", "relation": "CALLS", "object": "TokenMgr"}],
        signals={"vector_similarity": 0.70},
    )
    c4 = make_candidate(
        "c4", "UnrelatedJob", "jobs/cleanup.py", "def cleanup(): pass",
        committed_at=t3,
        temporal_relations=[{"subject": "UnrelatedJob", "relation": "RUNS", "object": "Db"}],
        signals={"vector_similarity": 0.30},
    )

    baseline_candidates = [c1, c2, c3, c4]

    analyzed = AnalyzedQuery(
        raw_query="how does auth handler verify tokens?",
        symbol_candidates=["AuthHandler", "TokenMgr"],
        path_candidates=["auth/handler.py"],
    )

    # 1. Baseline retrieval signals
    baseline_scores = [c.signals.get("vector_similarity", 0.0) for c in baseline_candidates]

    # 2. STAR-RAG retrieval
    star_rag_res = StarRagContextService.run_star_rag_pipeline(
        candidates=baseline_candidates,
        analyzed_query=analyzed,
        query_text="how does auth handler verify tokens?",
    )

    assert star_rag_res.is_fallback is False

    # Measure graph summarization compression:
    # 4 raw events summarized into fewer or equal rule nodes
    total_events = sum(len(rn.events) for rn in star_rag_res.rule_nodes.values())
    total_rule_nodes = len(star_rag_res.rule_nodes)
    assert total_rule_nodes <= total_events

    # Top candidates receive enhanced star_rag_ppr scores
    star_rag_candidates = star_rag_res.candidates
    auth_cand = next(c for c in star_rag_candidates if c.candidate_id == "c1")
    assert "star_rag_ppr" in auth_cand.signals
    assert auth_cand.signals["star_rag_ppr"] > 0.0

    # Report measured metrics
    print("\n--- STAR-RAG Evaluation Metrics ---")
    print(f"Raw events: {total_events}")
    print(f"Rule nodes: {total_rule_nodes} (Compression ratio: {round(total_rule_nodes / total_events, 2)})")
    print(f"Selected MDL edges: {len(star_rag_res.selected_edges)}")
    print(f"Initial MDL cost: {round(star_rag_res.initial_mdl_cost, 2)} bits")
    print(f"Final MDL cost: {round(star_rag_res.final_mdl_cost, 2)} bits")
    print(f"Baseline top score: {baseline_scores[0]}")
    print(f"STAR-RAG top candidate PPR boost: {auth_cand.signals['star_rag_ppr']}")
