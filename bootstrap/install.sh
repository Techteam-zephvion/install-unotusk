#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Bootstrap Script
#  Served at: https://install.unotusk.com
#  Usage:     curl -fsSL https://install.unotusk.com | bash
#
#  This script ONLY:
#    1. Verifies OS (Ubuntu 24.04 / Debian 12+) and architecture
#    2. Checks internet connectivity
#    3. Installs Docker Engine if missing
#    4. Installs Docker Compose plugin if missing
#    5. Creates /opt/unotusk
#    6. Downloads the latest versioned installer tarball from GitHub Releases
#    7. Verifies its SHA-256 checksum
#    8. Extracts and executes the real installer
#
#  The full installation logic lives in the versioned installer package,
#  never in this bootstrap script.
# ==============================================================================
set -Eeuo pipefail

# ── Constants ──────────────────────────────────────────────────────────────────
GITHUB_ORG="unotusk"
GITHUB_REPO="install"
INSTALL_DIR="/opt/unotusk"
LOG_FILE="/var/log/unotusk-install.log"
INSTALLER_BINARY="unotusk-installer.tar.gz"
MIN_DOCKER_VERSION=24
SUPPORTED_ARCHES=("x86_64" "aarch64")

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

log()     { { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE"; } 2>/dev/null || true; }
info()    { local m="  ${CYAN}→${RESET} $*"; echo -e "$m"; log "$m"; }
success() { local m="  ${GREEN}✔${RESET} $*"; echo -e "$m"; log "$m"; }
warn()    { local m="  ${YELLOW}⚠${RESET} $*"; echo -e "$m"; log "$m"; }
fail()    { local m="  ${RED}✘${RESET} $*  (see $LOG_FILE)"; echo -e "$m"; log "$m"; exit 1; }
header()  { echo -e "\n${BOLD}$*${RESET}"; log "=== $* ==="; }

# ── Banner ─────────────────────────────────────────────────────────────────────
mkdir -p "$(dirname "$LOG_FILE")" && touch "$LOG_FILE" 2>/dev/null || true
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       UNOTUSK Platform Installer         ║${RESET}"
echo -e "${BOLD}║      install.unotusk.com  •  v1          ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Root check ─────────────────────────────────────────────────────────────────
if [[ "$EUID" -ne 0 ]]; then
  echo -e "  ${RED}✘${RESET}  Run as root:"
  echo ""
  echo "      curl -fsSL https://install.unotusk.com | sudo bash"
  echo ""
  exit 1
fi
success "Running as root."

# ── OS detection ───────────────────────────────────────────────────────────────
header "[1/6] Checking operating system..."
if [[ ! -f /etc/os-release ]]; then
  fail "Cannot detect OS — /etc/os-release not found."
fi

source /etc/os-release
DISTRO="${ID:-unknown}"
DISTRO_VER="${VERSION_ID:-0}"
DISTRO_MAJOR="${DISTRO_VER%%.*}"
ID_LIKE_LIST="${ID_LIKE:-}"   # e.g. "ubuntu" on Pop!_OS, "ubuntu debian" on Mint

# Resolve effective upstream distro from ID_LIKE when ID is a derivative
resolve_distro() {
  local id="$1" like="$2"
  case "$id" in
    ubuntu|debian) echo "$id"; return ;;
  esac
  # Walk ID_LIKE list — first match wins
  for token in $like; do
    case "$token" in
      ubuntu) echo "ubuntu"; return ;;
      debian) echo "debian"; return ;;
    esac
  done
  echo "$id"   # unknown / unsupported
}

EFFECTIVE_DISTRO=$(resolve_distro "$DISTRO" "$ID_LIKE_LIST")

case "$EFFECTIVE_DISTRO" in
  ubuntu)
    if [[ "$DISTRO_MAJOR" -lt 22 ]]; then
      fail "${PRETTY_NAME:-$DISTRO} is not supported. Requires Ubuntu 22.04+."
    fi
    success "OS: ${PRETTY_NAME:-Ubuntu ${DISTRO_VER}} (Ubuntu-compatible)"
    ;;
  debian)
    if [[ "$DISTRO_MAJOR" -lt 11 ]]; then
      fail "${PRETTY_NAME:-$DISTRO} is not supported. Requires Debian 11+."
    fi
    success "OS: ${PRETTY_NAME:-Debian ${DISTRO_VER}} (Debian-compatible)"
    ;;
  *)
    fail "Unsupported OS: ${PRETTY_NAME:-$DISTRO}. UNOTUSK requires Ubuntu 22.04+/24.04 or Debian 11+ (or a derivative)."
    ;;
esac

# ── Architecture check ─────────────────────────────────────────────────────────
ARCH=$(uname -m)
ARCH_OK=false
for a in "${SUPPORTED_ARCHES[@]}"; do
  [[ "$ARCH" == "$a" ]] && ARCH_OK=true && break
done
$ARCH_OK || fail "Unsupported architecture: $ARCH. Supported: ${SUPPORTED_ARCHES[*]}."
success "Architecture: $ARCH"

# Map to Docker's arch naming
[[ "$ARCH" == "aarch64" ]] && DOCKER_ARCH="arm64" || DOCKER_ARCH="amd64"

# ── Internet connectivity ──────────────────────────────────────────────────────
header "[2/6] Checking internet connectivity..."
for host in api.github.com hub.docker.com; do
  if ! curl -sf --max-time 8 "https://${host}" >/dev/null 2>&1; then
    fail "Cannot reach ${host}. Check your internet connection or DNS."
  fi
done
success "Internet connectivity: OK"

# ── Docker Engine ──────────────────────────────────────────────────────────────
header "[3/6] Checking Docker Engine..."

install_docker() {
  info "Installing Docker Engine..."
  local pkg_manager
  pkg_manager=$(command -v apt-get || command -v apt || true)
  [[ -z "$pkg_manager" ]] && fail "apt-get not found. Install Docker manually: https://docs.docker.com/engine/install/"

  apt-get update -qq >> "$LOG_FILE" 2>&1
  apt-get install -y -qq ca-certificates curl gnupg lsb-release >> "$LOG_FILE" 2>&1

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${DISTRO}/gpg" \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg >> "$LOG_FILE" 2>&1
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo "deb [arch=${DOCKER_ARCH} signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/${DISTRO} $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -qq >> "$LOG_FILE" 2>&1
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin >> "$LOG_FILE" 2>&1

  systemctl enable docker >> "$LOG_FILE" 2>&1
  systemctl start docker  >> "$LOG_FILE" 2>&1
  success "Docker Engine installed."
}

if command -v docker &>/dev/null; then
  DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
  DOCKER_MAJOR="${DOCKER_VER%%.*}"
  if [[ "$DOCKER_MAJOR" -ge "$MIN_DOCKER_VERSION" ]]; then
    success "Docker ${DOCKER_VER} (>= ${MIN_DOCKER_VERSION} required)"
  else
    warn "Docker ${DOCKER_VER} is below minimum (${MIN_DOCKER_VERSION}). Upgrading..."
    install_docker
  fi
else
  install_docker
fi

# ── Docker Compose plugin ──────────────────────────────────────────────────────
header "[4/6] Checking Docker Compose..."
if docker compose version &>/dev/null; then
  success "Docker Compose plugin: $(docker compose version --short 2>/dev/null || echo 'OK')"
else
  info "Installing Docker Compose plugin..."
  apt-get install -y -qq docker-compose-plugin >> "$LOG_FILE" 2>&1
  docker compose version &>/dev/null || fail "Docker Compose plugin installation failed."
  success "Docker Compose plugin installed."
fi

# ── Create installation directory ─────────────────────────────────────────────
header "[5/6] Preparing /opt/unotusk..."
mkdir -p "$INSTALL_DIR"
success "Installation directory: $INSTALL_DIR"

# ── Download latest installer ──────────────────────────────────────────────────
header "[6/6] Downloading UNOTUSK installer..."

# Resolve latest release tag via GitHub API
LATEST_TAG=$(curl -fsSL \
  "https://api.github.com/repos/${GITHUB_ORG}/${GITHUB_REPO}/releases/latest" \
  | grep '"tag_name"' | head -1 | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')

[[ -z "$LATEST_TAG" ]] && fail "Could not resolve latest release tag from GitHub."
info "Latest release: $LATEST_TAG"

BASE_URL="https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/releases/download/${LATEST_TAG}"
TARBALL_URL="${BASE_URL}/${INSTALLER_BINARY}"
CHECKSUM_URL="${BASE_URL}/${INSTALLER_BINARY}.sha256"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

info "Downloading ${INSTALLER_BINARY}..."
curl -fsSL --progress-bar "$TARBALL_URL" -o "${TMP_DIR}/${INSTALLER_BINARY}" \
  || fail "Download failed: $TARBALL_URL"

info "Verifying SHA-256 checksum..."
curl -fsSL "$CHECKSUM_URL" -o "${TMP_DIR}/${INSTALLER_BINARY}.sha256" \
  || fail "Checksum download failed: $CHECKSUM_URL"

EXPECTED_SUM=$(awk '{print $1}' "${TMP_DIR}/${INSTALLER_BINARY}.sha256")
ACTUAL_SUM=$(sha256sum "${TMP_DIR}/${INSTALLER_BINARY}" | awk '{print $1}')

if [[ "$EXPECTED_SUM" != "$ACTUAL_SUM" ]]; then
  fail "SHA-256 checksum mismatch! Expected: $EXPECTED_SUM  Got: $ACTUAL_SUM"
fi
success "Checksum verified: $ACTUAL_SUM"

info "Extracting installer..."
tar -xzf "${TMP_DIR}/${INSTALLER_BINARY}" -C "$TMP_DIR" >> "$LOG_FILE" 2>&1
success "Installer extracted."

# ── Hand off to versioned installer ───────────────────────────────────────────
INSTALLER_SCRIPT="${TMP_DIR}/installer/install.sh"
[[ ! -f "$INSTALLER_SCRIPT" ]] && fail "Installer package is malformed — install.sh not found."
chmod +x "$INSTALLER_SCRIPT"

info "Handing off to UNOTUSK Installer ${LATEST_TAG}..."
echo ""
exec bash "$INSTALLER_SCRIPT" --install-dir "$INSTALL_DIR" --version "$LATEST_TAG"
