import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

# Ensure repo root is on sys.path
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

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


async def main():
    print("=== RUNNING CONTROL PLANE <-> DATA PLANE ARCHITECTURE VERIFICATION ===")

    # 1. Canonical Project UUID ('acme-corp:swastha-yoga')
    canonical_id = derive_canonical_project_id("acme-corp", "swastha-yoga")
    print(f"1. Canonical Project UUID ('acme-corp:swastha-yoga'): {canonical_id}")

    orig_id = settings.DATA_PLANE_PROJECT_ID
    orig_slug = settings.DATA_PLANE_PROJECT_SLUG
    try:
        settings.DATA_PLANE_PROJECT_ID = str(canonical_id)
        settings.DATA_PLANE_PROJECT_SLUG = "swastha-yoga"

        middleware = DataPlaneSecurityMiddleware(app=None)

        async def dummy_call_next(req: Request) -> Response:
            return Response(content=b'{"status":"ok"}', status_code=200, media_type="application/json")

        def make_req(method: str, path: str) -> Request:
            return Request({
                "type": "http",
                "method": method,
                "path": path,
                "headers": [(b"host", b"localhost")],
            })

        # Test Vectors
        test_cases = [
            ("POST", f"/api/v1/projects/{canonical_id}/ask", 200),
            ("POST", "/api/v1/projects/swastha-yoga/ask", 200),
            ("POST", "/api/v1/projects/99999999-9999-9999-9999-999999999999/ask", 403),
            ("POST", "/api/v1/projects/secret-finance-project/ask", 403),
            ("DELETE", f"/api/v1/projects/{canonical_id}", 403),
            ("DELETE", "/api/v1/projects/swastha-yoga", 403),
            ("DELETE", "/api/v1/projects/secret-finance-project", 403),
            ("DELETE", f"/api/v1/projects/{canonical_id}/conversations/123", 200),
            ("POST", "/api/v1/projects/sync-servers", 403),
            ("POST", "/api/v1/auth/signup", 403),
        ]

        for method, path, expected_status in test_cases:
            resp = await middleware.dispatch(make_req(method, path), dummy_call_next)
            assert resp.status_code == expected_status, f"Expected {expected_status} on {method} {path}, got {resp.status_code}"
            # Truncate long UUIDs for neat printing
            display_path = path.replace(str(canonical_id), f"{str(canonical_id)[:8]}-...-{str(canonical_id)[-12:]}")
            display_path = display_path.replace("99999999-9999-9999-9999-999999999999", "99999999-...-555555555555")
            print(f"   [PASS] Guard({method:6} {display_path:60}) -> {resp.status_code}")

        # 2. Federation Token verified
        user_id = uuid.uuid4()
        org_id = uuid.uuid4()
        fed_token = mint_federation_token(
            user_id=user_id,
            email="dhanush@acme.com",
            name="Dhanush",
            org_id=org_id,
            project_id=canonical_id,
            project_slug="swastha-yoga",
            role="ADMIN",
        )
        claims = verify_federation_token(fed_token, canonical_id)
        assert claims is not None and claims["email"] == "dhanush@acme.com" and claims["role"] == "ADMIN"
        print(f"2. [PASS] Federation Token verified for dhanush@acme.com on swastha-yoga (role=ADMIN)")

        # 3. Cross-project token replay rejected via strict `aud` claim binding
        foreign_id = uuid.uuid4()
        rejected = verify_federation_token(fed_token, foreign_id)
        assert rejected is None
        print("3. [PASS] Cross-project token replay rejected via strict `aud` claim binding")

        # 4. HMAC-SHA256 signed /projects/sync-servers verified (tamper & replay safe)
        sync_payload = {
            "servers": [{
                "project_id": str(canonical_id),
                "name": "swastha-yoga",
                "slug": "swastha-yoga",
                "port": 28150,
                "state": "running",
            }]
        }
        ts, sig, raw_body = sign_cluster_sync_payload(sync_payload)
        assert verify_cluster_sync_signature(ts, sig, raw_body) is True
        assert verify_cluster_sync_signature(ts, sig, raw_body + b"tampered") is False
        assert verify_cluster_sync_signature(str(int(time.time()) - 400), sig, raw_body) is False
        print("4. [PASS] HMAC-SHA256 signed /projects/sync-servers verified (tamper & replay safe)")

        print("=== ALL VERIFICATION TESTS PASSED 100% ===")

    finally:
        settings.DATA_PLANE_PROJECT_ID = orig_id
        settings.DATA_PLANE_PROJECT_SLUG = orig_slug


if __name__ == "__main__":
    asyncio.run(main())
