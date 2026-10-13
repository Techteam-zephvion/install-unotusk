import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_signup_flow(client: AsyncClient):
    payload = {
        "name": "Grace Hopper",
        "email": "grace@acme.com",
        "password": "SuperSecurePassword123!",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "grace@acme.com"
    assert data["user"]["name"] == "Grace Hopper"
    assert data["default_organization_id"] is not None


@pytest.mark.asyncio
async def test_disallowed_domain_signup_rejected(client: AsyncClient):
    payload = {
        "name": "External User",
        "email": "user@gmail.com",
        "password": "SuperSecurePassword123!",
    }
    response = await client.post("/api/v1/auth/signup", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "DISALLOWED_EMAIL_DOMAIN"
    assert "acme.com" in data["error"]["message"]


@pytest.mark.asyncio
async def test_disallowed_domain_login_rejected(client: AsyncClient):
    payload = {
        "email": "user@external-corp.org",
        "password": "SuperSecurePassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "DISALLOWED_EMAIL_DOMAIN"


@pytest.mark.asyncio
async def test_duplicate_signup_rejected(client: AsyncClient):
    payload = {
        "name": "Grace Hopper",
        "email": "duplicate@acme.com",
        "password": "SuperSecurePassword123!",
    }
    res1 = await client.post("/api/v1/auth/signup", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/signup", json=payload)
    assert res2.status_code == 409
    error_data = res2.json()
    assert error_data["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient):
    # First signup
    signup_payload = {
        "name": "Linus Torvalds",
        "email": "linus@acme.com",
        "password": "LinuxPassword123!",
    }
    await client.post("/api/v1/auth/signup", json=signup_payload)

    # Then login
    login_payload = {
        "email": "linus@acme.com",
        "password": "LinuxPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Invalid password login
    bad_login = {
        "email": "linus@acme.com",
        "password": "WrongPassword!",
    }
    bad_res = await client.post("/api/v1/auth/login", json=bad_login)
    assert bad_res.status_code == 401
    assert bad_res.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_me_endpoint_requires_auth(client: AsyncClient):
    # Unauthenticated
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401
    assert unauth_res.json()["error"]["code"] == "MISSING_TOKEN"

    # Authenticated
    signup_res = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Margaret Hamilton",
            "email": "margaret@acme.com",
            "password": "ApolloPassword123!",
        },
    )
    token = signup_res.json()["access_token"]

    auth_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_res.status_code == 200
    me_data = auth_res.json()
    assert me_data["user"]["email"] == "margaret@acme.com"
    assert len(me_data["organizations"]) >= 1

