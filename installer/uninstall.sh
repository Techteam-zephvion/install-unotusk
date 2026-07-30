#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Platform — Platform Uninstall Utility
# Usage: sudo ./uninstall.sh
# ==============================================================================
set -euo pipefail

# Sourcing libraries
INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
LIB_DIR="$INSTALL_DIR/lib"

if [ -d "$LIB_DIR" ]; then
  # shellcheck source=lib/common.sh
  source "$LIB_DIR/common.sh"
  # shellcheck source=lib/compose.sh
  source "$LIB_DIR/compose.sh"
  # shellcheck source=lib/services.sh
  source "$LIB_DIR/services.sh"
else
  # Local source context fallback
  SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SRC_DIR/lib/common.sh"
  # shellcheck source=lib/compose.sh
  source "$SRC_DIR/lib/compose.sh"
  # shellcheck source=lib/services.sh
  source "$SRC_DIR/lib/services.sh"
fi

main() {
  log_title "UNOTUSK Platform Uninstall Utility"

  # Privilege Check
  check_root

  local remove_volumes="false"

  # Read inputs
  if [ -z "${UNATTENDED:-}" ]; then
    echo ""
    log_warn "WARNING: This will stop all UNOTUSK services and remove integration links."
    read -r -p "  Do you want to purge all persistent database/volume data? [y/N]: " vol_choice
    if [[ "$vol_choice" =~ ^[Yy]$ ]]; then
      remove_volumes="true"
      log_warn "CRITICAL: All databases, caches, and vector store data will be deleted!"
    fi
    
    read -r -p "  Are you absolutely sure you want to uninstall UNOTUSK? [y/N]: " final_choice
    if [[ ! "$final_choice" =~ ^[Yy]$ ]]; then
      log_info "Uninstall aborted."
      exit 0
    fi
  else
    # Unattended default is safe (keep volumes)
    remove_volumes="${PURGE_VOLUMES:-false}"
  fi

  log_info "Stopping UNOTUSK container stack..."
  if [ "$remove_volumes" = "true" ]; then
    log_to_file_info "Uninstall: tearing down containers and deleting docker volumes."
    execute_compose down -v || true
  else
    log_to_file_info "Uninstall: tearing down containers (preserving volumes)."
    execute_compose down || true
  fi

  # ── Remove Systemd Service ──
  log_to_file_info "Uninstall" "Removing systemd service unit..."
  if [ -f "/etc/systemd/system/unotusk.service" ]; then
    systemctl stop unotusk.service 2>/dev/null || true
    systemctl disable unotusk.service 2>/dev/null || true
    rm -f "/etc/systemd/system/unotusk.service"
    systemctl daemon-reload
    log_success "Systemd service removed."
  fi

  # ── Remove CLI Binary ──
  log_to_file_info "Uninstall" "Removing CLI link..."
  if [ -f "/usr/local/bin/unotusk" ] || [ -L "/usr/local/bin/unotusk" ]; then
    rm -f "/usr/local/bin/unotusk"
    log_success "Global CLI link removed."
  fi

  log_success "UNOTUSK containers and services have been uninstalled."

  # Instruct operator on directory removal
  echo ""
  echo "  The installation directory '$INSTALL_DIR' has been preserved."
  echo "  To completely remove all remaining assets, execute:"
  echo "    sudo rm -rf $INSTALL_DIR"
  echo ""
  log_to_file_info "Uninstall" "Uninstall execution complete."
}

main "$@"
