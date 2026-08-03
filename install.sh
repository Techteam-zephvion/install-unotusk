#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer
# Usage:  curl -fsSL https://install.unotusk.com | bash
# Or:     sudo ./install.sh
# ==============================================================================
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
REPO_URL="https://github.com/Techteam-zephvion/install-unotusk.git"
BRANCH="${BRANCH:-main}"
MIN_DOCKER_VERSION=24
MIN_RAM_MB=4096
MIN_DISK_MB=10240
REQUIRED_PORTS=(3000 8444 50051 50052)

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "  ${CYAN}→${RESET} $*"; }
success() { echo -e "  ${GREEN}✔${RESET} $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; }
fail()    { echo -e "  ${RED}✘${RESET} $* — aborting."; exit 1; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }

# ── Banner ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       UNOTUSK Platform Installer         ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Idempotency check ──────────────────────────────────────────────────────────
# Detect an existing installation and present options rather than clobbering.
if [ -f "$INSTALL_DIR/.unotusk-version" ]; then
  EXISTING_VERSION=$(grep '^INSTALL_VERSION=' "$INSTALL_DIR/.unotusk-version" | cut -d= -f2)
  echo -e "  ${YELLOW}⚠  An existing UNOTUSK installation was detected${RESET}"
  echo "     Installation directory : $INSTALL_DIR"
  echo "     Installed version       : $EXISTING_VERSION"
  echo ""
  echo "  What would you like to do?"
  echo "    1) Upgrade        — pull latest images, migrate, restart"
  echo "    2) Reconfigure    — re-run the setup wizard"
  echo "    3) Repair         — reinstall CLI + scripts, keep data"
  echo "    4) Reinstall      — full reinstall, preserve existing data"
  echo "    5) Remove         — uninstall UNOTUSK"
  echo "    6) Abort          — exit without changes"
  echo ""
  read -r -p "  Choose [1-6]: " EXISTING_CHOICE
  case "$EXISTING_CHOICE" in
    1)
      info "Running upgrade..."
      cd "$INSTALL_DIR"
      exec bash scripts/unotusk-cli.sh update
      ;;
    2)
      info "Running reconfiguration..."
      cd "$INSTALL_DIR"
      exec bash scripts/unotusk-cli.sh reconfigure
      ;;
    3)
      info "Repairing CLI installation..."
      # Re-link CLI and make scripts executable, then exit
      chmod +x "$INSTALL_DIR"/scripts/*.sh
      ln -sf "$INSTALL_DIR/scripts/unotusk-cli.sh" /usr/local/bin/unotusk
      success "CLI repaired."
      exit 0
      ;;
    4)
      warn "Reinstall will rebuild from scratch but will NOT delete data volumes."
      read -r -p "  Continue? [y/N]: " CONFIRM
      [[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }
      # Fall through to a normal install run
      ;;
    5)
      info "Running uninstall..."
      cd "$INSTALL_DIR"
      exec bash scripts/unotusk-cli.sh uninstall
      ;;
    6|*)
      echo "  Aborted."
      exit 0
      ;;
  esac
fi

# ── Preflight checks ───────────────────────────────────────────────────────────
header "[1/5] Preflight checks"

# Root / sudo
if [ "$EUID" -ne 0 ]; then
  fail "Please run as root (sudo ./install.sh)"
fi
success "Running as root."

# OS detection
DISTRO=$(. /etc/os-release 2>/dev/null && echo "$ID" || echo "unknown")
DISTRO_VER=$(. /etc/os-release 2>/dev/null && echo "$VERSION_ID" || echo "?")
case "$DISTRO" in
  ubuntu)  success "OS: Ubuntu $DISTRO_VER" ;;
  debian)  success "OS: Debian $DISTRO_VER" ;;
  *)       warn "OS '$DISTRO $DISTRO_VER' is not officially supported (Ubuntu 24.04 / Debian 12+ recommended)." ;;
esac

# Required tools
for tool in docker curl openssl nslookup; do
  if command -v "$tool" &>/dev/null; then
    success "$tool is installed."
  else
    fail "$tool is required but not installed. Install it and re-run."
  fi
done

# Docker Compose plugin
if docker compose version &>/dev/null; then
  success "Docker Compose plugin is available."
else
  fail "Docker Compose plugin not found. Install it: https://docs.docker.com/compose/install/"
fi

# Docker version
DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
DOCKER_MAJOR=$(echo "$DOCKER_VER" | cut -d. -f1)
if [ "$DOCKER_MAJOR" -ge "$MIN_DOCKER_VERSION" ]; then
  success "Docker version: $DOCKER_VER (>= $MIN_DOCKER_VERSION required)."
else
  fail "Docker $DOCKER_VER is below the minimum required version ($MIN_DOCKER_VERSION)."
fi

# RAM
if command -v free &>/dev/null; then
  TOTAL_RAM_MB=$(free -m | awk '/^Mem:/ {print $2}')
  if [ "$TOTAL_RAM_MB" -ge "$MIN_RAM_MB" ]; then
    success "RAM: ${TOTAL_RAM_MB}MB total (>= ${MIN_RAM_MB}MB required)."
  else
    warn "RAM: ${TOTAL_RAM_MB}MB — recommended minimum is ${MIN_RAM_MB}MB."
  fi
fi

# Disk space
FREE_DISK=$(df -m "$( dirname "$INSTALL_DIR" )" | awk 'NR==2 {print $4}')
if [ "$FREE_DISK" -ge "$MIN_DISK_MB" ]; then
  success "Disk: ${FREE_DISK}MB available (>= ${MIN_DISK_MB}MB required)."
else
  fail "Insufficient disk space: ${FREE_DISK}MB available, ${MIN_DISK_MB}MB required."
fi

# CPU cores
CPU_CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
if [ "$CPU_CORES" -ge 2 ]; then
  success "CPU: ${CPU_CORES} cores available."
else
  warn "Only ${CPU_CORES} CPU core detected — 2+ recommended."
fi

# Port conflicts
PORT_BLOCKED=false
for port in "${REQUIRED_PORTS[@]}"; do
  if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
     netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
    warn "Port $port is already in use. This may cause a conflict."
    PORT_BLOCKED=true
  fi
done
$PORT_BLOCKED || success "All required ports are free: ${REQUIRED_PORTS[*]}"

# Internet connectivity
if curl -sf --max-time 5 https://hub.docker.com &>/dev/null; then
  success "Internet connectivity: OK"
else
  warn "Could not reach hub.docker.com — image pulls may fail."
fi

# Write access
if touch "$INSTALL_DIR/.write-test" 2>/dev/null; then
  rm -f "$INSTALL_DIR/.write-test"
  success "Write access to $INSTALL_DIR: OK"
else
  mkdir -p "$INSTALL_DIR"
  success "Created installation directory: $INSTALL_DIR"
fi

success "Preflight checks complete."

# ── Prepare directory ──────────────────────────────────────────────────────────
header "[2/5] Preparing installation directory at $INSTALL_DIR..."

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [ -d ".git" ]; then
  info "Repository already present — pulling latest..."
  git pull origin "$BRANCH" 2>/dev/null || warn "Git pull failed — continuing with existing files."
else
  # In production, clone from the real repo URL.
  # For local dev/testing, copy from the working tree if it exists.
  LOCAL_SRC="/home/devils/PRO/Unotusk"
  if [ -d "$LOCAL_SRC/.git" ] && [ "$INSTALL_DIR" != "$LOCAL_SRC" ]; then
    info "Copying from local development tree ($LOCAL_SRC)..."
    # The installer only ever runs pre-built GHCR images (see
    # installer/manifest.json) — it never builds US/UPS/UCA/UAC/UP from
    # source. Excluding their build/dependency dirs (Rust target/, npm
    # node_modules/, Tauri out/) turns this from a 70GB+ multi-minute copy
    # into a few hundred MB — those dirs contributed nothing the installer
    # reads, just made "sudo bash install.sh" look hung.
    rsync -a --exclude='.git' --exclude='backups' \
      --exclude='*/target' --exclude='*/node_modules' --exclude='*/out' \
      "$LOCAL_SRC/" "$INSTALL_DIR/" 2>/dev/null || \
      cp -a "$LOCAL_SRC/." "$INSTALL_DIR/" 2>/dev/null
  elif curl -sf --max-time 5 https://github.com &>/dev/null; then
    info "Cloning UNOTUSK repository..."
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" . 2>/dev/null || \
      warn "Git clone failed — ensure the repository is accessible."
  else
    warn "Cannot clone repository and no local source found. Continuing with existing files."
  fi
fi

chmod +x scripts/*.sh 2>/dev/null || true
success "Installation directory is ready."

# ── Install CLI globally ───────────────────────────────────────────────────────
header "[3/5] Installing CLI..."
ln -sf "$INSTALL_DIR/scripts/unotusk-cli.sh" /usr/local/bin/unotusk
chmod +x "$INSTALL_DIR/scripts/unotusk-cli.sh"
success "unotusk CLI installed at /usr/local/bin/unotusk"

# ── Configuration wizard ───────────────────────────────────────────────────────
header "[4/5] Configuration..."
if [ -z "${UNATTENDED:-}" ]; then
  bash "$INSTALL_DIR/scripts/wizard.sh" "$INSTALL_DIR/.env.wizard"
else
  info "Running in unattended mode — skipping interactive wizard."
  info "Ensure required variables are pre-set in the environment."
fi

# ── Bootstrap ──────────────────────────────────────────────────────────────────
header "[5/5] Bootstrapping services..."
bash "$INSTALL_DIR/scripts/bootstrap.sh"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║    UNOTUSK Installation Complete  🚀     ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo "  Run 'unotusk status' to verify all services are healthy."
echo "  Run 'unotusk doctor' to perform a full diagnostic check."
echo "  See docs/Operations_Manual.md for operational guidance."
echo ""
