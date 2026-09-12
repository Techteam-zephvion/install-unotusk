import uuid
import pytest
from httpx import AsyncClient
from apps.api.src.models.enums import MembershipRole


@pytest.mark.asyncio
async def test_cross_organization_project_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # Setup Tenant A: User A, Org A, Project A
    user_a = await create_test_user(email="user_a@org-a.com", name="User A")
    org_a, _ = await create_test_org(user=user_a, name="Organization A")
    project_a = await create_test_project(organization=org_a, name="Project Alpha")
    headers_a = auth_headers(user_a)

    # Setup Tenant B: User B, Org B, Project B
    user_b = await create_test_user(email="user_b@org-b.com", name="User B")
    org_b, _ = await create_test_org(user=user_b, name="Organization B")
    project_b = await create_test_project(organization=org_b, name="Project Beta")
    headers_b = auth_headers(user_b)

    # 1. Verify User A can access Project A
    res_a = await client.get(f"/api/v1/projects/{project_a.id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == str(project_a.id)

    # 2. Verify User B can access Project B
    res_b = await client.get(f"/api/v1/projects/{project_b.id}", headers=headers_b)
    assert res_b.status_code == 200
    assert res_b.json()["id"] == str(project_b.id)

    # 3. SECURITY CHECK: User A attempts to GET Project B (IDOR attempt)
    idor_get = await client.get(f"/api/v1/projects/{project_b.id}", headers=headers_a)
    assert idor_get.status_code in (403, 404)
    error_code = idor_get.json()["error"]["code"]
    assert error_code in ("ORGANIZATION_ACCESS_DENIED", "PROJECT_NOT_FOUND")

    # 4. SECURITY CHECK: User A attempts to PATCH Project B (Unauthorized mutation)
    idor_patch = await client.patch(
        f"/api/v1/projects/{project_b.id}",
        json={"name": "Hacked Project Name"},
        headers=headers_a,
    )
    assert idor_patch.status_code in (403, 404)

    # 5. SECURITY CHECK: User A attempts to DELETE Project B (Unauthorized destruction)
    idor_delete = await client.delete(
        f"/api/v1/projects/{project_b.id}",
        headers=headers_a,
    )
    assert idor_delete.status_code in (403, 404)

    # 6. SECURITY CHECK: User A attempts to LIST projects in Organization B
    idor_list = await client.get(
        f"/api/v1/projects?organization_id={org_b.id}",
        headers=headers_a,
    )
    assert idor_list.status_code == 403
    assert idor_list.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    # 7. SECURITY CHECK: User A attempts to CREATE a project inside Organization B
    idor_create = await client.post(
        "/api/v1/projects",
        json={"organization_id": str(org_b.id), "name": "Injected Project"},
        headers=headers_a,
    )
    assert idor_create.status_code == 403
    assert idor_create.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

    # Verify Project B remains unchanged and intact for User B
    check_b = await client.get(f"/api/v1/projects/{project_b.id}", headers=headers_b)
    assert check_b.status_code == 200
    assert check_b.json()["name"] == "Project Beta"
