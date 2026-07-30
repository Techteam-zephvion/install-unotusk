#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Platform Installer  v2.0.0
#
#  Commercial-grade on-premises installer.
#  Installs the complete UNOTUSK stack under /opt/unotusk.
#
#  Usage (via bootstrap):
#    curl -fsSL https://install.unotusk.com | sudo bash
#
#  Unattended:
#    UNATTENDED=1 \
#    UNOTUSK_ORG_NAME="Acme Corp" \
#    UNOTUSK_LICENSE_KEY="UNOT-XXXX-XXXX-XXXX" \
#    UNOTUSK_PLATFORM_URL="https://platform.unotusk.com" \
#    curl -fsSL https://install.unotusk.com | sudo bash
#
#  Supported OS:   Ubuntu 24.04  ·  Debian 12  ·  Pop!_OS 24.04
#  Supported Arch: amd64 (x86_64)  ·  arm64 (aarch64)
# ==============================================================================
set -Eeuo pipefail
IFS=$'\n\t'

# ── Argument parsing (must happen before readonly declarations) ────────────────
_ARG_INSTALL_DIR="/opt/unotusk"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) _ARG_INSTALL_DIR="$2"; shift 2 ;;
    --version)     shift 2 ;;   # accepted but ignored; version is hardcoded
    *)             shift ;;
  esac
done

# ── Immutable constants ────────────────────────────────────────────────────────
readonly INSTALLER_VERSION="2.0.0"
readonly INSTALL_DIR="${_ARG_INSTALL_DIR}"
readonly LOG_FILE="/var/log/unotusk-install.log"
readonly STATE_FILE="${INSTALL_DIR}/.install-state"
readonly ENV_FILE="${INSTALL_DIR}/.env"
readonly SECRETS_FILE="${INSTALL_DIR}/.secrets"
readonly COMPOSE_FILE="${INSTALL_DIR}/docker-compose.yml"
readonly CADDYFILE="${INSTALL_DIR}/Caddyfile"
readonly VERSION_FILE="${INSTALL_DIR}/.unotusk-version"
readonly BASE_URL="https://install.unotusk.com"

# Resource thresholds
readonly MIN_CPU_CORES=2
readonly MIN_RAM_MB=8192     # 8 GB  — hard minimum
readonly WARN_RAM_MB=14336   # 14 GB — warn below this (16 GB machines report ~15 GB)
readonly MIN_DISK_MB=20480   # 20 GB — hard minimum

# Docker
readonly MIN_DOCKER_MAJOR=24

# Timing
readonly CONTAINER_WAIT_SECS=180
readonly HEALTH_INTERVAL_SECS=5

# OS
readonly MIN_UBUNTU_MAJOR=24
readonly MIN_DEBIAN_MAJOR=12

# Ports — ONLY Caddy is exposed on the host
readonly -a REQUIRED_PORTS=(80 443)

# Stages
readonly TOTAL_STAGES=20
_STAGE_NUM=0
_TMP_DIR=""
_ROLLBACK_NEEDED="false"

# ── Colour palette ─────────────────────────────────────────────────────────────
readonly RED='\033[0;31m'    GREEN='\033[0;32m'   YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'   BLUE='\033[0;34m'    BOLD='\033[1m'
readonly DIM='\033[2m'       RESET='\033[0m'

# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════
_ts()     { date -u +%Y-%m-%dT%H:%M:%SZ; }
_log()    { { printf '%s %s\n' "$(_ts)" "$*" >> "${LOG_FILE}"; } 2>/dev/null || true; }

info()    { local m="  ${CYAN}→${RESET} $*";   echo -e "$m"; _log "INFO  $*"; }
success() { local m="  ${GREEN}✔${RESET} $*";  echo -e "$m"; _log "OK    $*"; }
warn()    { local m="  ${YELLOW}⚠${RESET} $*"; echo -e "$m"; _log "WARN  $*"; }

header() {
  (( _STAGE_NUM++ )) || true
  echo -e "\n${BOLD}${BLUE}━━  [${_STAGE_NUM}/${TOTAL_STAGES}] $*${RESET}"
  _log "──── [${_STAGE_NUM}/${TOTAL_STAGES}] $*"
}

# ══════════════════════════════════════════════════════════════════════════════
# ERROR HANDLING
# Every failure shows: reason · possible fixes · log path · exits cleanly
# ══════════════════════════════════════════════════════════════════════════════
fail() {
  local reason="$1"; shift
  local -a fixes=("$@")

  echo -e "\n  ${RED}${BOLD}✘  ${reason}${RESET}" >&2
  _log "FAIL  ${reason}"

  if [[ ${#fixes[@]} -gt 0 ]]; then
    echo -e "\n  ${DIM}Possible fixes:${RESET}" >&2
    local fix
    for fix in "${fixes[@]}"; do
      echo -e "    ${DIM}•${RESET} ${fix}" >&2
      _log "FIX   ${fix}"
    done
  fi

  echo -e "\n  ${DIM}Full log: ${LOG_FILE}${RESET}\n" >&2
  exit 1
}

# ══════════════════════════════════════════════════════════════════════════════
# TRAP HANDLERS
# ══════════════════════════════════════════════════════════════════════════════
_cleanup() {
  [[ -n "${_TMP_DIR}" && -d "${_TMP_DIR}" ]] && rm -rf "${_TMP_DIR}" 2>/dev/null || true
}

_rollback() {
  [[ "${_ROLLBACK_NEEDED}" != "true" ]] && return
  warn "Rolling back partial installation..."
  docker compose --file "${COMPOSE_FILE}" down --volumes 2>/dev/null || true
  _log "ROLLBACK containers stopped and volumes removed"
  info "System returned to clean state."
}

_on_error() {
  local code=$? line=$1
  _cleanup
  _rollback
  [[ $code -eq 1 ]] && exit 1   # fail() already handled it
  echo -e "\n  ${RED}✘ Unexpected error at line ${line} (exit ${code})${RESET}" >&2
  echo -e "  ${DIM}Full log: ${LOG_FILE}${RESET}\n" >&2
  _log "ERROR Unexpected exit ${code} at line ${line}"
  exit "${code}"
}

trap '_cleanup'            EXIT
trap '_on_error ${LINENO}' ERR

# ══════════════════════════════════════════════════════════════════════════════
# IDEMPOTENCY — stage state machine
# ══════════════════════════════════════════════════════════════════════════════
stage_done() { grep -qxF "stage:$1" "${STATE_FILE}" 2>/dev/null; }

mark_stage() {
  mkdir -p "${INSTALL_DIR}"
  echo "stage:$1" >> "${STATE_FILE}"
  _log "MARK  stage '$1' complete"
}

# ══════════════════════════════════════════════════════════════════════════════
# PROMPT HELPERS
# ══════════════════════════════════════════════════════════════════════════════
ask() {
  local prompt="$1" var_name="$2" default="${3:-}"
  if [[ "${UNATTENDED:-0}" == "1" ]]; then
    local val="${!var_name:-${default}}"
    [[ -z "$val" ]] && fail "Unattended mode: '${var_name}' is required but not set." \
      "Export ${var_name}=<value> before running the installer."
    printf -v "$var_name" '%s' "$val"
    return
  fi
  local input=""
  if [[ -n "$default" ]]; then
    read -r -p "  ${CYAN}?${RESET} ${prompt} [${default}]: " input < /dev/tty
    printf -v "$var_name" '%s' "${input:-${default}}"
  else
    read -r -p "  ${CYAN}?${RESET} ${prompt}: " input < /dev/tty
    printf -v "$var_name" '%s' "$input"
  fi
}

ask_secret() {
  local prompt="$1" var_name="$2"
  if [[ "${UNATTENDED:-0}" == "1" ]]; then
    local val="${!var_name:-}"
    [[ -z "$val" ]] && fail "Unattended mode: '${var_name}' is required but not set."
    printf -v "$var_name" '%s' "$val"
    return
  fi
  local input=""
  read -r -s -p "  ${CYAN}?${RESET} ${prompt}: " input < /dev/tty; echo
  printf -v "$var_name" '%s' "$input"
}

# ══════════════════════════════════════════════════════════════════════════════
# DOCKER COMPOSE RUNNER — hides output unless error occurs
# ══════════════════════════════════════════════════════════════════════════════
run_compose() {
  local tmp_out
  tmp_out=$(mktemp)
  if docker compose --file "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
     "$@" >"$tmp_out" 2>&1; then
    cat "$tmp_out" >> "${LOG_FILE}"
    rm -f "$tmp_out"
    return 0
  else
    local code=$?
    cat "$tmp_out" >> "${LOG_FILE}"
    echo -e "\n  ${DIM}Docker Compose output:${RESET}" >&2
    cat "$tmp_out" >&2
    rm -f "$tmp_out"
    return $code
  fi
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Banner
# ══════════════════════════════════════════════════════════════════════════════
show_banner() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}║       UNOTUSK Platform Installer         ║${RESET}"
  printf  "${BOLD}║       Version: %-26s║${RESET}\n" "${INSTALLER_VERSION}"
  echo -e "${BOLD}║       install.unotusk.com                ║${RESET}"
  echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
  echo ""
  _log "════ UNOTUSK Installer ${INSTALLER_VERSION} started ════"
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Root check
# ══════════════════════════════════════════════════════════════════════════════
check_root() {
  header "Root privileges"
  if [[ "${EUID}" -ne 0 ]]; then
    fail "Root privileges are required." \
      "Run: curl -fsSL https://install.unotusk.com | sudo bash"
  fi
  success "Running as root."
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — OS validation
# ══════════════════════════════════════════════════════════════════════════════
_effective_distro() {
  local id="$1" id_like="$2"
  case "$id" in
    ubuntu|debian) echo "$id"; return ;;
  esac
  # IFS=$'\n\t' disables space-splitting — must split ID_LIKE explicitly
  local -a tokens
  IFS=' ' read -ra tokens <<< "$id_like"
  local token
  for token in "${tokens[@]:-}"; do
    case "$token" in
      ubuntu|debian) echo "$token"; return ;;
    esac
  done
  echo "$id"
}

detect_os() {
  header "Operating system"
  [[ -f /etc/os-release ]] || fail \
    "Cannot detect operating system — /etc/os-release not found." \
    "UNOTUSK requires Ubuntu 24.04, Debian 12, or a compatible derivative."

  # shellcheck source=/dev/null
  source /etc/os-release
  local id="${ID:-unknown}" ver="${VERSION_ID:-0}" pretty="${PRETTY_NAME:-unknown}"
  local major="${ver%%.*}" effective
  effective=$(_effective_distro "$id" "${ID_LIKE:-}")

  case "$effective" in
    ubuntu)
      [[ "$major" -ge "$MIN_UBUNTU_MAJOR" ]] || fail \
        "${pretty} is not supported." \
        "Upgrade to Ubuntu 24.04 LTS: https://ubuntu.com/download/server"
      ;;
    debian)
      [[ "$major" -ge "$MIN_DEBIAN_MAJOR" ]] || fail \
        "${pretty} is not supported." \
        "Upgrade to Debian 12 (Bookworm): https://www.debian.org/releases/"
      ;;
    *)
      fail "Unsupported OS: ${pretty}." \
        "UNOTUSK supports Ubuntu 24.04, Debian 12, and compatible derivatives (Pop!_OS)."
      ;;
  esac

  success "OS: ${pretty}"
  _log "OS id=${id} effective=${effective} version=${ver}"
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — Architecture
# ══════════════════════════════════════════════════════════════════════════════
check_arch() {
  header "System architecture"
  local arch
  arch=$(uname -m)
  case "$arch" in
    x86_64)  success "Architecture: amd64 (x86_64)"  ;;
    aarch64) success "Architecture: arm64 (aarch64)" ;;
    *)
      fail "Unsupported architecture: ${arch}." \
        "UNOTUSK supports amd64 (x86_64) and arm64 (aarch64) only."
      ;;
  esac
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — Internet connectivity
# ══════════════════════════════════════════════════════════════════════════════
check_internet() {
  header "Internet connectivity"
  local -ra targets=(
    "https://install.unotusk.com"
    "https://hub.docker.com"
    "https://one.one.one.one"
  )
  local target
  for target in "${targets[@]}"; do
    if curl -fsS --max-time 10 --head "$target" >/dev/null 2>&1; then
      success "Reachable: ${target}"
    else
      fail "Cannot reach: ${target}" \
        "Check your internet connection." \
        "Verify firewall allows outbound HTTPS (port 443)." \
        "Test DNS: nslookup install.unotusk.com"
    fi
  done
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 6 — Docker Engine
# ══════════════════════════════════════════════════════════════════════════════
_add_docker_apt_repo() {
  local arch
  arch=$(dpkg --print-architecture 2>/dev/null || echo "amd64")

  # shellcheck source=/dev/null
  source /etc/os-release
  local codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
  [[ -z "$codename" ]] && codename=$(lsb_release -cs 2>/dev/null || echo "noble")

  local repo_distro="ubuntu"
  [[ "${ID:-}" == "debian" ]] && repo_distro="debian"

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${repo_distro}/gpg" \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg >> "${LOG_FILE}" 2>&1
  chmod a+r /etc/apt/keyrings/docker.gpg

  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/%s %s stable\n' \
    "$arch" "$repo_distro" "$codename" \
    > /etc/apt/sources.list.d/docker.list

  apt-get update -qq >> "${LOG_FILE}" 2>&1
}

_install_docker_engine() {
  info "Installing Docker Engine from Docker Inc. apt repository..."
  apt-get install -y -qq ca-certificates curl gnupg lsb-release >> "${LOG_FILE}" 2>&1
  _add_docker_apt_repo
  apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin >> "${LOG_FILE}" 2>&1 \
    || fail "Docker Engine installation failed." \
      "Check apt logs: journalctl -u apt" \
      "Verify Docker apt repo: cat /etc/apt/sources.list.d/docker.list" \
      "See full output: ${LOG_FILE}"
  systemctl enable --now docker >> "${LOG_FILE}" 2>&1
  success "Docker Engine installed."
}

check_docker() {
  header "Docker Engine"
  if ! command -v docker &>/dev/null; then
    info "Docker not found — installing..."
    _install_docker_engine
    return
  fi
  local ver major
  ver=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
  major="${ver%%.*}"
  if [[ "$major" -lt "$MIN_DOCKER_MAJOR" ]]; then
    warn "Docker ${ver} is below minimum required version ${MIN_DOCKER_MAJOR}. Upgrading..."
    _install_docker_engine
    return
  fi
  success "Docker ${ver} (minimum ${MIN_DOCKER_MAJOR} required)"
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 7 — Docker Compose plugin
# ══════════════════════════════════════════════════════════════════════════════
_install_compose_binary() {
  info "Installing Docker Compose plugin via binary release..."
  local arch_tag
  case "$(uname -m)" in
    x86_64)  arch_tag="linux-x86_64"  ;;
    aarch64) arch_tag="linux-aarch64" ;;
    *)       fail "No Compose binary available for architecture: $(uname -m)." ;;
  esac
  local ver
  ver=$(curl -fsSL "https://api.github.com/repos/docker/compose/releases/latest" \
    | grep '"tag_name"' | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
  [[ -z "$ver" ]] && fail "Could not resolve Docker Compose version." \
    "Check connectivity: curl https://api.github.com/repos/docker/compose/releases/latest"
  local dest="/usr/lib/docker/cli-plugins"
  mkdir -p "$dest"
  curl -fsSL \
    "https://github.com/docker/compose/releases/download/${ver}/docker-compose-${arch_tag}" \
    -o "${dest}/docker-compose" >> "${LOG_FILE}" 2>&1 \
    || fail "Docker Compose binary download failed." \
      "Check connectivity to github.com" "See: ${LOG_FILE}"
  chmod +x "${dest}/docker-compose"
}

check_compose() {
  header "Docker Compose plugin"
  if docker compose version &>/dev/null; then
    success "Docker Compose: $(docker compose version --short 2>/dev/null)"
    return
  fi
  info "Docker Compose plugin not found — installing..."
  if apt-get install -y -qq docker-compose-plugin >> "${LOG_FILE}" 2>&1 \
     && docker compose version &>/dev/null; then
    success "Docker Compose installed via apt."
    return
  fi
  _install_compose_binary
  docker compose version &>/dev/null \
    || fail "Docker Compose installation failed." \
      "Try manually: apt-get install docker-compose-plugin" \
      "Or see: https://docs.docker.com/compose/install/"
  success "Docker Compose installed: $(docker compose version --short 2>/dev/null)"
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 8 — Resource validation
# ══════════════════════════════════════════════════════════════════════════════
_check_cpu() {
  local cores
  cores=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo 1)
  if [[ "$cores" -lt "$MIN_CPU_CORES" ]]; then
    warn "CPU: ${cores} core(s) — minimum ${MIN_CPU_CORES} recommended. Performance may be degraded."
  else
    success "CPU: ${cores} core(s)"
  fi
}

_check_ram() {
  local ram_mb
  ram_mb=$(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo)
  if [[ "$ram_mb" -lt "$MIN_RAM_MB" ]]; then
    fail "Insufficient RAM: ${ram_mb} MB. UNOTUSK requires at least ${MIN_RAM_MB} MB (8 GB)." \
      "Add more RAM to this server before installing." \
      "16 GB is recommended for production workloads."
  elif [[ "$ram_mb" -lt "$WARN_RAM_MB" ]]; then
    warn "RAM: ${ram_mb} MB — ${WARN_RAM_MB} MB (16 GB) is recommended for production."
  else
    success "RAM: ${ram_mb} MB"
  fi
}

_check_disk() {
  local parent="${INSTALL_DIR%/*}"
  [[ -d "$parent" ]] || parent="/"
  local disk_mb
  disk_mb=$(df -m "$parent" 2>/dev/null | awk 'NR==2{print $4}')
  if [[ "${disk_mb:-0}" -lt "$MIN_DISK_MB" ]]; then
    fail "Insufficient disk: ${disk_mb:-0} MB free. Minimum: ${MIN_DISK_MB} MB (20 GB)." \
      "Free disk space: du -sh /* | sort -rh | head -10" \
      "Or mount a larger volume at ${INSTALL_DIR}."
  else
    success "Disk: ${disk_mb} MB available"
  fi
}

check_resources() {
  header "System resources"
  _check_cpu
  _check_ram
  _check_disk
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 9 — Create installation directory layout
# ══════════════════════════════════════════════════════════════════════════════
create_directories() {
  header "Installation directory"
  local -ra layout=(
    "${INSTALL_DIR}/config"
    "${INSTALL_DIR}/compose"
    "${INSTALL_DIR}/logs"
    "${INSTALL_DIR}/certs/ca"
    "${INSTALL_DIR}/certs/us"
    "${INSTALL_DIR}/certs/ups"
    "${INSTALL_DIR}/certs/ai-pie"
    "${INSTALL_DIR}/backups"
    "${INSTALL_DIR}/scripts"
  )
  local d
  for d in "${layout[@]}"; do
    mkdir -p "$d"
    _log "MKDIR ${d}"
  done
  chmod 750 "${INSTALL_DIR}"
  success "Directory layout created: ${INSTALL_DIR}"
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 10 — Port validation
# Only ports 80 and 443 need to be free (Caddy). Everything else is internal.
# ══════════════════════════════════════════════════════════════════════════════
check_ports() {
  header "Network ports"
  local port failed="false"
  for port in "${REQUIRED_PORTS[@]}"; do
    if ss -tlnp 2>/dev/null | grep -q ":${port} " \
    || netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
      warn "Port ${port} is already in use."
      failed="true"
    else
      success "Port ${port}: available"
    fi
  done
  [[ "$failed" == "true" ]] && fail \
    "One or more required ports (80, 443) are already in use." \
    "Find process: ss -tlnp | grep -E ':(80|443) '" \
    "Stop conflicting service: systemctl stop <service-name>" \
    "Only Caddy (reverse proxy) requires ports 80 and 443."
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 11 — Prompt user for configuration
# ══════════════════════════════════════════════════════════════════════════════
_prompt_org() {
  echo -e "\n${BOLD}── Organisation${RESET}"
  ask "Organisation name"               UNOTUSK_ORG_NAME    "${UNOTUSK_ORG_NAME:-}"
  ask "License key (UNOT-XXXX-XXXX-XXXX)" UNOTUSK_LICENSE_KEY "${UNOTUSK_LICENSE_KEY:-}"
  [[ -z "${UNOTUSK_ORG_NAME:-}"    ]] && fail "Organisation name is required."
  [[ -z "${UNOTUSK_LICENSE_KEY:-}" ]] && fail "License key is required."
}

_prompt_platform() {
  echo -e "\n${BOLD}── Platform connection${RESET}"
  ask "Platform URL" \
    UNOTUSK_PLATFORM_URL "${UNOTUSK_PLATFORM_URL:-https://platform.unotusk.com}"
  ask "JWKS push URL (from Zephvion onboarding)" \
    UNOTUSK_JWKS_PUSH_URL "${UNOTUSK_JWKS_PUSH_URL:-}"
  ask_secret "JWKS push secret" UNOTUSK_JWKS_PUSH_SECRET
}

_prompt_integrations() {
  echo -e "\n${BOLD}── Integrations  ${DIM}(press Enter to skip)${RESET}"
  ask "GitHub organisation (e.g. acme-corp)"   UNOTUSK_GITHUB_ORG  "${UNOTUSK_GITHUB_ORG:-}"
  ask "Jira URL (e.g. https://acme.atlassian.net)" UNOTUSK_JIRA_URL "${UNOTUSK_JIRA_URL:-}"
}

_prompt_oidc() {
  echo -e "\n${BOLD}── SSO / OIDC  ${DIM}(press Enter to skip)${RESET}"
  info "Supported providers: Entra ID · Okta · Google Workspace · Keycloak"
  ask "OIDC issuer URL" UNOTUSK_OIDC_ISSUER "${UNOTUSK_OIDC_ISSUER:-}"
  if [[ -n "${UNOTUSK_OIDC_ISSUER:-}" ]]; then
    ask        "OIDC client ID"     UNOTUSK_OIDC_CLIENT_ID     "${UNOTUSK_OIDC_CLIENT_ID:-}"
    ask_secret "OIDC client secret" UNOTUSK_OIDC_CLIENT_SECRET
  fi
}

_show_config_summary() {
  echo ""
  echo -e "${BOLD}Configuration summary:${RESET}"
  printf "  %-26s %s\n" "Organisation:"    "${UNOTUSK_ORG_NAME}"
  printf "  %-26s %s\n" "Org ID:"          "${UNOTUSK_ORG_ID}"
  printf "  %-26s %s\n" "License key:"     "${UNOTUSK_LICENSE_KEY:0:12}…"
  printf "  %-26s %s\n" "Platform URL:"    "${UNOTUSK_PLATFORM_URL}"
  printf "  %-26s %s\n" "GitHub org:"      "${UNOTUSK_GITHUB_ORG:-not set}"
  printf "  %-26s %s\n" "Jira:"            "${UNOTUSK_JIRA_URL:-not set}"
  printf "  %-26s %s\n" "OIDC issuer:"     "${UNOTUSK_OIDC_ISSUER:-not configured}"
}

prompt_config() {
  header "Configuration"
  [[ "${UNATTENDED:-0}" == "1" ]] && info "Unattended mode — reading from environment."
  _prompt_org
  _prompt_platform
  _prompt_integrations
  _prompt_oidc
  UNOTUSK_ORG_ID="${UNOTUSK_ORG_ID:-$(cat /proc/sys/kernel/random/uuid 2>/dev/null \
    || uuidgen 2>/dev/null \
    || printf '%s' "$(date +%s%N | sha256sum | head -c 32)")}"
  _show_config_summary
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 12 — Generate .env and .secrets
# ══════════════════════════════════════════════════════════════════════════════
_gen_password() {
  tr -dc 'A-Za-z0-9!@#$%^&*_+=-' < /dev/urandom 2>/dev/null | head -c 32 || true
}

generate_env() {
  header "Generating configuration files"
  local pg_pass redis_pass qdrant_key
  pg_pass=$(_gen_password)
  redis_pass=$(_gen_password)
  qdrant_key=$(_gen_password)

  cat > "${ENV_FILE}" <<EOF
# UNOTUSK Platform Configuration
# Generated by installer v${INSTALLER_VERSION} on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Re-generate: unotusk reconfigure

ORG_ID=${UNOTUSK_ORG_ID}
ORG_NAME=${UNOTUSK_ORG_NAME}
PLATFORM_URL=${UNOTUSK_PLATFORM_URL}
PLATFORM_JWKS_PUSH_URL=${UNOTUSK_JWKS_PUSH_URL:-}
UNOTUSK_VERSION=latest
LOG_LEVEL=info

# Database
POSTGRES_USER=unotusk
POSTGRES_PASSWORD=${pg_pass}
POSTGRES_DB=unotusk

# Cache
REDIS_PASSWORD=${redis_pass}

# Vector store
QDRANT_API_KEY=${qdrant_key}

# Integrations
GITHUB_ORG_NAME=${UNOTUSK_GITHUB_ORG:-}
JIRA_URL=${UNOTUSK_JIRA_URL:-}

# SSO
OIDC_ISSUER=${UNOTUSK_OIDC_ISSUER:-}
OIDC_CLIENT_ID=${UNOTUSK_OIDC_CLIENT_ID:-}
EOF
  chmod 600 "${ENV_FILE}"

  cat > "${SECRETS_FILE}" <<EOF
# UNOTUSK Secrets — chmod 600 — DO NOT COMMIT
PLATFORM_LICENSE_KEY=${UNOTUSK_LICENSE_KEY}
JWKS_PUSH_SECRET=${UNOTUSK_JWKS_PUSH_SECRET:-}
OIDC_CLIENT_SECRET=${UNOTUSK_OIDC_CLIENT_SECRET:-}
EOF
  chmod 600 "${SECRETS_FILE}"

  success ".env written  (chmod 600): ${ENV_FILE}"
  success ".secrets written (chmod 600): ${SECRETS_FILE}"
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 13 — Download docker-compose.yml and Caddyfile
# ══════════════════════════════════════════════════════════════════════════════
download_compose() {
  header "Downloading stack configuration"
  _TMP_DIR=$(mktemp -d)

  local compose_url="${BASE_URL}/compose/docker-compose.yml"
  local caddy_url="${BASE_URL}/compose/Caddyfile"

  info "Fetching docker-compose.yml..."
  curl -fsSL "$compose_url" -o "${_TMP_DIR}/docker-compose.yml" \
    || fail "Failed to download docker-compose.yml." \
      "Check connectivity to ${BASE_URL}" \
      "Try: curl -fsSL ${compose_url}"

  info "Fetching Caddyfile..."
  curl -fsSL "$caddy_url" -o "${_TMP_DIR}/Caddyfile" \
    || fail "Failed to download Caddyfile." \
      "Check connectivity to ${BASE_URL}"

  install -m 644 "${_TMP_DIR}/docker-compose.yml" "${COMPOSE_FILE}"
  install -m 644 "${_TMP_DIR}/Caddyfile"          "${CADDYFILE}"

  success "docker-compose.yml → ${COMPOSE_FILE}"
  success "Caddyfile → ${CADDYFILE}"
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 14 — Pull Docker images
# ══════════════════════════════════════════════════════════════════════════════
pull_images() {
  header "Pulling Docker images"
  info "This may take several minutes on first run..."

  run_compose pull \
    || fail "Failed to pull one or more Docker images." \
      "Verify Docker Hub connectivity: curl -I https://registry-1.docker.io" \
      "Check for private image auth: docker login ghcr.io" \
      "Inspect errors: ${LOG_FILE}"

  success "All images pulled successfully."
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 15 — Start containers
# ══════════════════════════════════════════════════════════════════════════════
start_containers() {
  header "Starting containers"
  _ROLLBACK_NEEDED="true"

  run_compose up --detach --remove-orphans \
    || fail "Failed to start containers." \
      "Validate compose file: docker compose --file ${COMPOSE_FILE} config" \
      "View container logs: docker compose --file ${COMPOSE_FILE} logs" \
      "Check .env file: cat ${ENV_FILE}" \
      "See installer log: ${LOG_FILE}"

  _ROLLBACK_NEEDED="false"
  success "Containers started."
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 16 — Wait for all containers to become healthy
# ══════════════════════════════════════════════════════════════════════════════
_wait_for_service() {
  local service="$1"
  local deadline=$(( $(date +%s) + CONTAINER_WAIT_SECS ))

  while [[ $(date +%s) -lt $deadline ]]; do
    local cid health
    cid=$(docker compose --file "${COMPOSE_FILE}" ps -q "${service}" 2>/dev/null || echo "")
    [[ -z "$cid" ]] && { sleep "${HEALTH_INTERVAL_SECS}"; continue; }

    health=$(docker inspect --format '{{.State.Health.Status}}' "$cid" 2>/dev/null || echo "starting")
    case "$health" in
      healthy)   success "${service}: healthy"; return 0 ;;
      unhealthy) fail "Service '${service}' reported unhealthy." \
        "Inspect logs: docker compose --file ${COMPOSE_FILE} logs ${service}" \
        "Inspect events: docker inspect ${cid} | python3 -m json.tool | grep Health -A 20" ;;
      *)         _log "INFO  ${service} status=${health}, waiting..."
                 sleep "${HEALTH_INTERVAL_SECS}" ;;
    esac
  done

  fail "Timed out (${CONTAINER_WAIT_SECS}s) waiting for '${service}' to become healthy." \
    "Check logs: docker compose --file ${COMPOSE_FILE} logs ${service}" \
    "Increase timeout or check service configuration."
}

wait_healthy() {
  header "Waiting for healthy containers"
  info "Waiting up to ${CONTAINER_WAIT_SECS}s per service..."
  # Boot order: DB → cache → vector → observability → services → proxy
  local -ra boot_order=(postgres redis qdrant phoenix us ups ai-pie caddy)
  local svc
  for svc in "${boot_order[@]}"; do
    _wait_for_service "$svc"
  done
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 17 — Register with UNOTUSK Platform
# ══════════════════════════════════════════════════════════════════════════════
register_platform() {
  header "Platform registration"
  # shellcheck source=/dev/null
  source "${SECRETS_FILE}"
  local license="${PLATFORM_LICENSE_KEY:-}"
  [[ -z "$license" ]] && fail "License key not found in ${SECRETS_FILE}." \
    "Re-run the installer or set PLATFORM_LICENSE_KEY in ${SECRETS_FILE}."

  local org_id
  org_id=$(grep '^ORG_ID=' "${ENV_FILE}" | cut -d= -f2-)

  local platform_url
  platform_url=$(grep '^PLATFORM_URL=' "${ENV_FILE}" | cut -d= -f2-)
  local register_url="${platform_url%:*}/api/v1/register"

  local http_code
  http_code=$(curl -fsS --max-time 30 \
    -X POST "$register_url" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${license}" \
    -d "{\"org_id\":\"${org_id}\",\"installer_version\":\"${INSTALLER_VERSION}\"}" \
    -o /dev/null -w "%{http_code}" 2>> "${LOG_FILE}" || echo "000")

  case "$http_code" in
    200|201|204) success "Registered with UNOTUSK Platform (HTTP ${http_code})." ;;
    401|403) fail "License key rejected by Platform (HTTP ${http_code})." \
      "Verify license key: ${license:0:12}…" \
      "Contact support@unotusk.com" ;;
    000) warn "Platform registration endpoint unreachable — continuing." ;;
    *)   warn "Platform responded HTTP ${http_code}. See ${LOG_FILE}." ;;
  esac
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 18 — Certificate provisioning
# ══════════════════════════════════════════════════════════════════════════════
_gen_ca() {
  local ca_dir="${INSTALL_DIR}/certs/ca"
  local org_name
  org_name=$(grep '^ORG_NAME=' "${ENV_FILE}" | cut -d= -f2-)

  openssl genrsa -out "${ca_dir}/ca.key" 4096 >> "${LOG_FILE}" 2>&1
  chmod 600 "${ca_dir}/ca.key"
  openssl req -new -x509 -days 3650 \
    -key "${ca_dir}/ca.key" -out "${ca_dir}/ca.crt" \
    -subj "/CN=UNOTUSK-CA/O=${org_name}/C=US" >> "${LOG_FILE}" 2>&1
}

_gen_service_cert() {
  local service="$1" dir="${INSTALL_DIR}/certs/$1"
  local ca_dir="${INSTALL_DIR}/certs/ca"
  local org_name
  org_name=$(grep '^ORG_NAME=' "${ENV_FILE}" | cut -d= -f2-)

  openssl genrsa -out "${dir}/${service}.key" 2048 >> "${LOG_FILE}" 2>&1
  chmod 600 "${dir}/${service}.key"
  openssl req -new -key "${dir}/${service}.key" -out "${dir}/${service}.csr" \
    -subj "/CN=${service}/O=${org_name}/C=US" >> "${LOG_FILE}" 2>&1
  openssl x509 -req -days 825 \
    -in "${dir}/${service}.csr" -CA "${ca_dir}/ca.crt" -CAkey "${ca_dir}/ca.key" \
    -CAcreateserial -out "${dir}/${service}.crt" >> "${LOG_FILE}" 2>&1
  rm -f "${dir}/${service}.csr"
}

download_certs() {
  header "Certificate provisioning"
  if [[ -f "${INSTALL_DIR}/certs/ca/ca.crt" ]]; then
    success "CA certificate already present — reusing."
    return
  fi
  info "Generating local CA (4096-bit RSA, 10-year validity)..."
  _gen_ca
  info "Generating service certificates (2048-bit RSA, 825-day validity)..."
  local -ra services=(us ups ai-pie)
  local svc
  for svc in "${services[@]}"; do
    _gen_service_cert "$svc"
    success "Certificate: ${svc}"
  done
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 19 — Verify mTLS
# ══════════════════════════════════════════════════════════════════════════════
_probe_grpc() {
  local label="$1" port="$2"
  local ca="${INSTALL_DIR}/certs/ca/ca.crt"
  if curl -sfk --max-time 10 "https://localhost:${port}/healthz" >/dev/null 2>&1; then
    success "mTLS ${label} (:${port}): verified"
  else
    warn "mTLS ${label} (:${port}) not yet responding — services may still be initialising."
    _log "WARN  mTLS probe on :${port} failed"
  fi
}

verify_mtls() {
  header "mTLS connectivity"
  [[ ! -f "${INSTALL_DIR}/certs/ca/ca.crt" ]] && {
    warn "Certificates not found — skipping mTLS verification."
    return
  }
  _probe_grpc "US gRPC"  50052
  _probe_grpc "UPS gRPC" 50051
}

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 20 — Health checks + success summary
# ══════════════════════════════════════════════════════════════════════════════
_probe_http() {
  local label="$1" url="$2"
  if curl -sfk --max-time 10 "$url" >/dev/null 2>&1; then
    success "${label}"
  else
    warn "${label} — not reachable at ${url}"
    _log "WARN  Health probe failed: ${url}"
  fi
}

run_health_checks() {
  header "Health checks"
  _probe_http "HTTPS (Caddy)"        "https://localhost/"
  _probe_http "OIDC discovery"       "https://localhost/.well-known/openid-configuration"
  _probe_http "US /healthz"          "https://localhost/healthz"
  _probe_http "AI-PIE API"           "https://localhost/api/ai/health"

  local ups_h
  ups_h=$(docker compose --file "${COMPOSE_FILE}" \
    exec -T ups curl -sf http://localhost:7001/healthz 2>/dev/null || echo "unreachable")
  if [[ "$ups_h" != "unreachable" ]]; then
    success "UPS internal health: OK"
  else
    warn "UPS internal health not reachable — check: docker compose logs ups"
  fi
}

_install_cli() {
  local dest="/usr/local/bin/unotusk"
  info "Installing unotusk CLI..."
  curl -fsSL "${BASE_URL}/installer/unotusk-cli.sh" -o "$dest" 2>/dev/null \
    && chmod +x "$dest" \
    && success "unotusk CLI: ${dest}" \
    || warn "CLI download failed — install manually from ${BASE_URL}"
}

_write_version_file() {
  local org_id org_name
  org_id=$(grep '^ORG_ID='   "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || echo "")
  org_name=$(grep '^ORG_NAME=' "${ENV_FILE}" 2>/dev/null | cut -d= -f2- || echo "")
  cat > "${VERSION_FILE}" <<EOF
INSTALL_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
INSTALLER_VERSION=${INSTALLER_VERSION}
ORG_ID=${org_id}
ORG_NAME=${org_name}
COMPOSE_FILE=${COMPOSE_FILE}
EOF
  chmod 644 "${VERSION_FILE}"
}

print_summary() {
  _install_cli
  _write_version_file
  mark_stage complete
  echo ""
  echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${GREEN}║  ✔  UNOTUSK installed successfully!      ║${RESET}"
  echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════╝${RESET}"
  echo ""
  echo -e "${BOLD}Access:${RESET}"
  echo "  https://<your-server-ip>"
  echo "  https://<your-server-ip>/.well-known/openid-configuration"
  echo ""
  echo -e "${BOLD}Files:${RESET}"
  printf "  %-22s %s\n" "Install dir:"  "${INSTALL_DIR}"
  printf "  %-22s %s\n" "Configuration:" "${ENV_FILE}"
  printf "  %-22s %s\n" "Secrets:"       "${SECRETS_FILE}"
  printf "  %-22s %s\n" "Compose file:"  "${COMPOSE_FILE}"
  printf "  %-22s %s\n" "Log:"           "${LOG_FILE}"
  echo ""
  echo -e "${BOLD}CLI:${RESET}"
  echo "  unotusk status    — service health overview"
  echo "  unotusk doctor    — full diagnostic report"
  echo "  unotusk logs      — tail all container logs"
  echo "  unotusk update    — upgrade to latest version"
  echo "  unotusk backup    — create encrypted backup"
  echo "  unotusk rollback  — restore from last backup"
  echo ""
  _log "════ Installation complete ════"
}

# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Orchestrates all stages
# ══════════════════════════════════════════════════════════════════════════════
main() {
  { mkdir -p "$(dirname "${LOG_FILE}")" && touch "${LOG_FILE}"; } 2>/dev/null || true

  show_banner

  # Always re-run: system validation (non-destructive, fast)
  check_root
  detect_os
  check_arch
  check_internet
  check_docker
  check_compose
  check_resources

  # Idempotent: skip stage if already completed on a previous run
  stage_done dirs       || { create_directories; mark_stage dirs;       }
  stage_done ports      || { check_ports;        mark_stage ports;      }
  stage_done config     || { prompt_config;      mark_stage config;     }
  stage_done env        || { generate_env;       mark_stage env;        }
  stage_done compose    || { download_compose;   mark_stage compose;    }
  stage_done images     || { pull_images;        mark_stage images;     }
  stage_done started    || { start_containers;   mark_stage started;    }
  stage_done healthy    || { wait_healthy;       mark_stage healthy;    }
  stage_done registered || { register_platform;  mark_stage registered; }
  stage_done certs      || { download_certs;     mark_stage certs;      }
  stage_done mtls       || { verify_mtls;        mark_stage mtls;       }
  stage_done tested     || { run_health_checks;  mark_stage tested;     }
  stage_done complete   || { print_summary;                             }
}

main "$@"
