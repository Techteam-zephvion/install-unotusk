#!/usr/bin/env bash
set -euo pipefail

# Unotusk Release Packaging Script
# Packages Employee App and Server Setup App desktop bundles for distribution.

VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"

echo "=== Packaging Unotusk v${VERSION} Release Artifacts ==="
mkdir -p "${DIST_DIR}"

# 1. Package Employee Client
EMPLOYEE_BUNDLE="${ROOT_DIR}/app/build/linux/x64/release/bundle"
if [ -d "${EMPLOYEE_BUNDLE}" ]; then
  echo "--> Packaging Unotusk Employee App..."
  ARCHIVE_NAME="unotusk-client-linux-x64-v${VERSION}.tar.gz"
  tar -czf "${DIST_DIR}/${ARCHIVE_NAME}" -C "${EMPLOYEE_BUNDLE}" .
  echo "    Created: dist/${ARCHIVE_NAME}"
else
  echo "WARN: Employee App release bundle not found. Run 'flutter build linux --release' in app/"
fi

# 2. Package Server Setup App
SETUP_BUNDLE="${ROOT_DIR}/setup_app/build/linux/x64/release/bundle"
if [ -d "${SETUP_BUNDLE}" ]; then
  echo "--> Packaging Unotusk Server Setup App..."
  ARCHIVE_NAME="unotusk-server-setup-linux-x64-v${VERSION}.tar.gz"
  tar -czf "${DIST_DIR}/${ARCHIVE_NAME}" -C "${SETUP_BUNDLE}" .
  echo "    Created: dist/${ARCHIVE_NAME}"
else
  echo "WARN: Server Setup App release bundle not found. Run 'flutter build linux --release' in setup_app/"
fi

# 3. Generate SHA-256 Checksums
echo "--> Generating Checksums..."
cd "${DIST_DIR}"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum *.tar.gz > checksums.txt 2>/dev/null || true
  echo "    Generated: dist/checksums.txt"
fi

echo "=== Release Packaging Complete ==="
ls -lh "${DIST_DIR}"
