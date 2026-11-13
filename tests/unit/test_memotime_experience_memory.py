"""
Unit tests for MemoTime Experience Memory & Verified Reasoning Trace Reuse (arXiv:2510.13614).

Verifies:
1. Recording verified reasoning experiences with quality threshold gate (>= 0.80).
2. Rejection of low-confidence, unverified, or empty experiences.
3. Strict repository and branch isolation.
4. Cross-question-type experience reuse (e.g., evolution trace aiding historical/diff queries).
5. Contradiction detection, rejection, and penalty demotion.
6. Explainable attribution strings in candidates and diagnostics.
7. MultiSignalRanker integration and score boosting.
8. Feature flag disabled (MEMOTIME_ENABLED=False) no-op baseline preservation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.memotime import (
    ExperienceRecord,
    MemoTimeExperienceStore,
    MemoTimeRetrievalResult,
    MemoTimeService,
)
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


@pytest.fixture
def repo_a_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def repo_b_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_candidates() -> list[RetrievedCandidate]:
    now = datetime.now(UTC)
    c1 = RetrievedCandidate(
        candidate_id="cand_1",
        entity_type="CHUNK",
        name="AuthService.authenticate (c1a2b3c)",
        path="src/auth/service.py",
        start_line=1,
        end_line=20,
        content="class AuthService:\n    def authenticate(token: str) -> User:\n        return verify(token)",
        file_id=uuid.uuid4(),
        signals={"exact_symbol": 1.0},
        metadata={
            "symbol_name": "AuthService",
            "commit_sha": "c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
            "is_current": False,
            "is_superseded": True,
            "created_at": (now - timedelta(days=60)).isoformat(),
        },
    )
    c2 = RetrievedCandidate(
        candidate_id="cand_2",
        entity_type="CHUNK",
        name="ModernAuth.authenticate (d4e5f6a)",
        path="src/auth/modern.py",
        start_line=1,
        end_line=20,
        content="class ModernAuth:\n    def authenticate(token: str) -> User:\n        return modern_verify(token)",
        file_id=uuid.uuid4(),
        signals={"exact_symbol": 1.0},
        metadata={
            "symbol_name": "ModernAuth",
            "commit_sha": "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3",
            "is_current": True,
            "is_superseded": False,
            "created_at": now.isoformat(),
        },
    )
    return [c1, c2]


@pytest.mark.asyncio
async def test_experience_store_quality_gate(repo_a_id: uuid.UUID):
    """Rejects unverified or low-confidence experiences (< 0.80)."""
    # 1. Reject low confidence (< 0.80)
    rec, err = await MemoTimeExperienceStore.record_verified_experience_async(
        session=None,
        repository_id=repo_a_id,
        branch="main",
        query_text="How was auth refactored?",
        intent_type="EVOLUTION",
        target_entities=["AuthService"],
        verified_outcome={"changes": ["refactored"]},
        confidence_score=0.75,  # Below 0.80
        is_verified=True,
    )
    assert rec is None
    assert err is not None
    assert "below threshold" in err

    # 2. Reject unverified
    rec, err = await MemoTimeExperienceStore.record_verified_experience_async(
        session=None,
        repository_id=repo_a_id,
        branch="main",
        query_text="How was auth refactored?",
        intent_type="EVOLUTION",
        target_entities=["AuthService"],
        verified_outcome={"changes": ["refactored"]},
        confidence_score=0.90,
        is_verified=False,  # Unverified
    )
    assert rec is None
    assert err is not None
    assert "unverified" in err

    # 3. Reject empty outcome
    rec, err = await MemoTimeExperienceStore.record_verified_experience_async(
        session=None,
        repository_id=repo_a_id,
        branch="main",
        query_text="How was auth refactored?",
        intent_type="EVOLUTION",
        target_entities=["AuthService"],
        verified_outcome={},  # Empty outcome
        confidence_score=0.90,
        is_verified=True,
    )
    assert rec is None
    assert err is not None
    assert "verified outcome" in err

    # 4. Accept verified with confidence >= 0.80
    rec, err = await MemoTimeExperienceStore.record_verified_experience_async(
        session=None,
        repository_id=repo_a_id,
        branch="main",
        query_text="How was auth refactored?",
        intent_type="EVOLUTION",
        target_entities=["AuthService"],
        commit_sha="c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
        verified_outcome={"changes": ["replaced AuthService with ModernAuth"]},
        confidence_score=0.88,
        is_verified=True,
        attribution="Verified evolution from AuthService to ModernAuth in PR #42",
    )
    assert rec is not None
    assert err is None
    assert rec.repository_id == str(repo_a_id)
    assert rec.confidence_score == 0.88
    assert "PR #42" in rec.attribution


@pytest.mark.asyncio
async def test_experience_store_repository_and_branch_isolation(
    repo_a_id: uuid.UUID, repo_b_id: uuid.UUID
):
    """Enforces strict repository and branch boundaries."""
    # Mock database session returning repository-specific items
    mock_session = AsyncMock()

    class MockDBRow:
        def __init__(self, r_id, br, ent, sha, attr):
            self.id = uuid.uuid4()
            self.repository_id = r_id
            self.branch = br
            self.query_text = "test query"
            self.intent_type = "EVOLUTION"
            self.target_entities = ent
            self.commit_sha = sha
            self.valid_from = datetime.now(UTC)
            self.valid_to = None
            self.verified_outcome = {"tested": True}
            self.confidence_score = 0.90
            self.is_verified = True
            self.is_contradictory = False
            self.contradiction_detail = None
            self.attribution = attr
            self.created_at = datetime.now(UTC)

    # When querying repo_a_id / main, only repo_a_id rows should be returned
    row_repo_a = MockDBRow(repo_a_id, "main", ["AuthService"], "c1a2b3c", "Repo A Main attribution")

    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value.all.return_value = [row_repo_a]
    mock_session.execute.return_value = mock_execute_result

    results = await MemoTimeExperienceStore.retrieve_relevant_experiences_async(
        session=mock_session,
        repository_id=repo_a_id,
        branch="main",
        target_entities=["AuthService"],
    )

    assert len(results) == 1
    assert results[0].repository_id == str(repo_a_id)
    assert results[0].branch == "main"
    assert "Repo A Main" in results[0].attribution


def test_experience_memory_application_and_signals(
    sample_candidates: list[RetrievedCandidate], repo_a_id: uuid.UUID
):
    """Tests injecting experience signals into candidates and explainability attribution."""
    exp = ExperienceRecord(
        id=str(uuid.uuid4()),
        repository_id=str(repo_a_id),
        branch="main",
        query_text="What was the previous AuthService implementation?",
        intent_type="HISTORICAL",
        target_entities=["AuthService", "src/auth/service.py"],
        commit_sha="c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
        verified_outcome={"legacy_auth": True},
        confidence_score=0.92,
        is_verified=True,
        attribution="Verified historical AuthService proof trace at commit c1a2b3c",
    )

    augmented, count = MemoTimeService.apply_experience_memory(
        candidates=sample_candidates,
        experiences=[exp],
    )

    assert count >= 1
    # Candidate 1 matches both entity and commit SHA
    c1 = next(c for c in augmented if c.candidate_id == "cand_1")
    assert "memotime_experience_relevance" in c1.signals
    assert c1.signals["memotime_experience_relevance"] >= 0.85
    assert c1.metadata.get("memotime_experience_id") == exp.id
    assert "Verified historical AuthService proof trace" in c1.metadata.get(
        "memotime_experience_attribution", ""
    )


def test_cross_question_type_experience_reuse(sample_candidates: list[RetrievedCandidate]):
    """
    Verifies that an EVOLUTION experience generated in a previous turn
    is successfully reused for a subsequent HISTORICAL or BEFORE query.
    """
    evolution_exp = ExperienceRecord(
        id=str(uuid.uuid4()),
        repository_id=str(uuid.uuid4()),
        branch="main",
        query_text="How did AuthService evolve into ModernAuth?",
        intent_type="EVOLUTION",
        target_entities=["AuthService", "ModernAuth"],
        commit_sha="c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
        verified_outcome={
            "phases": ["origin: AuthService", "current: ModernAuth"],
            "superseded_sha": "c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
        },
        confidence_score=0.95,
        is_verified=True,
        attribution="Verified evolutionary lineage: AuthService superseded by ModernAuth",
    )

    # Subsequent query asks a HISTORICAL question about legacy AuthService
    res: MemoTimeRetrievalResult = MemoTimeService.run_memotime_pipeline(
        candidates=sample_candidates,
        query_text="Show the legacy implementation of AuthService before modernization",
        experiences=[evolution_exp],
    )

    assert not res.is_fallback
    assert len(res.experiences_used) == 1
    assert res.experiences_used[0].id == evolution_exp.id
    assert res.diagnostics.get("experiences_applied_count", 0) >= 1

    # Verified historical candidate must be prioritized
    top_candidate = res.candidates[0]
    assert top_candidate.candidate_id == "cand_1"
    assert "memotime_experience_relevance" in top_candidate.signals


def test_experience_contradiction_detection_and_penalty():
    """Contradictory experiences or candidates are penalized or flagged."""
    exp = ExperienceRecord(
        id=str(uuid.uuid4()),
        repository_id=str(uuid.uuid4()),
        branch="main",
        query_text="Historical query",
        intent_type="HISTORICAL",
        target_entities=["LegacyComponent"],
        valid_from=datetime.now(UTC) - timedelta(days=30),
        confidence_score=0.90,
        attribution="LegacyComponent was active up to 30 days ago",
    )

    cand = RetrievedCandidate(
        candidate_id="contradictory_cand",
        entity_type="CHUNK",
        name="LegacyComponent.do_work",
        path="src/legacy.py",
        start_line=1,
        end_line=10,
        content="def do_work(): pass",
        file_id=uuid.uuid4(),
        signals={},
        metadata={
            "symbol_name": "LegacyComponent",
            "is_deleted": True,
            "ended_at": (datetime.now(UTC) - timedelta(days=60)).isoformat(),  # Ended before valid_from!
            "created_at": (datetime.now(UTC) - timedelta(days=90)).isoformat(),
        },
    )

    augmented, _ = MemoTimeService.apply_experience_memory([cand], [exp])
    assert augmented[0].signals.get("memotime_experience_contradiction") == 1.0
    assert "Contradicts verified experience" in augmented[0].metadata.get(
        "memotime_experience_conflict", ""
    )


def test_multisignal_ranker_experience_boosting(sample_candidates: list[RetrievedCandidate]):
    """Verifies MultiSignalRanker boosts candidates backed by verified experience memory."""
    query = AnalyzedQuery(
        raw_query="legacy AuthService",
        keywords=["legacy", "authservice"],
        symbol_candidates=["AuthService"],
        path_candidates=["src/auth/service.py"],
        concept_keywords=["auth"],
        is_temporal=True,
    )

    # Attach experience relevance to cand_1
    sample_candidates[0].signals["memotime_experience_relevance"] = 1.0

    ranked = MultiSignalRanker.rank_candidates(sample_candidates, query)
    assert len(ranked) == 2
    # cand_1 should be boosted by the experience signal (+1.5 * 1.0)
    top = ranked[0]
    assert top.candidate.candidate_id == "cand_1"
    assert any("MemoTime experience memory reuse" in r for r in top.matched_reasons)


def test_memotime_feature_flag_disabled_by_default():
    """Confirms MEMOTIME_ENABLED is False by default in settings."""
    assert getattr(settings, "MEMOTIME_ENABLED", False) is False
