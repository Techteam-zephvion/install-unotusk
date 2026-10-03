#!/bin/bash
set -euo pipefail

echo "================================================================"
echo " UNOTUSK MVP — OFFLINE SERVER SETUP"
echo "================================================================"

if ! command -v docker &> /dev/null; then
    echo "[!] Docker is not installed. Please install Docker first."
    exit 1
fi

echo "[1/2] Loading Docker Images from archive (this may take a few minutes)..."
docker load -i unotusk-images.tar

echo "[2/2] Starting Unotusk Server Stack..."
docker compose -f docker-compose.yml up -d

echo "================================================================"
echo " ✓ Server is running!"
echo " Access the Web Dashboard at: http://localhost:3000"
echo " Access the API at: http://localhost:8000"
echo "================================================================"
