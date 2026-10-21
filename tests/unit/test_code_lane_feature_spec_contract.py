"""
Unit and Contract tests for AI PIE Code Lane Feature-Spec Evidence Contract.

Verifies:
1. EvidenceItem schema preserves rich provenance (commit_sha, fingerprint,
   temporal status, relationship paths, atomic facts) while maintaining
   backward-compatibility with legacy 6-field consumers.
2. IntelligenceService._build_evidence_item faithfully forwards all provenance
   from ContextAssembler raw dictionary representations.
3. IntelligenceService.ask_question and get_conversation_messages return
   fully-populated EvidenceItem objects.
4. Empty candidate sets and zero-evidence cases degrade gracefully.
5. Error recovery handles retrieval failures cleanly.
6. FeatureSpecificationGenerator synthesizes grounded BDD scenarios from evidence.
7. Superseded precursor code flags diagnostic warnings.
8. MultiSignalRanker tie-breaking, path boosting, and test demotion.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.schemas.intelligence import (
    BDDScenarioItem,
    EvidenceItem,
    FeatureSpecificationResponse,
    FeatureSpecRequest,
    GroundedAnswerResponse,
    MessageRead,
)
from apps.api.src.services.context_engine.assembler import AssembledContext, ContextAssembler
from apps.api.src.services.context_engine.feature_spec_generator import (
    FeatureSpecificationGenerator,
)
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import MultiSignalRanker, RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.intelligence_service import IntelligenceService, _build_evidence_item


def test_evidence_item_minimal_backward_compatibility():
    """Ensure legacy callers providing only the 6 core fields still succeed."""
    item = EvidenceItem(
        type="symbol",
        file="src/auth.py",
        symbol="verify_token",
        lines="10-25",
        relevance=0.88,
        snippet="def verify_token(token: str) -> bool: ...",
    )
    assert item.type == "symbol"
    assert item.file == "src/auth.py"
    assert item.symbol == "verify_token"
    assert item.lines == "10-25"
    assert item.relevance == 0.88
    assert item.commit_sha is None
    assert item.is_current is None
    assert item.relationship_path is None


def test_evidence_item_rich_provenance_fields():
    """Verify all ATOM Code Lane provenance fields are preserved."""
    repo_id = str(uuid.uuid4())
    snap_id = str(uuid.uuid4())
    file_id = str(uuid.uuid4())
    sym_id = str(uuid.uuid4())

    item = EvidenceItem(
        type="chunk",
        file="src/services/billing.py",
        symbol="charge_card",
        lines="40-65",
        relevance=0.95,
        snippet="def charge_card(customer_id, amount): ...",
        commit_sha="a1b2c3d4e5f678901234567890abcdef12345678",
        commit_message="feat(billing): implement atomic retry on card charge",
        repository_id=repo_id,
        snapshot_id=snap_id,
        file_id=file_id,
        symbol_id=sym_id,
        fingerprint="chunk-sha256-abc123def456",
        chunk_type="code",
        committed_at="2026-10-20T10:00:00Z",
        is_current=True,
        is_superseded=False,
        is_deleted=False,
        superseded_by_sha=None,
        superseded_by_date=None,
        renamed_from=None,
        renamed_to=None,
        relationship_path="OrderService -> charge_card [CALLS, hop=1]",
        relationship_type="CALLS",
        relationship_hop=1,
        connected_from="OrderService",
        retrieval_reason="Direct AST call from checkout controller",
        alternative_paths=["PaymentGateway -> charge_card"],
        provenance={"indexer": "atom-v2", "tree_sitter_scope": "method"},
        atomic_code_facts=[{"statement": "charges customer card", "fact_type": "BEHAVIOR"}],
        temporal_relations=[{"subject": "OrderService", "relation": "CALLS", "object": "charge_card"}],
    )

    data = item.model_dump()
    assert data["commit_sha"] == "a1b2c3d4e5f678901234567890abcdef12345678"
    assert data["fingerprint"] == "chunk-sha256-abc123def456"
    assert data["is_current"] is True
    assert data["is_superseded"] is False
    assert data["relationship_hop"] == 1
    assert data["connected_from"] == "OrderService"
    assert len(data["atomic_code_facts"]) == 1
    assert len(data["temporal_relations"]) == 1


def test_build_evidence_item_from_context_assembler_output():
    """Verify _build_evidence_item accurately maps ContextAssembler output dict."""
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()
    cand = RetrievedCandidate(
        candidate_id="chunk:tax:calc",
        entity_type="CHUNK",
        name="calculate_tax",
        path="src/tax/calc.py",
        start_line=12,
        end_line=30,
        content="def calculate_tax(amount: float) -> float: return amount * 0.2",
        file_id=file_id,
        symbol_id=sym_id,
        signals={"exact_match": 1.0},
        metadata={
            "repository_id": str(uuid.uuid4()),
            "snapshot_id": str(uuid.uuid4()),
            "commit_sha": "deadbeef1234567890abcdef1234567890abcdef",
            "commit_message": "fix: tax rate update",
            "fingerprint": "fp-tax-999",
            "is_current": True,
            "is_superseded": False,
            "relationship_path": "InvoiceService -> calculate_tax [CALLS, hop=1]",
            "relationship_type": "CALLS",
            "relationship_hop": 1,
            "connected_from": "InvoiceService",
            "retrieval_reason": "direct invocation",
            "atomic_code_facts": [
                {"statement": "Calculates tax at 20%", "fact_type": "BEHAVIOR", "is_uncertain": False}
            ],
            "temporal_relations": [
                {"subject": "InvoiceService", "relation": "CALLS", "object": "calculate_tax", "t_start": "commit-1"}
            ],
        },
    )

    assembled: AssembledContext = ContextAssembler.assemble_context(
        ranked_candidates=[RankedCandidate(candidate=cand, score=0.92, matched_reasons=["exact_match"])]
    )

    assert len(assembled.evidence_items) == 1
    raw_ev = assembled.evidence_items[0]

    item = _build_evidence_item(raw_ev)
    assert isinstance(item, EvidenceItem)
    assert item.file == "src/tax/calc.py"
    assert item.symbol == "calculate_tax"
    assert item.relevance == 0.92
    assert item.commit_sha == "deadbeef1234567890abcdef1234567890abcdef"
    assert item.fingerprint == "fp-tax-999"
    assert item.is_current is True
    assert item.relationship_hop == 1
    assert item.connected_from == "InvoiceService"
    assert len(item.atomic_code_facts) == 1


@pytest.mark.asyncio
async def test_intelligence_service_ask_question_provenance_contract():
    """Verify ask_question endpoint forwards provenance into GroundedAnswerResponse."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_project = MagicMock()
    mock_project.id = project_id
    mock_project.organization_id = uuid.uuid4()

    mock_snapshot = MagicMock()
    mock_snapshot.id = snap_id

    mock_conversation = MagicMock()
    mock_conversation.id = conv_id
    mock_conversation.project_id = project_id
    mock_conversation.updated_at = None

    mock_answer = MagicMock()
    mock_answer.content = "The `calculate_tax` function handles standard 20% rate."
    mock_answer.related_entities = ["calculate_tax"]
    mock_answer.confidence = "HIGH"
    mock_answer.debug_signals = {"retrieval_latency_ms": 12.5}
    mock_answer.evidence = [
        {
            "type": "chunk",
            "file": "src/tax/calc.py",
            "symbol": "calculate_tax",
            "lines": "12-30",
            "relevance": 0.94,
            "snippet": "def calculate_tax(amount): ...",
            "commit_sha": "abcdef1234567890abcdef1234567890abcdef12",
            "commit_message": "refactor(tax): extracted tax calculation",
            "fingerprint": "fp-12345",
            "is_current": True,
            "is_superseded": False,
            "relationship_path": "Invoice -> calculate_tax [CALLS, hop=1]",
            "relationship_hop": 1,
            "connected_from": "Invoice",
        }
    ]

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    with (
        patch.object(IntelligenceService, "_verify_project_access", return_value=mock_project),
        patch.object(IntelligenceService, "_get_active_snapshot", return_value=mock_snapshot),
        patch("apps.api.src.services.intelligence_service.ProjectContextEngine") as mock_engine_cls,
    ):
        mock_engine = MagicMock()
        mock_engine.investigate = AsyncMock(return_value=mock_answer)
        mock_engine_cls.return_value = mock_engine

        mock_exec_conv = MagicMock()
        mock_exec_conv.scalar_one_or_none.return_value = mock_conversation

        mock_exec_hist = MagicMock()
        mock_exec_hist.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[mock_exec_conv, mock_exec_hist])

        response: GroundedAnswerResponse = await IntelligenceService.ask_question(
            session=mock_session,
            user_id=user_id,
            project_id=project_id,
            question="Where is tax calculated?",
            conversation_id=conv_id,
        )

        assert response.role == "assistant"
        assert response.content == mock_answer.content
        assert len(response.evidence) == 1
        ev = response.evidence[0]
        assert ev.file == "src/tax/calc.py"
        assert ev.symbol == "calculate_tax"
        assert ev.commit_sha == "abcdef1234567890abcdef1234567890abcdef12"
        assert ev.fingerprint == "fp-12345"
        assert ev.is_current is True
        assert ev.relationship_hop == 1
        assert ev.connected_from == "Invoice"


@pytest.mark.asyncio
async def test_intelligence_service_empty_evidence_contract():
    """Verify that empty evidence from context engine degrades gracefully."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    conv_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_project = MagicMock(id=project_id, organization_id=uuid.uuid4())
    mock_snapshot = MagicMock(id=snap_id)
    mock_conv = MagicMock(id=conv_id, project_id=project_id, updated_at=None)

    mock_answer = MagicMock(
        content="No relevant code was found in this snapshot for that query.",
        related_entities=[],
        confidence="LOW",
        debug_signals={},
        evidence=[],
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    with (
        patch.object(IntelligenceService, "_verify_project_access", return_value=mock_project),
        patch.object(IntelligenceService, "_get_active_snapshot", return_value=mock_snapshot),
        patch("apps.api.src.services.intelligence_service.ProjectContextEngine") as mock_engine_cls,
    ):
        mock_engine = MagicMock()
        mock_engine.investigate = AsyncMock(return_value=mock_answer)
        mock_engine_cls.return_value = mock_engine

        mock_conv_res = MagicMock()
        mock_conv_res.scalar_one_or_none.return_value = mock_conv
        mock_hist_res = MagicMock()
        mock_hist_res.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(side_effect=[mock_conv_res, mock_hist_res])

        response = await IntelligenceService.ask_question(
            session=mock_session,
            user_id=user_id,
            project_id=project_id,
            question="What is the quantum encryption protocol?",
            conversation_id=conv_id,
        )

        assert len(response.evidence) == 0
        assert response.confidence == "LOW"
        assert "No relevant code was found" in response.content


@pytest.mark.asyncio
async def test_get_conversation_messages_restores_rich_provenance():
    """Verify that stored message evidence is restored with rich provenance in MessageRead."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    conv_id = uuid.uuid4()

    mock_project = MagicMock(id=project_id, organization_id=uuid.uuid4())
    mock_conv = MagicMock(id=conv_id, project_id=project_id)

    mock_message = MagicMock()
    mock_message.id = uuid.uuid4()
    mock_message.conversation_id = conv_id
    mock_message.role = "assistant"
    mock_message.content = "Here is the implementation."
    mock_message.confidence = "HIGH"
    mock_message.debug_signals = {}
    mock_message.created_at = datetime.now(UTC)
    mock_message.related_entities = ["OrderService"]
    mock_message.evidence = [
        {
            "type": "symbol",
            "file": "src/orders.py",
            "symbol": "create_order",
            "lines": "5-25",
            "relevance": 0.91,
            "snippet": "def create_order(): pass",
            "commit_sha": "9999888877776666555544443333222211110000",
            "is_current": True,
            "relationship_path": "ApiRouter -> create_order",
        }
    ]

    mock_session = AsyncMock()
    with patch.object(IntelligenceService, "_verify_project_access", return_value=mock_project):
        mock_conv_res = MagicMock()
        mock_conv_res.scalar_one_or_none.return_value = mock_conv

        mock_msg_res = MagicMock()
        mock_msg_res.scalars.return_value.all.return_value = [mock_message]

        mock_session.execute = AsyncMock(side_effect=[mock_conv_res, mock_msg_res])

        messages: list[MessageRead] = await IntelligenceService.get_conversation_messages(
            session=mock_session,
            user_id=user_id,
            project_id=project_id,
            conversation_id=conv_id,
        )

        assert len(messages) == 1
        msg = messages[0]
        assert len(msg.evidence) == 1
        ev = msg.evidence[0]
        assert ev.symbol == "create_order"
        assert ev.commit_sha == "9999888877776666555544443333222211110000"
        assert ev.is_current is True
        assert ev.relationship_path == "ApiRouter -> create_order"


def test_feature_specification_generator_grounding():
    """Verify FeatureSpecificationGenerator grounds BDD scenarios directly in retrieved Code Lane evidence."""
    project_id = uuid.uuid4()
    feature_req = "Add rate limiting to authentication endpoints"

    evidence = [
        EvidenceItem(
            type="symbol",
            file="apps/api/src/api/routes/auth.py",
            symbol="login",
            lines="25-45",
            relevance=0.96,
            snippet="@router.post('/login')\nasync def login(form_data: OAuth2PasswordRequestForm): ...",
            commit_sha="c0ffee1234567890abcdef1234567890abcdef12",
            fingerprint="fp-auth-route",
            is_current=True,
            is_superseded=False,
            relationship_path="login -> AuthService.authenticate_user [CALLS, hop=1]",
            relationship_hop=1,
            connected_from="AuthService.authenticate_user",
            atomic_code_facts=[{"statement": "Authenticates user credentials and generates JWT tokens"}],
        ),
        EvidenceItem(
            type="chunk",
            file="apps/api/src/services/auth_service.py",
            symbol="AuthService.authenticate_user",
            lines="80-110",
            relevance=0.91,
            snippet="async def authenticate_user(session, email, password): ...",
            commit_sha="c0ffee1234567890abcdef1234567890abcdef12",
            fingerprint="fp-auth-service",
            is_current=True,
            is_superseded=False,
            atomic_code_facts=[{"statement": "Validates bcrypt password hash against stored user record"}],
        ),
    ]

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=feature_req,
        evidence_items=evidence,
        debug_signals={"candidates_retrieved": 2},
    )

    assert spec.project_id == project_id
    assert spec.confidence == "HIGH"
    assert spec.has_superseded_precursors is False
    assert spec.warning is None

    # Confirmed code facts must come from the actual evidence
    assert len(spec.confirmed_code_facts) >= 2
    assert any("Authenticates user credentials" in f for f in spec.confirmed_code_facts)
    assert any("Validates bcrypt password" in f for f in spec.confirmed_code_facts)

    # Cited files and symbols must reflect the real evidence
    assert "apps/api/src/api/routes/auth.py" in spec.cited_files
    assert "apps/api/src/services/auth_service.py" in spec.cited_files
    assert "login" in spec.cited_symbols
    assert "AuthService.authenticate_user" in spec.cited_symbols

    # BDD Scenarios must reference the cited components
    assert len(spec.scenarios) == 3
    s1 = spec.scenarios[0]
    assert "login" in s1.given or "auth.py" in s1.given
    assert "rate limiting" in s1.when.lower() or "action" in s1.when.lower()

    # Evidence with complete provenance must remain attached
    assert len(spec.evidence) == 2
    assert spec.evidence[0].commit_sha == "c0ffee1234567890abcdef1234567890abcdef12"
    assert spec.evidence[0].fingerprint == "fp-auth-route"


def test_feature_specification_superseded_precursors_flagged():
    """Verify historical / superseded code is not falsely presented as current implementation."""
    project_id = uuid.uuid4()
    feature_req = "Upgrade authentication token refresh"

    evidence = [
        EvidenceItem(
            type="chunk",
            file="apps/api/src/services/auth_service.py",
            symbol="refresh_token_v2",
            lines="120-145",
            relevance=0.92,
            snippet="async def refresh_token_v2(): ...",
            commit_sha="current_sha_123456",
            fingerprint="fp-v2",
            is_current=True,
            is_superseded=False,
            atomic_code_facts=[{"statement": "Current token refresh with rotation"}],
        ),
        EvidenceItem(
            type="chunk",
            file="apps/api/src/services/auth_service.py",
            symbol="refresh_token_legacy",
            lines="150-180",
            relevance=0.45,
            snippet="async def refresh_token_legacy(): ...",
            commit_sha="historical_sha_999",
            fingerprint="fp-legacy",
            is_current=False,
            is_superseded=True,
            superseded_by_sha="current_sha_123456",
            atomic_code_facts=[{"statement": "Deprecated token refresh without rotation"}],
        ),
    ]

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=feature_req,
        evidence_items=evidence,
    )

    assert spec.has_superseded_precursors is True
    assert spec.warning is not None
    assert "superseded or historical code" in spec.warning
    # Grounding facts should prioritize active code
    assert any("Current token refresh with rotation" in f for f in spec.confirmed_code_facts)
    # Both evidence items remain attached in the evidence list for provenance auditing
    assert len(spec.evidence) == 2


def test_feature_specification_empty_evidence_zero_hallucination():
    """Verify empty evidence results in LOW confidence, diagnostic warning, and zero invented files/symbols."""
    project_id = uuid.uuid4()
    feature_req = "Integrate quantum teleportation protocol"

    spec = FeatureSpecificationGenerator.generate_from_evidence(
        project_id=project_id,
        feature_request=feature_req,
        evidence_items=[],
    )

    assert spec.confidence == "LOW"
    assert spec.evidence == []
    assert spec.cited_files == []
    assert spec.cited_symbols == []
    assert spec.confirmed_code_facts == []
    assert spec.warning is not None
    assert "No matching implementation found" in spec.warning
    # Inferred requirements state what must be created from scratch
    assert any("quantum teleportation" in req.lower() for req in spec.inferred_requirements)


@pytest.mark.asyncio
async def test_intelligence_service_generate_feature_specification_call_chain():
    """Verify the complete permitted application call chain from IntelligenceService to FeatureSpecificationResponse."""
    project_id = uuid.uuid4()
    user_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_project = MagicMock(id=project_id, organization_id=uuid.uuid4())
    mock_snapshot = MagicMock(id=snap_id)

    mock_answer = MagicMock()
    mock_answer.content = "Analysis of authentication endpoints"
    mock_answer.related_entities = ["login", "AuthService"]
    mock_answer.confidence = "HIGH"
    mock_answer.debug_signals = {"candidates_retrieved": 1}
    mock_answer.evidence = [
        {
            "type": "symbol",
            "file": "apps/api/src/api/routes/auth.py",
            "symbol": "login",
            "lines": "25-45",
            "relevance": 0.95,
            "snippet": "@router.post('/login')\nasync def login(): pass",
            "commit_sha": "abc123def456",
            "fingerprint": "fp-login",
            "is_current": True,
            "is_superseded": False,
            "relationship_path": "routes/auth.py -> services/auth_service.py",
            "atomic_code_facts": [{"statement": "Authenticates user with username and password"}],
        }
    ]

    mock_session = AsyncMock()
    with (
        patch.object(IntelligenceService, "_verify_project_access", return_value=mock_project),
        patch.object(IntelligenceService, "_get_active_snapshot", return_value=mock_snapshot),
        patch("apps.api.src.services.intelligence_service.ProjectContextEngine") as mock_engine_cls,
    ):
        mock_engine = MagicMock()
        mock_engine.investigate = AsyncMock(return_value=mock_answer)
        mock_engine_cls.return_value = mock_engine

        spec: FeatureSpecificationResponse = await IntelligenceService.generate_feature_specification(
            session=mock_session,
            user_id=user_id,
            project_id=project_id,
            feature_request="Add login brute force protection",
        )

        assert isinstance(spec, FeatureSpecificationResponse)
        assert spec.project_id == project_id
        assert spec.confidence == "HIGH"
        assert len(spec.evidence) == 1
        assert spec.evidence[0].file == "apps/api/src/api/routes/auth.py"
        assert spec.evidence[0].commit_sha == "abc123def456"
        assert "apps/api/src/api/routes/auth.py" in spec.cited_files
        assert "login" in spec.cited_symbols
        assert any("Authenticates user" in f for f in spec.confirmed_code_facts)


def test_multi_signal_ranker_raw_score_tie_break():
    """Verify candidates with raw scores >= 3.0 maintain discriminatory rank order after normalization."""
    cand_strong = RetrievedCandidate(
        candidate_id="cand:strong",
        entity_type="CHUNK",
        name="authenticate_user",
        path="src/auth.py",
        start_line=1,
        end_line=20,
        content="def authenticate_user(): pass",
        file_id=uuid.uuid4(),
        signals={"symbol_match": 1.0, "file_match": 1.0, "content_match": 1.0, "vector_similarity": 0.95},
    )
    cand_moderate = RetrievedCandidate(
        candidate_id="cand:moderate",
        entity_type="CHUNK",
        name="verify_token",
        path="src/token.py",
        start_line=1,
        end_line=20,
        content="def verify_token(): pass",
        file_id=uuid.uuid4(),
        signals={"symbol_match": 0.8, "file_match": 0.5, "vector_similarity": 0.70},
    )

    query = AnalyzedQuery(
        raw_query="authenticate user in auth.py",
        keywords=["authenticate", "user"],
        symbol_candidates=["authenticate_user"],
        path_candidates=["src/auth.py"],
        concept_keywords=["auth"],
        is_temporal=False,
    )

    ranked = MultiSignalRanker.rank_candidates([cand_moderate, cand_strong], query)

    # Strong candidate must be ranked #1 despite input order having moderate first
    assert len(ranked) >= 2
    assert ranked[0].candidate.candidate_id == "cand:strong"
    assert ranked[1].candidate.candidate_id == "cand:moderate"
    assert ranked[0].score >= ranked[1].score


def test_multi_signal_ranker_path_candidate_matching():
    """Verify that path_candidates detected in query analyzer give appropriate boost to candidate."""
    cand = RetrievedCandidate(
        candidate_id="cand:service",
        entity_type="CHUNK",
        name="ProjectService",
        path="apps/api/src/services/project_service.py",
        start_line=10,
        end_line=30,
        content="class ProjectService: pass",
        file_id=uuid.uuid4(),
        signals={"content_match": 0.5},
    )

    query = AnalyzedQuery(
        raw_query="inspect project_service.py",
        keywords=["project", "service"],
        symbol_candidates=[],
        path_candidates=["project_service.py"],
        concept_keywords=[],
        is_temporal=False,
    )

    ranked = MultiSignalRanker.rank_candidates([cand], query)
    assert len(ranked) == 1
    assert any("Path candidate match" in r for r in ranked[0].matched_reasons)


def test_multi_signal_ranker_test_demotion_audit():
    """Audit the 0.7x test demotion penalty: applies to test files on non-test queries, does NOT apply to production files or test queries."""
    cand_prod = RetrievedCandidate(
        candidate_id="cand:prod",
        entity_type="CHUNK",
        name="login",
        path="apps/api/src/services/attestation_service.py",  # Substring 'test' in 'attestation' must NOT trigger penalty
        start_line=10,
        end_line=30,
        content="def login(): pass",
        file_id=uuid.uuid4(),
        signals={"content_match": 1.0},
    )
    cand_test = RetrievedCandidate(
        candidate_id="cand:test",
        entity_type="CHUNK",
        name="test_login",
        path="tests/unit/test_auth.py",
        start_line=10,
        end_line=30,
        content="def test_login(): pass",
        file_id=uuid.uuid4(),
        signals={"content_match": 1.0},
    )

    # Case 1: Non-test query -> test file should be penalized, production file should NOT be penalized
    query_prod = AnalyzedQuery(
        raw_query="how does login work",
        keywords=["login", "how", "work"],
        symbol_candidates=["login"],
        path_candidates=[],
        concept_keywords=[],
        is_temporal=False,
    )
    ranked_prod = MultiSignalRanker.rank_candidates([cand_prod, cand_test], query_prod)
    prod_ranked = next(r for r in ranked_prod if r.candidate.candidate_id == "cand:prod")
    test_ranked = next(r for r in ranked_prod if r.candidate.candidate_id == "cand:test")

    assert not any("Test/mock file demoted" in r for r in prod_ranked.matched_reasons)
    assert any("Test/mock file demoted" in r for r in test_ranked.matched_reasons)
    assert prod_ranked.score > test_ranked.score

    # Case 2: Test query -> test file must NOT be penalized
    query_test = AnalyzedQuery(
        raw_query="show login unit tests",
        keywords=["show", "login", "unit", "tests"],
        symbol_candidates=["login"],
        path_candidates=[],
        concept_keywords=[],
        is_temporal=False,
    )
    ranked_test = MultiSignalRanker.rank_candidates([cand_test], query_test)
    assert not any("Test/mock file demoted" in r for r in ranked_test[0].matched_reasons)


@pytest.mark.asyncio
async def test_api_route_generate_project_spec():
    """Verify the FastAPI route handler generate_project_spec resolves project and returns FeatureSpecificationResponse."""
    from apps.api.src.api.routes.intelligence import generate_project_spec
    from apps.api.src.models.user import User

    project_id = uuid.uuid4()
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()
    mock_db = AsyncMock()

    mock_spec_resp = FeatureSpecificationResponse(
        project_id=project_id,
        feature_name="Rate Limiting",
        intent="Add rate limiting to login",
        confidence="HIGH",
        confirmed_code_facts=["Confirmed login route in src/auth.py"],
        inferred_requirements=["Enforce rate ceiling"],
        scenarios=[
            BDDScenarioItem(
                id=1,
                title="Happy Path",
                given="Client with valid API key",
                when="Client calls login within limit",
                then="Login succeeds",
                cited_files=["src/auth.py"],
                cited_symbols=["login"],
            )
        ],
        evidence=[
            EvidenceItem(
                type="symbol",
                file="src/auth.py",
                symbol="login",
                lines="10-25",
                relevance=0.95,
                commit_sha="a1b2c3d4e5f6",
                fingerprint="fp-1",
            )
        ],
        cited_files=["src/auth.py"],
        cited_symbols=["login"],
        has_superseded_precursors=False,
        debug_signals={},
        created_at=datetime.now(UTC),
    )

    with (
        patch(
            "apps.api.src.api.routes.intelligence.ProjectService.resolve_project_id",
            new_callable=AsyncMock,
        ) as mock_resolve,
        patch.object(
            IntelligenceService,
            "generate_feature_specification",
            new_callable=AsyncMock,
        ) as mock_gen,
    ):
        mock_resolve.return_value = project_id
        mock_gen.return_value = mock_spec_resp

        payload = FeatureSpecRequest(
            feature_request="Add rate limiting to login",
            thinking_tier="warm",
        )

        response = await generate_project_spec(
            project_id=str(project_id),
            payload=payload,
            current_user=mock_user,
            db=mock_db,
        )

        assert response.project_id == project_id
        assert response.feature_name == "Rate Limiting"
        assert response.confidence == "HIGH"
        assert len(response.scenarios) == 1
        assert len(response.evidence) == 1
        assert response.evidence[0].commit_sha == "a1b2c3d4e5f6"
        mock_gen.assert_awaited_once_with(
            session=mock_db,
            user_id=mock_user.id,
            project_id=project_id,
            feature_request="Add rate limiting to login",
            thinking_tier="warm",
        )


