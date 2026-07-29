#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Rollback
#  Usage: unotusk rollback [backup-file]
#  Rolls back to the most recent pre-update backup if no file is specified.
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

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║         UNOTUSK Rollback                 ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

BACKUP_FILE="${1:-}"

if [[ -z "$BACKUP_FILE" ]]; then
  # Auto-detect most recent pre-update backup
  BACKUP_FILE=$(find "$BACKUP_DIR" -name "unotusk-backup-pre-update-*.tar.gz" \
    -printf '%T+ %p\n' 2>/dev/null | sort -r | head -1 | awk '{print $2}' || true)

  if [[ -z "$BACKUP_FILE" ]]; then
    # Fall back to most recent any backup
    BACKUP_FILE=$(find "$BACKUP_DIR" -name "*.tar.gz" \
      -printf '%T+ %p\n' 2>/dev/null | sort -r | head -1 | awk '{print $2}' || true)
  fi

  [[ -z "$BACKUP_FILE" ]] && fail "No backups found in $BACKUP_DIR. Cannot rollback."
  info "Auto-selected backup: $(basename "$BACKUP_FILE")"
fi

[[ -f "$BACKUP_FILE" ]] || fail "Backup file not found: $BACKUP_FILE"

warn "Rollback will restore the selected backup and restart all services."
echo "  Backup: $BACKUP_FILE"
echo ""
read -r -p "$(echo -e "  ${CYAN}?${RESET} Proceed with rollback? [y/N]: ")" CONFIRM
[[ "${CONFIRM}" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }

# Delegate to restore script
RESTORE_SCRIPT="${INSTALL_DIR}/installer/restore.sh"
if [[ -f "$RESTORE_SCRIPT" ]]; then
  exec bash "$RESTORE_SCRIPT" "$BACKUP_FILE"
else
  fail "Restore script not found at $RESTORE_SCRIPT"
fi
