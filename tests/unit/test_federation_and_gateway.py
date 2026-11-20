import json
import time
import uuid

import httpx
import pytest
from starlette.requests import Request
from starlette.responses import Response

from apps.api.src.config.settings import settings
from apps.api.src.core.data_plane_middleware import DataPlaneSecurityMiddleware
from apps.api.src.core.federation import (
    derive_canonical_project_id,
    mint_federation_token,
    sign_cluster_sync_payload,
    verify_cluster_sync_signature,
    verify_federation_token,
)


def test_canonical_uuid_derivation():
    # Deterministic UUIDv5 check
    id1 = derive_canonical_project_id("acme-corporation", "swastha-yoga")
    id2 = derive_canonical_project_id("Acme-Corporation", "Swastha-Yoga")
    assert id1 == id2
    assert isinstance(id1, uuid.UUID)

    # Different org or project produces different UUID
    id3 = derive_canonical_project_id("other-org", "swastha-yoga")
    assert id1 != id3


def test_federation_token_mint_and_verify():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    project_id = derive_canonical_project_id("acme-corporation", "swastha-yoga")

    token = mint_federation_token(
        user_id=user_id,
        email="developer@acme.com",
        name="Developer",
        org_id=org_id,
        project_id=project_id,
        project_slug="swastha-yoga",
        role="ADMIN",
        ttl_seconds=60,
    )
    assert isinstance(token, str)

    # 1. Valid token verification on matching data plane project
    claims = verify_federation_token(token, project_id)
    assert claims is not None
    assert claims["sub"] == str(user_id)
    assert claims["email"] == "developer@acme.com"
    assert claims["role"] == "ADMIN"
    assert claims["project_id"] == str(project_id)
    assert claims["token_use"] == "data_plane_federation"

    # 2. Replay attack against a different project data plane (mismatched aud)
    other_proj_id = uuid.uuid4()
    rejected_claims = verify_federation_token(token, other_proj_id)
    assert rejected_claims is None


def test_cluster_sync_hmac_signing_and_verification():
    payload = {
        "servers": [
            {
                "project_id": str(uuid.uuid4()),
                "name": "swastha-yoga",
                "slug": "swastha-yoga",
                "port": 28150,
                "state": "running",
            }
        ]
    }

    ts, sig, raw_body = sign_cluster_sync_payload(payload)

    # 1. Valid signature
    assert verify_cluster_sync_signature(ts, sig, raw_body) is True

    # 2. Tampered body
    tampered_body = raw_body + b" "
    assert verify_cluster_sync_signature(ts, sig, tampered_body) is False

    # 3. Tampered signature
    assert verify_cluster_sync_signature(ts, sig[:-2] + "00", raw_body) is False

    # 4. Replay attack past skew window (301 seconds old)
    old_ts = str(int(time.time()) - 350)
    old_ts_hdr, old_sig_hdr, _ = sign_cluster_sync_payload(payload, timestamp=int(old_ts))
    assert verify_cluster_sync_signature(old_ts_hdr, old_sig_hdr, raw_body, max_skew_sec=300) is False


@pytest.mark.asyncio
async def test_data_plane_security_middleware_slug_and_boundary_guard():
    canonical_id = derive_canonical_project_id("acme-corporation", "swastha-yoga")

    # Configure settings for a data plane instance
    orig_id = settings.DATA_PLANE_PROJECT_ID
    orig_slug = settings.DATA_PLANE_PROJECT_SLUG
    try:
        settings.DATA_PLANE_PROJECT_ID = str(canonical_id)
        settings.DATA_PLANE_PROJECT_SLUG = "swastha-yoga"

        middleware = DataPlaneSecurityMiddleware(app=None)

        async def dummy_call_next(req: Request) -> Response:
            return Response(content=b'{"status":"ok"}', status_code=200, media_type="application/json")

        def make_request(method: str, path: str) -> Request:
            scope = {
                "type": "http",
                "method": method,
                "path": path,
                "headers": [(b"host", b"localhost")],
            }
            return Request(scope)

        # Vector 1: Permitted canonical UUID route
        r1 = await middleware.dispatch(make_request("POST", f"/api/v1/projects/{canonical_id}/ask"), dummy_call_next)
        assert r1.status_code == 200

        # Vector 2: Permitted project slug route
        r2 = await middleware.dispatch(make_request("POST", "/api/v1/projects/swastha-yoga/ask"), dummy_call_next)
        assert r2.status_code == 200

        # Vector 3: Blocked foreign project UUID
        foreign_uuid = "99999999-9999-9999-9999-999999999999"
        r3 = await middleware.dispatch(make_request("POST", f"/api/v1/projects/{foreign_uuid}/ask"), dummy_call_next)
        assert r3.status_code == 403
        data3 = json.loads(r3.body.decode())
        assert data3["error"]["code"] == "DATA_PLANE_BOUNDARY_VIOLATION"

        # Vector 4: Blocked foreign project slug
        r4 = await middleware.dispatch(make_request("POST", "/api/v1/projects/secret-finance-project/ask"), dummy_call_next)
        assert r4.status_code == 403
        data4 = json.loads(r4.body.decode())
        assert data4["error"]["code"] == "DATA_PLANE_BOUNDARY_VIOLATION"

        # Vector 5: Blocked root DELETE by UUID
        r5 = await middleware.dispatch(make_request("DELETE", f"/api/v1/projects/{canonical_id}"), dummy_call_next)
        assert r5.status_code == 403
        data5 = json.loads(r5.body.decode())
        assert data5["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"

        # Vector 6: Blocked root DELETE by slug
        r6 = await middleware.dispatch(make_request("DELETE", "/api/v1/projects/swastha-yoga"), dummy_call_next)
        assert r6.status_code == 403
        data6 = json.loads(r6.body.decode())
        assert data6["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"

        # Vector 7: Blocked root DELETE foreign slug
        r7 = await middleware.dispatch(make_request("DELETE", "/api/v1/projects/secret-finance-project"), dummy_call_next)
        assert r7.status_code == 403

        # Vector 8: Permitted subresource DELETE on valid project
        r8 = await middleware.dispatch(make_request("DELETE", f"/api/v1/projects/{canonical_id}/conversations/123"), dummy_call_next)
        assert r8.status_code == 200

        # Vector 9: Blocked control plane route /sync-servers
        r9 = await middleware.dispatch(make_request("POST", "/api/v1/projects/sync-servers"), dummy_call_next)
        assert r9.status_code == 403
        data9 = json.loads(r9.body.decode())
        assert data9["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"

        # Vector 10: Blocked control plane route /auth/signup
        r10 = await middleware.dispatch(make_request("POST", "/api/v1/auth/signup"), dummy_call_next)
        assert r10.status_code == 403
        data10 = json.loads(r10.body.decode())
        assert data10["error"]["code"] == "CONTROL_PLANE_OPERATION_PROHIBITED"

    finally:
        settings.DATA_PLANE_PROJECT_ID = orig_id
        settings.DATA_PLANE_PROJECT_SLUG = orig_slug


@pytest.mark.asyncio
async def test_data_plane_gateway_middleware(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    from apps.api.src.auth.security import create_access_token
    from apps.api.src.core.data_plane_gateway import DataPlaneGatewayMiddleware
    from apps.api.src.models.enums import MembershipRole
    from apps.api.src.models.membership import OrganizationMembership
    from apps.api.src.models.project import Project
    from apps.api.src.models.user import User

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()

    mock_user = User(id=user_id, email="dev@acme.com", name="Dev", password_hash="")
    mock_project = Project(
        id=project_id,
        organization_id=org_id,
        name="swastha-yoga",
        slug="swastha-yoga",
        port=29999,  # Offline port to test 503
    )
    mock_org_mem = OrganizationMembership(
        organization_id=org_id,
        user_id=user_id,
        role=MembershipRole.OWNER,
    )

    middleware = DataPlaneGatewayMiddleware(app=None)

    async def dummy_call_next(req: Request) -> Response:
        return Response(content=b'{"status":"pass_through"}', status_code=200)

    # 1. Non-data-plane subpath passes through to standard router
    req_pass = Request({
        "type": "http",
        "method": "GET",
        "path": f"/api/v1/projects/{project_id}/nonexistent_subpath",
        "headers": [(b"host", b"localhost")],
    })
    resp_pass = await middleware.dispatch(req_pass, dummy_call_next)
    assert resp_pass.status_code == 200
    assert json.loads(resp_pass.body.decode())["status"] == "pass_through"

    # Mock DB session in gateway
    class FakeSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def get(self, model, ident):
            if model == Project and ident == project_id:
                return mock_project
            if model == User and ident == user_id:
                return mock_user
            return None
        async def execute(self, stmt):
            m = MagicMock()
            m.scalar_one_or_none.return_value = mock_org_mem
            return m

    monkeypatch.setattr("apps.api.src.core.data_plane_gateway.AsyncSessionLocal", lambda: FakeSession())
    monkeypatch.setattr("apps.api.src.services.project_service.ProjectService.resolve_project_id", AsyncMock(return_value=project_id))

    # 2. Missing token -> 401
    req_no_auth = Request({
        "type": "http",
        "method": "POST",
        "path": f"/api/v1/projects/{project_id}/ask",
        "headers": [(b"host", b"localhost")],
        "query_string": b"",
    })
    resp_no_auth = await middleware.dispatch(req_no_auth, dummy_call_next)
    assert resp_no_auth.status_code == 401
    assert json.loads(resp_no_auth.body.decode())["error"]["code"] == "MISSING_TOKEN"

    async def dummy_receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    # 3. Valid token, but data plane container offline -> 503 DATA_PLANE_UNREACHABLE
    token = create_access_token(user_id)
    req_with_auth = Request(
        {
            "type": "http",
            "method": "POST",
            "path": f"/api/v1/projects/{project_id}/ask",
            "headers": [
                (b"host", b"localhost"),
                (b"authorization", f"Bearer {token}".encode()),
            ],
            "query_string": b"",
        },
        receive=dummy_receive,
    )
    resp_unreachable = await middleware.dispatch(req_with_auth, dummy_call_next)
    assert resp_unreachable.status_code == 503
    assert json.loads(resp_unreachable.body.decode())["error"]["code"] == "DATA_PLANE_UNREACHABLE"

    # 4. Successful proxy when data plane container returns 200
    mock_dp_resp = httpx.Response(
        200,
        content=b'{"answer":"Federated answer from data plane"}',
        headers={"content-type": "application/json"},
    )

    async def mock_client_request(self, *args, **kwargs):
        # Verify the outgoing request contains X-Unotusk-Federation-Token
        assert "X-Unotusk-Federation-Token" in kwargs.get("headers", {})
        return mock_dp_resp

    monkeypatch.setattr("httpx.AsyncClient.request", mock_client_request)

    resp_proxied = await middleware.dispatch(req_with_auth, dummy_call_next)
    assert resp_proxied.status_code == 200
    assert resp_proxied.headers.get("X-Data-Plane-Proxied") == "true"
    assert resp_proxied.headers.get("X-Data-Plane-Target-Port") == "29999"
    assert json.loads(resp_proxied.body.decode())["answer"] == "Federated answer from data plane"


@pytest.mark.asyncio
async def test_jit_identity_upsert_handles_organization_slug_and_memberships():
    from unittest.mock import MagicMock

    from apps.api.src.api.dependencies.auth import get_current_user
    from apps.api.src.models.enums import MembershipRole
    from apps.api.src.models.membership import OrganizationMembership, ProjectMembership
    from apps.api.src.models.organization import Organization
    from apps.api.src.models.project import Project
    from apps.api.src.models.user import User

    user_id = uuid.uuid4()
    org_cp_id = uuid.uuid4()
    org_dp_id = uuid.uuid4()
    proj_id = derive_canonical_project_id("acme-corporation", "swastha-yoga")

    # Local Data Plane existing Org & Project
    local_org = Organization(id=org_dp_id, name="Acme Corporation", slug="acme-corporation")
    local_proj = Project(id=proj_id, organization_id=org_dp_id, name="swastha-yoga", slug="swastha-yoga")

    added_objects = []

    class MockDataPlaneSession:
        def __init__(self):
            self.user = None
            self.org = local_org
            self.proj = local_proj
            self.om = None
            self.pm = None

        async def get(self, model, ident):
            if model == User and ident == user_id:
                return self.user
            if model == Project and ident == proj_id:
                return self.proj
            if model == Organization and ident == self.org.id:
                return self.org
            return None

        async def execute(self, stmt):
            m = MagicMock()
            # If querying Organization by slug
            sql_str = str(stmt)
            if "organizations.slug" in sql_str:
                m.scalar_one_or_none.return_value = self.org
            elif "organization_memberships" in sql_str:
                m.scalar_one_or_none.return_value = self.om
            elif "project_memberships" in sql_str:
                m.scalar_one_or_none.return_value = self.pm
            elif "users.email" in sql_str:
                m.scalar_one_or_none.return_value = self.user
            else:
                m.scalar_one_or_none.return_value = None
            return m

        def add(self, obj):
            added_objects.append(obj)
            if isinstance(obj, User):
                self.user = obj
            elif isinstance(obj, OrganizationMembership):
                self.om = obj
            elif isinstance(obj, ProjectMembership):
                self.pm = obj

        async def flush(self):
            pass

        async def commit(self):
            pass

    orig_id = settings.DATA_PLANE_PROJECT_ID
    orig_slug = settings.DATA_PLANE_PROJECT_SLUG
    try:
        settings.DATA_PLANE_PROJECT_ID = str(proj_id)
        settings.DATA_PLANE_PROJECT_SLUG = "swastha-yoga"

        fed_token = mint_federation_token(
            user_id=user_id,
            email="dev@acme.com",
            name="Dev",
            org_id=org_cp_id,  # Different Control Plane Org ID!
            project_id=proj_id,
            project_slug="swastha-yoga",
            role="ADMIN",
        )

        req = Request({
            "type": "http",
            "method": "POST",
            "path": f"/api/v1/projects/{proj_id}/ask",
            "headers": [
                (b"host", b"localhost"),
                (b"x-unotusk-federation-token", fed_token.encode()),
            ],
        })

        session = MockDataPlaneSession()
        user = await get_current_user(request=req, credentials=None, db=session)

        assert user.id == user_id
        assert user.email == "dev@acme.com"

        # Verify OrganizationMembership was created and bound to the local Org ID
        assert session.om is not None
        assert session.om.organization_id == org_dp_id
        assert session.om.user_id == user_id
        assert session.om.role == MembershipRole.ADMIN

        # Verify ProjectMembership was created
        assert session.pm is not None
        assert session.pm.project_id == proj_id
        assert session.pm.user_id == user_id
        assert session.pm.role == MembershipRole.ADMIN

        # Verify no duplicate Organization was added
        added_orgs = [o for o in added_objects if isinstance(o, Organization)]
        assert len(added_orgs) == 0

    finally:
        settings.DATA_PLANE_PROJECT_ID = orig_id
        settings.DATA_PLANE_PROJECT_SLUG = orig_slug

