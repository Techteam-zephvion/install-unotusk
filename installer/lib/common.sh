#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Common Bootstrap and Environment Library
# ==============================================================================

# Ensure standard path is set
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Root installer directory detection
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER_ROOT="$(dirname "$LIB_DIR")"

# Source colors, logging, plugin, and migration libraries immediately
# shellcheck source=lib/colors.sh
source "$LIB_DIR/colors.sh"
# shellcheck source=lib/logging.sh
source "$LIB_DIR/logging.sh"
# shellcheck source=lib/plugins.sh
source "$LIB_DIR/plugins.sh"
# shellcheck source=lib/migrations.sh
source "$LIB_DIR/migrations.sh"

# Define default paths for deployment
INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
CONFIG_DIR="$INSTALL_DIR"
ENV_FILE="$INSTALL_DIR/.env"
WIZARD_CONF="$INSTALL_DIR/.env.wizard"
SECRETS_FILE="$INSTALL_DIR/.secrets"
OAUTH_SECRET_FILE="$INSTALL_DIR/.oauth.secret"
LOG_DIR="$INSTALL_DIR/logs"
BACKUP_DIR="$INSTALL_DIR/backups"
VERSION_FILE="$INSTALL_DIR/.unotusk-version"
ROLLBACK_FILE="$INSTALL_DIR/.unotusk-rollback"

# Check if running as root
check_root() {
  if [ "$EUID" -ne 0 ]; then
    log_fatal_err \
      "Installer must be run as root or using sudo." \
      "Re-run command using 'sudo bash install.sh' or as root user." \
      "https://docs.unotusk.com/ops/installation#permissions" \
      "100"
  fi
  log_to_file_info "Running with root privileges check: PASSED"
}
