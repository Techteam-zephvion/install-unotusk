#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Updater
#  Usage: unotusk update [--version v1.2.0]
# ==============================================================================
set -Eeuo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
LOG_FILE="/var/log/unotusk-install.log"
GITHUB_ORG="unotusk"
GITHUB_REPO="install"
BACKUP_BEFORE_UPDATE=true

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

_log()    { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE" 2>/dev/null || true; }
info()    { echo -e "  ${CYAN}→${RESET} $*"; _log "INFO $*"; }
success() { echo -e "  ${GREEN}✔${RESET} $*"; _log "OK   $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; _log "WARN $*"; }
fail()    { echo -e "  ${RED}✘${RESET} $*"; _log "FAIL $*"; exit 1; }
header()  { echo -e "\n${BOLD}━━  $*${RESET}"; _log "=== $* ==="; }

[[ "$EUID" -eq 0 ]] || fail "Run as root (sudo unotusk update)."
[[ -d "$INSTALL_DIR" ]] || fail "UNOTUSK installation not found at $INSTALL_DIR"

TARGET_VERSION="${1:-}"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║          UNOTUSK Updater                 ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Resolve current and target versions ───────────────────────────────────────
VERSION_FILE="${INSTALL_DIR}/.unotusk-version"
CURRENT_VERSION="unknown"
[[ -f "$VERSION_FILE" ]] && CURRENT_VERSION=$(grep '^INSTALL_VERSION=' "$VERSION_FILE" | cut -d= -f2 || echo "unknown")
info "Current version: $CURRENT_VERSION"

if [[ -z "$TARGET_VERSION" ]]; then
  TARGET_VERSION=$(curl -fsSL \
    "https://api.github.com/repos/${GITHUB_ORG}/${GITHUB_REPO}/releases/latest" \
    | grep '"tag_name"' | head -1 | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
  [[ -z "$TARGET_VERSION" ]] && fail "Could not resolve latest version from GitHub."
fi
info "Target version:  $TARGET_VERSION"

if [[ "$CURRENT_VERSION" == "$TARGET_VERSION" ]]; then
  success "Already on $TARGET_VERSION — nothing to do."
  exit 0
fi

echo ""
read -r -p "$(echo -e "  ${CYAN}?${RESET} Update $CURRENT_VERSION → $TARGET_VERSION? [Y/n]: ")" CONFIRM
[[ "${CONFIRM:-Y}" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }

# ── Step 1: Pre-update backup ──────────────────────────────────────────────────
if [[ "$BACKUP_BEFORE_UPDATE" == "true" ]]; then
  header "[1/4] Creating pre-update backup"
  BACKUP_SCRIPT="${INSTALL_DIR}/installer/backup.sh"
  if [[ -f "$BACKUP_SCRIPT" ]]; then
    bash "$BACKUP_SCRIPT" --label "pre-update-${TARGET_VERSION}" \
      || warn "Backup failed — continuing update. Rollback may be unavailable."
  else
    warn "Backup script not found — skipping pre-update backup."
  fi
fi

# ── Step 2: Download new installer ────────────────────────────────────────────
header "[2/4] Downloading installer $TARGET_VERSION"
BASE_URL="https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/releases/download/${TARGET_VERSION}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL "${BASE_URL}/unotusk-installer.tar.gz" -o "${TMP_DIR}/installer.tar.gz" \
  || fail "Download failed."

EXPECTED=$(curl -fsSL "${BASE_URL}/unotusk-installer.tar.gz.sha256" | awk '{print $1}')
ACTUAL=$(sha256sum "${TMP_DIR}/installer.tar.gz" | awk '{print $1}')
[[ "$EXPECTED" == "$ACTUAL" ]] || fail "Checksum mismatch. Update aborted for security."
success "Checksum verified."

tar -xzf "${TMP_DIR}/installer.tar.gz" -C "$TMP_DIR" >> "$LOG_FILE" 2>&1
success "New installer extracted."

# ── Step 3: Pull new images ───────────────────────────────────────────────────
header "[3/4] Pulling updated Docker images"
docker compose \
  -f "${INSTALL_DIR}/compose/docker-compose.yml" \
  --env-file "${INSTALL_DIR}/.env" \
  pull --quiet 2>&1 | grep -v "^$" | sed 's/^/  /' || true
success "Images pulled."

# ── Step 4: Rolling restart ───────────────────────────────────────────────────
header "[4/4] Restarting services"
_compose() {
  docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    "$@"
}

wait_healthy() {
  local service="$1" timeout="${2:-120}" elapsed=0 interval=5 cid
  cid=$(_compose ps -q "$service" 2>/dev/null || true)
  [[ -z "$cid" ]] && { warn "No container for $service"; return 1; }
  while [[ $elapsed -lt $timeout ]]; do
    local status
    status=$(docker inspect \
      --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' \
      "$cid" 2>/dev/null || echo unknown)
    case "$status" in
      healthy|running) success "$service healthy"; return 0 ;;
      unhealthy) fail "$service unhealthy after update. Rollback: unotusk rollback" ;;
      *) sleep $interval; elapsed=$((elapsed + interval)) ;;
    esac
  done
  fail "$service did not become healthy. Rollback: unotusk rollback"
}

_compose up -d --remove-orphans postgres && wait_healthy postgres 90
_compose up -d qdrant phoenix && wait_healthy qdrant 90 && wait_healthy phoenix 90
_compose up -d us && wait_healthy us 120
_compose up -d ups && wait_healthy ups 120
_compose up -d ai-pie && wait_healthy ai-pie 180

# Record new version
sed -i "s/^INSTALL_VERSION=.*/INSTALL_VERSION=${TARGET_VERSION}/" "$VERSION_FILE"
echo "LAST_UPDATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$VERSION_FILE"

echo ""
success "UNOTUSK updated to ${TARGET_VERSION}."
echo ""
