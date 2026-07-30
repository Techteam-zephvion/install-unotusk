#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK CLI — Platform Lifecycle Management Wrapper
# Usage: unotusk <command> [options]
# ==============================================================================
set -euo pipefail

# Locate the installation folder
INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"

# Source common libraries
# shellcheck source=lib/common.sh
source "$INSTALL_DIR/lib/common.sh"
# shellcheck source=lib/compose.sh
source "$INSTALL_DIR/lib/compose.sh"
# shellcheck source=lib/validation.sh
source "$INSTALL_DIR/lib/validation.sh"
# shellcheck source=lib/filesystem.sh
source "$INSTALL_DIR/lib/filesystem.sh"
# shellcheck source=lib/network.sh
source "$INSTALL_DIR/lib/network.sh"
# shellcheck source=lib/docker.sh
source "$INSTALL_DIR/lib/docker.sh"
# shellcheck source=lib/configuration.sh
source "$INSTALL_DIR/lib/configuration.sh"
# shellcheck source=lib/certificates.sh
source "$INSTALL_DIR/lib/certificates.sh"
# shellcheck source=lib/registration.sh
source "$INSTALL_DIR/lib/registration.sh"
# shellcheck source=lib/health.sh
source "$INSTALL_DIR/lib/health.sh"
# shellcheck source=lib/services.sh
source "$INSTALL_DIR/lib/services.sh"
# shellcheck source=lib/backup.sh
source "$INSTALL_DIR/lib/backup.sh"
# shellcheck source=lib/restore.sh
source "$INSTALL_DIR/lib/restore.sh"
# shellcheck source=lib/rollback.sh
source "$INSTALL_DIR/lib/rollback.sh"
# shellcheck source=lib/cli.sh
source "$INSTALL_DIR/lib/cli.sh"

# Ensure we dispatch commands as root
check_root

# Dispatch CLI actions
dispatch_cli_command "$@"
