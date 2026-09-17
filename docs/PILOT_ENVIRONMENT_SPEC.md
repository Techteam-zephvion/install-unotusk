# UNOTUSK MVP — PILOT ENVIRONMENT SPECIFICATION

**Document**: Pilot Environment Specification  
**Version**: Unotusk MVP v0.1.0  
**Status**: APPROVED FOR PILOT CUSTOMERS  
**Scope**: Single-Customer Design Partner / Pilot Deployment  

---

## 1. Executive Overview

This specification establishes the deployment topology, infrastructure requirements, network configuration, client distribution, and operational boundaries for running a single-customer pilot of **Unotusk MVP v0.1.0**.

The goal of the pilot environment is to provide a clean, secure, self-contained installation that allows an engineering team to connect real codebases, explore automated architecture discoveries, ask grounded questions, and curate team knowledge with zero external dependencies or multi-tenant complexity.

---

## 2. Infrastructure & Host Sizing

### 2.1 Host Machine Sizing
The pilot environment runs on a single host (bare-metal developer workstation, dedicated internal server, or isolated cloud VM):

| Resource | Minimum Specification | Recommended Specification |
|---|---|---|
| **CPU Architecture** | x86_64 (AMD64) | x86_64 (AMD64) |
| **CPU Cores** | 2 Physical Cores (4 vCPU) | 4+ Physical Cores (8 vCPU) |
| **System Memory** | 4 GB RAM | 8 GB RAM |
| **Available Disk Space** | 20 GB free SSD | 50 GB free SSD / NVMe |
| **Operating System** | Ubuntu 22.04 LTS / Debian 12 / RHEL 9 | Ubuntu 22.04 / 24.04 LTS |

### 2.2 Host Software Prerequisites
- **Container Engine**: Docker Engine 24.0.0+ (or Docker Desktop 4.25.0+)
- **Compose Tooling**: Docker Compose v2.20.0+ (standard `docker compose` plugin)
- **Local Utilities**: `curl`, `tar`, `gzip`, `sha256sum`

---

## 3. Deployment Topology & Network Architecture

### 3.1 Single-Customer Container Stack
The pilot environment deploys 4 interconnected containers on an internal Docker bridge network (`unotusk-network`):

```
                        Pilot User (Employee Desktop App)
                                      |
                                      v (HTTP / Port 8000)
┌────────────────────────────────────────────────────────────────────────┐
│ Host Machine                                                           │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ unotusk-api (FastAPI HTTP Service, Port 8000)                  │   │
│   └─────────────────┬───────────────────────────────┬──────────────┘   │
│                     │                               │                  │
│                     v (internal network)            v (internal network)
│   ┌─────────────────────────────────┐   ┌──────────────────────────┐   │
│   │ unotusk-postgres (pgvector:pg16)│   │ unotusk-redis (Redis 7)  │   │
│   │ Bound strictly: 127.0.0.1:5432  │   │ Bound: 127.0.0.1:6379    │   │
│   └─────────────────────────────────┘   └───────────┬──────────────┘   │
│                                                     │                  │
│                                                     v                  │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ unotusk-worker (Async Ingestion, AST Parsing, Discovery Engine)│   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Network Exposure & Port Bindings
- **API Port (`8000`)**: Accessible to pilot users running the Employee App. Bound to `0.0.0.0:8000` or the specific host network interface.
- **Database Port (`5432`)**: Strictly bound to `127.0.0.1` on the host to prevent unauthorized LAN exposure.
- **Redis Port (`6379`)**: Strictly bound to `127.0.0.1` on the host.
- **Outbound Network Requirements**:
  - *Public Git Repositories*: Outbound HTTPS (`443`) to GitHub / GitLab.
  - *Private Git Repositories*: Outbound HTTPS (`443`) or SSH (`22`) with provided tokens or deployment keys.
  - *Cloud LLM Synthesis (Optional)*: Outbound HTTPS (`443`) to Groq (`api.groq.com`) or Anthropic (`api.anthropic.com`).
  - *Offline Deterministic Mode*: **Zero outbound Internet required**. If no LLM API key is supplied, Unotusk operates completely offline using deterministic heuristic synthesis.

---

## 4. Deployment Methods

### Option A: Guided GUI Deployment (Recommended for Workstations)
1. Extract `dist/unotusk-server-setup-linux-x64-v0.1.0.tar.gz`.
2. Launch `./setup_app`.
3. The wizard validates Docker, Compose, ports, and disk space.
4. Generates cryptographically secure secrets (`AUTH_SECRET`, `POSTGRES_PASSWORD`).
5. Executes deployment and verifies readiness via `GET /health/ready`.

### Option B: Headless CLI Deployment (Recommended for Remote Linux Servers)
1. Copy repository files or deployment archive to target server (e.g. `/opt/unotusk`).
2. Generate `.env` from `.env.example`:
   ```bash
   cp .env.example .env
   chmod 0600 .env
   sed -i "s/AUTH_SECRET=.*/AUTH_SECRET=$(openssl rand -hex 32)/" .env
   sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$(openssl rand -hex 24)/" .env
   sed -i "s/APP_ENV=.*/APP_ENV=production/" .env
   sed -i "s/DEBUG=.*/DEBUG=false/" .env
   ```
3. Boot the stack:
   ```bash
   docker compose up -d
   ```
4. Verify readiness:
   ```bash
   curl -f http://localhost:8000/health/ready
   # Expected: {"status":"ready","database":"connected","redis":"connected"}
   ```

---

## 5. Employee App Distribution

### 5.1 Distribution Bundle
- **Archive**: `dist/unotusk-client-linux-x64-v0.1.0.tar.gz` (9.7 MB)
- **Checksum Verification**:
  ```bash
  sha256sum -c dist/checksums.txt
  ```
- **Contents**:
  - `app`: Native Linux x86_64 executable.
  - `lib/`: Flutter runtime and GTK3 embedding libraries.
  - `data/`: Flutter application assets, fonts, and shaders.

### 5.2 Client Installation & Execution
```bash
tar -xzf unotusk-client-linux-x64-v0.1.0.tar.gz -C ~/unotusk-client
cd ~/unotusk-client
./app
```

---

## 6. Pilot Credentials & Authentication

1. **Initial Organization & Admin Creation**:
   - The pilot uses a dynamic, self-service registration model.
   - The first engineer to sign up via the Employee App (`POST /api/v1/auth/register`) automatically initializes their organization and receives full workspace privileges.
2. **Team Member Access**:
   - Additional engineers create accounts against the same server; they are automatically bound to the organization and can collaborate immediately on shared projects and knowledge.
3. **Session Management**:
   - JWT tokens signed with `AUTH_SECRET` (HS256).
   - Session restoration on app launch.
   - Expired sessions trigger graceful 401 redirection to login.

---

## 7. Supported Repository Formats & Boundaries

### 7.1 Supported Repositories
- **Git Providers**: GitHub, GitLab, Bitbucket, self-hosted Git instances over HTTPS or SSH.
- **Languages Parsed via Native AST**:
  - Python (`.py`)
  - TypeScript (`.ts`, `.tsx`)
  - JavaScript (`.js`, `.jsx`, `.mjs`)
  - Rust (`.rs`)
  - Go (`.go`)
- **Other File Types**: Ingested and indexed via universal heuristic and text chunking.

### 7.2 MVP Pilot Size Limits
To guarantee sub-second UI navigation and reliable ingestion during the pilot:
- **Maximum Recommended Codebase Size**: ≤ 200,000 Lines of Code (LOC).
- **Maximum Files per Repository**: ≤ 2,500 files.
- **Repository Layout**: Single repository root. (Monorepo sub-package partitioning is scheduled for V1).

---

## 8. Verification & Health Monitoring

Pilot administrators can verify health at any time:
- **Liveness Probe**: `GET /health` (`{"status":"ok","version":"0.1.0"}`)
- **Readiness Probe**: `GET /health/ready` (`{"status":"ready","database":"connected","redis":"connected"}`)
- **Pre-Flight Verification Script**:
  ```bash
  python scripts/verify_pilot_env.py
  ```
