import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.enums import KnowledgeCategory, KnowledgeStatus


@pytest.mark.asyncio
async def test_knowledge_api_full_crud_and_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # Setup Org A and User A
    user_a = await create_test_user(email="user_a_know@unotusk.io")
    org_a, _ = await create_test_org(user=user_a, name="Org A")
    project_a = await create_test_project(organization=org_a, name="Project A")
    headers_a = auth_headers(user_a)

    # Setup Org B and User B
    user_b = await create_test_user(email="user_b_know@unotusk.io")
    org_b, _ = await create_test_org(user=user_b, name="Org B")
    await create_test_project(organization=org_b, name="Project B")
    headers_b = auth_headers(user_b)

    # 1. Test Unauthenticated Access -> 401
    unauth_resp = await client.get(f"/api/v1/projects/{project_a.id}/knowledge")
    assert unauth_resp.status_code == 401

    # 2. Test User A creates knowledge on Project A
    create_payload = {
        "category": "ARCHITECTURE_DECISION",
        "title": "AuthService boundary is intentional",
        "content": "AuthService centralizes all token generation and user session validation.",
        "related_file_path": "src/auth/service.py",
        "related_symbol": "AuthService",
    }
    create_resp = await client.post(
        f"/api/v1/projects/{project_a.id}/knowledge",
        json=create_payload,
        headers=headers_a,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    knowledge_id = created_data["id"]
    assert created_data["title"] == "AuthService boundary is intentional"
    assert created_data["category"] == KnowledgeCategory.ARCHITECTURE_DECISION.value
    assert created_data["status"] == KnowledgeStatus.ACTIVE.value
    assert created_data["created_by"] == str(user_a.id)

    # 3. Test Cross-Tenant Access: User B attempts to read User A's knowledge -> 403 Forbidden
    cross_read = await client.get(
        f"/api/v1/projects/{project_a.id}/knowledge/{knowledge_id}",
        headers=headers_b,
    )
    assert cross_read.status_code == 403

    # Cross-Tenant Access: User B attempts to list Project A's knowledge -> 403 Forbidden
    cross_list = await client.get(
        f"/api/v1/projects/{project_a.id}/knowledge",
        headers=headers_b,
    )
    assert cross_list.status_code == 403

    # Cross-Tenant Access: User B attempts to create knowledge on Project A -> 403 Forbidden
    cross_create = await client.post(
        f"/api/v1/projects/{project_a.id}/knowledge",
        json={"title": "Hacked", "content": "Bad context", "category": "INTENT"},
        headers=headers_b,
    )
    assert cross_create.status_code == 403

    # 4. User A reads the created knowledge
    get_resp = await client.get(
        f"/api/v1/projects/{project_a.id}/knowledge/{knowledge_id}",
        headers=headers_a,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == knowledge_id

    # 5. List with filters (category, status, search)
    list_resp = await client.get(
        f"/api/v1/projects/{project_a.id}/knowledge?status=ACTIVE&category=ARCHITECTURE_DECISION&search=AuthService",
        headers=headers_a,
    )
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(k["id"] == knowledge_id for k in list_data["items"])

    # 6. Update Knowledge
    patch_resp = await client.patch(
        f"/api/v1/projects/{project_a.id}/knowledge/{knowledge_id}",
        json={
            "title": "AuthService boundary is intentional (Updated)",
            "content": "AuthService centralizes tokens, sessions, and multi-tenant keys.",
        },
        headers=headers_a,
    )
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["title"] == "AuthService boundary is intentional (Updated)"
    assert "multi-tenant" in updated_data["content"]

    # 7. Archive Knowledge
    archive_resp = await client.post(
        f"/api/v1/projects/{project_a.id}/knowledge/{knowledge_id}/archive",
        headers=headers_a,
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == KnowledgeStatus.ARCHIVED.value

    # Archived item is not returned in status=ACTIVE query
    active_list = await client.get(
        f"/api/v1/projects/{project_a.id}/knowledge?status=ACTIVE",
        headers=headers_a,
    )
    assert active_list.status_code == 200
    assert not any(k["id"] == knowledge_id for k in active_list.json()["items"])

    # Archived item IS returned in status=ARCHIVED query
    archived_list = await client.get(
        f"/api/v1/projects/{project_a.id}/knowledge?status=ARCHIVED",
        headers=headers_a,
    )
    assert archived_list.status_code == 200
    assert any(k["id"] == knowledge_id for k in archived_list.json()["items"])

    # 8. Restore Knowledge
    restore_resp = await client.post(
        f"/api/v1/projects/{project_a.id}/knowledge/{knowledge_id}/restore",
        headers=headers_a,
    )
    assert restore_resp.status_code == 200
    assert restore_resp.json()["status"] == KnowledgeStatus.ACTIVE.value
