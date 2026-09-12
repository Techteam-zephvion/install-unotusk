import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    IntegrationProvider,
    IntegrationStatus,
    SnapshotStatus,
)
from apps.api.src.models.finding import Finding
from apps.api.src.models.integration import Integration
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot


@pytest.mark.asyncio
async def test_discovery_api_lifecycle_and_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # 1. Setup Org 1 + User 1 + Project 1
    user1 = await create_test_user(email="disc-api-1@unotusk.io")
    org1, _ = await create_test_org(user=user1, name="Disc Org 1")
    project1 = await create_test_project(organization=org1, name="Disc Project 1")

    # Setup Org 2 + User 2 (for isolation check)
    user2 = await create_test_user(email="disc-api-2@unotusk.io")
    org2, _ = await create_test_org(user=user2, name="Disc Org 2")
    _ = await create_test_project(organization=org2, name="Disc Project 2")

    headers1 = auth_headers(user1)
    headers2 = auth_headers(user2)

    # Setup Repo & Snapshot for Project 1
    integration1 = Integration(
        id=uuid.uuid4(),
        project_id=project1.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="ext-int-1",
        integration_metadata={},
    )
    db_session.add(integration1)

    repo1 = Repository(
        id=uuid.uuid4(),
        project_id=project1.id,
        integration_id=integration1.id,
        provider=IntegrationProvider.GITHUB,
        external_id="ext-repo-1",
        owner="owner-1",
        name="repo-1",
        full_name="owner-1/repo-1",
        default_branch="main",
        url="https://github.com/owner-1/repo-1",
        is_private=False,
    )
    db_session.add(repo1)

    snapshot1 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo1.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )
    db_session.add(snapshot1)

    # Seed 2 findings
    finding1 = Finding(
        id=uuid.uuid4(),
        project_id=project1.id,
        snapshot_id=snapshot1.id,
        category=FindingCategory.CIRCULAR_DEPENDENCY,
        title="Circular import loop detected",
        description="A -> B -> A circular dependency detected",
        why_it_matters="Tight coupling and initialization failures",
        severity=FindingSeverity.HIGH,
        confidence=FindingConfidence.HIGH,
        status=FindingStatus.OPEN,
        score=85.0,
        recommendation="Extract shared types",
        evidence=[{"type": "edge", "file": "src/a.py", "target": "src/b.py"}],
        related_entities=["src/a.py", "src/b.py"],
    )
    finding2 = Finding(
        id=uuid.uuid4(),
        project_id=project1.id,
        snapshot_id=snapshot1.id,
        category=FindingCategory.TEST_GAP,
        title="Missing test coverage for billing",
        description="billing.py has no test suite",
        why_it_matters="Regression risk",
        severity=FindingSeverity.MEDIUM,
        confidence=FindingConfidence.HIGH,
        status=FindingStatus.OPEN,
        score=50.0,
        recommendation="Add unit tests",
        evidence=[{"type": "file", "file": "src/billing.py"}],
        related_entities=["src/billing.py"],
    )
    db_session.add(finding1)
    db_session.add(finding2)
    await db_session.commit()

    # 2. Test GET /projects/{id}/findings
    res = await client.get(f"/api/v1/projects/{project1.id}/findings", headers=headers1)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2

    # Filter by category
    filter_res = await client.get(
        f"/api/v1/projects/{project1.id}/findings?category=CIRCULAR_DEPENDENCY",
        headers=headers1,
    )
    assert filter_res.status_code == 200
    filter_data = filter_res.json()
    assert len(filter_data) == 1
    assert filter_data[0]["id"] == str(finding1.id)

    # 3. Test GET /projects/{id}/findings/{finding_id}
    detail_res = await client.get(
        f"/api/v1/projects/{project1.id}/findings/{finding1.id}",
        headers=headers1,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Circular import loop detected"

    # 4. Test PATCH /projects/{id}/findings/{finding_id} (Status update)
    patch_res = await client.patch(
        f"/api/v1/projects/{project1.id}/findings/{finding1.id}",
        headers=headers1,
        json={"status": "RESOLVED"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "RESOLVED"

    # 5. Test GET /projects/{id}/discover/status
    status_res = await client.get(
        f"/api/v1/projects/{project1.id}/discover/status",
        headers=headers1,
    )
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["total_findings"] == 1  # 1 OPEN finding left (finding2)
    assert status_data["medium_count"] == 1

    # 6. Test Cross-Organization Security Isolation
    unauthorized_res = await client.get(
        f"/api/v1/projects/{project1.id}/findings",
        headers=headers2,
    )
    assert unauthorized_res.status_code == 403
    assert unauthorized_res.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    unauthorized_patch = await client.patch(
        f"/api/v1/projects/{project1.id}/findings/{finding1.id}",
        headers=headers2,
        json={"status": "DISMISSED"},
    )
    assert unauthorized_patch.status_code == 403
