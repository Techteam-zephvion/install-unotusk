#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
STAGE_DIR="${DIST_DIR}/unotusk-server"

echo "================================================================"
echo " UNOTUSK MVP — OFFLINE BUNDLE PACKAGER"
echo "================================================================"

mkdir -p "${STAGE_DIR}"

echo "[1/4] Building Custom Docker Images..."
cd "${ROOT_DIR}"
# Build the images and tag them explicitly so they can be bundled
docker build -t unotusk/api:latest -f infrastructure/docker/Dockerfile.api .
docker build -t unotusk/worker:latest -f infrastructure/docker/Dockerfile.worker .
docker build -t unotusk/web:latest -f infrastructure/docker/Dockerfile.web .

echo "[2/4] Pulling Public Docker Images..."
docker pull pgvector/pgvector:pg16
docker pull redis:7-alpine

echo "[3/4] Exporting all images to a single archive (this takes time)..."
docker save -o "${STAGE_DIR}/unotusk-images.tar" \
    unotusk/api:latest \
    unotusk/worker:latest \
    unotusk/web:latest \
    pgvector/pgvector:pg16 \
    redis:7-alpine

echo "[4/4] Preparing offline compose and scripts..."
# Copy the start script
cp "${SCRIPT_DIR}/templates/start_offline_server.sh" "${STAGE_DIR}/start.sh"
chmod +x "${STAGE_DIR}/start.sh"

# Create a modified docker-compose.yml that uses pre-built images instead of build contexts
cat docker-compose.yml | \
    sed '/build:/,+2d' | \
    sed 's/container_name: unotusk-migration/image: unotusk\/api:latest\n    container_name: unotusk-migration/g' | \
    sed 's/container_name: unotusk-api/image: unotusk\/api:latest\n    container_name: unotusk-api/g' | \
    sed 's/container_name: unotusk-worker/image: unotusk\/worker:latest\n    container_name: unotusk-worker/g' | \
    sed 's/container_name: unotusk-web/image: unotusk\/web:latest\n    container_name: unotusk-web/g' \
    > "${STAGE_DIR}/docker-compose.yml"

# Remove volume mount for api folder in the offline bundle so it uses baked-in code
sed -i '/volumes:/,+1d' "${STAGE_DIR}/docker-compose.yml"

echo "Compressing the final bundle..."
cd "${DIST_DIR}"
tar -czf unotusk-server-offline-bundle.tar.gz unotusk-server/
rm -rf "${STAGE_DIR}"

echo "================================================================"
echo " ✓ Offline bundle created: ${DIST_DIR}/unotusk-server-offline-bundle.tar.gz"
echo " (Host this file on a secure cloud storage and link it on install.unotusk.com)"
echo "================================================================"
