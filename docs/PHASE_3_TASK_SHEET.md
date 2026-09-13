# Unotusk Employee Application — Phase 3 Task Sheet
# Employee Usability, Refinement & Demo Validation

## Product Principle
**SIMPLE ON THE SURFACE. DEEP WHEN NEEDED.**
The Unotusk Employee Application must feel like a serious, calm, high-efficiency engineering tool.
It is not an AI showcase, ChatGPT clone, analytics dashboard, or marketing website.
Every screen communicates information naturally, with zero decorative clutter, no fake metrics, and deep progressive disclosure.

---

## Master Task Breakdown & Status Matrix

| Task ID | Task Name | Area | Dependencies | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TASK-301** | Global Navigation & Orientation Review | Navigation / Shell | Phase 2 Complete | DONE |
| **TASK-302** | Project Overview Screen Usability & Simplification | Overview | TASK-301 | DONE |
| **TASK-303** | File Tree & Code Inspection Ergonomics | Files / Code | TASK-301 | DONE |
| **TASK-304** | Architecture & Component Relationship Usability | Architecture | TASK-301, TASK-303 | DONE |
| **TASK-305** | Discovery Investigation & Action Workflow | Discoveries | TASK-301, TASK-303 | DONE |
| **TASK-306** | Project Knowledge Flow & Documentation Experience | Knowledge | TASK-301, TASK-303 | DONE |
| **TASK-307** | Grounded Ask & Project Search Refinement | Ask / Search | TASK-301, TASK-303 | DONE |
| **TASK-308** | Unified Object Cross-Navigation & Deep Links | Unified Graph | TASK-302 through TASK-307 | DONE |
| **TASK-309** | Robust Loading, Error, Empty & Offline Recovery States | State Resilience | TASK-308 | DONE |
| **TASK-310** | Desktop Keyboard Shortcuts & Window Ergonomics | Desktop Ergonomics | TASK-308 | DONE |
| **TASK-311** | Visual Consistency & UI De-cluttering Pass | UI Polish | TASK-309, TASK-310 | DONE |
| **TASK-312** | End-to-End Real Project Demo Validation (`psf/requests`) | Validation | TASK-311 | DONE |

---

## Detailed Task Specifications

### TASK-301: Global Navigation & Orientation Review
- **Task ID**: `TASK-301`
- **Task Name**: Global Navigation & Orientation Review
- **Problem being solved**: Employees need constant, unambiguous awareness of which project they are in, which workspace tab is active, what object is currently selected, and how to navigate back without getting trapped or losing context.
- **User-facing outcome**:
  - Clean project header showing active repository context, snapshot branch/commit, and clear `[< Projects]` back button.
  - Tab navigation bar clearly highlighting active section (`Overview`, `Discoveries`, `Architecture`, `Files`, `Knowledge`, `Ask`) with badge indicators for pending critical attention items.
  - Smooth tab switching preserving selection state where appropriate.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/workspace_screen.dart`
  - `app/lib/core/widgets/desktop_scaffold.dart`
- **Backend/API dependency**:
  - `GET /projects/{id}`
  - `GET /projects/{id}/repository`
- **Implementation steps**:
  1. Refine `WorkspaceScreen` header with concise project metadata (repo name, active branch, snapshot commit hash).
  2. Add attention counter indicator on the Discoveries tab title when unresolved critical findings exist.
  3. Ensure active tab and sub-navigation state transitions are instant and predictable.
- **Acceptance criteria**:
  - Employee can switch between all 6 tabs without state loss or flickering.
  - Back button navigates back to Projects list seamlessly.
- **Tests required**:
  - Widget test for workspace header, orientation labels, and navigation bar.
- **Manual verification**:
  - Switch tabs, check active states, navigate back to Projects screen and re-enter.
- **Status**: `DONE`

---

### TASK-302: Project Overview Screen Usability & Simplification
- **Task ID**: `TASK-302`
- **Task Name**: Project Overview Screen Usability & Simplification
- **Problem being solved**: Overview must instantly answer "What is this project and what needs attention?" without feeling like a generic analytics scorecard or marketing dashboard.
- **User-facing outcome**:
  - Clean, high-density facts strip: Primary Language, Total Files, Parsed Symbols, Tracked Dependencies.
  - Direct "Needs Attention" list highlighting critical findings or high-coupling nodes with instant `[Open in Discoveries]` or `[Open in Files]` actions.
  - Language distribution and active snapshot metadata formatted calmly as clean text rows rather than loud cards.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/tabs/overview_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/overview_metric_strip.dart`
  - `app/lib/features/workspace/presentation/widgets/overview_attention_card.dart`
- **Backend/API dependency**:
  - `GET /projects/{id}/repository`
  - `GET /projects/{id}/findings?severity=CRITICAL&status=OPEN`
- **Implementation steps**:
  1. Remove decorative uppercase labels and overly heavy borders in `OverviewMetricStrip`.
  2. Simplify `OverviewAttentionCard` to clean, scannable rows with direct action buttons.
  3. Ensure empty state ("All critical items resolved") is concise and reassuring.
- **Acceptance criteria**:
  - Overview renders all metrics calmly in under 1 second.
  - Clicking `[Open]` on an attention card jumps immediately to the exact finding or file.
- **Tests required**:
  - Unit/widget tests verifying metric strip formatting and attention item navigation.
- **Manual verification**:
  - Verify overview layout at 1280x720 and 1920x1080 window sizes.
- **Status**: `DONE`

---

### TASK-303: File Tree & Code Inspection Ergonomics
- **Task ID**: `TASK-303`
- **Task Name**: File Tree & Code Inspection Ergonomics
- **Problem being solved**: Browsing and inspecting source code must feel effortless, fast, and structured, prioritizing code readability and structural navigation without turning into a bloated IDE clone.
- **User-facing outcome**:
  - Clean, collapsible directory tree with folder icons, language badges, and line count indicators.
  - Fast file search input with instant query clearing (`Esc` or `X`).
  - Code Viewer with readable monospace typography, line numbers, and distinct highlight tint for targeted line ranges.
  - Symbols list showing classes/functions with one-click jump to highlight the exact lines in code.
  - Dependencies segment showing upstream callers ("Used by") and downstream imports.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/tabs/files_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/file_tree_view.dart`
  - `app/lib/features/workspace/presentation/widgets/file_detail_panel.dart`
  - `app/lib/features/workspace/presentation/widgets/code_viewer.dart`
- **Backend/API dependency**:
  - `GET /projects/{id}/files`
  - `GET /projects/{id}/files/{file_id}`
- **Implementation steps**:
  1. Refine tree row spacing, hover states, and folder expansion animations.
  2. Ensure `CodeViewer` auto-scrolls or visibly aligns with target highlighted line ranges.
  3. Polish `FileDetailPanel` segment switcher (`Code` | `Symbols` | `Dependencies`).
- **Acceptance criteria**:
  - Opening any file displays code, AST symbols, and dependencies without errors.
  - Clicking a symbol in the Symbols tab highlights the corresponding line range in Code view.
- **Tests required**:
  - Widget tests for tree navigation, search filtering, symbol jump, and line range highlight.
- **Manual verification**:
  - Open `requests/sessions.py` or `requests/adapters.py` and jump across symbols.
- **Status**: `DONE`

---

### TASK-304: Architecture & Component Relationship Usability
- **Task ID**: `TASK-304`
- **Task Name**: Architecture & Component Relationship Usability
- **Problem being solved**: Engineers need to understand component relationships (who calls what, what depends on what) quickly without being overwhelmed by noisy, unreadable node graphs.
- **User-facing outcome**:
  - Components search filter allowing instant lookup of any module or class (e.g. `adapters`, `sessions`, `models`).
  - Left component selector sorted by caller count (most central modules first).
  - Right relationship inspector clearly distinguishing internal callers, internal dependencies, and external third-party packages.
  - `[Open in Files]` action button on every caller and dependency target to jump directly to code.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/tabs/architecture_tab.dart`
- **Backend/API dependency**:
  - `GET /projects/{id}/dependencies`
  - `GET /projects/{id}/symbols`
- **Implementation steps**:
  1. Add real-time text search filter to the components list on the left pane.
  2. Refine caller and dependency target list items with clean file path badges and line numbers.
  3. Wire `[Open in Files]` buttons to cross-navigate to the target file.
- **Acceptance criteria**:
  - Search input instantly filters component list.
  - Selecting any component displays its incoming callers and outgoing dependencies.
- **Tests required**:
  - Widget tests for component searching, selection, and cross-navigation.
- **Manual verification**:
  - Select `adapters.py`, verify `urllib3` dependency and caller files list.
- **Status**: `DONE`

---

### TASK-305: Discovery Investigation & Action Workflow
- **Task ID**: `TASK-305`
- **Task Name**: Discovery Investigation & Action Workflow
- **Problem being solved**: Architectural findings, circular dependencies, and high coupling must be clear, actionable, and easy to resolve, without surfacing raw system noise.
- **User-facing outcome**:
  - Discoveries feed with severity indicators (Critical, High, Medium, Low) and concise titles.
  - Filter controls for Severity, Category, and Status (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`).
  - Investigation pane presenting "What was detected", "Why it matters", "Actionable Recommendation", affected files, and deterministic code evidence snippets.
  - One-click lifecycle action buttons (`Acknowledge`, `Resolve`, `Dismiss`, `Reopen`).
  - "Ask about finding" shortcut button that opens Grounded Ask with context pre-populated.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/tabs/discoveries_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/finding_card.dart`
  - `app/lib/features/workspace/presentation/widgets/finding_detail_view.dart`
- **Backend/API dependency**:
  - `GET /projects/{id}/findings`
  - `PATCH /projects/{id}/findings/{id}`
  - `POST /projects/{id}/discover`
- **Implementation steps**:
  1. Polish status transition buttons and provide visual feedback upon mutation.
  2. Refine evidence snippet formatting with line numbers and file paths.
  3. Wire affected entity chips to open File Detail in the Files tab.
- **Acceptance criteria**:
  - Updating finding status persists to backend and updates list badge immediately.
  - Clicking affected file opens the file in Files tab.
- **Tests required**:
  - Widget tests for findings filtering, investigation pane, status mutations, and cross-links.
- **Manual verification**:
  - Open finding, change lifecycle status to ACKNOWLEDGED / RESOLVED, click on affected entity file.
- **Status**: `DONE`

---

### TASK-306: Project Knowledge Flow & Documentation Experience
- **Task ID**: `TASK-306`
- **Task Name**: Project Knowledge Flow & Documentation Experience
- **Problem being solved**: Institutional knowledge (architectural decisions, business rules, constraints) must feel like natural project documentation rather than an opaque "AI memory" feature.
- **User-facing outcome**:
  - Clean list of project knowledge notes with category badges, author email, creation date, and content preview.
  - Category filters (`Architecture Decision`, `Business Rule`, `Intent`, `Constraint`, `Exception`, `Critical Component`).
  - Status toggle (`Active` vs `Archived`).
  - Modal form dialog to add and edit knowledge items with optional file and symbol links.
  - Quick actions to Edit, Archive, or Restore knowledge items.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/tabs/knowledge_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/knowledge_card.dart`
  - `app/lib/features/workspace/presentation/widgets/knowledge_form_dialog.dart`
- **Backend/API dependency**:
  - `GET /projects/{id}/knowledge`
  - `POST /projects/{id}/knowledge`
  - `PATCH /projects/{id}/knowledge/{id}`
  - `POST /projects/{id}/knowledge/{id}/archive`
  - `POST /projects/{id}/knowledge/{id}/restore`
- **Implementation steps**:
  1. Refine form validation and category selector in `KnowledgeFormDialog`.
  2. Implement search filter matching title, content, or linked file paths.
  3. Ensure archive/restore actions update provider state immediately with user feedback.
- **Acceptance criteria**:
  - Employee can create a new note, verify it in the list, edit it, archive it, and restore it.
  - Linked file path badge navigates directly to Files tab.
- **Tests required**:
  - Widget tests for knowledge CRUD, category filtering, search, and navigation.
- **Manual verification**:
  - Add architectural decision note, link `src/requests/adapters.py`, click link, archive item.
- **Status**: `DONE`

---

### TASK-307: Grounded Ask & Project Search Refinement
- **Task ID**: `TASK-307`
- **Task Name**: Grounded Ask & Project Search Refinement
- **Problem being solved**: The Ask tab must function as a high-precision project search and investigation tool with verifiable citations, not a generic chatbot with conversational fluff.
- **User-facing outcome**:
  - Clean inquiry prompt: "Search or ask about this project (e.g. Where is connection pooling configured?)".
  - Grounded answer presentation where factual explanation and supporting evidence citations (`file.py:L10-L25`) take priority.
  - Clickable evidence citation chips (`adapters.py:45-80`) jumping straight to code and highlighting lines.
  - Investigation history sidebar allowing recall of previous inquiries or starting a fresh inquiry.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/tabs/ask_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/grounded_answer_card.dart`
  - `app/lib/features/workspace/presentation/widgets/evidence_citation_chip.dart`
  - `app/lib/features/workspace/presentation/widgets/ask_history_sidebar.dart`
- **Backend/API dependency**:
  - `POST /projects/{id}/ask`
  - `GET /projects/{id}/conversations`
- **Implementation steps**:
  1. Add helpful suggested inquiry prompts for quick exploration.
  2. Polish citation chips with line numbers and monospace styling.
  3. Ensure `Enter` key submits question and input is disabled during execution with a calm spinner.
- **Acceptance criteria**:
  - Submitting inquiry returns grounded response with citations.
  - Clicking any citation opens the exact file in Files tab with line range highlighted.
- **Tests required**:
  - Widget tests for question submission, citation rendering, and citation cross-navigation.
- **Manual verification**:
  - Ask "Where is connection pooling configured?", click `adapters.py:45-80`, verify file opens.
- **Status**: `DONE`

---

### TASK-308: Unified Object Cross-Navigation & Deep Links
- **Task ID**: `TASK-308`
- **Task Name**: Unified Object Cross-Navigation & Deep Links
- **Problem being solved**: All project objects (Overview attention items, Files, AST symbols, Dependencies, Discoveries, Knowledge notes, Ask citations) must feel like a single connected graph.
- **User-facing outcome**:
  - Overview -> Attention item -> Jumps to Finding or File.
  - Finding -> Affected entity -> Jumps to File and Symbol.
  - Finding -> "Ask about finding" -> Opens Ask tab with pre-filled question.
  - Knowledge note -> Related file -> Jumps to File in Files tab.
  - Ask citation -> Jumps to File and highlights exact line range.
  - Architecture component -> "Open in Files" -> Jumps to File in Files tab.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/workspace_screen.dart`
  - All workspace tab widgets and navigation callbacks.
- **Backend/API dependency**:
  - None (Client-side coordination).
- **Implementation steps**:
  1. Audit all navigation callbacks across `OverviewTab`, `DiscoveriesTab`, `ArchitectureTab`, `FilesTab`, `KnowledgeTab`, and `AskTab`.
  2. Ensure target file selection and line highlight states are consistently passed and cleared upon user dismissal.
- **Acceptance criteria**:
  - Seamless bidirectional navigation across all 6 workspace tabs without getting stuck.
- **Tests required**:
  - Comprehensive integration test `cross_navigation_test.dart` verifying all cross-tab paths.
- **Manual verification**:
  - Perform the full cross-navigation loop from Overview -> Finding -> Ask -> Citation -> File -> Architecture.
- **Status**: `DONE`

---

### TASK-309: Robust Loading, Error, Empty & Offline Recovery States
- **Task ID**: `TASK-309`
- **Task Name**: Robust Loading, Error, Empty & Offline Recovery States
- **Problem being solved**: If the backend is slow, disconnected, or returns empty datasets, the application must stay calm, provide concise feedback, and offer an immediate `[Retry]` action without crash or unhandled null errors.
- **User-facing outcome**:
  - Uniform loading state indicators (`Loading project files...`, `Loading findings...`).
  - Friendly, concise error states with `[Retry]` action.
  - Reassuring empty states with actionable guidance.
  - Server connection footer indicating connection status and allowing server URL reconfiguration.
- **Existing implementation affected**:
  - `app/lib/core/widgets/loading_state_view.dart`
  - `app/lib/core/widgets/error_state_view.dart`
  - All workspace tabs and controllers.
- **Backend/API dependency**:
  - `GET /health`
- **Implementation steps**:
  1. Audit error handling in all Riverpod providers and async state views.
  2. Ensure error messages do not expose raw stack traces or internal JSON parsing dumps.
  3. Verify retry callbacks trigger clean provider invalidation and refetching.
- **Acceptance criteria**:
  - Simulated network failure displays clean error view with functional `[Retry]` button.
- **Tests required**:
  - Widget tests for loading, error, and empty states across tabs.
- **Manual verification**:
  - Add decision, edit title/content, archive item, verify item updates without page reload.
- **Status**: `DONE`

---

### TASK-310: Desktop Keyboard Shortcuts & Window Ergonomics
- **Task ID**: `TASK-310`
- **Task Name**: Desktop Keyboard Shortcuts & Window Ergonomics
- **Problem being solved**: Desktop engineering tools must support fast keyboard navigation, smooth resizing between 1280x720 and 1920x1080, and standard shortcuts.
- **User-facing outcome**:
  - `Ctrl/Cmd + 1` through `Ctrl/Cmd + 6` for instant tab switching.
  - `Ctrl/Cmd + F` for quick focus on search input in Files, Knowledge, and Architecture.
  - `Ctrl/Cmd + K` for quick focus on Ask inquiry prompt.
  - `Escape` key closes open dialogs, clears active search, or closes detail panels.
  - Responsive split-panes maintaining minimum widths without text clipping or overflow yellow/black bars.
- **Existing implementation affected**:
  - `app/lib/features/workspace/presentation/workspace_screen.dart`
  - `app/lib/features/workspace/presentation/tabs/files_tab.dart`
  - `app/lib/features/workspace/presentation/tabs/ask_tab.dart`
  - `app/lib/core/widgets/desktop_scaffold.dart`
- **Backend/API dependency**:
  - None.
- **Implementation steps**:
  1. Wrap `WorkspaceScreen` in `Shortcuts` and `Actions` handling global hotkeys.
  2. Add `FocusNode` management for instant search focusing.
  3. Verify split-pane flex ratios across window resizing.
- **Acceptance criteria**:
  - Pressing `Ctrl+1` through `Ctrl+6` switches tabs instantly.
  - Pressing `Escape` closes dialogs and dismisses active selections cleanly.
- **Tests required**:
  - Widget test verifying keyboard shortcut actions.
- **Manual verification**:
  - Resize desktop window to 1280x720, 1440x900, 1920x1080 and test keyboard navigation.
- **Status**: `DONE`

---

### TASK-311: Visual Consistency & UI De-cluttering Pass
- **Task ID**: `TASK-311`
- **Task Name**: Visual Consistency & UI De-cluttering Pass
- **Problem being solved**: Eliminate any remaining decorative AI badges, inconsistent margins, extraneous borders, and visual noise to achieve a cohesive, calm slate design system.
- **User-facing outcome**:
  - Uniform typography hierarchy (H1, H2, Body, Monospace) across all 6 tabs.
  - Curated slate color palette (slate-50 to slate-950) with subtle borders and zero gradients.
  - Removal of unnecessary headings, decorative pills, and redundant AI confidence labels.
- **Existing implementation affected**:
  - `app/lib/app/theme/app_colors.dart`
  - `app/lib/app/theme/app_text_styles.dart`
  - All workspace presentation widgets.
- **Backend/API dependency**:
  - None.
- **Implementation steps**:
  1. Audit all card margins, paddings, and border radiuses (standardizing on 6-8px).
  2. Remove any remaining redundant labels or decorative icons.
  3. Ensure active, hover, and focus states are visually consistent.
- **Acceptance criteria**:
  - `flutter analyze` passes with 0 issues.
  - Entire UI feels cohesive, polished, and professional.
- **Tests required**:
  - Visual consistency and golden/widget regression tests.
- **Manual verification**:
  - Full UI walkthrough across all screens.
- **Status**: `DONE`

---

### TASK-312: End-to-End Real Project Demo Validation (`psf/requests`)
- **Task ID**: `TASK-312`
- **Task Name**: End-to-End Real Project Demo Validation (`psf/requests`)
- **Problem being solved**: Validate the complete end-to-end employee workflow against real ingested project data (`psf/requests`) to ensure 100% demo readiness with zero mock data.
- **User-facing outcome**:
  - Flawless walkthrough: Login -> Projects -> psf/requests -> Overview metrics -> Browse files -> Inspect `sessions.py` code & symbols -> Review circular dependency discovery -> Ask grounded question -> Open evidence citation in code -> Add architectural knowledge note -> Verify note appears in active list -> Archive note -> Verify archived list.
- **Existing implementation affected**:
  - Entire application.
- **Backend/API dependency**:
  - Live FastAPI backend (`http://localhost:8000`) with ingested `psf/requests`.
- **Implementation steps**:
  1. Run backend server with ingested `psf/requests` repository.
  2. Execute complete 15-step employee productivity workflow.
  3. Verify all data matches reality and navigation is completely frictionless.
- **Acceptance criteria**:
  - All 15 steps execute cleanly without UI glitches, console errors, or network failures.
  - 100% Flutter and backend tests passing.
- **Tests required**:
  - Full test suite: `flutter test` (all tests passing) and `pytest tests/ -v` (all tests passing).
- **Manual verification**:
  - Complete demo rehearsal on Linux desktop.
- **Status**: `DONE`
