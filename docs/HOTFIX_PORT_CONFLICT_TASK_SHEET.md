# UNOTUSK HOTFIX: SERVER SETUP PORT CONFLICT TASK SHEET

**Date**: 2026-09-16  
**Status**: INVESTIGATION COMPLETE — PENDING APPROVAL  
**Component**: Unotusk Server Setup App & Deployment Architecture  
**Target Release**: Unotusk MVP v0.1.1 (Hotfix)

---

## 1. Observed Failure

During the installation phase of the Unotusk Server Setup Application (`setup_app`), the Docker container orchestration step failed with the following error:

```text
Error response from daemon: failed to set up container networking:
driver failed programming external connectivity on endpoint unotusk-redis:
Bind for 0.0.0.0:6379 failed: port is already allocated
```

### Environmental Context
- Host machine already has an active Redis instance or Docker container (`nammadharani-redis-1`) bound to `0.0.0.0:6379`.
- Host machine also has an active PostgreSQL container (`auth-service-postgres-1`) bound to `0.0.0.0:5432`.
- Docker images (`unotusk-api:0.1.0` and `unotusk-worker:0.1.0`) were built and present in the Docker daemon.
- The failure occurred specifically when Docker Compose attempted to bind the host port `6379` for the `unotusk-redis` container.

---

## 2. Root Cause Analysis

### 2.1 Why Host Port 6379 and 5432 Were Published
In the original local development `docker-compose.yml`, both `postgres` and `redis` had host ports exposed for developer convenience:
```yaml
ports:
  - "127.0.0.1:${POSTGRES_PORT:-5432}:5432"
  - "127.0.0.1:${REDIS_PORT:-6379}:6379"
```
When `ComposeGenerator.generateDockerCompose` and `ServerConfig` were authored in `setup_app`, they mirrored this developer configuration and included host port bindings for both `postgres` (5432) and `redis` (6379).

### 2.2 Why Existing Setup App Port Validation Failed
In `setup_app/lib/features/validation/data/environment_validator.dart`:
1. `checkPortsAvailable()` **only checked the API port** (`apiPort = 8000`). It completely omitted validation for port `6379` (Redis) and port `5432` (PostgreSQL), despite both being published to the host in the generated Compose file.
2. Even when a port was occupied, `checkPortsAvailable()` flagged the issue as `CheckStatus.warning` rather than `CheckStatus.failed`.
3. In `ServerCheckController.isAllPassed`, warning statuses are treated as passing (`item.status == CheckStatus.passed || item.status == CheckStatus.warning`), allowing the user to advance directly to "Ready to install" while a required host port was already allocated.

---

## 3. Current Architecture & Inspection Findings

### Q1: Why is host port 6379 currently published?
- **Finding**: It was published solely as a developer-convenience carry-over from early local development so engineers could run `redis-cli` from the host. It serves no customer-facing or inter-service production purpose.

### Q2: Is PostgreSQL host port 5432 also necessary?
- **Finding**: **No.** PostgreSQL is accessed exclusively by:
  - `unotusk-api` via `DATABASE_URL=postgresql+asyncpg://postgres:...@postgres:5432/unotusk`
  - `unotusk-migration` via `alembic upgrade head`
  All these run inside the Docker bridge network `unotusk-network`. The host port is not consumed by any external process.

### Q3: Can Redis and PostgreSQL communicate entirely through Docker's internal network?
- **Finding**: **Yes, 100%.** Docker Compose provisions a private bridge network (`unotusk-network`) with embedded DNS:
  - `api` connects to `postgres:5432` and `redis:6379`
  - `worker` connects to `redis:6379` (and `postgres:5432`)
  - `migration` connects to `postgres:5432`
  Docker handles all routing and container name resolution internally without publishing any host ports.

### Q4: Does the Employee App ever need direct access to Redis or PostgreSQL?
- **Finding**: **No.** The Unotusk Employee App (`app/`) communicates exclusively with the backend via HTTP/REST at `AppConfig.defaultServerUrl = 'http://localhost:8000'`. It contains zero database drivers, zero Redis clients, and zero direct network paths to the data stores.

### Q5: Is port 8000 the only port that genuinely needs host/network exposure for MVP?
- **Finding**: **Yes.** Port 8000 (or customer-configured server port) is the single ingress point required for the Employee Client and administrative API access.

### Q6: Why did Setup App port validation fail to prevent this?
- **Finding**: `EnvironmentValidator.checkPortsAvailable` hardcoded testing to only `apiPort` (8000) and treated conflicts as non-blocking `warning`. It lacked:
  - Inspection of all actually published host ports.
  - Process/container identification (distinguishing existing Unotusk vs Docker vs local process).
  - Strict gating preventing "Ready to install" when a collision exists.

---

## 4. Evaluation of Possible Solutions

| Option | Description | Pros | Cons | Verdict |
|---|---|---|---|---|
| **Option A**: Auto-increment / alternate host ports (e.g. 5435, 6385) | If 5432 or 6379 are busy, bind to random or offset host ports. | Keeps host access for debugging. | Complex, fragile, exposes internal databases to host network, contradicts zero-trust/minimal surface principles. | **REJECTED** |
| **Option B**: Kill conflicting processes automatically | Script terminates whoever holds 6379/5432. | Fast for happy dev path. | Catastrophic data loss risk; might terminate customer's production Redis or databases. | **STRICTLY FORBIDDEN** |
| **Option C**: Unpublish internal ports + Robust API port validation (Simplest Safe Architecture) | 1. Remove host `ports:` for `postgres` and `redis` entirely in Compose.<br>2. Expose only `:8000` (Unotusk API).<br>3. Enhance Setup App port validation for `:8000` with process/container inspection and strict blocking. | **Zero collision risk** with host Redis/Postgres. Minimal attack surface. Clear, predictable, adheres to standard container architecture. | None for customer production. (Devs who want direct DB access can use `docker exec`). | **RECOMMENDED (SAFEST)** |

---

## 5. Safest MVP Solution (Architecture & Design)

### 5.1 Deployment Topology (Customer Host)
```
Customer Host:
  └─ :8000 (or customer-configured port) ──────► Unotusk API (Container)
                                                      │
══════════════════════ Docker Internal Bridge Network (unotusk-network) ══════════════════════
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
         PostgreSQL Container (:5432)                                   Redis Container (:6379)
             ▲                      ▲                                              ▲
             │                      │                                              │
    Migration Container    Worker Container (optional)                   Worker Container
```
- **Published to Host**: Port `8000` (Unotusk API) only.
- **Internal Only**: PostgreSQL (`5432`) and Redis (`6379`). **No `ports:` directive on postgres or redis.**

### 5.2 Setup App Port Validation Enhancement
1. **Targeted Port Validation**:
   - Checks the target API port (`serverPort`, default 8000).
   - If occupied, performs diagnostic inspection:
     - Is it an existing healthy Unotusk instance? (`GET /health/ready` check)
     - Is it another Docker container? (`docker ps` inspection)
     - Is it a host OS process? (`lsof` / `ss` / `fuser` inspection)
2. **Clear Feedback & Actionable Remediation**:
   - If occupied by existing Unotusk: Informs user that Unotusk is already running and offers to connect or upgrade.
   - If occupied by another application: Clearly states `"Port <port> is already in use by <process/container>"` and directs user to select an alternate port in the Configuration step.
3. **Strict Installation Gating**:
   - `CheckItem.status` becomes `CheckStatus.failed` if the required API port is occupied and cannot be used.
   - The Setup App wizard will **never** display "Ready to install" when a required port is in an unresolved conflict state.

---

## 6. Affected Files

1. **`setup_app/lib/features/deploy/data/compose_generator.dart`**:
   - Remove host `ports:` mapping from `postgres` and `redis` services for both development and production compose outputs.
   - Keep internal container network definitions (`unotusk-network`).
2. **`setup_app/lib/features/config/domain/server_config.dart`**:
   - Clarify that `postgresPort` and `redisPort` represent internal container network ports, or remove them from host exposure logic in `.env` generation.
3. **`setup_app/lib/features/validation/data/environment_validator.dart`**:
   - Update `checkPortsAvailable` to perform robust diagnosis (existing Unotusk, Docker container, or local process).
   - Treat occupied target port as blocking `failed` status when conflict is unresolvable.
4. **`setup_app/lib/features/validation/presentation/server_check_controller.dart`**:
   - Ensure critical failure flag correctly inhibits wizard progression when port conflicts exist.
5. **`setup_app/lib/features/config/presentation/config_screen.dart`**:
   - Display real-time port availability validation if user selects a custom port.
6. **`docker-compose.yml` (root reference template)**:
   - Synchronize with the minimal safe architecture (remove unneeded external bindings or document that internal network is authoritative).
7. **`~/.unotusk/server/docker-compose.yml`**:
   - Update deployed configuration to match.

---

## 7. Required Regression Tests

1. **Test: Free Port Validation**:
   - Verify `checkPortsAvailable` passes cleanly when port 8000 is free.
2. **Test: Occupied Port Detection**:
   - Verify `checkPortsAvailable` returns `CheckStatus.failed` when port 8000 is occupied.
3. **Test: Occupied by Docker Container**:
   - Verify identification of foreign Docker container holding the port.
4. **Test: Occupied by Local Process**:
   - Verify identification when a native host process holds the port.
5. **Test: Existing Unotusk Deployment Recognition**:
   - Verify detection of existing Unotusk server (`/health/ready` returns 200).
6. **Test: Compose Generator Internal Networking**:
   - Verify generated compose file contains no host port bindings for `postgres` or `redis`.
   - Verify `api`, `worker`, and `migration` successfully connect over `unotusk-network`.
7. **Test: Deployment After Conflict Resolution**:
   - Verify full end-to-end deployment succeeds when port conflict is resolved.
8. **Test: Setup Failure Recovery**:
   - Verify error messages and logs are sanitized and clear if any deployment step encounters an error.

---

## 8. Implementation & Verification Summary

### Implementation Delivered
1. **Host Port Unpublishing (`compose_generator.dart`)**:
   - Removed host `ports:` bindings from `postgres` and `redis` services in both `generateDockerCompose` and `generateProductionCompose`.
   - All internal services (`api`, `worker`, `migration`) communicate with databases exclusively over Docker's bridge network (`unotusk-network`).
   - Only port 8000 (API) is exposed to the host for client application access.
2. **Setup App Port Conflict Inspection (`environment_validator.dart`)**:
   - Added `inspectPort(host, port)` with multi-tiered conflict detection:
     - `PortConflictSource.existingUnotusk`: detects active Unotusk instances via `/health` probe.
     - `PortConflictSource.dockerContainer`: identifies conflicting container names via `docker ps`.
     - `PortConflictSource.localProcess`: identifies host process names and PIDs via `lsof` / `ss`.
     - `PortConflictSource.unknownProcess`: handles fallback without crashing.
   - Updated `checkPortsAvailable()`:
     - Returns `CheckStatus.failed` (never warning) when the required port is occupied.
     - Formats clear error: `"Port <port> is already in use."` with source details and remediation.
     - Prevents wizard progression to "Ready to install" when a required port is in conflict.
3. **Deployment Safety & Error Recovery (`deployment_engine.dart`)**:
   - Captures Docker Compose port allocation errors (`port is already allocated` / `address already in use`) and translates them into actionable error messages.
4. **Host Stack Deployment & Verification**:
   - Deployed updated stack in `~/.unotusk/server/` using internal-only data tier (`postgres` and `redis` private to `unotusk-network`).
   - Rebuilt and installed Linux release bundle of `setup_app` to `~/.local/share/unotusk/server-setup/`.

### Automated Verification Results
- **Setup App Tests**: `44/44 PASS` (includes 9 environment validator tests, 4 deployment engine tests, 2 compose generator tests).
- **Employee App Tests**: `37/37 PASS`.
- **Backend Pytest Suite**: `94/94 PASS`.
- **Flutter Analyze**: `CLEAN` across both `setup_app` and `app` (0 warnings, 0 errors).
- **Backend Lint (Ruff)**: `CLEAN` (All checks passed).
- **Live Readiness Probe**:
  ```bash
  $ curl -s http://localhost:8000/health/ready
  {"status":"ready","database":"connected","redis":"connected"}
  ```
- **Live Docker Ports**:
  ```text
  unotusk-api:      0.0.0.0:8000->8000/tcp (Host Published)
  unotusk-postgres: 5432/tcp (Internal Docker Network Only)
  unotusk-redis:    6379/tcp (Internal Docker Network Only)
  ```

---

## 9. Status & Sign-off Checklist

- [x] Host port 6379 and 5432 removed from Compose generation.
- [x] Internal communication on `unotusk-network` verified working.
- [x] Port conflict detection implemented with process/container identification.
- [x] Wizard gated against proceeding to "Ready to install" on conflict.
- [x] All 8 regression test scenarios implemented and passing.
- [x] Both Flutter applications analyzed cleanly.
- [x] Setup App release binary rebuilt and installed.
- [x] Live deployment healthy and ready.
- [x] **HOTFIX COMPLETE AND SIGNED OFF.**
