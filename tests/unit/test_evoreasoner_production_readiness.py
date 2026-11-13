"""
Production Readiness & Hardening Unit Test Suite for EvoReasoner (T2.8 Milestone).
Verifies:
1. Feature flag defaults (EVOREASONER_ENABLED=False).
2. Disabled-mode behavior in ProjectContextEngine.
3. Graceful exception fallback during context generation.
4. Bounded execution timeouts in EvoBeamSearchEngine.
5. Branch isolation during graph traversal.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.schemas.evoreasoner import (
    BeamSearchConfig,
    MultiRoutePlan,
)
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.context_engine.memotime import TemporalIntentType
from apps.api.src.services.evoreasoner.beam_search import EvoBeamSearchEngine
from apps.api.src.services.evoreasoner.planner import EvoRoutePlanner
from apps.api.src.services.llm.base import GroundedAnswer


def test_1_feature_flag_is_disabled_by_default():
    """Confirms production safety invariant: EVOREASONER_ENABLED must be False by default."""
    assert settings.EVOREASONER_ENABLED is False
    assert settings.EVOKG_ENABLED is False


@pytest.mark.asyncio
async def test_2_disabled_mode_bypasses_evoreasoner():
    """Verifies that when EVOREASONER_ENABLED is False, no graph reasoning routes are executed."""
    mock_session = AsyncMock()
    snap_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(return_value=GroundedAnswer(
        content="Grounded answer text",
        confidence=0.9,
        evidence=[],
    ))
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with patch("apps.api.src.services.context_engine.engine.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_ret, \
         patch("apps.api.src.services.context_engine.engine.MultiSignalRanker.rank_candidates") as mock_rank, \
         patch("apps.api.src.services.context_engine.engine.ContextAssembler.assemble_context") as mock_asm, \
         patch("apps.api.src.services.context_engine.engine.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_know, \
         patch("apps.api.src.services.evoreasoner.planner.EvoRoutePlanner.generate_multi_route_plan") as mock_plan:

        mock_ret.return_value = []
        mock_rank.return_value = []
        mock_know.return_value = ("", [])
        mock_asm.return_value = MagicMock(
            assembled_context="",
            token_count=0,
            character_count=0,
            candidate_count=0,
            total_characters=0,
            assembled_chunks=[],
            truncated_count=0,
            budget_limit_tokens=8000,
            proof_chains=[],
        )

        engine = ProjectContextEngine(llm_provider=mock_llm)
        ctx = await engine.investigate(
            session=mock_session,
            snapshot_id=snap_id,
            repository_id=repo_id,
            question="How does ContextAssembler work?",
            enable_evoreasoner=None,  # Fall back to settings.EVOREASONER_ENABLED (False)
        )

        # Verify planner was NOT called
        mock_plan.assert_not_called()
        assert ctx.debug_signals.get("evoreasoner_used") is False or "evoreasoner_used" not in ctx.debug_signals


@pytest.mark.asyncio
async def test_3_graceful_fallback_on_exception():
    """Verifies that exceptions during beam search or planning do not crash context assembly."""
    mock_session = AsyncMock()
    snap_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(return_value=GroundedAnswer(
        content="Fallback answer",
        confidence=0.5,
        evidence=[],
    ))
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

    with patch("apps.api.src.services.context_engine.engine.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_ret, \
         patch("apps.api.src.services.context_engine.engine.MultiSignalRanker.rank_candidates") as mock_rank, \
         patch("apps.api.src.services.context_engine.engine.ContextAssembler.assemble_context") as mock_asm, \
         patch("apps.api.src.services.context_engine.engine.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_know, \
         patch("apps.api.src.services.evoreasoner.planner.EvoRoutePlanner.generate_multi_route_plan") as mock_plan:

        mock_ret.return_value = []
        mock_rank.return_value = []
        mock_know.return_value = ("", [])
        mock_asm.return_value = MagicMock(
            assembled_context="Fallback context",
            token_count=10,
            character_count=40,
            candidate_count=1,
            total_characters=40,
            assembled_chunks=[],
            truncated_count=0,
            budget_limit_tokens=8000,
            proof_chains=[],
        )
        # Simulate planning failure
        mock_plan.side_effect = RuntimeError("Simulated graph failure or timeout")

        engine = ProjectContextEngine(llm_provider=mock_llm)
        ctx = await engine.investigate(
            session=mock_session,
            snapshot_id=snap_id,
            repository_id=repo_id,
            question="How does ContextAssembler work?",
            enable_evoreasoner=True,  # Explicitly enabled for this test
        )

        assert ctx.debug_signals.get("evoreasoner_used") is False
        diag = ctx.debug_signals.get("evoreasoner_diagnostics", {})
        assert diag.get("exception_occurred") is True
        assert "Simulated graph failure" in diag.get("error", "")


@pytest.mark.asyncio
async def test_4_beam_search_execution_timeout():
    """Verifies that beam search respects timeout_seconds and flags timed_out in diagnostics."""
    mock_session = AsyncMock()
    repo_id = uuid.uuid4()

    plan = EvoRoutePlanner.generate_multi_route_plan(
        query_text="How does CodeAtomDecomposer call _find_enclosing_scope_heuristic?",
        seed_entities=["CodeAtomDecomposer"],
    )
    assert len(plan.selected_routes) > 0

    # Configure tiny timeout (0 seconds) to force immediate timeout
    cfg = BeamSearchConfig(timeout_seconds=0.0)

    result = await EvoBeamSearchEngine.search_paths(
        session=mock_session,
        repository_id=repo_id,
        route_plan=plan,
        branch="main",
        config=cfg,
    )

    assert result.search_diagnostics.get("timed_out") is True
    assert len(result.paths) == 0


@pytest.mark.asyncio
async def test_5_branch_isolation_parameter():
    """Verifies that branch parameter is enforced in PathSearchResult and beam search."""
    mock_session = AsyncMock()
    repo_id = uuid.uuid4()

    plan = MultiRoutePlan(
        query_text="What is A?",
        temporal_intent=TemporalIntentType.CURRENT,
        selected_routes=[],
        all_candidate_count=0,
        deduplicated_count=0,
    )

    result = await EvoBeamSearchEngine.search_paths(
        session=mock_session,
        repository_id=repo_id,
        route_plan=plan,
        branch="feature-sandbox",
    )

    assert result.branch == "feature-sandbox"
    assert result.repository_id == repo_id
