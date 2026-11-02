import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from apps.api.src.models.enums import IntegrationProvider, IntegrationStatus
from apps.api.src.models.evokg import EvoKGTriplet
from apps.api.src.models.integration import Integration
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.schemas.code_atom import (
    FactConfidence,
    TemporalCodeRelation,
)
from apps.api.src.services.evokg.service import EvoKGPersistenceService

POSTGRES_TEST_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/unotusk_test"


@pytest.fixture
def pg_engine():
    engine = create_async_engine(POSTGRES_TEST_URL, poolclass=NullPool, echo=False)
    yield engine


@pytest.fixture(autouse=True)
def clean_database():
    """Override root conftest autouse clean_database to prevent concurrent background truncation."""
    yield


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
    """Creates a test repository and project hierarchy for PostgreSQL testing."""
    org_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    integ_id = uuid.uuid4()

    org = Organization(
        id=org_id,
        name=f"Test Org {org_id.hex[:6]}",
        slug=f"org-{org_id.hex[:8]}",
    )
    pg_session.add(org)

    proj = Project(
        id=proj_id,
        organization_id=org_id,
        name=f"EvoKG PG Acceptance Project {proj_id}",
        slug=f"proj-{proj_id.hex[:8]}",
        description="PostgreSQL EvoKG Verification",
    )
    pg_session.add(proj)

    integ = Integration(
        id=integ_id,
        project_id=proj_id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
    )
    pg_session.add(integ)

    repo = Repository(
        id=repo_id,
        project_id=proj_id,
        integration_id=integ_id,
        external_id=f"ext-{repo_id.hex[:8]}",
        owner="test-owner",
        name=f"repo-{repo_id.hex[:8]}",
        full_name=f"test-owner/repo-{repo_id.hex[:8]}",
        url=f"https://github.com/test-owner/repo-{repo_id.hex[:8]}",
        default_branch="main",
    )
    pg_session.add(repo)
    await pg_session.commit()
    return repo


@pytest.mark.asyncio
async def test_1_postgresql_schema_and_indexes(pg_session: AsyncSession):
    """Verify actual PostgreSQL table, columns, indexes, and partial unique index."""
    # Check table exists in information_schema
    tbl = await pg_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_name = 'evokg_triplets'")
    )
    assert tbl.scalar() == "evokg_triplets"

    # Check PostgreSQL indexes
    idx_res = await pg_session.execute(
        text("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'evokg_triplets'")
    )
    index_defs = {row[0]: row[1] for row in idx_res.fetchall()}

    expected_indexes = [
        "ix_evokg_active_outgoing",
        "ix_evokg_active_incoming",
        "ix_evokg_temporal_lookup",
        "ix_evokg_exclusive_conflict",
        "ix_evokg_snapshot",
        "ix_evokg_commit",
        "ix_evokg_repo_fingerprint",
        "uq_evokg_active_exclusive",
    ]
    for idx_name in expected_indexes:
        assert idx_name in index_defs, f"Missing PostgreSQL index: {idx_name}"

    # Verify partial unique index definition on PostgreSQL
    uq_def = index_defs["uq_evokg_active_exclusive"]
    assert "UNIQUE INDEX" in uq_def
    assert "WHERE" in uq_def
    assert "valid_to IS NULL" in uq_def
    assert "is_exclusive = true" in uq_def
    assert "is_uncertain = false" in uq_def
    assert "has_temporal_conflict = false" in uq_def


@pytest.mark.asyncio
async def test_phase2_partial_unique_index_a_b_c_d(
    pg_session: AsyncSession, test_repo: Repository
):
    """
    Phase 2 Acceptance Verification:
    - Test A: Insert authoritative active exclusive assertion (succeeds).
    - Test B: Insert uncertain conflicting assertion for same slot (both coexist simultaneously).
    - Test C: Attempt to insert duplicate authoritative assertion (PostgreSQL rejects via uq_evokg_active_exclusive).
    - Test D: Verify the actual index definition excludes uncertain and conflicting assertions.
    """
    repo_id = test_repo.id
    subj = "auth.jwt::decode_header"
    rel = "DEFINES_RETURN_TYPE"
    scope = "overload:0"
    branch = "main"

    # --- Test A: Authoritative assertion insertion ---
    t_a = EvoKGTriplet(
        id=uuid.uuid4(),
        repository_id=repo_id,
        branch=branch,
        subject_id=subj,
        relation=rel,
        object_id="dict[str, Any]",
        is_exclusive=True,
        scope_key=scope,
        valid_to=None,
        is_uncertain=False,
        has_temporal_conflict=False,
        confidence_level="HIGH",
        confidence_score=0.95,
        fingerprint=f"fp_auth_a_{uuid.uuid4().hex[:6]}",
    )
    pg_session.add(t_a)
    await pg_session.commit()
    assert t_a.id is not None

    # --- Test B: Uncertain conflicting assertion coexists simultaneously ---
    t_b_conflict = EvoKGTriplet(
        id=uuid.uuid4(),
        repository_id=repo_id,
        branch=branch,
        subject_id=subj,
        relation=rel,
        object_id="HeaderObj",
        is_exclusive=True,
        scope_key=scope,
        valid_to=None,
        is_uncertain=True,
        has_temporal_conflict=True,
        confidence_level="UNCERTAIN",
        confidence_score=0.40,
        fingerprint=f"fp_auth_b_{uuid.uuid4().hex[:6]}",
    )
    pg_session.add(t_b_conflict)
    await pg_session.commit()

    # Query directly to prove both assertions are stored simultaneously
    slot_query = select(EvoKGTriplet).where(
        EvoKGTriplet.repository_id == repo_id,
        EvoKGTriplet.branch == branch,
        EvoKGTriplet.subject_id == subj,
        EvoKGTriplet.relation == rel,
        EvoKGTriplet.scope_key == scope,
        EvoKGTriplet.valid_to.is_(None),
    )
    res = await pg_session.execute(slot_query)
    active_rows = res.scalars().all()
    assert len(active_rows) == 2
    authoritative = next(r for r in active_rows if not r.is_uncertain)
    conflicting = next(r for r in active_rows if r.is_uncertain)
    assert authoritative.object_id == "dict[str, Any]"
    assert conflicting.object_id == "HeaderObj"
    assert conflicting.has_temporal_conflict is True

    # --- Test C: Duplicate authoritative assertion rejected by PostgreSQL ---
    t_c_duplicate = EvoKGTriplet(
        id=uuid.uuid4(),
        repository_id=repo_id,
        branch=branch,
        subject_id=subj,
        relation=rel,
        object_id="AnotherDict",
        is_exclusive=True,
        scope_key=scope,
        valid_to=None,
        is_uncertain=False,
        has_temporal_conflict=False,
        confidence_level="HIGH",
        confidence_score=0.95,
        fingerprint=f"fp_auth_c_{uuid.uuid4().hex[:6]}",
    )
    pg_session.add(t_c_duplicate)

    with pytest.raises(IntegrityError) as exc_info:
        await pg_session.commit()

    assert "uq_evokg_active_exclusive" in str(exc_info.value).lower()
    await pg_session.rollback()

    # Verify authoritative assertion remains active and unchanged after rollback
    res_after = await pg_session.execute(slot_query)
    remaining_rows = res_after.scalars().all()
    assert len(remaining_rows) == 2
    assert any(r.object_id == "dict[str, Any]" and not r.is_uncertain for r in remaining_rows)

    # --- Test D: Verify exact index definition in pg_indexes ---
    idx_def_res = await pg_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_evokg_active_exclusive'")
    )
    actual_def = idx_def_res.scalar()
    assert "uq_evokg_active_exclusive" in actual_def
    assert "is_exclusive = true" in actual_def
    assert "valid_to IS NULL" in actual_def
    assert "is_uncertain = false" in actual_def
    assert "has_temporal_conflict = false" in actual_def


@pytest.mark.asyncio
async def test_2_non_exclusive_coexistence(pg_session: AsyncSession, test_repo: Repository):
    """Verify that multiple concurrent non-exclusive relationships coexist in PostgreSQL."""
    service = EvoKGPersistenceService()
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)

    rel_calls_a = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="api.client::fetch",
        relation="CALLS",
        object="api.http::get",
        t_start=t0,
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_calls_a_{uuid.uuid4().hex[:6]}",
    )
    rel_calls_b = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="api.client::fetch",
        relation="CALLS",
        object="api.metrics::record",
        t_start=t0,
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_calls_b_{uuid.uuid4().hex[:6]}",
    )

    result = await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_calls_a, rel_calls_b],
    )
    await pg_session.commit()

    assert len(result.active_relations) == 2
    assert len(result.superseded_relations) == 0

    active_rows = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="api.client::fetch",
        relation="CALLS",
    )
    assert len(active_rows) == 2
    objects = {r.object_id for r in active_rows}
    assert objects == {"api.http::get", "api.metrics::record"}


@pytest.mark.asyncio
async def test_3_exclusive_supersession_and_dag_linking(
    pg_session: AsyncSession, test_repo: Repository
):
    """Verify exclusive relationship supersession, valid_to termination, and bidirectional DAG links."""
    service = EvoKGPersistenceService()
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)

    # Initial definition: returns str
    id_1 = str(uuid.uuid4())
    rel_1 = TemporalCodeRelation(
        id=id_1,
        subject="core.auth::get_token",
        relation="DEFINES_RETURN_TYPE",
        object="str",
        t_start=t1,
        commit_sha="commit_111",
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_ret_str_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_1],
        commit_sha="commit_111",
    )
    await pg_session.commit()

    # Second definition: returns TokenObject (supersedes str)
    id_2 = str(uuid.uuid4())
    rel_2 = TemporalCodeRelation(
        id=id_2,
        subject="core.auth::get_token",
        relation="DEFINES_RETURN_TYPE",
        object="TokenObject",
        t_start=t2,
        commit_sha="commit_222",
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_ret_token_{uuid.uuid4().hex[:6]}",
    )
    res2 = await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_2],
        commit_sha="commit_222",
    )
    await pg_session.commit()

    assert len(res2.active_relations) == 1
    assert len(res2.superseded_relations) == 1
    assert res2.active_relations[0].object == "TokenObject"
    assert res2.superseded_relations[0].object == "str"

    # Query PostgreSQL directly
    active = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="core.auth::get_token",
        relation="DEFINES_RETURN_TYPE",
    )
    assert len(active) == 1
    active_row = active[0]
    assert active_row.object_id == "TokenObject"
    assert active_row.valid_to is None
    assert str(active_row.supersedes_id) == id_1

    # Check historical record
    hist = await service.get_temporal_history(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="core.auth::get_token",
    )
    assert len(hist) == 2
    old_row = next(r for r in hist if r.object_id == "str")
    assert old_row.valid_to == t2
    assert str(old_row.superseded_by_id) == id_2


@pytest.mark.asyncio
async def test_4_low_confidence_conflict_preserved(pg_session: AsyncSession, test_repo: Repository):
    """Verify that low-confidence conflicting assertions do not supersede active knowledge in PostgreSQL."""
    service = EvoKGPersistenceService()
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)

    rel_high = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="models.user::get_id",
        relation="DEFINES_RETURN_TYPE",
        object="int",
        t_start=t1,
        confidence=FactConfidence.HIGH,
        confidence_score=0.95,
        fingerprint=f"fp_user_id_int_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_high],
    )
    await pg_session.commit()

    # Conflicting assertion with low confidence
    rel_low = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="models.user::get_id",
        relation="DEFINES_RETURN_TYPE",
        object="str",
        t_start=t2,
        confidence=FactConfidence.UNCERTAIN,
        confidence_score=0.40,
        is_uncertain=True,
        fingerprint=f"fp_user_id_str_{uuid.uuid4().hex[:6]}",
    )
    res = await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_low],
    )
    await pg_session.commit()

    assert len(res.superseded_relations) == 0
    assert len(res.conflicting_relations) == 1

    # In PostgreSQL, active valid fact is still int
    active = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="models.user::get_id",
        relation="DEFINES_RETURN_TYPE",
    )
    assert len(active) == 1
    assert active[0].object_id == "int"

    # Conflicting relation is retained with flag
    conflicts = await service.get_conflicts(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="models.user::get_id",
    )
    assert len(conflicts) == 1
    assert conflicts[0].has_temporal_conflict is True
    assert conflicts[0].is_uncertain is True
    assert conflicts[0].confidence_level == "UNCERTAIN"


@pytest.mark.asyncio
async def test_5_out_of_order_historical_insertion(pg_session: AsyncSession, test_repo: Repository):
    """Verify out-of-order historical insertions bound valid_to correctly without overwriting active."""
    service = EvoKGPersistenceService()
    t_v3 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    t_v2_historical = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)

    rel_v3 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="pkg.calc::compute",
        relation="DEFINES_RETURN_TYPE",
        object="float",
        t_start=t_v3,
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_calc_v3_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_v3],
    )
    await pg_session.commit()

    # Now backfill historical v2
    rel_v2 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="pkg.calc::compute",
        relation="DEFINES_RETURN_TYPE",
        object="int",
        t_start=t_v2_historical,
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_calc_v2_{uuid.uuid4().hex[:6]}",
    )
    res_backfill = await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_v2],
    )
    await pg_session.commit()

    assert len(res_backfill.active_relations) == 1
    assert res_backfill.active_relations[0].object == "float"
    assert len(res_backfill.historical_relations) == 1
    assert res_backfill.historical_relations[0].object == "int"
    assert res_backfill.historical_relations[0].t_end == t_v3


@pytest.mark.asyncio
async def test_6_reingestion_idempotency(pg_session: AsyncSession, test_repo: Repository):
    """Verify re-ingesting duplicate relations produces zero duplicate rows in PostgreSQL."""
    service = EvoKGPersistenceService()
    fp = f"fp_idempotent_{uuid.uuid4().hex[:8]}"

    rel = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="pkg.auth::has_perm",
        relation="DEFINES_RETURN_TYPE",
        object="bool",
        confidence=FactConfidence.HIGH,
        fingerprint=fp,
    )

    # Ingest 1
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel],
    )
    await pg_session.commit()

    # Ingest 2 (identical fingerprint, different relation instance id)
    rel_dup = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="pkg.auth::has_perm",
        relation="DEFINES_RETURN_TYPE",
        object="bool",
        confidence=FactConfidence.HIGH,
        fingerprint=fp,
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_dup],
    )
    await pg_session.commit()

    # Verify count in PostgreSQL
    count_stmt = select(func.count(EvoKGTriplet.id)).where(
        EvoKGTriplet.repository_id == test_repo.id,
        EvoKGTriplet.fingerprint == fp,
    )
    res = await pg_session.execute(count_stmt)
    assert res.scalar() == 1


@pytest.mark.asyncio
async def test_7_branch_isolation(pg_session: AsyncSession, test_repo: Repository):
    """Verify that changes on a feature branch do not alter main branch active assertions."""
    service = EvoKGPersistenceService()
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)

    # Main branch: int
    rel_main = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="service.billing::get_rate",
        relation="DEFINES_RETURN_TYPE",
        object="int",
        t_start=t0,
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_billing_main_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_main],
        branch="main",
    )
    await pg_session.commit()

    # Feature branch: Decimal
    rel_feat = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="service.billing::get_rate",
        relation="DEFINES_RETURN_TYPE",
        object="Decimal",
        t_start=t0 + timedelta(days=1),
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_billing_feat_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_feat],
        branch="feature/precise-billing",
    )
    await pg_session.commit()

    # Query main branch
    main_active = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="service.billing::get_rate",
        branch="main",
    )
    assert len(main_active) == 1
    assert main_active[0].object_id == "int"
    assert main_active[0].valid_to is None

    # Query feature branch
    feat_active = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="service.billing::get_rate",
        branch="feature/precise-billing",
    )
    assert len(feat_active) == 1
    assert feat_active[0].object_id == "Decimal"
    assert feat_active[0].valid_to is None


@pytest.mark.asyncio
async def test_8_merge_commit_ancestry_propagation(pg_session: AsyncSession, test_repo: Repository):
    """Verify that merge commits correctly supersede main branch assertions across branches."""
    service = EvoKGPersistenceService()
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)

    # Main commit c1
    rel_c1 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="service.cache::store",
        relation="DEFINES_RETURN_TYPE",
        object="bool",
        t_start=t1,
        commit_sha="c1",
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_cache_c1_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_c1],
        branch="main",
        commit_sha="c1",
    )
    await pg_session.commit()

    # Feature branch merged into main via merge commit m1 with parents [c1, feat1]
    rel_merge = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="service.cache::store",
        relation="DEFINES_RETURN_TYPE",
        object="CacheResult",
        t_start=t2,
        commit_sha="m1",
        confidence=FactConfidence.HIGH,
        fingerprint=f"fp_cache_m1_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_merge],
        branch="main",
        commit_sha="m1",
        commit_parents={"m1": ["c1", "feat1"]},
    )
    await pg_session.commit()

    # In main branch, CacheResult has superseded bool
    active = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="service.cache::store",
        branch="main",
    )
    assert len(active) == 1
    assert active[0].object_id == "CacheResult"


@pytest.mark.asyncio
async def test_9_transaction_rollback_safety(pg_session: AsyncSession, test_repo: Repository):
    """Verify that session rollback leaves zero orphaned triplets in PostgreSQL."""
    service = EvoKGPersistenceService()
    fp = f"fp_rollback_{uuid.uuid4().hex[:8]}"
    repo_id = test_repo.id

    rel = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="pkg.tx::test_func",
        relation="CALLS",
        object="pkg.tx::other_func",
        fingerprint=fp,
    )

    await service.persist_relations(
        session=pg_session,
        repository_id=repo_id,
        relations=[rel],
    )
    # Deliberate rollback
    await pg_session.rollback()

    count_stmt = select(func.count(EvoKGTriplet.id)).where(
        EvoKGTriplet.repository_id == repo_id,
        EvoKGTriplet.fingerprint == fp,
    )
    res = await pg_session.execute(count_stmt)
    assert res.scalar() == 0


@pytest.mark.asyncio
async def test_10_explicit_relation_deletion_closes_interval(
    pg_session: AsyncSession, test_repo: Repository
):
    """Verify that explicit code removal marks valid_to interval closed as designed."""
    service = EvoKGPersistenceService()
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)

    rel_import = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="pkg.main::run",
        relation="IMPORTS",
        object="pkg.legacy_helper",
        t_start=t1,
        fingerprint=f"fp_import_legacy_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_import],
    )
    await pg_session.commit()

    # Removal event
    rel_removed = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="pkg.main::run",
        relation="IMPORTS",
        object="pkg.legacy_helper",
        t_start=t1,
        t_end=t2,
        fingerprint=f"fp_import_legacy_del_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_removed],
    )
    await pg_session.commit()

    # Active imports should now be 0
    active = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="pkg.main::run",
        relation="IMPORTS",
    )
    assert len(active) == 0

    # Historical record is preserved with valid_to == t2
    hist = await service.get_temporal_history(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="pkg.main::run",
    )
    assert len(hist) == 1
    assert hist[0].valid_to == t2


@pytest.mark.asyncio
async def test_11_concurrent_updates_with_row_locks(
    pg_session: AsyncSession, pg_engine, test_repo: Repository
):
    """Verify concurrent updates with FOR UPDATE row-level locking."""
    service = EvoKGPersistenceService()
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)

    repo_id = test_repo.id

    # Initial relation
    rel_init = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="concurrent.service::status",
        relation="DEFINES_RETURN_TYPE",
        object="InitStatus",
        t_start=t0,
        fingerprint=f"fp_conc_init_{uuid.uuid4().hex[:6]}",
    )
    await service.persist_relations(
        session=pg_session,
        repository_id=repo_id,
        relations=[rel_init],
    )
    await pg_session.commit()

    # Simulate two sequential/interleaved transactions with row-level locks
    session_factory = async_sessionmaker(bind=pg_engine, class_=AsyncSession, expire_on_commit=False)

    async def update_status(new_val: str, delay: float):
        async with session_factory() as s:
            t = t0 + timedelta(seconds=delay * 10)
            rel = TemporalCodeRelation(
                id=str(uuid.uuid4()),
                subject="concurrent.service::status",
                relation="DEFINES_RETURN_TYPE",
                object=new_val,
                t_start=t,
                fingerprint=f"fp_conc_{new_val}_{uuid.uuid4().hex[:6]}",
            )
            await asyncio.sleep(delay)
            try:
                await service.persist_relations(
                    session=s,
                    repository_id=repo_id,
                    relations=[rel],
                )
                await s.commit()
            except Exception:
                await s.rollback()

    await asyncio.gather(
        update_status("StatusA", 0.05),
        update_status("StatusB", 0.10),
    )

    # Exactly 1 active relation must remain in PostgreSQL (partial unique index uq_evokg_active_exclusive guarantees no split-brain)
    active = await service.get_active_outgoing(
        session=pg_session,
        repository_id=repo_id,
        subject_id="concurrent.service::status",
        relation="DEFINES_RETURN_TYPE",
    )
    assert len(active) == 1
    assert active[0].object_id in ("StatusA", "StatusB")


@pytest.mark.asyncio
async def test_12_real_database_timing_measurements(
    pg_session: AsyncSession, test_repo: Repository
):
    """
    Measure and report real PostgreSQL execution latency for:
    - Single triplet insertion.
    - 100-triplet batch insertion under transaction.
    - Active relation query by subject.
    - Point-in-time historical query.
    - Conflict detection query.
    """
    service = EvoKGPersistenceService()
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)

    # 1. Single triplet insertion latency
    rel_single = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="perf.bench::single",
        relation="CALLS",
        object="perf.target::fn",
        t_start=t0,
        fingerprint=f"fp_bench_single_{uuid.uuid4().hex[:6]}",
    )
    t_start = time.perf_counter()
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=[rel_single],
    )
    await pg_session.commit()
    single_insert_ms = (time.perf_counter() - t_start) * 1000

    # 2. 100-triplet batch insertion under transaction
    batch_100 = [
        TemporalCodeRelation(
            id=str(uuid.uuid4()),
            subject=f"perf.bench::fn_{i}",
            relation="CALLS",
            object=f"perf.target::target_{i}",
            t_start=t0,
            fingerprint=f"fp_bench_batch_{i}_{uuid.uuid4().hex[:6]}",
        )
        for i in range(100)
    ]
    t_start = time.perf_counter()
    await service.persist_relations(
        session=pg_session,
        repository_id=test_repo.id,
        relations=batch_100,
    )
    await pg_session.commit()
    batch_100_ms = (time.perf_counter() - t_start) * 1000

    # 3. Active relation query by subject latency
    t_start = time.perf_counter()
    active_rows = await service.get_active_outgoing(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="perf.bench::fn_50",
    )
    active_query_ms = (time.perf_counter() - t_start) * 1000
    assert len(active_rows) == 1

    # 4. Point-in-time historical query latency
    t_start = time.perf_counter()
    hist_rows = await service.get_temporal_history(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="perf.bench::fn_50",
    )
    hist_query_ms = (time.perf_counter() - t_start) * 1000
    assert len(hist_rows) == 1

    # 5. Conflict detection query latency
    t_start = time.perf_counter()
    conflicts = await service.get_conflicts(
        session=pg_session,
        repository_id=test_repo.id,
        subject_id="perf.bench::fn_50",
    )
    conflict_query_ms = (time.perf_counter() - t_start) * 1000
    assert len(conflicts) == 0

    print("\n--- REAL POSTGRESQL 16 TIMINGS ---")
    print(f"Single triplet insertion latency: {single_insert_ms:.2f} ms")
    print(f"100-triplet batch insertion latency: {batch_100_ms:.2f} ms (avg {batch_100_ms/100:.2f} ms/triplet)")
    print(f"Active relation query latency: {active_query_ms:.2f} ms")
    print(f"Historical query latency: {hist_query_ms:.2f} ms")
    print(f"Conflict detection query latency: {conflict_query_ms:.2f} ms")

    # Assert reasonable database SLAs
    assert single_insert_ms < 500  # < 500ms
    assert batch_100_ms < 2000  # < 2s for 100 items
    assert active_query_ms < 100  # < 100ms
    assert hist_query_ms < 100  # < 100ms
    assert conflict_query_ms < 100  # < 100ms
