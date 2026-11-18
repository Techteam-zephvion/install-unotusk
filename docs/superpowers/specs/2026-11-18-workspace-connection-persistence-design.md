# Design Spec: Workspace Connection Persistence Across Screen Transitions

**Date:** 2026-11-18  
**Topic:** Persist workspace project connection across screen navigation  
**Status:** Pending Approval  

---

## 1. Intent & Why
In UnoTusk Flutter desktop app, the user connects backend projects via the "Connect Workspace" dialog on the project dashboard (`ProjectsScreen`). When the user clicks "Open" on a project, navigates into the workspace, and later clicks "< Projects" to return to the dashboard, the connection appears lost ("No projects in workspace"), forcing them to reconnect every time.

The connection should remain active across screen transitions until either:
1. The server or project container stops or goes offline.
2. The user explicitly disconnects the project via the workspace dialog.
3. The user logs out.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- Maintain connected workspace project cards seamlessly when navigating between `ProjectsScreen` and `WorkspaceView` (chat, files, architecture, etc.).
- Isolate Control Plane state (port 28000) from Data Plane state (ports 28100–28999), preventing data-plane project listings from pruning the control-plane connection set.
- Keep the active connected project state in memory in `_MainLayoutState` so it survives widget unmounting and remounting.
- Continue to properly evict projects that the control plane reports as `STOPPED`, `DELETED`, or `OFFLINE`.

### Non-Goals
- Do not introduce Riverpod or third-party state management libraries.
- Do not alter backend API schemas, OIDC authentication, or port-shifting contracts.
- Do not keep projects connected if their container is reported offline or stopped by the server.

### Anti-Goals
- No hardcoded IP addresses or ports (must derive from dynamic `ApiService.baseUrl`).
- No invasive network polling or heavy timeouts that trigger socket connection exhaustion.
- No auto-commit or auto-push to git remotes.

---

## 3. Approaches Considered & Trade-offs

1. **Approach 1: Control-Plane-Scoped State + Parent Session Hoisting (Selected)**
   - *Pros*: Directly eliminates the root cause (data-plane port pruning), minimal code footprint, zero risk of regressing existing screens, preserves all current multi-server flows.
   - *Cons*: Relies on standard Flutter state hoisting and static service state.
   - *Reason for selection*: Simplest, most reliable, and fits the existing codebase cleanly.

2. **Approach 2: Global `WorkspaceConnectionManager` (`ChangeNotifier`)**
   - *Pros*: Decouples state from `ApiService`.
   - *Cons*: Adds an extra layer of abstraction and requires updating multiple screen widget trees to listen to change notifications.

3. **Approach 3: Full App State Refactoring to Riverpod**
   - *Pros*: Formal unidirectional state management.
   - *Cons*: Extreme overkill for this issue, massive refactoring scope across working screens with high regression risk.

---

## 4. Implementation Design (The "How")

### A. Guard `ApiService` Connection Pruning by Port Scope
In `app/lib/services/api_service.dart`:
- Define a helper:
  ```dart
  static bool get isControlPlane {
    final uri = Uri.tryParse(baseUrl);
    return uri == null || uri.port == 28000;
  }
  ```
- In `ApiService.fetchProjects()`:
  - Only execute the pruning logic (`connectedProjectIds.removeWhere(...)` and `savePersistedConnectedProjects()`) when `isControlPlane == true`.
  - When querying a data-plane port (`port != 28000`), skip pruning `connectedProjectIds`.
- In `savePersistedConnectedProjects()`:
  - Add a safety check: never overwrite the persisted file if `connectedProjectIds` is empty while `connectedWorkspaceProjects` or memory cache had active items, preventing accidental zero-length wipeouts during transient transitions.

### B. State Hoisting in `_MainLayoutState` (`main.dart`)
- `_MainLayoutState` is the parent widget that stays mounted throughout the user's session.
- Add `List<ProjectItem> _workspaceConnectedProjects = []` to `_MainLayoutState`.
- Pass `connectedProjects: _workspaceConnectedProjects` and an `onConnectedProjectsChanged` callback into `ProjectsScreen`.
- In `_handleBackToProjects()`:
  - Preserve `_workspaceConnectedProjects`.
  - When switching base URL back to port 28000, do not clear `ApiService.connectedProjectIds`.

### C. `ProjectsScreen` Synchronization (`projects_screen.dart`)
- In `_ProjectsScreenState`:
  - Initialize `_projects` from `widget.initialConnectedProjects` or `ApiService.connectedWorkspaceProjects` rather than clearing on every mount.
  - When backend projects are fetched from port 28000:
    - Prune only projects that the control plane lists as `STOPPED`, `DELETED`, or `OFFLINE`.
    - Retain all running projects whose ID or name is in `connectedProjectIds`.
    - Notify parent `onConnectedProjectsChanged(_projects)`.

---

## 5. Verification Plan
1. Launch app with `flutter run -d chrome` (or desktop).
2. On dashboard, open "Connect Workspace" dialog and connect 1 or more projects. Confirm cards appear with "Open" buttons.
3. Click "Open" on a project -> verify workspace loads and shifts port to project container.
4. Click "< Projects" back to dashboard -> verify the connected projects remain displayed immediately without needing to click "Connect Workspace" again.
5. Verify stopping a container or clicking disconnect removes only the targeted project.
