# UNOTUSK MVP — QUICK START & PILOT USER MANUAL

**Product**: Unotusk MVP (v0.1.0)  
**Operating Principle**: *"Simple on the surface. Deep when needed."*  
**Audience**: Technical pilot users, engineering managers, software engineers.

---

## 1. Five-Minute Quick Start

### Step 1: Deploy or Connect to Unotusk Server
If running on your local workstation:
1. Extract `unotusk-server-setup-linux-x64-v0.1.0.tar.gz` and run `setup_app`.
2. Follow the wizard steps: **Get Started** → **Target (Local)** → **Verify Prerequisites** → **Deploy**.
3. Once the server is ready, copy the server address (`http://localhost:8000`).

*(If your team has deployed a shared server, obtain the server URL from your system administrator, e.g. `http://unotusk.internal:8000`).*

### Step 2: Launch Unotusk Employee Application
1. Extract `unotusk-client-linux-x64-v0.1.0.tar.gz` and execute `./app`.
2. On the **Server Connection** screen, confirm or input your server address (default: `http://localhost:8000`). Click **Connect** → **Continue to Sign In**.
3. On the **Sign In** screen, toggle **Don't have an account? Create one** to register your pilot account (Name, Email, Password).

### Step 3: Connect Your First Codebase
1. On the **Projects** dashboard, click **Connect Codebase** (or **Connect First Codebase** in the center).
2. Enter your repository URL (e.g., `https://github.com/psf/requests`).
   - *Notice*: Unotusk automatically infers the project name and slug from the Git URL.
3. Select your default branch (default: `main`) and click **Connect & Ingest**.

### Step 4: Monitor Ingestion & Explore Intelligence
- Watch the 5-phase transparent ingestion engine:
  `CLONING` → `SCANNING` → `PARSING` → `INDEXING` → `READY`.
- Once indexing completes, explore your codebase through 6 dedicated tabs:
  1. **Overview**: Codebase metrics, language distribution, and attention centers.
  2. **Discoveries**: Automated audit findings (circular dependencies, coupling, test gaps).
  3. **Architecture**: Component map, callers, and dependencies.
  4. **Files**: AST symbol tree and syntax-highlighted source viewer.
  5. **Knowledge**: Curated architectural decisions and business constraints.
  6. **Ask**: Grounded Q&A with clickable code evidence citations.

---

## 2. Employee Application User Manual

### 2.1 Exploring Architecture & Discoveries
- **Finding Cards**: Each discovery provides category, severity, affected files, and actionable descriptions.
- **Deep Code Links**: Clicking on any symbol or file link in Discoveries or Architecture takes you straight into the source code viewer with line highlights.
- **Keyboard Shortcuts**:
  - `Ctrl + 1`: Overview
  - `Ctrl + 2`: Discoveries
  - `Ctrl + 3`: Architecture
  - `Ctrl + 4`: Files
  - `Ctrl + 5`: Knowledge
  - `Ctrl + 6` (or `Ctrl + K`): Grounded Ask

### 2.2 Asking Grounded Questions (Evidentiary Intelligence)
- Type questions about your codebase in the **Ask** tab (e.g., *"How is connection pooling handled?"* or *"Where are HTTP requests authenticated?"*).
- **Evidentiary Integrity**: Unotusk never hallucinates. Every answer displays an evidentiary grounding badge and clickable citation chips pointing to exact file paths and line ranges.
- If a query asks about a non-existent file or concept, Unotusk clearly states the absence of code evidence without fabricating answers.

### 2.3 Curating Team Architectural Knowledge
- Engineering intent and undocumented business rules often live in developers' heads, not in comments.
- In the **Knowledge** tab, click **Add Knowledge** to record:
  - **Category**: Architecture Decision, Business Rule, Intent, Constraint, Exception, Critical Component.
  - **Title & Description**: Plain-language context for why something is built the way it is.
  - **Associated File & Symbol**: Ground the note to specific code artifacts.
- The system visually marks notes as **TEAM CURATED** to distinguish them from automated **OBSERVED FACTS**.

---

## 3. Demo & Reset Procedures
To reset your pilot environment or seed sample demonstration data with pre-calculated discoveries:
```bash
# Seed rich demo data (Acme Payments with circular dependency & coupling findings)
python scripts/seed_demo.py
```
Log in using:
- **Email**: `demo@unotusk.io`
- **Password**: `password123`

---

## 4. Support & Diagnostics
- If you encounter any server issues, inspect the container logs:
  ```bash
  docker compose logs -f api
  ```
- Unotusk automatically redacts API keys, tokens, and passwords in all diagnostic logs and UI views.
