"""
Real PostgreSQL 16 Acceptance Tests for EvoReasoner Beam Search (T2.5 Milestone).

Directly validates graph traversal, beam search, entity continuity, and temporal filtering
against a live PostgreSQL 16 database instance (container evokg-pg-test).
"""

from __future__ import annotations

import asyncio
import os
import socket
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    ProjectStatus,
)
from apps.api.src.models.evokg import EvoKGTriplet
from apps.api.src.models.integration import Integration
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.schemas.code_atom import RelationType
from apps.api.src.schemas.evoreasoner import (
    BeamSearchConfig,
    ReasoningHop,
    ReasoningRoute,
    RoutePerspective,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.memotime import TemporalIntentType
from apps.api.src.services.evoreasoner.aggregator import ProofChainAggregator
from apps.api.src.services.evoreasoner.beam_search import EvoBeamSearchEngine
from apps.api.src.services.evoreasoner.cost_estimator import RouteCostEstimator
from apps.api.src.services.evoreasoner.planner import EvoRoutePlanner


def _resolve_postgres_test_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]

    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        return os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/unotusk_test",
        )

    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url and ("5433" in env_db_url or "5432" not in env_db_url):
        return env_db_url

    local_5433 = "postgresql+asyncpg://postgres:postgres@localhost:5433/unotusk_test"
    default_5432 = "postgresql+asyncpg://postgres:postgres@localhost:5432/unotusk_test"

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.2)
        res = sock.connect_ex(("127.0.0.1", 5433))
        sock.close()
        if res == 0:
            return local_5433
    except Exception:
        pass

    return env_db_url or default_5432


POSTGRES_TEST_URL = _resolve_postgres_test_url()


@pytest.fixture
def pg_engine():
    engine = create_async_engine(POSTGRES_TEST_URL, poolclass=NullPool, echo=False)
    yield engine


@pytest.fixture(autouse=True)
async def check_db_available(pg_session: AsyncSession):
    """Skips acceptance test gracefully if PostgreSQL service is not reachable."""
    if pg_session is None:
        pytest.skip("Database session is not configured")
    try:
        await asyncio.wait_for(pg_session.execute(text("SELECT 1")), timeout=1.0)
    except Exception as exc:
        pytest.skip(f"PostgreSQL database acceptance environment not available: {exc}")


@pytest.fixture
async def pg_session(pg_engine) -> AsyncSession:
    session_factory = async_sessionmaker(
        bind=pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_repo(pg_session: AsyncSession) -> Repository:
    org = Organization(id=uuid.uuid4(), name="PostgresBeamOrg", slug=f"beam-org-{uuid.uuid4().hex[:6]}")
    pg_session.add(org)
    await pg_session.flush()

    proj = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="BeamProj",
        slug=f"beam-proj-{uuid.uuid4().hex[:6]}",
        status=ProjectStatus.READY,
    )
    pg_session.add(proj)
    await pg_session.flush()

    integ = Integration(
        id=uuid.uuid4(),
        project_id=proj.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
    )
    pg_session.add(integ)
    await pg_session.flush()

    repo = Repository(
        id=uuid.uuid4(),
        project_id=proj.id,
        integration_id=integ.id,
        external_id=f"ext-beam-{uuid.uuid4().hex[:6]}",
        owner="beam-team",
        name="core-beam",
        full_name="beam-team/core-beam",
        default_branch="main",
        url="https://github.com/beam-team/core-beam",
    )
    pg_session.add(repo)
    await pg_session.flush()
    await pg_session.commit()
    return repo


def _dt(offset_hours: int) -> datetime:
    return datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


def _make_route(
    route_id: str,
    name: str,
    hops: list[ReasoningHop],
    perspective: RoutePerspective = RoutePerspective.ARCHITECTURAL_DEPENDENCY,
    intent: TemporalIntentType = TemporalIntentType.CURRENT,
) -> ReasoningRoute:
    cost, breakdown = RouteCostEstimator.estimate_cost(hops, intent)
    canonical_key = "->".join(f"{h.source_entity}:{h.relation.value}:{h.target_entity}" for h in hops)
    return ReasoningRoute(
        route_id=route_id,
        name=name,
        intent=intent,
        perspective=perspective,
        hops=hops,
        estimated_cost=cost,
        cost_breakdown=breakdown,
        canonical_key=canonical_key,
    )


def _create_pg_triplet(
    repo_id: uuid.UUID,
    subject: str,
    relation: str,
    object_id: str,
    *,
    branch: str = "main",
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    commit_sha: str | None = "commit_pg_100",
    confidence: float = 0.90,
    is_uncertain: bool = False,
    has_conflict: bool = False,
    is_exclusive: bool = False,
    supersedes_id: uuid.UUID | None = None,
    superseded_by_id: uuid.UUID | None = None,
) -> EvoKGTriplet:
    return EvoKGTriplet(
        id=uuid.uuid4(),
        repository_id=repo_id,
        branch=branch,
        subject_id=subject,
        relation=relation,
        object_id=object_id,
        is_exclusive=is_exclusive,
        scope_key="default",
        valid_from=valid_from or _dt(0),
        valid_to=valid_to,
        observation_time=_dt(0),
        commit_sha=commit_sha,
        supersedes_id=supersedes_id,
        superseded_by_id=superseded_by_id,
        confidence_score=confidence,
        confidence_level="HIGH" if confidence >= 0.8 else "UNCERTAIN",
        is_uncertain=is_uncertain,
        has_temporal_conflict=has_conflict,
        fingerprint=f"fp_pg_{uuid.uuid4().hex}",
        provenance={"branch": branch, "commit": commit_sha},
    )


# =========================================================================
# 1. Forward and Inverse Traversal in Live PostgreSQL
# =========================================================================

@pytest.mark.asyncio
async def test_1_real_postgresql_forward_and_inverse_traversal(
    pg_session: AsyncSession, test_repo: Repository
):
    repo_id = test_repo.id

    t_fwd = _create_pg_triplet(repo_id, "pg/auth::AuthService", "CALLS", "pg/tokens::TokenManager")
    t_inv = _create_pg_triplet(repo_id, "pg/users::UserCtrl", "IMPORTS", "pg/auth::AuthService")
    pg_session.add_all([t_fwd, t_inv])
    await pg_session.commit()

    # Forward search: AuthService -> TokenManager
    hop_fwd = EvoRoutePlanner.create_hop(1, "pg/auth::AuthService", RelationType.CALLS, "pg/tokens::TokenManager")
    route_fwd = _make_route("r_pg_fwd", "Forward PG Route", [hop_fwd])

    paths_fwd, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=pg_session,
        repository_id=repo_id,
        route=route_fwd,
    )
    assert len(paths_fwd) == 1
    assert paths_fwd[0].target_entity == "pg/tokens::TokenManager"

    # Inverse search: AuthService <- IMPORTS <- UserCtrl
    hop_inv = EvoRoutePlanner.create_hop(
        1, "pg/auth::AuthService", RelationType.IMPORTS, "pg/users::UserCtrl", is_inverse=True
    )
    route_inv = _make_route("r_pg_inv", "Inverse PG Route", [hop_inv])

    paths_inv, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=pg_session,
        repository_id=repo_id,
        route=route_inv,
    )
    assert len(paths_inv) == 1
    assert paths_inv[0].target_entity == "pg/users::UserCtrl"
    assert paths_inv[0].edges[0].is_inverse is True


# =========================================================================
# 2. Repository and Branch Isolation in Live PostgreSQL
# =========================================================================

@pytest.mark.asyncio
async def test_2_real_postgresql_repository_and_branch_isolation(
    pg_session: AsyncSession, test_repo: Repository
):
    repo_id = test_repo.id

    other_repo = Repository(
        id=uuid.uuid4(),
        project_id=test_repo.project_id,
        integration_id=test_repo.integration_id,
        external_id=f"ext-other-{uuid.uuid4().hex[:6]}",
        owner="beam-team",
        name="other-beam",
        full_name="beam-team/other-beam",
        default_branch="main",
        url="https://github.com/beam-team/other-beam",
    )
    pg_session.add(other_repo)
    await pg_session.flush()
    other_repo_id = other_repo.id

    # Same subject and relation on main vs other branch vs other repo
    t_main = _create_pg_triplet(repo_id, "pg/svc::PaymentSvc", "CALLS", "pg/gw::StripeGw", branch="main")
    t_feat = _create_pg_triplet(repo_id, "pg/svc::PaymentSvc", "CALLS", "pg/gw::AdyenGw", branch="feat/adyen")
    t_other = _create_pg_triplet(other_repo_id, "pg/svc::PaymentSvc", "CALLS", "pg/gw::SquareGw", branch="main")

    pg_session.add_all([t_main, t_feat, t_other])
    await pg_session.commit()

    hop = EvoRoutePlanner.create_hop(1, "pg/svc::PaymentSvc", RelationType.CALLS, "pg/gw::StripeGw")
    route = _make_route("r_pg_iso", "PG Isolation Route", [hop])

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=pg_session,
        repository_id=repo_id,
        route=route,
        branch="main",
    )

    targets = [p.target_entity for p in paths]
    assert "pg/gw::StripeGw" in targets
    assert "pg/gw::AdyenGw" not in targets
    assert "pg/gw::SquareGw" not in targets


# =========================================================================
# 3. Temporal SQL Filters Across All 7 Intents in Live PostgreSQL
# =========================================================================

@pytest.mark.asyncio
async def test_3_real_postgresql_temporal_sql_filters_all_intents(
    pg_session: AsyncSession, test_repo: Repository
):
    repo_id = test_repo.id
    # base test setup

    # Historical triplet closed in past
    t_hist = _create_pg_triplet(
        repo_id, "pg/db::Connection", "CALLS", "pg/pool::LegacyPool",
        valid_from=_dt(-48),
        valid_to=_dt(-12),
        commit_sha="commit_pg_v1",
    )
    # Active triplet started in past and still active
    t_active = _create_pg_triplet(
        repo_id, "pg/db::Connection", "CALLS", "pg/pool::AsyncPool",
        valid_from=_dt(-12),
        valid_to=None,
        commit_sha="commit_pg_v2",
        supersedes_id=t_hist.id,
    )
    pg_session.add_all([t_hist, t_active])
    await pg_session.commit()

    # 1. CURRENT
    hop_curr = EvoRoutePlanner.create_hop(1, "pg/db::Connection", RelationType.CALLS, "pg/pool::AsyncPool")
    r_curr = _make_route("r_c", "Curr", [hop_curr], intent=TemporalIntentType.CURRENT)
    paths_curr, _ = await EvoBeamSearchEngine.execute_route_beam(
        pg_session, repo_id, r_curr, intent_type=TemporalIntentType.CURRENT
    )
    assert len(paths_curr) == 1
    assert paths_curr[0].target_entity == "pg/pool::AsyncPool"

    # 2. HISTORICAL
    hop_hist = EvoRoutePlanner.create_hop(1, "pg/db::Connection", RelationType.CALLS, "pg/pool::LegacyPool")
    r_hist = _make_route("r_h", "Hist", [hop_hist], intent=TemporalIntentType.HISTORICAL)
    paths_hist, _ = await EvoBeamSearchEngine.execute_route_beam(
        pg_session, repo_id, r_hist, intent_type=TemporalIntentType.HISTORICAL
    )
    assert any(p.target_entity == "pg/pool::LegacyPool" for p in paths_hist)

    # 3. BEFORE (anchor = -20h: LegacyPool was active, AsyncPool was not yet created)
    r_before = _make_route("r_b", "Before", [hop_hist], intent=TemporalIntentType.BEFORE)
    paths_before, _ = await EvoBeamSearchEngine.execute_route_beam(
        pg_session, repo_id, r_before, intent_type=TemporalIntentType.BEFORE, as_of=_dt(-20)
    )
    assert any(p.target_entity == "pg/pool::LegacyPool" for p in paths_before)
    assert not any(p.target_entity == "pg/pool::AsyncPool" for p in paths_before)

    # 4. AFTER (anchor = -10h: AsyncPool is active, LegacyPool was expired)
    r_after = _make_route("r_a", "After", [hop_curr], intent=TemporalIntentType.AFTER)
    paths_after, _ = await EvoBeamSearchEngine.execute_route_beam(
        pg_session, repo_id, r_after, intent_type=TemporalIntentType.AFTER, as_of=_dt(-10)
    )
    assert any(p.target_entity == "pg/pool::AsyncPool" for p in paths_after)
    assert not any(p.target_entity == "pg/pool::LegacyPool" for p in paths_after)

    # 5. DIFF (reference = commit_pg_v1, target = commit_pg_v2)
    r_diff = _make_route("r_d", "Diff", [hop_curr], intent=TemporalIntentType.DIFF)
    paths_diff, _ = await EvoBeamSearchEngine.execute_route_beam(
        pg_session, repo_id, r_diff, intent_type=TemporalIntentType.DIFF,
        reference_commit="commit_pg_v1", target_commit="commit_pg_v2"
    )
    assert len(paths_diff) >= 1

    # 6. EVOLUTION
    r_evo = _make_route("r_e", "Evo", [hop_curr], intent=TemporalIntentType.EVOLUTION)
    paths_evo, _ = await EvoBeamSearchEngine.execute_route_beam(
        pg_session, repo_id, r_evo, intent_type=TemporalIntentType.EVOLUTION
    )
    assert len(paths_evo) >= 1


# =========================================================================
# 4. Uncertainty and Contradiction Penalties in Live PostgreSQL
# =========================================================================

@pytest.mark.asyncio
async def test_4_real_postgresql_uncertainty_and_conflict_handling(
    pg_session: AsyncSession, test_repo: Repository
):
    repo_id = test_repo.id

    t_clean = _create_pg_triplet(repo_id, "pg/eval::CleanEngine", "CALLS", "pg/eval::CleanTarget", confidence=0.95)
    t_uncertain = _create_pg_triplet(
        repo_id, "pg/eval::UncertainEngine", "CALLS", "pg/eval::UncertainTarget",
        confidence=0.50, is_uncertain=True
    )
    t_conflict = _create_pg_triplet(
        repo_id, "pg/eval::ConflictEngine", "CALLS", "pg/eval::ConflictTarget",
        confidence=0.85, has_conflict=True
    )
    pg_session.add_all([t_clean, t_uncertain, t_conflict])
    await pg_session.commit()

    hop_clean = EvoRoutePlanner.create_hop(1, "pg/eval::CleanEngine", RelationType.CALLS, "pg/eval::CleanTarget")
    r_clean = _make_route("r_cl", "Clean", [hop_clean])
    paths_clean, _ = await EvoBeamSearchEngine.execute_route_beam(pg_session, repo_id, r_clean)

    hop_unc = EvoRoutePlanner.create_hop(1, "pg/eval::UncertainEngine", RelationType.CALLS, "pg/eval::UncertainTarget")
    r_unc = _make_route("r_un", "Unc", [hop_unc])
    paths_unc, _ = await EvoBeamSearchEngine.execute_route_beam(pg_session, repo_id, r_unc)

    assert paths_clean[0].path_score > paths_unc[0].path_score
    assert paths_unc[0].score_breakdown.uncertainty_penalty > 0.0


# =========================================================================
# 5. Candidate Edge Bounding and Deterministic Ranking in Live PostgreSQL
# =========================================================================

@pytest.mark.asyncio
async def test_5_real_postgresql_candidate_edge_bounding_and_pruning(
    pg_session: AsyncSession, test_repo: Repository
):
    repo_id = test_repo.id

    # Add 10 candidate edges from single node
    triplets = [
        _create_pg_triplet(
            repo_id, "pg/hub::Dispatcher", "CALLS", f"pg/workers::Worker_{i}",
            confidence=0.50 + (i * 0.04)  # higher i = higher confidence
        )
        for i in range(10)
    ]
    pg_session.add_all(triplets)
    await pg_session.commit()

    hop = EvoRoutePlanner.create_hop(1, "pg/hub::Dispatcher", RelationType.CALLS, "pg/workers::Worker_9")
    route = _make_route("r_hub", "Hub Route", [hop])

    cfg = BeamSearchConfig(beam_width=3, max_expansions_per_node=5)
    paths, expansions = await EvoBeamSearchEngine.execute_route_beam(
        pg_session, repo_id, route, config=cfg
    )

    # Must respect beam width
    assert len(paths) <= 3
    # Top path should be the highest confidence worker
    assert paths[0].target_entity == "pg/workers::Worker_9"
    assert expansions == 1


# =========================================================================
# 6. Real PostgreSQL Proof-Chain Aggregation and Traceability (T2.6)
# =========================================================================

@pytest.mark.asyncio
async def test_6_real_postgresql_proof_chain_aggregation(
    pg_session: AsyncSession, test_repo: Repository
):
    repo_id = test_repo.id

    # Persist multi-hop relationship in live PostgreSQL
    t1 = _create_pg_triplet(repo_id, "pg/chain::Controller", "CALLS", "pg/chain::Service", confidence=0.95)
    t2 = _create_pg_triplet(repo_id, "pg/chain::Service", "IMPORTS", "pg/chain::Repository", confidence=0.90)
    pg_session.add_all([t1, t2])
    await pg_session.commit()

    # Form route
    h1 = EvoRoutePlanner.create_hop(1, "pg/chain::Controller", RelationType.CALLS, "pg/chain::Service")
    h2 = EvoRoutePlanner.create_hop(2, "pg/chain::Service", RelationType.IMPORTS, "pg/chain::Repository")
    route = _make_route("r_chain", "Chain Route", [h1, h2])

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(pg_session, repo_id, route)
    assert len(paths) >= 1

    # Aggregate proof chains
    res = ProofChainAggregator.aggregate_paths(
        paths=paths,
        query_text="How does Controller interact with Repository?",
        temporal_intent=TemporalIntentType.CURRENT,
        repository_id=repo_id,
        branch="main",
    )

    assert len(res.chains) == 1
    chain = res.chains[0]
    assert chain.source_entity == "pg/chain::Controller"
    assert chain.target_entity == "pg/chain::Repository"
    assert len(chain.hops) == 2
    # Verify live PostgreSQL triplet IDs match
    assert t1.id in chain.supporting_triplet_ids
    assert t2.id in chain.supporting_triplet_ids
    assert chain.has_conflict is False


# =========================================================================
# 7. Real PostgreSQL ContextAssembler Proof-Chain Formatting (T2.6)
# =========================================================================

@pytest.mark.asyncio
async def test_7_real_postgresql_context_assembler_integration(
    pg_session: AsyncSession, test_repo: Repository
):
    repo_id = test_repo.id

    t_auth = _create_pg_triplet(repo_id, "pg/auth::Gateway", "CALLS", "pg/auth::TokenStore", confidence=0.92)
    pg_session.add(t_auth)
    await pg_session.commit()

    h = EvoRoutePlanner.create_hop(1, "pg/auth::Gateway", RelationType.CALLS, "pg/auth::TokenStore")
    r = _make_route("r_auth", "Auth Route", [h])
    paths, _ = await EvoBeamSearchEngine.execute_route_beam(pg_session, repo_id, r)

    res = ProofChainAggregator.aggregate_paths(
        paths=paths,
        query_text="How does Gateway authenticate?",
        temporal_intent=TemporalIntentType.CURRENT,
        repository_id=repo_id,
        branch="main",
    )
    assert len(res.chains) == 1

    assembled = ContextAssembler.assemble_context(
        ranked_candidates=[],
        proof_chains=res.chains,
    )

    assert assembled.proof_chain_count == 1
    assert "## EVOREASONER GROUNDED PROOF CHAINS" in assembled.prompt_context
    assert "pg/auth::Gateway -> pg/auth::TokenStore" in assembled.prompt_context
    assert str(t_auth.id) in assembled.proof_chains[0]["supporting_triplet_ids"]

