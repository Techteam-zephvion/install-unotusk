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
BASE_URL="https://install.unotusk.com"
INSTALL_DIR="/opt/unotusk"
LOG_FILE="/var/log/unotusk-install.log"
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

  # Strategy 1: apt-get (works when Docker's official apt repo is configured)
  if apt-get install -y -qq docker-compose-plugin >> "$LOG_FILE" 2>&1 \
       && docker compose version &>/dev/null; then
    success "Docker Compose plugin installed via apt."

  else
    # Strategy 2: direct binary from GitHub releases (works regardless of how
    # Docker was installed — e.g. pre-installed via Pop!_OS / Snap / manual)
    info "apt install failed — falling back to direct binary install..."
    COMPOSE_VER=$(curl -fsSL \
      "https://api.github.com/repos/docker/compose/releases/latest" \
      | grep '"tag_name"' | head -1 \
      | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
    [[ -z "$COMPOSE_VER" ]] && fail "Could not resolve Docker Compose version from GitHub."

    COMPOSE_URL="https://github.com/docker/compose/releases/download/${COMPOSE_VER}/docker-compose-linux-${ARCH}"
    mkdir -p /usr/lib/docker/cli-plugins
    curl -fsSL "$COMPOSE_URL" \
      -o /usr/lib/docker/cli-plugins/docker-compose >> "$LOG_FILE" 2>&1 \
      || fail "Docker Compose binary download failed. Check $LOG_FILE"
    chmod +x /usr/lib/docker/cli-plugins/docker-compose

    docker compose version &>/dev/null \
      || fail "Docker Compose plugin installation failed. Check $LOG_FILE"
    success "Docker Compose plugin installed: $(docker compose version --short 2>/dev/null)"
  fi
fi

# ── Create installation directory ─────────────────────────────────────────────
header "[5/6] Preparing /opt/unotusk..."
mkdir -p "$INSTALL_DIR"
success "Installation directory: $INSTALL_DIR"

# ── Download installer from install.unotusk.com (Vercel) ──────────────────────
header "[6/6] Downloading UNOTUSK installer..."

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

INSTALLER_URL="${BASE_URL}/installer/install.sh"
CHECKSUM_URL="${BASE_URL}/installer/install.sh.sha256"

info "Fetching installer from ${BASE_URL}..."
curl -fsSL "$INSTALLER_URL" -o "${TMP_DIR}/install.sh" \
  || fail "Installer download failed. Check your internet connection."

# Verify checksum if the .sha256 file is available
if curl -fsSL "$CHECKSUM_URL" -o "${TMP_DIR}/install.sh.sha256" 2>/dev/null; then
  EXPECTED_SUM=$(awk '{print $1}' "${TMP_DIR}/install.sh.sha256")
  ACTUAL_SUM=$(sha256sum "${TMP_DIR}/install.sh" | awk '{print $1}')
  if [[ "$EXPECTED_SUM" != "$ACTUAL_SUM" ]]; then
    fail "SHA-256 checksum mismatch! Expected: $EXPECTED_SUM  Got: $ACTUAL_SUM"
  fi
  success "Checksum verified: $ACTUAL_SUM"
else
  warn "Checksum file not available — skipping verification."
fi

chmod +x "${TMP_DIR}/install.sh"
success "Installer ready."

# ── Hand off to full installer ─────────────────────────────────────────────────
info "Handing off to UNOTUSK Installer..."
echo ""
exec bash "${TMP_DIR}/install.sh" --install-dir "$INSTALL_DIR" --version "latest"
