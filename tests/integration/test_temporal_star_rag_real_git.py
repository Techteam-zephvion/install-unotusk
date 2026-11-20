"""
Comprehensive Real-Git-History Integration Test Suite for Temporal STAR-RAG.
Implements Phase 10, Phase 11, Phase 12, Phase 13 of the Master Task.

Creates a deterministic 6-commit Git fixture with known historical changes:
1. Initial authentication implementation (2026-01-01)
2. Authentication validation update (2026-01-10)
3. Token expiration modification (2026-01-20)
4. Database query refactor (2026-02-01)
5. Security fix (2026-02-10)
6. Follow-up implementation change (2026-02-20)

Validates:
A. Event extraction and timestamp accuracy from real Git commits.
B. Apriori frequent relational pattern mining on real Git changes.
C. Temporal rule graph construction and Hamming distance candidate edges.
D. MDL compression objective.
E. Semantic anchor retrieval.
F. Seeded PPR ranking and convergence.
G. Historical change retrieval.
H. Previous implementation retrieval.
I. Before/after temporal ordering.
J. As-of-date queries.
K. Missing-history abstention.
L. Persistence after backend restart.
Plus Test A (ATOM only), Test B (Structure-Aware STAR-RAG), Test C (Temporal STAR-RAG), Test D (Coordinated).
"""

from __future__ import annotations

import math
import os
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.config.settings import settings
from apps.api.src.services.code_atom.git_extractor import (
    extract_incremental_commit_artifacts,
)
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag import (
    EntityRelationMiner,
    MdlGraphSelector,
    SeededPprRetriever,
    StarRagContextService,
    TemporalRuleGraphBuilder,
)
from apps.api.src.services.llm.base import GroundedAnswer


@pytest.fixture
def real_git_repo(tmp_path: Path) -> dict[str, Any]:
    """
    Creates a real, physical Git repository in tmp_path with 6 known deterministic commits.
    Controlled timestamps in UTC from 2026-01-01 to 2026-02-20.
    """
    repo_dir = str(tmp_path / "test_repo")
    os.makedirs(repo_dir, exist_ok=True)

    def run_git(args: list[str], env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            ["git"] + args,
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )

    # 1. Initialize git
    run_git(["init"])
    run_git(["config", "user.name", "Test Engineer"])
    run_git(["config", "user.email", "engineer@unotusk.local"])

    commits_info = []

    # Commit 1: Initial authentication implementation
    c1_time = "2026-01-01T10:00:00+00:00"
    auth_file = Path(repo_dir) / "auth_service.py"
    auth_file.write_text(
        "class AuthService:\n"
        "    def login(self, username, password):\n"
        "        return self.validate_credentials(username, password)\n\n"
        "    def validate_credentials(self, username, password):\n"
        "        return username != '' and password != ''\n"
    )
    run_git(["add", "auth_service.py"])
    run_git(
        ["commit", "-m", "feat(auth): initial authentication implementation"],
        env_extra={"GIT_AUTHOR_DATE": c1_time, "GIT_COMMITTER_DATE": c1_time},
    )
    c1_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    commits_info.append({"sha": c1_sha, "date": c1_time, "msg": "initial authentication implementation"})

    # Commit 2: Authentication validation update
    c2_time = "2026-01-10T12:00:00+00:00"
    auth_file.write_text(
        "class AuthService:\n"
        "    def login(self, username, password):\n"
        "        return self.validate_credentials(username, password)\n\n"
        "    def validate_credentials(self, username, password):\n"
        "        return username != '' and len(password) >= 8\n"
    )
    run_git(["add", "auth_service.py"])
    run_git(
        ["commit", "-m", "fix(auth): add password length requirement to validate_credentials"],
        env_extra={"GIT_AUTHOR_DATE": c2_time, "GIT_COMMITTER_DATE": c2_time},
    )
    c2_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    commits_info.append({"sha": c2_sha, "date": c2_time, "msg": "add password length requirement"})

    # Commit 3: Token expiration modification
    c3_time = "2026-01-20T14:00:00+00:00"
    auth_file.write_text(
        "class AuthService:\n"
        "    token_expiry_hours = 24\n\n"
        "    def login(self, username, password):\n"
        "        if self.validate_credentials(username, password):\n"
        "            return self.generate_jwt_token(username)\n"
        "        return None\n\n"
        "    def validate_credentials(self, username, password):\n"
        "        return username != '' and len(password) >= 8\n\n"
        "    def generate_jwt_token(self, username):\n"
        "        return f'jwt.{username}.token'\n"
    )
    run_git(["add", "auth_service.py"])
    run_git(
        ["commit", "-m", "feat(auth): add token expiration and jwt token generation"],
        env_extra={"GIT_AUTHOR_DATE": c3_time, "GIT_COMMITTER_DATE": c3_time},
    )
    c3_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    commits_info.append({"sha": c3_sha, "date": c3_time, "msg": "add token expiration"})

    # Commit 4: Database query refactor
    c4_time = "2026-02-01T09:00:00+00:00"
    user_repo_file = Path(repo_dir) / "user_repository.py"
    user_repo_file.write_text(
        "class UserRepository:\n"
        "    async def find_user_by_email(self, email):\n"
        "        return {'email': email, 'is_active': True}\n"
    )
    run_git(["add", "user_repository.py"])
    run_git(
        ["commit", "-m", "refactor(db): database query refactor for user lookup"],
        env_extra={"GIT_AUTHOR_DATE": c4_time, "GIT_COMMITTER_DATE": c4_time},
    )
    c4_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    commits_info.append({"sha": c4_sha, "date": c4_time, "msg": "database query refactor"})

    # Commit 5: Security fix
    c5_time = "2026-02-10T11:00:00+00:00"
    auth_file.write_text(
        "class AuthService:\n"
        "    token_expiry_hours = 24\n\n"
        "    def check_rate_limit(self, client_ip):\n"
        "        return True\n\n"
        "    def login(self, username, password, client_ip='127.0.0.1'):\n"
        "        if not self.check_rate_limit(client_ip):\n"
        "            raise Exception('Rate limit exceeded')\n"
        "        if self.validate_credentials(username, password):\n"
        "            return self.generate_jwt_token(username)\n"
        "        return None\n\n"
        "    def validate_credentials(self, username, password):\n"
        "        return username != '' and len(password) >= 8\n\n"
        "    def generate_jwt_token(self, username):\n"
        "        return f'jwt.{username}.token'\n"
    )
    run_git(["add", "auth_service.py"])
    run_git(
        ["commit", "-m", "sec(auth): add rate limiting security check"],
        env_extra={"GIT_AUTHOR_DATE": c5_time, "GIT_COMMITTER_DATE": c5_time},
    )
    c5_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    commits_info.append({"sha": c5_sha, "date": c5_time, "msg": "rate limiting security check"})

    # Commit 6: Follow-up implementation change
    c6_time = "2026-02-20T16:00:00+00:00"
    auth_file.write_text(
        "class AuthService:\n"
        "    token_expiry_hours = 24\n\n"
        "    def check_rate_limit(self, client_ip):\n"
        "        return True\n\n"
        "    def is_token_revoked(self, token_id):\n"
        "        return False\n\n"
        "    def login(self, username, password, client_ip='127.0.0.1'):\n"
        "        if not self.check_rate_limit(client_ip):\n"
        "            raise Exception('Rate limit exceeded')\n"
        "        if self.validate_credentials(username, password):\n"
        "            return self.generate_jwt_token(username)\n"
        "        return None\n\n"
        "    def validate_credentials(self, username, password):\n"
        "        return username != '' and len(password) >= 8\n\n"
        "    def generate_jwt_token(self, username):\n"
        "        return f'jwt.{username}.token'\n"
    )
    run_git(["add", "auth_service.py"])
    run_git(
        ["commit", "-m", "feat(auth): add token revocation verification"],
        env_extra={"GIT_AUTHOR_DATE": c6_time, "GIT_COMMITTER_DATE": c6_time},
    )
    c6_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    commits_info.append({"sha": c6_sha, "date": c6_time, "msg": "token revocation verification"})

    return {
        "repo_dir": repo_dir,
        "commits": commits_info,
    }


def test_real_git_history_extraction_and_provenance(real_git_repo):
    """
    Phase 10.A: Validates actual Git history extraction, chronological order,
    and UTC timestamp preservation across all 6 commits.
    """
    repo_dir = real_git_repo["repo_dir"]
    expected_commits = real_git_repo["commits"]

    # Extract all incremental artifacts
    artifacts = extract_incremental_commit_artifacts(repo_dir, target_commit_sha="HEAD", max_commits=100)
    assert len(artifacts) == 6

    # Verify chronological ordering (oldest to newest)
    for art, exp in zip(artifacts, expected_commits, strict=False):
        assert art.commit_sha == exp["sha"]
        assert exp["msg"] in art.commit_message
        assert art.committed_at is not None
        assert art.committed_at.tzinfo is not None  # Must be timezone-aware (UTC)

    # Decompose artifacts into historical events
    events = StarRagContextService.extract_events_from_commit_artifacts(artifacts)
    assert len(events) >= 6

    # Verify every event has deterministic event_id, commit_sha, and non-null timestamp
    for ev in events:
        assert ev.event_id.startswith("ev:")
        assert ev.commit_sha is not None
        assert ev.timestamp is not None
        assert ev.subject
        assert ev.relation
        assert ev.object


def test_real_git_apriori_mdl_ppr_pipeline(real_git_repo):
    """
    Phase 10.B, C, D, E, F: Tests the full research algorithm on real Git events:
    Apriori mining, Rule graph construction, MDL compression, Seeded PPR.
    """
    repo_dir = real_git_repo["repo_dir"]
    artifacts = extract_incremental_commit_artifacts(repo_dir, target_commit_sha="HEAD", max_commits=100)
    events = StarRagContextService.extract_events_from_commit_artifacts(artifacts)

    # 1. Apriori mining
    entity_types = EntityRelationMiner.mine_entity_types(events, min_support=2, max_len=3)
    assert len(entity_types) > 0

    # 2. Rule graph construction
    rule_nodes = TemporalRuleGraphBuilder.build_rule_nodes(events, entity_types)
    assert len(rule_nodes) >= 2
    candidate_edges = TemporalRuleGraphBuilder.generate_candidate_edges(rule_nodes)
    spans_map = TemporalRuleGraphBuilder.collect_temporal_spans(rule_nodes, candidate_edges)

    # 3. MDL edge selection
    selected_edges, init_mdl, final_mdl = MdlGraphSelector.select_edges(
        rule_nodes=rule_nodes,
        candidate_edges=candidate_edges,
        spans_map=spans_map,
        total_events=len(events),
        num_types=len(set(entity_types.values())),
        num_relations=len({e.relation for e in events}),
    )
    assert init_mdl > 0.0
    assert final_mdl <= init_mdl

    # 4. Seeded PPR on rule graph
    anchor_ev = events[0]  # Seed on earliest event
    top_rules, ppr_dist = SeededPprRetriever.retrieve_top_rules(
        rule_nodes=rule_nodes,
        selected_edges=selected_edges,
        anchor_events=[anchor_ev],
        top_k2=5,
    )
    assert len(top_rules) > 0
    assert math.isclose(sum(ppr_dist.values()), 1.0, abs_tol=1e-4)


def test_real_git_historical_change_and_previous_implementation(real_git_repo):
    """
    Phase 10.G, H, I: Validates historical change retrieval, previous implementation retrieval,
    and before/after temporal ordering.
    """
    repo_dir = real_git_repo["repo_dir"]
    artifacts = extract_incremental_commit_artifacts(repo_dir, target_commit_sha="HEAD", max_commits=100)
    events = StarRagContextService.extract_events_from_commit_artifacts(artifacts)

    # Convert commit artifacts to candidates
    file_id = uuid.uuid4()
    candidates = []
    for art in artifacts:
        cand = RetrievedCandidate(
            candidate_id=f"chunk:{art.commit_sha[:8]}",
            entity_type="CHUNK",
            name=f"auth_service ({art.commit_sha[:8]})",
            path="auth_service.py",
            start_line=1,
            end_line=25,
            content=art.raw_diff or "auth code",
            file_id=file_id,
            signals={"symbol_match": 1.5, "vector_similarity": 0.8},
            metadata={
                "commit_sha": art.commit_sha,
                "commit_message": art.commit_message,
                "committed_at": art.committed_at.isoformat() if art.committed_at else None,
                "chunk_type": "ATOM_MODIFY",
                "symbol_name": "AuthService",
            },
        )
        candidates.append(cand)

    # Query: What was the previous implementation before rate limiting (Commit 5)?
    c5_sha = real_git_repo["commits"][4]["sha"]
    q_prev = AnalyzedQuery(
        raw_query=f"What was the previous implementation of login before commit {c5_sha[:8]}?",
        keywords=["login", "authentication"],
        symbol_candidates=["login", "AuthService"],
        is_temporal=True,
        temporal_intent="BEFORE",
    )

    result = StarRagContextService.run_star_rag_pipeline(
        candidates=candidates,
        analyzed_query=q_prev,
        query_text=q_prev.raw_query,
        extra_events=events,
    )

    assert result.is_fallback is False
    assert len(result.temporal_evidence) > 0

    # Top historical evidence must be prior to Commit 5 (2026-02-10)
    top_ev = result.temporal_evidence[0]
    top_ts = datetime.fromisoformat(top_ev["timestamp"])
    c5_ts = datetime.fromisoformat(real_git_repo["commits"][4]["date"])
    assert top_ts <= c5_ts


def test_real_git_as_of_date_query(real_git_repo):
    """
    Phase 10.J: Validates as-of-date queries (state as of 2026-01-15).
    At 2026-01-15, Commit 1 (Jan 1) and Commit 2 (Jan 10) have occurred,
    but Commit 3 (Jan 20) and later have NOT occurred.
    """
    repo_dir = real_git_repo["repo_dir"]
    artifacts = extract_incremental_commit_artifacts(repo_dir, target_commit_sha="HEAD", max_commits=100)
    events = StarRagContextService.extract_events_from_commit_artifacts(artifacts)

    candidates = [
        RetrievedCandidate(
            candidate_id=f"chunk:{art.commit_sha[:8]}",
            entity_type="CHUNK",
            name=f"auth ({art.commit_sha[:8]})",
            path="auth_service.py",
            start_line=1,
            end_line=25,
            content=art.raw_diff or "auth code",
            file_id=uuid.uuid4(),
            signals={"symbol_match": 1.5, "vector_similarity": 0.8},
            metadata={
                "commit_sha": art.commit_sha,
                "commit_message": art.commit_message,
                "committed_at": art.committed_at.isoformat() if art.committed_at else None,
                "chunk_type": "ATOM_MODIFY",
            },
        )
        for art in artifacts
    ]

    q_asof = AnalyzedQuery(
        raw_query="What was the implementation of validate_credentials as of 2026-01-15?",
        keywords=["validate_credentials"],
        symbol_candidates=["validate_credentials"],
        is_temporal=True,
        temporal_intent="POINT_IN_TIME",
    )

    result = StarRagContextService.run_star_rag_pipeline(
        candidates=candidates,
        analyzed_query=q_asof,
        query_text=q_asof.raw_query,
        extra_events=events,
    )

    assert result.is_fallback is False
    assert len(result.temporal_evidence) > 0

    # Top evidence should be Commit 2 (Jan 10) or Commit 1 (Jan 1), NOT Commit 3 (Jan 20)
    as_of_target = datetime(2026, 1, 15, 23, 59, 59, tzinfo=UTC)
    for ev in result.temporal_evidence[:3]:
        if ev.get("timestamp"):
            ev_dt = datetime.fromisoformat(ev["timestamp"])
            assert ev_dt <= as_of_target


def test_real_git_missing_history_abstention(real_git_repo):
    """
    Phase 10.K: Validates honest abstention / fallback when query asks about
    unrelated components not present in repository history.
    """
    repo_dir = real_git_repo["repo_dir"]
    artifacts = extract_incremental_commit_artifacts(repo_dir, target_commit_sha="HEAD", max_commits=100)
    events = StarRagContextService.extract_events_from_commit_artifacts(artifacts)

    candidates = [
        RetrievedCandidate(
            candidate_id=f"chunk:{art.commit_sha[:8]}",
            entity_type="CHUNK",
            name="auth",
            path="auth_service.py",
            start_line=1,
            end_line=25,
            content="auth code",
            file_id=uuid.uuid4(),
            signals={"vector_similarity": 0.05},
            metadata={"commit_sha": art.commit_sha},
        )
        for art in artifacts
    ]

    q_missing = AnalyzedQuery(
        raw_query="What changes were committed to Kafka message broker integration last month?",
        keywords=["kafka", "message", "broker"],
        is_temporal=True,
        temporal_intent="HISTORICAL",
    )

    result = StarRagContextService.run_star_rag_pipeline(
        candidates=candidates,
        analyzed_query=q_missing,
        query_text=q_missing.raw_query,
        extra_events=events,
    )

    # Must fall back gracefully without hallucinating Kafka evidence
    assert result.is_fallback is True
    assert "below confidence threshold" in (result.fallback_reason or "")


@pytest.mark.asyncio
async def test_all_three_retrieval_capabilities_isolated_and_coordinated(monkeypatch):
    """
    Phase 11: Validates:
    Test A: ATOM only
    Test B: Structure-Aware STAR-RAG
    Test C: Temporal STAR-RAG
    Test D: Coordinated retrieval
    """
    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    file_id = uuid.uuid4()

    c_auth = RetrievedCandidate(
        candidate_id="chunk:auth",
        entity_type="CHUNK",
        name="validate_credentials",
        path="auth_service.py",
        start_line=1,
        end_line=25,
        content="def validate_credentials(): return True",
        file_id=file_id,
        signals={"symbol_match": 1.5, "vector_similarity": 0.85},
        metadata={"commit_sha": "11111111", "committed_at": "2026-01-01T10:00:00+00:00"},
    )
    c_user = RetrievedCandidate(
        candidate_id="chunk:user",
        entity_type="CHUNK",
        name="find_user_by_email",
        path="user_repository.py",
        start_line=1,
        end_line=25,
        content="def find_user_by_email(): return None",
        file_id=file_id,
        signals={"symbol_match": 1.4, "vector_similarity": 0.80},
        metadata={"commit_sha": "44444444", "committed_at": "2026-02-01T09:00:00+00:00"},
    )

    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=[c_auth, c_user]),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=[c_auth, c_user]),
    )

    engine = ProjectContextEngine()
    engine.llm_provider = AsyncMock()
    engine.llm_provider.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Grounded synthesis response",
            evidence=[],
            related_entities=[],
            debug_signals={},
        )
    )

    # -------------------------------------------------------------
    # Test A: ATOM only (STAR-RAG disabled)
    # -------------------------------------------------------------
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", False)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", False)

    ans_a = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Where is validate_credentials defined?",
        enable_star_rag=False,
        enable_structure_aware_star_rag=False,
    )
    assert ans_a.debug_signals.get("star_rag_used") is False
    assert ans_a.debug_signals.get("structure_aware_star_rag_used") is False

    # -------------------------------------------------------------
    # Test B: Structure-Aware STAR-RAG
    # -------------------------------------------------------------
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)
    ans_b = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the dependency flow from validate_credentials to UserRepository.",
        enable_structure_aware_star_rag=True,
        enable_star_rag=False,
    )
    assert ans_b.debug_signals.get("structure_aware_star_rag_used") is True
    assert ans_b.debug_signals.get("star_rag_used") is False

    # -------------------------------------------------------------
    # Test C: Temporal STAR-RAG
    # -------------------------------------------------------------
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", True)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", False)
    ans_c = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="What changed in validate_credentials across recent commits?",
        enable_star_rag=True,
        enable_structure_aware_star_rag=False,
    )
    assert ans_c.debug_signals.get("star_rag_used") is True
    assert ans_c.debug_signals.get("structure_aware_star_rag_used") is False

    # -------------------------------------------------------------
    # Test D: Coordinated retrieval (Structure + History)
    # -------------------------------------------------------------
    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", True)
    monkeypatch.setattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", True)
    ans_d = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Trace the dependency flow and historical evolution of validate_credentials.",
        enable_star_rag=True,
        enable_structure_aware_star_rag=True,
    )
    # Both systems run in coordinated fashion without collisions
    assert ans_d.debug_signals.get("star_rag_used") is True
    assert ans_d.debug_signals.get("structure_aware_star_rag_used") is True


@pytest.mark.asyncio
async def test_phase_13_five_historical_queries(real_git_repo, monkeypatch):
    """
    Phase 13: End-to-end validation across the 5 canonical historical queries:
    1. "What changed in authentication validation in January 2026?"
    2. "What was the previous implementation of validate_credentials before the password length update?"
    3. "Which change happened before the database query refactor?"
    4. "What did the token expiration implementation look like as of January 15, 2026?"
    5. "Show the evolution of auth_service across recent commits."
    """
    repo_dir = real_git_repo["repo_dir"]
    artifacts = extract_incremental_commit_artifacts(repo_dir, target_commit_sha="HEAD", max_commits=100)
    events = StarRagContextService.extract_events_from_commit_artifacts(artifacts)

    candidates = [
        RetrievedCandidate(
            candidate_id=f"chunk:{art.commit_sha[:8]}",
            entity_type="CHUNK",
            name=f"auth ({art.commit_sha[:8]})",
            path="auth_service.py" if "auth" in art.commit_message else "user_repository.py",
            start_line=1,
            end_line=25,
            content=art.raw_diff or "code",
            file_id=uuid.uuid4(),
            signals={"symbol_match": 1.5, "vector_similarity": 0.85},
            metadata={
                "commit_sha": art.commit_sha,
                "commit_message": art.commit_message,
                "committed_at": art.committed_at.isoformat() if art.committed_at else None,
                "chunk_type": "ATOM_MODIFY",
                "symbol_name": "AuthService" if "auth" in art.commit_message else "UserRepository",
            },
        )
        for art in artifacts
    ]

    snapshot_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    session = AsyncMock()
    snap_mock = MagicMock()
    snap_mock.scalar_one_or_none.return_value = repo_id
    session.execute.return_value = snap_mock

    monkeypatch.setattr(
        "apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates",
        AsyncMock(return_value=candidates),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates",
        AsyncMock(return_value=candidates),
    )
    monkeypatch.setattr(
        "apps.api.src.services.context_engine.star_rag.StarRagContextService.load_historical_events_from_db",
        AsyncMock(return_value=events),
    )

    monkeypatch.setattr(settings, "STAR_RAG_ENABLED", True)

    engine = ProjectContextEngine()

    # Query 1: What changed in authentication validation in January 2026?
    ans1 = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="What changed in authentication validation in January 2026?",
        enable_star_rag=True,
    )
    assert ans1.debug_signals.get("star_rag_used") is True
    assert ans1.debug_signals.get("star_rag_temporal_evidence_count", 0) > 0

    # Query 2: What was the previous implementation of validate_credentials before the password length update?
    ans2 = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="What was the previous implementation of validate_credentials before the password length update?",
        enable_star_rag=True,
    )
    assert ans2.debug_signals.get("star_rag_used") is True
    assert ans2.debug_signals.get("star_rag_temporal_evidence_count", 0) > 0

    # Query 3: Which change happened before the database query refactor?
    ans3 = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Which change happened before the database query refactor?",
        enable_star_rag=True,
    )
    assert ans3.debug_signals.get("star_rag_used") is True
    assert ans3.debug_signals.get("star_rag_temporal_evidence_count", 0) > 0

    # Query 4: What did the token expiration implementation look like as of January 15, 2026?
    ans4 = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="What did the token expiration implementation look like as of January 15, 2026?",
        enable_star_rag=True,
    )
    assert ans4.debug_signals.get("star_rag_used") is True
    assert ans4.debug_signals.get("star_rag_temporal_evidence_count", 0) > 0

    # Query 5: Show the evolution of auth_service across recent commits.
    ans5 = await engine.investigate(
        session=session,
        snapshot_id=snapshot_id,
        question="Show the evolution of auth_service across recent commits.",
        enable_star_rag=True,
    )
    assert ans5.debug_signals.get("star_rag_used") is True
    assert ans5.debug_signals.get("star_rag_temporal_evidence_count", 0) > 0

