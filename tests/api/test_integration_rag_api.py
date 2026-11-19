import os
import tempfile
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import IntegrationProvider, IntegrationStatus, SnapshotStatus
from apps.api.src.models.integration import Integration
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.ingestion_service import IngestionService


@pytest.mark.asyncio
async def test_integration_rag_api_endpoints(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # Setup Tenant & Project
    user = await create_test_user(email="api-rag-lead@unotusk.io")
    org, _ = await create_test_org(user=user, name="RAG Lead Org")
    project = await create_test_project(organization=org, name="RAG Lead Project")
    headers = auth_headers(user)

    # Connected GitHub Integration
    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-rag-api-1",
        integration_metadata={"username": "rag-org"},
    )
    db_session.add(integration)

    repo = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-rag-api-1",
        owner="rag-org",
        name="auth-service",
        full_name="rag-org/auth-service",
        default_branch="main",
        url="https://github.com/rag-org/auth-service",
        is_private=False,
    )
    db_session.add(repo)

    snap = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.QUEUED,
    )
    db_session.add(snap)
    await db_session.commit()

    # Ingest code
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "tokens.py"), "w") as f:
            f.write(
                "class TokenValidator:\n"
                "    def validate(self, token_str):\n"
                "        return len(token_str) > 10\n"
            )
        await IngestionService.run_ingestion(snap.id, override_local_dir=tmpdir)

    # 1. Test POST /api/v1/repositories/{repo_id}/sync-issues
    issues_payload = {
        "issues": [
            {
                "id": "2001",
                "number": 77,
                "title": "Migrate JWT signing from HS256 to RS256 with key rotation",
                "body": "Issue #77: For compliance, all tokens must be signed with RS256 asymmetric keys. HS256 is deprecated.",
                "is_pull_request": False,
                "html_url": "https://github.com/rag-org/auth-service/issues/77",
                "labels": ["security", "rfc"],
                "author": "secops",
            }
        ]
    }
    sync_res = await client.post(
        f"/api/v1/projects/{project.id}/repositories/{repo.id}/sync-issues",
        json=issues_payload,
        headers=headers,
    )
    assert sync_res.status_code == 200, f"Sync failed: {sync_res.text}"
    sync_data = sync_res.json()
    assert len(sync_data) == 1
    assert sync_data[0]["number"] == 77
    assert sync_data[0]["status"] == "created"

    # 2. Test POST /api/v1/projects/{project_id}/ask with integration query
    ask_res = await client.post(
        f"/api/v1/projects/{project.id}/ask",
        json={"question": "What signing algorithm is mandated by Issue #77?"},
        headers=headers,
    )
    assert ask_res.status_code == 200, f"Ask failed: {ask_res.text}"
    ask_data = ask_res.json()

    # Validate response structure
    assert "content" in ask_data
    assert "evidence" in ask_data
    assert "confidence" in ask_data
    assert ask_data["confidence"] in ("HIGH", "MEDIUM")

    # Content must reflect the integrated issue requirements
    content = ask_data["content"]
    assert "RS256" in content

    # Evidence items must include the GitHub integration record with provenance
    int_evidence = [
        e for e in ask_data["evidence"]
        if e.get("source_type") == "GITHUB" or e.get("source_reference_id") == "#77"
    ]
    assert len(int_evidence) >= 1, f"Expected GITHUB evidence item, got: {ask_data['evidence']}"
    ev = int_evidence[0]
    assert ev.get("source_type") == "GITHUB"
    assert ev.get("source_reference_id") == "#77"
    assert ev.get("source_reference_type") == "GITHUB_ISSUE"

    # 3. Test Combined Query (Code + Integration)
    combined_res = await client.post(
        f"/api/v1/projects/{project.id}/ask",
        json={"question": "How does TokenValidator.validate relate to Issue #77?"},
        headers=headers,
    )
    assert combined_res.status_code == 200
    combined_data = combined_res.json()
    comb_ev_types = {e.get("source_type") for e in combined_data["evidence"]}
    assert "GITHUB" in comb_ev_types or any(e.get("source_reference_id") == "#77" for e in combined_data["evidence"])
