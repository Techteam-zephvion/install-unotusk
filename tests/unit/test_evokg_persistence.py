import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.src.db.base import Base
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
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.code_atom import (
    FactConfidence,
    RelationType,
    TemporalCodeRelation,
)
from apps.api.src.services.evokg.service import EvoKGPersistenceService


def _dt(offset_hours: int) -> datetime:
    return datetime(2026, 11, 1, 10, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=UTC) if dt and dt.tzinfo is None else dt


@pytest.fixture
async def async_db():
    """Sets up an in-memory SQLite async engine with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        # Seed Organization, Project, Integration, Repository, Snapshot
        org = Organization(id=uuid.uuid4(), name="Acme Corp", slug="acme")
        session.add(org)
        await session.flush()

        proj = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Alpha Project",
            slug="alpha",
            status=ProjectStatus.READY,
        )
        session.add(proj)
        await session.flush()

        integ = Integration(
            id=uuid.uuid4(),
            project_id=proj.id,
            provider=IntegrationProvider.GITHUB,
            status=IntegrationStatus.CONNECTED,
        )
        session.add(integ)
        await session.flush()

        repo = Repository(
            id=uuid.uuid4(),
            project_id=proj.id,
            integration_id=integ.id,
            external_id="ext-alpha-1",
            owner="acme",
            name="alpha-core",
            full_name="acme/alpha-core",
            default_branch="main",
            url="https://github.com/acme/alpha-core",
        )
        session.add(repo)
        await session.flush()

        snap = RepositorySnapshot(
            id=uuid.uuid4(),
            repository_id=repo.id,
            branch="main",
            commit_sha="c000000000000000000000000000000000000000",
        )
        session.add(snap)
        await session.commit()

        yield {
            "session": session,
            "engine": engine,
            "repo_id": repo.id,
            "snap_id": snap.id,
            "factory": session_factory,
        }

    await engine.dispose()


@pytest.mark.asyncio
async def test_1_non_exclusive_relationships_coexist(async_db):
    """Verify non-exclusive relationships (CALLS, IMPORTS) coexist concurrently."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    r1 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.CALLS,
        object="apps/api/src/jwt.py::decode",
        t_start=_dt(1),
        confidence_score=0.95,
        fingerprint="fp_call_1",
    )
    r2 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.CALLS,
        object="apps/api/src/db.py::find_user",
        t_start=_dt(2),
        confidence_score=0.95,
        fingerprint="fp_call_2",
    )

    res = await service.persist_relations(session, repo_id, [r1, r2], branch="main")
    assert len(res.active_relations) == 2

    # Query active outgoing
    active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(active) == 2
    assert {a.object_id for a in active} == {
        "apps/api/src/jwt.py::decode",
        "apps/api/src/db.py::find_user",
    }
    assert all(a.valid_to is None for a in active)


@pytest.mark.asyncio
async def test_2_exclusive_relationships_supersede_and_link(async_db):
    """Verify exclusive relation (DEFINES_RETURN_TYPE) supersedes previous assertion with valid_to and links."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    r_old_id = str(uuid.uuid4())
    r_old = TemporalCodeRelation(
        id=r_old_id,
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="bool",
        t_start=_dt(1),
        confidence_score=0.95,
        fingerprint="fp_ret_v1",
    )
    await service.persist_relations(session, repo_id, [r_old], branch="main")

    # Confirm v1 is active
    active_v1 = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(active_v1) == 1
    assert active_v1[0].object_id == "bool"
    assert active_v1[0].valid_to is None

    # Ingest newer assertion v2
    r_new_id = str(uuid.uuid4())
    r_new = TemporalCodeRelation(
        id=r_new_id,
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="UserTokenPayload",
        t_start=_dt(5),
        confidence_score=0.95,
        fingerprint="fp_ret_v2",
    )
    res = await service.persist_relations(session, repo_id, [r_new], branch="main")

    assert len(res.active_relations) == 1
    assert res.active_relations[0].canonical_object == "UserTokenPayload"
    assert len(res.superseded_relations) == 1

    # Check active outgoing in DB: only v2 is active
    active_now = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(active_now) == 1
    assert active_now[0].object_id == "UserTokenPayload"
    assert _ensure_utc(active_now[0].valid_from) == _dt(5)
    assert active_now[0].valid_to is None
    assert str(active_now[0].supersedes_id) == r_old_id

    # Check historical evolution: both v1 and v2 exist, v1 has valid_to set to _dt(5)
    history = await service.get_temporal_history(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(history) == 2
    v1_triplet = next(h for h in history if h.object_id == "bool")
    assert _ensure_utc(v1_triplet.valid_to) == _dt(5)
    assert str(v1_triplet.superseded_by_id) == r_new_id


@pytest.mark.asyncio
async def test_3_low_confidence_conflict_preserved(async_db):
    """Verify low-confidence conflicting assertions do not terminate active assertions."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    # Active high-confidence assertion
    r_active = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/calc.py::compute",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="float",
        t_start=_dt(2),
        confidence_score=0.95,
        fingerprint="fp_calc_active",
    )
    await service.persist_relations(session, repo_id, [r_active], branch="main")

    # Conflicting low-confidence assertion (score = 0.40 < 0.65)
    r_low = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/calc.py::compute",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="int",
        t_start=_dt(4),
        confidence_score=0.40,
        confidence=FactConfidence.UNCERTAIN,
        fingerprint="fp_calc_low",
    )
    res = await service.persist_relations(session, repo_id, [r_low], branch="main")

    assert len(res.active_relations) == 1
    assert res.active_relations[0].canonical_object == "float"
    assert len(res.conflicting_relations) == 1

    # Active assertion in DB remains float
    active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/calc.py::compute"
    )
    assert len(active) == 1
    assert active[0].object_id == "float"
    assert active[0].valid_to is None

    # Conflicting triplet query returns r_low flagged as uncertain
    conflicts = await service.get_conflicts(
        session, repo_id, branch="main", subject_id="apps/api/src/calc.py::compute"
    )
    assert len(conflicts) == 1
    assert conflicts[0].object_id == "int"
    assert conflicts[0].is_uncertain is True
    assert conflicts[0].has_temporal_conflict is True


@pytest.mark.asyncio
async def test_4_out_of_order_historical_insertion(async_db):
    """Verify earlier historical assertions insert with interval [t_new, t_old] without displacing active."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    # Current active assertion at t=10
    r_current = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/config.py::get_timeout",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="int",
        t_start=_dt(10),
        confidence_score=0.95,
        fingerprint="fp_curr_int",
    )
    await service.persist_relations(session, repo_id, [r_current], branch="main")

    # Out-of-order historical assertion from t=2
    r_hist = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/config.py::get_timeout",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="float",
        t_start=_dt(2),
        confidence_score=0.90,
        fingerprint="fp_hist_float",
    )
    res = await service.persist_relations(session, repo_id, [r_hist], branch="main")

    assert len(res.active_relations) == 1
    assert res.active_relations[0].canonical_object == "int"
    assert len(res.historical_relations) == 1
    assert res.historical_relations[0].t_start == _dt(2)
    assert res.historical_relations[0].t_end == _dt(10)

    # Active remains int
    active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/config.py::get_timeout"
    )
    assert len(active) == 1
    assert active[0].object_id == "int"

    # Historical record is persisted with bounded interval [t=2, t=10]
    history = await service.get_temporal_history(
        session, repo_id, "apps/api/src/config.py::get_timeout"
    )
    assert len(history) == 2
    h_float = next(h for h in history if h.object_id == "float")
    assert _ensure_utc(h_float.valid_from) == _dt(2)
    assert _ensure_utc(h_float.valid_to) == _dt(10)


@pytest.mark.asyncio
async def test_5_idempotent_reingestion(async_db):
    """Verify re-ingesting the exact same batch produces no duplicates."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    rel = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::login",
        relation=RelationType.CALLS,
        object="apps/api/src/db.py::find_user",
        t_start=_dt(1),
        confidence_score=0.95,
        fingerprint="fp_idem_login",
    )

    # First pass
    await service.persist_relations(session, repo_id, [rel], branch="main")
    # Second pass with same fingerprint
    await service.persist_relations(session, repo_id, [rel], branch="main")

    active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::login"
    )
    assert len(active) == 1


@pytest.mark.asyncio
async def test_6_branch_isolation(async_db):
    """Verify feature branch assertions do not supersede main branch assertions."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    # Main branch assertion
    r_main = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::get_role",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="str",
        provenance={"branch": "main"},
        t_start=_dt(2),
        confidence_score=0.95,
        fingerprint="fp_role_main",
    )
    await service.persist_relations(session, repo_id, [r_main], branch="main")

    # Feature branch assertion
    r_feat = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::get_role",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="RoleEnum",
        provenance={"branch": "feature/roles"},
        t_start=_dt(5),
        confidence_score=0.95,
        fingerprint="fp_role_feat",
    )
    res = await service.persist_relations(session, repo_id, [r_feat], branch="feature/roles")
    assert len(res.active_relations) == 1

    # Both branches maintain their independent active assertions
    main_active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::get_role", branch="main"
    )
    assert len(main_active) == 1
    assert main_active[0].object_id == "str"

    feat_active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::get_role", branch="feature/roles"
    )
    assert len(feat_active) == 1
    assert feat_active[0].object_id == "RoleEnum"


@pytest.mark.asyncio
async def test_7_commit_ancestry_and_merge_commit(async_db):
    """Verify merge commit with verified ancestry supersedes across branch."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    commit_parents = {
        "c_feat": ["c_base"],
        "c_merge": ["c_base", "c_feat"],
    }

    # Pre-merge assertion on feature branch
    r_premerge = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::verify_v2",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="OldType",
        commit_sha="c_feat",
        provenance={"branch": "main"},
        t_start=_dt(2),
        confidence_score=0.95,
        fingerprint="fp_premerge",
    )
    await service.persist_relations(
        session, repo_id, [r_premerge], branch="main", commit_parents=commit_parents
    )

    # Merge commit on main
    r_merge = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::verify_v2",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="MergedType",
        commit_sha="c_merge",
        provenance={"branch": "main"},
        t_start=_dt(5),
        confidence_score=0.95,
        fingerprint="fp_merge",
    )
    res = await service.persist_relations(
        session, repo_id, [r_merge], branch="main", commit_parents=commit_parents
    )

    assert len(res.active_relations) == 1
    assert res.active_relations[0].canonical_object == "MergedType"
    assert len(res.superseded_relations) == 1

    active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_v2", branch="main"
    )
    assert len(active) == 1
    assert active[0].object_id == "MergedType"


@pytest.mark.asyncio
async def test_8_explicit_removal_closure(async_db):
    """Verify explicit removal closes relationship."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    r_active = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/app.py",
        relation=RelationType.IMPORTS,
        object="legacy_package",
        t_start=_dt(1),
        confidence_score=0.95,
        fingerprint="fp_imp_legacy",
    )
    await service.persist_relations(session, repo_id, [r_active], branch="main")

    # Ingest explicit removal
    r_remove = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/app.py",
        relation=RelationType.IMPORTS,
        object="legacy_package",
        t_end=_dt(3),
        provenance={"change_type": "DELETE", "is_removal": True},
        fingerprint="fp_imp_legacy_del",
    )
    await service.persist_relations(session, repo_id, [r_remove], branch="main")

    active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/app.py", relation="IMPORTS"
    )
    assert len(active) == 0


@pytest.mark.asyncio
async def test_9_point_in_time_temporal_traversal(async_db):
    """Verify as_of queries return the active state at any historic moment."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    # Step 1: at t=1, returns TypeA
    r1 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="api/endpoint",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="TypeA",
        t_start=_dt(1),
        confidence_score=0.95,
        fingerprint="fp_ts_1",
    )
    await service.persist_relations(session, repo_id, [r1])

    # Step 2: at t=5, supersedes with TypeB
    r2 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="api/endpoint",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="TypeB",
        t_start=_dt(5),
        confidence_score=0.95,
        fingerprint="fp_ts_2",
    )
    await service.persist_relations(session, repo_id, [r2])

    # Query as of t=3: should return TypeA
    at_t3 = await service.get_temporal_history(
        session, repo_id, "api/endpoint", as_of=_dt(3)
    )
    assert len(at_t3) == 1
    assert at_t3[0].object_id == "TypeA"

    # Query as of t=6: should return TypeB
    at_t6 = await service.get_temporal_history(
        session, repo_id, "api/endpoint", as_of=_dt(6)
    )
    assert len(at_t6) == 1
    assert at_t6[0].object_id == "TypeB"


@pytest.mark.asyncio
async def test_10_transaction_rollback_safety(async_db):
    """Verify that if a transaction fails midway, no corrupt partial state remains."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    r1 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="api/service::auth",
        relation=RelationType.CALLS,
        object="api/service::helper",
        t_start=_dt(1),
        fingerprint="fp_rollback_valid",
    )
    await service.persist_relations(session, repo_id, [r1])
    await session.commit()

    # Intentionally trigger an error during an attempt
    try:
        async with session.begin_nested():
            # Ingest invalid triplet violating not-null constraint
            bad_triplet = EvoKGTriplet(
                id=uuid.uuid4(),
                repository_id=repo_id,
                branch="main",
                subject_id=None,  # Not null violation
                relation="CALLS",
                object_id="something",
                fingerprint="fp_corrupt",
            )
            session.add(bad_triplet)
            await session.flush()
    except Exception:
        await session.rollback()

    # Verify original state is completely preserved
    active = await service.get_active_outgoing(session, repo_id, "api/service::auth")
    assert len(active) == 1
    assert active[0].object_id == "api/service::helper"


@pytest.mark.asyncio
async def test_11_performance_and_throughput_measurement(async_db):
    """Measures insertion throughput and indexed query latency for active edges."""
    session = async_db["session"]
    repo_id = async_db["repo_id"]
    service = EvoKGPersistenceService()

    batch_size = 50
    test_relations = [
        TemporalCodeRelation(
            id=str(uuid.uuid4()),
            subject=f"pkg/service_{i % 5}.py::func_{i}",
            relation=RelationType.CALLS,
            object=f"pkg/dep_{i % 3}.py::target_{i}",
            t_start=_dt(1),
            confidence_score=0.95,
            fingerprint=f"fp_perf_{i}",
        )
        for i in range(batch_size)
    ]

    t0 = time.perf_counter()
    res = await service.persist_relations(session, repo_id, test_relations, branch="main")
    await session.commit()
    t_persist = (time.perf_counter() - t0) * 1000

    assert len(res.active_relations) == batch_size

    # Measure active outgoing edge lookup latency
    t1 = time.perf_counter()
    outgoing = await service.get_active_outgoing(session, repo_id, "pkg/service_0.py::func_0")
    t_query = (time.perf_counter() - t1) * 1000

    assert len(outgoing) >= 1
    print(f"\n[EvoKG Benchmark] {batch_size} triplets persisted in {t_persist:.2f}ms ({t_persist/batch_size:.2f}ms/triplet); indexed query latency: {t_query:.2f}ms")
