import asyncio
import json
import os
import sys
import httpx

BASE_URL = os.environ.get("SERVER_URL", "http://10.0.0.59:8000")
API_PREFIX = f"{BASE_URL}/api/v1"

async def run_e2e():
    print(f"=== UNOTUSK MVP E2E INTEGRATION TEST ===")
    print(f"Target Server URL: {BASE_URL}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Health Checks
        print("\n[Step 1] Verifying Server Health...")
        h_res = await client.get(f"{BASE_URL}/health")
        assert h_res.status_code == 200, f"Health check failed: {h_res.text}"
        print(f"  /health -> {h_res.json()}")

        r_res = await client.get(f"{BASE_URL}/health/ready")
        assert r_res.status_code == 200, f"Ready check failed: {r_res.text}"
        print(f"  /health/ready -> {r_res.json()}")

        # 2. Authentication: Invalid Login
        print("\n[Step 2] Testing Authentication Failure (Invalid Credentials)...")
        bad_login = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": "nonexistent@unotusk.com", "password": "WrongPassword123!"},
        )
        print(f"  Invalid login status: {bad_login.status_code} (Expected 401)")
        assert bad_login.status_code in (401, 404), f"Expected 401/404 on bad login, got {bad_login.status_code}"

        # 3. Authentication: Signup or Login
        print("\n[Step 3] Registering / Logging in Test User...")
        test_email = "pilot_engineer@unotusk.com"
        test_pass = "SecurePass2026!"
        auth_data = None

        signup_res = await client.post(
            f"{API_PREFIX}/auth/signup",
            json={
                "email": test_email,
                "password": test_pass,
                "name": "Pilot Lead Engineer",
            },
        )
        if signup_res.status_code == 201:
            auth_data = signup_res.json()
            print("  Signup successful!")
        else:
            # Login if user already exists
            login_res = await client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": test_email, "password": test_pass},
            )
            assert login_res.status_code == 200, f"Login failed: {login_res.text}"
            auth_data = login_res.json()
            print("  Login successful!")

        token = auth_data["access_token"]
        assert token and len(token) > 20, "Invalid JWT token returned"
        print(f"  JWT token obtained: {token[:12]}... (type: {auth_data['token_type']})")
        headers = {"Authorization": f"Bearer {token}"}

        # 4. Authenticated /auth/me
        print("\n[Step 4] Calling Authenticated /auth/me...")
        me_res = await client.get(f"{API_PREFIX}/auth/me", headers=headers)
        assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
        me_data = me_res.json()
        print(f"  Current user: {me_data['user']['email']}")
        orgs = me_data.get("organizations", [])
        assert len(orgs) > 0, "User must belong to at least one organization"
        org_id = orgs[0]["id"]
        print(f"  Target Organization: {orgs[0]['name']} (ID: {org_id})")

        # 5. Project Creation / Retrieval
        print("\n[Step 5] Checking and Creating Project...")
        proj_list_res = await client.get(
            f"{API_PREFIX}/projects",
            params={"organization_id": org_id},
            headers=headers,
        )
        assert proj_list_res.status_code == 200, f"List projects failed: {proj_list_res.text}"
        projects = proj_list_res.json()
        project = None
        for p in projects:
            if p["name"] == "Requests Pilot":
                project = p
                break

        if not project:
            create_proj_res = await client.post(
                f"{API_PREFIX}/projects",
                headers=headers,
                json={
                    "name": "Requests Pilot",
                    "description": "Validation project for psf/requests repository",
                    "organization_id": org_id,
                },
            )
            assert create_proj_res.status_code == 201, f"Create project failed: {create_proj_res.text}"
            project = create_proj_res.json()
            print(f"  Created new project: {project['name']} (ID: {project['id']})")
        else:
            print(f"  Found existing project: {project['name']} (ID: {project['id']})")

        project_id = project["id"]

        # 6. Repository Selection (psf/requests)
        print("\n[Step 6] Connecting psf/requests Repository...")
        repo_res = await client.post(
            f"{API_PREFIX}/projects/{project_id}/repositories/select",
            headers=headers,
            json={
                "external_id": "psf/requests",
                "owner": "psf",
                "name": "requests",
                "full_name": "psf/requests",
                "url": "https://github.com/psf/requests.git",
                "default_branch": "main",
                "is_private": False,
            },
        )
        assert repo_res.status_code in (200, 201), f"Select repository failed: {repo_res.text}"
        repo_data = repo_res.json()
        repo_id = repo_data["id"]
        print(f"  Repository selected: {repo_data['full_name']} (ID: {repo_id})")

        # 7. Trigger Ingestion
        print("\n[Step 7] Triggering Ingestion Task...")
        ingest_trigger = await client.post(
            f"{API_PREFIX}/projects/{project_id}/repositories/{repo_id}/ingest",
            headers=headers,
        )
        assert ingest_trigger.status_code == 202, f"Trigger ingest failed: {ingest_trigger.text}"
        ingest_data = ingest_trigger.json()
        snapshot_id = ingest_data["snapshot_id"]
        print(f"  Ingestion queued with snapshot_id: {snapshot_id}")

        # 8. Poll Ingestion Status
        print("\n[Step 8] Monitoring Worker Ingestion Lifecycle (Cloning -> Parsing -> Indexing -> Ready)...")
        max_attempts = 90
        ready = False
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(2)
            st_res = await client.get(
                f"{API_PREFIX}/projects/{project_id}/ingestions/{snapshot_id}",
                headers=headers,
            )
            if st_res.status_code == 200:
                snap = st_res.json()
                status = snap["status"]
                total = snap.get("total_files", 0)
                processed = snap.get("processed_files", 0)
                print(f"  [{attempt}/{max_attempts}] Status: {status} | Processed: {processed}/{total}")
                if status.upper() in ("COMPLETED", "READY"):
                    ready = True
                    break
                elif status.upper() == "FAILED":
                    raise RuntimeError(f"Ingestion failed: {snap.get('error_message')}")

        assert ready, "Ingestion timed out before reaching READY status"
        print("  Ingestion successfully completed! Project is READY.")

        # 9. Trigger and Fetch Proactive Discovery
        print("\n[Step 9] Running Proactive Discovery Pipeline...")
        disc_trigger = await client.post(
            f"{API_PREFIX}/projects/{project_id}/discover",
            headers=headers,
        )
        print(f"  Discovery trigger response: {disc_trigger.status_code}")
        await asyncio.sleep(3)

        findings_res = await client.get(
            f"{API_PREFIX}/projects/{project_id}/findings",
            headers=headers,
        )
        assert findings_res.status_code == 200, f"Fetch findings failed: {findings_res.text}"
        findings = findings_res.json()
        print(f"  Findings discovered: {len(findings)}")
        for i, f in enumerate(findings[:3], 1):
            print(f"    {i}. [{f.get('severity')}] {f.get('title')} ({f.get('category')})")

        # 10. Grounded Ask & Citations Verification
        print("\n[Step 10] Testing Grounded Ask with Exact Repository Evidence...")
        question = "Where is authentication handled in requests?"
        ask_res = await client.post(
            f"{API_PREFIX}/projects/{project_id}/ask",
            headers=headers,
            json={"question": question},
        )
        assert ask_res.status_code == 200, f"Ask failed: {ask_res.text}"
        answer_data = ask_res.json()
        print(f"  Question: {question}")
        print(f"  Confidence: {answer_data.get('confidence')}")
        content = answer_data.get("content", "")
        print(f"  Answer preview: {content[:180]}...")

        evidence_list = answer_data.get("evidence", [])
        print(f"\n[Step 11] Validating Exact Citations & Grounding Evidence ({len(evidence_list)} citations)...")
        assert len(evidence_list) > 0, "Ask response must contain at least one evidence item"

        valid_citations = 0
        for ev in evidence_list:
            fpath = ev.get("file")
            sym = ev.get("symbol")
            lines = ev.get("lines")
            snippet = ev.get("snippet")
            print(f"  - Citation: {fpath} | Symbol: {sym} | Lines: {lines}")
            if snippet:
                first_line = snippet.strip().split("\n")[0]
                print(f"    Snippet: {first_line[:80]}...")
            if fpath and ("auth.py" in fpath or "sessions.py" in fpath or "models.py" in fpath or "adapters.py" in fpath):
                valid_citations += 1

        assert valid_citations > 0, "Evidence citations must point to real repository auth source files (auth.py, sessions.py)"
        print(f"\n>>> ALL {11} E2E PHASES PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    asyncio.run(run_e2e())
