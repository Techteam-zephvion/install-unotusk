#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Backup
#  Usage: unotusk backup [--label my-label]
# ==============================================================================
set -Eeuo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
BACKUP_DIR="${INSTALL_DIR}/backups"
LOG_FILE="/var/log/unotusk-install.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

_log()    { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE" 2>/dev/null || true; }
info()    { echo -e "  ${CYAN}→${RESET} $*"; _log "INFO $*"; }
success() { echo -e "  ${GREEN}✔${RESET} $*"; _log "OK   $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; _log "WARN $*"; }
fail()    { echo -e "  ${RED}✘${RESET} $*"; _log "FAIL $*"; exit 1; }

[[ "$EUID" -eq 0 ]] || fail "Run as root."

LABEL="manual"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label) LABEL="$2"; shift 2 ;;
    *) shift ;;
  esac
done

TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
BACKUP_NAME="unotusk-backup-${LABEL}-${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║         UNOTUSK Backup                   ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
info "Creating backup: $BACKUP_NAME"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "${TMP_DIR}/backup"

# ── 1. Postgres dump ──────────────────────────────────────────────────────────
info "Dumping PostgreSQL databases..."
if [[ -f "${INSTALL_DIR}/.env" ]]; then
  # shellcheck source=/dev/null
  source "${INSTALL_DIR}/.env"
fi
POSTGRES_USER="${POSTGRES_USER:-unotusk}"

docker compose \
  -f "${INSTALL_DIR}/compose/docker-compose.yml" \
  --env-file "${INSTALL_DIR}/.env" \
  exec -T postgres pg_dumpall -U "$POSTGRES_USER" \
  > "${TMP_DIR}/backup/postgres-dump.sql" 2>>"$LOG_FILE" \
  || fail "PostgreSQL dump failed."
success "PostgreSQL dumped."

# ── 2. Environment files ──────────────────────────────────────────────────────
info "Backing up configuration files..."
for f in .env .unotusk-version .install-state; do
  [[ -f "${INSTALL_DIR}/${f}" ]] && cp "${INSTALL_DIR}/${f}" "${TMP_DIR}/backup/"
done
mkdir -p "${TMP_DIR}/backup/certs"
[[ -d "${INSTALL_DIR}/US/certs" ]] && cp -r "${INSTALL_DIR}/US/certs" "${TMP_DIR}/backup/certs/US" 2>/dev/null || true
[[ -d "${INSTALL_DIR}/UPS/certs" ]] && cp -r "${INSTALL_DIR}/UPS/certs" "${TMP_DIR}/backup/certs/UPS" 2>/dev/null || true
success "Configuration files backed up."

# ── 3. Create archive ─────────────────────────────────────────────────────────
info "Compressing backup archive..."
tar -czf "$BACKUP_PATH" -C "$TMP_DIR" backup >> "$LOG_FILE" 2>&1
BACKUP_SIZE=$(du -sh "$BACKUP_PATH" | cut -f1)

# Write checksum
sha256sum "$BACKUP_PATH" > "${BACKUP_PATH}.sha256"
success "Backup created: $BACKUP_PATH ($BACKUP_SIZE)"

# ── 4. Rotate old backups (keep last 10) ─────────────────────────────────────
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "*.tar.gz" | wc -l)
if [[ $BACKUP_COUNT -gt 10 ]]; then
  info "Rotating old backups (keeping 10 most recent)..."
  find "$BACKUP_DIR" -name "*.tar.gz" -printf '%T+ %p\n' \
    | sort | head -n $((BACKUP_COUNT - 10)) | awk '{print $2}' \
    | xargs rm -f
  success "Old backups rotated."
fi

echo ""
success "Backup complete."
echo "  Path: $BACKUP_PATH"
echo "  SHA256: $(cat "${BACKUP_PATH}.sha256" | awk '{print $1}')"
echo ""
