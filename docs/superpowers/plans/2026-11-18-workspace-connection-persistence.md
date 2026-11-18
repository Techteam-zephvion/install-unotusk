# Workspace Connection Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep workspace project connections active on the project dashboard when navigating between screens until explicitly disconnected or the server stops.

**Architecture:** Isolate Control Plane project pruning (`port == 28000`) in `ApiService` so data-plane queries (`port != 28000`) never clear connected projects, and hoist the active connected projects list in `_MainLayoutState` (`main.dart`) to survive widget unmounting.

**Tech Stack:** Dart, Flutter, `package:test`

**Spec:** `docs/superpowers/specs/2026-11-18-workspace-connection-persistence-design.md`

## Global Constraints

- Never commit or push to git remotes without explicit user confirmation.
- Derive server host dynamically from `ApiService.baseUrl` (no hardcoded IP addresses).
- Evict projects only when the Control Plane confirms they are `STOPPED`, `DELETED`, or `OFFLINE`.
- Keep changes minimal and isolated to `api_service.dart`, `main.dart`, and `projects_screen.dart`.

## Review Focus

1. Data-plane port query: opening a project shifts `baseUrl` to `http://host:28200`; `fetchProjects()` must NOT prune `connectedProjectIds`.
2. Screen unmount and remount: navigating from dashboard into workspace and back via `< Projects` must preserve the list of connected project cards.
3. Explicit user disconnect: toggling off a project in "Connect Workspace" dialog must remove it immediately from both local and parent state.
4. Server stopped / offline: if a connected project's status changes to `STOPPED` or `OFFLINE` on port 28000, it must be evicted from the active workspace cards.
5. Desktop restart / persistence: `ApiService.loadPersistedConnectedProjects()` must restore previous connections without being corrupted by transient empty saves.

---

### Task 1: Isolate Control Plane Connection Pruning in `ApiService`

**Files:**
- Modify: `app/lib/services/api_service.dart:200-240`, `app/lib/services/api_service.dart:755-780`
- Test: `app/test/unit/api_service_connection_test.dart`

**Interfaces:**
- Consumes: `ApiService.baseUrl`, `ApiService.connectedProjectIds`, `ApiService.connectedWorkspaceProjects`
- Produces: `ApiService.isControlPlane -> bool`, safe `ApiService.fetchProjects()` that guards pruning to Control Plane only.

- [ ] **Step 1: Write the failing unit test**

Create `app/test/unit/api_service_connection_test.dart` verifying that `isControlPlane` correctly detects port 28000 vs data-plane ports (e.g. 28200), and that data-plane URLs do not prune `connectedProjectIds`.

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:app/services/api_service.dart';

void main() {
  group('ApiService Control Plane Scoping', () {
    test('isControlPlane returns true for port 28000 and default baseUrl', () {
      ApiService.baseUrl = 'http://10.0.0.43:28000';
      expect(ApiService.isControlPlane, isTrue);
    });

    test('isControlPlane returns false for data plane ports', () {
      ApiService.baseUrl = 'http://10.0.0.43:28200';
      expect(ApiService.isControlPlane, isFalse);
    });
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app; flutter test test/unit/api_service_connection_test.dart`
Expected: FAIL with `isControlPlane` not defined.

- [ ] **Step 3: Implement `isControlPlane` and guard pruning in `api_service.dart`**

1. In `ApiService`, add:
```dart
static bool get isControlPlane {
  final uri = Uri.tryParse(baseUrl);
  return uri == null || uri.port == 28000;
}
```
2. In `ApiService.fetchProjects()` around line 760, wrap the pruning logic so it only runs if `isControlPlane`:
```dart
if (isControlPlane) {
  final validProjectIds = projects.map((p) => p.id.toLowerCase()).toSet();
  final validProjectNames = projects.map((p) => p.name.toLowerCase()).toSet();
  connectedProjectIds.removeWhere(
    (id) => !validProjectIds.contains(id.toLowerCase()) && !validProjectNames.contains(id.toLowerCase()),
  );
  savePersistedConnectedProjects();
}
```
3. In `savePersistedConnectedProjects()`, guard against saving empty lists while non-control-plane is active.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app; flutter test test/unit/api_service_connection_test.dart`
Expected: PASS.

---

### Task 2: Hoist Workspace Projects State in `_MainLayoutState` (`main.dart`)

**Files:**
- Modify: `app/lib/main.dart:100-160`, `app/lib/main.dart:270-305`, `app/lib/main.dart:495-510`

**Interfaces:**
- Consumes: `_MainLayoutState`, `ProjectsScreen`
- Produces: `_workspaceConnectedProjects` held in `_MainLayoutState` passed to `ProjectsScreen` across navigation cycles.

- [ ] **Step 1: Add `_workspaceConnectedProjects` state in `_MainLayoutState`**

In `app/lib/main.dart`:
1. Add `List<ProjectItem> _workspaceConnectedProjects = [];` inside `_MainLayoutState`.
2. In `_handleBackToProjects()`:
   - Reset base URL to Control Plane: `ApiService.setBaseUrl(controlPlaneUrl);`
   - Preserve `_workspaceConnectedProjects` without clearing.
   - Do not clear `ApiService.connectedProjectIds`.
3. In `_handleLogOut()`:
   - Clear `_workspaceConnectedProjects.clear();` upon explicit logout.

- [ ] **Step 2: Pass state and update callback to `ProjectsScreen`**

In `_MainLayoutState.build()` where `ProjectsScreen` is created (around line 495):
```dart
return ProjectsScreen(
  userName: _user.name,
  onOpenProject: _handleOpenProject,
  initialConnectedProjects: _workspaceConnectedProjects,
  onConnectedProjectsChanged: (projects) {
    setState(() {
      _workspaceConnectedProjects = List<ProjectItem>.from(projects);
    });
  },
);
```

- [ ] **Step 3: Verify static analysis of `main.dart`**

Run: `cd app; dart analyze lib/main.dart`
Expected: PASS (or note missing constructor arguments to be added in Task 3).

---

### Task 3: Synchronize and Protect Connection in `ProjectsScreen`

**Files:**
- Modify: `app/lib/screens/projects_screen.dart:20-50`, `app/lib/screens/projects_screen.dart:110-145`, `app/lib/screens/projects_screen.dart:180-200`, `app/lib/screens/projects_screen.dart:360-405`

**Interfaces:**
- Consumes: `initialConnectedProjects`, `onConnectedProjectsChanged` from `main.dart`
- Produces: Persistent `_projects` in `_ProjectsScreenState` that retains connected cards across screen remounts.

- [ ] **Step 1: Update `ProjectsScreen` constructor**

In `app/lib/screens/projects_screen.dart`:
```dart
final List<ProjectItem>? initialConnectedProjects;
final ValueChanged<List<ProjectItem>>? onConnectedProjectsChanged;

const ProjectsScreen({
  super.key,
  this.userName = '',
  required this.onOpenProject,
  this.initialConnectedProjects,
  this.onConnectedProjectsChanged,
});
```

- [ ] **Step 2: Initialize `_projects` without destructive reset**

In `_ProjectsScreenState.initState()`:
1. If `widget.initialConnectedProjects != null && widget.initialConnectedProjects!.isNotEmpty`:
   - Initialize `_projects.addAll(widget.initialConnectedProjects!)`.
2. Else if `ApiService.connectedWorkspaceProjects.isNotEmpty`:
   - Initialize `_projects.addAll(ApiService.connectedWorkspaceProjects)`.
3. Remove only projects explicitly flagged `STOPPED`, `DELETED`, or `OFFLINE`.

- [ ] **Step 3: Notify parent on connection change**

1. In `_toggleProjectConnection()`:
   - Call `widget.onConnectedProjectsChanged?.call(_projects);`.
2. In `_connectAllWorkspaceProjects()`:
   - Call `widget.onConnectedProjectsChanged?.call(_projects);`.
3. In `_fetchServerProjects()`:
   - After updating `_projects` from serverProjects, call `widget.onConnectedProjectsChanged?.call(_projects);`.

- [ ] **Step 4: Verify static analysis of `projects_screen.dart`**

Run: `cd app; dart analyze lib/screens/projects_screen.dart lib/main.dart`
Expected: 0 errors.

---

### Task 4: End-to-End Verification

**Files:**
- Test: `app/test/unit/api_service_connection_test.dart`
- Run static analysis on all touched files: `lib/services/api_service.dart`, `lib/main.dart`, `lib/screens/projects_screen.dart`.

- [ ] **Step 1: Run complete test suite**

Run: `cd app; flutter test test/unit/api_service_connection_test.dart`
Expected: All tests pass.

- [ ] **Step 2: Run Dart static analysis**

Run: `cd app; dart analyze lib/services/api_service.dart lib/main.dart lib/screens/projects_screen.dart`
Expected: No issues found.

- [ ] **Step 3: Review Git diff**

Run: `git diff --stat`
Expected: Changes limited to `api_service.dart`, `main.dart`, `projects_screen.dart`, and the test file. No unintended commits or pushed code.
