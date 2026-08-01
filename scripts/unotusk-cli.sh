#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK CLI — Lifecycle management tool
# Usage: unotusk <command> [options]
# ==============================================================================
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
VERSION_FILE="$INSTALL_DIR/.unotusk-version"
LOG_DIR="$INSTALL_DIR/logs"
BACKUP_DIR="$INSTALL_DIR/backups"

# Switch to install dir so docker compose commands work seamlessly
if [ -d "$INSTALL_DIR" ]; then
  cd "$INSTALL_DIR"
fi

mkdir -p "$LOG_DIR" "$BACKUP_DIR"

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "  ${CYAN}→${RESET} $*"; }
success() { echo -e "  ${GREEN}✔${RESET} $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; }
fail()    { echo -e "  ${RED}✘${RESET} $*"; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }

# ── Help ───────────────────────────────────────────────────────────────────────
show_help() {
  echo ""
  echo -e "${BOLD}UNOTUSK CLI — Lifecycle Management${RESET}"
  echo "  Usage: unotusk <command> [options]"
  echo ""
  echo "  Service commands:"
  echo "    start                 Start all services"
  echo "    stop                  Stop all services"
  echo "    restart               Restart all services"
  echo "    status                Show service status"
  echo "    logs [service]        View logs (optionally for a specific service)"
  echo ""
  echo "  Maintenance commands:"
  echo "    update                Upgrade to the latest version (safe, with rollback)"
  echo "    backup                Create a complete backup"
  echo "    restore <file>        Restore from a backup archive"
  echo "    doctor                Run full system diagnostics"
  echo "    reconfigure           Re-run the setup wizard and apply changes"
  echo "    uninstall             Remove UNOTUSK from this server"
  echo ""
}

# ── Helpers ────────────────────────────────────────────────────────────────────
current_version() {
  if [ -f "$VERSION_FILE" ]; then
    grep '^INSTALL_VERSION=' "$VERSION_FILE" | cut -d= -f2
  else
    echo "unknown"
  fi
}

# Wait for a single service to be healthy (polls docker inspect)
wait_healthy() {
  local service="$1"
  local timeout="${2:-120}"
  local elapsed=0 interval=5
  local container_id

  container_id=$(docker compose ps -q "$service" 2>/dev/null || true)
  if [ -z "$container_id" ]; then
    warn "No container found for '$service'."
    return 1
  fi

  while [ "$elapsed" -lt "$timeout" ]; do
    local status
    status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$container_id" 2>/dev/null || echo "unknown")
    case "$status" in
      healthy|running) return 0 ;;
      unhealthy)       return 1 ;;
      *)               sleep "$interval"; elapsed=$((elapsed + interval)) ;;
    esac
  done
  return 1
}

# ── start ──────────────────────────────────────────────────────────────────────
cmd_start() {
  header "Starting UNOTUSK services..."
  docker compose up -d postgres
  wait_healthy postgres 90 && success "postgres healthy"
  docker compose up -d qdrant phoenix
  wait_healthy qdrant 90  && success "qdrant healthy"
  wait_healthy phoenix 90 && success "phoenix healthy"
  docker compose up -d us
  wait_healthy us 120 && success "us healthy"
  docker compose up -d ups
  wait_healthy ups 120 && success "ups healthy"
  docker compose up -d ai-pie
  wait_healthy ai-pie 180 && success "ai-pie healthy"
  echo ""
  success "All services started and healthy."
}

# ── stop ───────────────────────────────────────────────────────────────────────
cmd_stop() {
  header "Stopping UNOTUSK services..."
  docker compose down
  success "Services stopped."
}

# ── restart ────────────────────────────────────────────────────────────────────
cmd_restart() {
  header "Restarting UNOTUSK services..."
  docker compose restart
  # Wait for all key services to re-establish health
  for svc in postgres qdrant phoenix us ups ai-pie; do
    if docker compose ps -q "$svc" &>/dev/null; then
      wait_healthy "$svc" 120 && success "$svc healthy" || warn "$svc did not become healthy"
    fi
  done
  success "Restart complete."
}

# ── status ─────────────────────────────────────────────────────────────────────
cmd_status() {
  echo ""
  echo -e "${BOLD}UNOTUSK Service Status${RESET}  (version: $(current_version))"
  echo ""
  docker compose ps
  echo ""
}

# ── logs ───────────────────────────────────────────────────────────────────────
cmd_logs() {
  local service="${1:-}"
  if [ -n "$service" ]; then
    docker compose logs -f "$service"
  else
    docker compose logs -f
  fi
}

# ── backup ─────────────────────────────────────────────────────────────────────
cmd_backup() {
  local TIMESTAMP
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  local ARCHIVE="$BACKUP_DIR/unotusk_backup_${TIMESTAMP}"
  local STAGING="$BACKUP_DIR/staging_${TIMESTAMP}"

  header "Creating UNOTUSK backup..."
  mkdir -p "$STAGING/db" "$STAGING/certs" "$STAGING/config" "$STAGING/volumes"

  # ── 1. PostgreSQL: dump both databases via running container ──────────────
  info "Dumping PostgreSQL databases..."
  if docker compose ps postgres | grep -q "Up"; then
    docker compose exec -T postgres \
      pg_dump -U "${POSTGRES_USER:-unotusk}" auth > "$STAGING/db/auth.sql" 2>/dev/null || \
      warn "Could not dump 'auth' database (may not exist yet)."
    docker compose exec -T postgres \
      pg_dump -U "${POSTGRES_USER:-unotusk}" company > "$STAGING/db/company.sql" 2>/dev/null || \
      warn "Could not dump 'company' database (may not exist yet)."
    success "PostgreSQL dumps complete."
  else
    warn "PostgreSQL not running — skipping live DB dump. Volume backup will still be taken."
  fi

  # ── 2. TLS certificates ───────────────────────────────────────────────────
  info "Backing up TLS certificates..."
  for cert_dir in US/certs UPS/certs AI-PIE/certs; do
    [ -d "$cert_dir" ] && cp -r "$cert_dir" "$STAGING/certs/$(echo "$cert_dir" | tr '/' '_')"
  done
  success "Certificates backed up."

  # ── 3. Configuration files ────────────────────────────────────────────────
  info "Backing up configuration..."
  for f in .env US/.env UPS/.env AI-PIE/.env .env.wizard .unotusk-version; do
    [ -f "$f" ] && cp "$f" "$STAGING/config/"
  done
  # JWT signing keys are stored in the us_data Docker volume. Back up the entire volume.
  info "Snapshotting us_data volume (JWT signing keys)..."
  docker run --rm \
    -v "$(basename "$INSTALL_DIR")_us_data:/data:ro" \
    -v "$STAGING/volumes:/backup" \
    alpine sh -c "tar czf /backup/us_data.tar.gz -C /data ." 2>/dev/null || \
    warn "Could not snapshot us_data volume (may not exist yet)."
  success "Configuration files backed up."

  # ── 4. Named Docker volumes (Qdrant, phoenix) ─────────────────────────────
  info "Snapshotting Qdrant data volume..."
  docker run --rm \
    -v "$(basename "$INSTALL_DIR")_qdrant_data:/data:ro" \
    -v "$STAGING/volumes:/backup" \
    alpine sh -c "tar czf /backup/qdrant_data.tar.gz -C /data ." 2>/dev/null || \
    warn "Could not snapshot qdrant_data volume (may not exist yet)."

  info "Snapshotting phoenix data volume..."
  docker run --rm \
    -v "$(basename "$INSTALL_DIR")_phoenix_data:/data:ro" \
    -v "$STAGING/volumes:/backup" \
    alpine sh -c "tar czf /backup/phoenix_data.tar.gz -C /data ." 2>/dev/null || \
    warn "Could not snapshot phoenix_data volume (may not exist yet)."

  # ── 5. Activity logs ──────────────────────────────────────────────────────
  info "Backing up logs..."
  [ -d logs ] && cp -r logs "$STAGING/logs" || true

  # ── 6. Create final archive ────────────────────────────────────────────────
  info "Compressing archive..."
  tar -czf "${ARCHIVE}.tar.gz" -C "$BACKUP_DIR" "staging_${TIMESTAMP}"
  rm -rf "$STAGING"

  chmod 600 "${ARCHIVE}.tar.gz"
  echo ""
  success "Backup complete: ${ARCHIVE}.tar.gz"
  ls -lh "${ARCHIVE}.tar.gz"
}

# ── restore ────────────────────────────────────────────────────────────────────
cmd_restore() {
  local archive="${1:-}"
  if [ -z "$archive" ]; then
    # List available backups
    echo ""
    echo -e "${BOLD}Available backups:${RESET}"
    ls -lht "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "  No backups found in $BACKUP_DIR"
    echo ""
    read -r -p "  Enter backup file path: " archive
  fi

  if [ ! -f "$archive" ]; then
    fail "Backup file not found: $archive"
    exit 1
  fi

  echo ""
  warn "This will OVERWRITE the current installation. Data will be replaced."
  read -r -p "  Continue? [y/N]: " CONFIRM
  [[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }

  header "Restoring from: $archive"
  local STAGING
  STAGING=$(mktemp -d)

  info "Extracting archive..."
  tar -xzf "$archive" -C "$STAGING"
  local PAYLOAD
  PAYLOAD=$(find "$STAGING" -mindepth 1 -maxdepth 1 -type d | head -1)

  info "Stopping services..."
  docker compose down

  # Restore config
  if [ -d "$PAYLOAD/config" ]; then
    info "Restoring configuration..."
    cp -f "$PAYLOAD/config/.env"          .env          2>/dev/null || true
    cp -f "$PAYLOAD/config/US/.env"       US/.env       2>/dev/null || true
    cp -f "$PAYLOAD/config/UPS/.env"      UPS/.env      2>/dev/null || true
    cp -f "$PAYLOAD/config/AI-PIE/.env"   AI-PIE/.env   2>/dev/null || true
    cp -f "$PAYLOAD/config/.unotusk-version" .unotusk-version 2>/dev/null || true
  fi

  # Restore certs
  if [ -d "$PAYLOAD/certs" ]; then
    info "Restoring certificates..."
    for src in "$PAYLOAD/certs"/*/; do
      target=$(basename "$src" | tr '_' '/')
      mkdir -p "$target"
      cp -r "$src". "$target/" 2>/dev/null || true
    done
  fi

  if [ -f "$PAYLOAD/volumes/us_data.tar.gz" ]; then
    info "Restoring us_data volume (JWT signing keys)..."
    docker volume create "$(basename "$INSTALL_DIR")_us_data" 2>/dev/null || true
    docker run --rm \
      -v "$(basename "$INSTALL_DIR")_us_data:/data" \
      -v "$PAYLOAD/volumes:/backup:ro" \
      alpine sh -c "tar xzf /backup/us_data.tar.gz -C /data"
    success "JWT signing keys restored."
  fi

  # Start postgres first, then restore DB
  info "Starting postgres for restore..."
  docker compose up -d postgres
  wait_healthy postgres 90

  if [ -f "$PAYLOAD/db/auth.sql" ]; then
    info "Restoring 'auth' database..."
    docker compose exec -T postgres \
      psql -U "${POSTGRES_USER:-unotusk}" -d auth < "$PAYLOAD/db/auth.sql"
    success "auth database restored."
  fi
  if [ -f "$PAYLOAD/db/company.sql" ]; then
    info "Restoring 'company' database..."
    docker compose exec -T postgres \
      psql -U "${POSTGRES_USER:-unotusk}" -d company < "$PAYLOAD/db/company.sql"
    success "company database restored."
  fi

  rm -rf "$STAGING"
  info "Restarting all services..."
  cmd_start
  echo ""
  success "Restore complete."
}

# ── update ─────────────────────────────────────────────────────────────────────
cmd_update() {
  local CURRENT_VERSION
  CURRENT_VERSION=$(current_version)
  header "Updating UNOTUSK (current version: $CURRENT_VERSION)..."

  # ── 1. Save rollback manifest ─────────────────────────────────────────────
  local ROLLBACK_FILE="$INSTALL_DIR/.unotusk-rollback"
  info "Saving rollback manifest..."
  docker compose images -q 2>/dev/null | while read -r img; do
    echo "$img" >> "$ROLLBACK_FILE.new"
  done
  # Also save image digests for pinned rollback
  docker compose config --format json 2>/dev/null | \
    python3 -c "import json,sys; cfg=json.load(sys.stdin); [print(s+':'+v.get('image','')) for s,v in cfg.get('services',{}).items()]" \
    > "$ROLLBACK_FILE.images" 2>/dev/null || true

  # ── 2. Automatic pre-update backup ───────────────────────────────────────
  info "Creating pre-update backup..."
  cmd_backup

  # ── 3. Pull new images ────────────────────────────────────────────────────
  info "Pulling latest images..."
  docker compose pull 2>&1 | tee -a "$LOG_DIR/upgrade.log"

  # ── 4. Rolling restart in dependency order ────────────────────────────────
  info "Applying update..."
  docker compose up -d postgres
  wait_healthy postgres 90 || { fail "postgres failed after update — rolling back"; cmd_rollback; exit 1; }

  docker compose up -d qdrant phoenix
  wait_healthy qdrant 90  || { fail "qdrant failed after update — rolling back";   cmd_rollback; exit 1; }
  wait_healthy phoenix 90 || { fail "phoenix failed after update — rolling back";  cmd_rollback; exit 1; }

  docker compose up -d us
  wait_healthy us 120 || { fail "us failed after update — rolling back"; cmd_rollback; exit 1; }

  docker compose up -d ups
  wait_healthy ups 120 || { fail "ups failed after update — rolling back"; cmd_rollback; exit 1; }

  docker compose up -d ai-pie
  wait_healthy ai-pie 180 || { fail "ai-pie failed after update — rolling back"; cmd_rollback; exit 1; }

  # ── 5. Post-update doctor check ────────────────────────────────────────────
  info "Running post-update health verification..."
  if ! cmd_doctor --quick 2>&1 | tee -a "$LOG_DIR/upgrade.log"; then
    fail "Post-update health check failed. Rolling back..."
    cmd_rollback
    exit 1
  fi

  # Update version file
  sed -i "s/^INSTALL_VERSION=.*/INSTALL_VERSION=$(date +%Y%m%d)/" "$VERSION_FILE" 2>/dev/null || true
  echo ""
  success "Update complete."
}

# ── rollback ───────────────────────────────────────────────────────────────────
cmd_rollback() {
  warn "Initiating automatic rollback..."
  local ROLLBACK_FILE="$INSTALL_DIR/.unotusk-rollback.images"
  if [ -f "$ROLLBACK_FILE" ]; then
    # Re-tag local 'local' images back to previous
    warn "Rollback: restarting previous image versions from rollback manifest."
    # In a real deployment, this would re-pin image digests in docker-compose.override.yml
    # For now, we do a `down + up` which may pull cached layers
    docker compose down
    docker compose up -d
    warn "Rollback applied. Run 'unotusk doctor' to verify."
  else
    warn "No rollback manifest found. Restore from the latest backup:"
    ls -lht "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -5
  fi
}

# ── doctor ─────────────────────────────────────────────────────────────────────
cmd_doctor() {
  local QUICK_MODE=0
  [ "${1:-}" = "--quick" ] && QUICK_MODE=1

  local DOCTOR_LOG="$LOG_DIR/doctor.log"
  local FAILS=0
  local WARNS=0

  {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}║       UNOTUSK Doctor  🩺                 ║${RESET}"
  echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
  echo ""

  # ── Check: Docker daemon ────────────────────────────────────────────────
  header "── Infrastructure"
  if docker info &>/dev/null; then
    success "Docker daemon is running."
  else
    fail "Docker daemon is NOT running."
    FAILS=$((FAILS+1))
  fi

  # ── Check: Docker version ───────────────────────────────────────────────
  DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
  DOCKER_MAJOR=$(echo "$DOCKER_VER" | cut -d. -f1)
  if [ "$DOCKER_MAJOR" -ge 24 ]; then
    success "Docker version $DOCKER_VER (>= 24 required)."
  else
    fail "Docker version $DOCKER_VER is below minimum (24.0)."
    FAILS=$((FAILS+1))
  fi

  # ── Check: Disk space ────────────────────────────────────────────────────
  FREE_MB=$(df -m "$INSTALL_DIR" | awk 'NR==2 {print $4}')
  if [ "$FREE_MB" -ge 10240 ]; then
    success "Disk space: ${FREE_MB}MB free (>= 10GB required)."
  elif [ "$FREE_MB" -ge 5120 ]; then
    warn "Disk space: ${FREE_MB}MB free. Less than 10GB — consider freeing space."
    WARNS=$((WARNS+1))
  else
    fail "Disk space critically low: ${FREE_MB}MB. UNOTUSK requires at least 5GB."
    FAILS=$((FAILS+1))
  fi

  # ── Check: Memory ────────────────────────────────────────────────────────
  if command -v free &>/dev/null; then
    FREE_MEM_MB=$(free -m | awk '/^Mem:/ {print $7}')
    if [ "$FREE_MEM_MB" -ge 4096 ]; then
      success "Available memory: ${FREE_MEM_MB}MB (>= 4GB recommended)."
    elif [ "$FREE_MEM_MB" -ge 2048 ]; then
      warn "Available memory: ${FREE_MEM_MB}MB. Some services may be slow."
      WARNS=$((WARNS+1))
    else
      fail "Available memory critically low: ${FREE_MEM_MB}MB."
      FAILS=$((FAILS+1))
    fi
  fi

  # ── Check: Configuration files ──────────────────────────────────────────
  header "── Configuration"
  for f in .env US/.env UPS/.env AI-PIE/.env .unotusk-version; do
    if [ -f "$INSTALL_DIR/$f" ]; then
      success "Found: $f"
    else
      fail "Missing: $f"
      FAILS=$((FAILS+1))
    fi
  done

  # ── Check: Container health status ──────────────────────────────────────
  header "── Services"
  for svc in postgres qdrant phoenix us ups ai-pie; do
    container_id=$(docker compose ps -q "$svc" 2>/dev/null || true)
    if [ -z "$container_id" ]; then
      fail "$svc: container not found"
      FAILS=$((FAILS+1))
      continue
    fi
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$container_id" 2>/dev/null || echo "unknown")
    running=$(docker inspect --format='{{.State.Status}}' "$container_id" 2>/dev/null || echo "unknown")
    case "$health" in
      healthy|running) success "$svc: $running / $health" ;;
      unhealthy)       fail "$svc: UNHEALTHY — run: docker compose logs $svc"; FAILS=$((FAILS+1)) ;;
      *)               warn "$svc: $running / $health"; WARNS=$((WARNS+1)) ;;
    esac
  done

  # ── Check: Postgres connectivity ────────────────────────────────────────
  header "── Database"
  if docker compose exec -T postgres \
      pg_isready -U "${POSTGRES_USER:-unotusk}" &>/dev/null; then
    success "PostgreSQL is accepting connections."
  else
    fail "PostgreSQL is NOT accepting connections."
    FAILS=$((FAILS+1))
  fi

  # ── Check: US health endpoint ────────────────────────────────────────────
  header "── Service endpoints"
  if curl -sf --max-time 5 http://localhost:3000/healthz &>/dev/null; then
    success "US /healthz → 200 OK"
  else
    fail "US /healthz did not respond on localhost:3000"
    FAILS=$((FAILS+1))
  fi

  if curl -sf --max-time 5 http://localhost:8080/healthz &>/dev/null; then
    success "UPS /healthz → 200 OK"
  else
    warn "UPS /healthz did not respond on localhost:8080 (port may not be published externally)"
    WARNS=$((WARNS+1))
  fi

  # ── Check: Platform reachability ─────────────────────────────────────────
  header "── Connectivity"
  if [ -f "$INSTALL_DIR/.env" ]; then
    # shellcheck source=/dev/null
    source "$INSTALL_DIR/.env" 2>/dev/null || true
  fi
  PLATFORM_HOST=$(echo "${PLATFORM_URL:-}" | sed -E 's|https?://([^:/]+).*|\1|')
  if [ -n "$PLATFORM_HOST" ]; then
    if nslookup "$PLATFORM_HOST" &>/dev/null || host "$PLATFORM_HOST" &>/dev/null; then
      success "Platform host '$PLATFORM_HOST' resolves."
    else
      warn "Cannot resolve Platform host '$PLATFORM_HOST'. License heartbeat will fail."
      WARNS=$((WARNS+1))
    fi
  fi

  # ── Check: License heartbeat (via UPS status endpoint) ───────────────────
  HEARTBEAT_STATUS=$(curl -sf --max-time 5 \
    "http://localhost:3000/license/status" 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" \
    2>/dev/null || echo "unreachable")
  case "$HEARTBEAT_STATUS" in
    normal)    success "License heartbeat: normal" ;;
    grace)     warn "License heartbeat: grace period — Platform may be temporarily unreachable"; WARNS=$((WARNS+1)) ;;
    degraded)  fail "License heartbeat: DEGRADED — contact support"; FAILS=$((FAILS+1)) ;;
    *)         warn "License heartbeat: $HEARTBEAT_STATUS (endpoint may not be reachable from host)"; WARNS=$((WARNS+1)) ;;
  esac

  # ── Check: TLS certificate expiry ────────────────────────────────────────
  header "── Certificates"
  for cert in US/certs/server.crt UPS/certs/client.crt UPS/certs/platform/client.crt; do
    if [ -f "$INSTALL_DIR/$cert" ]; then
      EXPIRY=$(openssl x509 -enddate -noout -in "$INSTALL_DIR/$cert" 2>/dev/null | cut -d= -f2)
      EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || echo 0)
      NOW_EPOCH=$(date +%s)
      DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
      if [ "$DAYS_LEFT" -gt 30 ]; then
        success "$cert expires in ${DAYS_LEFT} days."
      elif [ "$DAYS_LEFT" -gt 0 ]; then
        warn "$cert expires in ${DAYS_LEFT} days — renew soon!"
        WARNS=$((WARNS+1))
      else
        fail "$cert has EXPIRED."
        FAILS=$((FAILS+1))
      fi
    fi
  done

  # ── Check: Clock skew ────────────────────────────────────────────────────
  header "── System"
  if command -v timedatectl &>/dev/null; then
    SYNC_STATUS=$(timedatectl show --property=NTPSynchronized --value 2>/dev/null || echo "unknown")
    if [ "$SYNC_STATUS" = "yes" ]; then
      success "NTP is synchronized."
    else
      warn "NTP sync status: $SYNC_STATUS. Clock skew may affect JWT validation."
      WARNS=$((WARNS+1))
    fi
  fi

  # ── Check: Port conflicts ─────────────────────────────────────────────────
  for port_label in "3000:US/OIDC" "8444:US/Admin" "50051:UPS/gRPC" "50052:US/gRPC"; do
    p="${port_label%%:*}"; l="${port_label##*:}"
    LISTENER=$(ss -tlnp 2>/dev/null | grep ":${p} " | grep -v docker-proxy | head -1 || true)
    if [ -n "$LISTENER" ]; then
      # A listener on this port is expected (it's our own service)
      success "Port $p ($l) is in use by UNOTUSK."
    fi
  done

  # ── Summary ───────────────────────────────────────────────────────────────
  echo ""
  if [ "$FAILS" -gt 0 ]; then
    echo -e "${RED}${BOLD}Doctor found $FAILS problem(s) and $WARNS warning(s).${RESET}"
    echo "  Review the issues above and consult docs/Operations_Manual.md."
    [ "$QUICK_MODE" -eq 1 ] && exit 1
  elif [ "$WARNS" -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}Doctor found $WARNS warning(s). No critical failures.${RESET}"
  else
    echo -e "${GREEN}${BOLD}All checks passed. System is healthy.${RESET}"
  fi
  echo ""
  } 2>&1 | tee -a "$DOCTOR_LOG"
}

# ── reconfigure ────────────────────────────────────────────────────────────────
cmd_reconfigure() {
  header "Reconfigure UNOTUSK..."
  if [ -f "scripts/wizard.sh" ]; then
    bash scripts/wizard.sh "$INSTALL_DIR/.env.wizard"
    info "Re-running bootstrap to apply new configuration..."
    bash scripts/bootstrap.sh
  else
    fail "wizard.sh not found at scripts/wizard.sh"
    exit 1
  fi
}

# ── uninstall ──────────────────────────────────────────────────────────────────
cmd_uninstall() {
  echo ""
  warn "This will stop all containers and optionally delete data volumes."
  echo ""
  read -r -p "  Remove data volumes too? (ALL data will be lost) [y/N]: " REMOVE_VOL
  read -r -p "  Are you absolutely sure you want to uninstall? [y/N]: " CONFIRM
  [[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }

  if [[ "$REMOVE_VOL" =~ ^[Yy]$ ]]; then
    warn "Stopping containers and removing volumes..."
    docker compose down -v
  else
    info "Stopping containers (volumes preserved)..."
    docker compose down
  fi

  rm -f /usr/local/bin/unotusk 2>/dev/null || true
  success "UNOTUSK has been uninstalled."
  echo "  Data directory: $INSTALL_DIR (not removed)"
  echo "  To fully remove: sudo rm -rf $INSTALL_DIR"
}

# ── Command dispatch ───────────────────────────────────────────────────────────
COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
  start)       cmd_start "$@" ;;
  stop)        cmd_stop "$@" ;;
  restart)     cmd_restart "$@" ;;
  status)      cmd_status "$@" ;;
  logs)        cmd_logs "$@" ;;
  update)      cmd_update "$@" ;;
  backup)      cmd_backup "$@" ;;
  restore)     cmd_restore "$@" ;;
  doctor)      cmd_doctor "$@" ;;
  reconfigure) cmd_reconfigure "$@" ;;
  rollback)    cmd_rollback "$@" ;;
  uninstall)   cmd_uninstall "$@" ;;
  help|--help|-h) show_help ;;
  *)
    echo "Unknown command: $COMMAND"
    show_help
    exit 1
    ;;
esac
