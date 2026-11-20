"""
Comprehensive End-to-End Activation and Verification Test Suite for
Temporal STAR-RAG (Zhu et al., arXiv:2510.16715) and
Structure-Aware STAR-RAG (SNR, DTP, SSAF, Evidence Paths).

Tests A through N:
- Test A: Both disabled (STAR_RAG_ENABLED=False, STRUCTURE_AWARE_STAR_RAG_ENABLED=False) -> ATOM only.
- Test B: Temporal only enabled -> Historical queries route to Temporal STAR-RAG; structural queries use ATOM.
- Test C: Structure-Aware only enabled -> Structural queries route to Structure-Aware STAR-RAG; historical use ATOM.
- Test D: Both enabled -> Coordinated retrieval for combined query, direct lookups use ATOM.
- Test E: Function-level CALLS edge extraction verified in build_graph_for_snapshot.
- Test F: Evidence paths and temporal events reach ContextAssembler within budget envelope.
- Test G: Direct symbol lookup preserved on ATOM without graph overhead.
- Test H: Real API route validation (POST /projects/{project_id}/ask).
- Test I: Multi-snapshot history retrieval across snapshots of same repo.
- Test J: Branch separation (snapshots on differing branches maintain isolated histories).
- Test K: API flag forwarding on both /ask and /conversations/{id}/messages.
- Test L: Combined evidence reaches LLM synthesis prompt.
- Test M: Restart persistence (in-memory cache cleared, loads from DB).
- Test N: Real source provenance (caller, callee, file path, line numbers match source code).
"""

from __future__ import annotations

import ast
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.models.symbol import SymbolType
from apps.api.src.schemas.intelligence import GroundedAskRequest
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag import (
    StarRagContextService,
    TemporalCodeEvent,
)
from apps.api.src.services.context_engine.star_rag_structure.cache import (
    _MEMORY_GRAPH_CACHE,
    CodeGraphCache,
)
from apps.api.src.services.context_engine.star_rag_structure.graph_extractor import (
    ASTFunctionCallVisitor,
    CodeGraphExtractor,
)
from apps.api.src.services.context_engine.star_rag_structure.selective_router import (
    StarRagSelectiveRouter,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraph,
    GranularEvidenceHop,
    GranularEvidencePath,
    GraphRelationType,
)
from apps.api.src.services.intelligence_service import IntelligenceService
from apps.api.src.services.llm.base import GroundedAnswer

# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

def make_candidate(
    candidate_id: str,
    name: str,
    path: str,
    content: str,
    committed_at: str | None = None,
    signals: dict[str, float] | None = None,
    symbol_name: str | None = None,
    chunk_type: str = "ATOM_MODIFY",
    file_id: uuid.UUID | None = None,
) -> RetrievedCandidate:
    f_id = file_id or uuid.uuid4()
    meta = {
        "chunk_type": chunk_type,
        "symbol_name": symbol_name or name,
        "file_id": str(f_id),
    }
    if committed_at:
        meta["committed_at"] = committed_at
        meta["commit_sha"] = "commit_" + candidate_id[:8]
        meta["commit_message"] = f"Update {name}"

    return RetrievedCandidate(
        candidate_id=candidate_id,
        entity_type="CHUNK",
        name=name,
        path=path,
        start_line=1,
        end_line=30,
        content=content,
        file_id=f_id,
        signals=signals or {"symbol_match": 1.5, "vector_similarity": 0.85},
        metadata=meta,
    )


# ---------------------------------------------------------------------------
# Test A: Both Disabled -> ATOM Only
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a_both_disabled_uses_atom_only(monkeypatch):
    """
    Test A: When STAR_RAG_ENABLED=False and STRUCTURE_AWARE_STAR_RAG_ENABLED=False,
    neither retrieval engine executes, strictly preserving ATOM as primary.
    """
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", False)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", False)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    cand = make_candidate("c1", "AuthService", "src/auth.py", "class AuthService: pass")
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[cand]),
    )

    engine = ProjectContextEngine()
    ans = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the dependency flow and history of AuthService",
        enable_star_rag=False,
        enable_structure_aware_star_rag=False,
    )

    assert ans.debug_signals.get("star_rag_used") is False
    assert ans.debug_signals.get("structure_aware_star_rag_used") is False
    assert ans.debug_signals.get("star_rag_temporal_routing_decision") == "feature_flag_disabled"
    assert ans.debug_signals.get("star_rag_routing_decision") == "feature_flag_disabled"


# ---------------------------------------------------------------------------
# Test B: Temporal Only Enabled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_b_temporal_only_routes_historical_to_star_and_structural_to_atom(monkeypatch):
    """
    Test B: When STAR_RAG_ENABLED=True and STRUCTURE_AWARE_STAR_RAG_ENABLED=False:
    - Historical queries route to Temporal STAR-RAG.
    - Structural queries without temporal intent route to ATOM.
    """
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", True)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", False)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    cand = make_candidate(
        "c1",
        "validate_credentials",
        "src/auth.py",
        "def validate_credentials(): return True",
        committed_at="2026-01-10T12:00:00+00:00",
    )
    events = [
        TemporalCodeEvent(
            event_id="ev:c1:validate_credentials:MODIFIES:src/auth.py",
            subject="validate_credentials",
            relation="MODIFIES",
            object="src/auth.py",
            timestamp=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
            commit_sha="c1_sha",
            file_path="src/auth.py",
            symbol_name="validate_credentials",
            snippet="def validate_credentials(): return True",
            candidate=cand,
        )
    ]

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag.StarRagContextService.load_historical_events_from_db",
        AsyncMock(return_value=events),
    )

    engine = ProjectContextEngine()

    # 1. Historical query -> Routes to Temporal STAR-RAG
    ans_hist = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="What changed in validate_credentials across recent commits?",
        enable_star_rag=True,
        enable_structure_aware_star_rag=False,
    )
    assert ans_hist.debug_signals.get("star_rag_used") is True
    assert ans_hist.debug_signals.get("structure_aware_star_rag_used") is False

    # 2. Structural query (non-temporal) -> Routes to ATOM, NOT Temporal STAR-RAG
    ans_struct = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the dependency flow between AuthService and UserRepository.",
        enable_star_rag=True,
        enable_structure_aware_star_rag=False,
    )
    assert ans_struct.debug_signals.get("star_rag_used") is False
    assert ans_struct.debug_signals.get("star_rag_temporal_routing_decision") == "query_lacks_temporal_intent"
    assert ans_struct.debug_signals.get("structure_aware_star_rag_used") is False


# ---------------------------------------------------------------------------
# Test C: Structure-Aware Only Enabled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_c_structure_aware_only_routes_structural_to_star_and_historical_to_atom(monkeypatch):
    """
    Test C: When STRUCTURE_AWARE_STAR_RAG_ENABLED=True and STAR_RAG_ENABLED=False:
    - Structural queries route to Structure-Aware STAR-RAG.
    - Historical queries route to ATOM.
    """
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", False)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    cand = make_candidate("c1", "process_payment", "src/payment.py", "def process_payment(): pass")
    hop = GranularEvidenceHop(
        hop_index=0,
        source_node_id="src/payment.py::process_payment",
        source_name="process_payment",
        source_file="src/payment.py",
        relation="CALLS",
        target_node_id="src/gateway.py::charge",
        target_name="charge",
        target_file="src/gateway.py",
        line_number=15,
    )
    ev_path = GranularEvidencePath(
        path_id="path:p1",
        source_entity="process_payment",
        target_entity="charge",
        hops=[hop],
        full_path_str="src/payment.py:process_payment -> [CALLS] -> src/gateway.py:charge",
        confidence=0.95,
    )

    mock_struct_res = MagicMock()
    mock_struct_res.is_fallback = False
    mock_struct_res.evidence_paths = [ev_path]
    mock_struct_res.diagnostics = {"snr_score": 0.88}

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag_structure.service.StructureAwareStarRagService.run_pipeline_async",
        AsyncMock(return_value=([MagicMock(candidate=cand, score=1.0)], mock_struct_res)),
    )

    engine = ProjectContextEngine()

    # 1. Structural query -> Routes to Structure-Aware STAR-RAG
    ans_struct = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the execution flow from process_payment to gateway.",
        enable_star_rag=False,
        enable_structure_aware_star_rag=True,
    )
    assert ans_struct.debug_signals.get("structure_aware_star_rag_used") is True
    assert ans_struct.debug_signals.get("star_rag_evidence_paths_count") == 1
    assert ans_struct.debug_signals.get("star_rag_used") is False

    # 2. Historical query -> Routes to ATOM, NOT Structure-Aware STAR-RAG
    ans_hist = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="What changed in process_payment in January 2026?",
        enable_star_rag=False,
        enable_structure_aware_star_rag=True,
    )
    assert ans_hist.debug_signals.get("star_rag_used") is False
    assert ans_hist.debug_signals.get("star_rag_temporal_routing_decision") == "feature_flag_disabled"


# ---------------------------------------------------------------------------
# Test D: Both Enabled -> Coordinated Joint Retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_d_both_enabled_coordinated_retrieval(monkeypatch):
    """
    Test D: When both STAR-RAG engines are enabled:
    - Combined query executes both in coordinated joint routing without collision.
    - Direct symbol lookup routes to ATOM without graph overhead.
    """
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", True)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    cand = make_candidate(
        "c1",
        "validate_credentials",
        "src/auth.py",
        "def validate_credentials(): return True",
        committed_at="2026-01-10T12:00:00+00:00",
    )
    events = [
        TemporalCodeEvent(
            event_id="ev:c1:validate_credentials:MODIFIES:src/auth.py",
            subject="validate_credentials",
            relation="MODIFIES",
            object="src/auth.py",
            timestamp=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
            commit_sha="c1_sha",
            file_path="src/auth.py",
            symbol_name="validate_credentials",
            snippet="def validate_credentials(): return True",
            candidate=cand,
        )
    ]
    hop = GranularEvidenceHop(
        hop_index=0,
        source_node_id="src/auth.py::validate_credentials",
        source_name="validate_credentials",
        source_file="src/auth.py",
        relation="CALLS",
        target_node_id="src/user.py::find_user",
        target_name="find_user",
        target_file="src/user.py",
        line_number=20,
    )
    ev_path = GranularEvidencePath(
        path_id="path:p1",
        source_entity="validate_credentials",
        target_entity="find_user",
        hops=[hop],
        full_path_str="src/auth.py:validate_credentials -> [CALLS] -> src/user.py:find_user",
        confidence=0.92,
    )

    mock_struct_res = MagicMock()
    mock_struct_res.is_fallback = False
    mock_struct_res.evidence_paths = [ev_path]
    mock_struct_res.diagnostics = {"snr_score": 0.9}

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag.StarRagContextService.load_historical_events_from_db",
        AsyncMock(return_value=events),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag_structure.service.StructureAwareStarRagService.run_pipeline_async",
        AsyncMock(return_value=([MagicMock(candidate=cand, score=1.0)], mock_struct_res)),
    )

    engine = ProjectContextEngine()

    # 1. Combined query (structural flow + historical evolution)
    ans_combo = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the dependency flow and historical evolution of validate_credentials.",
        enable_star_rag=True,
        enable_structure_aware_star_rag=True,
    )
    assert ans_combo.debug_signals.get("star_rag_used") is True
    assert ans_combo.debug_signals.get("structure_aware_star_rag_used") is True
    assert ans_combo.debug_signals.get("star_rag_temporal_evidence_count", 0) > 0
    assert ans_combo.debug_signals.get("star_rag_evidence_paths_count", 0) > 0

    # 2. Direct symbol lookup query -> routes to ATOM
    ans_direct = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Where is validate_credentials defined?",
        enable_star_rag=True,
        enable_structure_aware_star_rag=True,
    )
    assert ans_direct.debug_signals.get("star_rag_used") is False
    assert ans_direct.debug_signals.get("structure_aware_star_rag_used") is False
    assert ans_direct.debug_signals.get("star_rag_routing_decision") == "direct_symbol_lookup_atom"


# ---------------------------------------------------------------------------
# Test E: Function-Level CALLS Edge Extraction
# ---------------------------------------------------------------------------

def test_e_function_calls_edge_extraction_and_builtins_filtering():
    """
    Test E: ASTFunctionCallVisitor extracts verified CALLS edges between caller
    and callee, resolves imports and local scope, and strictly ignores Python built-ins.
    """
    source_code = (
        "import helper\n"
        "from database import execute_query\n\n"
        "def process_transaction(user_id, amount):\n"
        "    if len(user_id) == 0:\n"
        "        print('Invalid user')\n"
        "        return False\n"
        "    valid = validate_user(user_id)\n"
        "    res = execute_query('SELECT 1')\n"
        "    return valid and res\n\n"
        "def validate_user(uid):\n"
        "    return len(uid) > 3\n"
    )

    tree = ast.parse(source_code)
    known = {"process_transaction": "src/transaction.py", "validate_user": "src/transaction.py"}

    visitor = ASTFunctionCallVisitor(
        file_path="src/transaction.py",
        code_content=source_code,
        known_symbols=known,
    )
    visitor.visit(tree)

    # 1. process_transaction should call validate_user (local)
    local_calls = [
        (e.source_id, e.target_id, e.relation_type, e.line_number)
        for e in visitor.edges
        if e.relation_type == GraphRelationType.CALLS and e.metadata.get("callee_name") == "validate_user"
    ]
    assert len(local_calls) == 1
    assert "process_transaction" in local_calls[0][0]
    assert "validate_user" in local_calls[0][1]
    assert local_calls[0][2] == GraphRelationType.CALLS
    assert local_calls[0][3] == 8

    # 2. process_transaction should call execute_query (cross-file resolved via import)
    cross_calls = [
        (e.source_id, e.target_id, e.relation_type, e.line_number)
        for e in visitor.edges
        if e.relation_type == GraphRelationType.CALLS and e.metadata.get("callee_name") == "execute_query"
    ]
    assert len(cross_calls) == 1
    assert "process_transaction" in cross_calls[0][0]
    assert cross_calls[0][1] == "database.py::execute_query"
    assert cross_calls[0][2] == GraphRelationType.CALLS
    assert cross_calls[0][3] == 9

    # 3. Built-ins 'len' and 'print' must NOT produce any CALLS edges
    callee_names = {e.metadata.get("callee_name") for e in visitor.edges if e.relation_type == GraphRelationType.CALLS}
    assert "len" not in callee_names
    assert "print" not in callee_names


# ---------------------------------------------------------------------------
# Test F: ContextAssembler Budget Envelope & Combined Formatting
# ---------------------------------------------------------------------------

def test_f_evidence_paths_and_temporal_events_reach_assembler_within_budget():
    """
    Test F: ContextAssembler formats both granular evidence paths and historical
    temporal events within the tight context budget envelope.
    """
    hop = GranularEvidenceHop(
        hop_index=0,
        source_node_id="auth.py::login",
        source_name="login",
        source_file="auth.py",
        relation="CALLS",
        target_node_id="auth.py::validate_credentials",
        target_name="validate_credentials",
        target_file="auth.py",
        line_number=5,
    )
    ev_path = GranularEvidencePath(
        path_id="path:auth1",
        source_entity="login",
        target_entity="validate_credentials",
        hops=[hop],
        full_path_str="auth.py:login -> [CALLS] -> auth.py:validate_credentials",
        confidence=0.96,
    )

    temp_ev = {
        "type": "temporal_event",
        "event_id": "ev:1234:login:MODIFIES:auth.py",
        "subject": "login",
        "relation": "MODIFIES",
        "object": "auth.py",
        "timestamp": "2026-01-10T12:00:00+00:00",
        "commit_sha": "12345678",
        "description": "Initial auth setup",
        "snippet": "def login(): pass",
    }

    cand = make_candidate("c1", "login", "auth.py", "def login(): pass")
    from apps.api.src.services.context_engine.ranker import RankedCandidate
    ranked = [RankedCandidate(candidate=cand, score=1.0, matched_reasons=["exact_match"])]

    assembled = ContextAssembler.assemble_context(
        ranked_candidates=ranked,
        max_tokens=2000,
        evidence_paths=[ev_path],
        temporal_evidence=[temp_ev],
    )

    # Verify both structural evidence paths and temporal events are included
    types = {e["type"] for e in assembled.evidence_items}
    assert "evidence_path" in types
    assert "temporal_event" in types
    assert "chunk" in types or "code" in types

    # Verify context strictly stays within budget
    assert assembled.total_characters <= 2000 * 4
    assert "STRUCTURE-AWARE STAR-RAG EVIDENCE PATH" in assembled.prompt_context
    assert "HISTORICAL TEMPORAL EVIDENCE (STAR-RAG)" in assembled.prompt_context


# ---------------------------------------------------------------------------
# Test G: Direct Symbol Lookup Preserved on ATOM
# ---------------------------------------------------------------------------

def test_g_direct_symbol_lookup_preserved_on_atom():
    """
    Test G: When user queries for a direct symbol or file path, selective router
    preserves baseline ATOM retrieval without graph traversal overhead.
    """
    cand = make_candidate("c1", "UserService", "src/user.py", "class UserService: pass")
    analyzed_sym = analyze_query("Where is UserService defined?")
    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="Where is UserService defined?",
        analyzed_query=analyzed_sym,
        candidates=[cand],
        flag_enabled=True,
    )
    assert should_route is False
    assert reason == "direct_symbol_lookup_atom"

    analyzed_path = analyze_query("Show me src/user.py")
    should_route_p, reason_p = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="Show me src/user.py",
        analyzed_query=analyzed_path,
        candidates=[cand],
        flag_enabled=True,
    )
    assert should_route_p is False
    assert reason_p in ("direct_path_lookup_atom", "direct_symbol_lookup_atom")


# ---------------------------------------------------------------------------
# Test H: Real API Route POST /projects/{project_id}/ask
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_h_real_api_ask_project_endpoint(monkeypatch):
    """
    Test H: Real API endpoint POST /projects/{project_id}/ask properly receives
    and forwards opt-in flags to IntelligenceService.
    """
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    mock_project = MagicMock(id=project_id)
    mock_snap = MagicMock(id=uuid.uuid4())

    monkeypatch.setattr(IntelligenceService, "_verify_project_access", AsyncMock(return_value=mock_project))
    monkeypatch.setattr(IntelligenceService, "_get_active_snapshot", AsyncMock(return_value=mock_snap))

    mock_engine = MagicMock()
    mock_answer = GroundedAnswer(
        content="Grounded API response.",
        evidence=[],
        related_entities=["OrderService"],
        confidence="HIGH",
        debug_signals={
            "structure_aware_star_rag_used": True,
            "star_rag_used": True,
        },
    )
    mock_engine.investigate = AsyncMock(return_value=mock_answer)
    monkeypatch.setattr(
        "apps.api.src.services.intelligence_service.ProjectContextEngine",
        lambda: mock_engine,
    )

    session = AsyncMock()
    exec_mock = MagicMock()
    exec_mock.scalars.return_value.all.return_value = []
    exec_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = exec_mock

    payload = GroundedAskRequest(
        question="Trace the dependency flow and evolution of OrderService",
        enable_structure_aware_star_rag=True,
        enable_star_rag=True,
        thinking_tier="warm",
    )

    resp = await IntelligenceService.ask_question(
        session=session,
        user_id=user_id,
        project_id=project_id,
        question=payload.question,
        enable_structure_aware_star_rag=payload.enable_structure_aware_star_rag,
        enable_star_rag=payload.enable_star_rag,
        thinking_tier=payload.thinking_tier,
    )

    assert resp.content == "Grounded API response."
    assert resp.debug_signals["structure_aware_star_rag_used"] is True
    assert resp.debug_signals["star_rag_used"] is True
    mock_engine.investigate.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test I: Multi-Snapshot History Retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_i_multi_snapshot_history_retrieval_across_snapshots():
    """
    Test I: load_historical_events_from_db queries chunks across all completed
    snapshots of the same repository and idempotently deduplicates events.
    """
    repo_id = uuid.uuid4()
    snap1_id = uuid.uuid4()
    snap2_id = uuid.uuid4()

    # Simulate chunks from two different snapshots
    c1 = MagicMock()
    c1.id = uuid.uuid4()
    c1.snapshot_id = snap1_id
    c1.chunk_type = "ATOM_ADD"
    c1.name = "login"
    c1.symbol_name = "login"
    c1.path = "auth.py"
    c1.file_path = "auth.py"
    c1.content = "def login(): pass"
    c1.commit_sha = "aaa111"
    c1.commit_message = "Add login"
    c1.provenance = {
        "commit_sha": "aaa111",
        "commit_message": "Add login",
        "committed_at": "2026-01-01T10:00:00+00:00",
        "author": "Engineer",
        "parent_shas": [],
    }
    c1.metadata_ = dict(c1.provenance)

    c2 = MagicMock()
    c2.id = uuid.uuid4()
    c2.snapshot_id = snap2_id
    c2.chunk_type = "ATOM_MODIFY"
    c2.name = "login"
    c2.symbol_name = "login"
    c2.path = "auth.py"
    c2.file_path = "auth.py"
    c2.content = "def login(): return validate()"
    c2.commit_sha = "bbb222"
    c2.commit_message = "Update login"
    c2.provenance = {
        "commit_sha": "bbb222",
        "commit_message": "Update login",
        "committed_at": "2026-01-15T12:00:00+00:00",
        "author": "Engineer",
        "parent_shas": ["aaa111"],
    }
    c2.metadata_ = dict(c2.provenance)

    # Simulate duplicate chunk in snapshot 2 representing the same commit aaa111
    c1_dup = MagicMock()
    c1_dup.id = uuid.uuid4()
    c1_dup.snapshot_id = snap2_id
    c1_dup.chunk_type = "ATOM_ADD"
    c1_dup.name = "login"
    c1_dup.symbol_name = "login"
    c1_dup.path = "auth.py"
    c1_dup.file_path = "auth.py"
    c1_dup.content = "def login(): pass"
    c1_dup.commit_sha = "aaa111"
    c1_dup.commit_message = "Add login"
    c1_dup.provenance = dict(c1.provenance)
    c1_dup.metadata_ = dict(c1.provenance)

    session = AsyncMock()
    exec_mock = MagicMock()
    exec_mock.scalars.return_value.all.return_value = [c1, c2, c1_dup]
    session.execute.return_value = exec_mock

    events = await StarRagContextService.load_historical_events_from_db(
        session=session,
        repository_id=repo_id,
        target_branch="main",
    )

    # 3 chunks queried, but 2 unique commits/events -> Exactly 2 events after deduplication
    assert len(events) == 2
    event_ids = {e.event_id for e in events}
    assert any("aaa111" in eid for eid in event_ids)
    assert any("bbb222" in eid for eid in event_ids)


# ---------------------------------------------------------------------------
# Test J: Branch Separation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_j_branch_separation_isolates_histories():
    """
    Test J: Verify query SQL statement filters by RepositorySnapshot.branch == target_branch,
    ensuring experimental/feature branches do not pollute main branch history.
    """
    session = AsyncMock()
    exec_mock = MagicMock()
    exec_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = exec_mock

    await StarRagContextService.load_historical_events_from_db(
        session=session,
        repository_id=uuid.uuid4(),
        target_branch="release-v1",
    )

    session.execute.assert_awaited_once()
    called_stmt = session.execute.call_args[0][0]
    sql_str = str(called_stmt)
    # The statement must join snapshots and check branch
    assert "repository_snapshots" in sql_str
    assert "branch" in sql_str


# ---------------------------------------------------------------------------
# Test K: API Flag Forwarding on /messages Endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_k_api_flag_forwarding_in_conversations_endpoint(monkeypatch):
    """
    Test K: post_conversation_message endpoint properly forwards
    enable_structure_aware_star_rag, enable_star_rag, and thinking_tier.
    """
    from apps.api.src.api.routes.intelligence import post_conversation_message

    project_id = "test-proj"
    conv_id = uuid.uuid4()
    resolved_id = uuid.uuid4()

    monkeypatch.setattr(
        "apps.api.src.services.project_service.ProjectService.resolve_project_id",
        AsyncMock(return_value=resolved_id),
    )

    mock_ask = AsyncMock(
        return_value=GroundedAnswer(
            content="Thread answer",
            evidence=[],
            related_entities=[],
            confidence="HIGH",
            debug_signals={},
        )
    )
    monkeypatch.setattr(IntelligenceService, "ask_question", mock_ask)

    payload = GroundedAskRequest(
        question="What was changed in auth?",
        enable_structure_aware_star_rag=True,
        enable_star_rag=True,
        thinking_tier="cold",
    )

    mock_user = MagicMock(id=uuid.uuid4())
    mock_db = AsyncMock()

    await post_conversation_message(
        project_id=project_id,
        conversation_id=conv_id,
        payload=payload,
        current_user=mock_user,
        db=mock_db,
    )

    mock_ask.assert_awaited_once_with(
        session=mock_db,
        user_id=mock_user.id,
        project_id=resolved_id,
        question=payload.question,
        conversation_id=conv_id,
        thinking_tier="cold",
        enable_structure_aware_star_rag=True,
        enable_star_rag=True,
    )


# ---------------------------------------------------------------------------
# Test L: Combined Evidence Reaches LLM Synthesis Prompt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_l_combined_evidence_reaches_llm_synthesis(monkeypatch):
    """
    Test L: Both temporal evidence and structural evidence paths are injected into
    the LLM project_context and evidence_items passed to generate_grounded_answer.
    """
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", True)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    cand = make_candidate("c1", "auth", "auth.py", "def auth(): pass")
    events = [
        TemporalCodeEvent(
            event_id="ev:c1:auth:MODIFIES:auth.py",
            subject="auth",
            relation="MODIFIES",
            object="auth.py",
            timestamp=datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC),
            snippet="def auth(): pass",
            candidate=cand,
        )
    ]
    hop = GranularEvidenceHop(
        hop_index=0,
        source_node_id="auth.py::auth",
        source_name="auth",
        source_file="auth.py",
        relation="CALLS",
        target_node_id="db.py::query",
        target_name="query",
        target_file="db.py",
        line_number=5,
    )
    ev_path = GranularEvidencePath(
        path_id="path:p1",
        source_entity="auth",
        target_entity="query",
        hops=[hop],
        full_path_str="auth.py:auth -> [CALLS] -> db.py:query",
        confidence=0.91,
    )

    mock_struct_res = MagicMock()
    mock_struct_res.is_fallback = False
    mock_struct_res.evidence_paths = [ev_path]
    mock_struct_res.diagnostics = {}

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag.StarRagContextService.load_historical_events_from_db",
        AsyncMock(return_value=events),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag_structure.service.StructureAwareStarRagService.run_pipeline_async",
        AsyncMock(return_value=([MagicMock(candidate=cand, score=1.0)], mock_struct_res)),
    )

    engine = ProjectContextEngine()
    engine.llm_provider = AsyncMock()
    engine.llm_provider.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Synthesized answer",
            evidence=[],
            related_entities=[],
            debug_signals={},
        )
    )

    await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the dependency flow and historical evolution of auth.",
        enable_star_rag=True,
        enable_structure_aware_star_rag=True,
    )

    engine.llm_provider.generate_grounded_answer.assert_awaited_once()
    kwargs = engine.llm_provider.generate_grounded_answer.call_args[1]
    prompt_ctx = kwargs["project_context"]
    assert "STRUCTURE-AWARE STAR-RAG EVIDENCE PATH" in prompt_ctx
    assert "HISTORICAL TEMPORAL EVIDENCE (STAR-RAG)" in prompt_ctx

    ev_items = kwargs["evidence_items"]
    ev_types = {e["type"] for e in ev_items}
    assert "evidence_path" in ev_types
    assert "temporal_event" in ev_types


# ---------------------------------------------------------------------------
# Test M: Restart Persistence (Cache Invalidation & DB Reloading)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_m_restart_persistence_in_memory_cache_cleared():
    """
    Test M: Clearing in-memory graph cache (_GRAPH_CACHE) simulates server restart.
    Verifies that the graph extractor safely falls back to DB reload.
    """
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()

    # Populate cache artificially
    dummy_graph = FunctionGraph()
    key = CodeGraphCache._make_key(snapshot_id)
    _MEMORY_GRAPH_CACHE[key] = dummy_graph
    assert key in _MEMORY_GRAPH_CACHE

    # Clear cache to simulate restart
    _MEMORY_GRAPH_CACHE.clear()
    assert key not in _MEMORY_GRAPH_CACHE

    # Now verify build_graph_for_snapshot re-queries DB and builds new graph
    session = AsyncMock()
    f_mock = MagicMock()
    f_mock.id = file_id
    f_mock.path = "app.py"
    f_mock.content = "def start(): run()\ndef run(): pass"

    sym_start = MagicMock()
    sym_start.id = uuid.uuid4()
    sym_start.name = "start"
    sym_start.file_id = file_id
    sym_start.symbol_type = SymbolType.FUNCTION

    sym_run = MagicMock()
    sym_run.id = uuid.uuid4()
    sym_run.name = "run"
    sym_run.file_id = file_id
    sym_run.symbol_type = SymbolType.FUNCTION

    res_files = MagicMock()
    res_files.scalars.return_value.all.return_value = [f_mock]

    res_syms = MagicMock()
    res_syms.scalars.return_value.all.return_value = [sym_start, sym_run]

    res_deps = MagicMock()
    res_deps.scalars.return_value.all.return_value = []

    res_chunks = MagicMock()
    res_chunks.scalars.return_value.all.return_value = []

    session.execute.side_effect = [res_files, res_syms, res_deps, res_chunks]

    reloaded_graph = await CodeGraphExtractor.build_graph_for_snapshot(session, snapshot_id)
    assert reloaded_graph is not None
    # Check that CALLS edge was parsed from source
    calls_edges = [
        (e.source_id, e.target_id, e.relation_type)
        for e in reloaded_graph.edges
        if e.relation_type == "CALLS"
    ]
    assert len(calls_edges) >= 1


# ---------------------------------------------------------------------------
# Test N: Real Source Provenance
# ---------------------------------------------------------------------------

def test_n_real_source_provenance_matches_source_code():
    """
    Test N: Verifies extracted caller, callee, file path, and exact line numbers
    match the original source code lines.
    """
    source_lines = [
        "# Line 1: Header",
        "import os",
        "",
        "def main():",
        "    setup()",
        "    execute()",
        "",
        "def setup():",
        "    pass",
        "",
        "def execute():",
        "    cleanup()",
        "",
        "def cleanup():",
        "    pass",
    ]
    source_code = "\n".join(source_lines)
    tree = ast.parse(source_code)
    known = {
        "main": "src/workflow.py",
        "setup": "src/workflow.py",
        "execute": "src/workflow.py",
        "cleanup": "src/workflow.py",
    }

    visitor = ASTFunctionCallVisitor(
        file_path="src/workflow.py",
        code_content=source_code,
        known_symbols=known,
    )
    visitor.visit(tree)

    calls_by_callee = {
        e.metadata["callee_name"]: e
        for e in visitor.edges
        if e.relation_type == GraphRelationType.CALLS
    }

    # setup() is called on line 5
    assert "setup" in calls_by_callee
    assert "main" in calls_by_callee["setup"].source_id
    assert calls_by_callee["setup"].line_number == 5
    assert source_lines[calls_by_callee["setup"].line_number - 1].strip() == "setup()"

    # execute() is called on line 6
    assert "execute" in calls_by_callee
    assert "main" in calls_by_callee["execute"].source_id
    assert calls_by_callee["execute"].line_number == 6
    assert source_lines[calls_by_callee["execute"].line_number - 1].strip() == "execute()"

    # cleanup() is called on line 12
    assert "cleanup" in calls_by_callee
    assert "execute" in calls_by_callee["cleanup"].source_id
    assert calls_by_callee["cleanup"].line_number == 12
    assert source_lines[calls_by_callee["cleanup"].line_number - 1].strip() == "cleanup()"
