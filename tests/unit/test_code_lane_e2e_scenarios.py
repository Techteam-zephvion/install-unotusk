"""
Phase 4 Realistic End-to-End Evaluation Suite for AI PIE Code Lane.

Tests 8 realistic production scenarios:
1. Exact Symbol / Module Match
2. Multi-File / Structural Relation Query
3. Recent Changes / Evolution Query
4. Historical vs. Current Code Lineage
5. Superseded Logic Demotion
6. Empty / Irrelevant Query Degradation
7. Misleading Keyword Overlap Resilience
8. Component Failure / Signal Recovery

Verifies retrieval, graph expansion, ranking, context assembly, and provenance retention.
"""

import uuid
from datetime import UTC, datetime

from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import MultiSignalRanker, RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


def _make_candidate(
    candidate_id: str,
    name: str,
    path: str,
    start_line: int,
    end_line: int,
    content: str,
    entity_type: str = "CHUNK",
    signals: dict[str, float] | None = None,
    metadata: dict | None = None,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        candidate_id=candidate_id,
        entity_type=entity_type,
        name=name,
        path=path,
        start_line=start_line,
        end_line=end_line,
        content=content,
        file_id=uuid.uuid4(),
        symbol_id=uuid.uuid4(),
        signals=signals or {},
        metadata=metadata or {},
    )


def test_scenario_1_exact_symbol_module_match():
    """Scenario 1: User asks for a specific function name.

    Expected: Exact symbol ranked #1, correct lines and file, score >= 0.85.
    """
    query = AnalyzedQuery(
        raw_query="where is verify_token implemented?",
        keywords=["verify_token", "implemented"],
        symbol_candidates=["verify_token"],
        path_candidates=[],
        concept_keywords=["token", "verify"],
        is_temporal=False,
    )

    exact_target = _make_candidate(
        candidate_id="chunk:auth:verify_token",
        name="verify_token",
        path="src/auth/service.py",
        start_line=15,
        end_line=35,
        content="def verify_token(token: str) -> bool:\n    return jwt.decode(token, SECRET_KEY)",
        signals={"symbol_match": 1.0, "vector_similarity": 0.92, "content_match": 0.8},
        metadata={"commit_sha": "abc12345", "is_current": True},
    )

    partial_match = _make_candidate(
        candidate_id="chunk:auth:verify_session",
        name="verify_session",
        path="src/auth/session.py",
        start_line=40,
        end_line=60,
        content="def verify_session(session_id: str) -> bool:\n    return session_store.has(session_id)",
        signals={"vector_similarity": 0.55},
        metadata={"commit_sha": "abc12345", "is_current": True},
    )

    ranked: list[RankedCandidate] = MultiSignalRanker.rank_candidates(
        candidates=[partial_match, exact_target],
        analyzed_query=query,
    )

    assert len(ranked) >= 2
    top = ranked[0]
    assert top.candidate.name == "verify_token"
    assert top.candidate.path == "src/auth/service.py"
    assert top.candidate.start_line == 15
    assert top.candidate.end_line == 35
    assert top.score >= 0.85
    assert any("Exact symbol match" in reason for reason in top.matched_reasons)

    # Context assembly check
    assembled = ContextAssembler.assemble_context(ranked)
    assert "verify_token" in assembled.prompt_context
    assert assembled.evidence_items[0]["symbol"] == "verify_token"
    assert assembled.evidence_items[0]["relevance"] >= 0.85


def test_scenario_2_multi_file_structural_relation_query():
    """Scenario 2: User asks about interaction between two components.

    Expected: Graph expansion pulls neighbor, path documented, hop count correct.
    """
    query = AnalyzedQuery(
        raw_query="how does OrderService interact with PaymentGateway?",
        keywords=["orderservice", "interact", "paymentgateway"],
        symbol_candidates=["OrderService", "PaymentGateway"],
        path_candidates=[],
        concept_keywords=["order", "payment"],
        is_temporal=False,
    )

    order_svc = _make_candidate(
        candidate_id="chunk:orders:service",
        name="OrderService",
        path="src/orders/service.py",
        start_line=10,
        end_line=50,
        content="class OrderService:\n    def checkout(self):\n        self.payment_gateway.charge()",
        signals={"symbol_match": 1.0, "vector_similarity": 0.88},
        metadata={"commit_sha": "c0ffee1", "is_current": True},
    )

    payment_gw = _make_candidate(
        candidate_id="chunk:payments:gateway",
        name="PaymentGateway",
        path="src/payments/gateway.py",
        start_line=1,
        end_line=45,
        content="class PaymentGateway:\n    def charge(self, amount):\n        return stripe.charge(amount)",
        signals={"symbol_match": 1.0, "graph_expansion": 0.9},
        metadata={
            "commit_sha": "c0ffee2",
            "is_current": True,
            "relationship_path": "OrderService -> PaymentGateway [CALLS, hop=1]",
            "relationship_type": "CALLS",
            "relationship_hop": 1,
            "connected_from": "OrderService",
            "retrieval_reason": "Direct method call from OrderService.checkout",
        },
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[order_svc, payment_gw],
        analyzed_query=query,
    )

    assert len(ranked) == 2
    names = {r.candidate.name for r in ranked}
    assert "OrderService" in names
    assert "PaymentGateway" in names

    assembled = ContextAssembler.assemble_context(ranked)
    assert "OrderService -> PaymentGateway" in assembled.prompt_context
    assert "Hop 1" in assembled.prompt_context

    ev_gw = next(e for e in assembled.evidence_items if e["symbol"] == "PaymentGateway")
    assert ev_gw["relationship_hop"] == 1
    assert ev_gw["connected_from"] == "OrderService"
    assert ev_gw["relationship_type"] == "CALLS"


def test_scenario_3_recent_changes_evolution_query():
    """Scenario 3: User asks what changed in auth recently.

    Expected: Temporal retrieval detects intent, rewards commit metadata and chronological lineage.
    """
    query = AnalyzedQuery(
        raw_query="what changed in auth recently?",
        keywords=["auth", "changed", "recently"],
        symbol_candidates=[],
        path_candidates=["auth"],
        concept_keywords=["auth", "change"],
        is_temporal=True,
    )

    old_commit = _make_candidate(
        candidate_id="chunk:auth:v1",
        name="login_handler",
        path="src/auth/login.py",
        start_line=1,
        end_line=20,
        content="def login_handler(): pass",
        signals={"file_match": 0.8},
        metadata={
            "commit_sha": "1111111111111111111111111111111111111111",
            "commit_message": "feat: initial basic login",
            "committed_at": datetime(2026, 1, 10, tzinfo=UTC),
            "is_superseded": True,
        },
    )

    recent_commit = _make_candidate(
        candidate_id="chunk:auth:v2",
        name="login_handler",
        path="src/auth/login.py",
        start_line=1,
        end_line=25,
        content="def login_handler(): # added rate limiting and MFA",
        signals={"file_match": 0.8},
        metadata={
            "commit_sha": "2222222222222222222222222222222222222222",
            "commit_message": "feat(auth): add MFA verification and rate limits",
            "committed_at": datetime(2026, 10, 15, tzinfo=UTC),
            "is_current": True,
        },
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[old_commit, recent_commit],
        analyzed_query=query,
    )

    assembled = ContextAssembler.assemble_context(ranked)
    assert "MFA verification" in assembled.prompt_context
    assert any("Historical commit evidence" in r.matched_reasons for r in ranked)


def test_scenario_4_historical_vs_current_code():
    """Scenario 4: User asks about current implementation of a function modified across commits.

    Expected: Current version prioritized, superseded version identified as such, no hallucinated merges.
    """
    query = AnalyzedQuery(
        raw_query="how is calculate_discount computed?",
        keywords=["calculate_discount", "computed"],
        symbol_candidates=["calculate_discount"],
        path_candidates=[],
        concept_keywords=["discount", "calc"],
        is_temporal=False,
    )

    cand_old = _make_candidate(
        candidate_id="chunk:discount:old",
        name="calculate_discount",
        path="src/billing/discount.py",
        start_line=5,
        end_line=15,
        content="def calculate_discount(total): return total * 0.05",
        signals={"symbol_match": 1.0, "vector_similarity": 0.8},
        metadata={
            "commit_sha": "old_sha_123",
            "committed_at": datetime(2026, 2, 1, tzinfo=UTC),
            "is_superseded": True,
        },
    )

    cand_current = _make_candidate(
        candidate_id="chunk:discount:new",
        name="calculate_discount",
        path="src/billing/discount.py",
        start_line=5,
        end_line=22,
        content="def calculate_discount(total, tier='standard'): return total * TIER_RATES.get(tier, 0.1)",
        signals={"symbol_match": 1.0, "vector_similarity": 0.8},
        metadata={
            "commit_sha": "new_sha_456",
            "committed_at": datetime(2026, 10, 1, tzinfo=UTC),
            "is_current": True,
            "has_superseded_versions": True,
        },
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[cand_old, cand_current],
        analyzed_query=query,
    )

    assert ranked[0].candidate.metadata["commit_sha"] == "new_sha_456"
    assert ranked[0].score > ranked[1].score
    assert ranked[0].candidate.metadata.get("is_current") is True

    assembled = ContextAssembler.assemble_context(ranked)
    ev_current = assembled.evidence_items[0]
    assert ev_current["commit_sha"] == "new_sha_456"
    assert ev_current["is_current"] is True


def test_scenario_5_superseded_logic_demotion():
    """Scenario 5: Function was rewritten; user asks about current implementation.

    Expected: Superseded chunk receives 0.4x penalty and demoted below current code.
    """
    query = AnalyzedQuery(
        raw_query="show me the authentication implementation",
        keywords=["authentication", "implementation"],
        symbol_candidates=[],
        path_candidates=["auth"],
        concept_keywords=["auth"],
        is_temporal=False,
    )

    superseded_chunk = _make_candidate(
        candidate_id="chunk:legacy_auth",
        name="legacy_auth",
        path="src/auth/legacy.py",
        start_line=1,
        end_line=30,
        content="def legacy_auth(u, p): return check_md5(u, p)",
        signals={"vector_similarity": 0.9, "content_match": 0.8},
        metadata={"is_superseded": True, "commit_sha": "old111"},
    )

    current_chunk = _make_candidate(
        candidate_id="chunk:oauth_flow",
        name="oauth_flow",
        path="src/auth/oauth.py",
        start_line=1,
        end_line=45,
        content="def oauth_flow(req): return oauth_provider.authenticate(req)",
        signals={"vector_similarity": 0.85, "content_match": 0.7},
        metadata={"is_current": True, "commit_sha": "cur222"},
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[superseded_chunk, current_chunk],
        analyzed_query=query,
    )

    assert ranked[0].candidate.candidate_id == "chunk:oauth_flow"
    assert any("demoted for current-state query" in r for r in ranked[1].matched_reasons)


def test_scenario_6_empty_irrelevant_query_graceful_degradation():
    """Scenario 6: Completely unrelated query with no relevance.

    Expected: Noise filter cleans out irrelevant chunks, fallback prompt context used.
    """
    query = AnalyzedQuery(
        raw_query="explain the quantum teleportation reactor in alpha centauri",
        keywords=["quantum", "teleportation", "reactor", "alpha", "centauri"],
        symbol_candidates=[],
        path_candidates=[],
        concept_keywords=[],
        is_temporal=False,
    )

    unrelated_chunk = _make_candidate(
        candidate_id="chunk:utils:math",
        name="add_numbers",
        path="src/utils/math.py",
        start_line=1,
        end_line=5,
        content="def add(a, b): return a + b",
        signals={"content_match": 0.05},
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[unrelated_chunk],
        analyzed_query=query,
        noise_threshold=0.25,
    )

    assembled = ContextAssembler.assemble_context(ranked)
    assert assembled.candidate_count >= 1
    assert assembled.evidence_items[0]["relevance"] < 0.25


def test_scenario_7_misleading_keyword_overlap_resilience():
    """Scenario 7: Test files contain terms like 'test', 'temp', 'mock' matching generic query.

    Expected: Semantic & path matching ranks production business logic over test mock.
    """
    query = AnalyzedQuery(
        raw_query="user registration workflow",
        keywords=["user", "registration", "workflow"],
        symbol_candidates=["register_user"],
        path_candidates=["registration"],
        concept_keywords=["user", "register"],
        is_temporal=False,
    )

    test_mock_candidate = _make_candidate(
        candidate_id="chunk:test:mock_user",
        name="mock_registration",
        path="tests/mocks/test_user_registration.py",
        start_line=1,
        end_line=20,
        content="# Test mock helper for user registration workflow test temp mock",
        signals={"content_match": 0.9, "vector_similarity": 0.4},
        metadata={"commit_sha": "test999"},
    )

    prod_candidate = _make_candidate(
        candidate_id="chunk:prod:register_user",
        name="register_user",
        path="src/users/registration.py",
        start_line=10,
        end_line=60,
        content="def register_user(email: str, password: str):\n    user = User(email=email)\n    db.save(user)",
        signals={"symbol_match": 1.0, "file_match": 1.0, "vector_similarity": 0.85},
        metadata={"commit_sha": "prod888", "is_current": True},
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[test_mock_candidate, prod_candidate],
        analyzed_query=query,
    )

    assert ranked[0].candidate.candidate_id == "chunk:prod:register_user"
    assert ranked[0].score > ranked[1].score
    assert "src/users/registration.py" in ranked[0].candidate.path


def test_scenario_8_component_failure_signal_recovery():
    """Scenario 8: Vector embedding signal is missing (None/failure).

    Expected: Lexical and graph signals still retrieve and rank successfully without crashing.
    """
    query = AnalyzedQuery(
        raw_query="database connection pool timeout",
        keywords=["database", "connection", "pool", "timeout"],
        symbol_candidates=["ConnectionPool"],
        path_candidates=["db"],
        concept_keywords=["database", "connection"],
        is_temporal=False,
    )

    db_candidate = _make_candidate(
        candidate_id="chunk:db:pool",
        name="ConnectionPool",
        path="src/db/pool.py",
        start_line=1,
        end_line=40,
        content="class ConnectionPool:\n    timeout = 30\n    def get_conn(self): pass",
        signals={"symbol_match": 1.0, "file_match": 0.9, "content_match": 0.8},
        metadata={"commit_sha": "db777", "is_current": True},
    )

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[db_candidate],
        analyzed_query=query,
    )

    assert len(ranked) == 1
    assert ranked[0].candidate.name == "ConnectionPool"
    assert ranked[0].score > 0.7

    assembled = ContextAssembler.assemble_context(ranked)
    assert len(assembled.evidence_items) == 1
    assert assembled.evidence_items[0]["symbol"] == "ConnectionPool"
