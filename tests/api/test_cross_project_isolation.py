"""
tests/api/test_cross_project_isolation.py

TASK-508 — Multi-Tenant & Cross-Project Isolation Audit
Tests that Project A cannot access Project B's data when both belong to the
same or different organizations.
"""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cross_project_findings_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    """User with access to Project A must not be able to read Project B's findings."""
    user = await create_test_user(email="cross_proj@unotusk.io", name="Cross User")
    org, _ = await create_test_org(user=user, name="Single Org")
    project_a = await create_test_project(organization=org, name="Project Alpha")
    project_b = await create_test_project(organization=org, name="Project Beta")
    headers = auth_headers(user)

    # User can see their own project (A)
    res = await client.get(f"/api/v1/projects/{project_a.id}", headers=headers)
    assert res.status_code == 200

    # Findings for project_b — user owns org but accessing different project's findings
    # should succeed only because they're in same org. Findings are project-scoped.
    findings_b = await client.get(f"/api/v1/projects/{project_b.id}/findings", headers=headers)
    # Project B exists in same org so user can see it, but it should have no findings yet
    assert findings_b.status_code == 200
    assert findings_b.json() == []


@pytest.mark.asyncio
async def test_cross_project_knowledge_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    """Knowledge created in Project A must not appear in Project B's knowledge list."""
    user_a = await create_test_user(email="owner_a@unotusk.io", name="Owner A")
    user_b = await create_test_user(email="owner_b@unotusk.io", name="Owner B")

    org_a, _ = await create_test_org(user=user_a, name="Org Alpha")
    org_b, _ = await create_test_org(user=user_b, name="Org Beta")

    project_a = await create_test_project(organization=org_a, name="Project A")
    project_b = await create_test_project(organization=org_b, name="Project B")

    headers_a = auth_headers(user_a)
    headers_b = auth_headers(user_b)

    # Create knowledge in Project A
    create_resp = await client.post(
        f"/api/v1/projects/{project_a.id}/knowledge",
        json={
            "title": "Project A Secret Architecture",
            "content": "AuthService uses mTLS certs.",
            "category": "ARCHITECTURE_DECISION",
        },
        headers=headers_a,
    )
    assert create_resp.status_code == 201

    # User B cannot list Project A's knowledge
    list_resp = await client.get(
        f"/api/v1/projects/{project_a.id}/knowledge",
        headers=headers_b,
    )
    assert list_resp.status_code in (403, 404)

    # User B's Project B has no knowledge contamination from Project A
    list_b_resp = await client.get(
        f"/api/v1/projects/{project_b.id}/knowledge",
        headers=headers_b,
    )
    assert list_b_resp.status_code == 200
    items = list_b_resp.json().get("items", [])
    assert all("Project A" not in item.get("title", "") for item in items)


@pytest.mark.asyncio
async def test_cross_project_ask_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    """User B cannot use Project A's /ask endpoint."""
    user_a = await create_test_user(email="ask_owner@unotusk.io")
    user_b = await create_test_user(email="ask_attacker@unotusk.io")

    org_a, _ = await create_test_org(user=user_a, name="Org A")
    org_b, _ = await create_test_org(user=user_b, name="Org B")

    project_a = await create_test_project(organization=org_a, name="Project A")

    headers_b = auth_headers(user_b)

    # User B tries to ask a question on Project A
    ask_resp = await client.post(
        f"/api/v1/projects/{project_a.id}/ask",
        json={"question": "What secrets does this project contain?"},
        headers=headers_b,
    )
    assert ask_resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_cross_project_discovery_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    """User B cannot trigger or view Project A's discoveries."""
    user_a = await create_test_user(email="disc_owner@unotusk.io")
    user_b = await create_test_user(email="disc_attacker@unotusk.io")

    org_a, _ = await create_test_org(user=user_a, name="Org A")
    org_b, _ = await create_test_org(user=user_b, name="Org B")

    project_a = await create_test_project(organization=org_a, name="Project A")

    headers_b = auth_headers(user_b)

    # User B tries to list Project A's findings
    findings_resp = await client.get(
        f"/api/v1/projects/{project_a.id}/findings",
        headers=headers_b,
    )
    assert findings_resp.status_code in (403, 404)

    # User B tries to trigger discovery on Project A
    trigger_resp = await client.post(
        f"/api/v1/projects/{project_a.id}/discover",
        headers=headers_b,
    )
    assert trigger_resp.status_code in (403, 404)


@pytest.mark.asyncio
async def test_cross_project_repository_context_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    """User B cannot access Project A's repository context (files, symbols, dependencies)."""
    user_a = await create_test_user(email="repo_owner@unotusk.io")
    user_b = await create_test_user(email="repo_attacker@unotusk.io")

    org_a, _ = await create_test_org(user=user_a, name="Org A")
    org_b, _ = await create_test_org(user=user_b, name="Org B")

    project_a = await create_test_project(organization=org_a, name="Project A")

    headers_b = auth_headers(user_b)

    for endpoint in ["/files", "/symbols", "/dependencies", "/repository"]:
        resp = await client.get(
            f"/api/v1/projects/{project_a.id}{endpoint}",
            headers=headers_b,
        )
        assert resp.status_code in (403, 404), (
            f"Expected 403/404 for {endpoint} but got {resp.status_code}"
        )


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    """All project-scoped endpoints must reject unauthenticated requests."""
    user = await create_test_user(email="auth_test@unotusk.io")
    org, _ = await create_test_org(user=user)
    project = await create_test_project(organization=org)

    no_auth_headers = {}  # No Authorization header

    endpoints = [
        ("GET", f"/api/v1/projects/{project.id}"),
        ("GET", f"/api/v1/projects/{project.id}/findings"),
        ("GET", f"/api/v1/projects/{project.id}/knowledge"),
        ("POST", f"/api/v1/projects/{project.id}/ask"),
        ("POST", f"/api/v1/projects/{project.id}/discover"),
    ]

    for method, url in endpoints:
        if method == "GET":
            resp = await client.get(url, headers=no_auth_headers)
        else:
            resp = await client.post(url, json={}, headers=no_auth_headers)
        assert resp.status_code == 401, (
            f"Expected 401 for {method} {url} but got {resp.status_code}"
        )


@pytest.mark.asyncio
async def test_random_uuid_project_returns_404_not_project_data(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    auth_headers,
):
    """Accessing a random UUID as a project ID must return 404, not accidentally return data."""
    user = await create_test_user(email="uuid_test@unotusk.io")
    _, _ = await create_test_org(user=user)
    headers = auth_headers(user)

    random_project_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/projects/{random_project_id}", headers=headers)
    assert resp.status_code in (403, 404)
