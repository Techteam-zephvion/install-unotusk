import os
import tempfile
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.discovery_run import DiscoveryRun
from apps.api.src.models.enums import (
    DiscoveryJobStatus,
    FindingCategory,
    FindingStatus,
    IntegrationProvider,
    IntegrationStatus,
    SnapshotStatus,
)
from apps.api.src.models.finding import Finding
from apps.api.src.models.integration import Integration
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.discovery_engine.engine import ProjectDiscoveryEngine
from apps.api.src.services.ingestion_service import IngestionService


@pytest.mark.asyncio
async def test_end_to_end_discovery_engine(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    # 1. Setup project hierarchy
    user = await create_test_user(email="discover-tester@unotusk.io")
    org, _ = await create_test_org(user=user, name="Discovery Org")
    project = await create_test_project(organization=org, name="Discovery Project")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-disc-123",
        integration_metadata={},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-disc-456",
        owner="disc-owner",
        name="disc-repo",
        full_name="disc-owner/disc-repo",
        default_branch="main",
        url="https://github.com/disc-owner/disc-repo",
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

    # 2. Ingest codebase with designed architecture signals
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)

        # Circular loop: mod_a <-> mod_b
        with open(os.path.join(tmpdir, "src", "mod_a.py"), "w") as f:
            f.write("from .mod_b import ServiceB\n\nclass ServiceA:\n    pass\n")

        with open(os.path.join(tmpdir, "src", "mod_b.py"), "w") as f:
            f.write("from .mod_a import ServiceA\n\nclass ServiceB:\n    pass\n")

        # Central core bus with 6 consumers
        with open(os.path.join(tmpdir, "src", "bus.py"), "w") as f:
            f.write("class MessageBus:\n    def publish(self, topic, msg):\n        pass\n")

        for i in range(6):
            with open(os.path.join(tmpdir, "src", f"consumer_{i}.py"), "w") as f:
                f.write(f"from .bus import MessageBus\n\nclass Worker{i}:\n    pass\n")

        # Isolated helper with no consumers
        with open(os.path.join(tmpdir, "src", "orphan.py"), "w") as f:
            f.write("class OrphanCalculator:\n    def compute_secret(self):\n        return 42\n")

        # Core file with no test suite
        with open(os.path.join(tmpdir, "src", "payment.py"), "w") as f:
            f.write("class PaymentGateway:\n    def charge(self, amount):\n        return True\n")

        await IngestionService.run_ingestion(snapshot.id, override_local_dir=tmpdir)

    # 3. Run Discovery Engine
    findings = await ProjectDiscoveryEngine.run_discovery(
        project_id=project.id,
        snapshot_id=snapshot.id,
        session=db_session,
    )

    assert len(findings) >= 3

    categories = {f.category for f in findings}
    assert FindingCategory.CIRCULAR_DEPENDENCY in categories
    assert FindingCategory.COUPLING in categories or FindingCategory.CHANGE_RISK in categories
    assert FindingCategory.TEST_GAP in categories

    # 4. Verify Database Persistence & DiscoveryRun
    runs_q = select(DiscoveryRun).where(DiscoveryRun.project_id == project.id)
    runs_res = await db_session.execute(runs_q)
    run = runs_res.scalar_one()

    assert run.status == DiscoveryJobStatus.COMPLETED
    assert run.progress == 100
    assert run.findings_count == len(findings)

    # Check evidence format
    db_findings_q = select(Finding).where(Finding.project_id == project.id)
    db_findings_res = await db_session.execute(db_findings_q)
    db_findings = db_findings_res.scalars().all()

    for f in db_findings:
        assert f.status == FindingStatus.OPEN
        assert f.score > 0
        assert len(f.evidence) >= 1
        assert len(f.recommendation) > 10
        assert len(f.why_it_matters) > 10
