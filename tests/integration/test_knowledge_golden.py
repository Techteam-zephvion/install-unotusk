import os
import tempfile
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    KnowledgeCategory,
    KnowledgeClass,
    KnowledgeStatus,
    ReportStatus,
    SnapshotStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.knowledge import ProjectKnowledge
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.discovery_engine.engine import ProjectDiscoveryEngine
from apps.api.src.services.ingestion_service import IngestionService
from apps.api.src.services.intelligence_service import IntelligenceService
from apps.api.src.services.report_engine.engine import ProjectReportEngine


@pytest.mark.asyncio
async def test_golden_persistent_project_knowledge(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    # 1. Setup project hierarchy
    user = await create_test_user(email="golden-knowledge@unotusk.io")
    org, _ = await create_test_org(user=user, name="Knowledge Golden Org")
    project = await create_test_project(organization=org, name="Knowledge Golden Project")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-knowledge-golden",
        integration_metadata={},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-knowledge-golden",
        owner="golden-owner",
        name="golden-knowledge-repo",
        full_name="golden-owner/golden-knowledge-repo",
        default_branch="main",
        url="https://github.com/golden-owner/golden-knowledge-repo",
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

    # 2. Ingest a fixture codebase with AuthService and Legacy API
    with tempfile.TemporaryDirectory() as tmp_dir:
        src_dir = os.path.join(tmp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)

        # Central AuthService
        with open(os.path.join(src_dir, "auth_service.py"), "w") as f:
            f.write(
                'class AuthService:\n'
                '    def __init__(self):\n'
                '        self.tokens = {}\n'
                '    def authenticate(self, user, token):\n'
                '        return True\n'
                '    def issue_token(self, user_id):\n'
                '        return "jwt-token"\n'
            )

        # Multiple consumers of AuthService creating structural coupling
        for i in range(1, 6):
            with open(os.path.join(src_dir, f"consumer_{i}.py"), "w") as f:
                f.write(
                    f'from src.auth_service import AuthService\n\n'
                    f'class Consumer{i}:\n'
                    f'    def run(self):\n'
                    f'        auth = AuthService()\n'
                    f'        return auth.issue_token("{i}")\n'
                )

        # Legacy API
        with open(os.path.join(src_dir, "legacy_api.py"), "w") as f:
            f.write(
                '# DEPRECATED legacy API for backward compatibility\n'
                '# legacy endpoint\n'
                'class LegacyAPI:\n'
                '    def handle_old_request(self):\n'
                '        return "legacy payload"\n'
            )

        snapshot_id = snapshot.id
        await IngestionService.run_ingestion(snapshot_id, override_local_dir=tmp_dir)

    await db_session.refresh(snapshot)
    assert snapshot.status == SnapshotStatus.COMPLETED

    # Run initial discovery
    discovery_run_id = uuid.uuid4()
    await ProjectDiscoveryEngine.run_discovery(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        session=db_session,
    )

    # 3. Generate initial Project Intelligence Report (Report v1 - Historical baseline)
    report_v1 = ProjectIntelligenceReport(
        id=uuid.uuid4(),
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        status=ReportStatus.GENERATING,
        report_version="1.0.0",
        summary="Generating golden project report v1",
        report_data={},
    )
    db_session.add(report_v1)
    await db_session.commit()

    await ProjectReportEngine.generate_report(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        report_id=report_v1.id,
        session=db_session,
    )

    await db_session.refresh(report_v1)
    assert report_v1.status == ReportStatus.COMPLETED
    assert report_v1.report_version == "1.0.0"
    # Initially no project knowledge was added
    assert len(report_v1.report_data.get("project_knowledge", [])) == 0

    # 4. Customer adds persistent project knowledge
    # Teaching Unotusk:
    # 1. AuthService coupling is an intentional architectural decision
    # 2. LegacyAPI is retained for external enterprise customers
    knowledge_auth = ProjectKnowledge(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=user.id,
        category=KnowledgeCategory.ARCHITECTURE_DECISION,
        title="AuthService boundary is intentional",
        content="AuthService intentionally owns authentication and session state. It should remain centralized despite high coupling.",
        related_file_path="src/auth_service.py",
        related_symbol="AuthService",
        status=KnowledgeStatus.ACTIVE,
    )
    db_session.add(knowledge_auth)

    knowledge_legacy = ProjectKnowledge(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=user.id,
        category=KnowledgeCategory.LEGACY_CONTEXT,
        title="LegacyAPI required by enterprise partners",
        content="LegacyAPI appears legacy but is still actively required by external enterprise clients.",
        related_file_path="src/legacy_api.py",
        related_symbol="LegacyAPI",
        status=KnowledgeStatus.ACTIVE,
    )
    db_session.add(knowledge_legacy)
    await db_session.commit()

    # 5. Test Stage 2 Grounded Ask with Persistent Knowledge
    context_engine = ProjectContextEngine()
    answer_pack = await context_engine.investigate(
        session=db_session,
        question="Why is AuthService highly coupled?",
        snapshot_id=snapshot.id,
        project_id=project.id,
    )

    # Customer knowledge must be included in retrieved context and synthesis
    assert answer_pack.debug_signals["customer_knowledge_count"] >= 1
    assert "AuthService boundary is intentional" in answer_pack.content

    ask_response = await IntelligenceService.ask_question(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        question="Why is AuthService highly coupled?",
    )

    # Epistemic assertions:
    # - Observed facts remain intact (the coupling exists)
    # - Customer knowledge is recognized and transparently attributed
    # - It does NOT hallucinate that AuthService has no coupling
    answer_text = ask_response.content
    assert "AuthService" in answer_text
    assert "Customer Project Knowledge" in answer_text or "CUSTOMER" in answer_text
    assert "intentional" in answer_text.lower()

    # 6. Verify historical Report v1 remains UNCHANGED
    await db_session.refresh(report_v1)
    assert len(report_v1.report_data.get("project_knowledge", [])) == 0

    # 7. Regenerate Report (Report v2)
    report_v2 = ProjectIntelligenceReport(
        id=uuid.uuid4(),
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        status=ReportStatus.GENERATING,
        report_version="1.1.0",
        summary="Generating golden project report v2",
        report_data={},
    )
    db_session.add(report_v2)
    await db_session.commit()

    await ProjectReportEngine.generate_report(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        report_id=report_v2.id,
        session=db_session,
    )

    await db_session.refresh(report_v2)
    assert report_v2.status == ReportStatus.COMPLETED
    assert report_v2.id != report_v1.id
    assert report_v2.report_version == "1.1.0"

    # Report v2 must incorporate the project knowledge
    v2_knowledge = report_v2.report_data.get("project_knowledge", [])
    assert len(v2_knowledge) == 2
    v2_knowledge_titles = [k["title"] for k in v2_knowledge]
    assert "AuthService boundary is intentional" in v2_knowledge_titles
    assert "LegacyAPI required by enterprise partners" in v2_knowledge_titles

    # Verify epistemic integrity in Report v2
    claims = report_v2.report_data["executive_summary"]["top_things_to_know"]
    claim_types = [c["claim_type"] for c in claims]
    assert KnowledgeClass.OBSERVED.value in claim_types or "OBSERVED" in claim_types
    assert KnowledgeClass.CUSTOMER.value in claim_types or "CUSTOMER" in claim_types

    # 8. Test Archiving Knowledge excludes it from active context
    knowledge_auth.status = KnowledgeStatus.ARCHIVED
    await db_session.commit()

    archived_answer = await context_engine.investigate(
        session=db_session,
        question="Why is AuthService highly coupled?",
        snapshot_id=snapshot.id,
        project_id=project.id,
    )
    assert "AuthService boundary is intentional" not in archived_answer.content
