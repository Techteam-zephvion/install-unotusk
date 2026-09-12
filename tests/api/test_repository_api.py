import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_repository_api_lifecycle_and_isolation(
    client: AsyncClient,
    db_session,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # Setup Tenant A
    user_a = await create_test_user(email="repo-user-a@org-a.com")
    org_a, _ = await create_test_org(user=user_a, name="Org A")
    project_a = await create_test_project(organization=org_a, name="Project A")
    headers_a = auth_headers(user_a)

    # Setup Tenant B
    user_b = await create_test_user(email="repo-user-b@org-b.com")
    org_b, _ = await create_test_org(user=user_b, name="Org B")
    project_b = await create_test_project(organization=org_b, name="Project B")
    headers_b = auth_headers(user_b)

    # 1. Select repository for Project A
    select_payload = {
        "external_id": "987654",
        "owner": "org-a",
        "name": "core-repo",
        "full_name": "org-a/core-repo",
        "default_branch": "main",
        "url": "https://github.com/org-a/core-repo",
        "is_private": True,
        "description": "Core backend repo",
    }
    select_res = await client.post(
        f"/api/v1/projects/{project_a.id}/repositories/select",
        json=select_payload,
        headers=headers_a,
    )
    assert select_res.status_code == 201
    repo_data = select_res.json()
    repo_id = repo_data["id"]
    assert repo_data["full_name"] == "org-a/core-repo"

    # 2. Get repository context for Project A
    ctx_res = await client.get(f"/api/v1/projects/{project_a.id}/repository", headers=headers_a)
    assert ctx_res.status_code == 200
    ctx_data = ctx_res.json()
    assert ctx_data["repository"]["full_name"] == "org-a/core-repo"

    # 3. Trigger Ingestion for Project A
    ingest_res = await client.post(
        f"/api/v1/projects/{project_a.id}/repositories/{repo_id}/ingest",
        headers=headers_a,
    )
    assert ingest_res.status_code == 202
    ingest_data = ingest_res.json()
    snapshot_id = ingest_data["snapshot_id"]
    assert ingest_data["status"] == "QUEUED"

    # 4. Get Ingestion Status
    status_res = await client.get(
        f"/api/v1/projects/{project_a.id}/ingestions/{snapshot_id}",
        headers=headers_a,
    )
    assert status_res.status_code == 200
    assert status_res.json()["id"] == snapshot_id

    # 5. List Files, Symbols, Dependencies for Project A
    files_res = await client.get(f"/api/v1/projects/{project_a.id}/files", headers=headers_a)
    assert files_res.status_code == 200
    assert isinstance(files_res.json(), list)

    symbols_res = await client.get(f"/api/v1/projects/{project_a.id}/symbols", headers=headers_a)
    assert symbols_res.status_code == 200
    assert isinstance(symbols_res.json(), list)

    deps_res = await client.get(f"/api/v1/projects/{project_a.id}/dependencies", headers=headers_a)
    assert deps_res.status_code == 200
    assert isinstance(deps_res.json(), list)

    # 6. SECURITY CHECK: Cross-Organization Isolation
    # User B attempts to access Project A's repository context
    cross_ctx = await client.get(f"/api/v1/projects/{project_a.id}/repository", headers=headers_b)
    assert cross_ctx.status_code == 403
    assert cross_ctx.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    # User B attempts to trigger ingestion on Project A
    cross_ingest = await client.post(
        f"/api/v1/projects/{project_a.id}/repositories/{repo_id}/ingest",
        headers=headers_b,
    )
    assert cross_ingest.status_code == 403

    # User B attempts to list files of Project A
    cross_files = await client.get(f"/api/v1/projects/{project_a.id}/files", headers=headers_b)
    assert cross_files.status_code == 403

    # User A attempts to access Project B
    cross_b = await client.get(f"/api/v1/projects/{project_b.id}/repository", headers=headers_a)
    assert cross_b.status_code == 403
