# PHASE 5 — CUSTOMER-GRADE END-TO-END VALIDATION & RELEASE HARDENING

**Product Goal**: Validate, harden, and rigorously prove the complete customer journey from a fresh, supported host environment to usable, grounded project intelligence without requiring developer intervention or manual repairs.

---

## Status Matrix

| Task ID | Task Name | Status | Dependencies | Target Milestone |
|---|---|---|---|---|
| **TASK-501** | System Baseline & Architecture Validation | COMPLETED | - | System Baseline |
| **TASK-502** | Clean Environment Installation & Prerequisites | COMPLETED | TASK-501 | Installation Hardening |
| **TASK-503** | Database & Redis Persistence Regression | COMPLETED | TASK-502 | Persistence & Data Integrity |
| **TASK-504** | Full Server Restart Recovery | COMPLETED | TASK-503 | Recovery Verification |
| **TASK-505** | Real Employee App E2E Journey | COMPLETED | TASK-504 | End-to-End Product Flow |
| **TASK-506** | Real Repository Validation (`psf/requests`) | COMPLETED | TASK-505 | Real-World Intelligence |
| **TASK-507** | Grounding & Anti-Hallucination Verification | COMPLETED | TASK-506 | Intelligence Accuracy |
| **TASK-508** | Multi-Tenant & Cross-Project Isolation Audit | COMPLETED | TASK-507 | Security & Privacy |
| **TASK-509** | Secret Sanitization & Diagnostic Logging Audit | COMPLETED | TASK-508 | Security & Privacy |
| **TASK-510** | Production Configuration & Exposure Hardening | COMPLETED | TASK-509 | Production Hardening |
| **TASK-511** | Failure Injection, Retry & Safe Recovery | COMPLETED | TASK-510 | Resilience & Reliability |
| **TASK-512** | Operational Backup & Restore Procedures | COMPLETED | TASK-511 | Operational Continuity |
| **TASK-513** | Safe Reset & Uninstall Guardrails | COMPLETED | TASK-512 | Operational Continuity |
| **TASK-514** | Customer Operations Runbook & Documentation | COMPLETED | TASK-513 | Release Enablement |
| **TASK-515** | Clean-Room Final End-to-End Validation | COMPLETED | TASK-514 | Release Validation |
| **TASK-516** | Release Readiness Review & Disposition Report | COMPLETED | TASK-515 | Release Sign-Off |

---

## Detailed Task Specifications

### TASK-501: System Baseline & Architecture Validation
- **Objective**: Inspect, verify, and document the actual current architecture, component interactions, container boundaries, ports, environment configuration, database models, background queues, and intelligence engines.
- **Scope**:
  - Unotusk Server API (FastAPI, Alembic migrations 0001-0006).
  - Background worker queue (Celery/Redis worker).
  - Persistence layers (PostgreSQL 16 with pgvector, Redis 7).
  - Flutter Desktop Client ("Employee Application" in `app/`).
  - Flutter Desktop Wizard ("Server Setup Application" in `setup_app/`).
  - Container compose definitions (`docker-compose.yml`, `setup_app/lib/features/deploy/data/compose_generator.dart`).
- **Acceptance Criteria**:
  - The documented system baseline reflects active code truth, verified ports (5432, 6379, 8000), dependency order, health checks, and data models.
- **Status**: PENDING

---

### TASK-502: Clean Environment Installation & Prerequisites
- **Objective**: Validate the Server Setup Application against a clean supported machine without assuming development artifacts are present. Address discovered gaps where generated compose configurations depend on local relative paths (`context: .`).
- **Scope**:
  - Verify prerequisites checking (Docker Engine, Compose v2, storage space, port conflicts).
  - Verify container orchestration, `.env` file creation with `0600` permissions.
  - Verify API, Redis, and Postgres container boot sequence and health readiness (`/health` & `/health/ready`).
- **Acceptance Criteria**:
  - Setup wizard successfully deploys healthy containers on a clean host.
  - No relative build-context breakages on standalone deployment targets.
- **Status**: PENDING

---

### TASK-503: Database & Redis Persistence Regression
- **Objective**: Validate that customer data in PostgreSQL and state in Redis persist across service restarts, container recreation, and volume remounting.
- **Scope**:
  - Volume binding verification (`postgres_data`, `redis_data`).
  - Schema migration idempotency (`alembic upgrade head`).
  - In-place container restart and service recreation tests.
- **Acceptance Criteria**:
  - Re-running migrations or restarting containers causes zero data loss or schema degradation.
- **Status**: PENDING

---

### TASK-504: Full Server Restart Recovery
- **Objective**: Perform a complete lifecycle test: ingest project and repository, add custom knowledge and discoveries, stop all server containers, restart containers, re-authenticate, and verify all objects remain intact.
- **Scope**:
  - Verify Projects, Repositories, Files, Symbols, Dependencies, Discoveries, Intelligence Reports, and Knowledge items before and after server reboot.
- **Acceptance Criteria**:
  - 100% of persisted project entities, findings, and knowledge items survive server restarts.
- **Status**: PENDING

---

### TASK-505: Real Employee App E2E Journey
- **Objective**: Execute the complete real user flow through the Flutter Employee Application against the live server without mocking or backend database injection.
- **Scope**:
  - Server URL configuration → User Login → Project List → Repository Linking → Ingestion Trigger → Inspection of Files, Symbols, Dependencies → Discovery Feed & Finding Details → Architecture Component View → Knowledge Management → Grounded Ask Querying with Evidence Citations.
- **Acceptance Criteria**:
  - Employee App completes all UI workflows cleanly without unhandled exceptions or state synchronization failures.
- **Status**: PENDING

---

### TASK-506: Real Repository Validation (`psf/requests`)
- **Objective**: Ingest and process the real benchmark repository (`psf/requests`) on the current build and measure actual intelligence metrics.
- **Scope**:
  - File indexing, AST symbol extraction, dependency extraction, code chunking.
  - Automated discovery generation (security, architecture, quality, performance).
  - Grounded question-answering verification and customer knowledge creation.
- **Acceptance Criteria**:
  - Current build yields verifiable, high-fidelity symbols, dependencies, findings, and grounded answers on `psf/requests`.
- **Status**: PENDING

---

### TASK-507: Grounding & Anti-Hallucination Verification
- **Objective**: Strengthen regression tests against hallucination and verify strict evidentiary grounding.
- **Scope**:
  - Nonexistent files, nonexistent functions/classes, fabricated third-party dependencies.
  - Unanswerable or out-of-scope architectural queries.
  - Evidence citation validation (every claim must cite real chunks/symbols/files).
- **Acceptance Criteria**:
  - System cleanly refuses or explicitly qualifies responses when evidence is missing, never inventing facts.
- **Status**: PENDING

---

### TASK-508: Multi-Tenant & Cross-Project Isolation Audit
- **Objective**: Audit the entire query and retrieval data path for tenant and project boundaries.
- **Scope**:
  - Database queries across Organizations and Projects.
  - Retrieval engine chunk filtering.
  - Finding and report boundaries.
  - Conversation context and knowledge base isolation.
- **Acceptance Criteria**:
  - Zero cross-organization or cross-project data leakage across any API endpoint or intelligence retrieval.
- **Status**: PENDING

---

### TASK-509: Secret Sanitization & Diagnostic Logging Audit
- **Objective**: Audit all logging, error-handling, and diagnostic reporting paths in the backend and setup wizard.
- **Scope**:
  - LLM API keys (Groq, Anthropic), JWT `AUTH_SECRET`, Postgres credentials, Redis connection strings, authorization headers.
  - Setup app technical details dialog and error cards.
  - Docker container logs and traceback logging.
- **Acceptance Criteria**:
  - Sensitive credentials never appear in plaintext in logs, exception traces, or diagnostic UI cards.
- **Status**: PENDING

---

### TASK-510: Production Configuration & Exposure Hardening
- **Objective**: Audit and harden production configuration defaults across backend and Docker deployment.
- **Scope**:
  - Restrict host bindings (PostgreSQL and Redis should not be exposed externally in production unless required).
  - Verify CORS origins and disable Swagger/OpenAPI docs in production mode.
  - Validate non-default high-entropy credential generation.
- **Acceptance Criteria**:
  - Customer deployment avoids unnecessary network exposures or default credentials.
- **Status**: PENDING

---

### TASK-511: Failure Injection, Retry & Safe Recovery
- **Objective**: Test system resilience under realistic failure conditions.
- **Scope**:
  - Port collision, invalid database password, stopped Docker daemon.
  - Unreachable LLM provider API, malformed repository URL, worker process kill during ingestion.
- **Acceptance Criteria**:
  - Failures present human-readable remediation guidance with safe retry capabilities; no database corruption or zombie jobs.
- **Status**: PENDING

---

### TASK-512: Operational Backup & Restore Procedures
- **Objective**: Formulate and validate a minimal, safe, and practical operational backup and restore procedure for customer deployments.
- **Scope**:
  - PostgreSQL database dump & restore (`pg_dump` / `pg_restore`).
  - Persistent volume data management (`unotusk_postgres_data`).
  - Configuration and `.env` preservation.
- **Acceptance Criteria**:
  - Documented backup/restore procedure tested and proven to restore an instance to identical functional state.
- **Status**: PENDING

---

### TASK-513: Safe Reset & Uninstall Guardrails
- **Objective**: Audit and define safe, non-destructive defaults for uninstallation, container pruning, and system reset.
- **Scope**:
  - Distinguish between service teardown (`docker compose down`) and data destruction (`docker compose down -v`).
  - Prevent accidental customer data deletion.
- **Acceptance Criteria**:
  - Customer data is never deleted automatically or silently; destructive operations require explicit manual commands.
- **Status**: PENDING

---

### TASK-514: Customer Operations Runbook & Documentation
- **Objective**: Produce concise, operator-focused documentation covering requirements, installation, initial pairing, daily operations, troubleshooting, and maintenance.
- **Scope**:
  - System requirements, installation walk-through, first login and project creation, troubleshooting guide, backup/restore runbook.
- **Acceptance Criteria**:
  - Complete, readable operational documentation enabling a customer engineer to run Unotusk without reading source code.
- **Status**: PENDING

---

### TASK-515: Clean-Room Final End-to-End Validation
- **Objective**: Execute the complete customer journey from a clean state through setup wizard, deployment, employee app login, project ingestion, discovery inspection, grounded Q&A, server reboot, and recovery.
- **Scope**:
  - Run full test suites: Backend tests, Setup App tests, Employee App tests, Flutter analyze, Backend lint.
  - Record execution environment, commands, and verified outputs.
- **Acceptance Criteria**:
  - 100% test pass rate across all components; clean analyzer and linter output; complete journey succeeds.
- **Status**: PENDING

---

### TASK-516: Release Readiness Review & Disposition Report
- **Objective**: Deliver a comprehensive release readiness review (`docs/PHASE_5_RELEASE_READINESS.md`) summarizing system status, security posture, limitations, and defect classifications (P0-P3).
- **Scope**:
  - Final audit of architecture, security, persistence, operational procedures, and outstanding issues.
- **Acceptance Criteria**:
  - Formal disposition report delivered with zero unresolved P0 blockers.
- **Status**: PENDING
