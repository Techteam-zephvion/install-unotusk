import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_project_crud_lifecycle(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    auth_headers,
):
    user = await create_test_user(email="developer@unotusk.io")
    org, _ = await create_test_org(user=user, name="Acme Labs")
    headers = auth_headers(user)

    # 1. Create project
    create_payload = {
        "organization_id": str(org.id),
        "name": "Payment Gateway",
        "description": "Stripe and PayPal integration engine",
    }
    create_res = await client.post("/api/v1/projects", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    project_data = create_res.json()
    project_id = project_data["id"]
    assert project_data["name"] == "Payment Gateway"
    assert project_data["slug"] == "payment-gateway"
    assert project_data["status"] == "CREATED"

    # 2. List projects
    list_res = await client.get(f"/api/v1/projects?organization_id={org.id}", headers=headers)
    assert list_res.status_code == 200
    projects = list_res.json()
    assert len(projects) == 1
    assert projects[0]["id"] == project_id

    # 3. Get single project
    get_res = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Payment Gateway"

    # 4. Update project
    patch_payload = {
        "name": "Payment Engine v2",
        "description": "Updated engine architecture",
    }
    patch_res = await client.patch(
        f"/api/v1/projects/{project_id}",
        json=patch_payload,
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Payment Engine v2"

    # 5. Delete project
    del_res = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert del_res.status_code == 204

    # 6. Verify deleted
    verify_res = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert verify_res.status_code == 404
    assert verify_res.json()["error"]["code"] == "PROJECT_NOT_FOUND"


@pytest.mark.asyncio
async def test_nonexistent_project_returns_404(
    client: AsyncClient,
    create_test_user,
    auth_headers,
):
    user = await create_test_user(email="random@unotusk.io")
    headers = auth_headers(user)
    random_id = str(uuid.uuid4())

    response = await client.get(f"/api/v1/projects/{random_id}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"
