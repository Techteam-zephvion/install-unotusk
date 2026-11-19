"""
End-to-End Runtime Integration Tests for Structure-Aware STAR-RAG.
Validates selective routing, graph retrieval, evidence path assembly,
LLM synthesis consumption, API integration, and fallback safeguards.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.models.enums import SnapshotStatus
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol, SymbolType
from apps.api.src.schemas.intelligence import GroundedAskRequest
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.selective_router import (
    StarRagSelectiveRouter,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    GranularEvidenceHop,
    GranularEvidencePath,
)
from apps.api.src.services.intelligence_service import IntelligenceService
from apps.api.src.services.llm.claude import ClaudeProvider
from apps.api.src.services.llm.groq import GroqProvider


@pytest.mark.asyncio
async def test_a_runtime_flag_disabled_by_default(monkeypatch):
    """
    Test A: Safety Gate & Default Behavior.
    When STRUCTURE_AWARE_STAR_RAG_ENABLED is False and not overridden,
    STAR-RAG is strictly bypassed and ATOM executes.
    """
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", False)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    question = "Trace the execution flow and call hierarchy of payment processing"

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    # Mock candidate retrieval
    cand = RetrievedCandidate(
        candidate_id="c1",
        entity_type="SYMBOL",
        name="process_charge",
        path="src/payment.py",
        start_line=1,
        end_line=20,
        content="def process_charge(): pass",
        file_id=file_id,
        signals={"exact_match": 1.5},
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[cand]),
    )

    engine = ProjectContextEngine()
    answer = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question=question,
        enable_structure_aware_star_rag=None,  # Default
    )

    assert answer.debug_signals.get("structure_aware_star_rag_used") is False
    assert answer.debug_signals.get("star_rag_routing_decision") == "feature_flag_disabled"


@pytest.mark.asyncio
async def test_b_runtime_opt_in_direct_symbol_lookup_atom(monkeypatch):
    """
    Test B: Router Preservation.
    When enable_structure_aware_star_rag=True, direct symbol lookups without
    structural intent are preserved on Baseline ATOM without graph overhead.
    """
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    question = "Where is process_charge defined?"

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    cand = RetrievedCandidate(
        candidate_id="c1",
        entity_type="SYMBOL",
        name="process_charge",
        path="src/payment.py",
        start_line=1,
        end_line=20,
        content="def process_charge(): pass",
        file_id=file_id,
        signals={"exact_match": 1.5},
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[cand]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[cand]),
    )

    engine = ProjectContextEngine()
    answer = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question=question,
        enable_structure_aware_star_rag=True,
    )

    assert answer.debug_signals.get("structure_aware_star_rag_used") is False
    assert answer.debug_signals.get("star_rag_routing_decision") == "direct_symbol_lookup_atom"


@pytest.mark.asyncio
async def test_c_runtime_opt_in_structural_tracing_intent():
    """
    Test C: Selective Routing Verification.
    Structural query triggers 'structural_tracing_intent'.
    """
    analyzed = analyze_query("Trace the call hierarchy and callers of checkout_endpoint")
    c1 = RetrievedCandidate(
        candidate_id="c1",
        entity_type="SYMBOL",
        name="checkout_endpoint",
        path="api/checkout.py",
        start_line=1,
        end_line=20,
        content="def checkout_endpoint(): pass",
        file_id=uuid.uuid4(),
    )
    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="Trace the call hierarchy and callers of checkout_endpoint",
        analyzed_query=analyzed,
        candidates=[c1],
        flag_enabled=True,
    )
    assert should_route is True
    assert reason == "structural_tracing_intent"


@pytest.mark.asyncio
async def test_d_runtime_evidence_paths_context_assembler():
    """
    Test D: Evidence Path Context Assembly.
    Verifies that GranularEvidencePaths are formatted into prompt context
    and included as first-class evidence items.
    """
    file_id = uuid.uuid4()
    cand = RetrievedCandidate(
        candidate_id="c1",
        entity_type="SYMBOL",
        name="PaymentService",
        path="src/payment.py",
        start_line=10,
        end_line=50,
        content="class PaymentService:\n    def process_charge(self): pass",
        file_id=file_id,
    )
    ranked = [RankedCandidate(candidate=cand, score=0.92, matched_reasons=["exact_match"])]

    hop1 = GranularEvidenceHop(
        hop_index=0,
        source_node_id="api:checkout",
        source_name="checkout_endpoint",
        source_file="api/checkout.py",
        relation="CALLS",
        target_node_id="svc:payment",
        target_name="PaymentService",
        target_file="src/payment.py",
        line_number=15,
    )
    path = GranularEvidencePath(
        path_id="path:test-1234",
        source_entity="checkout_endpoint",
        target_entity="PaymentService",
        hops=[hop1],
        full_path_str="api/checkout.py:checkout_endpoint -> [CALLS] -> src/payment.py:PaymentService",
        confidence=0.95,
        provenance={"engine": "structure_aware_star_rag"},
    )

    assembled = ContextAssembler.assemble_context(
        ranked_candidates=ranked,
        evidence_paths=[path],
    )

    assert assembled.evidence_path_count == 1
    assert len(assembled.evidence_paths) == 1
    assert "## STRUCTURE-AWARE STAR-RAG EVIDENCE PATHS" in assembled.prompt_context
    assert "checkout_endpoint -> PaymentService" in assembled.prompt_context
    assert "CALLS" in assembled.prompt_context

    ev_path_items = [e for e in assembled.evidence_items if e.get("type") == "evidence_path"]
    assert len(ev_path_items) == 1
    first_ev = ev_path_items[0]
    assert first_ev["symbol"] == "checkout_endpoint -> PaymentService"
    assert first_ev["relationship_path"] == path.full_path_str
    assert first_ev["relevance"] == 0.95
    assert "checkout_endpoint" in assembled.related_entities
    assert "PaymentService" in assembled.related_entities


@pytest.mark.asyncio
async def test_e_runtime_offline_llm_synthesis_incorporates_paths():
    """
    Test E: Grounded Synthesis with Structural Evidence.
    Verifies that offline synthesis by ClaudeProvider and GroqProvider
    synthesizes structural call paths into the answer without hallucination.
    """
    evidence = [
        {
            "type": "evidence_path",
            "file": "api/checkout.py",
            "symbol": "checkout_endpoint -> PaymentService",
            "lines": "15",
            "relevance": 0.95,
            "snippet": "Structural call path: api/checkout.py:checkout_endpoint -> [CALLS] -> src/payment.py:PaymentService",
            "relationship_path": "api/checkout.py:checkout_endpoint -> [CALLS] -> src/payment.py:PaymentService",
        },
        {
            "type": "symbol",
            "file": "src/payment.py",
            "symbol": "PaymentService",
            "lines": "10-50",
            "relevance": 0.90,
            "snippet": "class PaymentService: pass",
        },
    ]

    claude = ClaudeProvider(api_key=None)
    ans_claude = await claude.generate_grounded_answer(
        question="Trace the call hierarchy from checkout to payment",
        project_context="## STRUCTURE-AWARE STAR-RAG EVIDENCE PATHS\n### checkout_endpoint -> PaymentService",
        evidence_items=evidence,
        related_entities=["checkout_endpoint", "PaymentService"],
    )

    assert ans_claude.confidence == "HIGH"
    assert "Structural Call Path" in ans_claude.content
    assert "checkout_endpoint -> [CALLS] -> src/payment.py:PaymentService" in ans_claude.content

    groq = GroqProvider(api_key=None)
    ans_groq = await groq.generate_grounded_answer(
        question="Trace the call hierarchy from checkout to payment",
        project_context="## STRUCTURE-AWARE STAR-RAG EVIDENCE PATHS\n### checkout_endpoint -> PaymentService",
        evidence_items=evidence,
        related_entities=["checkout_endpoint", "PaymentService"],
    )

    assert ans_groq.confidence == "HIGH"
    assert "Structural Call Path" in ans_groq.content
    assert "checkout_endpoint -> [CALLS] -> src/payment.py:PaymentService" in ans_groq.content


@pytest.mark.asyncio
async def test_f_runtime_investigate_end_to_end_with_star_rag(monkeypatch):
    """
    Test F: Complete ProjectContextEngine.investigate() run with Structure-Aware STAR-RAG.
    Verifies graph retrieval, DTP propagation, path construction, context assembly,
    and output evidence items.
    """
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id_1 = uuid.uuid4()
    file_id_2 = uuid.uuid4()
    sym_id_1 = uuid.uuid4()
    sym_id_2 = uuid.uuid4()

    f1 = RepositoryFile(
        id=file_id_1,
        snapshot_id=snapshot_id,
        path="api/checkout.py",
        filename="checkout.py",
        line_count=30,
    )
    f2 = RepositoryFile(
        id=file_id_2,
        snapshot_id=snapshot_id,
        path="services/payment.py",
        filename="payment.py",
        line_count=40,
    )
    s1 = CodeSymbol(
        id=sym_id_1,
        file_id=file_id_1,
        name="checkout_endpoint",
        qualified_name="api.checkout.checkout_endpoint",
        symbol_type=SymbolType.FUNCTION,
        start_line=5,
        end_line=25,
    )
    s2 = CodeSymbol(
        id=sym_id_2,
        file_id=file_id_2,
        name="PaymentService",
        qualified_name="services.payment.PaymentService",
        symbol_type=SymbolType.CLASS,
        start_line=1,
        end_line=35,
    )

    c1 = RetrievedCandidate(
        candidate_id=f"sym:{sym_id_1}",
        entity_type="SYMBOL",
        name="checkout_endpoint",
        path="api/checkout.py",
        start_line=5,
        end_line=25,
        content="def checkout_endpoint(): payment_service.charge()",
        file_id=file_id_1,
        symbol_id=sym_id_1,
        signals={"file_match": 1.5, "vector_similarity": 0.85},
    )
    c2 = RetrievedCandidate(
        candidate_id=f"sym:{sym_id_2}",
        entity_type="SYMBOL",
        name="PaymentService",
        path="services/payment.py",
        start_line=1,
        end_line=35,
        content="class PaymentService:\n    def charge(self): pass",
        file_id=file_id_2,
        symbol_id=sym_id_2,
        signals={"vector_similarity": 0.78},
    )

    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repository_snapshots" in stmt_str or "repositorysnapshot" in stmt_str:
            mock_res.scalar_one_or_none.return_value = repo_id
        elif "from repository_files" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [f1, f2]
        elif "from code_symbols" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [s1, s2]
        elif "from code_dependencies" in stmt_str:
            mock_res.scalars.return_value.all.return_value = []
        elif "from project_knowledge" in stmt_str:
            mock_res.scalars.return_value.all.return_value = []
        else:
            mock_res.scalar_one_or_none.return_value = None
            mock_res.scalars.return_value.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[c1, c2]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[c1, c2]),
    )

    engine = ProjectContextEngine()
    answer = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the execution flow and call dependencies of checkout_endpoint",
        enable_structure_aware_star_rag=True,
    )

    assert answer.debug_signals.get("structure_aware_star_rag_used") is True
    assert answer.debug_signals.get("star_rag_routing_decision") == "structural_tracing_intent"
    assert answer.confidence in ("HIGH", "MEDIUM")
    assert len(answer.evidence) >= 1


@pytest.mark.asyncio
async def test_g_runtime_graph_exception_graceful_fallback(monkeypatch):
    """
    Test G: Safe Fallback on Graph Retrieval Exception.
    When an unexpected error happens inside STAR-RAG, the pipeline
    gracefully falls back to baseline ranking without raising.
    """
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    c1 = RetrievedCandidate(
        candidate_id="c1",
        entity_type="SYMBOL",
        name="test_symbol",
        path="src/test.py",
        start_line=1,
        end_line=10,
        content="def test_symbol(): pass",
        file_id=file_id,
        signals={"exact_match": 1.5},
    )

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[c1]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[c1]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag_structure.service.StructureAwareStarRagService.run_pipeline_async",
        AsyncMock(side_effect=RuntimeError("Transient database graph fault")),
    )

    engine = ProjectContextEngine()
    answer = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the call hierarchy of test_symbol",
        enable_structure_aware_star_rag=True,
    )

    assert answer.debug_signals.get("structure_aware_star_rag_used") is False
    diag = answer.debug_signals.get("structure_aware_star_rag_diagnostics", {})
    assert diag.get("exception_occurred") is True
    assert "Transient database graph fault" in diag.get("error", "")
    assert answer.confidence in ("HIGH", "MEDIUM", "LOW")


@pytest.mark.asyncio
async def test_h_runtime_api_ask_question_with_star_rag_opt_in(monkeypatch):
    """
    Test H: Verification of IntelligenceService.ask_question with enable_structure_aware_star_rag=True.
    Verifies that API request schemas propagate the flag, invoke the pipeline, and return
    first-class evidence items.
    """
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    session = AsyncMock()
    session.add = MagicMock()
    user_id = uuid.uuid4()
    project_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_project = MagicMock()
    mock_project.id = project_id

    mock_snap = MagicMock()
    mock_snap.id = snap_id
    mock_snap.status = SnapshotStatus.COMPLETED

    monkeypatch.setattr(
        IntelligenceService, "_verify_project_access", AsyncMock(return_value=mock_project)
    )
    monkeypatch.setattr(
        IntelligenceService, "_get_active_snapshot", AsyncMock(return_value=mock_snap)
    )

    # Mock execute response for conversations and messages queries
    exec_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    exec_mock.scalars.return_value = scalars_mock
    exec_mock.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=exec_mock)

    mock_engine = MagicMock()
    hop = GranularEvidenceHop(
        hop_index=0,
        source_node_id="src/a.py::f1",
        source_name="f1",
        source_file="src/a.py",
        relation="CALLS",
        target_node_id="src/b.py::f2",
        target_name="f2",
        target_file="src/b.py",
    )
    ev_path = GranularEvidencePath(
        path_id="path:p1",
        source_entity="f1",
        target_entity="f2",
        hops=[hop],
        full_path_str="src/a.py:f1 -> [CALLS] -> src/b.py:f2",
        confidence=0.92,
    )
    mock_answer = MagicMock()
    mock_answer.content = "Traced call hierarchy from f1 to f2."
    mock_answer.evidence = [
        {
            "type": "evidence_path",
            "file": "src/a.py",
            "symbol": "f1 -> f2",
            "lines": "1",
            "relevance": 0.92,
            "snippet": f"Structural call path: {ev_path.full_path_str}",
            "relationship_path": ev_path.full_path_str,
        }
    ]
    mock_answer.related_entities = ["f1", "f2"]
    mock_answer.confidence = "HIGH"
    mock_answer.debug_signals = {
        "structure_aware_star_rag_used": True,
        "star_rag_evidence_paths_count": 1,
        "star_rag_routing_decision": "structural_tracing_intent",
    }
    mock_engine.investigate = AsyncMock(return_value=mock_answer)
    monkeypatch.setattr(
        "apps.api.src.services.intelligence_service.ProjectContextEngine",
        lambda: mock_engine,
    )

    # Test GroundedAskRequest schema validation
    req = GroundedAskRequest(
        question="Trace the call hierarchy between f1 and f2",
        enable_structure_aware_star_rag=True,
    )
    assert req.enable_structure_aware_star_rag is True

    resp = await IntelligenceService.ask_question(
        session=session,
        user_id=user_id,
        project_id=project_id,
        question=req.question,
        enable_structure_aware_star_rag=req.enable_structure_aware_star_rag,
    )

    assert resp.content == "Traced call hierarchy from f1 to f2."
    assert resp.confidence == "HIGH"
    assert resp.debug_signals["structure_aware_star_rag_used"] is True
    assert resp.debug_signals["star_rag_evidence_paths_count"] == 1
    assert len(resp.evidence) == 1
    assert resp.evidence[0].type == "evidence_path"
