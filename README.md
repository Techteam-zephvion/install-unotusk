# Unotusk MVP — Stage 0 Foundation

A clean-slate, production-oriented technical foundation for the **Unotusk Project Intelligence** product.

This repository establishes the authoritative baseline for tenant isolation, project boundaries, pgvector-ready persistence, background task plumbing, and Next.js frontend workflows.

---

## 1. System Architecture

```
Unotusk-MVP/
├── apps/
│   ├── web/                     # Next.js 14+ App Router frontend (TypeScript, Tailwind CSS)
│   └── api/                     # FastAPI async backend (Python 3.12, SQLAlchemy 2, Pydantic v2)
├── packages/
│   └── types/                   # Shared TypeScript definitions for API contracts
├── services/
│   └── workers/                 # Lightweight Redis background task consumer
├── infrastructure/
│   ├── docker/                  # Dockerfiles for web, api, and worker
│   └── scripts/                 # Migration and helper scripts
├── docs/
│   └── architecture/
│       └── stage-0.md           # Stage 0 architecture and security model
├── tests/
│   ├── unit/                    # Unit tests (schemas, slugification, security)
│   ├── integration/             # Database relationships, cascading, Redis worker
│   └── api/                     # Auth, Project CRUD, and Cross-Org Isolation tests
├── .env.example                 # Example configuration
├── docker-compose.yml           # Local multi-container development environment
└── pytest.ini                   # Test runner configuration
```

---

## 2. Prerequisites

- **Docker & Docker Compose** (Docker v24+, Compose v2+)
- **Node.js 20+** and **npm**
- **Python 3.12+**

---

## 3. Quickstart (Local Docker Compose)

```bash
# 1. Clone repository
git clone <repository_url>
cd Unotusk-MVP

# 2. Configure environment
cp .env.example .env

# 3. Start complete local stack (Postgres + pgvector, Redis, API, Worker, Web)
docker compose up --build
```

Access the services:
- **Web Application**: `http://localhost:3000` (or `http://localhost:3005`)
- **FastAPI Documentation**: `http://localhost:8000/docs`
- **Readiness Check**: `http://localhost:8000/health/ready`

---

## 4. Local Development (Without Docker)

### Backend & Worker
```bash
# Setup Python virtual environment
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start API server
uvicorn apps.api.src.main:app --reload --port 8000

# Start Worker (in separate terminal)
python services/workers/worker.py
```

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

---

## 5. Running Automated Tests

Run the complete test suite:

```bash
# Run pytest across unit, integration, and security tests
apps/api/.venv/bin/pytest -v

# Run with coverage report
apps/api/.venv/bin/pytest --cov=apps/api/src
```

### Golden Security Test
Run the cross-organization tenant isolation test:
```bash
apps/api/.venv/bin/pytest tests/api/test_cross_org_isolation.py -v
```

---

## 6. Stage 0 Scope & Decisions

### Implemented in Stage 0:
- **Identity & Organization Boundaries**: User registration, password hashing (bcrypt), JWT generation/validation, organization membership roles (`OWNER`, `ADMIN`, `MEMBER`).
- **Project Boundary Enforcement**: Projects are strictly scoped to organizations. Slugs are unique within organizations.
- **Cross-Organization Protection**: Enforced backend validation on every project lookup/mutation preventing IDOR access.
- **Database & Migrations**: Reproducible Alembic migrations, PostgreSQL 16 with `pgvector` enabled at database level.
- **Background Plumbing**: Redis task queue dispatcher and worker loop confirming `API -> Queue -> Worker` communication.
- **Next.js UI Flow**: Login, Signup, Organization selector, Project List, Create Project, and Project Overview with clean Stage 1 repository connection entry point.

### Intentionally Deferred to Later Stages:
- **Stage 1**: GitHub OAuth, GitHub App webhook handling, repository cloning, AST parsing, commit history ingestion.
- **Stage 2+**: Vector embeddings pipeline, similarity search, ontology graph construction, AI Project Intelligence Report generation.
- **Out of Scope**: Licensing, degraded mode, enterprise mTLS, microservice sprawl, LLM chat agents.
