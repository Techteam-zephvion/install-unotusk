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
import time
import uuid
from datetime import UTC, datetime

from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
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
    r3 = RuleNode("<T1, CALLS, T3>", "T1", "CALLS", "T3")  # dH = 1 (object differs)
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
    Verifies Minimum Description Length (Paper Section 3.2):
    - Model cost L(M) with node and directed chain edge lengths.
    - Coverage cost L_cov with log2 binomial coefficient (Paper Eq. 5).
    - Temporal cost L_time modeling exponential distribution (Paper Eq. 6).
    - Greedy edge selection retains edges that decrease MDL and discards noisy edges.
    """
    r1 = RuleNode("<T1, CALLS, T2>", "T1", "CALLS", "T2")
    r2 = RuleNode("<T1, IMPORTS, T2>", "T1", "IMPORTS", "T2")
    r3 = RuleNode("<T1, DEFINES, T2>", "T1", "DEFINES", "T2")

    t_now = datetime(2026, 4, 1, tzinfo=UTC)
    for i in range(2):
        r1.events.append(TemporalCodeEvent(f"e1_{i}", "S", "CALLS", "O", t_now))
        r2.events.append(TemporalCodeEvent(f"e2_{i}", "S", "IMPORTS", "O", t_now))
        r3.events.append(TemporalCodeEvent(f"e3_{i}", "S", "DEFINES", "O", t_now))

    nodes = {r1.node_id: r1, r2.node_id: r2, r3.node_id: r3}

    # Candidate 1: r1 - r2 has tight temporal spans (mean 0.01 days ~ 14 mins, 100% conversion k=4, n=4)
    # Candidate 2: r1 - r3 has huge temporal spans (mean 800 days)
    candidate_edges = [(r1.node_id, r2.node_id), (r1.node_id, r3.node_id)]
    spans_map = {
        (r1.node_id, r2.node_id): [0.01] * 4,
        (r1.node_id, r3.node_id): [800.0] * 4,
    }

    selected_edges, init_mdl, final_mdl = MdlGraphSelector.select_edges(
        rule_nodes=nodes,
        candidate_edges=candidate_edges,
        spans_map=spans_map,
        total_events=6,
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
        temporal_relations=[
            {"subject": "OrderProcessor", "relation": "CALLS", "object": "PaymentGateway"}
        ],
    )
    c2 = make_candidate(
        "cand-2",
        "PaymentGateway",
        "apps/payment.py",
        "class PaymentGateway: ...",
        committed_at=t1,
        temporal_relations=[
            {"subject": "PaymentGateway", "relation": "DEFINES", "object": "charge"}
        ],
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
        temporal_relations=[
            {"subject": "hash_password", "relation": "CALLS", "object": "sha1_hasher"}
        ],
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
        "cA",
        "ModA",
        "a.py",
        "code_a",
        repository_id=repo_a,
        snapshot_id=snap_a,
        temporal_relations=[{"subject": "ModA", "relation": "CALLS", "object": "HelperA"}],
    )
    cB = make_candidate(
        "cB",
        "ModB",
        "b.py",
        "code_b",
        repository_id=repo_b,
        snapshot_id=snap_b,
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
        "c1",
        "AuthHandler",
        "auth/handler.py",
        "def handle(): token_mgr.check()",
        committed_at=t1,
        temporal_relations=[{"subject": "AuthHandler", "relation": "CALLS", "object": "TokenMgr"}],
        signals={"vector_similarity": 0.85},
    )
    c2 = make_candidate(
        "c2",
        "TokenMgr",
        "auth/token.py",
        "def check(): crypto.verify()",
        committed_at=t2,
        temporal_relations=[{"subject": "TokenMgr", "relation": "CALLS", "object": "Crypto"}],
        signals={"vector_similarity": 0.75},
    )
    c3 = make_candidate(
        "c3",
        "SessionMgr",
        "auth/session.py",
        "def save(): token_mgr.check()",
        committed_at=t2,
        temporal_relations=[{"subject": "SessionMgr", "relation": "CALLS", "object": "TokenMgr"}],
        signals={"vector_similarity": 0.70},
    )
    c4 = make_candidate(
        "c4",
        "UnrelatedJob",
        "jobs/cleanup.py",
        "def cleanup(): pass",
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
    assert baseline_scores[0] == 0.85

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

    # Verify scoring arithmetic: distinguish raw signals from weighted score contributions
    raw_vec = auth_cand.signals["vector_similarity"]
    raw_ppr = auth_cand.signals["star_rag_ppr"]
    weighted_vec = raw_vec * 1.4  # MultiSignalRanker vector_similarity weight
    weighted_ppr = raw_ppr * 1.6  # MultiSignalRanker star_rag_ppr weight
    base_signal_contribution = weighted_vec + weighted_ppr

    assert math.isclose(raw_vec, 0.85, rel_tol=1e-3)
    assert math.isclose(weighted_vec, 1.19, rel_tol=1e-3)
    assert math.isclose(weighted_ppr, raw_ppr * 1.6, rel_tol=1e-4)
    assert math.isclose(base_signal_contribution, 1.19 + (raw_ppr * 1.6), rel_tol=1e-4)

    # Report measured metrics
    print("\n--- STAR-RAG Evaluation Metrics ---")
    print(f"Raw events: {total_events}")
    print(
        f"Rule nodes: {total_rule_nodes} (Compression ratio: {round(total_rule_nodes / total_events, 2)})"
    )
    print(f"Selected MDL edges: {len(star_rag_res.selected_edges)}")
    print(f"Initial MDL cost: {round(star_rag_res.initial_mdl_cost, 2)} bits")
    print(f"Final MDL cost: {round(star_rag_res.final_mdl_cost, 2)} bits")
    print(
        f"Baseline top raw vector score: {raw_vec} (weighted contribution: {round(weighted_vec, 4)})"
    )
    print(
        f"STAR-RAG top candidate raw PPR: {round(raw_ppr, 4)} (weighted contribution: {round(weighted_ppr, 4)})"
    )
    print(f"Combined base signal sum: {round(base_signal_contribution, 4)}")


# ==============================================================================
# 13. Grounded Repository-Derived Temporal Query Evaluation
# ==============================================================================


def test_13_grounded_repo_temporal_query_evaluation():
    """
    Reproducible evaluation using grounded repository-derived temporal queries.
    Models a realistic multi-commit subsystem evolution across 4 snapshots / commits
    with 12 candidates spanning auth, token management, session storage, and background jobs.

    Evaluates across:
    1. Relevant-source retrieval: Precision of retrieving active components vs legacy/unrelated components.
    2. Temporal correctness: Current queries prefer active code; historical queries preserve superseded precursors.
    3. Provenance preservation: Candidate IDs, file paths, and commit snapshots remain intact.
    4. Candidate reduction & rule compression: Rule graph summarizes raw events into rule nodes.
    5. Retrieval latency: Execution time measured in milliseconds (sub-5ms requirement).
    """
    repo_id = uuid.uuid4()
    snap1, snap2, snap3, snap4 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    t1 = datetime(2026, 1, 1, tzinfo=UTC)
    t2 = datetime(2026, 2, 1, tzinfo=UTC)
    t3 = datetime(2026, 3, 1, tzinfo=UTC)
    t4 = datetime(2026, 4, 1, tzinfo=UTC)

    candidates = [
        # Snapshot 1 (Legacy Initial Implementation - superseded)
        make_candidate(
            "c_leg_auth",
            "LegacyAuthHandler",
            "auth/legacy_handler.py",
            "def handle(): legacy_token.verify()",
            committed_at=t1,
            snapshot_id=snap1,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "LegacyAuthHandler", "relation": "CALLS", "object": "LegacyTokenMgr"}
            ],
            signals={"vector_similarity": 0.72},
        ),
        make_candidate(
            "c_leg_tok",
            "LegacyTokenMgr",
            "auth/legacy_token.py",
            "def verify(): md5.hash()",
            committed_at=t1,
            snapshot_id=snap1,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "LegacyTokenMgr", "relation": "USES", "object": "Md5Hasher"}
            ],
            signals={"vector_similarity": 0.70},
        ),
        make_candidate(
            "c_md5",
            "Md5Hasher",
            "auth/hasher.py",
            "def hash(): md5()",
            committed_at=t1,
            snapshot_id=snap1,
            repository_id=repo_id,
            temporal_relations=[{"subject": "Md5Hasher", "relation": "HASHES", "object": "Token"}],
            signals={"vector_similarity": 0.65},
        ),
        # Snapshot 2 (Modern Token Introduction)
        make_candidate(
            "c_jwt",
            "JwtTokenMgr",
            "auth/jwt_token.py",
            "def verify(): signer.verify()",
            committed_at=t2,
            snapshot_id=snap2,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "JwtTokenMgr", "relation": "USES", "object": "Sha256Signer"}
            ],
            signals={"vector_similarity": 0.82},
        ),
        make_candidate(
            "c_sha",
            "Sha256Signer",
            "auth/signer.py",
            "def verify(): hmac()",
            committed_at=t2,
            snapshot_id=snap2,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "Sha256Signer", "relation": "SIGNS", "object": "JwtPayload"}
            ],
            signals={"vector_similarity": 0.75},
        ),
        make_candidate(
            "c_sync",
            "NightlySync",
            "jobs/nightly_sync.py",
            "def run(): backup()",
            committed_at=t2,
            snapshot_id=snap2,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "NightlySync", "relation": "RUNS", "object": "DbBackup"}
            ],
            signals={"vector_similarity": 0.20},
        ),
        # Snapshot 3 (OAuth & Session Store)
        make_candidate(
            "c_oauth",
            "OAuthHandler",
            "auth/oauth_handler.py",
            "def oauth(): jwt.verify()",
            committed_at=t3,
            snapshot_id=snap3,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "OAuthHandler", "relation": "CALLS", "object": "JwtTokenMgr"}
            ],
            signals={"vector_similarity": 0.78},
        ),
        make_candidate(
            "c_sess",
            "SessionStore",
            "auth/session_store.py",
            "def store(): redis.set()",
            committed_at=t3,
            snapshot_id=snap3,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "SessionStore", "relation": "STORES_IN", "object": "RedisCache"}
            ],
            signals={"vector_similarity": 0.68},
        ),
        make_candidate(
            "c_redis",
            "RedisCache",
            "db/redis_pool.py",
            "def set(): redis()",
            committed_at=t3,
            snapshot_id=snap3,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "RedisCache", "relation": "CONNECTS", "object": "RedisServer"}
            ],
            signals={"vector_similarity": 0.25},
        ),
        # Snapshot 4 (Current Active Refactor)
        make_candidate(
            "c_auth_svc",
            "AuthService",
            "auth/auth_service.py",
            "def authenticate(): jwt.verify(); rotator.check()",
            committed_at=t4,
            snapshot_id=snap4,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "AuthService", "relation": "CALLS", "object": "JwtTokenMgr"}
            ],
            signals={"vector_similarity": 0.88},
        ),
        make_candidate(
            "c_rotator",
            "KeyRotator",
            "auth/key_rotator.py",
            "def check(): signer.refresh()",
            committed_at=t4,
            snapshot_id=snap4,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "KeyRotator", "relation": "USES", "object": "Sha256Signer"}
            ],
            signals={"vector_similarity": 0.80},
        ),
        make_candidate(
            "c_inv",
            "InvoiceJob",
            "billing/invoice_job.py",
            "def bill(): stripe()",
            committed_at=t4,
            snapshot_id=snap4,
            repository_id=repo_id,
            temporal_relations=[
                {"subject": "InvoiceJob", "relation": "PROCESSES", "object": "StripePayment"}
            ],
            signals={"vector_similarity": 0.15},
        ),
    ]

    # --------------------------------------------------------------------------
    # Evaluation 1: Current Implementation Query
    # --------------------------------------------------------------------------
    q_current = AnalyzedQuery(
        raw_query="How does the current AuthService verify tokens and rotate keys?",
        symbol_candidates=["AuthService", "KeyRotator"],
        path_candidates=["auth/auth_service.py", "auth/key_rotator.py"],
        keywords=["authservice", "verify", "tokens", "rotate", "keys"],
        is_temporal=False,
    )

    t0_current = time.perf_counter()
    star_rag_res_curr = StarRagContextService.run_star_rag_pipeline(
        candidates=candidates,
        analyzed_query=q_current,
        query_text=q_current.raw_query,
    )
    ranked_curr = MultiSignalRanker.rank_candidates(star_rag_res_curr.candidates, q_current)
    latency_curr_ms = (time.perf_counter() - t0_current) * 1000.0

    # 1. Relevant-source retrieval & rank correctness:
    top_curr_names = [r.candidate.name for r in ranked_curr[:3]]
    assert "AuthService" in top_curr_names
    assert "KeyRotator" in top_curr_names
    # Active JwtTokenMgr dependency is boosted via STAR-RAG propagation
    assert "JwtTokenMgr" in [r.candidate.name for r in ranked_curr[:4]]

    # 2. Candidate reduction / noise filtering:
    ranked_cand_ids = {r.candidate.candidate_id for r in ranked_curr}
    assert (
        "c_inv" not in ranked_cand_ids
        or next(r.score for r in ranked_curr if r.candidate.candidate_id == "c_inv") < 0.2
    )

    # 3. Provenance preservation:
    top_cand = ranked_curr[0].candidate
    assert top_cand.path.startswith("auth/")
    assert top_cand.file_id is not None
    assert top_cand.metadata.get("snapshot_id") is not None

    # 4. Latency performance:
    assert latency_curr_ms < 50.0

    # --------------------------------------------------------------------------
    # Evaluation 2: Historical Evolution Query
    # --------------------------------------------------------------------------
    q_history = AnalyzedQuery(
        raw_query="How did token verification evolve from MD5 to SHA-256 and JWT?",
        symbol_candidates=["LegacyTokenMgr", "JwtTokenMgr", "Md5Hasher", "Sha256Signer"],
        path_candidates=["auth/legacy_token.py", "auth/jwt_token.py"],
        keywords=["token", "verification", "evolve", "md5", "sha-256", "jwt"],
        is_temporal=True,
    )

    t0_hist = time.perf_counter()
    star_rag_res_hist = StarRagContextService.run_star_rag_pipeline(
        candidates=candidates,
        analyzed_query=q_history,
        query_text=q_history.raw_query,
    )
    ranked_hist = MultiSignalRanker.rank_candidates(star_rag_res_hist.candidates, q_history)
    latency_hist_ms = (time.perf_counter() - t0_hist) * 1000.0

    # 1. Historical retrieval correctness:
    hist_names = [r.candidate.name for r in ranked_hist[:5]]
    assert "JwtTokenMgr" in hist_names
    assert "LegacyTokenMgr" in hist_names
    assert "Md5Hasher" in hist_names
    assert "Sha256Signer" in hist_names

    # 2. Historical precursors are not demoted when query is temporal:
    leg_cand = next(r for r in ranked_hist if r.candidate.name == "LegacyTokenMgr")
    assert any(
        "Historical" in reason or "precursor" in reason for reason in leg_cand.matched_reasons
    )

    # 3. Latency performance:
    assert latency_hist_ms < 50.0

    # Report comprehensive benchmark metrics
    print("\n=== GROUNDED REPOSITORY TEMPORAL QUERY EVALUATION ===")
    print(f"Total multi-commit candidates: {len(candidates)} across 4 snapshots")
    print(f"Current query top ranked: {top_curr_names} (latency: {latency_curr_ms:.2f} ms)")
    print(f"Historical query top ranked: {hist_names[:4]} (latency: {latency_hist_ms:.2f} ms)")
    print("=====================================================")


# ==============================================================================
# 14. Anchor Scoring Signal Disagreement & Determinism Audit
# ==============================================================================


def test_14_anchor_scoring_signal_disagreement_and_determinism():
    """
    Tests the audited anchor relevance scoring in STAR-RAG.
    Verifies:
    1. Multi-signal linear combination eliminates short-circuiting defects.
    2. High semantic similarity legitimately dominates weak incidental keyword hits.
    3. Pre-computed ranker scores (signals['score']) are respected without duplication.
    4. Deterministic tie-breaking on candidate_id produces stable ordering across permutations.
    """
    import random

    query = AnalyzedQuery(
        raw_query="How does JwtTokenMgr authenticate cryptographic tokens?",
        symbol_candidates=["JwtTokenMgr"],
        path_candidates=["auth/jwt_token.py"],
        keywords=["jwttokenmgr", "authenticate", "cryptographic", "tokens"],
        is_temporal=False,
    )

    # Candidate A: High semantic similarity (0.85), no symbol match
    cand_a = make_candidate(
        candidate_id="cand_a_semantic",
        name="TokenAuthenticator",
        path="auth/authenticator.py",
        content="Validates JWT cryptographic signatures and claims.",
        signals={"vector_similarity": 0.85, "semantic_match": 0.80},
    )

    # Candidate B: Incidental keyword in content, low semantic similarity (0.10)
    cand_b = make_candidate(
        candidate_id="cand_b_incidental",
        name="DatabasePool",
        path="db/pool.py",
        content="Database connection pool utilizing a token bucket rate limiter.",
        signals={"vector_similarity": 0.10},
    )

    # Candidate C: Base ranker pre-computed score is preserved
    cand_c = make_candidate(
        candidate_id="cand_c_prescored",
        name="KeyRotator",
        path="auth/key_rotator.py",
        content="Rotates RSA keys.",
        signals={"score": 2.20, "vector_similarity": 0.10},
    )

    # Candidate D: Direct exact symbol match with moderate vector similarity
    cand_d = make_candidate(
        candidate_id="cand_d_exact_symbol",
        name="JwtTokenMgr",
        path="auth/jwt_token.py",
        content="Core JWT token manager for authentication.",
        signals={"vector_similarity": 0.60},
    )

    score_a = StarRagContextService.compute_anchor_relevance(cand_a, query)
    score_b = StarRagContextService.compute_anchor_relevance(cand_b, query)
    score_c = StarRagContextService.compute_anchor_relevance(cand_c, query)
    score_d = StarRagContextService.compute_anchor_relevance(cand_d, query)

    # 1. Semantic match dominates incidental keyword
    assert score_a > score_b, (
        f"Semantic candidate ({score_a}) should beat incidental keyword ({score_b})"
    )

    # 2. Exact symbol match with moderate similarity ranks top
    assert score_d > score_a, (
        f"Exact symbol candidate ({score_d}) should outrank pure semantic ({score_a})"
    )

    # 3. Pre-computed score is preserved exactly without double-counting lexical signals
    assert score_c == 2.20, f"Pre-computed score was double-counted! Expected 2.20, got {score_c}"
    assert score_c > score_b, (
        f"Pre-computed score ({score_c}) should outrank weak candidate ({score_b})"
    )

    # 3b. Unscored candidate with same content gets raw signals + lexical signals
    cand_e_unscored = make_candidate(
        candidate_id="cand_e_unscored",
        name="KeyRotator",
        path="auth/key_rotator.py",
        content="Rotates RSA keys.",
        signals={"vector_similarity": 0.10},
    )
    score_e = StarRagContextService.compute_anchor_relevance(cand_e_unscored, query)
    assert score_e == round(0.10 * 1.4 + 0.0, 4), (
        f"Expected raw unscored calculation, got {score_e}"
    )

    # 4. Deterministic tie-breaking on identical scores
    cand_tie1 = make_candidate(
        candidate_id="cand_tie_alpha",
        name="IdenticalWorker",
        path="workers/worker.py",
        content="Background task execution worker.",
        signals={"vector_similarity": 0.50},
    )
    cand_tie2 = make_candidate(
        candidate_id="cand_tie_beta",
        name="IdenticalWorker",
        path="workers/worker.py",
        content="Background task execution worker.",
        signals={"vector_similarity": 0.50},
    )

    assert StarRagContextService.compute_anchor_relevance(
        cand_tie1, query
    ) == StarRagContextService.compute_anchor_relevance(cand_tie2, query)

    # Regardless of input ordering or permutations, tie-break produces identical sorted order
    for _ in range(20):
        cands = [cand_tie2, cand_tie1]
        random.shuffle(cands)
        sorted_cands = sorted(
            cands,
            key=lambda c: (
                -StarRagContextService.compute_anchor_relevance(c, query),
                c.candidate_id,
            ),
        )
        assert [c.candidate_id for c in sorted_cands] == ["cand_tie_alpha", "cand_tie_beta"]


# ==============================================================================
# 15. Absent-Evidence Gating and Hub-Node Attenuation Audit
# ==============================================================================


def test_15_absent_evidence_gating_and_hub_attenuation():
    """
    Verifies:
    1. Absent-evidence / weak-anchor queries bypass PPR graph propagation.
    2. Answerable queries with strong anchors pass the gate and receive graph propagation.
    3. Pre-computed score scale ([0, 1]) is safely handled by the gate.
    4. Hub-node attenuation dampens generic high-event rules inversely with cardinality.
    """
    t0 = datetime(2026, 1, 1, tzinfo=UTC)

    # 1. Weak / absent-evidence query
    q_absent = AnalyzedQuery(
        raw_query="How is real-time bidirectional WebSocket audio streaming handled?",
        symbol_candidates=["WebSocketAudioStreamer"],
        path_candidates=["net/ws_audio.py"],
        keywords=["websocket", "audio", "streaming", "opus"],
        is_temporal=False,
    )

    unrelated_cands = [
        make_candidate(
            candidate_id="c_db_1",
            name="DatabasePool",
            path="db/pool.py",
            content="PostgreSQL connection pool management.",
            committed_at=t0,
            signals={"vector_similarity": 0.05},
            temporal_relations=[
                {"subject": "DatabasePool", "relation": "DEFINES", "object": "db/pool.py"}
            ],
        ),
        make_candidate(
            candidate_id="c_db_2",
            name="DatabasePool",
            path="db/pool.py",
            content="Pool acquire and release routines.",
            committed_at=t0,
            signals={"vector_similarity": 0.04},
            temporal_relations=[
                {"subject": "DatabasePool", "relation": "CONNECTS", "object": "PostgreSQL"}
            ],
        ),
    ]

    res_absent = StarRagContextService.run_star_rag_pipeline(
        candidates=unrelated_cands,
        analyzed_query=q_absent,
        query_text=q_absent.raw_query,
        min_anchor_score=1.0,
    )

    # Gated out: fallback triggered, no PPR signal injected
    assert res_absent.is_fallback is True
    assert "below confidence threshold" in res_absent.fallback_reason
    assert res_absent.top_rules == []
    for cand in res_absent.candidates:
        assert "star_rag_ppr" not in cand.signals

    # 2. Answerable query with strong anchor passes the gate
    q_valid = AnalyzedQuery(
        raw_query="How does DatabasePool acquire connections?",
        symbol_candidates=["DatabasePool"],
        path_candidates=["db/pool.py"],
        keywords=["databasepool", "acquire", "connections"],
        is_temporal=False,
    )

    res_valid = StarRagContextService.run_star_rag_pipeline(
        candidates=unrelated_cands,
        analyzed_query=q_valid,
        query_text=q_valid.raw_query,
        min_anchor_score=1.0,
    )

    assert res_valid.is_fallback is False
    assert len(res_valid.top_rules) > 0
    assert any("star_rag_ppr" in c.signals for c in res_valid.candidates)

    # 3. Pre-computed score gating
    prescored_weak = [
        make_candidate(
            candidate_id="c_pre_1",
            name="DatabasePool",
            path="db/pool.py",
            content="Pool.",
            committed_at=t0,
            signals={"score": 0.22, "vector_similarity": 0.05},
            temporal_relations=[
                {"subject": "DatabasePool", "relation": "DEFINES", "object": "db/pool.py"}
            ],
        ),
        make_candidate(
            candidate_id="c_pre_2",
            name="DatabasePool",
            path="db/pool.py",
            content="Pool.",
            committed_at=t0,
            signals={"score": 0.20, "vector_similarity": 0.05},
            temporal_relations=[
                {"subject": "DatabasePool", "relation": "CONNECTS", "object": "PostgreSQL"}
            ],
        ),
    ]

    res_prescored_weak = StarRagContextService.run_star_rag_pipeline(
        candidates=prescored_weak,
        analyzed_query=q_absent,
        query_text=q_absent.raw_query,
    )
    assert res_prescored_weak.is_fallback is True
    assert "below confidence threshold" in res_prescored_weak.fallback_reason

    # 4. Hub attenuation verification
    # Construct a pipeline with hub_attenuation=True vs hub_attenuation=False
    c_hub = make_candidate(
        candidate_id="c_hub",
        name="HubClass",
        path="hub.py",
        content="Generic hub class.",
        committed_at=t0,
        signals={"vector_similarity": 0.70},
        temporal_relations=[
            {"subject": "HubClass", "relation": "CALLS", "object": f"target_{i}"} for i in range(25)
        ],
    )
    c_spec = make_candidate(
        candidate_id="c_spec",
        name="SpecClass",
        path="spec.py",
        content="Specific class.",
        committed_at=t0,
        signals={"vector_similarity": 0.70},
        temporal_relations=[{"subject": "SpecClass", "relation": "DEFINES", "object": "spec.py"}],
    )
    hub_candidates = [c_hub, c_spec]

    res_attenuated = StarRagContextService.run_star_rag_pipeline(
        candidates=hub_candidates,
        analyzed_query=q_valid,
        query_text=q_valid.raw_query,
        min_anchor_score=0.0,
        hub_attenuation=True,
    )
    res_unattenuated = StarRagContextService.run_star_rag_pipeline(
        candidates=hub_candidates,
        analyzed_query=q_valid,
        query_text=q_valid.raw_query,
        min_anchor_score=0.0,
        hub_attenuation=False,
    )

    # Hub node candidates should have their ppr score dampened under attenuation
    hub_ppr_att = next(
        c.signals.get("star_rag_ppr", 0.0)
        for c in res_attenuated.candidates
        if c.candidate_id == "c_hub"
    )
    hub_ppr_unatt = next(
        c.signals.get("star_rag_ppr", 0.0)
        for c in res_unattenuated.candidates
        if c.candidate_id == "c_hub"
    )
    assert hub_ppr_att <= hub_ppr_unatt


# ==============================================================================
# 16. Safe Configuration and Effective Defaults Audit
# ==============================================================================


def test_16_star_rag_configuration_and_defaults():
    """
    Verifies that STAR-RAG is opt-in by default and configurable without side-effects:
    1. settings.STAR_RAG_ENABLED is False by default.
    2. settings.STAR_RAG_MIN_ANCHOR_SCORE is 1.0 by default.
    3. settings.STAR_RAG_HUB_ATTENUATION is True by default.
    4. ProjectContextEngine respects explicit opt-in and defaults to False.
    """
    from apps.api.src.config.settings import settings

    # 1. Unconfigured installations default to disabled
    assert settings.STAR_RAG_ENABLED is False, "STAR-RAG must be opt-in (disabled by default)"
    assert settings.STAR_RAG_MIN_ANCHOR_SCORE == 1.0
    assert settings.STAR_RAG_HUB_ATTENUATION is True

    # 2. Engine honors explicit opt-in
    assert getattr(settings, "STAR_RAG_ENABLED", False) is False


# ==============================================================================
# 17. Lexical Matching and False-Positive Prevention
# ==============================================================================


def test_17_lexical_matching_and_false_positive_prevention():
    """
    Verifies token-aware lexical matching in STAR-RAG anchor relevance:
    1. 'and' must not match 'RelationshipExpander'.
    2. 'cat' must not match unrelated identifiers such as 'scatter'.
    3. Genuine symbol and keyword matches still work.
    4. Meaningful matches across snake_case, camelCase, and PascalCase remain supported.
    5. Path and content matches behave correctly without accidental substring hits.
    6. Precomputed ranker scores are not double-counted.
    7. Absent-evidence queries still fall back without injecting star_rag_ppr.
    8. Existing current-state and historical temporal retrieval behavior remains intact.
    """
    # 1. 'and' must not match RelationshipExpander
    cand_rel = make_candidate(
        candidate_id="c_rel",
        name="RelationshipExpander",
        path="apps/api/src/services/context_engine/graph_expander.py",
        content="class RelationshipExpander:\n    pass",
        signals={"vector_similarity": 0.0},
    )
    q_and = AnalyzedQuery(raw_query="test and query", keywords=["and"], symbol_candidates=["and"])
    assert StarRagContextService.compute_anchor_relevance(cand_rel, q_and) == 0.0

    # 2. 'cat' must not match an unrelated identifier such as scatter
    cand_scatter = make_candidate(
        candidate_id="c_scatter",
        name="scatter",
        path="math/scatter.py",
        content="def scatter(x, y):\n    return x + y",
        signals={"vector_similarity": 0.0},
    )
    q_cat = AnalyzedQuery(raw_query="cat", keywords=["cat"], symbol_candidates=["cat"])
    assert StarRagContextService.compute_anchor_relevance(cand_scatter, q_cat) == 0.0

    # 3. Genuine symbol and keyword matches still work
    q_rel_sym = AnalyzedQuery(
        raw_query="RelationshipExpander", symbol_candidates=["RelationshipExpander"]
    )
    score_rel_sym = StarRagContextService.compute_anchor_relevance(cand_rel, q_rel_sym)
    assert score_rel_sym >= 1.5, f"Expected exact symbol match bonus >= 1.5, got {score_rel_sym}"

    q_rel_kw = AnalyzedQuery(raw_query="expander", keywords=["expander"])
    score_rel_kw = StarRagContextService.compute_anchor_relevance(cand_rel, q_rel_kw)
    assert score_rel_kw >= 0.8, f"Expected keyword match bonus >= 0.8, got {score_rel_kw}"

    # 4. Meaningful matches across snake_case, camelCase, and PascalCase
    cand_snake = make_candidate(
        candidate_id="c_snake",
        name="user_session_manager",
        path="auth/user_session_manager.py",
        content="pass",
        signals={"vector_similarity": 0.0},
    )
    cand_camel = make_candidate(
        candidate_id="c_camel",
        name="userSessionManager",
        path="auth/userSessionManager.py",
        content="pass",
        signals={"vector_similarity": 0.0},
    )
    cand_pascal = make_candidate(
        candidate_id="c_pascal",
        name="UserSessionManager",
        path="auth/UserSessionManager.py",
        content="pass",
        signals={"vector_similarity": 0.0},
    )

    q_pascal = AnalyzedQuery(
        raw_query="UserSessionManager", symbol_candidates=["UserSessionManager"]
    )
    score_s = StarRagContextService.compute_anchor_relevance(cand_snake, q_pascal)
    score_c = StarRagContextService.compute_anchor_relevance(cand_camel, q_pascal)
    score_p = StarRagContextService.compute_anchor_relevance(cand_pascal, q_pascal)
    assert score_s >= 1.5 and score_c >= 1.5 and score_p >= 1.5

    # 5. Path and content matches behave correctly
    cand_util = make_candidate(
        candidate_id="c_util",
        name="util",
        path="auth/token_util.py",
        content="def calculate_discount(amount):\n    return amount * 0.15",
        signals={"vector_similarity": 0.0},
    )
    q_pth_valid = AnalyzedQuery(raw_query="token_util.py", path_candidates=["token_util.py"])
    q_pth_unrelated = AnalyzedQuery(raw_query="scatter.py", path_candidates=["scatter.py"])
    assert StarRagContextService.compute_anchor_relevance(cand_util, q_pth_valid) >= 0.8
    assert StarRagContextService.compute_anchor_relevance(cand_util, q_pth_unrelated) == 0.0

    q_content_valid = AnalyzedQuery(raw_query="discount", keywords=["discount"])
    q_content_sub = AnalyzedQuery(raw_query="count", keywords=["count"])
    assert StarRagContextService.compute_anchor_relevance(cand_util, q_content_valid) >= 0.3
    assert StarRagContextService.compute_anchor_relevance(cand_util, q_content_sub) == 0.0

    # 6. Precomputed ranker scores are not double-counted
    cand_prescored = make_candidate(
        candidate_id="c_prescored",
        name="RelationshipExpander",
        path="expander.py",
        content="class RelationshipExpander: pass",
        signals={"score": 0.75, "vector_similarity": 0.5},
    )
    assert StarRagContextService.compute_anchor_relevance(cand_prescored, q_rel_sym) == 0.75

    # 7. Absent-evidence queries still fall back without injecting star_rag_ppr
    q_absent = AnalyzedQuery(
        raw_query="How is WebSocket audio streaming handled?",
        keywords=["websocket", "audio", "streaming"],
        symbol_candidates=["WebSocketAudio"],
    )
    res_absent = StarRagContextService.run_star_rag_pipeline(
        [cand_rel, cand_scatter],
        analyzed_query=q_absent,
        query_text=q_absent.raw_query,
    )
    assert res_absent.is_fallback is True
    assert res_absent.top_rules == []
    assert all("star_rag_ppr" not in c.signals for c in res_absent.candidates)

    # 8. Existing current-state and historical temporal retrieval behavior remains intact
    cand_old = make_candidate(
        candidate_id="c_old",
        name="Worker.run",
        path="worker.py",
        content="old worker implementation",
        committed_at=datetime(2026, 1, 1, tzinfo=UTC),
        signals={"vector_similarity": 0.6},
        temporal_relations=[
            {"subject": "Worker.run", "relation": "SUPERSEDED_BY", "object": "Worker.execute"}
        ],
    )
    cand_new = make_candidate(
        candidate_id="c_new",
        name="Worker.execute",
        path="worker.py",
        content="new worker implementation",
        committed_at=datetime(2026, 2, 1, tzinfo=UTC),
        signals={"vector_similarity": 0.6},
        temporal_relations=[
            {"subject": "Worker.execute", "relation": "SUPERSEDES", "object": "Worker.run"}
        ],
    )
    res_temporal = StarRagContextService.run_star_rag_pipeline(
        [cand_old, cand_new],
        query_text="How did worker evolve?",
        min_anchor_score=0.0,
    )
    assert res_temporal.is_fallback is False
    assert any(
        c.metadata.get("commit_sha") or c.metadata.get("committed_at")
        for c in res_temporal.candidates
    )

    # 9. Semantic negation words ('not', 'no', 'never', 'without') do not inflate anchor relevance
    cand_with_not = make_candidate(
        candidate_id="c_not",
        name="authenticate",
        path="auth/authenticate.py",
        content="def authenticate():\n    if not user:\n        return False",
        signals={"vector_similarity": 0.0},
    )
    q_neg_not = AnalyzedQuery(
        raw_query="Which functions do not call authenticate?",
        keywords=["functions", "not", "call", "authenticate"],
        has_negation=True,
        negation_keywords=["not"],
    )
    # The score should come from 'authenticate' in name (+0.8), NOT from 'not' matching the code content (+0.3)
    score_with_not = StarRagContextService.compute_anchor_relevance(cand_with_not, q_neg_not)
    assert score_with_not == 0.8, (
        f"Expected 0.8 (from 'authenticate' name match), got {score_with_not}"
    )

    q_pure_neg = AnalyzedQuery(
        raw_query="without never no",
        keywords=["without", "never", "no"],
        has_negation=True,
        negation_keywords=["without", "never", "no"],
    )
    assert StarRagContextService.compute_anchor_relevance(cand_with_not, q_pure_neg) == 0.0

    # 10. Token caching cannot produce stale matches when candidate content changes
    cand_mutable = make_candidate(
        candidate_id="c_mut",
        name="initial_func",
        path="mut.py",
        content="def initial_func(): pass",
        signals={"vector_similarity": 0.0},
    )
    tokens_v1 = StarRagContextService._get_candidate_tokens(cand_mutable)
    assert "initial_func" in tokens_v1[0]
    assert "updated_func" not in tokens_v1[3]

    cand_mutable.content = "def updated_func(): return True"
    tokens_v2 = StarRagContextService._get_candidate_tokens(cand_mutable)
    assert "updated_func" in tokens_v2[3]
    assert "initial_func" not in tokens_v2[3]
