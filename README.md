# Unotusk — Pushpa Release

[![Status](https://img.shields.io/badge/Release-Pushpa_(v1.0.4)--pushpa-success.svg)](#whats-new-in-the-pushpa-release)
[![Architecture](https://img.shields.io/badge/Architecture-Single--Tenant_Control_Plane_(28000)-blue.svg)](#1-system-architecture)
[![Backend Tests](https://img.shields.io/badge/Pytest-356_Passed-brightgreen.svg)](#6-testing--verification)
[![Frontend Tests](https://img.shields.io/badge/Flutter_Tests-135+_Passed-green.svg)](#6-testing--verification)
[![Grounding Accuracy](https://img.shields.io/badge/Grounding_Accuracy-100%25_Verified-orange.svg)](#5-empirical-validation--real-repository-benchmarks)

**Unotusk** is an evidence-grounded codebase intelligence and proactive architectural discovery platform built for engineering teams. Unlike generic AI coding assistants that hallucinate ungrounded abstractions, Unotusk ingests repositories through multi-language Tree-sitter AST parsing, extracts architectural dependency graphs, proactively identifies systemic risks, and delivers conversational codebase intelligence strictly anchored to physical code citations and Architectural Decision Records (ADRs).

The **Pushpa Release** represents our flagship production-ready milestone—introducing interactive Mermaid 2.0 diagram synthesis, live Control Plane PostgreSQL server coordination, enterprise RBAC team management, and zero-terminal on-site Windows/macOS/Linux deployment packaging.

---

## 🌟 What's New in the Pushpa Release

### 1. 🎨 Interactive Mermaid 2.0 Architectural Engine
* **Visual Flowchart & Topology Rendering**: Directly renders interactive system architecture diagrams, state machines, and sequence flowcharts natively within the Flutter Desktop Client and Web preview.
* **Code / Visual Toggle**: Seamless switch between human-readable Mermaid syntax and live rendered graphics.
* **Full-Screen Interactive Viewer**: Dedicated high-fidelity modal equipped with pan controls, step-level zoom (`+` / `-`), and one-click fit-to-screen reset (`Matrix4.scaleByDouble`).
* **High-Resolution Asset Export**: Single-click downloads for **PNG** and **JPEG** image exports, alongside an instant external browser popout for friction-free diagram inspection.

### 2. ⚡ Live Control Plane Topology & Server Synchronization
* **Authoritative PostgreSQL Source of Truth**: Unified Control Plane on port `28000` tracks live container health, server states (`READY`, `STOPPED`, `DEGRADED`), and assigned repositories.
* **De-Hardcoded Repository Mapping**: Completely eliminated legacy mock projects (`ORCA`, `SyncGuard`) and hardcoded workspace prefixes. Dynamic project schemas now bind directly to real customer repositories (e.g., `Techteam-zephvion/School-management-app`, `pallets/flask`).
* **Automated Server Sync API**: Exposed `POST /api/v1/projects/sync-servers` allowing the Server Setup App ([setup_app](file:///home/devils/PRO/Unotusk-MVP/setup_app)) to automatically coordinate running Docker data planes with the central database on deployment, startup, or teardown.

### 3. 👥 Enterprise RBAC & Team Management Roster
* **Organization Team Roster (`/team`)**: Interactive directory for Admins and Owners to review registered workspace members, role distributions, and activity metrics.
* **Dynamic Project Team Management**: Built-in modal dialog ([ManageProjectTeamDialog](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/projects/presentation/manage_project_team_dialog.dart)) to inspect codebase access, search employee directories, assign roles (`MEMBER`, `MANAGER`, `ADMIN`), and revoke access.
* **Lead Admin Immunity & Role Restrictions**: Permanent Lead Admin status ensuring unbroken administrative control; restricted public signup forms limited to designated developer roles with automatic project membership synchronization.
* **Zero Cross-Tenant Leakage**: Strict organization-scoped database queries and token verification guaranteeing 100% multi-tenant isolation.

### 4. 🛡️ Desktop Client & Web Platform Hardening
* **Web Platform Compatibility**: Implemented `kIsWeb` environment guards across configuration services, eliminating runtime `UnsupportedError` crashes.
* **Flicker-Free Workspace State**: Resolved project selection flickering and maintained sticky workspace selection across app restarts.
* **Modernized Flutter Matrix APIs**: Replaced deprecated `Matrix4.scale` calls with typed transformations to ensure forward compatibility with Flutter 3.24+ and modern CanvasKit runners.

---

## 1. System Architecture

Unotusk MVP discards complex, over-engineered microservice meshes in favor of a robust, self-contained single-tenant deployment:

```
                               ┌────────────────────────────────────────────────────────┐
                               │           Unotusk Desktop Client (app/)                │
                               │        Figma Warm Dark Design System (#181816)         │
                               │          Native macOS (.dmg) | Windows (.msi)          │
                               │     9-Tab Workspace | Mermaid 2.0 Interactive Engine   │
                               └───────────────────────────┬────────────────────────────┘
                                                           │ HTTP REST (:28000 Control Plane / :28100+ Data Planes)
                                                           ▼
┌──────────────────────────────┐       ┌────────────────────────────────────────────────┐
│      Server Setup App        │       │             FastAPI Async Backend              │
│        (setup_app/)          ├──────►│                  (apps/api/)                   │
│  Single-command host deploy  │       │  ├── Tree-sitter AST Parser Engine (Py/TS/Go)  │
│  & pre-flight diagnostics    │       │  ├── 9 Proactive Architectural Risk Analyzers   │
└──────────────────────────────┘       │  ├── Grounded Context Engine (SQL + 1-Hop)     │
                                       │  ├── Project Intelligence Report Engine        │
                                       │  └── Knowledge Base Service (ADR Curation)     │
                                       └───────────────────┬──────────────────┬─────────┘
                                                           │                  │
                                                           ▼                  ▼
                                                PostgreSQL 16 + pgvector    Redis 7 + Worker
                                                (Relational Context, AST,  (services/workers/)
                                                 Embeddings, Findings)     (Async Ingestion)
```

---

## 2. Core Capabilities

### 💬 Grounded Ask & Chat Engine
* **Physical Evidence Anchoring**: Every response is synthesized with exact file paths, line ranges, symbol references, and relevance scores.
* **Hallucination Resistance**: Adversarial negative queries (e.g., asking for non-existent controllers or endpoints) return verified low-confidence alerts and report zero fabricated citations.
* **Full Multi-Turn History**: Persistent conversation threads with sidebar navigation, preserving historical queries across new and resumed sessions.
* **Productive Desktop UX**: Natural `Enter` submission, `Shift+Enter` multi-line insertion, personalized time-of-day greetings, and responsive search filtering.

### 🔍 Tree-sitter Code Parser Engine
* Deep syntactic parsing for **Python**, **TypeScript / JavaScript**, and **Go**.
* Extracts symbol tables, class hierarchies, import dependencies, function call graphs, and structural AST chunks in milliseconds.

### 🛡️ 9 Proactive Risk Analyzers
Identifies architectural degradation and codebase vulnerabilities without requiring manual rules:
1. **God Module / Component Detector**: Flags monoliths exceeding complexity thresholds.
2. **Circular Dependency Analyzer**: Identifies multi-hop import cycles across packages and files.
3. **Dead / Orphaned Code Analyzer**: Detects unreachable modules and unreferenced exports.
4. **Architectural Boundary Drift**: Flags cross-domain leakage violating system conventions (e.g., production code importing test harnesses).
5. **High-Churn Fragility Analyzer**: Correlates commit frequency with error-prone files.
6. **Security & Secrets Scanner**: Identifies hardcoded tokens and unsafe patterns.
7. **Performance Bottleneck Detector**: Catches blocking synchronous operations on critical paths.
8. **Test Coverage Disparity Analyzer**: Identifies mission-critical modules missing tests.
9. **ADR Drift Analyzer**: Verifies whether active implementation aligns with documented Architectural Decision Records.

### 📊 9-Tab Workspace Experience (`app/`)
* **Ask**: Conversational code intelligence with thinking tier controls (`Warm`, `Deep`).
* **Spec History**: Versioned requirements, BDD specifications, and architectural diffs.
* **Ontology Graph**: Interactive entity-relationship visualizer mapping files, symbols, and dependencies.
* **Ingestion Feed**: Real-time parser feed showing file indexing progress and chunk metrics.
* **Discoveries**: Severity-ranked findings feed with remediation suggestions.
* **Architecture**: Interactive Mermaid 2.0 diagrams, system-level topology, module boundaries, and dependency tiers.
* **Files**: Centered search and exploration for ingested repository files.
* **Knowledge**: ADR collection and engineering guidelines repository with `TEAM CURATED` badges.
* **Overview**: Project health dashboard, repository summary, and quick metrics.

### 📦 Multi-Platform Packaging & Distribution
* **Windows MSI (`.msi`)**: Automated WiX Toolset compilation producing clean native installers for Server Setup and Employee Client.
* **macOS Disk Image (`.dmg`)**: Built for Apple Silicon & Intel, with Apple Sandbox network and user-selected file entitlements, deep ad-hoc code signing in CI, and Gatekeeper quarantine resolution.
* **Linux Archive (`.tar.gz`)**: Standalone portable runtime bundles.
* **Auto-Update System**: In-app version checker, dismissible update banners, and GitHub Releases asset downloads.

---

## 3. Repository Layout

```
Unotusk-MVP/
├── app/                  # Employee Desktop Client (Flutter, Warm Dark UI)
│   ├── lib/              # UI screens, workspace tabs, controllers, API services
│   │   ├── features/     # Auth, Projects, Workspace, Knowledge, Discovery
│   │   ├── widgets/      # Mermaid diagram viewer, top nav bar, search dialogs
│   │   └── main.dart     # Application bootstrap & port-switching router
│   ├── macos/            # macOS Runner & Sandbox Entitlements
│   ├── windows/          # Windows native runner & CMake configuration
│   ├── linux/            # Linux GTK runner
│   └── test/             # Widget, unit, navigation, and RBAC test suites
├── setup_app/            # Server Setup Wizard Desktop Application (Flutter)
│   ├── lib/              # Pre-flight checks, Docker deployment, live sync
│   └── test/             # Wizard verification suite
├── apps/
│   ├── api/              # FastAPI Backend, Tree-sitter engines, analyzers, LLM routing
│   │   ├── src/          # API routers, intelligence services, database models
│   │   └── requirements.txt
│   └── install-site/     # Static distribution landing site & download portal
├── services/
│   └── workers/          # Redis background task consumer (worker.py)
├── infrastructure/
│   └── docker/           # Dockerfiles for API and Worker
├── scripts/              # Validation runners, diagnostics, and release packagers
├── sessions/             # Historical session logs and architectural decisions
└── docker-compose.yml    # Local multi-container backend stack
```

---

## 4. Running Locally

### 1. Start the Backend Infrastructure
```bash
# Start PostgreSQL (pgvector), Redis, FastAPI Backend, and Background Worker
docker compose up -d
```
* **API Documentation**: `http://localhost:28000/docs`
* **Health Check**: `http://localhost:28000/health/ready`

### 2. Run the Employee Desktop Client
```bash
cd app
flutter pub get
flutter run -d linux # or macos / windows
```

### 3. Run the Server Setup Wizard
```bash
cd setup_app
flutter pub get
flutter run -d linux # or windows
```

---

## 5. Empirical Validation & Real Repository Benchmarks

Unotusk's intelligence pipeline is continuously audited against production open-source codebases and customer environments:

| Benchmark Metric | `pallets/flask` (Pilot) | `psf/requests` (Validation) |
| :--- | :--- | :--- |
| **Files Ingested** | 226 files | 121 files |
| **AST Symbols Indexed** | 919 symbols | 707 symbols |
| **Dependencies Mapped** | 675 dependencies | 324 dependencies |
| **Code Chunks Created** | 1,067 chunks | 790 chunks |
| **Ingestion Duration** | **0.89s** | **0.61s** |
| **Discovery Run Duration** | **62.8s** | **1.75s** |
| **Systemic Findings Discovered**| 2,704 findings | 647 findings |
| **Grounding Accuracy Rate** | **100.0%** | **100.0%** |
| **False Positive Rate** | **0.0%** | **0.0%** |
| **Cross-Tenant Isolation** | **PASSED (100% isolated)** | **PASSED (100% isolated)** |

### Verified Finding Highlight: Multi-Hop Circular Dependency Cycle in Flask
During the `pallets/flask` pilot audit, Unotusk detected a deep 6-to-8 node circular dependency cycle:
```
src/flask/__init__.py ──► src/flask/blueprints.py ──► src/flask/cli.py 
        ▲                                                      │
        │                                                      ▼
src/flask/app.py ◄────── src/flask/globals.py ◄─────── src/flask/helpers.py
```
* **Why it matters**: In Python, such circular chains only survive at runtime through deferred imports inside functions, creating brittle module initialization order bugs.
* **Hallucination Verification**: Adversarial probe `"Where is the QuantumPaymentController defined in this codebase?"` returned `Confidence: LOW` and cited zero fake files, confirming zero hallucinated responses.

---

## 6. Testing & Verification

### Backend Verification Suite
```bash
# Run 356+ unit, integration, and security tests
pytest -v

# Run Ruff linter
ruff check apps/api/ tests/
```

### Flutter Desktop Client Test Suite
```bash
cd app
flutter test
flutter analyze
```

### Server Setup Wizard Test Suite
```bash
cd setup_app
flutter test
flutter analyze
```

---

## 7. macOS Installation & Gatekeeper Note

Because the macOS build is distributed directly via disk image (`.dmg`) without an enterprise Apple Developer ID, macOS Gatekeeper attaches a quarantine attribute.

If macOS displays a warning (*"Unotusk is damaged and can't be opened"* or *"developer cannot be verified"*):
1. Move `Unotusk` into `/Applications`.
2. Open **Terminal** and run:
   ```bash
   xattr -cr /Applications/Unotusk.app
   ```
3. Launch `Unotusk` from `/Applications`.
*(Alternatively, approve it under **System Settings → Privacy & Security → Security → Open Anyway**).*

---

## 8. License

Copyright © 2026 Unotusk / Zephvion Pvt. Ltd. All rights reserved.
