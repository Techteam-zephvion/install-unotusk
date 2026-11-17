"""
Integration tests for Structure-Aware STAR-RAG in Unotusk Code Lane.
Validates end-to-end ProjectContextEngine integration, feature flag toggling,
and fallback safeguards.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.llm.base import GroundedAnswer


@pytest.mark.asyncio
async def test_structure_aware_star_rag_disabled_by_default(monkeypatch):
    """Verify that Structure-Aware STAR-RAG is opt-in and disabled by default."""
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", False)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    question = "How does user authentication work?"

    session = AsyncMock()
    # Mock snapshot and repository queries
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    # Mock MultiSignalRetriever returning empty list to test flow
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[]),
    )

    engine = ProjectContextEngine()
    engine.llm_provider = AsyncMock()
    engine.llm_provider.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Grounded answer",
            evidence=[],
            related_entities=[],
            debug_signals={},
        )
    )

    answer = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question=question,
    )

    assert answer.debug_signals.get("structure_aware_star_rag_used") is False


@pytest.mark.asyncio
async def test_structure_aware_star_rag_enabled_runs_pipeline(monkeypatch):
    """Verify that when enabled, Structure-Aware STAR-RAG runs SNR, DTP, and SSAF."""
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()
    question = "Trace the dependency chain from payment API to database ledger."

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    # Create mock candidates with code content
    from apps.api.src.services.context_engine.retriever import RetrievedCandidate

    c1 = RetrievedCandidate(
        candidate_id="chunk:api",
        entity_type="CHUNK",
        name="checkout_endpoint",
        path="api/checkout.py",
        start_line=1,
        end_line=20,
        content="def checkout_endpoint(): payment_service.process()",
        file_id=file_id,
        signals={"file_match": 1.2, "vector_similarity": 0.8},
    )
    c2 = RetrievedCandidate(
        candidate_id="chunk:service",
        entity_type="CHUNK",
        name="payment_service",
        path="services/payment.py",
        start_line=1,
        end_line=20,
        content="def process(): ledger.persist()",
        file_id=file_id,
        signals={"vector_similarity": 0.75},
    )

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[c1, c2]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[c1, c2]),
    )

    engine = ProjectContextEngine()
    engine.llm_provider = AsyncMock()
    engine.llm_provider.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Payment flow connects api -> service -> ledger.",
            evidence=[],
            related_entities=[],
            debug_signals={},
        )
    )

    answer = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question=question,
        enable_structure_aware_star_rag=True,
    )

    assert answer.debug_signals.get("structure_aware_star_rag_used") is True
    diag = answer.debug_signals.get("structure_aware_star_rag_diagnostics", {})
    assert diag.get("is_fallback") is False
    assert "nodes_count" in diag
    assert diag.get("snr_enabled") is True
    assert diag.get("dtp_enabled") is True
    assert diag.get("ssaf_enabled") is True


@pytest.mark.asyncio
async def test_structure_aware_star_rag_fallback_on_exception(monkeypatch):
    """Verify safe fallback to baseline ranking when an unexpected error occurs."""
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    from apps.api.src.services.context_engine.retriever import RetrievedCandidate

    c1 = RetrievedCandidate(
        candidate_id="chunk:fallback",
        entity_type="CHUNK",
        name="fallback_func",
        path="test.py",
        start_line=1,
        end_line=5,
        content="pass",
        file_id=file_id,
        signals={"vector_similarity": 0.8},
    )

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[c1]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[c1]),
    )

    # Force an exception in StructureAwareStarRagService.run_pipeline_async
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag_structure.service.StructureAwareStarRagService.run_pipeline_async",
        AsyncMock(side_effect=RuntimeError("Simulated pipeline glitch")),
    )

    engine = ProjectContextEngine()
    engine.llm_provider = AsyncMock()
    engine.llm_provider.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Safe fallback answer",
            evidence=[],
            related_entities=[],
            debug_signals={},
        )
    )

    answer = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the dependency flow in fallback",
        enable_structure_aware_star_rag=True,
    )

    # Should fall back cleanly without failing investigate()
    assert answer.debug_signals.get("structure_aware_star_rag_used") is False
    diag = answer.debug_signals.get("structure_aware_star_rag_diagnostics", {})
    assert diag.get("exception_occurred") is True
    assert "Simulated pipeline glitch" in diag.get("error", "")
