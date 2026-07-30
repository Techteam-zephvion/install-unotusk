#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Offline Bundler — Package Builder Utility
# ==============================================================================
set -euo pipefail

# Sourcing colors and logging
INSTALLER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/colors.sh
source "$INSTALLER_ROOT/lib/colors.sh"
# shellcheck source=lib/logging.sh
source "$INSTALLER_ROOT/lib/logging.sh"

log_title "UNOTUSK Offline Bundle Packager"

# Check if docker is available
if ! command -v docker &>/dev/null; then
  log_fatal_err "Docker is required to pull and package images." "Install Docker on this builder machine." "https://docs.docker.com" "130"
fi

# Load manifest images
MANIFEST_FILE="$INSTALLER_ROOT/manifest.json"
if [ ! -f "$MANIFEST_FILE" ]; then
  log_fatal_err "Version manifest.json not found." "Check manifest existence." "https://docs.unotusk.com" "40"
fi

log_info "Reading manifest image tags..."
IMAGES=$(python3 -c "
import json
with open('$MANIFEST_FILE') as f:
    data = json.load(f)
    for img in data.get('images', {}).values():
        print(img)
" 2>/dev/null || echo "")

if [ -z "$IMAGES" ]; then
  log_fatal_err "No images discovered in manifest.json." "Ensure manifest images mapping is set." "https://docs.unotusk.com" "41"
fi

# Create target offline directory
OFFLINE_DIR="$INSTALLER_ROOT/offline"
mkdir -p "$OFFLINE_DIR"

log_info "Downloading images from registry..."
for img in $IMAGES; do
  log_info "Pulling: $img ..."
  docker pull "$img" >/dev/null
done

log_info "Serializing container layers to $OFFLINE_DIR/images.tar..."
# shellcheck disable=SC2086
docker save -o "$OFFLINE_DIR/images.tar" $IMAGES

log_info "Packaging all installer scripts and libraries..."
BUNDLE_FILE="$INSTALLER_ROOT/unotusk-offline-bundle.tar.gz"
tar -czf "$BUNDLE_FILE" -C "$INSTALLER_ROOT" \
  --exclude="offline/images.tar" \
  --exclude="unotusk-offline-bundle.tar.gz" \
  --exclude="backups" \
  --exclude="logs" \
  --exclude=".git" \
  . 

# Append images.tar to the final bundle file safely
log_info "Appending container archives to the bundle..."
tar -rf "$BUNDLE_FILE" -C "$INSTALLER_ROOT" offline/images.tar

log_success "Offline bundle created successfully: $BUNDLE_FILE"
ls -lh "$BUNDLE_FILE"
