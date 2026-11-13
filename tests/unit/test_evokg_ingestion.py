import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.src.config.settings import settings
from apps.api.src.db.base import Base
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    ProjectStatus,
    SymbolType,
)
from apps.api.src.models.evokg import EvoKGTriplet
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.schemas.code_atom import (
    GitCommitArtifact,
    RelationType,
    TemporalCodeRelation,
)
from apps.api.src.services.evokg.service import EvoKGPersistenceService
from apps.api.src.services.ingestion_service import IngestionService

DIFF_ADD_RETURN_TYPE = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
index 1111111..2222222 100644
--- a/apps/api/src/auth.py
+++ b/apps/api/src/auth.py
@@ -10,3 +10,4 @@
 def verify_token(token: str) -> bool:
     if not token:
         return False
+    jwt.decode(token)
"""

DIFF_MODIFY_RETURN_TYPE = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
index 2222222..3333333 100644
--- a/apps/api/src/auth.py
+++ b/apps/api/src/auth.py
@@ -10,4 +10,4 @@
-def verify_token(token: str) -> bool:
+def verify_token(token: str) -> TokenPayload:
     if not token:
-        return False
+        return None
"""


@pytest.fixture
async def ingestion_db():
    """Sets up an in-memory SQLite async engine for ingestion tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        org = Organization(id=uuid.uuid4(), name="Acme Corp", slug="acme")
        session.add(org)
        await session.flush()

        proj = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Core Repo",
            slug="core",
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
            external_id="ext-core-1",
            owner="acme",
            name="core-service",
            full_name="acme/core-service",
            default_branch="main",
            url="https://github.com/acme/core-service",
        )
        session.add(repo)
        await session.flush()

        snap = RepositorySnapshot(
            id=uuid.uuid4(),
            repository_id=repo.id,
            branch="main",
            commit_sha="c111111111111111111111111111111111111111",
        )
        session.add(snap)
        await session.flush()

        repo_file = RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snap.id,
            path="apps/api/src/auth.py",
            filename="auth.py",
            extension=".py",
            content_hash="hash1",
        )
        session.add(repo_file)
        await session.flush()

        sym = CodeSymbol(
            id=uuid.uuid4(),
            file_id=repo_file.id,
            name="verify_token",
            symbol_type=SymbolType.FUNCTION,
            qualified_name="verify_token",
            start_line=10,
            end_line=20,
        )
        session.add(sym)
        await session.commit()

        yield {
            "session": session,
            "engine": engine,
            "repo_id": repo.id,
            "snap_id": snap.id,
            "file_id": repo_file.id,
            "sym_id": sym.id,
        }

    await engine.dispose()


@pytest.mark.asyncio
async def test_1_evokg_disabled_by_default_preserves_existing_behavior(ingestion_db):
    """Verify that with EVOKG_ENABLED=False (default), no triplets are persisted."""
    session = ingestion_db["session"]
    snap_id = ingestion_db["snap_id"]
    repo_id = ingestion_db["repo_id"]

    assert settings.EVOKG_ENABLED is False

    commit = GitCommitArtifact(
        commit_sha="c111111111111111111111111111111111111111",
        commit_message="feat: initial auth verify",
        raw_diff=DIFF_ADD_RETURN_TYPE,
    )

    chunks = await IngestionService.ingest_commit_atom_changes(
        session=session,
        snapshot_id=snap_id,
        commit_artifact=commit,
        repository_id=repo_id,
    )

    assert len(chunks) >= 1

    # Verify no triplets were written to evokg_triplets
    triplet_res = await session.execute(
        select(EvoKGTriplet).where(EvoKGTriplet.repository_id == repo_id)
    )
    triplets = triplet_res.scalars().all()
    assert len(triplets) == 0


@pytest.mark.asyncio
async def test_2_evokg_enabled_persists_triplets(ingestion_db):
    """Verify that with EVOKG_ENABLED=True, relations are extracted and persisted."""
    session = ingestion_db["session"]
    snap_id = ingestion_db["snap_id"]
    repo_id = ingestion_db["repo_id"]

    commit = GitCommitArtifact(
        commit_sha="c111111111111111111111111111111111111111",
        commit_message="feat: initial auth verify",
        raw_diff=DIFF_ADD_RETURN_TYPE,
    )

    with patch.object(settings, "EVOKG_ENABLED", True):
        chunks = await IngestionService.ingest_commit_atom_changes(
            session=session,
            snapshot_id=snap_id,
            commit_artifact=commit,
            repository_id=repo_id,
        )

        assert len(chunks) >= 1

        # Check that relations were persisted
        triplet_res = await session.execute(
            select(EvoKGTriplet).where(EvoKGTriplet.repository_id == repo_id)
        )
        triplets = list(triplet_res.scalars().all())
        # Triplet should be persisted
        assert len(triplets) >= 1
        assert triplets[0].branch == "main"
        assert triplets[0].commit_sha == "c111111111111111111111111111111111111111"


@pytest.mark.asyncio
async def test_3_reingestion_is_idempotent_with_evokg(ingestion_db):
    """Verify re-ingesting the same commit with EVOKG_ENABLED=True causes no duplicate triplets."""
    session = ingestion_db["session"]
    snap_id = ingestion_db["snap_id"]
    repo_id = ingestion_db["repo_id"]

    commit = GitCommitArtifact(
        commit_sha="c111111111111111111111111111111111111111",
        commit_message="feat: initial auth verify",
        raw_diff=DIFF_ADD_RETURN_TYPE,
    )

    with patch.object(settings, "EVOKG_ENABLED", True):
        # Pass 1
        await IngestionService.ingest_commit_atom_changes(
            session=session,
            snapshot_id=snap_id,
            commit_artifact=commit,
            repository_id=repo_id,
        )
        res1 = await session.execute(
            select(EvoKGTriplet).where(EvoKGTriplet.repository_id == repo_id)
        )
        count1 = len(list(res1.scalars().all()))

        # Pass 2: identical commit re-ingested
        await IngestionService.ingest_commit_atom_changes(
            session=session,
            snapshot_id=snap_id,
            commit_artifact=commit,
            repository_id=repo_id,
        )
        res2 = await session.execute(
            select(EvoKGTriplet).where(EvoKGTriplet.repository_id == repo_id)
        )
        count2 = len(list(res2.scalars().all()))

        assert count1 == count2, "Duplicate triplets created on re-ingestion"


@pytest.mark.asyncio
async def test_4_incremental_change_supersedes_exclusive_relation(ingestion_db):
    """Verify incremental commit updating return type supersedes previous triplet."""
    session = ingestion_db["session"]
    snap_id = ingestion_db["snap_id"]
    repo_id = ingestion_db["repo_id"]
    service = EvoKGPersistenceService()

    # Commit 1 establishes return type bool
    r1 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="bool",
        commit_sha="c1",
        t_start=datetime(2026, 11, 1, 10, 0, tzinfo=UTC),
        confidence_score=0.95,
        fingerprint="fp_c1_bool",
    )
    with patch.object(settings, "EVOKG_ENABLED", True):
        await service.persist_relations(session, repo_id, [r1], snapshot_id=snap_id)

    # Verify r1 active
    active1 = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(active1) == 1
    assert active1[0].object_id == "bool"

    # Commit 2 changes return type to TokenPayload
    r2 = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.DEFINES_RETURN_TYPE,
        object="TokenPayload",
        commit_sha="c2",
        t_start=datetime(2026, 11, 1, 12, 0, tzinfo=UTC),
        confidence_score=0.95,
        fingerprint="fp_c2_payload",
    )
    with patch.object(settings, "EVOKG_ENABLED", True):
        await service.persist_relations(session, repo_id, [r2], snapshot_id=snap_id)

    # Verify r1 superseded and r2 active
    active2 = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(active2) == 1
    assert active2[0].object_id == "TokenPayload"
    assert active2[0].valid_to is None

    history = await service.get_temporal_history(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(history) == 2
    r1_triplet = next(h for h in history if h.object_id == "bool")
    assert r1_triplet.valid_to == datetime(2026, 11, 1, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_5_file_renames_preserve_entity_lineage(ingestion_db):
    """Verify file renames map old entity identifiers cleanly to new canonical path."""
    session = ingestion_db["session"]
    snap_id = ingestion_db["snap_id"]
    repo_id = ingestion_db["repo_id"]
    service = EvoKGPersistenceService()

    renames = {"apps/api/src/old_auth.py": "apps/api/src/auth.py"}

    rel = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/old_auth.py::verify_token",
        relation=RelationType.CALLS,
        object="apps/api/src/jwt.py::decode",
        fingerprint="fp_rename_call",
    )

    await service.persist_relations(
        session,
        repo_id,
        [rel],
        snapshot_id=snap_id,
        rename_history=renames,
    )

    # Querying using the new canonical identifier finds the active relationship
    active = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(active) == 1
    assert active[0].object_id == "apps/api/src/jwt.py::decode"


@pytest.mark.asyncio
async def test_6_partial_batch_does_not_cause_false_deletions(ingestion_db):
    """Verify that absent relationships from a partial commit are NOT terminated."""
    session = ingestion_db["session"]
    repo_id = ingestion_db["repo_id"]
    service = EvoKGPersistenceService()

    # Pre-existing active calls
    r_existing = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/auth.py::verify_token",
        relation=RelationType.CALLS,
        object="apps/api/src/logger.py::log_auth",
        fingerprint="fp_call_logger",
    )
    await service.persist_relations(session, repo_id, [r_existing])

    # A partial commit that only touches a completely different function
    r_unrelated = TemporalCodeRelation(
        id=str(uuid.uuid4()),
        subject="apps/api/src/report.py::render",
        relation=RelationType.CALLS,
        object="apps/api/src/pdf.py::export",
        fingerprint="fp_call_pdf",
    )
    await service.persist_relations(session, repo_id, [r_unrelated])

    # Original relationship must remain active and unaffected
    active_auth = await service.get_active_outgoing(
        session, repo_id, "apps/api/src/auth.py::verify_token"
    )
    assert len(active_auth) == 1
    assert active_auth[0].object_id == "apps/api/src/logger.py::log_auth"
    assert active_auth[0].valid_to is None
