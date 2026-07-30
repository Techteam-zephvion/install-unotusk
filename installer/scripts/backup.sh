#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Wrapper — System Backup Script
# ==============================================================================
set -euo pipefail

# Delegate to the primary CLI utility
exec /usr/local/bin/unotusk backup "$@"
