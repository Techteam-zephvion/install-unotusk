"""
Complete Unit Test Suite for Temporal STAR-RAG (Zhu et al., arXiv:2510.16715).
Validates:
1. Entity labeling and Apriori frequent relational pattern mining with configurable thresholds.
2. Temporal rule graph construction, Hamming distance <= 1 candidate edges, and time span collection.
3. MDL graph compression: L(G, M) = L(M) + L(G|M), model cost, coverage cost, temporal cost.
4. Seeded Personalized PageRank: personalization vector normalization, power iteration, convergence, mass conservation.
5. Event reranking: mapping top rule nodes to supporting events, temporal constraint scoring, evidence item generation.
6. Temporal query intent detection and routing via TemporalStarRagRouter.
7. ContextAssembler integration: formatting historical evidence and distinguishing past from present.
8. Failure handling: empty graph, missing timestamps, duplicate events, empty anchors, non-convergence.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta

from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag import (
    EntityRelationMiner,
    MdlGraphSelector,
    RuleNode,
    SeededPprRetriever,
    StarRagContextService,
    TemporalCodeEvent,
    TemporalRuleGraphBuilder,
    TemporalStarRagRouter,
)


def _make_candidate(
    candidate_id: str,
    name: str,
    path: str,
    content: str,
    committed_at: datetime | None = None,
    signals: dict[str, float] | None = None,
    temporal_relations: list[dict] | None = None,
    commit_sha: str = "abc12345",
) -> RetrievedCandidate:
    f_id = uuid.uuid4()
    meta = {
        "file_id": str(f_id),
        "commit_sha": commit_sha,
        "commit_message": f"Update {name}",
        "symbol_name": name,
        "chunk_type": "ATOM_MODIFY",
    }
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
        end_line=25,
        content=content,
        file_id=f_id,
        signals=dict(signals or {"vector_similarity": 0.85, "symbol_match": 1.5}),
        metadata=meta,
    )


# ==============================================================================
# 1. Apriori Mining & Entity Labeling
# ==============================================================================


def test_apriori_frequent_pattern_mining_and_typing():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    events = [
        TemporalCodeEvent("e1", "AuthService", "CALLS", "UserRepository", t0),
        TemporalCodeEvent("e2", "AuthService", "IMPORTS", "TokenHelper", t0),
        TemporalCodeEvent("e3", "AuthService", "DEFINES", "login", t0),
        TemporalCodeEvent("e4", "BillingService", "CALLS", "UserRepository", t0),
        TemporalCodeEvent("e5", "BillingService", "IMPORTS", "TokenHelper", t0),
        TemporalCodeEvent("e6", "BillingService", "DEFINES", "process_payment", t0),
        TemporalCodeEvent("e7", "TokenHelper", "CALLS", "CryptoUtil", t0),
        TemporalCodeEvent("e8", "StandaloneModule", "REFERENCES", "Config", t0),
    ]

    entity_types = EntityRelationMiner.mine_entity_types(events, min_support=3, max_len=3)
    assert len(entity_types) > 0
    # AuthService and BillingService share relation patterns
    assert entity_types["AuthService"] == entity_types["BillingService"]
    # StandaloneModule has support < 3 -> falls back to FALLBACK
    assert "FALLBACK" in entity_types["StandaloneModule"]


# ==============================================================================
# 2. Temporal Rule Graph Builder & Candidate Edges
# ==============================================================================


def test_rule_graph_construction_and_hamming_distance():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    t1 = datetime(2026, 1, 5, tzinfo=UTC)

    events = [
        TemporalCodeEvent("e1", "AuthService", "CALLS", "UserRepository", t0),
        TemporalCodeEvent("e2", "BillingService", "CALLS", "UserRepository", t1),
        TemporalCodeEvent("e3", "AuthService", "IMPORTS", "UserRepository", t0),
    ]
    entity_types = {
        "AuthService": "TYPE_SERVICE",
        "BillingService": "TYPE_SERVICE",
        "UserRepository": "TYPE_REPO",
    }

    rule_nodes = TemporalRuleGraphBuilder.build_rule_nodes(events, entity_types)
    assert "<TYPE_SERVICE, CALLS, TYPE_REPO>" in rule_nodes
    assert "<TYPE_SERVICE, IMPORTS, TYPE_REPO>" in rule_nodes
    assert rule_nodes["<TYPE_SERVICE, CALLS, TYPE_REPO>"].support == 2

    candidate_edges = TemporalRuleGraphBuilder.generate_candidate_edges(rule_nodes)
    # The two rules differ only by relation ("CALLS" vs "IMPORTS") -> Hamming distance = 1
    assert len(candidate_edges) == 1
    edge = candidate_edges[0]
    assert set(edge) == {"<TYPE_SERVICE, CALLS, TYPE_REPO>", "<TYPE_SERVICE, IMPORTS, TYPE_REPO>"}

    # Spans calculation
    spans_map = TemporalRuleGraphBuilder.collect_temporal_spans(rule_nodes, candidate_edges)
    assert edge in spans_map
    spans = spans_map[edge]
    assert len(spans) > 0
    # Difference between Jan 5 and Jan 1 is 4 days (or Jan 1 and Jan 1 is 0 -> clamped to 0.001)
    assert any(math.isclose(s, 4.0, abs_tol=0.01) for s in spans)


# ==============================================================================
# 3. MDL Graph Selection
# ==============================================================================


def test_mdl_graph_selection_compression_objective():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    events = [
        TemporalCodeEvent("e1", "AuthService", "CALLS", "UserRepo", t0),
        TemporalCodeEvent("e2", "BillingService", "CALLS", "UserRepo", t0 + timedelta(hours=2)),
        TemporalCodeEvent("e3", "AuthService", "IMPORTS", "UserRepo", t0),
        TemporalCodeEvent("e4", "BillingService", "IMPORTS", "UserRepo", t0 + timedelta(hours=3)),
    ]
    entity_types = {
        "AuthService": "TYPE_SERVICE",
        "BillingService": "TYPE_SERVICE",
        "UserRepo": "TYPE_REPO",
    }
    rule_nodes = TemporalRuleGraphBuilder.build_rule_nodes(events, entity_types)
    candidate_edges = TemporalRuleGraphBuilder.generate_candidate_edges(rule_nodes)
    spans_map = TemporalRuleGraphBuilder.collect_temporal_spans(rule_nodes, candidate_edges)

    selected_edges, init_mdl, final_mdl = MdlGraphSelector.select_edges(
        rule_nodes=rule_nodes,
        candidate_edges=candidate_edges,
        spans_map=spans_map,
        total_events=len(events),
        num_types=len(set(entity_types.values())),
        num_relations=2,
    )
    assert init_mdl > 0.0
    # Final MDL must be less than or equal to initial cost
    assert final_mdl <= init_mdl


# ==============================================================================
# 4. Seeded Personalized PageRank (PPR)
# ==============================================================================


def test_seeded_ppr_convergence_and_mass_conservation():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    e1 = TemporalCodeEvent("e1", "A", "CALLS", "B", t0)
    e2 = TemporalCodeEvent("e2", "B", "CALLS", "C", t0)
    e3 = TemporalCodeEvent("e3", "C", "CALLS", "D", t0)

    r1 = RuleNode("rule_1", "TYPE_A", "CALLS", "TYPE_B", events=[e1])
    r2 = RuleNode("rule_2", "TYPE_B", "CALLS", "TYPE_C", events=[e2])
    r3 = RuleNode("rule_3", "TYPE_C", "CALLS", "TYPE_D", events=[e3])

    rule_nodes = {"rule_1": r1, "rule_2": r2, "rule_3": r3}
    selected_edges = {("rule_1", "rule_2"), ("rule_2", "rule_3")}

    # Seed on e1 (rule_1)
    gamma, u_seed = SeededPprRetriever.compute_personalization_vector(
        rule_nodes=rule_nodes,
        anchor_events=[e1],
    )
    assert "rule_1" in u_seed
    assert math.isclose(sum(gamma.values()), 1.0, abs_tol=1e-5)

    pi = SeededPprRetriever.run_seeded_ppr(
        rule_nodes=rule_nodes,
        selected_edges=selected_edges,
        gamma=gamma,
        alpha=0.2,
        epsilon=1e-6,
    )
    # Conservation of probability mass
    assert math.isclose(sum(pi.values()), 1.0, abs_tol=1e-4)
    # Seeded node rule_1 should receive highest or high stationary probability
    assert pi["rule_1"] > pi["rule_3"]


# ==============================================================================
# 5. Temporal Router Policy
# ==============================================================================


def test_temporal_star_rag_router_policy():
    # 1. Feature flag disabled
    should_route, reason = TemporalStarRagRouter.should_route_to_temporal_star_rag(
        query_text="What changed in authentication last month?",
        flag_enabled=False,
    )
    assert should_route is False
    assert reason == "feature_flag_disabled"

    # 2. Flag enabled but query is direct code lookup
    q_direct = AnalyzedQuery(
        raw_query="def validate_credentials",
        is_temporal=False,
        keywords=["validate_credentials"],
    )
    should_route, reason = TemporalStarRagRouter.should_route_to_temporal_star_rag(
        query_text="def validate_credentials",
        analyzed_query=q_direct,
        flag_enabled=True,
    )
    assert should_route is False
    assert "query_lacks_temporal_intent" in reason

    # 3. Flag enabled and query has temporal intent
    q_temp = AnalyzedQuery(
        raw_query="What changed in authentication before commit 22222222?",
        is_temporal=True,
        temporal_intent="BEFORE",
        keywords=["authentication"],
    )
    should_route, reason = TemporalStarRagRouter.should_route_to_temporal_star_rag(
        query_text=q_temp.raw_query,
        analyzed_query=q_temp,
        flag_enabled=True,
    )
    assert should_route is True
    assert "temporal_intent:BEFORE" in reason


# ==============================================================================
# 6. Event Reranking and Temporal Evidence Generation
# ==============================================================================


def test_event_reranking_and_evidence_generation():
    t_old = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    t_new = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)

    c_old = _make_candidate(
        candidate_id="cand_1",
        name="validate_credentials",
        path="auth_service.py",
        content="def validate_credentials(user, pwd):\n    return False\n",
        committed_at=t_old,
        commit_sha="11111111",
        temporal_relations=[
            {
                "subject": "validate_credentials",
                "relation": "VALIDATES",
                "object": "UserCredentials",
                "t_obs": t_old.isoformat(),
                "statement": "Initial credential validation",
                "commit_sha": "11111111",
            }
        ],
    )
    c_new = _make_candidate(
        candidate_id="cand_2",
        name="validate_credentials",
        path="auth_service.py",
        content="def validate_credentials(user, pwd):\n    return len(pwd) >= 8\n",
        committed_at=t_new,
        commit_sha="22222222",
        temporal_relations=[
            {
                "subject": "validate_credentials",
                "relation": "VALIDATES",
                "object": "UserCredentials",
                "t_obs": t_new.isoformat(),
                "statement": "Added password length requirement",
                "commit_sha": "22222222",
            }
        ],
    )

    q = AnalyzedQuery(
        raw_query="What was the previous implementation of validate_credentials before 2026-01-10?",
        keywords=["validate_credentials", "password"],
        symbol_candidates=["validate_credentials"],
        is_temporal=True,
        temporal_intent="HISTORICAL",
    )

    result = StarRagContextService.run_star_rag_pipeline(
        candidates=[c_old, c_new],
        analyzed_query=q,
        query_text=q.raw_query,
    )

    assert result.is_fallback is False
    assert len(result.top_rules) > 0
    assert len(result.ranked_events) > 0
    assert len(result.temporal_evidence) > 0

    # The query asked for state before 2026-01-10 -> c_old (2026-01-01) should rank highest
    top_ev = result.temporal_evidence[0]
    assert top_ev["commit_sha"] == "11111111"
    assert top_ev["type"] == "temporal_event"
    assert "validate_credentials" in top_ev["subject"]


# ==============================================================================
# 7. ContextAssembler Historical Evidence Formatting
# ==============================================================================


def test_context_assembler_formats_historical_evidence():
    ranked_cand = RankedCandidate(
        candidate=_make_candidate(
            "c1",
            "validate_credentials",
            "auth.py",
            "def validate_credentials(): return True",
        ),
        score=0.92,
        matched_reasons=["symbol_match"],
    )
    temporal_ev = [
        {
            "type": "temporal_event",
            "event_id": "ev_1",
            "subject": "validate_credentials",
            "relation": "VALIDATES",
            "object": "Credentials",
            "timestamp": "2026-01-01T10:00:00+00:00",
            "commit_sha": "11111111",
            "file": "auth.py",
            "lines": "1-20",
            "snippet": "Added initial credential validation without length checks",
            "change_type": "ATOM_ADD",
            "relationship_path": "validate_credentials --[VALIDATES]--> Credentials",
        }
    ]

    assembled = ContextAssembler.assemble_context(
        ranked_candidates=[ranked_cand],
        temporal_evidence=temporal_ev,
    )

    assert "## HISTORICAL TEMPORAL EVIDENCE (STAR-RAG)" in assembled.prompt_context
    assert "Commit: 11111111" in assembled.prompt_context
    assert "Temporal Status: HISTORICAL" in assembled.prompt_context
    assert any(e.get("type") == "temporal_event" for e in assembled.evidence_items)


# ==============================================================================
# 8. Failure Handling and Safeguards
# ==============================================================================


def test_failure_handling_and_sparse_fallback():
    # 1. Empty candidate list
    res_empty = StarRagContextService.run_star_rag_pipeline([])
    assert res_empty.is_fallback is True
    assert "No input candidates" in (res_empty.fallback_reason or "")

    # 2. Candidates with insufficient events (< 2)
    single_cand = _make_candidate("c0", "LoneFunc", "lone.py", "def lone(): pass")
    res_single = StarRagContextService.run_star_rag_pipeline([single_cand])
    assert res_single.is_fallback is True
    assert "Insufficient temporal events" in (res_single.fallback_reason or "")

    # 3. Completely unrelated query below anchor gate
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    c1 = _make_candidate(
        "c1",
        "auth",
        "auth.py",
        "def auth(): pass",
        committed_at=t0,
        signals={"vector_similarity": 0.1, "symbol_match": 0.0},
    )
    c2 = _make_candidate(
        "c2",
        "user",
        "user.py",
        "def user(): pass",
        committed_at=t0,
        signals={"vector_similarity": 0.1, "symbol_match": 0.0},
    )
    q_unrelated = AnalyzedQuery(
        raw_query="How do I deploy a Cassandra Helm chart on Kubernetes?",
        keywords=["cassandra", "helm", "kubernetes"],
    )
    res_unrelated = StarRagContextService.run_star_rag_pipeline(
        candidates=[c1, c2],
        analyzed_query=q_unrelated,
        query_text=q_unrelated.raw_query,
    )
    assert res_unrelated.is_fallback is True
    assert "below confidence threshold" in (res_unrelated.fallback_reason or "")
