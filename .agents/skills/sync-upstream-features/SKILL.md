---
name: sync-upstream-features
description: Safely pull and merge updates from the upstream repository (target or origin) into unotusk_flutter_app while keeping all local feature implementations, architectural invariants, dual-plane fallbacks, and project persistence 100% intact.
---

# Sync Upstream Features & Architectural Invariant Protection

This skill provides a battle-tested runbook and automated tooling to pull updates from upstream Git branches (`target` or `origin`, specifically `frontend-sidebar-extended-v3`) into `unotusk_flutter_app` without regressing or wiping any local features, architectural fixes, or backend-as-master guards.

---

## Why This Skill Is Critical

In the past, blind `git pull` or unguided merge operations overwrote critical architectural patterns in `unotusk_flutter_app`, leading to severe regressions:
1. **Vanishing Dashboard Projects**: Connected projects disappeared from the dashboard whenever a user navigated back or opened a project because upstream lacked local disk/SharedPreferences serialization and wiped cached projects on empty responses.
2. **File Explorer 404 & 401 Errors**: Upstream routed file tree requests directly to container data plane ports (28100–28999) using invalidated tokens, triggering `PROJECT_NOT_FOUND` (404) and `INVALID_TOKEN` (401). Our repo implements control plane routing (port 28000) with dual-plane fallback.
3. **Resurrected Phantom Projects**: Upstream re-injected old laptop directories from `~/.unotusk/servers.json` (`Project 1`, `Sahaay`), violating the Server-As-Master architectural rule.
4. **Connecting to Stopped Servers**: Upstream showed active `+ Connect` buttons for stopped or connecting containers.

This skill automates the pull workflow and validates **15 essential feature invariants** to ensure zero regressions.

---

## The 5 Core Invariants Protected

| Category | Invariant Rule | Files Impacted |
| :--- | :--- | :--- |
| **1. Workspace Persistence** | Connected projects must persist indefinitely in `SharedPreferences` and `$TEMP/unotusk_connected_projects_data.json` until explicitly disconnected by the user or reported stopped by the server. | `app/lib/models/models.dart`, `app/lib/services/api_service.dart`, `app/lib/screens/projects_screen.dart` |
| **2. Server Authority** | The backend server (`/api/v1/projects`) is the sole master of what projects exist. Never inject phantom projects from local laptop disk. | `app/lib/services/api_service.dart` |
| **3. Stopped Server Guard** | Projects with inactive or stopped server status (`STOPPED`, `OFFLINE`, `CONNECTING`) must hide the `+ Connect` button and disable click interaction. | `app/lib/screens/projects_screen.dart` |
| **4. Dual-Plane Routing** | Maintain `controlPlaneUrl` (port 28000) and `controlPlaneToken`. If container ports (28100+) return 404 or 422 for files/symbols/dependencies, fall back to control plane with re-authentication. | `app/lib/services/api_service.dart`, `app/lib/main.dart` |
| **5. Navigation Preservation** | Opening a project and returning to the dashboard must seamlessly restore control plane session state and instantly display persisted connected projects. | `app/lib/main.dart` |

For complete technical specifications of each invariant, refer to:
[feature_invariants.md](file:///c:/Users/sindk/OneDrive/Desktop/antigravity%20webs/unotusk_flutter_app/.agents/skills/sync-upstream-features/references/feature_invariants.md)

---

## Automated Tooling

This skill includes two automated Python scripts located in `scripts/`:

1. **`verify_features.py`**:
   Comprehensive static analysis verification suite containing 15 automated checks verifying AST, model methods, dual-plane fallbacks, and UI guards.
   ```powershell
   python .agents/skills/sync-upstream-features/scripts/verify_features.py
   ```

2. **`safe_pull.py`**:
   The primary CLI entrypoint that safely manages stashing, remote fetching, git merging/rebasing, conflict warnings, and automatic verification.
   ```powershell
   python .agents/skills/sync-upstream-features/scripts/safe_pull.py --remote target --branch frontend-sidebar-extended-v3
   ```

---

## Step-by-Step Execution Workflow

### Step 1: Pre-Pull Verification
Before pulling anything, ensure that your current local state satisfies all 15 invariants:
```powershell
cd "c:\Users\sindk\OneDrive\Desktop\antigravity webs\unotusk_flutter_app"
python .agents/skills/sync-upstream-features/scripts/verify_features.py
```
> If any check fails, resolve it before attempting to pull upstream updates.

### Step 2: Execute Safe Pull
Run the automated safe pull script. By default, it targets remote `target` and branch `frontend-sidebar-extended-v3`:
```powershell
# If you have uncommitted changes you wish to preserve during pull:
python .agents/skills/sync-upstream-features/scripts/safe_pull.py --remote target --branch frontend-sidebar-extended-v3 --stash

# Or with custom remote (e.g., origin):
python .agents/skills/sync-upstream-features/scripts/safe_pull.py --remote origin --branch frontend-sidebar-extended-v3 --stash
```

### Step 3: Conflict Resolution Guidance
If git detects merge conflicts, do **not** accept upstream's version wholesale (`--theirs`). Apply the following file-by-file rules:

#### A. `app/lib/models/models.dart`
- **Keep**: `ProjectItem.toJson()` and `ProjectItem.fromJson(Map<String, dynamic> json)`.
- **Reason**: Required for project disk & SharedPreferences caching.

#### B. `app/lib/services/api_service.dart`
- **Keep**:
  - `static String controlPlaneUrl = 'http://10.0.0.59:28000';`
  - `static String? controlPlaneToken;`
  - `static final String _connectedProjectsDataFile = ...;`
  - `savePersistedConnectedProjects()` and `loadPersistedConnectedProjects()`.
  - In `fetchProjects()`: query `controlPlaneUrl`, use `controlPlaneToken`, and **never** append local laptop disk servers.
  - In `fetchProjectFiles()`, `fetchFileDetail()`, `fetchProjectSymbols()`, `fetchProjectDependencies()`, `fetchDiscoverySummary()`: keep the dual-plane fallback loop probing `[baseUrl, controlPlaneUrl]`.

#### C. `app/lib/screens/projects_screen.dart`
- **Keep**:
  - `final bool isServerOn = ...;` guard checking for `'READY'`, `'ACTIVE'`, or `'live'`.
  - Hiding `+ Connect` via `const SizedBox.shrink()` when `!isServerOn`.
  - `initState()` loading `connectedWorkspaceProjects` directly into `_projects`.
  - In `_fetchServerProjects()`: do not wipe active `_projects` when response is empty.

#### D. `app/lib/main.dart`
- **Keep**:
  - In `_handleOpenProject()`: save `controlPlaneUrl` and `controlPlaneToken` before re-pointing `baseUrl`.
  - In `_handleBackToProjects()`: restore `baseUrl` to `controlPlaneUrl`, restore `controlPlaneToken`, and call `loadPersistedConnectedProjects()`.

### Step 4: Post-Pull Verification
After resolving conflicts or completing the merge, run the verification suite:
```powershell
python .agents/skills/sync-upstream-features/scripts/verify_features.py
```
Ensure all 15 checks output `[PASS]` and exit code is `0`.

---

## Important Rules & Constraints
- **Never Commit or Push Without Explicit User Approval**:
  Do not run `git commit` or `git push` unless the user specifically instructs you to do so.
- **Always Run Invariant Checks**:
  Never assume a merge was harmless. Always run `verify_features.py`.

