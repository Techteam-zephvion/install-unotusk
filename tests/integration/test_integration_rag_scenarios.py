import os
import tempfile
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    KnowledgeCategory,
    KnowledgeStatus,
    SnapshotStatus,
)
from apps.api.src.models.integration import Integration
from apps.api.src.models.knowledge import ProjectKnowledge
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.ingestion_service import IngestionService
from apps.api.src.services.repository_service import RepositoryService


@pytest.mark.asyncio
async def test_all_integration_rag_scenarios(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    # -------------------------------------------------------------------------
    # Setup Tenant A & Project A
    # -------------------------------------------------------------------------
    user_a = await create_test_user(email="scenario-tester-a@unotusk.io")
    org_a, _ = await create_test_org(user=user_a, name="Scenario Org A")
    project_a = await create_test_project(organization=org_a, name="Scenario Project A")

    # Setup Tenant B & Project B for isolation verification (Scenario G)
    user_b = await create_test_user(email="scenario-tester-b@unotusk.io")
    org_b, _ = await create_test_org(user=user_b, name="Scenario Org B")
    project_b = await create_test_project(organization=org_b, name="Scenario Project B")

    integration_a = Integration(
        id=uuid.uuid4(),
        project_id=project_a.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-scenario-a",
        integration_metadata={"username": "scenario-org-a"},
    )
    db_session.add(integration_a)

    repo_a = Repository(
        id=uuid.uuid4(),
        project_id=project_a.id,
        integration_id=integration_a.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-scenario-a",
        owner="scenario-org",
        name="payment-service",
        full_name="scenario-org/payment-service",
        default_branch="main",
        url="https://github.com/scenario-org/payment-service",
        is_private=False,
    )
    db_session.add(repo_a)

    snap_a = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo_a.id,
        branch="main",
        status=SnapshotStatus.QUEUED,
    )
    db_session.add(snap_a)
    await db_session.commit()

    # Ingest Code for Project A
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src", "payment.py"), "w") as f:
            f.write(
                "class StripeProcessor:\n"
                "    def charge(self, amount, currency):\n"
                '        return {"status": "success", "tx_id": "tx_123"}\n'
            )
        await IngestionService.run_ingestion(snap_a.id, override_local_dir=tmpdir)

    await db_session.refresh(snap_a)
    assert snap_a.status == SnapshotStatus.COMPLETED

    # Synchronize Integration Records (GitHub Issues and PRs) into Project A
    mock_issues = [
        {
            "id": "1001",
            "number": 101,
            "title": "Enforce Idempotency-Key header on all charge requests",
            "body": "Issue #101: To prevent double charging, all calls to StripeProcessor.charge must provide an Idempotency-Key header. Keys expire after 24 hours.",
            "is_pull_request": False,
            "html_url": "https://github.com/scenario-org/payment-service/issues/101",
            "labels": ["payments", "reliability", "specification"],
            "author": "payment-lead",
        },
        {
            "id": "1002",
            "number": 105,
            "title": "Add multi-currency conversion for EUR and GBP",
            "body": "PR #105: Proposes multi-currency conversion support when processing non-USD charges in StripeProcessor.",
            "is_pull_request": True,
            "html_url": "https://github.com/scenario-org/payment-service/pull/105",
            "labels": ["feature", "currency"],
            "author": "fintech-dev",
        },
    ]

    synced = await RepositoryService.sync_github_issues(
        session=db_session,
        user_id=user_a.id,
        project_id=project_a.id,
        repository_id=repo_a.id,
        issues_data=mock_issues,
    )
    assert len(synced) == 2
    assert any(s["number"] == 101 for s in synced)
    assert any(s["number"] == 105 for s in synced)

    # Add a customer domain note into Project A
    cust_note = ProjectKnowledge(
        id=uuid.uuid4(),
        project_id=project_a.id,
        created_by=user_a.id,
        category=KnowledgeCategory.CONSTRAINT,
        title="Production settlement currency constraint",
        content="Customer Constraint: Live settlement accounts are strictly USD denominated until Q4 migration.",
        status=KnowledgeStatus.ACTIVE,
        source_type="CUSTOMER",
    )
    db_session.add(cust_note)
    await db_session.commit()

    engine = ProjectContextEngine()

    # -------------------------------------------------------------------------
    # Scenario A: Code-only question
    # -------------------------------------------------------------------------
    ans_a = await engine.investigate(
        session=db_session,
        question="How does StripeProcessor.charge work?",
        snapshot_id=snap_a.id,
        project_id=project_a.id,
    )
    assert "StripeProcessor" in ans_a.content
    code_evidence = [e for e in ans_a.evidence if "payment.py" in str(e.get("file", "")) or e.get("symbol") == "charge"]
    assert len(code_evidence) >= 1

    # -------------------------------------------------------------------------
    # Scenario B: Integration-only question
    # -------------------------------------------------------------------------
    ans_b = await engine.investigate(
        session=db_session,
        question="What header is required by Issue #101 to prevent double charging?",
        snapshot_id=snap_a.id,
        project_id=project_a.id,
    )
    assert "Idempotency-Key" in ans_b.content or "idempotency" in ans_b.content.lower()
    int_evidence_b = [
        e for e in ans_b.evidence
        if e.get("source_reference_id") == "#101" or e.get("source_type") == "GITHUB"
    ]
    assert len(int_evidence_b) >= 1
    assert int_evidence_b[0].get("source_type") == "GITHUB"
    assert int_evidence_b[0].get("source_reference_id") == "#101"

    # -------------------------------------------------------------------------
    # Scenario C: Combined question (Implementation Code + Integration Spec)
    # -------------------------------------------------------------------------
    ans_c = await engine.investigate(
        session=db_session,
        question="Compare the StripeProcessor.charge implementation with the requirement in issue #101.",
        snapshot_id=snap_a.id,
        project_id=project_a.id,
    )
    # Both code evidence and integration evidence must be present in the evidence list!
    c_code = [e for e in ans_c.evidence if "payment.py" in str(e.get("file", "")) or e.get("symbol") in ("StripeProcessor", "charge")]
    c_int = [e for e in ans_c.evidence if e.get("source_reference_id") == "#101" or e.get("source_type") == "GITHUB"]
    assert len(c_code) >= 1, f"Expected code evidence in Scenario C, got: {ans_c.evidence}"
    assert len(c_int) >= 1, f"Expected integration evidence in Scenario C, got: {ans_c.evidence}"
    assert "Idempotency" in ans_c.content or "idempotency" in ans_c.content.lower()

    # -------------------------------------------------------------------------
    # Scenario D: Conflicting / Layered Information (Customer Constraint vs PR #105)
    # -------------------------------------------------------------------------
    ans_d = await engine.investigate(
        session=db_session,
        question="What currencies are supported according to PR #105 and project constraints?",
        snapshot_id=snap_a.id,
        project_id=project_a.id,
    )
    assert "EUR" in ans_d.content or "GBP" in ans_d.content or "USD" in ans_d.content
    # Origin preservation in evidence
    d_origins = {e.get("source_type") for e in ans_d.evidence if e.get("source_type")}
    assert "GITHUB" in d_origins or any(e.get("source_reference_id") == "#105" for e in ans_d.evidence)

    # -------------------------------------------------------------------------
    # Scenario E: Missing integration evidence (Honest uncertainty)
    # -------------------------------------------------------------------------
    ans_e = await engine.investigate(
        session=db_session,
        question="What does Issue #999 say about cryptocurrency refunds for dogecoin?",
        snapshot_id=snap_a.id,
        project_id=project_a.id,
    )
    # Must express lack of evidence / uncertainty rather than fabricating issue #999
    assert (
        "Insufficient Evidence" in ans_e.content
        or "no matching" in ans_e.content.lower()
        or "not find" in ans_e.content.lower()
        or ans_e.confidence == "LOW"
    )
    assert not any(e.get("source_reference_id") == "#999" for e in ans_e.evidence)

    # -------------------------------------------------------------------------
    # Scenario F: Integration update propagation
    # -------------------------------------------------------------------------
    updated_mock_issues = [
        {
            "id": "1001",
            "number": 101,
            "title": "Enforce Idempotency-Key header with 15-minute strict TTL",
            "body": "Issue #101 UPDATE: The idempotency window is reduced to 15 minutes (900 seconds) for fraud mitigation.",
            "is_pull_request": False,
            "html_url": "https://github.com/scenario-org/payment-service/issues/101",
            "labels": ["payments", "updated"],
            "author": "payment-lead",
        }
    ]
    update_res = await RepositoryService.sync_github_issues(
        session=db_session,
        user_id=user_a.id,
        project_id=project_a.id,
        repository_id=repo_a.id,
        issues_data=updated_mock_issues,
    )
    assert len(update_res) == 1
    assert update_res[0]["status"] == "updated"

    ans_f = await engine.investigate(
        session=db_session,
        question="What is the updated TTL for Idempotency-Key in issue #101?",
        snapshot_id=snap_a.id,
        project_id=project_a.id,
    )
    assert "15-minute" in ans_f.content or "15 minutes" in ans_f.content or "900 seconds" in ans_f.content

    # -------------------------------------------------------------------------
    # Scenario G: Multi-source & Tenant Isolation
    # -------------------------------------------------------------------------
    # Project B (different organization) queries for Issue #101
    # Must NOT find Project A's issue or code!
    # Query project B for project A's data
    ans_g = await engine.investigate(
        session=db_session,
        question="What does Issue #101 say?",
        snapshot_id=snap_a.id,
        project_id=project_b.id,  # Project B
    )
    # Project B must NOT retrieve Project A's knowledge or issue
    assert not any(e.get("source_reference_id") == "#101" for e in ans_g.evidence)
    assert "double charging" not in ans_g.content.lower()
