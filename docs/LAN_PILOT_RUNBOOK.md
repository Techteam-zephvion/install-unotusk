# Unotusk MVP — LAN Pilot Operational Runbook

**Audience**: Pilot Test Lead, Systems Engineer, Field Operators  
**Scope**: Real-world Local Area Network (LAN) deployment of Unotusk MVP (1 Linux Server + 4 Windows Clients + 2 macOS Clients).  
**Requirement**: Zero source code inspection required. All tasks executed via CLI scripts or graphical interfaces.

---

## Quick Reference Commands

| Operation | Command | Expected Result |
|---|---|---|
| **Verify LAN Server Health** | `./scripts/verify_lan_connectivity.sh` | `✓ ALL CHECKS PASSED: Server is fully ready` |
| **Clean Server Reset (Preserve Data)** | `./scripts/clean_server_reset.sh` | Rebuilds and restarts API & worker, preserves Postgres/Redis data |
| **Clean Server Reset (Factory Wipe)** | `./scripts/clean_server_reset.sh --wipe-data` | Complete wipe of database and Redis, fresh schema migration |
| **Export Diagnostics Bundle** | `python3 scripts/export_diagnostics.py` | Generates SHA256-verified sanitized `.tar.gz` in `diagnostics/` |
| **Package Linux Client** | `./scripts/package_release.sh` | Builds release archive in `dist/unotusk-employee-linux-x64.tar.gz` |

---

## Step-by-Step Pilot Operational Guide

### Step 1: Linux Server Host Preparation
1. Connect the Linux server laptop to the pilot Wi-Fi or Ethernet switch.
2. Confirm the host has Docker and Docker Compose installed:
   ```bash
   docker compose version
   ```
3. Open a terminal in `/home/devils/PRO/Unotusk-MVP`.

---

### Step 2: Discover Server LAN Address
Run the automated connectivity probe to identify the server's RFC 1918 private IPv4 address:
```bash
./scripts/verify_lan_connectivity.sh
```
Look for the output line:
```
Primary LAN IP Detected: 10.0.0.59 (interface: wlo1)
Connect Employee Apps (Windows/macOS) using this Server URL:
   --> http://10.0.0.59:8000
```
*Note this URL — every employee laptop will connect to this exact address.*

---

### Step 3: Clean Server State Verification
If starting a new test session, perform a clean server reset:
```bash
# To preserve existing test projects and user accounts:
./scripts/clean_server_reset.sh

# To perform a complete factory wipe (fresh database):
./scripts/clean_server_reset.sh --wipe-data
```
> **Safety Guarantee**: The clean reset script strictly targets ONLY the 5 Unotusk MVP containers (`unotusk-api`, `unotusk-worker`, `unotusk-migration`, `unotusk-postgres`, `unotusk-redis`). All other Docker projects on the machine are 100% untouched.

---

### Step 4: Verify Docker Services Status
Confirm all required services are healthy:
```bash
docker compose ps
```
Required state:
- `unotusk-postgres`: `healthy` (Internal port 5432)
- `unotusk-redis`: `healthy` (Internal port 6379)
- `unotusk-api`: `healthy` (Port 8000 exposed to LAN)
- `unotusk-worker`: `Up`

---

### Step 5: Distribute Employee App to Windows Laptops
On the 4 Windows test laptops:
1. Copy `unotusk-employee-windows-x64.zip` from the server's `dist/` directory (via USB drive or local network share).
2. Right-click the ZIP and select **"Extract All..."** to `C:\Unotusk\`.
3. Open the folder and double-click `app.exe`.
4. **SmartScreen Warning**: If Windows displays *"Windows protected your PC"*:
   - Click **"More info"**.
   - Click **"Run anyway"**.
   *(This warning occurs because pilot binaries are unsigned with commercial Microsoft certificates).*

---

### Step 6: Distribute Employee App to macOS Laptops
On the 2 macOS test laptops (Apple Silicon or Intel):
1. Copy `unotusk-employee-macos.tar.gz` from the server's `dist/` directory.
2. Extract the archive:
   ```bash
   tar -xzf unotusk-employee-macos.tar.gz
   ```
3. Drag `app.app` into `/Applications/`.
4. **Gatekeeper Clearance**:
   - Open Terminal and run:
     ```bash
     xattr -cr /Applications/app.app
     ```
   - Alternatively: Right-click `app.app` in Finder -> select **Open** -> click **Open** in the dialog.

---

### Step 7: Connect Employee Clients to the Server
On each of the 6 laptops:
1. Launch the Unotusk Employee Client.
2. On the initial **Server Connection** screen, enter the Server LAN URL from Step 2:
   ```
   http://10.0.0.59:8000
   ```
3. Click **"Connect"**.
4. Verify the green confirmation badge appears:
   ```
   CONNECTED (v0.1.0)
   ```
5. Click **"Continue to Sign In"**.

---

### Step 8: User Login & Session Verification
1. Sign in with the respective assigned employee credentials:
   - Laptop 1: `dev1@acme.com` / `password123`
   - Laptop 2: `dev2@acme.com` / `password123`
   - Laptop 3: `dev3@acme.com` / `password123`
   - Laptop 4: `dev4@acme.com` / `password123`
   - Laptop 5: `qa1@acme.com` / `password123`
   - Laptop 6 (Admin): `lead@acme.com` / `adminpassword123`
2. Confirm the application transitions to the **Projects** dashboard.

---

### Step 9: Workspace Ingestion & Query Pilot
1. From the Admin laptop (`lead@acme.com`), click **"Create Project"**.
2. Enter project details and repository Git URL (or local test repo).
3. Confirm the ingestion progress bar indicates parsing and symbol indexing.
4. On all other 5 laptops, refresh the project list and open the newly created project.
5. In the **"Ask"** tab, submit concurrent architectural questions (e.g. *"What are the primary components in this repository?"*).
6. Verify answers stream back smoothly on each laptop.

---

### Step 10: In-App Client Diagnostic Log Inspection
If any client experiences an issue:
1. Navigate to **Settings** (gear icon in sidebar).
2. Under **Application & Diagnostics**, click **"View Logs"**.
3. Inspect the in-memory circular event buffer (up to 500 events).
4. Click **"Copy All Logs"** to capture the sanitized JSON event stream.
5. Paste into an incident report or support ticket.
   *(All passwords, Bearer tokens, and JWTs are automatically stripped before display and clipboard copy).*

---

### Step 11: Exporting Server Diagnostic Bundle
On the Linux server, generate a consolidated, sanitized support archive:
```bash
python3 scripts/export_diagnostics.py --server-url http://10.0.0.59:8000
```
Output:
```
✓ Diagnostics successfully exported:
  JSON:    diagnostics/unotusk_diagnostics_20260918_170000.json
  Archive: diagnostics/unotusk_diagnostics_20260918_170000.tar.gz
  Size:    14.2 KB
  SHA256:  a1b2c3d4e5...
```
This archive contains host metrics, container states, health probes, and sanitized logs. It contains zero customer proprietary code or credentials.

---

## Troubleshooting & Failure Recovery

### Symptom 1: Client Says "Server Unreachable" / Connection Timed Out
1. **Verify Wi-Fi Network**: Ensure the employee laptop and Linux server are connected to the exact same Wi-Fi SSID or physical switch.
2. **Test Basic Ping from Client**:
   - On Windows: `ping 10.0.0.59`
   - On macOS: `ping -c 3 10.0.0.59`
3. **Router AP Isolation**:
   - If ping fails between two laptops on the same Wi-Fi, the Wi-Fi router has **AP Isolation / Client Isolation** enabled.
   - **Fix**: Disable "AP Isolation" in the router settings, or connect all machines to a dedicated unmanaged network switch or mobile hotspot.

---

### Symptom 2: Port 8000 Blocked by Linux Firewall
If ping succeeds but HTTP fails:
```bash
# Check UFW status on server
sudo ufw status

# If active, allow port 8000
sudo ufw allow 8000/tcp
```

---

### Symptom 3: CORS Error in Client Logs
If client logs show `Disallowed CORS origin`:
1. Check client IP in the error log (e.g. `10.0.0.120`).
2. Verify `./scripts/verify_lan_connectivity.sh` passes the CORS check.
3. Restart API container to reload CORS rules:
   ```bash
   docker stop unotusk-api && docker rm unotusk-api && docker compose up -d --no-deps api
   ```

---

### Symptom 4: Database Connection Errors
If server logs show `DB connection failed`:
1. Check Postgres container health:
   ```bash
   docker inspect --format='{{.State.Health.Status}}' unotusk-postgres
   ```
2. If unhealthy, restart Postgres:
   ```bash
   docker compose restart postgres
   ```

---

### Step 12: Post-Pilot Teardown & Factory Reset
When the pilot concludes:
```bash
# To completely reset the server for the next customer:
./scripts/clean_server_reset.sh --wipe-data

# To stop all containers without wiping data:
docker compose down
```
All resources are safely cleaned up.
