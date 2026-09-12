import os
import tempfile
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    ProjectStatus,
    SnapshotStatus,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.ingestion_service import IngestionService


@pytest.mark.asyncio
async def test_end_to_end_repository_ingestion(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    # 1. Setup Project hierarchy
    user = await create_test_user(email="ingest-tester@unotusk.io")
    org, _ = await create_test_org(user=user, name="Ingest Org")
    project = await create_test_project(organization=org, name="Sample Ingest Repo")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-test-123",
        metadata={},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="123456",
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        default_branch="main",
        url="https://github.com/test-owner/test-repo",
        is_private=False,
    )
    db_session.add(repository)

    snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repository.id,
        branch="main",
        status=SnapshotStatus.QUEUED,
    )
    db_session.add(snapshot)
    await db_session.commit()

    # 2. Create sample repository files in tempdir
    with tempfile.TemporaryDirectory() as tmpdir:
        # Python file
        py_file = os.path.join(tmpdir, "main.py")
        with open(py_file, "w") as f:
            f.write(
                "import os\nfrom .utils import helper\n\nclass CoreEngine:\n    def compute(self, x):\n        return x * 2\n"
            )

        # TypeScript file
        ts_file = os.path.join(tmpdir, "service.ts")
        with open(ts_file, "w") as f:
            f.write(
                "import React from 'react';\n\nexport interface Config {\n    timeout: number;\n}\n\nexport function setup(): boolean {\n    return true;\n}\n"
            )

        # Markdown file (parser unsupported)
        md_file = os.path.join(tmpdir, "README.md")
        with open(md_file, "w") as f:
            f.write("# Sample Readme\nThis is sample documentation.\n")

        # Excluded directory
        ignored_dir = os.path.join(tmpdir, "node_modules", "pkg")
        os.makedirs(ignored_dir, exist_ok=True)
        with open(os.path.join(ignored_dir, "index.js"), "w") as f:
            f.write("// Should be ignored")

        # 3. Run Ingestion Pipeline
        await IngestionService.run_ingestion(snapshot.id, override_local_dir=tmpdir)

    # 4. Verify Database State using a clean session
    from apps.api.src.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        snap_check = await session.execute(
            select(RepositorySnapshot).where(RepositorySnapshot.id == snapshot.id)
        )
        completed_snap = snap_check.scalar_one()
        assert completed_snap.status == SnapshotStatus.COMPLETED
        assert completed_snap.total_files == 3  # main.py, service.ts, README.md (node_modules excluded)
        assert completed_snap.processed_files == 3
        assert completed_snap.error_message is None

        # Check files
        files_res = await session.execute(
            select(RepositoryFile).where(RepositoryFile.snapshot_id == snapshot.id)
        )
        files = files_res.scalars().all()
        assert len(files) == 3

        paths = [f.path for f in files]
        assert "main.py" in paths
        assert "service.ts" in paths
        assert "README.md" in paths
        assert not any("node_modules" in p for p in paths)

        # Check symbols
        symbols_res = await session.execute(
            select(CodeSymbol)
            .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
            .where(RepositoryFile.snapshot_id == snapshot.id)
        )
        symbols = symbols_res.scalars().all()
        sym_names = [s.name for s in symbols]
        assert "CoreEngine" in sym_names
        assert "compute" in sym_names
        assert "Config" in sym_names
        assert "setup" in sym_names

        # Check dependencies
        deps_res = await session.execute(
            select(CodeDependency)
            .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
            .where(RepositoryFile.snapshot_id == snapshot.id)
        )
        deps = deps_res.scalars().all()
        dep_targets = [d.external_package for d in deps if d.external_package]
        assert "os" in dep_targets
        assert "react" in dep_targets

        # Check code chunks created
        from apps.api.src.models.chunk import CodeChunk
        chunks_res = await session.execute(
            select(CodeChunk).where(CodeChunk.snapshot_id == snapshot.id)
        )
        chunks = chunks_res.scalars().all()
        assert len(chunks) >= 4  # CoreEngine, compute, Config, setup, README
        chunk_names = [c.name for c in chunks]
        assert "CoreEngine" in chunk_names
        assert "README.md" in chunk_names

        # Check Project status transitioned to READY
        p_check = await session.execute(select(Project).where(Project.id == project.id))
        ready_proj = p_check.scalar_one()
        assert ready_proj.status == ProjectStatus.READY
