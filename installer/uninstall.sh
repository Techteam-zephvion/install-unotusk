#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Uninstaller
#  Usage: unotusk uninstall
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

[[ "$EUID" -eq 0 ]] || fail "Run as root (sudo unotusk uninstall)."

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║         UNOTUSK Uninstaller              ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
warn "This will stop and remove all UNOTUSK containers and images."
warn "Your DATA VOLUMES will be preserved unless you explicitly confirm deletion."
echo ""
read -r -p "$(echo -e "  ${CYAN}?${RESET} Continue with uninstall? [y/N]: ")" CONFIRM
[[ "${CONFIRM}" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }

# ── Step 1: Stop services ──────────────────────────────────────────────────────
info "Stopping all UNOTUSK services..."
if [[ -d "$INSTALL_DIR" ]]; then
  docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    down --remove-orphans 2>>"$LOG_FILE" || warn "docker compose down failed — containers may already be stopped."
  success "Services stopped."
else
  warn "Installation directory not found — skipping compose down."
fi

# ── Step 2: Remove CLI ─────────────────────────────────────────────────────────
if [[ -L /usr/local/bin/unotusk ]] || [[ -f /usr/local/bin/unotusk ]]; then
  rm -f /usr/local/bin/unotusk
  success "CLI removed from /usr/local/bin/unotusk"
fi

# ── Step 3: Data volumes — ask explicitly ─────────────────────────────────────
echo ""
warn "DATA VOLUMES contain your database and service state."
echo ""
read -r -p "$(echo -e "  ${CYAN}?${RESET} DELETE data volumes? This CANNOT be undone. [y/N]: ")" DEL_VOLUMES
if [[ "${DEL_VOLUMES}" =~ ^[Yy]$ ]]; then
  read -r -p "$(echo -e "  ${RED}!${RESET} Type 'DELETE' to confirm: ")" DOUBLE_CONFIRM
  if [[ "$DOUBLE_CONFIRM" == "DELETE" ]]; then
    docker compose \
      -f "${INSTALL_DIR}/compose/docker-compose.yml" \
      --env-file "${INSTALL_DIR}/.env" \
      down -v 2>>"$LOG_FILE" || true
    success "Data volumes deleted."
  else
    warn "Confirmation did not match. Volumes preserved."
  fi
else
  success "Data volumes preserved."
  info "Re-attach volumes anytime by reinstalling into the same directory."
fi

# ── Step 4: Remove installation directory ─────────────────────────────────────
echo ""
read -r -p "$(echo -e "  ${CYAN}?${RESET} Remove installation directory $INSTALL_DIR? [y/N]: ")" DEL_DIR
if [[ "${DEL_DIR}" =~ ^[Yy]$ ]]; then
  rm -rf "$INSTALL_DIR"
  success "Installation directory removed."
else
  success "Installation directory preserved at $INSTALL_DIR"
fi

echo ""
success "UNOTUSK has been uninstalled."
echo ""
