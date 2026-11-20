# Feature Invariants & Architectural Protections for Unotusk Flutter App

This document serves as the canonical reference for all architectural invariants, bug fixes, and feature behaviors that must be preserved whenever changes are pulled, merged, or rebased from upstream repositories (`target` or `origin`).

---

## 1. Persistent Connected Workspace Projects

### Expected Behavior
- When an admin connects a project from the "Connect Workspace" dialog, that project is added to the workspace dashboard.
- The project **must persist across screen transitions, app reloads, and server restarts**.
- Returning from Workspace/Chat/Files to the Projects screen must immediately render the connected projects without delay or showing "No projects in workspace".
- A connected project is **ONLY** removed from the dashboard under two conditions:
  1. The server explicitly reports the project as `STOPPED`, `DELETED`, or `OFFLINE`.
  2. The user explicitly toggles/disconnects it via the "Connect Workspace" dialog.
- A connected project must **NEVER** be removed because an API call returned empty `[]`, threw an error, or during a port shift.

### Implementation References
- **`app/lib/models/models.dart`**:
  - `ProjectItem` must implement `toJson()` and `ProjectItem.fromJson(Map<String, dynamic> json)`.
- **`app/lib/services/api_service.dart`**:
  - `connectedProjectIds` (Set of IDs and names).
  - `connectedWorkspaceProjects` (List of full `ProjectItem` objects).
  - `_connectedProjectsDataFile`: Serializes full `ProjectItem` JSON list to `$TEMP/unotusk_connected_projects_data.json`.
  - `savePersistedConnectedProjects()`: Saves to both SharedPreferences (`unotusk_connected_workspace_projects_json`) and local disk.
  - `loadPersistedConnectedProjects()`: Restores both IDs and full `ProjectItem` objects before network requests run.
- **`app/lib/screens/projects_screen.dart`**:
  - `initState()` immediately loads `connectedWorkspaceProjects` into `_projects`.
  - `_fetchServerProjects()` and `_fetchAvailableWorkspaceProjects()` update running project metadata without clearing existing active projects.

---

## 2. Server as Sole Authority (No Phantom Projects)

### Expected Behavior
- The remote backend (`GET /api/v1/projects` on Port 28000) is the sole authority on what projects exist.
- Old deployment directories on local laptops (in `~/.unotusk/servers`) must **NEVER** be injected into the project list as fake or phantom projects (`Project 1`, `Sahaay`).

### Implementation References
- **`app/lib/services/api_service.dart`**:
  - In `fetchProjects()`, `LocalRegistryService.getRunningServers()` is only used to augment port mappings on projects that *already exist* on the server.
  - It must **never** call `projects.add(localProj)` or resurrect phantom projects.

---

## 3. Stopped Server Connect Guard

### Expected Behavior
- If a project exists on the server but is in an offline or inactive state (such as `CONNECTING`, `STOPPED`, `OFFLINE`, `ERROR`), the "Connect Workspace" dialog must **hide the Connect button** (`SizedBox.shrink()`).
- Tapping the project tile is disabled (`onTap: null`).
- The `+ Connect` button is only visible when the server is verified to be on (`upsStatus == 'READY'` or `upsStatus == 'ACTIVE'` or `ingestionStatus == 'live'`).
- Batch connection (`_connectAllWorkspaceProjects()`) skips any server that is not running.

### Implementation References
- **`app/lib/screens/projects_screen.dart`**:
  - `isServerOn = project.upsStatus.toUpperCase() == 'READY' || project.upsStatus.toUpperCase() == 'ACTIVE' || project.ingestionStatus.toLowerCase() == 'live'`.
  - In `_buildConnectWorkspaceDialog`:
    ```dart
    onTap: (!isServerOn && !isConnected) ? null : () => _toggleProjectConnection(project)
    ```
  - Connect button:
    ```dart
    if (isConnected) ...
    else if (!isServerOn) const SizedBox.shrink()
    else Container( /* + Connect button */ )
    ```

---

## 4. Dual-Plane Routing & Control Plane Isolation

### Expected Behavior
- The app operates on a multi-server architecture:
  - **Control Plane (Port 28000)**: Database authority for projects, organizations, user memberships, AST code parsing, file tree, symbols, and dependencies.
  - **Data Plane (Port 28100-28999 Pool)**: Per-project isolated execution containers for queries and running tasks.
- When opening a project, the client shifts its base URL to the project's data plane container.
- However, the client must **preserve `controlPlaneUrl` (port 28000) and `controlPlaneToken`**.
- Fetching projects (`fetchProjects()`) must **always query `controlPlaneUrl`**, never the isolated data-plane port.
- Code exploration endpoints (`fetchProjectFiles()`, `fetchFileDetail()`, `fetchProjectSymbols()`, `fetchProjectDependencies()`, `fetchDiscoverySummary()`):
  - Must attempt dual-plane routing: if the data plane returns `404 PROJECT_NOT_FOUND` or `422`, automatically query `controlPlaneUrl` with `controlPlaneToken`.
  - Must automatically re-authenticate via `reauthenticateControlPlane()` if `401 INVALID_TOKEN` is received.

### Implementation References
- **`app/lib/services/api_service.dart`**:
  - `static String controlPlaneUrl`: Tracks primary port 28000.
  - `static String? controlPlaneToken`: Preserves the control plane session JWT.
  - `setBaseUrl()` updates `controlPlaneUrl` when pointing to control plane ports (28000 / 8000).
  - `fetchProjects()` routes to `controlPlaneUrl` with `controlPlaneToken`.
  - `fetchProjectFiles()` loops through `[baseUrl, controlPlaneUrl]` with automatic 404/422 fallback.
- **`app/lib/main.dart`**:
  - `_handleOpenProject()` saves `controlPlaneUrl` and `controlPlaneToken` before shifting `baseUrl`.
  - `_handleBackToProjects()` reverts `baseUrl` to `controlPlaneUrl`, restores `controlPlaneToken`, and loads persisted projects immediately.

---

## 5. UI and Theme Consistency

### Expected Behavior
- UnoPalette themes (dark and light modes) supported across all screens.
- Top navigation bar displays breadcrumbs with the active repository name (`owner/repo · branch`).
- Sidebar navigation supports quick switching between Projects, Overview, Chat, Files, Architecture, Discoveries, and Knowledge.

