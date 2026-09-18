#!/usr/bin/env bash
# scripts/package_release.sh
# Packages release artifacts for Unotusk MVP LAN Pilot Distribution.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"

mkdir -p "${DIST_DIR}"

echo "================================================================"
echo " UNOTUSK MVP — RELEASE PACKAGING UTILITY"
echo "================================================================"

# Package Linux Employee Client
LINUX_BUNDLE="${ROOT_DIR}/app/build/linux/x64/release/bundle"
if [ -d "${LINUX_BUNDLE}" ]; then
    echo "[1/3] Packaging Linux Employee Client..."
    LINUX_ARCHIVE="${DIST_DIR}/unotusk-employee-linux-x64.tar.gz"
    tar -czf "${LINUX_ARCHIVE}" -C "${ROOT_DIR}/app/build/linux/x64/release" bundle
    sha256sum "${LINUX_ARCHIVE}" | awk '{print $1}' > "${LINUX_ARCHIVE}.sha256"
    echo "  ✓ Linux Archive: ${LINUX_ARCHIVE}"
    echo "  ✓ SHA256: $(cat "${LINUX_ARCHIVE}.sha256")"
else
    echo "[!] Linux release bundle not built yet. Run: (cd app && flutter build linux --release)"
fi

# Summary of packages
echo ""
echo "================================================================"
echo " RELEASE DISTRIBUTION DIRECTORY: ${DIST_DIR}"
echo "================================================================"
ls -lh "${DIST_DIR}" || true
echo "================================================================"
