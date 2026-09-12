import os
import tempfile
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    ReportStatus,
    SnapshotStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.discovery_engine.engine import ProjectDiscoveryEngine
from apps.api.src.services.ingestion_service import IngestionService
from apps.api.src.services.report_engine.engine import ProjectReportEngine


@pytest.mark.asyncio
async def test_golden_project_intelligence_report(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    # 1. Setup project hierarchy
    user = await create_test_user(email="golden-report@unotusk.io")
    org, _ = await create_test_org(user=user, name="Golden Org")
    project = await create_test_project(organization=org, name="Golden Project")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-golden-123",
        integration_metadata={},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-golden-456",
        owner="golden-owner",
        name="golden-repo",
        full_name="golden-owner/golden-repo",
        default_branch="main",
        url="https://github.com/golden-owner/golden-repo",
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

    # 2. Ingest codebase with known deterministic signals
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src", "auth"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "payment"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "modules"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, "src", "legacy"), exist_ok=True)

        # Coupling hotspot: AuthService
        with open(os.path.join(tmpdir, "src", "auth", "service.py"), "w") as f:
            f.write("class AuthService:\n    def authenticate(self, token):\n        return True\n")

        for i in range(6):
            with open(os.path.join(tmpdir, "src", f"consumer_{i}.py"), "w") as f:
                f.write(f"from src.auth.service import AuthService\n\nclass Worker{i}:\n    pass\n")

        # Circular dependency cycle: mod_a -> mod_b -> mod_c -> mod_a
        with open(os.path.join(tmpdir, "src", "modules", "mod_a.py"), "w") as f:
            f.write("from src.modules.mod_b import B\nclass A:\n    pass\n")

        with open(os.path.join(tmpdir, "src", "modules", "mod_b.py"), "w") as f:
            f.write("from src.modules.mod_c import C\nclass B:\n    pass\n")

        with open(os.path.join(tmpdir, "src", "modules", "mod_c.py"), "w") as f:
            f.write("from src.modules.mod_a import A\nclass C:\n    pass\n")

        # Test gap: payment processor without test file
        with open(os.path.join(tmpdir, "src", "payment", "processor.py"), "w") as f:
            f.write("class PaymentProcessor:\n    def charge(self, amount):\n        return True\n")

        # Legacy signal
        with open(os.path.join(tmpdir, "src", "legacy", "old_routine.py"), "w") as f:
            f.write("# TODO: deprecated legacy implementation\ndef legacy_run():\n    pass\n")

        # Run Stage 1 Ingestion
        await IngestionService.run_ingestion(snapshot.id, override_local_dir=tmpdir)

    # Run Stage 3 Discovery Engine
    discovery_run_id = uuid.uuid4()
    await ProjectDiscoveryEngine.run_discovery(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        session=db_session,
    )

    # 3. Generate Stage 4 Project Intelligence Report
    report = ProjectIntelligenceReport(
        id=uuid.uuid4(),
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        status=ReportStatus.GENERATING,
        report_version="1.0.0",
        summary="Generating golden project report",
        report_data={},
    )
    db_session.add(report)
    await db_session.commit()

    # Execute Report Engine
    await ProjectReportEngine.generate_report(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        report_id=report.id,
        session=db_session,
    )

    # 4. Verify Generated Report in Database
    res = await db_session.execute(
        select(ProjectIntelligenceReport).where(ProjectIntelligenceReport.id == report.id)
    )
    saved_report = res.scalar_one()

    assert saved_report.status == ReportStatus.COMPLETED
    assert saved_report.generated_at is not None
    assert saved_report.report_data is not None

    data = saved_report.report_data

    # Assert deterministic vital metrics
    vital = data["executive_summary"]["vital_metrics"]
    assert vital["total_files"] >= 10
    assert vital["total_symbols"] >= 8
    assert vital["total_discoveries"] >= 2

    # Assert known coupling hotspot: AuthService
    top_things = data["executive_summary"]["top_things_to_know"]
    assert len(top_things) > 0

    all_statements = [t["statement"] for t in top_things]
    all_findings_titles = [d["title"] for d in data["discoveries"]]

    # Check for coupling and circular dependency findings
    has_coupling = any("AuthService" in s or "coupling" in s.lower() for s in all_statements + all_findings_titles)
    has_cycle = any("cycle" in s.lower() or "circular" in s.lower() for s in all_statements + all_findings_titles)

    assert has_coupling, "Expected AuthService or high coupling to be captured in report"
    assert has_cycle, "Expected circular dependency to be captured in report"

    # Assert risk areas and debt
    assert len(data["risk_areas"]) > 0
    assert len(data["next_actions"]) > 0

    # Assert every next action has recommended knowledge class
    for act in data["next_actions"]:
        assert act["claim_type"] == "RECOMMENDED"

    # Assert all referenced files actually exist in the fixture (no hallucinations)
    known_files = {
        "src/auth/service.py",
        "src/payment/processor.py",
        "src/modules/mod_a.py",
        "src/modules/mod_b.py",
        "src/modules/mod_c.py",
        "src/legacy/old_routine.py",
    }
    for i in range(6):
        known_files.add(f"src/consumer_{i}.py")

    for disc in data["discoveries"]:
        for ev in disc.get("evidence", []):
            file_ref = ev.get("file") or ev.get("file_path") or ev.get("target")
            if file_ref and not file_ref.startswith("http") and not file_ref.startswith("pkg:"):
                # Clean any prefix if needed
                normalized = file_ref.lstrip("/")
                assert normalized in known_files or any(k in normalized for k in known_files), (
                    f"Fabricated file detected: {file_ref}"
                )
