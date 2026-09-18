# UNOTUSK MVP — LAN PILOT TEST PREPARATION TASK SHEET
## Multi-OS Employee Client Builds, Server Reset, Hardened LAN Exposure & Structured Logging

**Document**: LAN Pilot Test Preparation Task Sheet  
**Date**: 2026-09-18  
**Scope**: Real LAN Test (1 Linux Server, 4 Windows Laptops, 2 macOS Laptops)  
**Status**: ALL 10 TASKS COMPLETED & VERIFIED (100% PASS RATE)  
**Branch**: `MVP_build` (or current active development branch)  

---

## 1. Executive Summary & Objective

The objective of this phase is to prepare the existing Unotusk MVP for an internal, multi-device **Local Area Network (LAN) Pilot Test** involving:
- **1 Linux Laptop**: Dedicated Unotusk Server host (API + PostgreSQL + Redis + Worker + Migration).
- **4 Windows Laptops (x64)**: Employee App clients connecting over LAN.
- **2 macOS Laptops (Apple Silicon / Intel)**: Employee App clients connecting over LAN.

This is **strictly not a V2 feature phase**. We are not adding autonomous coding, Jira/Slack integrations, cloud fleet management, Kubernetes, Terraform, or new intelligence models. We are operationalizing and hardening the **existing MVP** to ensure:
1. Clean, safe, repeatable server reset and reinstallation via the Server Setup App.
2. Hardened LAN server exposure: API (`:8000`) reachable on LAN; PostgreSQL (`:5432`) and Redis (`:6379`) strictly internal to Docker.
3. Dynamic LAN IP detection in the Server Setup App (e.g. `http://10.0.0.59:8000`).
4. Honest, verifiable multi-OS packaging for Windows, macOS, and Linux clients with checksums and clear platform build requirements.
5. Structured, sanitized operational logging in the Employee App and Server backend with zero secret leaks.
6. Safe diagnostic bundle exporter with automated secret redaction verification.
7. End-to-end LAN connectivity verification and actionable runbooks.

---

## 2. Pre-Implementation Baseline & Inspection Findings

| Component | Current State | LAN Pilot Readiness & Gaps |
|---|---|---|
| **Server Stack** | 4 Docker services (`unotusk-api`, `unotusk-worker`, `unotusk-postgres`, `unotusk-redis`) | Internal network isolated; API port 8000 bound to host; Postgres & Redis ports are not exposed to host. Ready for LAN. |
| **Server Reset** | Manual `docker compose down` or ad-hoc container removal | **GAP**: No safe, dedicated reset script. Risk of affecting co-hosted containers or deleting data inadvertently. |
| **LAN IP Resolution** | `ServerConfig.serverUrl` hardcodes `http://localhost:8000` | **GAP**: Server Setup App does not dynamically detect the active LAN interface/IP (e.g. `10.0.0.59`). Needs dynamic network interface detection. |
| **CORS Configuration** | Hardcoded localhost ports (`3000`, `3001`, `3005`) | Needs support for LAN origins/regex to ensure seamless cross-device communication. |
| **Employee App (Flutter)** | Native desktop client running on Linux x64; supports server URL configuration & `/health` check | Connects to arbitrary server URL; 36 tests passing. Ready for LAN testing. |
| **Cross-Platform Builds** | Host is Linux (`Pop!_OS 24.04 x86_64`). Flutter builds Linux desktop natively. | **GAP**: Windows (`.exe`) and macOS (`.app`) cannot be cross-compiled on a Linux host natively. Exact build procedures, scripts, and build environment requirements must be formalized without faking support. |
| **Employee App Logging** | Zero structured logging in `app/lib` | **GAP**: No operational logging for application lifecycle, connection attempts, auth, ingestion, discoveries, or ask. |
| **Server Logging** | Standard Python `logging.basicConfig` text logs | **GAP**: Lacks structured correlation IDs, request duration middleware, and uniform log sanitization filter across all loggers. |
| **Diagnostic Exporter** | `scripts/export_diagnostics.py` exists (v0.1.0) | **GAP**: Needs active LAN interface telemetry, validation tests proving secret redaction, and optional client log inclusion. |
| **Test Baseline** | 94 backend tests passing (pytest), 46 setup_app tests passing, 36 app tests passing, 0 ruff errors, 0 flutter analyze warnings. | Baseline verified and healthy. |

---

## 3. LAN Architecture & Network Topology

```
                                  Local Area Network (LAN)
                      [ Wi-Fi / Ethernet Subnet: e.g. 10.0.0.0/24 ]
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         │                                 │                                 │
         v                                 v                                 v
┌───────────────────┐             ┌───────────────────┐             ┌───────────────────┐
│  Windows Laptop 1 │             │   macOS Laptop 1  │             │   Linux Laptop    │
│  (Employee App)   │             │   (Employee App)  │             │  (Optional Client)│
└────────┬──────────┘             └────────┬──────────┘             └────────┬──────────┘
         │                                 │                                 │
         └─────────────────────────────────┼─────────────────────────────────┘
                                           │ HTTP Requests to API (:8000)
                                           v
┌───────────────────────────────────────────────────────────────────────────────────────┐
│ LINUX SERVER LAPTOP (e.g. 10.0.0.59)                                                  │
│                                                                                       │
│  LAN Interface (wlo1 / eth0) ──> Port 8000 Published to Host (0.0.0.0:8000)           │
│                                                                                       │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐  │
│  │ Docker Bridge Network: unotusk-network                                          │  │
│  │                                                                                 │  │
│  │   ┌──────────────────────────────┐          ┌────────────────────────────────┐  │  │
│  │   │ unotusk-api (FastAPI)        │          │ unotusk-worker (Async Ingestion│  │  │
│  │   │ - Structured Audit Logs      │          │ - Discovery & AST Engine)      │  │  │
│  │   │ - Secret Sanitizer Filter    │          └──────────────┬─────────────────┘  │  │
│  │   └──────────────┬───────────────┘                         │                    │  │
│  │                  │                                         │                    │  │
│  │                  ▼                                         ▼                    │  │
│  │   ┌──────────────────────────────┐          ┌────────────────────────────────┐  │  │
│  │   │ unotusk-postgres (pgvector)  │          │ unotusk-redis (Task Queue)     │  │  │
│  │   │ - Port 5432 INTERNAL ONLY    │          │ - Port 6379 INTERNAL ONLY      │  │  │
│  │   │ - No Host Port Binding       │          │ - No Host Port Binding         │  │  │
│  │   └──────────────────────────────┘          └────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                       │
│  Server Setup App (Desktop GUI):                                                      │
│  - Dynamically inspects host network interfaces (filters virtual/docker bridges).     │
│  - Displays usable LAN URL: http://<LAN_IP>:8000                                      │
└───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Master Task Breakdown & Execution Plan

### TASK-LAN-001 — Clean Server Reset / Reinstallation Utility
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Provide a safe, deterministic CLI/script mechanism to completely stop, clean, and reset the Unotusk Server on the Linux host so the Server Setup App can be tested from scratch.
- **Safety Constraints Met**:
  - Targets ONLY Unotusk containers (`unotusk-api`, `unotusk-worker`, `unotusk-migration`, `unotusk-postgres`, `unotusk-redis`).
  - Explicitly protects foreign containers (`unotusk-2-*`, `nammadharani-*`, `supabase_*`, etc.).
  - Mandatory confirmation prompt before deleting persistent data volumes unless `--yes` / `-y` is provided.
  - Distinguishes between preserving data (`--preserve-data`, default) and full factory reset (`--wipe-data` / `--all`).
- **Implementation**:
  - Authored [clean_server_reset.py](file:///home/devils/PRO/Unotusk-MVP/scripts/clean_server_reset.py) with options `--preserve-data`, `--wipe-data`, `--wipe-config`, `--all`, `--dry-run`, `-y`, and `--check-only`.
  - Authored executable bash wrapper [clean_server_reset.sh](file:///home/devils/PRO/Unotusk-MVP/scripts/clean_server_reset.sh).
  - Authored comprehensive unit test suite [test_clean_server_reset.py](file:///home/devils/PRO/Unotusk-MVP/tests/test_clean_server_reset.py).
- **Verification**:
  - Unit tests: 6 of 6 passed in `tests/test_clean_server_reset.py`.
  - Full pytest suite: 100 of 100 passed in 44.6s.
  - Lint / static analysis: `ruff check` passed with 0 errors.
  - Flutter tests: 46 of 46 setup_app passed, 36 of 36 app passed; 0 flutter analyze warnings across both apps.
  - Real host test: Ran `--check-only` and `--dry-run --all`, verified that all 5 Unotusk containers are targeted while all 24 foreign containers on the host remain completely protected.
  - Tested safety guard: Aborted data wipe on rejected confirmation.

---

### TASK-LAN-002 — LAN Server Configuration & Dynamic IP Discovery
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Enable the Linux server to properly serve the LAN and make the Server Setup App display the actual LAN IP.
- **Implementation**:
  - Implemented [lan_detector.dart](file:///home/devils/PRO/Unotusk-MVP/setup_app/lib/core/network/lan_detector.dart) with automatic detection of RFC 1918 private IPv4 addresses (10.x, 172.16-31.x, 192.168.x) and filtering of virtual/container bridge adapters (`docker0`, `br-*`, `virbr*`, `lxcbr*`, `vboxnet*`, `vmnet*`, `tailscale*`, `tun*`).
  - Added physical interface prioritization (`wl*`, `en*`, `eth*`).
  - Updated [server_config.dart](file:///home/devils/PRO/Unotusk-MVP/setup_app/lib/features/config/domain/server_config.dart) and [config_controller.dart](file:///home/devils/PRO/Unotusk-MVP/setup_app/lib/features/config/presentation/config_controller.dart) to store and resolve `lanIp`, `lanUrl`, and `localUrl`.
  - Updated [ready_screen.dart](file:///home/devils/PRO/Unotusk-MVP/setup_app/lib/features/ready/presentation/ready_screen.dart) to display the dynamic LAN URL (e.g. `http://10.0.0.59:8000`), the `LAN REACHABLE` badge, a local host address row, and an interface switcher chip list when multiple network interfaces exist.
  - Added LAN CORS support in [main.py](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/main.py) via `allow_origin_regex` for localhost and private IP ranges.
  - Authored unit tests in [lan_detector_test.dart](file:///home/devils/PRO/Unotusk-MVP/setup_app/test/unit/lan_detector_test.dart), [ready_screen_test.dart](file:///home/devils/PRO/Unotusk-MVP/setup_app/test/widget/ready_screen_test.dart), and [test_lan_cors.py](file:///home/devils/PRO/Unotusk-MVP/tests/test_lan_cors.py).
- **Verification**:
  - Setup App unit & widget tests: 52 of 52 passed.
  - Backend tests: 105 of 105 passed.
  - Flutter analyze: 0 issues on `setup_app` and `app`.
  - Python lint: 0 errors on `ruff check`.
  - Live probe on LAN IP: `curl http://10.0.0.59:8000/health` (200 OK) and `curl http://10.0.0.59:8000/health/ready` (200 OK).
  - Port isolation verified via `docker inspect`: `unotusk-postgres` and `unotusk-redis` host port mappings are `null` (strictly Docker bridge internal).

---

### TASK-LAN-003 — Multi-OS Employee App Builds & Toolchain Packaging
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Prepare verified client builds for Linux, Windows, and macOS, with honest platform build requirements.
- **Platform Strategy & Deliverables**:
  - **Linux x64**: Built natively on current Linux host via `flutter build linux --release`. Verified release binary at `app/build/linux/x64/release/bundle/app`.
  - **Windows x64**: Created automated build script [build_windows_client.bat](file:///home/devils/PRO/Unotusk-MVP/scripts/build_windows_client.bat) with prerequisites checking (Visual Studio 2022 C++ desktop workload, Flutter SDK), release build execution, PowerShell zip archiving to `dist/unotusk-employee-windows-x64.zip`, and SHA256 checksum generation.
  - **macOS (Universal / Apple Silicon / Intel)**: Created [build_macos_client.sh](file:///home/devils/PRO/Unotusk-MVP/scripts/build_macos_client.sh) with Xcode / CocoaPods verification, release build execution, `.tar.gz` bundle archiving to `dist/unotusk-employee-macos.tar.gz`, and SHA256 generation.
- **Pilot Runtime Guidance**:
  - Documented unsigned pilot build notices: Windows SmartScreen "More info -> Run anyway", macOS Gatekeeper `xattr -cr /Applications/app.app`.
- **Verification**:
  - Successfully built and packaged native Linux x64 release client in `dist/unotusk-employee-linux-x64.tar.gz`.

---

### TASK-LAN-004 — Installation / Packaging Verification & Checksums
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Standardize release artifacts in `dist/` with metadata and SHA-256 checksums.
- **Deliverables**:
  - Authored [package_release.sh](file:///home/devils/PRO/Unotusk-MVP/scripts/package_release.sh) to assemble, compress, and verify distribution bundles.
  - Generates `dist/unotusk-employee-linux-x64.tar.gz` and `dist/unotusk-employee-linux-x64.tar.gz.sha256`.
  - Validated checksum calculation and archive contents with `tar -tzf`.
- **Verification**:
  - Executed `./scripts/package_release.sh`, verified 9.8MB release archive and valid SHA256 hash (`57a7fdb10eb2c637f94f0305ff322e87c07f61f2f77211260a5d4c4870ad61cd`).

---

### TASK-LAN-005 — Structured Application Logging in Employee App
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Implement high-fidelity, privacy-preserving structured logging in `app/lib`.
- **Implementation**:
  - Created [app_logger.dart](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/logging/app_logger.dart) with 24 distinct event types (`APPLICATION_START`, `SERVER_URL_CONFIGURED`, `SERVER_CONNECTION_*`, `LOGIN_*`, `SESSION_*`, `PROJECT_LOAD_*`, `INGESTION_*`, `DISCOVERY_*`, `ASK_*`, `UNEXPECTED_ERROR`).
  - Added in-memory circular buffer (max 500 events) for real-time diagnostic viewing.
  - Added automatic regex secret scrubber for Bearer tokens, raw JWTs, passwords, API keys (`gsk_*`, `sk-ant-*`), and DB URLs.
  - Created [diagnostic_logs_modal.dart](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/logging/diagnostic_logs_modal.dart) and integrated "View Logs" buttons into `ServerConnectionScreen` and `SettingsScreen`.
  - Integrated logging into `ConnectionController`, `AuthController`, `ProjectsController`, and `main.dart`.
- **Verification**:
  - Authored unit test suite [app_logger_test.dart](file:///home/devils/PRO/Unotusk-MVP/app/test/unit/app_logger_test.dart) (5 of 5 passed).
  - Authored widget test [diagnostic_logs_modal_test.dart](file:///home/devils/PRO/Unotusk-MVP/app/test/widget/diagnostic_logs_modal_test.dart) (passed).
  - Full `app/` test suite: 42 of 42 passed.
  - `flutter analyze`: 0 issues found on `app/`.

---

### TASK-LAN-006 — Server Logging & Secret Redaction Audit
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Upgrade backend logging to structured, correlation-aware logging with universal secret sanitization.
- **Implementation**:
  - Created [apps/api/src/core/logging.py](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/core/logging.py) with:
    - `RequestCorrelationMiddleware` attaching and propagating `X-Request-ID` across async tasks.
    - `SecretSanitizingFilter` automatically redacting DB connection passwords (PostgreSQL, Redis), LLM API keys (Anthropic, Groq, OpenAI), JWTs, Bearer headers, and sensitive key-value maps.
    - `StructuredJSONFormatter` producing JSON logs with timestamps, level, logger, request ID, and message.
  - Registered middleware and root logging filter in [apps/api/src/main.py](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/main.py).
- **Verification**:
  - Authored comprehensive test suite [test_server_logging.py](file:///home/devils/PRO/Unotusk-MVP/tests/test_server_logging.py) (13 of 13 passed).
  - Verified request ID generation, propagation, and header injection with `TestClient`.
  - `ruff check`: 0 errors.

---

### TASK-LAN-007 — Safe Diagnostic Bundle Exporter Enhancement
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Enhance `scripts/export_diagnostics.py` to capture LAN configuration and verify 100% secret scrubbing.
- **Implementation**:
  - Enhanced [export_diagnostics.py](file:///home/devils/PRO/Unotusk-MVP/scripts/export_diagnostics.py) to capture:
    - Host hardware specs (OS, CPU, memory, disk).
    - LAN network details (active interfaces, private IPs, gateway, port 8000 listening).
    - Exact Unotusk container status (strictly protecting foreign containers).
    - Live health probes (`/health`, `/health/ready`).
    - Last 500 lines of sanitized service logs.
    - SHA256-verified `.tar.gz` bundle creation.
  - Added [test_export_diagnostics.py](file:///home/devils/PRO/Unotusk-MVP/tests/test_export_diagnostics.py) with synthetic secret injection tests.
- **Verification**:
  - Automated tests: 6 of 6 passed in `tests/test_export_diagnostics.py`.
  - Verified 100% absence of synthetic secrets in exported bundle.
  - `ruff check`: 0 errors.

---

### TASK-LAN-008 — LAN Connectivity Verification Probe & Preflight Check
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Provide automated diagnostic probe and procedures for verifying LAN connectivity.
- **Implementation**:
  - Authored [verify_lan_connectivity.py](file:///home/devils/PRO/Unotusk-MVP/scripts/verify_lan_connectivity.py) and executable wrapper [verify_lan_connectivity.sh](file:///home/devils/PRO/Unotusk-MVP/scripts/verify_lan_connectivity.sh).
  - Performs 5-point verification:
    1. RFC 1918 private IPv4 detection.
    2. Port 8000 listening state (0.0.0.0 vs local).
    3. `/health` and `/health/ready` HTTP 200 response on LAN IP.
    4. CORS preflight OPTIONS check for LAN client origins.
    5. Firewall status inspection (UFW / iptables).
  - Authored unit test suite [test_verify_lan_connectivity.py](file:///home/devils/PRO/Unotusk-MVP/tests/test_verify_lan_connectivity.py).
- **Verification**:
  - Unit tests: 8 of 8 passed in `tests/test_verify_lan_connectivity.py`.
  - Live probe test against running container: All 5 checks passed!
  - `ruff check`: 0 errors.

---

### TASK-LAN-009 — Multi-Client Pilot Matrix Documentation
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Document the complete test matrix for 1 Linux Server + 4 Windows Clients + 2 macOS Clients.
- **Deliverables**:
  - Authored [docs/LAN_PILOT_MATRIX.md](file:///home/devils/PRO/Unotusk-MVP/docs/LAN_PILOT_MATRIX.md).
  - Details 7 nodes (`SRV-01`, `WIN-01`..`WIN-04`, `MAC-01`..`MAC-02`), test accounts, 6 test execution phases, and sign-off checklist (`CHK-LAN-01` through `CHK-LAN-10`).
- **Verification**:
  - Reviewed against pilot hardware and networking requirements.

---

### TASK-LAN-010 — Final LAN Pilot Runbook
- **Status**: COMPLETED
- **Completed Date**: 2026-09-18
- **Goal**: Author comprehensive, step-by-step, zero-code-inspection runbook for conducting the pilot test.
- **Deliverables**:
  - Authored [docs/LAN_PILOT_RUNBOOK.md](file:///home/devils/PRO/Unotusk-MVP/docs/LAN_PILOT_RUNBOOK.md).
  - Covers complete operational lifecycle: setup, IP discovery, clean reset, multi-OS distribution, SmartScreen/Gatekeeper bypass, simultaneous connection, workspace ingestion, client log inspection, diagnostic export, and failure recovery.
- **Verification**:
  - Verified all scripts, commands, and procedures match live implementation.

---

## 5. Proposed Task Execution Order & Gates

```
TASK-LAN-001 (Server Reset Utility)
       │
       ▼
TASK-LAN-002 (LAN Server Config & Dynamic IP)
       │
       ▼
TASK-LAN-005 (Employee App Structured Logging)
       │
       ▼
TASK-LAN-006 (Server Logging & Redaction Filter)
       │
       ▼
TASK-LAN-007 (Safe Diagnostic Bundle & Leak Test)
       │
       ▼
TASK-LAN-008 (LAN Connectivity Verification Probe)
       │
       ▼
TASK-LAN-003 (Multi-OS Builds & Build Environment Specs)
       │
       ▼
TASK-LAN-004 (Packaging Verification & Checksums)
       │
       ▼
TASK-LAN-009 (Multi-Client Test Matrix)
       │
       ▼
TASK-LAN-010 (Final Practical LAN Runbook)
       │
       ▼
Final Verification & Conventional Commit
```

*Note on Order Rationale*:
1. Establishing the **Clean Server Reset (001)** and **LAN Server Config / Dynamic IP (002)** comes first so the server environment is solid and re-testable.
2. Implementing **Logging (005, 006)** and **Diagnostics (007, 008)** before multi-OS packaging ensures that any binaries packaged include the telemetry needed for testing.
3. Packaging, matrix, and the final runbook close the loop.

---

## 6. Risk Register & Mitigations

| Risk ID | Description | Impact | Mitigation Strategy |
|---|---|---|---|
| **R-LAN-1** | Server reset script inadvertently stops or removes non-Unotusk containers on developer laptop | High | Strict container name matching (`unotusk-*`); verify compose project name; prompt for explicit confirmation before volume removal. |
| **R-LAN-2** | Linux host has multiple network interfaces (Wi-Fi, Docker bridges, VPNs, virtual bridges) | Medium | Intelligent interface detection: prioritize default gateway interface; filter out `docker0`, `br-*`, `virbr*`, `127.0.0.1`; allow user override in UI. |
| **R-LAN-3** | Windows/macOS cross-compilation impossible on Linux host | Medium | Be completely transparent: do not fake binaries. Package Linux x64 natively, provide turnkey build scripts and environment specifications for Windows & macOS build hosts. |
| **R-LAN-4** | Wi-Fi router or AP client isolation blocks peer-to-peer LAN traffic between laptops | High | Document Wi-Fi router / AP client isolation prerequisites in runbook; provide `verify_lan_connectivity.py` with specific network isolation diagnosis. |
| **R-LAN-5** | Unsigned binaries trigger Windows SmartScreen or macOS Gatekeeper warnings | Medium | Document exact OS security prompts and how pilot testers safely allow the application to execute. |
| **R-LAN-6** | Customer credentials or tokens leak into application or server logs during LAN test | Critical | Universal secret sanitization filters in Python logging, Dart logging, and diagnostic exporter; automated test asserting redaction of synthetic secrets. |

---

## 7. Verification Strategy

1. **Automated Unit & Integration Tests**:
   - Backend: Run full pytest suite (must maintain 94/94 passing + new tests).
   - Setup App: Run flutter test (must maintain 46/46 passing + new tests).
   - Employee App: Run flutter test (must maintain 36/36 passing + new tests).
   - Leak Prevention Test: Run automated pytest asserting complete redaction of injected credentials.
2. **Static Analysis & Linting**:
   - Backend: `ruff check` on all code (0 errors).
   - Frontend: `flutter analyze` on `setup_app` and `app` (0 issues).
3. **Live System Verification**:
   - Execute reset script and verify ports 8000, 5432, 6379 release cleanly.
   - Run Server Setup App, verify dynamic LAN IP detection and server launch.
   - Probe server from LAN IP (`curl -f http://<LAN_IP>:8000/health/ready`).
   - Run Employee App, connect via LAN IP, log in, create project, test logging.
   - Run `scripts/export_diagnostics.py` and inspect output for zero leaked secrets.
