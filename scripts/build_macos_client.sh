#!/usr/bin/env bash
# scripts/build_macos_client.sh
# Unotusk MVP Employee Client — macOS Build & Packaging Script
# Target: macOS 12+ (Apple Silicon & Intel x64)

set -euo pipefail

echo "================================================================"
echo " UNOTUSK EMPLOYEE CLIENT — MACOS RELEASE BUILD"
echo "================================================================"

# 1. Verify Host OS
if [ "$(uname -s)" != "Darwin" ]; then
    echo "[ERROR] This build script must be executed on a macOS host with Xcode installed."
    echo "Current OS: $(uname -s)"
    echo "Cross-compiling macOS desktop binaries from Linux is not supported by the Flutter toolchain."
    exit 1
fi

# 2. Verify Prerequisites
if ! command -v flutter >/dev/null 2>&1; then
    echo "[ERROR] Flutter SDK not found in PATH."
    exit 1
fi

if ! xcode-select -p >/dev/null 2>&1; then
    echo "[ERROR] Xcode Command Line Tools not found. Run: xcode-select --install"
    exit 1
fi

if ! command -v pod >/dev/null 2>&1; then
    echo "[ERROR] CocoaPods not found. Install with: sudo gem install cocoapods"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}/app"

echo "[1/4] Running flutter pub get..."
flutter pub get

echo "[2/4] Building macOS Release bundle..."
flutter build macos --release

APP_BUNDLE="${ROOT_DIR}/app/build/macos/Build/Products/Release/app.app"
if [ ! -d "${APP_BUNDLE}" ]; then
    # Search for any .app in Release directory
    APP_BUNDLE=$(find "${ROOT_DIR}/app/build/macos/Build/Products/Release" -maxdepth 1 -name "*.app" | head -n 1)
fi

if [ -z "${APP_BUNDLE}" ] || [ ! -d "${APP_BUNDLE}" ]; then
    echo "[ERROR] Could not find built .app bundle in Release folder."
    exit 1
fi

echo "[3/4] Packaging .app bundle into dist/..."
DIST_DIR="${ROOT_DIR}/dist"
mkdir -p "${DIST_DIR}"

APP_NAME="$(basename "${APP_BUNDLE}")"
ARCHIVE_OUT="${DIST_DIR}/unotusk-employee-macos.tar.gz"

cd "$(dirname "${APP_BUNDLE}")"
tar -czf "${ARCHIVE_OUT}" "${APP_NAME}"

echo "[4/4] Computing SHA256 checksum..."
CHECKSUM_FILE="${ARCHIVE_OUT}.sha256"
shasum -a 256 "${ARCHIVE_OUT}" | awk '{print $1}' > "${CHECKSUM_FILE}"

echo "================================================================"
echo " BUILD SUCCESSFUL: macOS Employee Client"
echo "================================================================"
echo " Archive:  ${ARCHIVE_OUT}"
echo " Checksum: ${CHECKSUM_FILE} ($(cat "${CHECKSUM_FILE}"))"
echo ""
echo " PILOT RUNTIME NOTES:"
echo " 1. Copy ${ARCHIVE_OUT} to the employee macOS laptop."
echo " 2. Extract: tar -xzf unotusk-employee-macos.tar.gz"
echo " 3. Move ${APP_NAME} to /Applications/"
echo " 4. Gatekeeper clearance for unsigned pilot builds:"
echo "    Option A: In Terminal run: xattr -cr /Applications/${APP_NAME}"
echo "    Option B: Right-click ${APP_NAME} -> Select Open -> Click Open"
echo " 5. In the app, enter the Linux Server LAN address: http://<SERVER_LAN_IP>:8000"
echo "================================================================"
