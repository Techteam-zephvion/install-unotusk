import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
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


@pytest.mark.asyncio
async def test_reports_api_full_lifecycle_and_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # Setup Org A and User A
    user_a = await create_test_user(email="user_a_rep@unotusk.io")
    org_a, _ = await create_test_org(user=user_a, name="Org A")
    project_a = await create_test_project(organization=org_a, name="Project A")
    headers_a = auth_headers(user_a)

    # Setup Org B and User B
    user_b = await create_test_user(email="user_b_rep@unotusk.io")
    org_b, _ = await create_test_org(user=user_b, name="Org B")
    project_b = await create_test_project(organization=org_b, name="Project B")
    headers_b = auth_headers(user_b)

    # Attach repository and completed snapshot to Project A
    integration_a = Integration(
        id=uuid.uuid4(),
        project_id=project_a.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-a-rep",
        integration_metadata={},
    )
    db_session.add(integration_a)

    repo_a = Repository(
        id=uuid.uuid4(),
        project_id=project_a.id,
        integration_id=integration_a.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-a-rep",
        owner="owner-a",
        name="repo-a",
        full_name="owner-a/repo-a",
        default_branch="main",
        url="https://github.com/owner-a/repo-a",
        is_private=False,
    )
    db_session.add(repo_a)

    snapshot_a = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo_a.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )
    db_session.add(snapshot_a)

    # Pre-seed a completed report for Project A
    report_a = ProjectIntelligenceReport(
        id=uuid.uuid4(),
        project_id=project_a.id,
        snapshot_id=snapshot_a.id,
        status=ReportStatus.COMPLETED,
        report_version="1.0.0",
        generated_at=datetime.now(UTC),
        summary="Initial completed report for Project A",
        report_data={
            "metadata": {"test": True},
            "executive_summary": {
                "project_summary": "Test project summary",
                "state_assessment": "MODERATE_RISK",
                "vital_metrics": {
                    "total_files": 12,
                    "total_symbols": 45,
                    "total_dependencies": 30,
                    "total_discoveries": 4,
                    "critical_findings": 0,
                    "high_findings": 1,
                },
                "top_things_to_know": [],
                "top_next_actions": [],
            },
            "project_understanding": {
                "primary_languages": {"Python": 10},
                "repository_size": {
                    "total_lines": 500,
                    "total_bytes": 1024,
                    "size_formatted": "1 KB",
                },
                "major_areas": [],
                "key_symbols": [],
                "architectural_boundaries": [],
                "business_purpose_note": "Test purpose",
            },
            "observed": [],
            "discoveries": [],
            "risk_areas": [],
            "technical_debt": [],
            "dependencies": [],
            "testing_and_documentation": {
                "testing_observed": [],
                "testing_derived": "",
                "testing_recommended": "",
                "testing_coverage_note": "No coverage tool",
                "docs_observed": [],
                "docs_recommended": "",
            },
            "next_actions": [],
        },
    )
    db_session.add(report_a)
    await db_session.commit()

    # 1. User A lists reports for Project A
    resp = await client.get(f"/api/v1/projects/{project_a.id}/reports", headers=headers_a)
    assert resp.status_code == 200
    reports_list = resp.json()
    assert len(reports_list) == 1
    assert reports_list[0]["id"] == str(report_a.id)
    assert reports_list[0]["status"] == "COMPLETED"

    # 2. User A gets latest report for Project A
    resp = await client.get(f"/api/v1/projects/{project_a.id}/reports/latest", headers=headers_a)
    assert resp.status_code == 200
    latest_data = resp.json()
    assert latest_data["id"] == str(report_a.id)
    assert latest_data["report_data"]["executive_summary"]["state_assessment"] == "MODERATE_RISK"

    # 3. User A gets specific report for Project A
    resp = await client.get(
        f"/api/v1/projects/{project_a.id}/reports/{report_a.id}", headers=headers_a
    )
    assert resp.status_code == 200
    specific_data = resp.json()
    assert specific_data["id"] == str(report_a.id)

    # 4. User A triggers report generation for Project A
    resp = await client.post(f"/api/v1/projects/{project_a.id}/reports", headers=headers_a)
    assert resp.status_code in [200, 202]
    trigger_data = resp.json()
    assert "report_id" in trigger_data
    assert trigger_data["status"] in ["QUEUED", "GENERATING", "COMPLETED"]

    # 5. Cross-Organization Tenant Isolation: User B attempts to access Project A's reports
    resp_cross_list = await client.get(
        f"/api/v1/projects/{project_a.id}/reports", headers=headers_b
    )
    assert resp_cross_list.status_code == 403, "Cross-tenant list reports must return 403 Forbidden"

    resp_cross_latest = await client.get(
        f"/api/v1/projects/{project_a.id}/reports/latest", headers=headers_b
    )
    assert resp_cross_latest.status_code == 403, (
        "Cross-tenant get latest report must return 403 Forbidden"
    )

    resp_cross_get = await client.get(
        f"/api/v1/projects/{project_a.id}/reports/{report_a.id}", headers=headers_b
    )
    assert resp_cross_get.status_code == 403, "Cross-tenant get report must return 403 Forbidden"

    resp_cross_post = await client.post(
        f"/api/v1/projects/{project_a.id}/reports", headers=headers_b
    )
    assert resp_cross_post.status_code == 403, (
        "Cross-tenant trigger report must return 403 Forbidden"
    )

    resp_cross_reverse = await client.get(
        f"/api/v1/projects/{project_b.id}/reports", headers=headers_a
    )
    assert resp_cross_reverse.status_code == 403, (
        "User A accessing Project B must return 403 Forbidden"
    )

    # 6. Unauthenticated requests must return 401 Unauthorized
    resp_unauth = await client.get(f"/api/v1/projects/{project_a.id}/reports")
    assert resp_unauth.status_code == 401

    # 7. Non-existent report returns 404
    random_id = uuid.uuid4()
    resp_404 = await client.get(
        f"/api/v1/projects/{project_a.id}/reports/{random_id}", headers=headers_a
    )
    assert resp_404.status_code == 404
