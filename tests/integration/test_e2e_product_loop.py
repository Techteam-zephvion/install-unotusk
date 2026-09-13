import os
import tempfile
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import (
    FindingStatus,
    IntegrationProvider,
    IntegrationStatus,
    KnowledgeCategory,
    KnowledgeStatus,
    ReportStatus,
    SnapshotStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.knowledge import KnowledgeCreateRequest
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.discovery_engine.engine import ProjectDiscoveryEngine
from apps.api.src.services.ingestion_service import IngestionService
from apps.api.src.services.intelligence_service import IntelligenceService
from apps.api.src.services.knowledge_service import KnowledgeService
from apps.api.src.services.report_engine.engine import ProjectReportEngine


@pytest.mark.asyncio
async def test_complete_e2e_product_loop(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """
    Validates the end-to-end Unotusk product loop:
    1. Connect Project & Ingest Repo
    2. Discover Structural Findings
    3. Grounded Question Asking
    4. Generate Flagship Report v1
    5. Add Customer Knowledge
    6. Grounded Ask incorporates Knowledge
    7. Generate Flagship Report v2 reflecting Knowledge
    8. Archive Knowledge and verify degradation
    """
    # ---------------------------------------------------------
    # 1. Connect Project & Ingest Codebase
    # ---------------------------------------------------------
    user = await create_test_user(email="cto-demo@unotusk.io")
    org, _ = await create_test_org(user=user, name="Acme Corp")
    project = await create_test_project(organization=org, name="Core Billing Platform")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-acme-billing",
        integration_metadata={},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-acme-billing",
        owner="acme",
        name="billing-service",
        full_name="acme/billing-service",
        default_branch="main",
        url="https://github.com/acme/billing-service",
        is_private=True,
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

    with tempfile.TemporaryDirectory() as tmp_dir:
        src_dir = os.path.join(tmp_dir, "src")
        os.makedirs(src_dir, exist_ok=True)

        # Payment processor with high coupling
        with open(os.path.join(src_dir, "payment_gateway.py"), "w") as f:
            f.write(
                'class PaymentGateway:\n'
                '    """Main entrypoint for Stripe and PayPal integrations."""\n'
                '    def process_charge(self, customer_id: str, amount_cents: int):\n'
                '        return {"status": "success", "charge_id": "ch_123"}\n'
            )

        # 4 dependent modules calling PaymentGateway
        for idx in range(1, 5):
            with open(os.path.join(src_dir, f"invoice_module_{idx}.py"), "w") as f:
                f.write(
                    'from src.payment_gateway import PaymentGateway\n\n'
                    f'class InvoiceModule{idx}:\n'
                    '    def bill(self, user_id, amount):\n'
                    '        gw = PaymentGateway()\n'
                    '        return gw.process_charge(user_id, amount)\n'
                )

        snapshot_id = snapshot.id
        await IngestionService.run_ingestion(snapshot_id, override_local_dir=tmp_dir)

    await db_session.refresh(snapshot)
    assert snapshot.status == SnapshotStatus.COMPLETED
    assert snapshot.total_files >= 5

    # ---------------------------------------------------------
    # 2. Discover Problems / Risks
    # ---------------------------------------------------------
    discovery_run_id = uuid.uuid4()
    findings = await ProjectDiscoveryEngine.run_discovery(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        session=db_session,
    )

    assert len(findings) > 0
    high_coupling_finding = next((f for f in findings if "PaymentGateway" in f.title or "payment_gateway" in str(f.evidence)), None)
    assert high_coupling_finding is not None
    assert high_coupling_finding.status == FindingStatus.OPEN

    # ---------------------------------------------------------
    # 3. Grounded Ask (Baseline before Customer Knowledge)
    # ---------------------------------------------------------
    context_engine = ProjectContextEngine()
    ans_baseline = await context_engine.investigate(
        session=db_session,
        question="Where is payment processing handled and what are its constraints?",
        snapshot_id=snapshot.id,
        project_id=project.id,
    )
    assert ans_baseline.debug_signals.get("customer_knowledge_count", 0) == 0
    assert "PaymentGateway" in ans_baseline.content or "payment_gateway" in ans_baseline.content

    ask_response_baseline = await IntelligenceService.ask_question(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        question="Where is payment processing handled?",
    )
    assert ask_response_baseline.content is not None
    assert "PaymentGateway" in ask_response_baseline.content or "payment" in ask_response_baseline.content.lower()

    # ---------------------------------------------------------
    # 4. Generate Intelligence Report v1 (Baseline)
    # ---------------------------------------------------------
    report_v1 = ProjectIntelligenceReport(
        id=uuid.uuid4(),
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        status=ReportStatus.GENERATING,
        report_version="1.0.0",
        summary="",
        report_data={},
    )
    db_session.add(report_v1)
    await db_session.commit()

    completed_report_v1 = await ProjectReportEngine.generate_report(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        report_id=report_v1.id,
        session=db_session,
    )
    assert completed_report_v1.status == ReportStatus.COMPLETED
    assert completed_report_v1.report_data is not None
    assert completed_report_v1.report_data.get("project_knowledge", []) == []

    # ---------------------------------------------------------
    # 5. Customer Corrects / Adds Knowledge
    # ---------------------------------------------------------
    knowledge_resp = await KnowledgeService.create_knowledge(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        data=KnowledgeCreateRequest(
            category=KnowledgeCategory.ARCHITECTURE_DECISION,
            title="Stripe PCI Compliance Isolation",
            content="All payment charges must route strictly through PaymentGateway because it is wrapped in PCI tokenization vault proxy.",
            related_symbol="PaymentGateway",
            related_file_path="src/payment_gateway.py",
            related_finding_id=high_coupling_finding.id,
        ),
    )
    assert knowledge_resp.id is not None
    assert knowledge_resp.status == KnowledgeStatus.ACTIVE

    # ---------------------------------------------------------
    # 6. Unotusk Remembers: Grounded Ask Prioritizes Knowledge
    # ---------------------------------------------------------
    ans_enhanced = await context_engine.investigate(
        session=db_session,
        question="Where is payment processing handled and what are its constraints?",
        snapshot_id=snapshot.id,
        project_id=project.id,
    )
    assert ans_enhanced.debug_signals.get("customer_knowledge_count", 0) >= 1
    assert "PCI" in ans_enhanced.content or "tokenization" in ans_enhanced.content

    ask_response_enhanced = await IntelligenceService.ask_question(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        question="Where is payment processing handled and what are its constraints?",
    )
    assert ask_response_enhanced.content is not None
    assert "PCI" in ask_response_enhanced.content or "tokenization" in ask_response_enhanced.content

    # ---------------------------------------------------------
    # 7. Future Intelligence Improves: Report v2 Synthesizes Knowledge
    # ---------------------------------------------------------
    report_v2 = ProjectIntelligenceReport(
        id=uuid.uuid4(),
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        status=ReportStatus.GENERATING,
        report_version="1.1.0",
        summary="",
        report_data={},
    )
    db_session.add(report_v2)
    await db_session.commit()

    completed_report_v2 = await ProjectReportEngine.generate_report(
        project_id=project.id,
        snapshot_id=snapshot.id,
        discovery_run_id=discovery_run_id,
        report_id=report_v2.id,
        session=db_session,
    )
    assert completed_report_v2.status == ReportStatus.COMPLETED
    report_2_knowledge = completed_report_v2.report_data.get("project_knowledge", [])
    assert len(report_2_knowledge) >= 1
    assert report_2_knowledge[0]["title"] == "Stripe PCI Compliance Isolation"

    # ---------------------------------------------------------
    # 8. Archive Knowledge & Lifecycle Management
    # ---------------------------------------------------------
    archived_k = await KnowledgeService.archive_knowledge(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        knowledge_id=knowledge_resp.id,
    )
    assert archived_k.status == KnowledgeStatus.ARCHIVED

    ans_after_archive = await context_engine.investigate(
        session=db_session,
        question="Where is payment processing handled and what are its constraints?",
        snapshot_id=snapshot.id,
        project_id=project.id,
    )
    assert ans_after_archive.debug_signals.get("customer_knowledge_count", 0) == 0
