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
from apps.api.src.services.intelligence_service import IntelligenceService


@pytest.mark.asyncio
async def test_integration_to_rag_retrieval_and_citation(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """
    Test that an external integration record (e.g. a synchronized GitHub Issue requirement)
    is properly indexed, retrieved by RAG, included in assembled context, and returned in evidence
    with valid source attribution and citations.
    """
    # 1. Setup tenant, project, and GitHub integration
    user = await create_test_user(email="integration-rag-test@unotusk.io")
    org, _ = await create_test_org(user=user, name="Integration RAG Org")
    project = await create_test_project(organization=org, name="Integration RAG Project")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-integration-rag-test",
        integration_metadata={"username": "integration-tester"},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-integration-rag-test",
        owner="unotusk-org",
        name="secure-auth-service",
        full_name="unotusk-org/secure-auth-service",
        default_branch="main",
        url="https://github.com/unotusk-org/secure-auth-service",
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

    # 2. Ingest minimal repository code
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, "src", "gateway.py"), "w") as f:
            f.write(
                "class AuthGateway:\n"
                "    def verify_request(self, headers, payload):\n"
                "        return True\n"
            )
        await IngestionService.run_ingestion(snapshot.id, override_local_dir=tmpdir)

    await db_session.refresh(snapshot)
    assert snapshot.status == SnapshotStatus.COMPLETED

    # 3. Add an integration record: GitHub Issue #42 detailing an authentication requirement
    issue_record = ProjectKnowledge(
        id=uuid.uuid4(),
        project_id=project.id,
        created_by=user.id,
        category=KnowledgeCategory.CONSTRAINT,
        title="Issue #42: Enforce HMAC-SHA256 request signing with 5-minute replay window",
        content=(
            "Requirement documented in GitHub Issue #42: All external API requests must include "
            "an HMAC-SHA256 signature in the X-Signature header and a timestamp in X-Timestamp. "
            "Requests with timestamps older than 300 seconds (5 minutes) must be rejected with HTTP 401."
        ),
        status=KnowledgeStatus.ACTIVE,
        source_type="GITHUB",
        source_reference_type="GITHUB_ISSUE",
        source_reference_id="#42",
        related_file_path="src/gateway.py",
        related_symbol="AuthGateway",
        knowledge_metadata={
            "issue_number": 42,
            "author": "security-lead",
            "url": "https://github.com/unotusk-org/secure-auth-service/issues/42",
            "labels": ["security", "api", "specification"],
        },
    )
    db_session.add(issue_record)
    await db_session.commit()

    # 4. Ask a question targeting the integration requirement
    question = "What signature algorithm and replay window does issue #42 require for requests?"

    engine = ProjectContextEngine()
    answer_pack = await engine.investigate(
        session=db_session,
        question=question,
        snapshot_id=snapshot.id,
        project_id=project.id,
    )

    # Assertions for RAG retrieval of integration data:
    # A. Content must reflect the integration record
    assert "HMAC-SHA256" in answer_pack.content or "HMAC" in answer_pack.content
    assert "5-minute" in answer_pack.content or "300" in answer_pack.content or "5 minutes" in answer_pack.content

    # B. Evidence items MUST include the integration record!
    assert len(answer_pack.evidence) >= 1
    integration_evidence = [
        e for e in answer_pack.evidence
        if e.get("source_reference_id") == "#42" or "42" in str(e.get("file", "")) or e.get("source_type") == "GITHUB"
    ]
    assert len(integration_evidence) >= 1, f"Expected integration evidence in evidence items, got: {answer_pack.evidence}"

    ev = integration_evidence[0]
    assert ev.get("source_type") == "GITHUB"
    assert ev.get("source_reference_type") == "GITHUB_ISSUE"
    assert ev.get("source_reference_id") == "#42"

    # C. Full IntelligenceService.ask_question API response test
    ask_res = await IntelligenceService.ask_question(
        session=db_session,
        user_id=user.id,
        project_id=project.id,
        question=question,
    )
    assert ask_res.role == "assistant"
    assert len(ask_res.evidence) >= 1
    api_int_ev = [
        e for e in ask_res.evidence
        if getattr(e, "source_reference_id", None) == "#42" or "42" in e.file or getattr(e, "source_type", None) == "GITHUB"
    ]
    assert len(api_int_ev) >= 1, f"Expected integration evidence in ask_res.evidence, got: {ask_res.evidence}"
