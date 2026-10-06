import uuid

import pytest
from httpx import AsyncClient

from apps.api.src.config.settings import settings
from apps.api.src.models.enums import MembershipRole


@pytest.mark.asyncio
async def test_control_plane_default_headers(
    client: AsyncClient,
):
    """Verify that in default Control Plane mode, X-Data-Plane is 'false'."""
    settings.DATA_PLANE_PROJECT_ID = None
    settings.DATA_PLANE_ORG_ID = None

    response = await client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Data-Plane") == "false"
    assert "X-Data-Plane-Project-Id" not in response.headers


@pytest.mark.asyncio
async def test_data_plane_headers_and_health(
    client: AsyncClient,
):
    """Verify that in Data Plane mode, X-Data-Plane is 'true' and health checks pass."""
    proj_id = uuid.uuid4()
    org_id = uuid.uuid4()
    settings.DATA_PLANE_PROJECT_ID = str(proj_id)
    settings.DATA_PLANE_ORG_ID = str(org_id)

    try:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.headers.get("X-Data-Plane") == "true"
        assert response.headers.get("X-Data-Plane-Project-Id") == str(proj_id)
        assert response.headers.get("X-Data-Plane-Org-Id") == str(org_id)
    finally:
        settings.DATA_PLANE_PROJECT_ID = None
        settings.DATA_PLANE_ORG_ID = None


@pytest.mark.asyncio
async def test_data_plane_cross_project_boundary_violation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    auth_headers,
):
    """Verify that attempting to access a different project on a Data Plane container is blocked."""
    assigned_proj_id = uuid.uuid4()
    different_proj_id = uuid.uuid4()
    user = await create_test_user(email="dp-admin@unotusk.io")
    org, _ = await create_test_org(user=user, name="DP Isolation Org", role=MembershipRole.OWNER)
    headers = auth_headers(user)

    settings.DATA_PLANE_PROJECT_ID = str(assigned_proj_id)
    settings.DATA_PLANE_ORG_ID = str(org.id)

    try:
        # Requesting a different project on this dedicated container must be rejected with 403
        response = await client.get(f"/api/v1/projects/{different_proj_id}", headers=headers)
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["code"] == "DATA_PLANE_BOUNDARY_VIOLATION"
        assert str(different_proj_id).lower() in data["error"]["details"]["requested_project_id"]
        assert response.headers.get("X-Data-Plane") == "true"
    finally:
        settings.DATA_PLANE_PROJECT_ID = None
        settings.DATA_PLANE_ORG_ID = None


@pytest.mark.asyncio
async def test_data_plane_control_plane_routes_locked_down(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    auth_headers,
):
    """Verify that Control Plane mutations (create project, delete project, org management, signup) are blocked on Data Plane."""
    proj_id = uuid.uuid4()
    user = await create_test_user(email="dp-lockdown@unotusk.io")
    org, _ = await create_test_org(user=user, name="DP Lockdown Org", role=MembershipRole.OWNER)
    headers = auth_headers(user)

    settings.DATA_PLANE_PROJECT_ID = str(proj_id)
    settings.DATA_PLANE_ORG_ID = str(org.id)

    try:
        # 1. POST /projects blocked
        resp_post = await client.post(
            "/api/v1/projects",
            json={"name": "New Project", "organization_id": str(org.id)},
            headers=headers,
        )
        assert resp_post.status_code == 403
        assert resp_post.json()["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"

        # 2. DELETE /projects/{id} blocked
        resp_del = await client.delete(
            f"/api/v1/projects/{proj_id}",
            headers=headers,
        )
        assert resp_del.status_code == 403
        assert resp_del.json()["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"

        # 3. Organizations routes blocked
        resp_org = await client.get(
            "/api/v1/organizations",
            headers=headers,
        )
        assert resp_org.status_code == 403
        assert resp_org.json()["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"

        # 4. Signup route blocked
        resp_signup = await client.post(
            "/api/v1/auth/signup",
            json={
                "name": "Attacker",
                "email": "attacker@evil.com",
                "password": "Password123!",
                "organization_name": "Rogue Org",
            },
        )
        assert resp_signup.status_code == 403
        assert resp_signup.json()["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"
    finally:
        settings.DATA_PLANE_PROJECT_ID = None
        settings.DATA_PLANE_ORG_ID = None


@pytest.mark.asyncio
async def test_data_plane_user_membership_authorization(
    client: AsyncClient,
    db_session,
    create_test_user,
    create_test_org,
    create_test_project,
    create_test_project_membership,
    auth_headers,
):
    """
    Verify container-level user authorization guardrails:
    - User from foreign org -> 403 ORGANIZATION_ACCESS_DENIED
    - Org member not assigned to project -> 403 PROJECT_ACCESS_DENIED
    - Assigned member -> 200 OK
    - Org Owner/Admin -> 200 OK
    """
    from apps.api.src.models.membership import OrganizationMembership

    owner1 = await create_test_user(email="owner1@org1.com")
    org1, _ = await create_test_org(user=owner1, name="Org One", role=MembershipRole.OWNER)

    foreign_user = await create_test_user(email="foreign@org2.com")
    org2, _ = await create_test_org(user=foreign_user, name="Org Two", role=MembershipRole.OWNER)

    member_assigned = await create_test_user(email="assigned@org1.com")
    member_unassigned = await create_test_user(email="unassigned@org1.com")

    db_session.add_all([
        OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org1.id,
            user_id=member_assigned.id,
            role=MembershipRole.MEMBER,
        ),
        OrganizationMembership(
            id=uuid.uuid4(),
            organization_id=org1.id,
            user_id=member_unassigned.id,
            role=MembershipRole.MEMBER,
        ),
    ])
    await db_session.commit()

    # Project on org1
    project = await create_test_project(organization=org1, name="Data Plane Project")
    await create_test_project_membership(project=project, user=member_assigned, role=MembershipRole.MEMBER)

    settings.DATA_PLANE_PROJECT_ID = str(project.id)
    settings.DATA_PLANE_ORG_ID = str(org1.id)

    try:
        # 1. Foreign user from org2
        resp_foreign = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers(foreign_user),
        )
        assert resp_foreign.status_code == 403
        assert resp_foreign.json()["error"]["code"] == "ORGANIZATION_ACCESS_DENIED"

        # 2. Member of org1 but not assigned to this project
        resp_unassigned = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers(member_unassigned),
        )
        assert resp_unassigned.status_code == 403
        assert resp_unassigned.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"

        # 3. Assigned member of project
        resp_assigned = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers(member_assigned),
        )
        assert resp_assigned.status_code == 200
        assert resp_assigned.json()["id"] == str(project.id)

        # 4. Org Owner (has access to all projects in org)
        resp_owner = await client.get(
            f"/api/v1/projects/{project.id}",
            headers=auth_headers(owner1),
        )
        assert resp_owner.status_code == 200
        assert resp_owner.json()["id"] == str(project.id)
    finally:
        settings.DATA_PLANE_PROJECT_ID = None
        settings.DATA_PLANE_ORG_ID = None
