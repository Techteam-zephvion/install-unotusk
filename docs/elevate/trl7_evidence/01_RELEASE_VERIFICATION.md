# UNOTUSK V1 — Release Verification Audit

**Audit Date:** 2026-11-03  
**Auditor:** Senior Software Architect & Technical Audit Lead  
**Evaluation Scope:** ELEVATE NxT TRL 7 Compliance — Task 1: Verify the Actual V1 Release  

---

## 1. Executive Summary & Verification Findings

This audit establishes the definitive baseline of the UNOTUSK codebase, resolving release version naming conflicts, identifying running binaries, verifying exact git commit states, and detailing component-level capabilities.

```
+-----------------------------------------------------------------------------------------+
|                               RELEASE AUDIT AT A GLANCE                                 |
+-----------------------------------------------------------------------------------------+
| Repository Origin    : https://github.com/Techteam-zephvion/Unotusk-MVP.git             |
| Active Branch        : main                                                             |
| Latest Commit SHA    : cbbbbae476be1bc8ae415494cb6808f97e20ec42 (cbbbbae)               |
| Active Release Tag   : v1.0.3-rudra (Commit 85239a2, 2026-10-13)                        |
| Deployment Manifest  : apps/install-site/version.json ("version": "1.0.3", "Rudra")     |
| Discrepancy Resolved : "v1.0.4 Pushpa" is an unstaged README draft, NOT a deployed tag  |
| Old Tag "v1.0.4"     : Pre-pivot legacy tag dated 2026-07-30 (Unotusk-2 monolithic era) |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Exact Git Repository State

Command Execution Output (`git status`, `git log`, `git show-ref`):

```bash
$ git status
On branch main
Your branch is up to date with 'origin/main'.
Changes not staged for commit:
  modified:   README.md
  modified:   docker-compose.yml
  modified:   scripts/seed_demo.py

$ git log -n 5 --format="%h %cd (%ci) %d %s" --date=short
cbbbbae 2026-10-13 (2026-10-13 18:41:22 +0530) (HEAD -> main, origin/main) fix(rbac): resolve User.is_active schema mismatch, Matrix4 scale deprecation, and org isolation in member sync
71c85f2 2026-10-13 (2026-10-13 17:34:02 +0530) Merge pull request #3 from Techteam-zephvion/Frontend-sidebar-extended
7a3ead7 2026-10-13 (2026-10-13 17:15:44 +0530) feat(server-sync): coordinate live server status with control plane postgres and de-hardcode repo mapping
6b53db5 2026-10-13 (2026-10-13 16:51:29 +0530) fix(auth): guarantee single-tenant org user sync and lead admin access in manage workspace
808b402 2026-10-13 (2026-10-13 16:35:12 +0530) fix(workspace): establish permanent lead admin status with full repository access
```

### Git Tag History & Lineage

The repository contains two distinct historical tagging epochs:

1. **Pre-Pivot Legacy Monolith Epoch (`Unotusk-2` / Multi-Service, July–August 2026):**
   - `v1.0.4`: Tagged Thu Jul 30 01:28:24 2026 (`7a28075070c7c2c9a8bce96c08b580ee2444513b`)
     *Commit message:* `"fix: correct GitHub org/repo to Techteam-zephvion/install-unotusk across all scripts"`
   - `v1.0.7`: Tagged Mon Aug 3 21:51:16 2026 (`575c396caa8e4ff05d36109f1aaf7636a1c564dc`)
     *Commit message:* `"fix: local-dev install.sh copied 70GB of build artifacts; wizard.sh arg mismatch"`
   *Audit Finding:* These tags belonged to the obsolete microservice architecture (US, UPS, Qdrant, Phoenix) that was discarded per `AGENTS.md` Section 0.

2. **Single-Tenant MVP Epoch (Hindu Codename Series, October 2026):**
   - `v1.0.1-rudra`: Tagged Sun Oct 4 2026 (`2c9a7b08a96cd8cd2988935e9acf69eb1be8fbb9`)
   - `v1.0.2-rudra`: Tagged Mon Oct 5 21:29:30 2026 (`f942c962d5a8d859b558f83eecd27bba30c070fc`)
     *Commit message:* `"feat(security): implement port 28000 series, workspace RBAC (Phase 1), and data plane security guardrails (Phase 2)"`
   - `v1.0.3-rudra`: Tagged Tue Oct 13 14:17:57 2026 (`85239a29aa625025a62d9a34d21c0719c491afb3`)
     *Commit message:* `"fix(windows): silence experimental coroutine deprecation warning for MSVC 14.51+ in CMake and CI"`
   - Followed by `a922d75` (*"chore(release): update install.unotusk.com links to v1.0.3-rudra"*).

---

## 3. Resolution of Version Discrepancy: `v1.0.2-rudra` vs `v1.0.4 Pushpa`

The technical audit investigated the apparent contradiction between `v1.0.2-rudra` / `v1.0.3-rudra` and `v1.0.4 Pushpa`:

1. **Root Cause Analysis:**
   - An unstaged edit in `README.md` (uncommitted in working directory) introduced the heading:  
     `# Unotusk — Pushpa Release` with badge `Release-Pushpa_(v1.0.4)--pushpa-success.svg`.
   - The developer drafted this README update locally on October 13 to describe four upcoming features:
     1. Interactive Mermaid 2.0 Architectural Engine
     2. Live Control Plane Topology & Server Synchronization (`POST /api/v1/projects/sync-servers`)
     3. Enterprise RBAC & Team Management Roster (`/team` screen)
     4. Desktop Client & Web Platform Hardening
   - However, **no Git tag named `v1.0.4-pushpa` or `pushpa` was ever created**.
   - Git tag `v1.0.4` in the repository points to commit `7a28075` from **July 30, 2026** (3 months prior), which has no relation to the Pushpa features.
   - The official deployment portal (`apps/install-site/version.json`) published to `install.unotusk.com` strictly specifies:
     ```json
     {
       "version": "1.0.3",
       "codename": "Rudra",
       "tag": "v1.0.3-rudra",
       "releaseDate": "2026-10-13",
       "channel": "stable",
       "repository": "Techteam-zephvion/install-unotusk"
     }
     ```

2. **Audit Conclusion on Versioning:**
   - **Currently Deployed Release Milestone:** **`v1.0.3-rudra`** (built and distributed via `install.unotusk.com`).
   - **Repository Head State:** Commit `cbbbbae` on `main` contains the unreleased changes slated for the next codename release ("Pushpa").
   - **Claiming `v1.0.4 Pushpa` as an already deployed TRL 7 release is indefensible and factually inaccurate.** The deployed release is `v1.0.3-rudra`.

---

## 4. Component-Level Version Matrix

| Subsystem | Configuration File / Code Path | Declared Version | Actual Runtime Value | Discrepancy Notes |
|:---|:---|:---|:---|:---|
| **Release Manifest** | `apps/install-site/version.json:2` | `1.0.3` | `1.0.3` ("Rudra") | Authoritative customer distribution manifest |
| **Backend API Engine** | `apps/api/src/main.py:35` | `0.1.0` | `0.1.0` | FastAPI metadata string was not incremented |
| **Backend Health Endpoint** | `apps/api/src/api/routes/health.py:18` | `0.1.0` | `0.1.0` | `/health` returns `{"version": "0.1.0"}` |
| **Desktop Client (app)** | `app/pubspec.yaml:4` | `1.0.0+1` | `1.0.0+1` | Flutter package version |
| **Desktop AppConfig** | `app/lib/app/config/app_config.dart:3` | `1.0.1` | `1.0.1` | Hardcoded internal string |
| **Server Setup Wizard** | `setup_app/pubspec.yaml:4` | `1.0.0+1` | `1.0.0+1` | Flutter package version |
| **Database Engine** | `docker-compose.yml:23` | `pgvector/pgvector:pg16` | PostgreSQL 16.3 + pgvector | Relational schema at Alembic head `0008` |
| **Task Broker** | `docker-compose.yml:37` | `redis:7-alpine` | Redis 7.2 | Async task queue for worker |
| **Container Networking** | Port Architecture | Control: `28000`, Data: `28100–28999` | Bound to `0.0.0.0:28000` | Replaced legacy `:8000` collision-prone ports |

---

## 5. Verified Working vs. Experimental Capabilities

### A. Fully Implemented & Working Capabilities (Evidence-Verified)

1. **Tree-sitter Multi-Language AST Parsing**:
   - Python, TypeScript/JavaScript, and Go AST parsing verified in `apps/api/src/services/parser/`.
   - Extracts symbol hierarchies, function declarations, class definitions, and exact line spans.
2. **Deterministic Proactive Discovery Engine (10 Analyzers)**:
   - `CircularDependencyAnalyzer`: Multi-hop cycle detection in dependency graphs.
   - `CouplingAnalyzer`: Fan-in/fan-out metric computation.
   - `ChangeRiskAnalyzer`: High churn and blast radius calculation.
   - `UnusedCodeAnalyzer`: Dead and unreachable export detection.
   - `DocumentationGapAnalyzer`: Public interface docstring auditing.
   - `DuplicationAnalyzer`: Cross-module code clone identification.
   - `ArchitectureAnalyzer`: Layering violation detection.
   - `LegacyAnalyzer`: Deprecated pattern and obsolescence auditing.
   - `TestGapAnalyzer`: Untested logic and test coverage gap detection.
   - `SecurityAnalyzer`: Hardcoded credentials and insecure pattern detection.
3. **Multi-Signal Context Retrieval & 2-Hop Graph Expansion**:
   - `MultiSignalRetriever` and `RelationshipExpander` in `apps/api/src/services/context_engine/`.
   - Combines symbol match (1.5x), file path match (1.3x), content match (1.1x), vector similarity (1.4x), and graph expansion (0.7x direct, 0.5x 2-hop).
4. **Flagship Project Intelligence Report Generation (10 Sections)**:
   - Deterministic fact assembly and structured markdown report synthesis (`apps/api/src/services/report_engine/`).
5. **Customer Knowledge Service (ADRs & Epistemic Separation)**:
   - Preserves user-supplied Architectural Decision Records and constraints (`apps/api/src/services/knowledge_service.py`), strictly segregated from observed code facts.
6. **Multi-Tenant Organization Isolation & Workspace RBAC**:
   - Alembic migration `0008` enforcing `organization_id` boundaries and `ProjectMembership` roles (`MEMBER`, `MANAGER`, `ADMIN`, `OWNER`).
7. **Offline Deterministic LLM Synthesizer Fallback**:
   - Multi-provider fallback (`apps/api/src/services/llm/`): Groq (`qwen/qwen3.8-27b`) / Claude 3.5 Sonnet, gracefully falling back to deterministic offline templating when disconnected.

### B. Experimental, Mocked, or Deliberately Out of Scope

1. **External Issue Trackers (Jira, Linear, Asana)**:
   - **NOT IMPLEMENTED IN BACKEND**. Jira only exists as a static UI toggle string in `settings_modal.dart`. `AGENTS.md` explicitly lists external connectors as out of scope.
2. **Feedback Propagation Rate (FPR) Instrumentation**:
   - **NOT IMPLEMENTED**. While static mock numbers appear in `SpecHistoryTab._demoSpecs`, there is zero calculation logic or database model tracking longitudinal FPR.
3. **Automated Code Mutation / PR Creation Bots**:
   - Read-only intelligence. Out of scope per `AGENTS.md` Section 2.
4. **Autonomous Cloud Telemetry / Central Heartbeats**:
   - Deliberately removed from `Unotusk-2` architecture. Operates strictly air-gapped / local single-tenant.

---

## 6. Build Artifacts on Disk

The following verified build artifacts are present in the repository and local environment:

| Build Artifact | Local File Path | Size | SHA-256 Checksum |
|:---|:---|:---|:---|
| **Employee Desktop Binary** | `/home/devils/.local/share/unotusk/client/bundle/app` | 24 KB (ELF) + 12.2 MB data | Verified runtime binary |
| **Employee Linux Tarball** | `dist/unotusk-employee-linux-x64.tar.gz` | 12,269,375 bytes | Verified via `dist/checksums.txt` |
| **Server Setup Binary** | `/home/devils/.local/share/unotusk/server-setup/bundle/setup_app` | 24 KB (ELF) + 10.0 MB data | Verified runtime binary |
| **Server Linux Tarball** | `/home/devils/.local/share/unotusk/server-setup/unotusk-server-linux-x64.tar.gz` | 10,061,312 bytes | Verified via `.sha256` manifest |
| **Docker API Image** | `ghcr.io/techteam-zephvion/unotusk-api:0.1.0` | Built locally / GHCR | Base image: `python:3.12-slim` |
| **Docker Worker Image** | `ghcr.io/techteam-zephvion/unotusk-worker:0.1.0` | Built locally / GHCR | Base image: `python:3.12-slim` |

---

## 7. Architectural Recommendation for CTO

1. **Standardize Semantic Version Strings**: Align `apps/api/src/main.py` (`0.1.0`), `app/pubspec.yaml` (`1.0.0+1`), and `AppConfig.appVersion` (`1.0.1`) with the authoritative release tag **`v1.0.3-rudra`**.
2. **Prevent Premature Codename Advertising**: Discard or stash the unstaged `README.md` reference to "v1.0.4 Pushpa" until code on `main` is tagged, packaged, and verified.
3. **Acknowledge Air-Gapped Scope**: Do not claim Jira integration in external audit filings; accurately state that Git-based ingestion is active and authoritative.
