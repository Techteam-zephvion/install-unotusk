import uuid
import httpx

CP_URL = "http://127.0.0.1:28000"
DP_PORT = 28150  # Change if your Data Plane project runs on a different port
DP_URL = f"http://127.0.0.1:{DP_PORT}"


def main():
    with httpx.Client(timeout=60.0) as client:
        # 1. Verify unsigned /projects/sync-servers is now blocked with 401
        r_sync = client.post(f"{CP_URL}/api/v1/projects/sync-servers", json={"servers": []})
        print(f"[1] Unsigned /sync-servers -> HTTP {r_sync.status_code} (Expected: 401)")
        assert r_sync.status_code == 401, f"Expected 401, got {r_sync.text}"

        # 2. Sign up a brand-new user on Control Plane with a NON-password123 password
        test_email = f"verify_{uuid.uuid4().hex[:6]}@acme.com"
        r_auth = client.post(
            f"{CP_URL}/api/v1/auth/signup",
            json={
                "email": test_email,
                "name": "Architecture Verifier",
                "password": "NeverUsePassword123!",
                "organization_name": "Acme Corporation",
                "role": "Admin",
            },
        )
        print(f"[2] Signup with custom password ({test_email}) -> HTTP {r_auth.status_code} (Expected: 201)")
        assert r_auth.status_code in (200, 201), r_auth.text
        jwt_token = r_auth.json()["access_token"]
        headers = {"Authorization": f"Bearer {jwt_token}"}

        # 3. Fetch projects from Control Plane (:28000) and find the Data Plane project
        r_projs = client.get(f"{CP_URL}/api/v1/projects", headers=headers)
        projects = r_projs.json()
        dp_proj = next((p for p in projects if p.get("port") == DP_PORT), None)
        if not dp_proj:
            print(f"No project registered on port {DP_PORT} yet. Open setup_app to sync it first.")
            return
        proj_id = dp_proj["id"]
        proj_slug = dp_proj["slug"]
        print(f"[3] Found Data Plane project on :28000 -> slug='{proj_slug}', id={proj_id}, port={DP_PORT}")

        # 4. THE KEY TEST: Query /ask on Control Plane (:28000) and verify it proxies to :28150!
        # (Before our fix, this returned 400 NO_INDEXED_SNAPSHOT on port 28000!)
        r_ask = client.post(
            f"{CP_URL}/api/v1/projects/{proj_slug}/ask",
            headers=headers,
            json={"question": "What are the main components of this repository?"},
        )
        proxied_hdr = r_ask.headers.get("x-data-plane-proxied")
        target_port_hdr = r_ask.headers.get("x-data-plane-target-port")
        print(
            f"[4] POST :28000/api/v1/projects/{proj_slug}/ask -> HTTP {r_ask.status_code} "
            f"(X-Data-Plane-Proxied={proxied_hdr}, Target-Port={target_port_hdr})"
        )
        assert r_ask.status_code == 200, f"Gateway /ask failed: {r_ask.text}"
        assert proxied_hdr == "true", "Request was not proxied by DataPlaneGatewayMiddleware!"

        # 5. Verify Data Plane slug-bypass & DELETE exploits are blocked on :28150
        r_cross = client.post(
            f"{DP_URL}/api/v1/projects/secret-other-project/ask",
            headers=headers,
            json={"question": "test"},
        )
        print(f"[5] Cross-project slug exploit on :{DP_PORT} -> HTTP {r_cross.status_code} (Expected: 403)")
        assert r_cross.status_code == 403

        r_del = client.delete(f"{DP_URL}/api/v1/projects/{proj_slug}", headers=headers)
        print(f"[6] Root DELETE by slug on :{DP_PORT} -> HTTP {r_del.status_code} (Expected: 403)")
        assert r_del.status_code == 403

        print("\n=== ALL 6 LIVE CONTAINER VERIFICATION CHECKS PASSED! ===")


if __name__ == "__main__":
    main()
