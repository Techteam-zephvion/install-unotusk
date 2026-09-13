# PHASE 4 — UNOTUSK SERVER SETUP TASK SHEET

**Product Goal**: Provide a simple, guided Flutter desktop wizard ("Unotusk Server Setup") that enables an organization to deploy, configure, and verify ONE Unotusk Server in their own infrastructure (Local / Remote Linux host) without requiring deep DevOps/database knowledge.

---

## Task Overview & Status Matrix

| Task ID | Task Name | Dependencies | Status |
|---|---|---|---|
| **TASK-401** | Server Setup Flutter Foundation | - | DONE |
| **TASK-402** | Setup Wizard Shell & Navigation | TASK-401 | DONE |
| **TASK-403** | Target Machine Selection (Local / Remote SSH) | TASK-402 | DONE |
| **TASK-404** | Target Machine & Environment Validation Engine | TASK-403 | DONE |
| **TASK-405** | Server Configuration Form & Secrets Management | TASK-404 | DONE |
| **TASK-406** | Deployment & Container Orchestration Engine | TASK-405 | DONE |
| **TASK-407** | Startup, Migration & Health Verification | TASK-406 | DONE |
| **TASK-408** | Setup Completion & Employee App Handshake | TASK-407 | DONE |
| **TASK-409** | Failure Handling, Recovery & Sanitized Diagnostics | TASK-404, TASK-406 | DONE |
| **TASK-410** | Security Audit & Secret Redaction Verification | TASK-405, TASK-409 | DONE |
| **TASK-411** | End-to-End Real Deployment & Connection Test | TASK-408, TASK-410 | DONE |
| **TASK-412** | UX Polish & Final Demo Validation | TASK-411 | DONE |

---

## Detailed Task Specifications

### TASK-401: Server Setup Flutter Foundation
- **Purpose**: Initialize the standalone Flutter desktop project for the Unotusk Server Setup wizard with Riverpod, GoRouter, Dio, desktop window sizing, and clean design tokens matching the Unotusk design system.
- **User-Facing Result**: Setup application boots as a clean, restrained desktop window titled "Unotusk Server Setup".
- **Technical Dependencies**: Flutter SDK, `flutter_riverpod`, `go_router`, `dio`, `window_manager` (or standard desktop runners).
- **Files Affected**:
  - `setup_app/pubspec.yaml`
  - `setup_app/lib/main.dart`
  - `setup_app/lib/core/theme/`
  - `setup_app/lib/core/constants/`
  - `setup_app/linux/`, `setup_app/macos/`, `setup_app/windows/`
- **Implementation Steps**:
  1. Create the `setup_app` Flutter project.
  2. Configure dependencies (`flutter_riverpod`, `go_router`, `dio`, `process_run`/`dart:io`).
  3. Configure desktop window constraints (optimal setup wizard size ~800x640, non-resizable or constrained minimum size).
  4. Establish theme tokens (neutral palette, restrained typography, clear status indicators).
- **Acceptance Criteria**:
  - `flutter analyze` passes with 0 warnings/errors.
  - Setup app runs and renders initial desktop window cleanly.
- **Status**: DONE

---

### TASK-402: Setup Wizard Shell & Navigation
- **Purpose**: Build the linear 7-stage step-by-step wizard controller and layout shell: Welcome → Target → Server Check → Configure → Install → Verify → Ready.
- **User-Facing Result**: Clear visual progress indicator showing current step without noisy marketing text or clutter.
- **Technical Dependencies**: TASK-401
- **Files Affected**:
  - `setup_app/lib/features/wizard/presentation/wizard_shell.dart`
  - `setup_app/lib/features/wizard/presentation/wizard_controller.dart`
  - `setup_app/lib/features/wizard/domain/wizard_step.dart`
- **Implementation Steps**:
  1. Define `WizardStep` enum representing linear flow.
  2. Implement `WizardController` managing state transitions, navigation guards, and step history.
  3. Build `WizardShell` widget displaying top-level step breadcrumb / header and clean content area.
  4. Build Welcome step with "Get Started" action.
- **Acceptance Criteria**:
  - Step transitions are smooth and strictly linear.
  - Back navigation works where safe (prevented during active installation/verification).
- **Status**: DONE

---

### TASK-403: Target Machine Selection
- **Purpose**: Allow the customer to choose the deployment target: "This computer" (Local Host) or "Remote Linux Server" (via SSH).
- **User-Facing Result**: Clean selection cards with clear indications of requirements for each target.
- **Technical Dependencies**: TASK-402
- **Files Affected**:
  - `setup_app/lib/features/target/presentation/target_screen.dart`
  - `setup_app/lib/features/target/domain/target_config.dart`
  - `setup_app/lib/features/target/presentation/target_controller.dart`
  - `setup_app/lib/features/target/presentation/widgets/remote_ssh_form.dart`
- **Implementation Steps**:
  1. Create Target selection UI (Local vs Remote).
  2. For Remote target, provide input fields: Hostname/IP, Port (default 22), SSH User, and Auth Method (SSH Key file or Password).
  3. Validate input format before proceeding to server check.
- **Acceptance Criteria**:
  - Customer can select "This computer" with 1 click.
  - Customer selecting "Remote Linux Server" can enter valid connection credentials.
- **Status**: DONE

---

### TASK-404: Target Machine & Environment Validation Engine
- **Purpose**: Validate target environment prerequisites before proceeding: Docker daemon availability, Docker Compose plugin/binary, disk space, and port availability (8000, 5432, 6379).
- **User-Facing Result**: Check items showing pass/fail status with human-readable guidance if a prerequisite fails (e.g. "Docker is not running").
- **Technical Dependencies**: TASK-403, `process_run` / `dart:io` / SSH client.
- **Files Affected**:
  - `setup_app/lib/features/validation/domain/check_result.dart`
  - `setup_app/lib/features/validation/data/environment_validator.dart`
  - `setup_app/lib/features/validation/presentation/server_check_screen.dart`
  - `setup_app/lib/features/validation/presentation/server_check_controller.dart`
- **Implementation Steps**:
  1. Implement validator interface for Local (CLI subprocesses) and Remote (SSH exec).
  2. Check Docker daemon (`docker info`).
  3. Check Docker Compose (`docker compose version`).
  4. Check port availability (TCP socket bind test / `ss`/`netstat`).
  5. Check free disk storage (minimum 5GB recommended).
  6. Present results cleanly with progress spinners, green checkmarks, or clear remediation hints.
- **Acceptance Criteria**:
  - Accurately detects missing Docker or bound ports.
  - Does not proceed to configuration if critical checks fail.
  - "Retry" re-runs validation seamlessly.
- **Status**: DONE

---

### TASK-405: Server Configuration Form & Secrets Management
- **Purpose**: Collect minimum essential server configuration without overwhelming the customer with infrastructure details.
- **User-Facing Result**: Clean form asking only for: Server Name, Admin Email, Admin Password, Server Port/URL, and LLM Provider (Groq / Anthropic) with API Key.
- **Technical Dependencies**: TASK-404
- **Files Affected**:
  - `setup_app/lib/features/config/domain/server_config.dart`
  - `setup_app/lib/features/config/presentation/config_screen.dart`
  - `setup_app/lib/features/config/presentation/config_controller.dart`
  - `setup_app/lib/core/security/secret_sanitizer.dart`
- **Implementation Steps**:
  1. Define `ServerConfig` model containing server metadata, admin credentials, LLM settings, and generated secrets (`AUTH_SECRET`, DB password).
  2. Build form with sensible defaults (Server Name: "Unotusk Server", Port: 8000, Provider: Groq).
  3. Auto-generate high-entropy secrets (32+ byte hex) for internal `AUTH_SECRET` and Postgres password without asking user.
  4. Securely mask API keys and passwords in memory and UI.
- **Acceptance Criteria**:
  - Validates email format, password complexity, and API key presence.
  - All internal infrastructure parameters (DB URLs, Redis URLs) are generated automatically.
- **Status**: DONE

---

### TASK-406: Deployment & Container Orchestration Engine
- **Purpose**: Render deployment configurations (`docker-compose.yml`, `.env`), package/transfer required assets to the target, and invoke container orchestrations.
- **User-Facing Result**: Real-time deployment progress showing discrete completed milestones (Preparing files → Generating secrets → Starting database & Redis → Launching Unotusk API & Worker).
- **Technical Dependencies**: TASK-405
- **Files Affected**:
  - `setup_app/lib/features/deploy/data/deployment_engine.dart`
  - `setup_app/lib/features/deploy/data/compose_generator.dart`
  - `setup_app/lib/features/deploy/presentation/deploy_screen.dart`
  - `setup_app/lib/features/deploy/presentation/deploy_controller.dart`
- **Implementation Steps**:
  1. Build compose and `.env` template generator with isolated volume names and parameterized ports.
  2. Implement deployment executor for Local machine (`docker compose up -d`).
  3. Implement deployment executor for Remote SSH target (safe file transfer and `docker compose up -d`).
  4. Stream real stage progress without displaying raw unredacted terminal logs.
- **Acceptance Criteria**:
  - Starts real PostgreSQL, Redis, and API containers on target host.
  - Handles process failure gracefully with clear retry option.
- **Status**: DONE

---

### TASK-407: Startup, Migration & Health Verification
- **Purpose**: Confirm actual server health by executing DB migrations and polling `/health` and `/health/ready` until operational.
- **User-Facing Result**: Verification screen displaying real-time status of Database, Redis, and API readiness.
- **Technical Dependencies**: TASK-406, `dio`
- **Files Affected**:
  - `setup_app/lib/features/verify/data/health_verifier.dart`
  - `setup_app/lib/features/verify/presentation/verify_screen.dart`
  - `setup_app/lib/features/verify/presentation/verify_controller.dart`
- **Implementation Steps**:
  1. Execute DB migration (`alembic upgrade head` inside API container or via startup script).
  2. Seed initial admin user if configured.
  3. Poll target server's `/health` and `/health/ready` endpoints with timeout and exponential backoff.
  4. Confirm status changes from "Starting services..." to "Server is operational".
- **Acceptance Criteria**:
  - Accurately detects ready state via real HTTP calls.
  - Times out after a reasonable threshold (~60s) with clear diagnostic recovery if services fail to start.
- **Status**: DONE

---

### TASK-408: Setup Completion & Employee App Handshake
- **Purpose**: Display the final ready screen with the accessible Unotusk Server URL, quick copy button, and a direct action to launch or connect the Employee Application.
- **User-Facing Result**: Clean "Unotusk is ready" screen with server address and "Open Employee App" button.
- **Technical Dependencies**: TASK-407
- **Files Affected**:
  - `setup_app/lib/features/ready/presentation/ready_screen.dart`
  - `setup_app/lib/features/ready/data/app_launcher.dart`
- **Implementation Steps**:
  1. Build Ready screen displaying the resolved Server URL (`http://localhost:<PORT>` or `http://<HOST>:<PORT>`).
  2. Provide "Copy Address" with immediate visual confirmation.
  3. Provide "Open Employee App" which can launch the local Unotusk desktop binary or instruct the user.
  4. Provide option to save connection profile for employee distribution.
- **Acceptance Criteria**:
  - Customer can easily copy server URL and launch the Employee App.
- **Status**: DONE

---

### TASK-409: Failure Handling, Recovery & Sanitized Diagnostics
- **Purpose**: Handle every potential failure mode (unreachable host, port collision, Docker daemon stopped, compose error, DB migration error) with human-readable messaging and safe "View technical details" logs.
- **User-Facing Result**: Helpful error banners with "Retry" action and expandable technical details that are 100% sanitized.
- **Technical Dependencies**: TASK-404, TASK-406
- **Files Affected**:
  - `setup_app/lib/core/widgets/error_state_card.dart`
  - `setup_app/lib/core/widgets/technical_details_dialog.dart`
  - `setup_app/lib/core/security/secret_sanitizer.dart`
- **Implementation Steps**:
  1. Build reusable `ErrorStateCard` with clear title, guidance, retry button, and secondary "Technical details" button.
  2. Implement `SecretSanitizer` regex filter ensuring API keys, passwords, and tokens are replaced with `[REDACTED]` in all output logs.
- **Acceptance Criteria**:
  - Injected failures (e.g. invalid port, wrong API key format, daemon kill) display clear recovery prompts without crashes.
  - Secrets are never visible in technical details dialogs.
- **Status**: DONE

---

### TASK-410: Security Audit & Secret Redaction Verification
- **Purpose**: Verify that no passwords, API keys, private SSH keys, or JWT secrets are ever logged to stdout/stderr, written to unencrypted temporary files, or exposed in UI views.
- **User-Facing Result**: Rock-solid security guarantees for enterprise and customer environments.
- **Technical Dependencies**: TASK-405, TASK-409
- **Files Affected**:
  - `setup_app/test/unit/security_sanitizer_test.dart`
  - `setup_app/lib/core/security/`
- **Implementation Steps**:
  1. Write comprehensive unit tests verifying that `SecretSanitizer` strips Groq, Anthropic, Postgres, and JWT secrets from arbitrary error logs.
  2. Audit all file writing operations to ensure file permissions (e.g. `chmod 600` on generated `.env`) are secure.
- **Acceptance Criteria**:
  - Unit tests for secret sanitization pass 100%.
  - Zero sensitive credentials leaked in debug logs or UI trees.
- **Status**: DONE

---

### TASK-411: End-to-End Real Deployment & Connection Test
- **Purpose**: Perform a complete, clean end-to-end run: Unotusk Server Setup installs and starts real containers -> Verifies health -> Employee Desktop App connects to the new server -> Admin logs in -> Navigates to Projects.
- **User-Facing Result**: Fully working multi-app demonstration from zero to operational project workspace.
- **Technical Dependencies**: TASK-408, TASK-410, Employee App (`app/`)
- **Files Affected**:
  - `setup_app/test/integration/setup_e2e_test.dart`
  - `scripts/verify_server_setup_e2e.py`
- **Implementation Steps**:
  1. Execute clean setup via the setup wizard or automated engine against a fresh port.
  2. Verify all 3 backend containers (`postgres`, `redis`, `api`) are healthy.
  3. Authenticate with Employee Application against the newly spawned server URL.
  4. Perform project workspace discovery query to prove end-to-end functionality.
- **Acceptance Criteria**:
  - Real setup succeeds end-to-end against local host.
  - Employee App connects and functions normally against the deployed instance.
- **Status**: DONE

---

### TASK-412: Final UX / Demo Polish
- **Purpose**: Ensure pristine aesthetics, smooth animations, desktop keyboard shortcuts (Enter to proceed, Esc to close dialogs), and clean visual feedback throughout the entire wizard.
- **User-Facing Result**: High-polish, effortless setup experience that instills immediate customer confidence.
- **Technical Dependencies**: TASK-411
- **Files Affected**:
  - `setup_app/lib/`
  - `docs/PHASE_4_SERVER_SETUP_TASK_SHEET.md`
- **Implementation Steps**:
  1. Refine layout spacing, typography, and card elevations.
  2. Ensure keyboard navigation and default button focus.
  3. Verify clean responsive sizing on standard desktop screens.
  4. Update task sheet and walkthrough documentation.
- **Acceptance Criteria**:
  - All 12 tasks marked DONE.
  - Zero analyzer errors.
  - Complete demo flow ready for investor/customer demonstration.
- **Status**: DONE
