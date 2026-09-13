# Unotusk Employee Application — Phase 2 Task Sheet
# Project Workspace Implementation

## Product Principle
**SIMPLE ON THE SURFACE. DEEP WHEN NEEDED.**
Unotusk is a calm, serious engineering productivity tool. It is not an AI dashboard, ChatGPT clone, or marketing analytics viewer.
Progressive disclosure governs all screens: show the immediate useful fact first; reveal depth upon employee investigation.

---

## Master Task Breakdown & Status Matrix

| Task ID | Task Name | Area | Dependencies | Status |
| :--- | :--- | :--- | :--- | :--- |
| **TASK-201** | Project Repository & Context Data Layer | Infrastructure / Data | Phase 1 Complete | DONE |
| **TASK-202** | Phase 2A — Project Overview Screen | Overview | TASK-201 | DONE |
| **TASK-203** | Phase 2B — Project File Browser & Tree List | Files | TASK-201 | DONE |
| **TASK-204** | Backend File Detail Endpoint & Chunks Support | Backend Integration | TASK-201 | DONE |
| **TASK-205** | Phase 2C — File Detail & Code Structure Inspector | File Detail | TASK-203, TASK-204 | DONE |
| **TASK-206** | Phase 2D — Component Relationships & Architecture | Architecture / Dependencies | TASK-201, TASK-205 | DONE |
| **TASK-207** | Phase 2E — Discoveries Feed & Findings Summary | Discoveries | TASK-201 | DONE |
| **TASK-208** | Phase 2F — Discovery Investigation & Evidence View | Discovery Deep-dive | TASK-207, TASK-205 | DONE |
| **TASK-209** | Phase 2G — Project Knowledge Management | Knowledge | TASK-201 | DONE |
| **TASK-210** | Phase 2H — Grounded Ask & Project Search | Ask / Investigation | TASK-201, TASK-209 | DONE |
| **TASK-211** | Phase 2I — Cross-Navigation & Unified Evidence Graph | Navigation / Interactivity | TASK-202 through TASK-210 | DONE |
| **TASK-212** | Phase 2J — Workspace UX Polish & Desktop Refinement | UX / Performance / Ergonomics | TASK-211 | DONE |

---

## Detailed Task Specifications

### TASK-201: Project Repository & Context Data Layer
- **Task ID**: `TASK-201`
- **Task Name**: Project Repository & Context Data Layer (Models, Repositories, Providers)
- **Objective**: Establish the core domain models, DTOs, and Riverpod repositories in Flutter to consume the existing FastAPI backend context, file list, symbol list, dependency list, and discovery summary endpoints.
- **User-facing result**: Foundation for all Phase 2 workspace data loading without UI changes.
- **Backend/API dependencies**:
  - `GET /projects/{id}/repository` (`ProjectRepositoryContext`)
  - `GET /projects/{id}/files` (`list[FileRead]`)
  - `GET /projects/{id}/symbols` (`list[SymbolRead]`)
  - `GET /projects/{id}/dependencies` (`list[DependencyRead]`)
  - `GET /projects/{id}/discover/status` (`DiscoverSummaryResponse`)
- **Flutter files/components likely affected**:
  - `app/lib/core/network/api_endpoints.dart`
  - `app/lib/features/workspace/domain/repository_context.dart` (new)
  - `app/lib/features/workspace/domain/project_file.dart` (new)
  - `app/lib/features/workspace/domain/project_symbol.dart` (new)
  - `app/lib/features/workspace/domain/project_dependency.dart` (new)
  - `app/lib/features/workspace/domain/discovery_summary.dart` (new)
  - `app/lib/features/workspace/domain/project_finding.dart` (new)
  - `app/lib/features/workspace/data/workspace_repository.dart` (new)
  - `app/lib/features/workspace/presentation/workspace_controller.dart` (new)
- **Implementation steps**:
  1. Add missing endpoint paths to `ApiEndpoints`.
  2. Implement strongly typed Dart models matching backend Pydantic schemas.
  3. Implement `WorkspaceRepository` using `ApiClient` to fetch context, files, symbols, and dependencies.
  4. Create Riverpod providers for asynchronous loading and caching.
- **Acceptance criteria**:
  - All context models deserialize JSON from the live backend without runtime exceptions.
  - Riverpod providers expose clean `AsyncValue` states.
- **Tests required**:
  - Unit tests for model deserialization with sample backend JSON fixtures.
  - Unit tests for `WorkspaceRepository`.
- **Verification command**: `flutter test test/unit/workspace_repository_test.dart`
- **Dependencies**: Phase 1 Complete
- **Status**: `DONE`

---

### TASK-202: Phase 2A — Project Overview Screen
- **Task ID**: `TASK-202`
- **Task Name**: Phase 2A — Project Overview Screen
- **Objective**: Replace the placeholder Overview tab with a calm, high-density project summary showing primary language distribution, file/symbol counts, critical items needing attention, and recent indexing status.
- **User-facing result**: When opening a project, the employee immediately sees:
  - Concise header: Repository name, primary language, total file count, last indexed timestamp.
  - "Needs Attention" section: Top high-severity circular dependencies or key components with high usage.
  - "Project Structure" summary: Language distribution and core symbol totals.
  - Direct action links (`[Open]`, `[Inspect]`) to navigate to Files or Discoveries.
- **Backend/API dependencies**:
  - `GET /projects/{id}/repository`
  - `GET /projects/{id}/findings?severity=CRITICAL&status=OPEN`
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/overview_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/overview_attention_card.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/overview_metric_strip.dart` (new)
- **Implementation steps**:
  1. Create `OverviewTab` state consumer watching `projectContextProvider` and top findings.
  2. Implement high-density summary strip (Files, Symbols, Dependencies, Languages).
  3. Implement "Needs Attention" items list with direct action buttons.
  4. Implement loading, error, and empty states.
- **Acceptance criteria**:
  - Shows real backend metrics for `psf/requests` (e.g. Python project, file count, active snapshot).
  - No decorative AI scorecards, no health scores, no confidence percentages.
  - Clicking `[Open]` on an attention item navigates to the relevant tab.
- **Tests required**:
  - Widget test for `OverviewTab` displaying project context and attention items.
- **Verification command**: `flutter test test/widget/overview_tab_test.dart`
- **Dependencies**: `TASK-201`
- **Status**: `DONE`

---

### TASK-203: Phase 2B — Project File Browser & Tree List
- **Task ID**: `TASK-203`
- **Task Name**: Phase 2B — Project File Browser & Tree List
- **Objective**: Build a compact, searchable file browser with hierarchical directory navigation, language badges, line counts, and test file indicators.
- **User-facing result**:
  - Compact file tree / list view with folders collapsible/expandable.
  - Instant text filter/search by filename or path.
  - Metadata badges (language, lines, test tag).
  - Selecting a file updates the active selection for detail inspection.
- **Backend/API dependencies**:
  - `GET /projects/{id}/files?limit=1000`
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/files_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/file_tree_view.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/file_search_bar.dart` (new)
  - `app/lib/features/workspace/domain/file_node.dart` (new tree utility)
- **Implementation steps**:
  1. Build directory tree builder transforming flat `List<ProjectFile>` into a hierarchical `FileNode` tree.
  2. Create `FileTreeView` with expandable folders and compact item rows.
  3. Implement search input with real-time filtering.
  4. Connect selection state to Riverpod `selectedFileIdProvider`.
- **Acceptance criteria**:
  - Correctly renders directory structure for `psf/requests` (`requests/`, `tests/`, etc.).
  - Search input filters files dynamically without lagging.
  - Clear empty state when search produces 0 results.
- **Tests required**:
  - Unit tests for directory tree building and search filtering.
  - Widget test for `FilesTab` rendering and selection.
- **Verification command**: `flutter test test/widget/files_tab_test.dart`
- **Dependencies**: `TASK-201`
- **Status**: `DONE`

---

### TASK-204: Backend File Detail Endpoint & Chunks Support
- **Task ID**: `TASK-204`
- **Task Name**: Backend File Detail Endpoint (`GET /projects/{project_id}/files/{file_id}`)
- **Objective**: Add a single, minimal backend endpoint to fetch a single file with its AST symbols, incoming & outgoing dependencies, and stored code chunks/content.
- **User-facing result**: Enables real code viewing and structural breakdown for Phase 2C without inventing mock data.
- **Backend/API dependencies**:
  - `apps/api/src/api/routes/repository.py`
  - `apps/api/src/services/repository_service.py`
  - `apps/api/src/schemas/context.py`
- **Flutter files/components likely affected**:
  - None (Backend only; consumed in TASK-205).
- **Implementation steps**:
  1. Define `FileDetailRead` schema with file metadata, symbols list, outgoing dependencies, incoming references, and code chunks.
  2. Add `GET /projects/{project_id}/files/{file_id}` route to `repository.py`.
  3. Implement `RepositoryService.get_file_detail` joining `RepositoryFile`, `CodeSymbol`, `CodeDependency`, and `CodeChunk`.
  4. Write pytest test verifying file detail retrieval on ingested test database.
- **Acceptance criteria**:
  - Returns 200 OK with complete file details, symbols, dependencies, and chunk content.
  - Returns 404 for nonexistent file or forbidden project.
- **Tests required**:
  - Backend pytest test `tests/api/test_file_detail_api.py`.
- **Verification command**: `pytest tests/api/test_file_detail_api.py -v`
- **Dependencies**: `TASK-201`
- **Status**: `DONE`

---

### TASK-205: Phase 2C — File Detail & Code Structure Inspector
- **Task ID**: `TASK-205`
- **Task Name**: Phase 2C — File Detail & Code Structure Inspector
- **Objective**: Provide a split-pane or detail drawer when a file is selected, showing symbols (classes/functions with line ranges), dependencies, consumers, related discoveries, and source code viewer.
- **User-facing result**:
  - Clicking a file opens its detail view.
  - Symbols list (e.g. `Session`, `HTTPAdapter`, `send()`).
  - Outgoing imports / dependencies list.
  - Incoming consumers ("Used by 14 files").
  - Code viewer with line numbers and syntax formatting.
- **Backend/API dependencies**:
  - `GET /projects/{id}/files/{file_id}` (from TASK-204)
  - `GET /projects/{id}/findings` (filtered by file)
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/files_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/file_detail_panel.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/code_viewer.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/symbol_list_view.dart` (new)
- **Implementation steps**:
  1. Implement split pane in `FilesTab` (left: tree, right: detail & code).
  2. Display file metadata (path, size, line count, language).
  3. Render symbols table with line jump markers.
  4. Render dependencies and consumer references.
  5. Render clean code text viewer with line numbers.
- **Acceptance criteria**:
  - Opening `requests/sessions.py` displays its symbols (`Session`, `SessionRedirectMixin`), outgoing dependencies (`urllib3`, `adapters`), and code chunks.
  - Clicking a symbol jumps/highlights the relevant code section.
- **Tests required**:
  - Widget test for `FileDetailPanel`.
- **Verification command**: `flutter test test/features/workspace/file_detail_test.dart`
- **Dependencies**: `TASK-203`, `TASK-204`
- **Status**: `NOT_STARTED`

---

### TASK-206: Phase 2D — Component Relationships & Architecture
- **Task ID**: `TASK-206`
- **Task Name**: Phase 2D — Component Relationships & Architecture View
- **Objective**: Expose clear, readable component relationships without unnecessary visual gimmicks.
- **User-facing result**:
  - Clear list/search of top project components and modules.
  - For any selected component:
    - "Used by" (incoming references & caller files).
    - "Depends on" (outgoing internal imports & external packages).
  - Quick action buttons to navigate directly to the target file.
- **Backend/API dependencies**:
  - `GET /projects/{id}/dependencies?limit=1000`
  - `GET /projects/{id}/symbols?limit=1000`
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/architecture_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/component_relationship_card.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/dependency_matrix_view.dart` (new)
- **Implementation steps**:
  1. Build component aggregator grouping dependencies by module/component.
  2. Implement two-pane Architecture tab: components list on left, relationship inspector on right.
  3. Display upstream callers and downstream dependencies.
  4. Add `[Open File]` buttons navigating straight to `FilesTab`.
- **Acceptance criteria**:
  - Clear, readable layout with zero clutter.
  - Accurately reflects internal dependencies of `psf/requests` (e.g. `adapters.py` -> `urllib3`).
- **Tests required**:
  - Widget test for `ArchitectureTab`.
- **Verification command**: `flutter test test/features/workspace/architecture_tab_test.dart`
- **Dependencies**: `TASK-201`, `TASK-205`
- **Status**: `NOT_STARTED`

---

### TASK-207: Phase 2E — Discoveries Feed & Findings Summary
- **Task ID**: `TASK-207`
- **Task Name**: Phase 2E — Discoveries Feed & Findings Summary
- **Objective**: Connect the existing discovery engine findings to a compact, actionable findings list.
- **User-facing result**:
  - Categorized list of findings (e.g. Circular Dependencies, High Coupling, Untested Critical Paths).
  - Severity badge (Critical, High, Medium, Low) and category tag.
  - Concise title and affected file count.
  - Filter bar (by Category, Severity, Status).
  - Action to trigger a fresh discovery scan (`[Run Analysis]`).
- **Backend/API dependencies**:
  - `GET /projects/{id}/findings`
  - `GET /projects/{id}/discover/status`
  - `POST /projects/{id}/discover`
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/discoveries_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/finding_card.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/findings_filter_bar.dart` (new)
  - `app/lib/features/workspace/domain/project_finding.dart` (new)
- **Implementation steps**:
  1. Create `ProjectFinding` Dart model and `findingsProvider`.
  2. Implement compact findings list with severity indicators.
  3. Implement category/severity filter controls.
  4. Implement "Run Analysis" button with trigger and live polling for completion.
- **Acceptance criteria**:
  - Displays real findings from the backend for `psf/requests`.
  - Filters update the list immediately.
  - Empty state displayed gracefully if no findings match filter.
- **Tests required**:
  - Widget test for `DiscoveriesTab` and filtering.
- **Verification command**: `flutter test test/features/workspace/discoveries_tab_test.dart`
- **Dependencies**: `TASK-201`
- **Status**: `DONE`

---

### TASK-208: Phase 2F — Discovery Investigation & Evidence View
- **Task ID**: `TASK-208`
- **Task Name**: Phase 2F — Discovery Investigation & Evidence View
- **Objective**: Deep-dive view for a selected finding, detailing what was detected, affected files, supporting evidence snippets, why it matters, and status update actions.
- **User-facing result**:
  - Opening a discovery opens a dedicated investigation pane.
  - Explains the issue in clear, concise engineering language.
  - Lists affected files with one-click navigation to File Detail.
  - Displays deterministic evidence items (line ranges, code snippets, cycle paths).
  - Status toggle buttons (Acknowledge, Dismiss, Resolve).
  - "Ask about this finding" quick action jumping to the Ask tab with context pre-populated.
- **Backend/API dependencies**:
  - `GET /projects/{id}/findings/{finding_id}`
  - `PATCH /projects/{id}/findings/{finding_id}`
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/discoveries_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/finding_detail_view.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/evidence_snippet_view.dart` (new)
- **Implementation steps**:
  1. Build `FindingDetailView` displaying description, why it matters, recommendation, and evidence.
  2. Implement status update mutation using `PATCH /projects/{id}/findings/{id}`.
  3. Add evidence snippet renderer with line numbers.
  4. Add navigation hooks to `FilesTab` and `AskTab`.
- **Acceptance criteria**:
  - Employee can inspect full evidence for any finding.
  - Updating finding status persists to backend and updates list badge.
- **Tests required**:
  - Widget test for `FindingDetailView` and status mutation.
- **Verification command**: `flutter test test/features/workspace/finding_detail_test.dart`
- **Dependencies**: `TASK-207`, `TASK-205`
- **Status**: `DONE`

---

### TASK-209: Phase 2G — Project Knowledge Management
- **Task ID**: `TASK-209`
- **Task Name**: Phase 2G — Project Knowledge Management
- **Objective**: Connect the Project Knowledge backend to allow viewing, creating, editing, archiving, and searching organizational knowledge items.
- **User-facing result**:
  - Clean list of project knowledge cards (Title, Category, Snippet, Created date, Status).
  - Category filters (Architecture Decision, Technical Debt, Business Logic, Security Requirement, Operational Gotcha).
  - Modal / form dialog to Add new knowledge item.
  - Quick actions to Edit, Archive, or Restore knowledge items.
- **Backend/API dependencies**:
  - `GET /projects/{id}/knowledge`
  - `POST /projects/{id}/knowledge`
  - `PATCH /projects/{id}/knowledge/{id}`
  - `POST /projects/{id}/knowledge/{id}/archive`
  - `POST /projects/{id}/knowledge/{id}/restore`
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/knowledge_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/knowledge_card.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/knowledge_form_dialog.dart` (new)
  - `app/lib/features/workspace/domain/project_knowledge.dart` (new)
- **Implementation steps**:
  1. Create `ProjectKnowledge` model and `knowledgeRepositoryProvider`.
  2. Implement `KnowledgeTab` with filter pills and search bar.
  3. Build `KnowledgeFormDialog` for create and edit flows.
  4. Implement archive and restore actions with optimistic/immediate UI updates.
- **Acceptance criteria**:
  - Employee can add a new knowledge note, view it in the list, edit it, and archive it.
  - Search input filters knowledge titles and contents.
- **Tests required**:
  - Widget test for `KnowledgeTab` operations.
- **Verification command**: `flutter test test/features/workspace/knowledge_tab_test.dart`
- **Dependencies**: `TASK-201`
- **Status**: `DONE`

---

### TASK-210: Phase 2H — Grounded Ask & Project Search
- **Task ID**: `TASK-210`
- **Task Name**: Phase 2H — Grounded Ask & Project Search
- **Objective**: Build an investigation search tool (not a generic AI chat) connecting to the grounded question-answering backend.
- **User-facing result**:
  - Search/investigation prompt input: "Search or ask about this project...".
  - Grounded answer presentation where project entities and evidence citations dominate over raw text.
  - Citations list (`auth.py:24-41`, `sessions.py:100-142`) with click-to-open actions.
  - Thread history sidebar to recall previous investigation questions.
- **Backend/API dependencies**:
  - `POST /projects/{id}/ask`
  - `GET /projects/{id}/conversations`
  - `GET /projects/{id}/conversations/{conversation_id}`
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/tabs/ask_tab.dart`
  - `app/lib/features/workspace/presentation/widgets/grounded_answer_card.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/evidence_citation_chip.dart` (new)
  - `app/lib/features/workspace/presentation/widgets/ask_history_sidebar.dart` (new)
  - `app/lib/features/workspace/domain/grounded_answer.dart` (new)
- **Implementation steps**:
  1. Create `GroundedAnswer` and `EvidenceItem` Dart models.
  2. Implement `AskTab` with prominent query input and history sidebar.
  3. Render grounded responses with clear separation between concise explanation and supporting evidence.
  4. Wire clickable evidence chips to jump to file / symbol.
- **Acceptance criteria**:
  - Submitting a query (e.g. "Where is connection pooling configured?") renders the grounded answer with evidence chips.
  - UI is restrained: no generic chatbot bubbles, no sparkling animations.
- **Tests required**:
  - Widget test for `AskTab` and query execution.
- **Verification command**: `flutter test test/features/workspace/ask_tab_test.dart`
- **Dependencies**: `TASK-201`, `TASK-209`
- **Status**: `DONE`

---

### TASK-211: Phase 2I — Cross-Navigation & Unified Evidence Graph
- **Task ID**: `TASK-211`
- **Task Name**: Phase 2I — Cross-Navigation & Unified Evidence Graph
- **Objective**: Connect all project objects seamlessly so an employee can navigate bidirectionally across Overview, Files, Architecture, Discoveries, Knowledge, and Ask.
- **User-facing result**:
  - Overview -> Click attention item -> Jumps to specific Finding in Discoveries or File in Files.
  - Finding -> Click affected file -> Jumps to File Detail in Files.
  - File Detail -> Click related finding / symbol -> Jumps to Finding or Symbol.
  - Ask Answer -> Click evidence citation -> Opens exact file and highlights line range.
  - Workspace navigation state remains synchronized and back/forward navigation is smooth.
- **Backend/API dependencies**:
  - Uses existing endpoints wired in previous tasks.
- **Flutter files/components likely affected**:
  - `app/lib/features/workspace/presentation/workspace_screen.dart`
  - `app/lib/features/workspace/presentation/workspace_navigation_controller.dart` (new)
  - All tab widgets (passing navigation callbacks).
- **Implementation steps**:
  1. Create `WorkspaceNavigationController` managing active tab, selected file, selected finding, and line highlight.
  2. Connect all clickable entity references (chips, links, buttons) to navigation controller intents.
  3. Ensure active tab switches and target item focuses cleanly.
- **Acceptance criteria**:
  - Clicking an evidence chip in Ask navigates directly to Files tab, selects the file, and scrolls to lines.
  - Clicking an affected file in Discoveries navigates directly to Files tab with that file open.
- **Tests required**:
  - Integration test for cross-tab navigation flows.
- **Verification command**: `flutter test test/features/workspace/cross_navigation_test.dart`
- **Dependencies**: `TASK-202` through `TASK-210`
- **Status**: `DONE`

---

### TASK-212: Phase 2J — Workspace UX Polish & Desktop Refinement
- **Task ID**: `TASK-212`
- **Task Name**: Phase 2J — Workspace UX Polish & Desktop Refinement
- **Objective**: Polish desktop aesthetics, keyboard shortcuts, resizing ergonomics, typography, hover/focus states, and error handling across the entire Project Workspace.
- **User-facing result**:
  - Smooth desktop resizing with responsive split-panes.
  - Keyboard shortcuts (`Ctrl/Cmd + K` for Ask/Search, `Escape` to close drawers/modals, Arrow navigation in tree).
  - Consistent hover and selection states following the slate design system.
  - Polished empty and error recovery states across all 6 tabs.
- **Backend/API dependencies**:
  - None (Frontend polish).
- **Flutter files/components likely affected**:
  - All workspace presentation widgets.
  - `app/lib/core/widgets/desktop_scaffold.dart`
  - `app/lib/app/theme/app_colors.dart`
  - `app/lib/app/theme/app_text_styles.dart`
- **Implementation steps**:
  1. Implement keyboard shortcut handlers (`Shortcuts` / `Actions`).
  2. Polish split-pane dividers and responsive breakpoints for desktop window sizing.
  3. Audit all hover, active, focus, and disabled styling for consistency.
  4. Ensure zero UI glitches, text overflows, or unhandled null states.
- **Acceptance criteria**:
  - `flutter analyze` passes with 0 issues.
  - `flutter test` passes 100% of tests.
  - Desktop UI feels snappy, calm, and robust.
- **Tests required**:
  - Full test suite execution across all workspace tests.
- **Verification command**: `flutter analyze && flutter test`
- **Dependencies**: `TASK-211`
- **Status**: `DONE`
