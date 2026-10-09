# Unotusk — Codebase Intelligence & Project Insights

**Unotusk** is an evidence-grounded codebase intelligence platform designed for engineering teams. It analyzes repositories through multi-language AST parsing, extracts architectural ontology graphs, proactively discovers systemic risks, and provides a conversational interface backed strictly by verified code evidence and Architectural Decision Records (ADRs).

---

## 1. System Architecture

```
                               ┌──────────────────────────────────────────────┐
                               │       Unotusk Desktop Client (app/)          │
                               │   Figma Warm Dark Design System (#181816)    │
                               │      Native macOS (.dmg) | Windows (.msi)    │
                               └──────────────────────┬───────────────────────┘
                                                      │ HTTP REST (:28000 / :8000)
                                                      ▼
┌──────────────────────────────┐       ┌──────────────────────────────────────┐
│  Server Setup App            │       │      FastAPI Async Backend           │
│  (setup_app/)                ├──────►│      (apps/api/)                     │
│  Single-command host deploy  │       │  ├── Tree-sitter Parser Engine       │
│  & pre-flight diagnostics    │       │  ├── 9 Proactive Risk Analyzers      │
└──────────────────────────────┘       │  ├── Grounded Context Engine         │
                                       │  ├── Project Intelligence Reports    │
                                       │  └── Knowledge Base Service (ADRs)   │
                                       └──────────────┬──────────────────┬────┘
                                                      │                  │
                                                      ▼                  ▼
                                           PostgreSQL 16 + pgvector    Redis 7 + Worker
                                           (Relational Context, AST,  (services/workers/)
                                            Embeddings, Findings)     (Async Ingestion)
```

---

## 2. Core Capabilities Built to Date

### 💬 Grounded Ask & Chat Engine
* **Evidence-Anchored Responses**: Every answer is synthesized with code citations, file paths, line ranges, and relevance scoring.
* **Full Multi-Turn History**: Persistent conversation threads with sidebar navigation, preserving historical queries across new and resumed sessions.
* **Productive Desktop UX**: Natural `Enter` submission, `Shift+Enter` multi-line insertion, personalized time-of-day greetings, and responsive search filtering.

### 🔍 Tree-sitter Code Parser Engine
* Deep syntactic parsing for **Python**, **TypeScript / JavaScript**, and **Go**.
* Extracts symbol tables, class hierarchies, import dependencies, function call graphs, and structural AST chunks.

### 🛡️ 9 Proactive Risk Analyzers
Identifies architectural degradation and codebase vulnerabilities without requiring manual rules:
1. **God Module / Component Detector**: Flags monoliths exceeding complexity thresholds.
2. **Circular Dependency Analyzer**: Maps dependency cycles across packages and files.
3. **Dead / Orphaned Code Analyzer**: Detects unreachable modules and unreferenced exports.
4. **Architectural Boundary Drift**: Flags cross-domain leakage violating system conventions.
5. **High-Churn Fragility Analyzer**: Correlates commit frequency with error-prone files.
6. **Security & Secrets Scanner**: Identifies hardcoded tokens and unsafe patterns.
7. **Performance Bottleneck Detector**: Catches blocking synchronous operations on critical paths.
8. **Test Coverage Disparity Analyzer**: Identifies mission-critical modules missing tests.
9. **ADR Drift Analyzer**: Verifies whether active implementation aligns with documented ADRs.

### 📊 9-Tab Workspace Experience (`app/`)
* **Ask**: Conversational code intelligence with thinking tier controls (`Warm`, `Deep`).
* **Spec History**: Versioned requirements, BDD specifications, and architectural diffs.
* **Ontology Graph**: Interactive entity-relationship visualizer mapping files, symbols, and dependencies.
* **Ingestion Feed**: Real-time parser feed showing file indexing progress and chunk metrics.
* **Discoveries**: Severity-ranked findings feed with remediation suggestions.
* **Architecture**: System-level topology, module boundaries, and dependency tiers.
* **Files**: Centered search and exploration for ingested repository files.
* **Knowledge**: ADR collection and engineering guidelines repository.
* **Overview**: Project health dashboard, repository summary, and quick metrics.

### 📦 Multi-Platform Packaging & Distribution
* **macOS Disk Image (`.dmg`)**: Built for Apple Silicon & Intel, with Apple Sandbox network and user-selected file entitlements, deep ad-hoc code signing in CI, and Gatekeeper quarantine resolution.
* **Windows MSI (`.msi`)**: Automated WiX Toolset compilation producing clean native installers.
* **Linux Archive (`.tar.gz`)**: Standalone portable runtime bundles.
* **Auto-Update System**: In-app version checker, dismissible update banners, and GitHub Releases asset downloads.

---

## 3. Repository Layout

```
install-unotusk/
├── app/                  # Employee Desktop Client (Flutter, Warm Dark UI)
│   ├── lib/              # UI screens, workspace tabs, controllers, API services
│   ├── macos/            # macOS Runner & Sandbox Entitlements
│   ├── windows/          # Windows native runner
│   ├── linux/            # Linux GTK runner
│   └── test/             # Widget, unit, and navigation test suites
├── setup_app/            # Server Setup Wizard Desktop Application (Flutter)
├── apps/
│   ├── api/              # FastAPI Backend, Tree-sitter engines, analyzers, LLM routing
│   │   ├── src/          # API routers, intelligence services, database models
│   │   └── requirements.txt
│   └── install-site/     # Static distribution landing site & download portal
├── services/
│   └── workers/          # Redis background task worker (worker.py)
├── infrastructure/
│   └── docker/           # Dockerfiles for API and Worker
├── .github/
│   └── workflows/
│       ├── ci.yml        # Continuous integration (Analyze, Unit, Widget Tests)
│       └── release.yml   # Multi-platform build & release pipeline (macOS DMG, Windows MSI, Linux)
└── docker-compose.yml    # Local multi-container backend stack
```

---

## 4. Running Locally

### 1. Start the Backend Infrastructure
```bash
# Start PostgreSQL (pgvector), Redis, FastAPI Backend, and Background Worker
docker compose up -d
```
* **API Documentation**: `http://localhost:8000/docs` (or configured host port `28000`)
* **Health Check**: `http://localhost:8000/health/ready`

### 2. Run the Employee Desktop Client
```bash
cd app
flutter pub get
flutter run
```

### 3. Run the Server Setup Wizard
```bash
cd setup_app
flutter pub get
flutter run
```

---

## 5. Testing & Verification

### Flutter Client Test Suite
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

### Backend Test Suite
```bash
cd apps/api
pytest -v
```

---

## 6. macOS Installation & Gatekeeper Note

Because the macOS build is distributed directly via disk image (`.dmg`) without an enterprise Apple Developer ID, macOS Gatekeeper attaches a quarantine attribute.

If macOS displays a warning (*"Unotusk is damaged and can't be opened"* or *"developer cannot be verified"*):
1. Move `Unotusk` into `/Applications`.
2. Open **Terminal** and run:
   ```bash
   xattr -cr /Applications/Unotusk.app
   ```
3. Launch `Unotusk` from `/Applications`.
*(Alternatively, approve it under **System Settings → Privacy & Security → Security → Open Anyway**).*
