# PHASE 8: IMPLEMENT THE ACTUAL UNOTUSK PRODUCT DESIGN

## Task Sheet & Architecture Mapping

**Document Version**: 1.0.0  
**Date**: September 18, 2026  
**Status**: COMPLETED & VERIFIED — ALL TASKS DONE

---

## 1. Executive Summary

This task sheet defines the migration path to merge the **Functional Unotusk MVP** (real FastAPI backend + PostgreSQL/pgvector database + Tree-sitter repository ingestion + grounded intelligence engine) with the **Intended Unotusk Product Design** (`Unotusk MVP Design`).

### Core Principle
- **Functionality**: Sourced strictly from the real Unotusk backend (`apps/api`). No mock data, no static placeholders, no fake analytics.
- **Visual & Interaction Model**: Sourced strictly from the designed Unotusk product experience (`docs/Unotusk MVP Design/Unotusk MVP Design`).

---

## 2. Architecture Comparison: Current MVP vs. Designed Product

| Dimension | Current MVP | Designed Unotusk Product |
|---|---|---|
| **Mental Model** | Traditional Project-first tabs (`Projects → Workspace → Overview/Discoveries/Architecture/Files/Knowledge/Ask`) | **Intelligence-first workspace** (`Ask / Investigation` as hero, surrounded by real project context, history, and deep inspection objects) |
| **Top Shell** | Top-nav tab strip (`DesktopScaffold`) | **Collapsible Left Sidebar** (72px ↔ 264px) + Minimal 52px Sticky Top Nav |
| **Primary Interaction** | Tab switching among 6 disparate views | **Grounded Ask inquiry** with live query generation, composite reasoning inspection, and deep object citations |
| **Secondary Views** | Standalone Overview/Files/Architecture pages | **Spec History**, **Ontology Graph**, and **Ingestion Feed** connected directly to repository entities |
| **Design Language** | Standard dark theme with Material elements | **Editorial Warm Dark Palette** (`#181816`, `#21211E`, `#DA7756` terracotta), Young/Instrument Serif + Inter + IBM Plex Mono typography |

---

## 3. Comprehensive Mapping: Design Element → Current MVP Functionality

| Design Component / View | Designed UI Behavior | Real MVP Backend / API Support | Flutter Implementation Plan | Status |
|---|---|---|---|---|
| **App Shell & Sidebar** | Collapsible sidebar (72px ↔ 264px), logo wordmark, New Query button, navigation items, recent queries list, user profile button + popover | `GET /api/v1/auth/me`, `GET /api/v1/projects`, `GET /api/v1/projects/{id}/conversations` | `SidebarScaffold` wrapping the active project workspace with real project selector & user profile session | **REAL BACKEND SUPPORTED** |
| **Ask / Investigation (Hero State)** | Instrument Serif h1 (`"Investigate your project?"`), disclaimer, 2×2 quick inquiry prompt cards | Grounded Ask API (`POST /api/v1/projects/{id}/intelligence/ask`) | `AskTab` hero state passing selected prompts directly to `intelligenceService.ask()` | **REAL BACKEND SUPPORTED** |
| **Ask Input Bar** | Multi-action `+` button, thinking tier selector (`Hot`, `Warm`, `Cold`), auto-suggestions, voice mic, terracotta submit | Real prompt submission, query parameters | `AskInputBar` connected to real text controller and query runner | **REAL BACKEND SUPPORTED** |
| **Constellation Loader** | SVG/Canvas animated nodes and edges displaying live ingestion, citation scoring, and deep graph scoring | Ingestion & query latency phases in `intelligence_service.py` | `ConstellationLoader` widget rendered while `askQuestion()` executes | **REAL BACKEND SUPPORTED** |
| **Grounded Answer Bubble** | Answer text with `[CONFIRMED]` / `[INFERRED]` tags, file citations with line ranges | `GroundedAnswer.evidence` (`EvidenceItem` list with `file`, `symbol`, `lines`, `snippet`, `relevance`) | `GroundedAnswerCard` with real citations linking to code/file viewer | **REAL BACKEND SUPPORTED** |
| **Reasoning Panel** | Expandable thought process accordion with composite score, components (Coverage, Directness, Recency, Authority), routing path | `confidence`, `related_entities`, `relevance` scores from context retriever | `ReasoningPanel` displaying real confidence breakdown from backend retriever | **REAL BACKEND SUPPORTED** |
| **Spec History View** | List of architecture decisions, query history, date filtering, confidence badges, FPR delta | `GET /api/v1/projects/{id}/conversations`, `GET /api/v1/projects/{id}/knowledge`, `GET /api/v1/projects/{id}/reports` | `SpecHistoryTab` populated with real conversation threads, generated reports, and verified ADR facts | **REAL BACKEND SUPPORTED** |
| **Ingestion Feed (Dashboard)** | Project status cards, UPS status, live ingestion status, files count, last ingestion timestamp, re-ingest action | `GET /api/v1/projects`, `GET /api/v1/projects/{id}/repository/context`, `POST /api/v1/projects/{id}/discover/trigger` | `IngestionFeedTab` bound to real repository snapshot status, total files/symbols, and real scan trigger | **REAL BACKEND SUPPORTED** |
| **Ontology Knowledge Graph** | Interactive node-edge graph representing Services, Decisions, Commits, Tickets, Threads, People | `ProjectSymbol`, `ProjectDependency`, `ProjectKnowledge`, `RepositoryContext` | `OntologyTab` rendering real symbols, dependencies, and architectural relations extracted by Tree-sitter | **REAL BACKEND SUPPORTED** |
| **Deep Project Inspection (Files, Symbols, Discoveries)** | Deep investigation of files, syntax highlighted code viewer, finding details | `GET /api/v1/projects/{id}/repository/files`, `GET /api/v1/projects/{id}/repository/files/{file_id}`, `GET /api/v1/projects/{id}/findings` | File drawer / detail modal opening directly from citation clicks and search | **REAL BACKEND SUPPORTED** |
| **Knowledge Management** | Customer-provided facts, provenance, archive, restore | `GET/POST/PATCH /api/v1/projects/{id}/knowledge` | Customer Knowledge dialog accessible from project workspace | **REAL BACKEND SUPPORTED** |
| **Authentication Flow** | OIDC Discovery, work email entry, SSO provider selection | `POST /api/v1/auth/login`, `POST /api/v1/auth/register`, `GET /api/v1/auth/me` | `LoginScreen` matching Figma OIDC discovery UI seamlessly connected to backend auth | **REAL BACKEND SUPPORTED** |
| **Settings & Profile Modal** | Profile avatar, general settings (theme, language), personalization, data controls, security (MFA, mTLS) | `User` domain model, local settings storage, connection state | `ChatGPTSettingsModal` managing active user profile, theme, and connection preferences | **REAL BACKEND SUPPORTED** |

---

## 4. Design Concepts Without Current Backend Support (Documented Gaps)

The following concepts appear in the visual prototype but are not yet implemented in the MVP backend. As required by the specification, **these will not be faked with mock APIs**:

1. **DESIGN CONCEPT — MULTI-TOOL CONNECTOR SYNC (JIRA / SLACK / CONFLUENCE)**:
   - *Design UI*: Shows external integration connectors in `PlusDropdown` and `Connected Apps`.
   - *Current Backend*: Ingestion currently runs on Git repositories via Tree-sitter AST parsing.
   - *Implementation Rule*: UI will show "Connectors (Git active — Jira/Slack available in Enterprise)" without mocking fake syncs.

2. **DESIGN CONCEPT — LIVE BDD COMPILER / GHERKIN TEST RUNNER**:
   - *Design UI*: Shows automated Gherkin test case execution inside BDD contract cards.
   - *Current Backend*: The LLM generates structured BDD scenarios and intent contracts as part of grounded intelligence.
   - *Implementation Rule*: BDD contract cards will display the LLM's generated Given/When/Then text and copy action without simulating fake automated test runs.

3. **DESIGN CONCEPT — CONTINUOUS FPR (FALSE POSITIVE RATE) ANALYTICS ENGINE**:
   - *Design UI*: Shows dynamic `FPR +0.08` delta trend calculations across multiple historical runs.
   - *Current Backend*: Precision is calculated per discovery run using finding confidence metrics.
   - *Implementation Rule*: The UI will display the real finding confidence score and ranking from `discovery_service.py` rather than synthetic FPR historical charts.

---

## 5. Proposed Incremental Implementation Order

```
[TASK-801: Design System Tokens]
       ↓
[TASK-802: Application Shell & SidebarScaffold]
       ↓
[TASK-803: Grounded Ask Workspace Integration]
       ↓
[TASK-804: Real Conversation History & Recent Queries]
       ↓
[TASK-805: Real Project Context & Switcher Integration]
       ↓
[TASK-806: Real Ingestion State Machine in Ingestion Feed]
       ↓
[TASK-807: Discoveries & Investigation Detail Drawer]
       ↓
[TASK-808: Customer Knowledge & Fact Provenance]
       ↓
[TASK-809: Deep Objects (Files, Symbols, Code Viewer)]
       ↓
[TASK-810: Design-Accurate Loading/Empty/Error States]
       ↓
[TASK-811: Pixel & Typography Refinement]
       ↓
[TASK-812: Interaction & Keyboard Shortcuts Fidelity]
       ↓
[TASK-813: Real Backend End-to-End Verification]
       ↓
[TASK-814: Real Repository Validation (psf/requests)]
       ↓
[TASK-815: Design vs Implementation Visual Audit]
       ↓
[TASK-816: UX & Regression Test Gate]
```

---

## 6. Detailed Task Specifications

### TASK-801 — Design System Extraction & Verification
- Verify and standardize all color tokens in `AppColors` against Figma CSS tokens (`#181816`, `#21211E`, `#2A2A26`, `#33332E`, `#DA7756`, `#E59866`, `#52B788`, `#E07A5F`, `#68A090`, `#F0EFEA`, `#A3A199`).
- Ensure font styles in `AppTextStyles` use Young Serif, Instrument Serif, Inter, and IBM Plex Mono.

### TASK-802 — Application Shell & Sidebar Integration
- Ensure `SidebarScaffold` seamlessly hosts the real active project from `selectedProjectProvider`.
- Add project switcher dropdown in sidebar header for seamless multi-project navigation.
- Connect profile pill button to real authenticated user name and email.

### TASK-803 — Ask / Grounded Investigation Workspace
- Wire `AskTab` query bar directly to `ref.read(workspaceRepositoryProvider).askQuestion(projectId, text)`.
- Connect returned citations (`EvidenceItem`) to click-through file viewer opening the real source file at exact line ranges.

### TASK-804 — Recent Queries & Conversation History
- Populate sidebar "RECENT" section from real `GET /api/v1/projects/{id}/conversations`.
- Selecting a recent inquiry loads the conversation messages from the backend.

### TASK-805 — Project Context & Repository Information
- Display real repository full name, branch, commit hash, and file/symbol counts in the project context header.

### TASK-806 — Ingestion Feed & State Machine
- Bind `IngestionFeedTab` to real repository ingestion states: `CLONING` → `SCANNING` → `PARSING` → `INDEXING` → `READY`.
- Wire `Re-ingest ↺` button to `POST /api/v1/projects/{id}/discover/trigger`.

### TASK-807 — Discoveries & Investigation Experience
- Provide access to real repository findings (`CRITICAL`, `HIGH`, `MEDIUM`) with recommendation cards, risk scores, and evidence links.

### TASK-808 — Knowledge Management Integration
- Allow creating, editing, archiving, and restoring customer knowledge items with real API synchronization.

### TASK-809 — Deep Project Objects (Files, Symbols, Dependencies)
- Integrate full code viewer with syntax highlighting and symbol search accessible from file citations in Ask answers.

### TASK-810 — Design-Accurate Feedback & Error States
- Provide design-accurate empty states, network error banners, and loading constellations.

### TASK-811 to TASK-816 — Polish, Verification & Regression Testing
- Verify all 36+ Flutter tests pass, run backend test suite, test against real `psf/requests` repository, build Linux release.

---

## 7. Acceptance Criteria
1. The application visual appearance matches the Unotusk design prototype 1:1.
2. Every interactive inquiry, citation, file view, and discovery runs against real backend endpoints.
3. Zero mock/synthetic data in production flows.
4. `flutter analyze` returns 0 errors and 0 warnings.
5. All automated unit and widget tests pass.
