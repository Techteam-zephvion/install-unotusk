#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Platform — Main Rollback Entrypoint
# Usage: sudo ./rollback.sh
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
  # shellcheck source=lib/restore.sh
  source "$LIB_DIR/restore.sh"
  # shellcheck source=lib/health.sh
  source "$LIB_DIR/health.sh"
  # shellcheck source=lib/rollback.sh
  source "$LIB_DIR/rollback.sh"
else
  # Local source context fallback
  SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SRC_DIR/lib/common.sh"
  # shellcheck source=lib/compose.sh
  source "$SRC_DIR/lib/compose.sh"
  # shellcheck source=lib/services.sh
  source "$SRC_DIR/lib/services.sh"
  # shellcheck source=lib/restore.sh
  source "$SRC_DIR/lib/restore.sh"
  # shellcheck source=lib/health.sh
  source "$SRC_DIR/lib/health.sh"
  # shellcheck source=lib/rollback.sh
  source "$SRC_DIR/lib/rollback.sh"
fi

log_title "UNOTUSK Platform Rollback Utility"

# Privilege Check
check_root

# Trigger rollback sequence
trigger_rollback
