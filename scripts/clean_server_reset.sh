#!/usr/bin/env bash
set -euo pipefail

# Unotusk Server Clean Reset Shell Wrapper
# Usage: ./scripts/clean_server_reset.sh [--preserve-data | --wipe-data | --all] [--dry-run] [-y]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Use project .venv python if available, else system python3
if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "ERROR: Python 3 is required to run clean_server_reset.py" >&2
    exit 1
fi

chmod +x "${SCRIPT_DIR}/clean_server_reset.py"
exec "${PYTHON_BIN}" "${SCRIPT_DIR}/clean_server_reset.py" "$@"
