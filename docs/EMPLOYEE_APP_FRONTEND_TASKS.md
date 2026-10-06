# Employee Desktop Client — Frontend Tasks & Engineering Roadmap

**Document Version**: `1.0.0`  
**Application**: Unotusk Employee Desktop Client (`app/`)  
**Target Platforms**: Linux (x64), Windows (x64), macOS (Universal)  
**Corporate Entity**: Unotusk Pvt. Ltd.  
**Design System**: 1:1 Warm Dark Editorial Figma Design System (`#181816` Base, `#DA7756` Terracotta Accent, Instrument / Young Serif, IBM Plex Mono)

---

## 1. Architecture & Technology Stack

The Unotusk Employee Desktop Client is a native, evidence-grounded desktop workspace built with Flutter. It provides developers and engineering leads with real-time architectural risk discovery, grounded intelligence Q&A with verifiable code citations, interactive ontology exploration, automated spec generation, and persistent customer knowledge.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   UNOTUSK EMPLOYEE DESKTOP CLIENT                      │
│                                (app/)                                  │
├────────────────────────────────────────────────────────────────────────┤
│ Presentation Layer (Riverpod Controllers, Warm Dark Editorial Widgets) │
│  ├── DesktopScaffold (Persistent Sidebar, Nav Rail, Account Dropdown)  │
│  ├── Projects Dashboard & Team Management (/team)                      │
│  └── WorkspaceScreen (9 Intelligence Tabs)                             │
│       ├── 01. OverviewTab        ├── 04. IngestionFeedTab ├── 07. Architecture │
│       ├── 02. AskTab             ├── 05. DiscoveriesTab   ├── 08. FilesTab    │
│       └── 03. SpecHistoryTab     ├── 06. OntologyTab      └── 09. KnowledgeTab│
├────────────────────────────────────────────────────────────────────────┤
│ Domain Layer (Immutable Entities, Value Objects, RBAC Getters)         │
│  ├── User, AuthState, Project, ProjectMember, OrganizationMember       │
│  └── GroundedAnswer, ProjectFinding, FileNode, ComponentNode, ADRs     │
├────────────────────────────────────────────────────────────────────────┤
│ Data Layer (Repositories, Networking, Persistent Storage)              │
│  ├── ApiClient (Dio, Bearer Auth Interceptor, 401 Session Interceptor) │
│  ├── StorageService (SharedPreferences token/server persistence)       │
│  └── AppLogger (Circular In-Memory Buffer, Secret Sanitizer)           │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Completed End-to-End Tasks (Employee App)

### 2.1 Design System & Component Library
- [x] **Warm Dark Color Palette ([`app/lib/app/theme/app_colors.dart`](file:///home/devils/PRO/Unotusk-MVP/app/lib/app/theme/app_colors.dart))**:
  - Background Hierarchy: `#181816` (`bgBase`), `#21211E` (`bgSurface`), `#2A2A26` (`bgElevated`), `#33332E` (`divider`).
  - Signature Accent: `#DA7756` (`primary` / Warm Terracotta), `#C86646` (`accentHover`), `#24DA7756` (`primaryMuted`).
  - Signal System: `#52B788` (`live` / active green), `#E07A5F` (`confirmed`), `#DA7756` (`inferred`), `#68A090` (`neutral` / info), `#E05A5A` (`error`), `#E59866` (`warning`).
- [x] **Editorial Typography System ([`app/lib/app/theme/app_text_styles.dart`](file:///home/devils/PRO/Unotusk-MVP/app/lib/app/theme/app_text_styles.dart))**:
  - Display & Headings: `Instrument Serif` / `Young Serif` (`displayLarge`, `h1`, `h2`, `h3`).
  - Body & Labels: Inter (`bodyLarge`, `bodyMedium`, `bodySmall`, `label`).
  - Code & Badges: `IBM Plex Mono` (`monoCode`, `monoBadge`, `monoSmall`).
- [x] **Theme Switching Foundation ([`app/lib/app/theme/theme_controller.dart`](file:///home/devils/PRO/Unotusk-MVP/app/lib/app/theme/theme_controller.dart))**:
  - Dark Mode (default primary) and Light Mode tokens with seamless theme switching.
- [x] **Core Reusable UI Components**:
  - [`AppButton`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/widgets/app_button.dart): Supports `primary`, `secondary`, `ghost`, and `destructive` variants with loading state.
  - [`AppCard`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/widgets/app_card.dart): Themed elevated container with border tokens and padding presets.
  - [`AppTextField`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/widgets/app_text_field.dart): Form text field with prefix/suffix icons, obscure text, and error states.
  - [`StatusBadge`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/widgets/status_badge.dart): Pill badges for `success`, `warning`, `error`, `info`, `neutral`, `confirmed`, `inferred`.
  - [`DesktopScaffold`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/widgets/desktop_scaffold.dart): Window frame layout with active navigation indicator, profile widget, and team link.
  - [`ConstellationLoader`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/constellation_loader.dart): Custom geometric SVG-like constellation animation for AI synthesis states.
  - [`EmptyStateView`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/widgets/empty_state_view.dart) & [`ErrorStateView`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/widgets/error_state_view.dart): Standardized fallback and error placeholders.

---

### 2.2 Connection & Authentication Layer
- [x] **LAN Server Discovery & Configuration ([`ServerConnectionScreen`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/connection/presentation/server_connection_screen.dart))**:
  - Live HTTP ping test to host URL with response latency badge (`<50ms`).
  - Custom IP / port input with persistence in `StorageService`.
- [x] **Diagnostic Logs Modal ([`DiagnosticLogsModal`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/logging/diagnostic_logs_modal.dart))**:
  - Circular in-memory logging buffer ([`AppLogger`](file:///home/devils/PRO/Unotusk-MVP/app/lib/core/logging/app_logger.dart)).
  - Automated regex redaction of Bearer tokens, raw JWTs, passwords, and database connection strings.
  - One-click copy and export of diagnostic event logs.
- [x] **User Authentication & Session Restoration ([`AuthController`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/auth/presentation/auth_controller.dart))**:
  - Email/password authentication via `/api/v1/auth/login`.
  - Secure token storage via `StorageService`.
  - Session auto-restore on launch with automatic redirection between `/login`, `/projects`, and `/server-connection`.

---

### 2.3 Role-Based Access Control (RBAC) & Team Management
- [x] **Role Modeling**:
  - [`User`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/auth/domain/user.dart): `isOwner`, `isAdmin`, `isMember` getters.
  - [`AuthState`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/auth/domain/auth_state.dart): Exposes `isAdmin`, `isOwner`, and `userRole`.
  - [`Project`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/projects/domain/project.dart): Exposes `role` and `isProjectAdmin`.
  - [`ProjectMember`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/projects/domain/project_member.dart): Role mapping for project teammates.
  - [`OrganizationMember`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/domain/organization_member.dart): Roster mapping for workspace accounts.
- [x] **Projects Dashboard Authorization ([`ProjectsScreen`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/projects/presentation/projects_screen.dart))**:
  - Gated "Add Codebase" button visible only to Organization Admins and Owners.
  - Project role badge on each project card showing `MEMBER` or `ADMIN`.
  - "Manage Team" action button visible strictly to Project Admins.
- [x] **Project Teammates Modal ([`ManageProjectTeamDialog`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/projects/presentation/manage_project_team_dialog.dart))**:
  - Displays current project members with avatars and role badges.
  - Invite colleague by email with role selector (`MEMBER` vs `ADMIN`).
  - Remove member action with immediate state refresh via [`project_members_controller.dart`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/projects/presentation/project_members_controller.dart).
- [x] **Organization Team Roster Screen ([`TeamManagementScreen`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/team_management_screen.dart))**:
  - Navigable route `/team` accessible from the sidebar and account menu for Admins/Owners.
  - Summary metric cards: Total Members, Admins, Regular Members.
  - Search filter input by member name or email.
  - Member cards with "YOU" tag for current user, role badge, and join date.

---

### 2.4 Workspace & 9 Feature Tabs

- [x] **Tab 1: Overview Tab ([`OverviewTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/overview_tab.dart))**:
  - [`OverviewMetricStrip`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/overview_metric_strip.dart): Key metrics (total files, AST nodes, critical risks, ADRs).
  - [`OverviewAttentionCard`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/overview_attention_card.dart): Highlights high-priority architectural violations requiring developer triage.
  - Quick action shortcuts to Ask tab, Discoveries tab, and Files tab.

- [x] **Tab 2: Ask Tab ([`AskTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/ask_tab.dart))**:
  - [`AskInputBar`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/ask_input_bar.dart): Query input with enter-to-submit, prompt suggestions, and thinking mode selector.
  - **Multi-Tier Thinking Modes**:
    - `Hot` (Deep Architectural Reasoning — `#E05A5A`)
    - `Warm` (Standard Evidence Grounded — `#E8A455`)
    - `Cold` (Fast Synthesizer / Offline Fallback — `#6EC8B8`)
  - [`GroundedAnswerCard`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/grounded_answer_card.dart): Markdown answer streaming with syntax-highlighted code fences.
  - [`EvidenceCitationChip`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/evidence_citation_chip.dart): Clickable file citation chips jumping directly to file lines in the Files tab.
  - [`ReasoningPanel`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/reasoning_panel.dart): Collapsible reasoning trace showing multi-signal graph hops.
  - [`AskHistorySidebar`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/ask_history_sidebar.dart): Previous query session history.

- [x] **Tab 3: Spec History Tab ([`SpecHistoryTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/spec_history_tab.dart))**:
  - Revision timeline of 10-section project intelligence reports.
  - Markdown spec viewer with table of contents jump links.
  - [`BddContractCard`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/bdd_contract_card.dart): Given/When/Then BDD scenario contract cards.

- [x] **Tab 4: Ontology Tab ([`OntologyTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/ontology_tab.dart))**:
  - Structural view of codebase ontology entities (Services, Repositories, Domain Models, Controllers).
  - Component dependency viewer with callers and callees.

- [x] **Tab 5: Ingestion Feed Tab ([`IngestionFeedTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/ingestion_feed_tab.dart))**:
  - [`IngestionProgressView`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/ingestion_progress_view.dart): Linear progress bar, parsed file counter, and phase indicator (Cloning -> AST Parsing -> Chunking -> Graph Building).
  - Detailed file status log table.

- [x] **Tab 6: Discoveries Tab ([`DiscoveriesTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/discoveries_tab.dart))**:
  - 9 Proactive Analyzer findings (Dead Code, Circular Dependencies, Security Hotspots, API Drift, Architectural Boundary Violations, etc.).
  - Severity filtering pills: `All`, `Critical`, `High`, `Medium`, `Low`.
  - [`FindingCard`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/finding_card.dart): Summary card with severity icon, file location, and affected component.
  - [`FindingDetailView`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/finding_detail_view.dart): Slide-over drawer with deep architectural explanation, impacted files, and remediation recommendations.

- [x] **Tab 7: Architecture Tab ([`ArchitectureTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/architecture_tab.dart))**:
  - High-level modular architecture breakdown.
  - Inbound and outbound dependency lists per component.

- [x] **Tab 8: Files Tab ([`FilesTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/files_tab.dart))**:
  - [`FileTreeView`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/file_tree_view.dart): Hierarchical folder tree with directory collapse/expand and icons.
  - [`FileSearchBar`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/file_search_bar.dart): Substring file search filter.
  - [`FileDetailPanel`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/file_detail_panel.dart): Side-by-side file detail view.
  - [`CodeViewer`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/code_viewer.dart): Syntax-colored source code preview with symbol list.

- [x] **Tab 9: Knowledge Tab ([`KnowledgeTab`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/knowledge_tab.dart))**:
  - [`KnowledgeCard`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/knowledge_card.dart): Persistent ADR and architectural constraint cards.
  - [`KnowledgeFormDialog`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/knowledge_form_dialog.dart): Modal to draft and commit new architectural decisions and guidelines.

---

## 3. Pending Tasks & Engineering Roadmap (Employee App Only)

### 3.1 Priority 0 — Critical Functional Enhancements

| Task ID | Component / File | Scope & Acceptance Criteria | Complexity |
|:---|:---|:---|:---:|
| **EMP-P0-01** | **Real-Time Ingestion Event Stream**<br>`features/workspace/presentation/tabs/ingestion_feed_tab.dart` | Replace 2-second polling with a real-time SSE (`EventSource`) or WebSocket channel connecting to `/api/v1/projects/{id}/ingestion/stream`. Smoothly animate the progress percentage and file counter without UI stutters. | Medium |
| **EMP-P0-02** | **Interactive 2D Graph Visualizer**<br>`features/workspace/presentation/tabs/ontology_tab.dart` & `architecture_tab.dart` | Replace the static text lists in `OntologyTab` with an interactive 2D canvas graph (using `CustomPainter` or a force-directed layout). Support zooming, panning, dragging component nodes, and clicking a node to reveal callers/callees. | High |
| **EMP-P0-03** | **Network Disconnect & Reconnect Banner**<br>`core/widgets/desktop_scaffold.dart` | Render an unobtrusive, non-modal top alert banner when the background ping fails. Display "Connecting to server..." with a reconnect retry button. Automatically resume session when server is reachable. | Low |
| **EMP-P0-04** | **Citation Click Cross-Navigation Deep Linking**<br>`features/workspace/presentation/widgets/evidence_citation_chip.dart` | Clicking an [`EvidenceCitationChip`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/evidence_citation_chip.dart) must switch tabs to `FilesTab`, expand the tree to that file, select it, and scroll the [`CodeViewer`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/widgets/code_viewer.dart) directly to the referenced line number. | Medium |

---

### 3.2 Priority 1 — Developer Experience & Workflow Productivity

| Task ID | Component / File | Scope & Acceptance Criteria | Complexity |
|:---|:---|:---|:---:|
| **EMP-P1-01** | **Global Keyboard Shortcuts & Command Palette**<br>`core/widgets/desktop_shortcuts.dart` | 1. Implement `Ctrl+1` through `Ctrl+9` (`Cmd+1`–`Cmd+9` on macOS) to instantly jump between the 9 workspace tabs.<br>2. Implement `Ctrl+K` (`Cmd+K`) opening a fuzzy-search Command Palette to jump to any file, symbol, or discovery finding. | Medium |
| **EMP-P1-02** | **Enhanced Code Viewer (Gutter Line Numbers & Themes)**<br>`features/workspace/presentation/widgets/code_viewer.dart` | Upgrade `CodeViewer` to render line numbers in the gutter, highlight lines referenced in findings, support double-click word selection, and provide a "Copy File Path" / "Copy Line Range" permalink button. | Medium |
| **EMP-P1-03** | **Finding Triage & Status Actions**<br>`features/workspace/presentation/widgets/finding_detail_view.dart` | Add triage action buttons in the finding drawer:<br>• "Mark Acknowledged"<br>• "Dismiss as False Positive" (with optional reason)<br>• "Promote to Architectural Constraint" (pre-fills `KnowledgeFormDialog`). | Medium |
| **EMP-P1-04** | **Ask Query Code Block Copy & Formatting**<br>`features/workspace/presentation/widgets/grounded_answer_card.dart` | Add a floating "Copy Code" button and language indicator header above all fenced code blocks rendered in Markdown responses. | Low |
| **EMP-P1-05** | **Multi-Turn Conversation Branching & Clear Thread**<br>`features/workspace/presentation/tabs/ask_tab.dart` | Add a "New Question / Clear Thread" action in the `AskTab` toolbar and display the active session conversation title in the header. | Low |

---

### 3.3 Priority 2 — Polish, Export & Performance

| Task ID | Component / File | Scope & Acceptance Criteria | Complexity |
|:---|:---|:---|:---:|
| **EMP-P2-01** | **Intelligence Report Export (PDF & Markdown)**<br>`features/workspace/presentation/tabs/spec_history_tab.dart` | Add an "Export Spec" action button that downloads the full 10-section report formatted as clean Markdown (`.md`) or compiled PDF (`.pdf`) for sharing outside the desktop client. | Medium |
| **EMP-P2-02** | **UI Density & Scaling Preference**<br>`features/settings/presentation/settings_screen.dart` | Add user-selectable UI scaling (90%, 100%, 110%, 125%) in Settings to support both compact laptop displays and high-resolution 4K external monitors cleanly. | Low |
| **EMP-P2-03** | **Local Cache & Offline Optimistic Reads**<br>`features/workspace/data/workspace_repository.dart` | Cache the file tree and discovery summaries in local SQLite/Hive storage so that switching codebases or re-opening the app displays previous data instantly before network sync finishes. | Medium |
| **EMP-P2-04** | **End-to-End Flutter Integration Test Suite**<br>`app/integration_test/` | Author integration tests using `package:integration_test` that boot the app, log in, navigate all 9 workspace tabs, submit an Ask query, and verify citation navigation. | Medium |

---

## 4. Verification & Testing Matrix for `app/`

All code modifications in `app/` must be verified using the local Flutter SDK:

```bash
# 1. Run static analysis (must report: No issues found!)
PATH=/home/devils/flutter/bin:$PATH flutter analyze app

# 2. Run unit and widget test suite
cd app
PATH=/home/devils/flutter/bin:$PATH flutter test

# 3. Run specific feature test files
PATH=/home/devils/flutter/bin:$PATH flutter test test/unit/rbac_domain_test.dart
PATH=/home/devils/flutter/bin:$PATH flutter test test/widget/thinking_tier_test.dart
PATH=/home/devils/flutter/bin:$PATH flutter test test/widget/workspace_navigation_header_test.dart
```

### Current Quality Baseline (as of 2026-10-06)
- **Static Analyzer**: **0 Errors, 0 Warnings**.
- **Unit & Widget Tests**: **59 / 59 Passed** (100% success rate).
- **Compilation Targets Verified**: Linux x64 bundle, Windows x64 runner, macOS runner.
