# UNOTUSK MVP — CUSTOMER PILOT ONBOARDING CHECKLIST

**Document**: Customer Pilot Onboarding Manual & Verification Protocol  
**Version**: Unotusk MVP v0.1.0  
**Target Audience**: Pilot Engineering Leads, Developers, Design Partners  

---

## 1. Onboarding Objective

This checklist provides a zero-coaching, step-by-step verification protocol ensuring a new technical user can independently navigate the complete **10-Step Unotusk Value Journey** in under 10 minutes:

```
[Connect Server] → [Sign Up/In] → [Create Project] → [Connect Git Repo] → [Monitor Ingestion]
        ↓
[Open Workspace] → [Understand Discoveries] → [Inspect Code & AST] → [Ask Questions] → [Curate Knowledge]
```

---

## 2. The 10-Step Customer Value Journey

### Step 1: Install Client & Connect Server
- **Action**: Extract `unotusk-client-linux-x64-v0.1.0.tar.gz` and run `./app`.
- **UI State**: Server Connection Screen.
- **Verification**:
  - Pre-populated default hint `http://localhost:8000`.
  - Enter server URL and click **Connect**.
  - System verifies connectivity with green indicator: *"Connected to Unotusk Server"*.
  - Click **Continue to Sign In**.

### Step 2: Account Creation & Sign In
- **Action**:
  - Click **Don't have an account? Create one**.
  - Enter Full Name (e.g. `Jane Doe`), Work Email (`jane@pilot.company.com`), and Password (`SecurePass123!`).
  - Click **Create Account & Continue**.
- **Verification**:
  - System automatically creates the pilot organization, binds the user as Organization Owner, issues a JWT token, and navigates to the Projects Dashboard.

### Step 3: Create Project & Define Slug
- **Action**:
  - Click **Connect First Codebase** (or **Connect Codebase** in top header).
  - Enter Git Repository URL (e.g., `https://github.com/pilot-org/service-auth`).
- **Verification**:
  - Project name (`service-auth`) and slug (`service-auth`) are automatically derived.
  - User can edit or confirm the derived project name.

### Step 4: Connect Repository
- **Action**:
  - Confirm default branch (default: `main`).
  - (Optional) Enter Personal Access Token if private repository.
  - Click **Connect & Ingest**.
- **Verification**:
  - Modal confirms repository creation and seamlessly transitions to the Ingestion Progress view.

### Step 5: Observe Ingestion Progress
- **Action**: Watch the honest 5-stage ingestion state machine:
  1. `CLONING` — Clones shallow Git ref into isolated scratch volume.
  2. `SCANNING` — Detects file types, LOC, and language distribution.
  3. `PARSING` — Extracts AST symbols (functions, classes, callers, dependencies).
  4. `INDEXING` — Indexes code chunks and structural graph edges into pgvector.
  5. `READY` — Activates project workspace.
- **Verification**:
  - Progress shows real stage names (no artificial percentage timers).
  - Once status changes to `READY`, click **Open Workspace**.

### Step 6: Explore Project Overview
- **Action**: Land on **Overview** tab (`Ctrl + 1`).
- **Verification**:
  - Key codebase metrics: Total Files, Total Lines of Code, Primary Languages.
  - Attention Centers: Modules with high churn, coupling, or dependency concentration.

### Step 7: Inspect Architectural Discoveries
- **Action**: Click **Discoveries** tab (`Ctrl + 2`).
- **Verification**:
  - Discoveries feed displays categorized findings (Circular Dependencies, Hidden Coupling, Test Gaps).
  - Severity tags (High, Medium, Low) and affected file paths are clearly displayed.
  - Click a discovery card to expand the explanation and see why it matters.

### Step 8: Investigate Code Evidence & AST Symbols
- **Action**: Click **Files** tab (`Ctrl + 4`) or click directly on an affected file link in Discoveries.
- **Verification**:
  - File tree navigates cleanly.
  - Syntax-highlighted code viewer displays the source lines.
  - AST symbol inspector shows classes, methods, callers, and dependencies with zero lag (<100ms).

### Step 9: Ask Grounded Technical Questions
- **Action**: Click **Ask** tab (`Ctrl + 6` or `Ctrl + K`).
- **Sample Questions to Try**:
  - *"How does request authentication work in this codebase?"*
  - *"Where is database connection pooling configured?"*
  - *"What are the main entry points for the HTTP API?"*
- **Verification**:
  - Grounded answer appears with an evidentiary grounding badge.
  - Clickable citation chips (e.g. `src/auth/jwt.py:45-82`) jump straight to the source viewer at that line range.
  - If asking about something non-existent, the system honestly states absence of evidence rather than hallucinating.

### Step 10: Curate Team Knowledge
- **Action**: Click **Knowledge** tab (`Ctrl + 5`).
  - Click **Add Knowledge**.
  - Select Category: `Architecture Decision` (or `Business Rule`, `Constraint`, `Exception`).
  - Title: *"Why token blacklisting uses Redis TTL instead of DB"*.
  - Description: *"Tokens are stored in Redis with matching expiration to prevent table bloat in Postgres."*
  - Link associated file: `src/auth/jwt.py`.
  - Click **Save Knowledge**.
- **Verification**:
  - Card appears with a prominent **TEAM CURATED** badge (distinguishing human intent from machine **OBSERVED FACTS**).
  - Subsequent Ask queries incorporate this curated knowledge into grounded synthesis!

---

## 3. Onboarding Success Criteria
A pilot onboarding session is considered **100% Successful** when:
1. The technical user completes all 10 steps without operator intervention.
2. The user identifies at least one real code insight or discovery in their codebase.
3. The user successfully links a piece of team context via the Knowledge tab.
4. Total time from launch to value is under 10 minutes.
