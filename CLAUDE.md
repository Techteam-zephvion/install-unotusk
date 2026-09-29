# CLAUDE.md — Unotusk MVP

## 0. What this is

The **authoritative single-tenant MVP** of Unotusk Project Intelligence. It demonstrates evidence-grounded codebase intelligence, proactive architectural risk discovery, and persistent team knowledge in a self-contained local deployment.

The complex multi-repository microservice topology (`US`, `UPS`, `AI-PIE`, `UP`, `UCA`, `UAC`, OIDC federation, licensing heartbeat, degraded mode, mTLS mesh, Qdrant, Phoenix) from `~/PRO/Unotusk-2` is **deliberately discarded** for this MVP.

## 1. Current Architecture & Stack

```
UNOTUSK MVP =
Flutter Desktop Client (app/) + Server Setup App (setup_app/)
                       │ (HTTP REST: Port 8000)
                       ▼
FastAPI Async Backend (apps/api/)
  ├── Parser Engine (Tree-sitter: Python, TS/JS, Go)
  ├── Proactive Discovery Engine (9 Analyzers)
  ├── Grounded Context Engine (Multi-Signal SQL + 1-Hop Graph)
  ├── Project Intelligence Report Engine (10 Sections)
  └── Customer Knowledge Service (ADRs, Constraints)
         │                               │
         ▼                               ▼
PostgreSQL 16 + pgvector         Redis 7 + Background Worker
(Relational Context, AST,       (services/workers/worker.py)
 Findings, Reports, Chunks)
```

- **Desktop Client (`app/`)**: Native Flutter desktop application with 1:1 Warm Dark Figma design system (`#181816`), Young/Instrument Serif typography, and 9 workspace tabs (`AskTab`, `SpecHistoryTab`, `OntologyTab`, `IngestionFeedTab`, `DiscoveriesTab`, `ArchitectureTab`, `FilesTab`, `KnowledgeTab`, `OverviewTab`).
- **Server Setup App (`setup_app/`)**: Native Flutter desktop wizard for single-command/wizard deployment and pre-flight health checks.
- **Backend API (`apps/api/`)**: FastAPI Python 3.12 async backend providing REST endpoints for auth, projects, repository ingestion, discovery, grounded ask, reports, and knowledge management.
- **Worker (`services/workers/`)**: Lightweight Redis task consumer executing repository ingestion, discovery analysis, and report generation asynchronously.
- **Database**: PostgreSQL 16 with `pgvector` extension.
- **LLM Grounding**: Multi-provider (`apps/api/src/services/llm/`): Groq (`qwen/qwen3.8-27b` default) or Claude 3.5 Sonnet, with deterministic offline synthesizer fallback for zero-hallucination testing and offline environments.
- **Web Frontend (`apps/web/`)**: Secondary Next.js 14 companion web client containerized in Docker Compose.

## 2. Explicitly Out of Scope for MVP

- No licensing, entitlement validation, or degraded mode.
- No cloud platform (`UP`) heartbeat or telemetry calls.
- No mTLS certificate meshes between services.
- No enterprise OIDC/SAML federation (uses local email + bcrypt + HS256 JWT).
- No standalone Auth Service (`US`), Company Server (`UPS`), or standalone `AI-PIE`.
- No Qdrant vector database or Phoenix observability service.
- No external tool connectors (Jira, Linear, Slack, Confluence) — Git active only.
- No autonomous code mutation or PR modification bots.

## 3. Repository Layout

```
Unotusk-MVP/
├── app/                  Flutter Desktop Employee Client (Warm Dark Figma UI)
├── setup_app/            Flutter Server Setup Wizard
├── apps/
│   ├── api/              FastAPI Backend & Embedded Intelligence Engines
│   └── web/              Next.js 14 Web Client (Dockerized)
├── packages/
│   └── types/            Shared TypeScript API types
├── services/
│   └── workers/          Redis background task consumer (worker.py)
├── infrastructure/
│   └── docker/           Dockerfiles for api, worker, and web
├── scripts/              Operational, verification, and packaging scripts
├── tests/                Pytest suite (unit, integration, api, security)
├── docs/                 Product specs, runbooks, and pilot reviews
└── docker-compose.yml    Local multi-container stack
```

## 4. Running Locally

```bash
# 1. Start backend stack with Docker Compose
docker compose up -d

# 2. Run Desktop Employee App
cd app
PATH=/home/devils/flutter/bin:$PATH flutter run -d linux

# 3. Run Server Setup Wizard
cd setup_app
PATH=/home/devils/flutter/bin:$PATH flutter run -d linux
```

## 5. Verification & Testing

```bash
# Backend pytest suite (unit, api, integration, security)
apps/api/.venv/bin/pytest -v

# Ruff linting
apps/api/.venv/bin/ruff check apps/api/ tests/

# Flutter Employee App tests & analyze
cd app && PATH=/home/devils/flutter/bin:$PATH flutter test
cd app && PATH=/home/devils/flutter/bin:$PATH flutter analyze

# Flutter Server Setup App tests & analyze
cd setup_app && PATH=/home/devils/flutter/bin:$PATH flutter test
cd setup_app && PATH=/home/devils/flutter/bin:$PATH flutter analyze
```
