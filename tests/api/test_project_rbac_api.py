import uuid

import pytest
from httpx import AsyncClient

from apps.api.src.models.enums import MembershipRole


@pytest.mark.asyncio
async def test_project_membership_rbac_filtering(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    auth_headers,
    db_session,
):
    # 1. Setup Org with OWNER (owner_user) and regular MEMBER (member_user)
    owner_user = await create_test_user(email="owner@unotusk.io", name="Org Owner")
    member_user = await create_test_user(email="member@unotusk.io", name="Org Member")
    org, _ = await create_test_org(user=owner_user, name="RBAC Test Org")

    # Add member_user to the organization as MEMBER
    from apps.api.src.models.membership import OrganizationMembership

    org_membership = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=member_user.id,
        role=MembershipRole.MEMBER,
    )
    db_session.add(org_membership)
    await db_session.commit()

    owner_headers = auth_headers(owner_user)
    member_headers = auth_headers(member_user)

    # 2. Owner creates Project A and Project B
    res_a = await client.post(
        "/api/v1/projects",
        json={"organization_id": str(org.id), "name": "Project Alpha"},
        headers=owner_headers,
    )
    assert res_a.status_code == 201
    proj_a = res_a.json()
    proj_a_id = proj_a["id"]
    assert proj_a["role"] == "ADMIN"

    res_b = await client.post(
        "/api/v1/projects",
        json={"organization_id": str(org.id), "name": "Project Beta"},
        headers=owner_headers,
    )
    assert res_b.status_code == 201
    proj_b = res_b.json()
    proj_b_id = proj_b["id"]

    # 3. Owner lists projects: sees BOTH Alpha and Beta
    owner_list = await client.get(f"/api/v1/projects?organization_id={org.id}", headers=owner_headers)
    assert owner_list.status_code == 200
    owner_projects = owner_list.json()
    assert len(owner_projects) == 2
    proj_ids = {p["id"] for p in owner_projects}
    assert proj_a_id in proj_ids
    assert proj_b_id in proj_ids

    # 4. Member lists projects: sees 0 projects (not assigned to any yet)
    member_list_init = await client.get(f"/api/v1/projects?organization_id={org.id}", headers=member_headers)
    assert member_list_init.status_code == 200
    assert member_list_init.json() == []

    # 5. Member tries direct GET on Project Alpha: 403 Forbidden
    member_get_unassigned = await client.get(f"/api/v1/projects/{proj_a_id}", headers=member_headers)
    assert member_get_unassigned.status_code == 403
    assert member_get_unassigned.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"

    # 6. Owner assigns Member to Project Alpha via POST /members (using email)
    add_res = await client.post(
        f"/api/v1/projects/{proj_a_id}/members",
        json={"email": member_user.email, "role": "MEMBER"},
        headers=owner_headers,
    )
    assert add_res.status_code == 201
    member_entry = add_res.json()
    assert member_entry["user_id"] == str(member_user.id)
    assert member_entry["user_email"] == member_user.email
    assert member_entry["user_name"] == member_user.name
    assert member_entry["role"] == "MEMBER"

    # 7. Member lists projects again: now sees only Project Alpha
    member_list_after = await client.get(f"/api/v1/projects?organization_id={org.id}", headers=member_headers)
    assert member_list_after.status_code == 200
    member_projs = member_list_after.json()
    assert len(member_projs) == 1
    assert member_projs[0]["id"] == proj_a_id
    assert member_projs[0]["role"] == "MEMBER"

    # 8. Member direct GET on Project Alpha now succeeds
    member_get_assigned = await client.get(f"/api/v1/projects/{proj_a_id}", headers=member_headers)
    assert member_get_assigned.status_code == 200
    assert member_get_assigned.json()["name"] == "Project Alpha"

    # Project Beta remains forbidden for Member
    member_get_beta = await client.get(f"/api/v1/projects/{proj_b_id}", headers=member_headers)
    assert member_get_beta.status_code == 403

    # 9. List project members
    members_res = await client.get(f"/api/v1/projects/{proj_a_id}/members", headers=member_headers)
    assert members_res.status_code == 200
    members_data = members_res.json()
    assert len(members_data) == 2  # Owner (ADMIN) + Member (MEMBER)
    emails = {m["user_email"] for m in members_data}
    assert owner_user.email in emails
    assert member_user.email in emails

    # 10. Regular Member attempts to add another member: 403 Forbidden
    outsider_user = await create_test_user(email="outsider@unotusk.io", name="Outsider")
    # Add outsider to org
    outsider_membership = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=outsider_user.id,
        role=MembershipRole.MEMBER,
    )
    db_session.add(outsider_membership)
    await db_session.commit()

    forbidden_add = await client.post(
        f"/api/v1/projects/{proj_a_id}/members",
        json={"user_id": str(outsider_user.id), "role": "MEMBER"},
        headers=member_headers,
    )
    assert forbidden_add.status_code == 403
    assert forbidden_add.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # 11. Regular Member attempts to update project name: 403 Forbidden
    forbidden_update = await client.patch(
        f"/api/v1/projects/{proj_a_id}",
        json={"name": "Hacked Name"},
        headers=member_headers,
    )
    assert forbidden_update.status_code == 403
    assert forbidden_update.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # 12. Removing members:
    # A) Regular Member leaves project voluntarily: succeeds
    leave_res = await client.delete(
        f"/api/v1/projects/{proj_a_id}/members/{member_user.id}",
        headers=member_headers,
    )
    assert leave_res.status_code == 204

    # Now Member's project list is empty again
    member_list_final = await client.get(f"/api/v1/projects?organization_id={org.id}", headers=member_headers)
    assert member_list_final.status_code == 200
    assert member_list_final.json() == []


@pytest.mark.asyncio
async def test_project_membership_validation_errors(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    auth_headers,
):
    owner = await create_test_user(email="admin@unotusk.io")
    org, _ = await create_test_org(user=owner, name="Validation Org")
    headers = auth_headers(owner)

    # Create project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"organization_id": str(org.id), "name": "Val Project"},
        headers=headers,
    )
    proj_id = proj_res.json()["id"]

    # 1. Add non-existent user: 404
    res_404 = await client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"email": "nonexistent@unotusk.io"},
        headers=headers,
    )
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "USER_NOT_FOUND"

    # 2. Add user who does NOT belong to the organization: 409 USER_NOT_IN_ORGANIZATION
    foreign_user = await create_test_user(email="foreign@othercompany.io")
    res_foreign = await client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": str(foreign_user.id)},
        headers=headers,
    )
    assert res_foreign.status_code == 409
    assert res_foreign.json()["error"]["code"] == "USER_NOT_IN_ORGANIZATION"

    # 3. Add user who is already a member (creator is already admin): 409 MEMBER_ALREADY_EXISTS
    res_duplicate = await client.post(
        f"/api/v1/projects/{proj_id}/members",
        json={"user_id": str(owner.id)},
        headers=headers,
    )
    assert res_duplicate.status_code == 409
    assert res_duplicate.json()["error"]["code"] == "MEMBER_ALREADY_EXISTS"

    # 4. Remove non-existent member: 404
    res_del_404 = await client.delete(
        f"/api/v1/projects/{proj_id}/members/{foreign_user.id}",
        headers=headers,
    )
    assert res_del_404.status_code == 404
    assert res_del_404.json()["error"]["code"] == "MEMBERSHIP_NOT_FOUND"


@pytest.mark.asyncio
async def test_organization_members_list(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    auth_headers,
    db_session,
):
    owner = await create_test_user(email="org-owner@unotusk.io", name="Team Lead")
    employee = await create_test_user(email="engineer@unotusk.io", name="Staff Engineer")
    org, _ = await create_test_org(user=owner, name="Engineering Department")

    from apps.api.src.models.membership import OrganizationMembership

    mem = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=employee.id,
        role=MembershipRole.MEMBER,
    )
    db_session.add(mem)
    await db_session.commit()

    headers = auth_headers(owner)
    res = await client.get(f"/api/v1/organizations/{org.id}/members", headers=headers)
    assert res.status_code == 200
    members = res.json()
    assert len(members) == 2
    emails = {m["user_email"] for m in members}
    assert "org-owner@unotusk.io" in emails
    assert "engineer@unotusk.io" in emails

