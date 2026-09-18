# Unotusk MVP — Multi-Client LAN Pilot Test Matrix

## 1. Pilot Architecture Overview

This document specifies the test topology, device assignments, and multi-client test verification protocols for a real on-premise Local Area Network (LAN) deployment of Unotusk MVP.

```
                                  ==============================
                                  Local Area Network (Wi-Fi/LAN)
                                    Subnet: 10.0.0.0/24 (RFC 1918)
                                  ==============================
                                                |
              ┌─────────────────────────────────┼─────────────────────────────────┐
              |                                 |                                 |
              v                                 v                                 v
   ┌──────────────────────┐          ┌──────────────────────┐          ┌──────────────────────┐
   │    Node 1: SERVER    │          │  Nodes 2-5: WINDOWS  │          │   Nodes 6-7: MACOS   │
   │  Linux x64 Host      │          │  4 x Windows Laptops │          │   2 x macOS Laptops  │
   │  IP: 10.0.0.59       │          │  (Win 10/11 x64)     │          │  (Apple Silicon + x64)
   │                      │          │                      │          │                      │
   │  Docker Services:    │◄─────────┤  Employee App Client ├─────────►│  Employee App Client │
   │  - unotusk-api (8000)│ (HTTP/1.1) (Desktop Bundle)     │ (HTTP/1.1) (Desktop Bundle)     │
   │  - unotusk-worker    │          └──────────────────────┘          └──────────────────────┘
   │  - unotusk-postgres  │
   │  - unotusk-redis     │
   └──────────────────────┘
```

---

## 2. Hardware & Device Matrix

| Node ID | Role | Device Type | OS & Architecture | Network Address | Client Software | Assigned User |
|---|---|---|---|---|---|---|
| **SRV-01** | Unotusk Server | Laptop / Mini PC | Linux x86_64 (Pop!_OS / Ubuntu 22.04+) | Static/Reserved DHCP: `10.0.0.59` | Docker Compose Stack (API, Worker, DB, Redis) | System Admin |
| **WIN-01** | Employee Client | Laptop | Windows 11 64-bit (x64) | DHCP: `10.0.0.101` | `unotusk-employee-windows-x64.zip` | `dev1@acme.com` (Member) |
| **WIN-02** | Employee Client | Laptop | Windows 11 64-bit (x64) | DHCP: `10.0.0.102` | `unotusk-employee-windows-x64.zip` | `dev2@acme.com` (Member) |
| **WIN-03** | Employee Client | Laptop | Windows 10 64-bit (x64) | DHCP: `10.0.0.103` | `unotusk-employee-windows-x64.zip` | `qa1@acme.com` (Member) |
| **WIN-04** | Employee Client (Admin) | Laptop | Windows 11 64-bit (x64) | DHCP: `10.0.0.104` | `unotusk-employee-windows-x64.zip` | `lead@acme.com` (Admin) |
| **MAC-01** | Employee Client | MacBook Air/Pro | macOS 14+ (Apple Silicon M1/M2/M3) | DHCP: `10.0.0.105` | `unotusk-employee-macos.tar.gz` | `dev3@acme.com` (Member) |
| **MAC-02** | Employee Client | MacBook Pro | macOS 13+ (Intel x64 or Apple Silicon) | DHCP: `10.0.0.106` | `unotusk-employee-macos.tar.gz` | `dev4@acme.com` (Member) |

---

## 3. Network Isolation & Security Guarantees

1. **RFC 1918 Private Addressing**:
   All communication remains internal to the corporate subnet (`10.0.0.0/8`, `172.16.0.0/12`, or `192.168.0.0/16`). No external traffic or ports are exposed to the WAN.
2. **Exposed Port Boundary**:
   **ONLY Port 8000** (`unotusk-api`) is bound to `0.0.0.0:8000`.
   `unotusk-postgres` (5432) and `unotusk-redis` (6379) are bound exclusively to the private Docker bridge network (`unotusk-network`) and are inaccessible from any laptop on the LAN.
3. **CORS LAN Whitelisting**:
   API strictly accepts LAN HTTP origins matching `r"^https?://(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|localhost|127\.0\.0\.1)(:\d+)?$"`.
4. **Zero-Secret Logging**:
   Both server and employee app enforce continuous regex redaction on tokens, JWTs, passwords, and database credentials.

---

## 4. Test Phases & Execution Protocols

### Phase 1: Server Preflight & Network Validation
- **Objective**: Confirm server health and LAN reachability before launching client apps.
- **Commands on Linux Server**:
  ```bash
  # 1. Verify clean container status
  docker compose ps
  
  # 2. Run preflight connectivity probe
  ./scripts/verify_lan_connectivity.sh
  ```
- **Pass Criteria**:
  - `[PASS] Primary LAN IP Detected`
  - `[PASS] Port 8000 is Listening`
  - `[PASS] HTTP GET .../health -> 200 OK`
  - `[PASS] HTTP GET .../health/ready -> 200 OK`
  - `[PASS] CORS Preflight OPTIONS accepted`

---

### Phase 2: Multi-OS Client Distribution & Installation
- **Windows Laptops (WIN-01 to WIN-04)**:
  1. Transfer `dist/unotusk-employee-windows-x64.zip` via local shared drive or USB.
  2. Verify SHA256 checksum: `certutil -hashfile unotusk-employee-windows-x64.zip SHA256`.
  3. Extract to `C:\Unotusk\`.
  4. Launch `app.exe`.
  5. Windows SmartScreen warning: Click **"More info" -> "Run anyway"** (normal for internal pilot builds).
- **macOS Laptops (MAC-01, MAC-02)**:
  1. Transfer `dist/unotusk-employee-macos.tar.gz`.
  2. Verify SHA256 checksum: `shasum -a 256 unotusk-employee-macos.tar.gz`.
  3. Extract and drag `app.app` to `/Applications/`.
  4. Terminal clearance: `xattr -cr /Applications/app.app` (or Right-click -> Open).
  5. Launch application.

---

### Phase 3: Server Discovery & Multi-Client Connection
- **Action**: On all 6 employee laptops simultaneously:
  1. Launch Unotusk Employee App.
  2. Observe Server Connection screen.
  3. Enter Server URL: `http://10.0.0.59:8000` (or detected LAN IP).
  4. Click **"Connect"**.
- **Pass Criteria**:
  - Green status badge: `CONNECTED (v0.1.0)`.
  - Button transitions to `"Continue to Sign In"`.
  - Response time < 100ms across all 6 devices.

---

### Phase 4: Concurrent User Authentication & Session Management
- **Action**:
  1. Authenticate users `dev1@acme.com` through `dev4@acme.com`, `qa1@acme.com`, and `lead@acme.com` across all 6 laptops within a 60-second window.
  2. Verify token storage in secure local storage.
  3. Close and relaunch the app on `WIN-01` and `MAC-01` to test silent session restoration.
- **Pass Criteria**:
  - All 6 logins succeed (HTTP 200 with JWT HS256).
  - Relaunched apps restore session immediately without prompting for re-login (`SESSION_RESTORED` logged).

---

### Phase 5: Simultaneous Workspace Ingestion & Querying
- **Action**:
  1. `lead@acme.com` (WIN-04) creates a test project with Git repository.
  2. Background worker processes AST parsing, symbol extraction, and discovery cards.
  3. All 6 clients open the project overview, file tree, and discoveries tab.
  4. 3 clients simultaneously submit queries in the "Ask" tab.
- **Pass Criteria**:
  - File tree and discovery cards load cleanly across all 6 clients without timeouts.
  - Server metrics show zero connection pool exhaustion.
  - LLM / intelligence worker streams responses back to respective clients without cross-talk.

---

### Phase 6: Diagnostic Verification & Log Auditing
- **Action**:
  1. On WIN-01: Click **Settings -> View Logs**. Verify client event stream:
     - `SERVER_CONNECTION_SUCCESS`, `LOGIN_SUCCESS`, `SESSION_RESTORED`, `PROJECT_LOAD_SUCCESS`.
     - Verify no passwords, tokens, or JWTs appear in cleartext.
  2. On Linux Server: Export diagnostic bundle:
     ```bash
     python3 scripts/export_diagnostics.py --server-url http://10.0.0.59:8000
     ```
  3. Inspect the exported JSON and server logs (`docker compose logs api`).
- **Pass Criteria**:
  - Every HTTP request has an `X-Request-ID` and client LAN IP.
  - Zero plaintext secrets in server logs or diagnostic archive.
  - Checksum generated and valid.

---

## 5. Pilot Sign-Off Checklist

| Test ID | Description | Target Nodes | Expected Result | Pass / Fail | Verified By |
|---|---|---|---|---|---|
| **CHK-LAN-01** | Linux host RFC 1918 LAN IP detection | SRV-01 | Primary private IP detected on Wi-Fi/Eth adapter | [ ] PASS | |
| **CHK-LAN-02** | Internal container port isolation | SRV-01 | Only 8000 published; DB 5432 and Redis 6379 are null | [ ] PASS | |
| **CHK-LAN-03** | Server preflight probe execution | SRV-01 | All 5 checks pass in `./scripts/verify_lan_connectivity.sh` | [ ] PASS | |
| **CHK-LAN-04** | Windows client packaging & extraction | WIN-01..04 | Zip extracts and runs cleanly on Windows 10 & 11 | [ ] PASS | |
| **CHK-LAN-05** | macOS client packaging & Gatekeeper | MAC-01..02 | App opens on Apple Silicon and Intel macOS | [ ] PASS | |
| **CHK-LAN-06** | 6-client simultaneous connection | All Clients | All 6 clients display green `CONNECTED` status | [ ] PASS | |
| **CHK-LAN-07** | Concurrent user authentication | All Clients | 6 unique employee logins succeed simultaneously | [ ] PASS | |
| **CHK-LAN-08** | Client log viewer & secrets check | WIN-01, MAC-01 | Logs modal renders, copy button works, secrets redacted | [ ] PASS | |
| **CHK-LAN-09** | Diagnostic bundle export | SRV-01 | Valid SHA256 `.tar.gz` bundle produced with zero secrets | [ ] PASS | |
| **CHK-LAN-10** | Clean server reset verification | SRV-01 | Server reset script resets without harming other projects | [ ] PASS | |
