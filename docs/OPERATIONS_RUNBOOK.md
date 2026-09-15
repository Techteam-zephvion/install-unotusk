# UNOTUSK CUSTOMER OPERATIONS RUNBOOK

**Target Version**: Unotusk MVP (v0.1.0)  
**Audience**: DevOps Engineers, System Administrators, Customer Operations Teams  
**Last Updated**: September 2026

---

## 1. System Requirements & Prerequisites

### 1.1 Hardware Sizing
| Tier | VCPU | RAM | Disk Space | Workload Capacity |
|---|---|---|---|---|
| **Minimal / Pilot** | 2 cores | 4 GB | 20 GB SSD | 1-5 active repositories (<50k LOC each) |
| **Standard Production** | 4 cores | 8 GB | 50 GB SSD | 5-25 active repositories (<200k LOC each) |
| **High Capacity** | 8 cores | 16 GB | 100 GB NVMe | 25+ enterprise repositories |

### 1.2 Host Software Requirements
- **Operating System**: Ubuntu 22.04 LTS+, Debian 12+, RHEL 9+, macOS 13+, or Windows 11 with WSL2.
- **Container Engine**: Docker Engine 24.0.0+ (or Docker Desktop 4.25.0+).
- **Compose Plugin**: Docker Compose v2.20.0+ (`docker compose` syntax).
- **Network Access**:
  - Inbound: Port `8000` (Unotusk API HTTP/WebSocket) accessible to Employee App users.
  - Outbound (Optional): Outbound HTTPS (`443`) to Groq / Anthropic API endpoints if cloud LLM synthesis is enabled. (Offline deterministic mode works with zero outbound connectivity).

---

## 2. Installation & Server Setup Wizard

### 2.1 Using the Unotusk Server Setup App (Recommended)
1. Launch the **Unotusk Server Setup Application** (`setup_app`).
2. The wizard automatically performs pre-flight checks:
   - Docker Engine daemon connectivity.
   - Docker Compose v2 availability.
   - Free disk space verification (>10 GB).
   - Port collision detection on 8000, 5432, 6379.
3. Select your deployment directory (default: `~/.unotusk/server`).
4. Configure application credentials:
   - Generated high-entropy `AUTH_SECRET` and `POSTGRES_PASSWORD`.
   - Optional: Groq or Anthropic LLM API Key (leave blank for offline fallback).
5. Click **Deploy Server**:
   - The wizard writes hardened `.env` (file mode `0600`) and `docker-compose.yml`.
   - Boots PostgreSQL (pgvector), Redis 7, Alembic migration init-container, and FastAPI backend.
   - Verifies readiness via `GET /health/ready`.
6. Use the displayed **Server URL** (`http://<host-ip>:8000`) to connect the Employee App.

### 2.2 CLI Deployment (Headless Host)
```bash
# 1. Clone or copy deployment directory
cd /opt/unotusk

# 2. Generate secure environment
cp .env.example .env
# Edit .env and supply non-default secrets:
# AUTH_SECRET=$(openssl rand -hex 32)
# POSTGRES_PASSWORD=$(openssl rand -hex 24)

# 3. Start services with migration init-container
docker compose up -d

# 4. Verify system health
curl -f http://localhost:8000/health/ready
```

---

## 3. Daily Operations & Monitoring

### 3.1 Health and Readiness Endpoints
- **Liveness Probe**: `GET http://localhost:8000/health`  
  Returns `{"status": "healthy", "service": "unotusk-server"}`.
- **Readiness Probe**: `GET http://localhost:8000/health/ready`  
  Validates active database connection pool and Redis cache readiness.

### 3.2 Service Logging & Inspection
```bash
# View aggregated live logs
docker compose logs -f

# View API logs only
docker compose logs -f api

# View database logs
docker compose logs -f postgres
```
*Note: Diagnostic logs automatically redact sensitive tokens, database passwords, and API keys.*

---

## 4. Operational Backup & Restore Procedures (TASK-512)

### 4.1 Automated Database Backup (`pg_dump`)
Run a consistent logical database backup of the PostgreSQL database:
```bash
# Set timestamp and backup path
BACKUP_DIR="/opt/unotusk/backups"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/unotusk_backup_${TIMESTAMP}.sql.gz"

# Execute pg_dump directly inside the postgres container
docker compose exec -T postgres pg_dump -U postgres unotusk | gzip > "$BACKUP_FILE"

echo "Backup created successfully: $BACKUP_FILE"
```

### 4.2 Restoring from Backup
```bash
# 1. Ensure containers are running
docker compose up -d postgres

# 2. Terminate existing connections and recreate empty database
docker compose exec -T postgres psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'unotusk' AND pid <> pg_backend_pid();"
docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS unotusk;"
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE unotusk;"

# 3. Restore schema and data from compressed backup
gunzip -c /opt/unotusk/backups/unotusk_backup_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T postgres psql -U postgres -d unotusk

# 4. Run migrations to verify schema alignment
docker compose run --rm migration
docker compose restart api
```

### 4.3 Volume-Level Backup
To backup persistent volume storage directly:
```bash
# Stop containers cleanly before volume snapshot
docker compose stop

# Archive volume data directory
tar -czvf /opt/unotusk/backups/postgres_volume_$(date +"%Y%m%d").tar.gz -C /var/lib/docker/volumes/unotusk_postgres_data/_data .

# Restart services
docker compose start
```

---

## 5. Safe Reset & Uninstallation Guardrails (TASK-513)

### 5.1 Non-Destructive Service Restart / Teardown
To restart or stop the Unotusk services **without losing any customer data or indexed repositories**:
```bash
# Stop all service containers (preserves database volumes)
docker compose down

# Restart services cleanly
docker compose up -d
```

### 5.2 Destructive Reset (Requires Explicit Confirmation)
> [!CAUTION]
> Running `docker compose down -v` permanently destroys all PostgreSQL tables, user accounts, indexed repository snapshots, symbols, findings, and customer knowledge. Never run this in production without a verified backup.

To perform a complete factory reset:
```bash
# 1. Stop containers and destroy named persistent volumes
docker compose down -v

# 2. Remove configuration files if decommissioning host
rm -rf ~/.unotusk/server/.env ~/.unotusk/server/docker-compose.yml
```

---

## 6. Troubleshooting & Diagnostics

| Symptom | Probable Cause | Remediation |
|---|---|---|
| `/health/ready` returns `503 Service Unavailable` | Database container not ready or migration running | Check `docker compose logs migration` and `docker compose logs postgres`. Ensure PostgreSQL has completed startup. |
| API returns `401 Unauthorized` | Invalid or expired JWT token, or `AUTH_SECRET` changed | Log in again through the Employee App. If `AUTH_SECRET` in `.env` was modified, existing sessions are invalidated. |
| Port collision on `8000` | Another service is using port 8000 | In Setup App, change Server Port to `8080` or `9000`, or edit `PORT` in `.env` and `ports:` in `docker-compose.yml`. |
| LLM queries return offline structured answers | No Groq/Anthropic API key configured or network blocked | Expected behavior. Offline synthesis generates grounded answers from AST symbols and code chunks. To enable cloud synthesis, supply a valid `GROQ_API_KEY` in `.env`. |
| Repository ingestion fails | Corrupt Git repo or inaccessible remote URL | Check `docker compose logs api`. Ensure repo path is readable and contains valid source files. |

---

## 7. Security Hardening Checklist (TASK-510)
- [x] Host port bindings for PostgreSQL (`5432`) and Redis (`6379`) restricted to `127.0.0.1` or internal docker network only.
- [x] Sensitive parameters in logs redacted using regex sanitizer.
- [x] Debug endpoints (`/context/search`) disabled in `APP_ENV=production`.
- [x] Environment files generated with restrictive filesystem permissions (`0600`).
- [x] Multi-tenant and cross-project database queries enforce organization and project foreign key scoping.
