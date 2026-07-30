#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Wrapper — Database Migrations Script
# ==============================================================================
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"

# Source the main common bootstrap library
# shellcheck source=lib/common.sh
source "$INSTALL_DIR/lib/common.sh"

# Run schema migrations
execute_database_migrations
