#!/usr/bin/env bash
# scripts/verify_lan_connectivity.sh
# Executable wrapper for LAN connectivity verification probe.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if [ -f ".venv/bin/python3" ]; then
    PYTHON_BIN=".venv/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "[ERROR] python3 not found."
    exit 1
fi

exec "${PYTHON_BIN}" "${SCRIPT_DIR}/verify_lan_connectivity.py" "$@"
