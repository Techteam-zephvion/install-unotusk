# PHASE 6 — MVP CUSTOMER READINESS TASK SHEET

**Product Goal**: Make the existing Unotusk MVP fully customer-ready for initial design partners and technical pilot customers. The product must feel stable, understandable, professional, and self-explanatory without requiring founder/engineering intervention for basic operations.

---

## Operating Principle
> **"Simple on the surface. Deep when needed."**  
> The Employee Application must remain quiet, fast, and information-dense without clutter or marketing language. It is not an AI chatbot, IDE replacement, or autonomous coding agent—it is a grounded project intelligence tool for developers and technical leaders.

---

## Status Matrix

| Task ID | Task Name | Status | Dependencies | Target Area |
|---|---|---|---|---|
| **TASK-601** | Phase 5 Findings Triage & Customer Impact Audit | COMPLETED | - | Triage & Baseline |
| **TASK-602** | Employee App First-Run Experience | COMPLETED | TASK-601 | Employee App UX |
| **TASK-603** | Project Creation & Repository Connection Flow | COMPLETED | TASK-602 | Workflow Hardening |
| **TASK-604** | Ingestion Status & Progress Experience | COMPLETED | TASK-603 | Reliability & Clarity |
| **TASK-605** | Intelligence Views & Evidentiary Clarity | COMPLETED | TASK-604 | Core Product Value |
| **TASK-606** | Plain-Language Error, Empty & Offline States | COMPLETED | TASK-605 | Resilience UX |
| **TASK-607** | Authentication, Session Restoration & 401 Recovery | COMPLETED | TASK-606 | Auth UX |
| **TASK-608** | Server Setup App Customer Polish | COMPLETED | TASK-607 | Setup Wizard UX |
| **TASK-609** | Platform Build Evaluation (Linux / macOS / Windows) | COMPLETED | TASK-608 | Build Engineering |
| **TASK-610** | Packaging, Naming & Distribution Artifacts | COMPLETED | TASK-609 | Release Engineering |
| **TASK-611** | Customer-Facing Performance & Latency Audit | COMPLETED | TASK-610 | Performance |
| **TASK-612** | Security, Secret Exposure & Isolation Verification | COMPLETED | TASK-611 | Security & Privacy |
| **TASK-613** | Customer Quick-Start & Operations Documentation | COMPLETED | TASK-612 | Documentation |
| **TASK-614** | Repeatable Design Partner Demo Environment | COMPLETED | TASK-613 | Demo Enablement |
| **TASK-615** | Clean-Room Final Customer Journey Test | COMPLETED | TASK-614 | E2E Customer Journey |
| **TASK-616** | MVP Release Gate & Final Disposition Report | COMPLETED | TASK-615 | Release Sign-Off |

---

## Detailed Task Specifications

### TASK-601: Phase 5 Findings Triage & Customer Impact Audit
- **Objective**: Review all findings, limitations, and defect resolutions from Phase 5 (DEF-501 to DEF-505) and audit how they directly affect customer perception and workflow.
- **Status**: COMPLETED
- **Triage Matrix & Audit Results**:

| Issue ID | Severity | Category | Customer Impact | Resolution & Verification |
|---|---|---|---|---|
| **DEF-501** | P1 | Deployment | Without automated migrations, first-time server start crashed on missing tables. | Resolved via migration init-container in `ComposeGenerator` & verified in integration tests. |
| **DEF-502** | P2 | Security | Database and cache ports exposed to local LAN on customer machines. | Hardened to `127.0.0.1` binding; unit test verified and passing. |
| **DEF-503** | P2 | Security | Raw retrieval internals exposed to unauthorized network observers. | Guarded with `APP_ENV == "production"` 403 Forbidden check. |
| **DEF-504** | P2 | Evidentiary | Offline synthesis template previously echoed query strings as if they were facts. | Refined template to strictly state absence of evidence without fabrication. |
| **DEF-505** | P3 | Quality | Regressions in desktop UI could pass unnoticed in PR builds. | Added automated Flutter analysis and test suites to `.github/workflows/ci.yml`. |

- **Conclusion**: All P0/P1 issues are resolved. System baseline is verified green across 85 backend tests and 70 frontend tests. Customer readiness focus shifts to UI/UX first-run flow and plain-language resilience.

---

### TASK-602: Employee App First-Run Experience
- **Objective**: Audit and refine the initial launch experience of the Employee App on a fresh machine.
- **Scope**:
  - Server connection screen (`http://localhost:8000` default hint, connection test feedback).
  - Clear sign-up / login toggles with validation feedback.
  - Welcoming first-project state that guides the user to connect a codebase without overwhelming tour modals.
- **Acceptance Criteria**:
  - A first-time engineer can connect to their server, sign up/in, and arrive at project creation without ambiguity.

---

### TASK-603: Project Creation & Repository Connection Flow
- **Objective**: Ensure project creation and repository linking is robust, transparent, and resilient to user input variations.
- **Scope**:
  - Project name, description, and slug auto-generation.
  - Git repository connection (URL parsing, branch selection, credentials/token validation).
  - Real-time input validation and meaningful error messages for unreachable or private repos.
- **Acceptance Criteria**:
  - Invalid repository URLs or credentials produce immediate, clear remediation instructions without crashing or hanging.

---

### TASK-604: Ingestion Status & Progress Experience
- **Objective**: Provide honest, clear, and reassuring ingestion feedback.
- **Scope**:
  - Disclose exact ingestion phases: `CLONING` → `SCANNING` → `PARSING` → `INDEXING` → `READY`.
  - Avoid misleading progress bars if step-by-step progress cannot be strictly measured.
  - Provide a clear retry action if ingestion fails due to network or filesystem errors.
- **Acceptance Criteria**:
  - Ingestion state transitions are obvious; users never wonder if the worker is hung.

---

### TASK-605: Intelligence Views & Evidentiary Clarity
- **Objective**: Audit the intelligence views (Overview, Discoveries, Architecture, Files, Knowledge, Ask).
- **Scope**:
  - Overview: Key metrics, state assessment, and primary architecture areas.
  - Discoveries: Grouped findings (circular dependencies, coupling, test gaps) with actionable descriptions.
  - Architecture & Files: AST symbol hierarchy and clean syntax-highlighted code viewer.
  - Knowledge: Clear visual badges distinguishing team-curated knowledge from observed code facts.
  - Ask: Grounded responses with clickable evidence chips linking directly to file lines.
- **Acceptance Criteria**:
  - Every insight is backed by visible code evidence; AI marketing jargon is eliminated in favor of direct engineering facts.

---

### TASK-606: Plain-Language Error, Empty & Offline States
- **Objective**: Standardize and polish all empty, loading, error, and offline UI components.
- **Scope**:
  - Empty states for: No Projects, No Repositories, No Discoveries, No Knowledge Items, Empty Ask History.
  - Error states: Server Unreachable, 404 Not Found, 403 Forbidden, 500 Server Error.
  - Replace technical exception dumps in standard UI with plain-English problem + remediation suggestions.
- **Acceptance Criteria**:
  - Zero unhandled red Flutter error screens or unexplained empty white boxes across the app.

---

### TASK-607: Authentication, Session Restoration & 401 Recovery
- **Objective**: Ensure seamless session management and robust handling of token expiration.
- **Scope**:
  - Local token persistence (`StorageService`).
  - Auto-login on app launch if token is valid.
  - Clean logout mechanism.
  - Graceful interception of `401 Unauthorized` responses to redirect to login without application freeze.
- **Acceptance Criteria**:
  - Users are never trapped in a broken authenticated state or forced to manually clear local files.

---

### TASK-608: Server Setup App Customer Polish
- **Objective**: Polish the step-by-step Server Setup Application for non-expert system administrators.
- **Scope**:
  - Flow: Welcome → Target Selection → Pre-flight Checks → Configuration → Deploy → Verify → Ready.
  - Clear status indicators for Docker daemon, compose version, and port availability.
  - High-entropy secret generation with copy buttons.
  - Expandable "Technical Diagnostics" dialog for operators who need full container logs.
- **Acceptance Criteria**:
  - Setup wizard provides an error-free deployment experience with zero secret leakage.

---

### TASK-609: Platform Build Evaluation (Linux / macOS / Windows)
- **Objective**: Audit and document the exact desktop build status and platform capabilities.
- **Scope**:
  - Linux (native verified).
  - macOS and Windows (prerequisites, platform-specific constraints, build commands).
  - Honest disclosure of tier-1 vs. tier-2 supported client platforms.
- **Acceptance Criteria**:
  - Explicit, tested platform matrix documented in release notes.

---

### TASK-610: Packaging, Naming & Distribution Artifacts
- **Objective**: Standardize application packaging, binary naming, icons, and bundle metadata.
- **Scope**:
  - App names: "Unotusk" (Employee App) and "Unotusk Server Setup" (Setup App).
  - Version consistency: `0.1.0`.
  - Simple, repeatable archive packaging scripts for customer distribution.
- **Acceptance Criteria**:
  - Reproducible build scripts generate release-ready desktop binaries with consistent branding.

---

### TASK-611: Customer-Facing Performance & Latency Audit
- **Objective**: Verify snappy responsiveness across UI navigation, data retrieval, and AST parsing.
- **Scope**:
  - Cold startup < 1.5s for desktop clients.
  - Project workspace loading < 500ms.
  - File tree expansion and code viewer rendering < 100ms.
  - Ask query synthesis response time and offline fallback latency.
- **Acceptance Criteria**:
  - System meets customer responsiveness benchmarks under realistic repository sizes.

---

### TASK-612: Security, Secret Exposure & Isolation Verification
- **Objective**: Execute final security check for customer rollout.
- **Scope**:
  - Verify zero plaintext API keys in logs or UI.
  - Verify PostgreSQL & Redis host isolation.
  - Verify strict cross-tenant and cross-project query filtering.
- **Acceptance Criteria**:
  - 100% pass on security and tenant isolation test suites.

---

### TASK-613: Customer Quick-Start & Operations Documentation
- **Objective**: Produce unified, operator-ready documentation.
- **Scope**:
  - Quick-Start Guide (5-minute setup).
  - Employee App User Manual (finding code, asking questions, adding knowledge).
  - Customer Operations Runbook (backup, restore, troubleshooting).
- **Acceptance Criteria**:
  - Technical customers can deploy and use Unotusk without live engineering support.

---

### TASK-614: Repeatable Design Partner Demo Environment
- **Objective**: Create a deterministic, high-impact demonstration environment using a real benchmark repository (`psf/requests`).
- **Scope**:
  - Seed script / demo data loader with realistic architectural findings and curated team knowledge.
  - Step-by-step demo flow proving the 8 key customer value steps (Setup → Connect → Ingest → Understand → Discover → Investigate → Ask → Add Knowledge).
- **Acceptance Criteria**:
  - Demo can be reset and run reliably in under 3 minutes.

---

### TASK-615: Clean-Room Final Customer Journey Test
- **Objective**: Execute the complete end-to-end customer journey from scratch on a clean environment.
- **Scope**:
  - Clean server deploy via Setup App → Employee App server connection → User Sign-Up → Repository Ingestion → Exploration → Grounded Q&A → Knowledge Capture.
- **Acceptance Criteria**:
  - Complete customer workflow succeeds with zero workarounds or terminal interventions.

---

### TASK-616: MVP Release Gate & Final Disposition Report
- **Objective**: Execute full test validation and produce the final Phase 6 release disposition document.
- **Scope**:
  - Backend tests (unit + API), Flutter tests, linter, formatter, container build check.
  - Deliver `docs/PHASE_6_MVP_RELEASE_READINESS.md`.
- **Acceptance Criteria**:
  - Formal sign-off confirming Unotusk MVP is ready for real customer design partners.
