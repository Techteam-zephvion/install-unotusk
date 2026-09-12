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
async def test_intelligence_api_lifecycle_and_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # Setup Tenant A
    user_a = await create_test_user(email="tenant-a-intel@unotusk.io")
    org_a, _ = await create_test_org(user=user_a, name="Org A")
    project_a = await create_test_project(organization=org_a, name="Project A")
    headers_a = auth_headers(user_a)

    # Setup Tenant B
    user_b = await create_test_user(email="tenant-b-intel@unotusk.io")
    org_b, _ = await create_test_org(user=user_b, name="Org B")
    project_b = await create_test_project(organization=org_b, name="Project B")
    headers_b = auth_headers(user_b)

    # Ingest a simple repo for Project A
    integration = Integration(
        id=uuid.uuid4(),
        project_id=project_a.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-a-123",
        integration_metadata={},
    )
    db_session.add(integration)

    repository = Repository(
        id=uuid.uuid4(),
        project_id=project_a.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-a-123",
        owner="org-a",
        name="backend",
        full_name="org-a/backend",
        default_branch="main",
        url="https://github.com/org-a/backend",
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

    with tempfile.TemporaryDirectory() as tmpdir:
        api_file = os.path.join(tmpdir, "routes.py")
        with open(api_file, "w") as f:
            f.write("class PaymentGateway:\n    def process_charge(self, amt):\n        return True\n")
        await IngestionService.run_ingestion(snapshot.id, override_local_dir=tmpdir)

    # 1. Ask question on Project A
    ask_res = await client.post(
        f"/api/v1/projects/{project_a.id}/ask",
        json={"question": "Where is PaymentGateway implemented?"},
        headers=headers_a,
    )
    assert ask_res.status_code == 200
    data = ask_res.json()
    assert "PaymentGateway" in data["content"]
    assert data["confidence"] in ("HIGH", "MEDIUM")
    assert len(data["evidence"]) >= 1
    conv_id = data["conversation_id"]

    # 2. List conversations on Project A
    convs_res = await client.get(
        f"/api/v1/projects/{project_a.id}/conversations",
        headers=headers_a,
    )
    assert convs_res.status_code == 200
    convs = convs_res.json()
    assert len(convs) >= 1
    assert convs[0]["id"] == conv_id

    # 3. Get messages for conversation
    msgs_res = await client.get(
        f"/api/v1/projects/{project_a.id}/conversations/{conv_id}",
        headers=headers_a,
    )
    assert msgs_res.status_code == 200
    msgs = msgs_res.json()
    assert len(msgs) == 2  # user + assistant

    # 4. Context Search Debug on Project A
    search_res = await client.post(
        f"/api/v1/projects/{project_a.id}/context/search",
        json={"query": "PaymentGateway"},
        headers=headers_a,
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["candidates_count"] >= 1

    # 5. SECURITY / MULTI-TENANT ISOLATION (The Golden Test)
    # User B attempts to ask questions on Project A
    cross_ask = await client.post(
        f"/api/v1/projects/{project_a.id}/ask",
        json={"question": "Secret data?"},
        headers=headers_b,
    )
    assert cross_ask.status_code == 403
    assert cross_ask.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    # User B attempts to read Project A's conversations
    cross_convs = await client.get(
        f"/api/v1/projects/{project_a.id}/conversations",
        headers=headers_b,
    )
    assert cross_convs.status_code == 403

    # User A attempts to read Project B's conversations
    cross_convs_b = await client.get(
        f"/api/v1/projects/{project_b.id}/conversations",
        headers=headers_a,
    )
    assert cross_convs_b.status_code == 403
