#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Restore
#  Usage: unotusk restore /opt/unotusk/backups/unotusk-backup-manual-20260101-120000.tar.gz
# ==============================================================================
set -Eeuo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
LOG_FILE="/var/log/unotusk-install.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

_log()    { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE" 2>/dev/null || true; }
info()    { echo -e "  ${CYAN}→${RESET} $*"; _log "INFO $*"; }
success() { echo -e "  ${GREEN}✔${RESET} $*"; _log "OK   $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; _log "WARN $*"; }
fail()    { echo -e "  ${RED}✘${RESET} $*"; _log "FAIL $*"; exit 1; }

[[ "$EUID" -eq 0 ]] || fail "Run as root."
BACKUP_FILE="${1:-}"
[[ -z "$BACKUP_FILE" ]] && fail "Usage: unotusk restore <backup-file.tar.gz>"
[[ -f "$BACKUP_FILE" ]] || fail "Backup file not found: $BACKUP_FILE"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║         UNOTUSK Restore                  ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
warn "This will OVERWRITE current data with the backup contents."
echo "  Backup: $BACKUP_FILE"
echo ""
read -r -p "$(echo -e "  ${CYAN}?${RESET} Proceed with restore? [y/N]: ")" CONFIRM
[[ "${CONFIRM}" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }

# ── Verify checksum ───────────────────────────────────────────────────────────
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [[ -f "$CHECKSUM_FILE" ]]; then
  info "Verifying backup checksum..."
  EXPECTED=$(awk '{print $1}' "$CHECKSUM_FILE")
  ACTUAL=$(sha256sum "$BACKUP_FILE" | awk '{print $1}')
  [[ "$EXPECTED" == "$ACTUAL" ]] || fail "Checksum mismatch — backup may be corrupt."
  success "Checksum verified."
else
  warn "No checksum file found — proceeding without verification."
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

info "Extracting backup archive..."
tar -xzf "$BACKUP_FILE" -C "$TMP_DIR" >> "$LOG_FILE" 2>&1
success "Extracted."

# ── Stop services ─────────────────────────────────────────────────────────────
info "Stopping all services..."
docker compose \
  -f "${INSTALL_DIR}/compose/docker-compose.yml" \
  --env-file "${INSTALL_DIR}/.env" \
  down 2>>"$LOG_FILE" || warn "Could not stop services gracefully."
success "Services stopped."

# ── Restore config files ──────────────────────────────────────────────────────
info "Restoring configuration files..."
for f in .env .unotusk-version; do
  [[ -f "${TMP_DIR}/backup/${f}" ]] && cp "${TMP_DIR}/backup/${f}" "${INSTALL_DIR}/" && success "Restored: $f"
done

# Restore certs
if [[ -d "${TMP_DIR}/backup/certs" ]]; then
  [[ -d "${TMP_DIR}/backup/certs/US" ]] && \
    rsync -a "${TMP_DIR}/backup/certs/US/" "${INSTALL_DIR}/US/certs/" 2>/dev/null && success "US certs restored."
  [[ -d "${TMP_DIR}/backup/certs/UPS" ]] && \
    rsync -a "${TMP_DIR}/backup/certs/UPS/" "${INSTALL_DIR}/UPS/certs/" 2>/dev/null && success "UPS certs restored."
fi

# ── Restore database ──────────────────────────────────────────────────────────
if [[ -f "${TMP_DIR}/backup/postgres-dump.sql" ]]; then
  info "Starting PostgreSQL for restore..."
  docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    up -d postgres 2>>"$LOG_FILE"

  # Wait for postgres
  for i in $(seq 1 30); do
    docker compose -f "${INSTALL_DIR}/compose/docker-compose.yml" \
      --env-file "${INSTALL_DIR}/.env" \
      exec -T postgres pg_isready -U "${POSTGRES_USER:-unotusk}" >/dev/null 2>&1 && break
    sleep 2
  done

  info "Restoring PostgreSQL from dump..."
  # shellcheck source=/dev/null
  [[ -f "${INSTALL_DIR}/.env" ]] && source "${INSTALL_DIR}/.env"
  docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    exec -T postgres psql -U "${POSTGRES_USER:-unotusk}" \
    < "${TMP_DIR}/backup/postgres-dump.sql" >> "$LOG_FILE" 2>&1 \
    || fail "Database restore failed."
  success "PostgreSQL restored."
fi

# ── Restart all services ──────────────────────────────────────────────────────
info "Restarting services..."
bash "${INSTALL_DIR}/installer/install.sh" --install-dir "$INSTALL_DIR" --version \
  "$(grep '^INSTALL_VERSION=' "${INSTALL_DIR}/.unotusk-version" | cut -d= -f2 || echo dev)" \
  || warn "Full restart via installer failed — try: unotusk start"

echo ""
success "Restore complete."
echo ""
