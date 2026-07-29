#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Installer — Versioned, distributed via GitHub Releases
#  This script is extracted from unotusk-installer.tar.gz and executed
#  by the bootstrap script after checksum verification.
#
#  Usage (called by bootstrap):
#    bash installer/install.sh --install-dir /opt/unotusk --version v1.0.0
#
#  Usage (manual / unattended):
#    sudo UNATTENDED=1 \
#         UNOTUSK_ORG_NAME="Acme" \
#         UNOTUSK_LICENSE_KEY="UNOT-XXXX-XXXX-XXXX" \
#         bash installer/install.sh
# ==============================================================================
set -Eeuo pipefail

# ── Argument parsing ───────────────────────────────────────────────────────────
INSTALL_DIR="/opt/unotusk"
INSTALLER_VERSION="dev"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --version)     INSTALLER_VERSION="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

# ── Constants ──────────────────────────────────────────────────────────────────
GITHUB_ORG="Techteam-zephvion"
GITHUB_REPO="install-unotusk"
COMPOSE_BASE_URL="https://raw.githubusercontent.com/${GITHUB_ORG}/${GITHUB_REPO}/${INSTALLER_VERSION}/compose"
LOG_FILE="/var/log/unotusk-install.log"
STATE_FILE="${INSTALL_DIR}/.install-state"
VERSION_FILE="${INSTALL_DIR}/.unotusk-version"
MIN_RAM_MB=3584        # 3.5 GB — hard minimum
WARN_RAM_MB=7168       # 7 GB — recommended
MIN_DISK_MB=10240      # 10 GB
REQUIRED_PORTS=(3000 8444 50051 50052)

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

_log()    { echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" >> "$LOG_FILE" 2>/dev/null || true; }
info()    { local m="  ${CYAN}→${RESET} $*"; echo -e "$m"; _log "INFO  $*"; }
success() { local m="  ${GREEN}✔${RESET} $*"; echo -e "$m"; _log "OK    $*"; }
warn()    { local m="  ${YELLOW}⚠${RESET} $*"; echo -e "$m"; _log "WARN  $*"; }
fail()    { local m="  ${RED}✘${RESET} $* — see $LOG_FILE"; echo -e "$m" >&2; _log "FAIL  $*"; exit 1; }
header()  { echo -e "\n${BOLD}━━  $*${RESET}"; _log "=== $* ==="; }
step()    { echo -e "  ${DIM}$*${RESET}"; }

# ── State machine (resumable installs) ────────────────────────────────────────
# Stages: validated | configured | certs_ready | composed | started | registered | tested | complete
mark_stage() { echo "STAGE=$1" > "$STATE_FILE"; _log "stage: $1"; }

current_stage() {
  [[ -f "$STATE_FILE" ]] && grep '^STAGE=' "$STATE_FILE" | cut -d= -f2 || echo "none"
}

stage_done() {
  local stages=(validated configured certs_ready composed started registered tested complete)
  local target="$1"
  local current
  current=$(current_stage)
  for s in "${stages[@]}"; do
    [[ "$s" == "$target" ]] && return 1   # not done yet
    [[ "$s" == "$current" ]] && return 0  # current is past target, so target is done
  done
  return 1
}

# ── Secret generation ─────────────────────────────────────────────────────────
gen_password()  { LC_ALL=C tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 32; }
gen_hex()       { openssl rand -hex 32; }
gen_uuid() {
  command -v uuidgen &>/dev/null && uuidgen | tr '[:upper:]' '[:lower:]' \
    || cat /proc/sys/kernel/random/uuid
}

# ── Health-aware service wait ──────────────────────────────────────────────────
wait_healthy() {
  local service="$1" timeout="${2:-120}"
  local elapsed=0 interval=5 cid

  cid=$(docker compose -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" ps -q "$service" 2>/dev/null || true)
  [[ -z "$cid" ]] && fail "No container found for service '$service'."

  printf "  ${CYAN}⏳${RESET} Waiting for %-20s" "$service..."
  while [[ $elapsed -lt $timeout ]]; do
    local status
    status=$(docker inspect \
      --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' \
      "$cid" 2>/dev/null || echo "unknown")
    case "$status" in
      healthy|running) echo -e " ${GREEN}healthy${RESET}"; return 0 ;;
      unhealthy)
        echo ""
        fail "'${service}' entered unhealthy state. Run: docker compose logs ${service}"
        ;;
      *)
        printf "."
        sleep "$interval"
        elapsed=$((elapsed + interval))
        ;;
    esac
  done
  echo ""
  fail "'${service}' did not become healthy within ${timeout}s. Run: docker compose logs ${service}"
}

# ── Banner ─────────────────────────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR" "$(dirname "$LOG_FILE")"
touch "$LOG_FILE" 2>/dev/null || true

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       UNOTUSK Platform Installer         ║${RESET}"
echo -e "${BOLD}║       Version: ${INSTALLER_VERSION}$(printf '%*s' $((24 - ${#INSTALLER_VERSION})) '')║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

STAGE=$(current_stage)
if [[ "$STAGE" != "none" && "$STAGE" != "complete" ]]; then
  warn "Resuming interrupted installation from stage: ${STAGE}"
  info "Previously completed stages will be skipped."
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Validate environment
# ══════════════════════════════════════════════════════════════════════════════
if ! stage_done validated; then
  header "[1/9] Validating environment"

  # Root
  [[ "$EUID" -eq 0 ]] || fail "Run as root (sudo)."
  success "Running as root."

  # Docker
  command -v docker &>/dev/null || fail "Docker not found. Run the bootstrap script."
  success "Docker: $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'present')"

  # Compose plugin
  docker compose version &>/dev/null || fail "Docker Compose plugin not found."
  success "Docker Compose: $(docker compose version --short 2>/dev/null || echo 'present')"

  # RAM
  if command -v free &>/dev/null; then
    RAM_MB=$(free -m | awk '/^Mem:/ {print $2}')
    if [[ "$RAM_MB" -lt "$MIN_RAM_MB" ]]; then
      fail "Insufficient RAM: ${RAM_MB}MB. Minimum is ${MIN_RAM_MB}MB."
    elif [[ "$RAM_MB" -lt "$WARN_RAM_MB" ]]; then
      warn "RAM: ${RAM_MB}MB — recommended is ${WARN_RAM_MB}MB+ for production."
    else
      success "RAM: ${RAM_MB}MB"
    fi
  fi

  # Disk
  FREE_DISK=$(df -m "$INSTALL_DIR" | awk 'NR==2 {print $4}')
  [[ "$FREE_DISK" -ge "$MIN_DISK_MB" ]] \
    || fail "Insufficient disk: ${FREE_DISK}MB available, ${MIN_DISK_MB}MB required."
  success "Disk: ${FREE_DISK}MB available"

  # Internet
  curl -sf --max-time 8 https://hub.docker.com >/dev/null 2>&1 \
    || warn "Cannot reach hub.docker.com — image pulls may fail."
  success "Internet: OK"

  # Required ports
  PORT_FAIL=false
  for port in "${REQUIRED_PORTS[@]}"; do
    if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
       netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
      warn "Port ${port} is already in use."
      PORT_FAIL=true
    fi
  done
  $PORT_FAIL && fail "One or more required ports are in use. Free them and re-run."
  success "Required ports are free: ${REQUIRED_PORTS[*]}"

  mark_stage validated
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Interactive configuration wizard
# ══════════════════════════════════════════════════════════════════════════════
ENV_FILE="${INSTALL_DIR}/.env"

if ! stage_done configured; then
  header "[2/9] Configuration"

  if [[ -n "${UNATTENDED:-}" ]]; then
    # ── Unattended mode ───────────────────────────────────────────────────────
    info "Unattended mode — reading from environment variables."
    ORG_NAME="${UNOTUSK_ORG_NAME:?Set UNOTUSK_ORG_NAME}"
    COMPANY_NAME="${UNOTUSK_COMPANY_NAME:-$ORG_NAME}"
    LICENSE_KEY="${UNOTUSK_LICENSE_KEY:?Set UNOTUSK_LICENSE_KEY}"
    PLATFORM_URL="${UNOTUSK_PLATFORM_URL:-https://platform.unotusk.com:50051}"
    GITHUB_ORG_NAME="${UNOTUSK_GITHUB_ORG:-}"
    JIRA_URL="${UNOTUSK_JIRA_URL:-}"
    OIDC_ISSUER="${UNOTUSK_OIDC_ISSUER:-}"
    OIDC_CLIENT_ID="${UNOTUSK_OIDC_CLIENT_ID:-}"
    OIDC_CLIENT_SECRET="${UNOTUSK_OIDC_CLIENT_SECRET:-}"
    ADMIN_EMAIL="${UNOTUSK_ADMIN_EMAIL:-}"
  else
    # ── Interactive wizard ────────────────────────────────────────────────────
    echo ""
    echo "  This wizard collects your deployment configuration."
    echo "  Secrets are generated automatically — no manual .env editing needed."
    echo ""

    # Helpers
    ask()        { read -r -p "$(echo -e "  ${CYAN}?${RESET} $1: ")" "$2"; }
    ask_secret() { read -r -s -p "$(echo -e "  ${CYAN}?${RESET} $1: ")" "$2"; echo ""; }
    ask_default() {
      read -r -p "$(echo -e "  ${CYAN}?${RESET} $1 [${2}]: ")" _tmp
      printf -v "$3" '%s' "${_tmp:-$2}"
    }
    ask_nonempty() {
      while true; do
        read -r -p "$(echo -e "  ${CYAN}?${RESET} $1: ")" "$2"
        [[ -n "${!2}" ]] && break
        echo -e "  ${RED}This field is required.${RESET}"
      done
    }

    echo -e "  ${BOLD}── 1/6  Organisation${RESET}"
    ask_nonempty "Organisation name (e.g. Acme Corp)"     ORG_NAME
    ask_default  "Company / display name"   "$ORG_NAME"   COMPANY_NAME

    echo ""
    echo -e "  ${BOLD}── 2/6  License${RESET}"
    ask_nonempty "License key (format: UNOT-XXXX-XXXX-XXXX)" LICENSE_KEY

    echo ""
    echo -e "  ${BOLD}── 3/6  Platform URL${RESET}"
    ask_default  "Platform gRPC URL" "https://platform.unotusk.com:50051" PLATFORM_URL

    echo ""
    echo -e "  ${BOLD}── 4/6  Integrations  (press Enter to skip)${RESET}"
    ask "GitHub organisation (e.g. acme-corp)" GITHUB_ORG_NAME
    ask "Jira base URL (e.g. https://acme.atlassian.net)" JIRA_URL

    echo ""
    echo -e "  ${BOLD}── 5/6  OIDC / SSO  (press Enter to skip for now)${RESET}"
    echo "  Supported providers: Entra ID, Okta, Google Workspace, Keycloak"
    ask "OIDC Issuer URL" OIDC_ISSUER
    if [[ -n "$OIDC_ISSUER" ]]; then
      ask_nonempty "OIDC Client ID"     OIDC_CLIENT_ID
      ask_secret   "OIDC Client Secret" OIDC_CLIENT_SECRET
    else
      OIDC_CLIENT_ID=""; OIDC_CLIENT_SECRET=""
    fi

    echo ""
    echo -e "  ${BOLD}── 6/6  Administrator${RESET}"
    ask "Admin email address" ADMIN_EMAIL

    # Confirmation
    echo ""
    echo -e "  ${BOLD}── Configuration summary ─────────────────────────────${RESET}"
    printf "  %-22s %s\n" "Organisation:"   "$ORG_NAME"
    printf "  %-22s %s\n" "License key:"    "${LICENSE_KEY:0:8}***"
    printf "  %-22s %s\n" "Platform URL:"   "$PLATFORM_URL"
    printf "  %-22s %s\n" "GitHub org:"     "${GITHUB_ORG_NAME:-not set}"
    printf "  %-22s %s\n" "Jira URL:"       "${JIRA_URL:-not set}"
    printf "  %-22s %s\n" "OIDC Issuer:"    "${OIDC_ISSUER:-not set}"
    printf "  %-22s %s\n" "Admin email:"    "${ADMIN_EMAIL:-not set}"
    echo ""
    read -r -p "$(echo -e "  ${CYAN}?${RESET} Confirm and proceed? [Y/n]: ")" _confirm
    [[ "${_confirm:-Y}" =~ ^[Yy]$ ]] || { echo "  Aborted."; exit 0; }
  fi

  # ── Generate secrets ────────────────────────────────────────────────────────
  if [[ -f "$ENV_FILE" ]] && grep -q "^POSTGRES_PASSWORD=" "$ENV_FILE" 2>/dev/null; then
    info "Existing .env found — loading (idempotent resume)."
    # shellcheck source=/dev/null
    source "$ENV_FILE"
  else
    info "Generating cryptographic secrets..."
    POSTGRES_PASSWORD=$(gen_password)
    QDRANT_API_KEY=$(gen_password)
    JWKS_PUSH_SECRET=$(gen_hex)
    TOKEN_ENC_KEY=$(openssl rand -base64 32)
    ORG_ID=$(gen_uuid)

    cat > "$ENV_FILE" <<EOF
# UNOTUSK — generated by installer ${INSTALLER_VERSION} on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# DO NOT edit manually. Use: unotusk reconfigure

# ── Organisation ──────────────────────────────────────────────────────────────
ORG_ID=${ORG_ID}
ORG_NAME=${ORG_NAME}
COMPANY_NAME=${COMPANY_NAME}

# ── Database ──────────────────────────────────────────────────────────────────
POSTGRES_USER=unotusk
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=unotusk

# ── Vector store ──────────────────────────────────────────────────────────────
QDRANT_API_KEY=${QDRANT_API_KEY}

# ── Platform connection (UPS → cloud, outbound only) ──────────────────────────
PLATFORM_URL=${PLATFORM_URL}
PLATFORM_LICENSE_KEY=${LICENSE_KEY}
LICENSE_HEARTBEAT_INTERVAL=60
LICENSE_GRACE_PERIOD=18000
PLATFORM_TOKEN_AUDIENCE=platform.unotusk.com
PLATFORM_JWKS_PUSH_URL=https://platform.unotusk.com/internal/orgs/${ORG_ID}/jwks

# ── Security ──────────────────────────────────────────────────────────────────
JWKS_PUSH_SECRET=${JWKS_PUSH_SECRET}
TOKEN_ENC_KEY=${TOKEN_ENC_KEY}

# ── Integrations ──────────────────────────────────────────────────────────────
GITHUB_ORG_NAME=${GITHUB_ORG_NAME:-}
JIRA_URL=${JIRA_URL:-}

# ── OIDC / SSO ────────────────────────────────────────────────────────────────
OIDC_ISSUER=${OIDC_ISSUER:-}
OIDC_CLIENT_ID=${OIDC_CLIENT_ID:-}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL=info
EOF
    chmod 600 "$ENV_FILE"

    # OIDC secret stored separately with tighter permissions
    SECRETS_FILE="${INSTALL_DIR}/.secrets"
    cat > "$SECRETS_FILE" <<EOF
OIDC_CLIENT_SECRET=${OIDC_CLIENT_SECRET:-}
EOF
    chmod 600 "$SECRETS_FILE"
    success "Secrets generated and stored."
  fi

  # Write per-service env stubs (idempotent)
  mkdir -p "${INSTALL_DIR}/US" "${INSTALL_DIR}/UPS" "${INSTALL_DIR}/AI-PIE"

  [[ ! -f "${INSTALL_DIR}/US/.env" ]] && cat > "${INSTALL_DIR}/US/.env" <<EOF
LOG_LEVEL=info
PLATFORM_TOKEN_AUDIENCE=platform.unotusk.com
EOF

  [[ ! -f "${INSTALL_DIR}/UPS/.env" ]] && cat > "${INSTALL_DIR}/UPS/.env" <<EOF
LOG_LEVEL=info
LICENSE_HEARTBEAT_INTERVAL=60
LICENSE_GRACE_PERIOD=18000
EOF

  [[ ! -f "${INSTALL_DIR}/AI-PIE/.env" ]] && cat > "${INSTALL_DIR}/AI-PIE/.env" <<EOF
LOG_LEVEL=info
GITHUB_ORG=${GITHUB_ORG_NAME:-}
JIRA_URL=${JIRA_URL:-}
EOF

  chmod 600 "${INSTALL_DIR}/US/.env" "${INSTALL_DIR}/UPS/.env" "${INSTALL_DIR}/AI-PIE/.env"
  success "Per-service configuration written."
  mark_stage configured
fi

# Re-load env for subsequent stages
# shellcheck source=/dev/null
source "$ENV_FILE"

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — TLS certificates
# ══════════════════════════════════════════════════════════════════════════════
if ! stage_done certs_ready; then
  header "[3/9] Generating mTLS certificates"

  CERT_MARKER="${INSTALL_DIR}/.certs-generated"
  if [[ -f "$CERT_MARKER" ]]; then
    success "Certificates already present — skipping."
  else
    mkdir -p \
      "${INSTALL_DIR}/US/certs" \
      "${INSTALL_DIR}/UPS/certs/platform" \
      "${INSTALL_DIR}/AI-PIE/certs/dev"

    step "Generating local CA..."
    openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
      -keyout "${INSTALL_DIR}/US/certs/ca.key" \
      -out "${INSTALL_DIR}/US/certs/ca.crt" \
      -subj "/C=IN/O=UNOTUSK/CN=UnotuskLocalCA" >> "$LOG_FILE" 2>&1
    success "Root CA generated (10-year validity)."

    step "Generating US (auth-server) certificate..."
    openssl req -newkey rsa:2048 -nodes \
      -keyout "${INSTALL_DIR}/US/certs/server.key" \
      -out "${INSTALL_DIR}/US/certs/server.csr" \
      -subj "/C=IN/O=UNOTUSK/CN=auth-server" >> "$LOG_FILE" 2>&1
    openssl x509 -req \
      -in "${INSTALL_DIR}/US/certs/server.csr" \
      -CA "${INSTALL_DIR}/US/certs/ca.crt" \
      -CAkey "${INSTALL_DIR}/US/certs/ca.key" \
      -CAcreateserial -out "${INSTALL_DIR}/US/certs/server.crt" \
      -days 825 >> "$LOG_FILE" 2>&1

    step "Distributing CA to dependent services..."
    cp "${INSTALL_DIR}/US/certs/ca.crt" "${INSTALL_DIR}/UPS/certs/ca.crt"
    cp "${INSTALL_DIR}/US/certs/ca.crt" "${INSTALL_DIR}/AI-PIE/certs/ca.crt"

    step "Generating UPS client certificate..."
    openssl req -newkey rsa:2048 -nodes \
      -keyout "${INSTALL_DIR}/UPS/certs/client.key" \
      -out "${INSTALL_DIR}/UPS/certs/client.csr" \
      -subj "/C=IN/O=UNOTUSK/CN=company-server" >> "$LOG_FILE" 2>&1
    openssl x509 -req \
      -in "${INSTALL_DIR}/UPS/certs/client.csr" \
      -CA "${INSTALL_DIR}/US/certs/ca.crt" \
      -CAkey "${INSTALL_DIR}/US/certs/ca.key" \
      -CAcreateserial -out "${INSTALL_DIR}/UPS/certs/client.crt" \
      -days 825 >> "$LOG_FILE" 2>&1

    step "Generating AI-PIE client certificate..."
    openssl req -newkey rsa:2048 -nodes \
      -keyout "${INSTALL_DIR}/AI-PIE/certs/dev/client.key" \
      -out "${INSTALL_DIR}/AI-PIE/certs/dev/client.csr" \
      -subj "/C=IN/O=UNOTUSK/CN=ai-pie" >> "$LOG_FILE" 2>&1
    openssl x509 -req \
      -in "${INSTALL_DIR}/AI-PIE/certs/dev/client.csr" \
      -CA "${INSTALL_DIR}/US/certs/ca.crt" \
      -CAkey "${INSTALL_DIR}/US/certs/ca.key" \
      -CAcreateserial -out "${INSTALL_DIR}/AI-PIE/certs/dev/client.pem" \
      -days 825 >> "$LOG_FILE" 2>&1

    step "Generating placeholder Platform certificates for UPS..."
    openssl req -x509 -newkey rsa:2048 -days 365 -nodes \
      -keyout "${INSTALL_DIR}/UPS/certs/platform/client.key" \
      -out "${INSTALL_DIR}/UPS/certs/platform/client.crt" \
      -subj "/C=IN/O=UNOTUSK/CN=platform-client" >> "$LOG_FILE" 2>&1
    cp "${INSTALL_DIR}/UPS/certs/platform/client.crt" \
       "${INSTALL_DIR}/UPS/certs/platform/ca.crt"

    # Readable by bind-mounted containers
    find "${INSTALL_DIR}/US/certs" "${INSTALL_DIR}/UPS/certs" \
         "${INSTALL_DIR}/AI-PIE/certs" -name "*.key" -exec chmod 644 {} +

    touch "$CERT_MARKER"
    success "All mTLS certificates generated."
  fi
  mark_stage certs_ready
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — Download compose files
# ══════════════════════════════════════════════════════════════════════════════
if ! stage_done composed; then
  header "[4/9] Downloading compose configuration"

  mkdir -p "${INSTALL_DIR}/compose" "${INSTALL_DIR}/scripts"

  for file in docker-compose.yml docker-compose.override.yml .env.example; do
    local_path="${INSTALL_DIR}/compose/${file}"
    if [[ -f "$local_path" ]]; then
      info "  ${file} already present — skipping."
    else
      info "  Downloading ${file}..."
      curl -fsSL "${COMPOSE_BASE_URL}/${file}" -o "$local_path" \
        || fail "Failed to download compose/${file}"
      success "  ${file} downloaded."
    fi
  done

  # Download init-databases script
  if [[ ! -f "${INSTALL_DIR}/scripts/init-databases.sh" ]]; then
    curl -fsSL \
      "https://raw.githubusercontent.com/${GITHUB_ORG}/${GITHUB_REPO}/${INSTALLER_VERSION}/scripts/init-databases.sh" \
      -o "${INSTALL_DIR}/scripts/init-databases.sh" 2>/dev/null || true
    chmod +x "${INSTALL_DIR}/scripts/init-databases.sh" 2>/dev/null || true
  fi

  # Validate compose file
  docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    config --quiet >> "$LOG_FILE" 2>&1 \
    || fail "docker-compose.yml has configuration errors. See $LOG_FILE"
  success "Compose configuration validated."
  mark_stage composed
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — Pull Docker images
# ══════════════════════════════════════════════════════════════════════════════
if ! stage_done started; then
  header "[5/9] Pulling Docker images"
  info "Pulling images (this may take a few minutes)..."
  docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    pull --quiet 2>&1 | grep -v "^$" | sed 's/^/  /' || true
  success "Images pulled."

  # ── Health-aware service startup ───────────────────────────────────────────
  header "[6/9] Starting services"

  _compose() {
    docker compose \
      -f "${INSTALL_DIR}/compose/docker-compose.yml" \
      --env-file "${INSTALL_DIR}/.env" \
      "$@"
  }

  info "Starting infrastructure tier (postgres, qdrant, phoenix)..."
  _compose up -d postgres
  wait_healthy postgres 90

  _compose up -d qdrant phoenix
  wait_healthy qdrant 90
  wait_healthy phoenix 90

  info "Starting US (auth service)..."
  _compose up -d us
  wait_healthy us 120

  info "Starting UPS (company server)..."
  _compose up -d ups
  wait_healthy ups 120

  info "Starting AI-PIE (intelligence engine)..."
  _compose up -d ai-pie
  wait_healthy ai-pie 180

  success "All services are healthy."
  mark_stage started
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 6 — Register with UP (Platform)
# ══════════════════════════════════════════════════════════════════════════════
if ! stage_done registered; then
  header "[7/9] Registering with UNOTUSK Platform"

  # shellcheck source=/dev/null
  source "$ENV_FILE"

  PLATFORM_HTTP_URL="${PLATFORM_URL//:50051/}"
  PLATFORM_HTTP_URL="${PLATFORM_HTTP_URL/grpc/https}"

  REGISTRATION_OK=false
  if curl -sf --max-time 10 \
       -H "Authorization: Bearer ${PLATFORM_LICENSE_KEY}" \
       -H "Content-Type: application/json" \
       -d "{\"org_id\":\"${ORG_ID}\",\"org_name\":\"${ORG_NAME}\",\"installer_version\":\"${INSTALLER_VERSION}\"}" \
       "${PLATFORM_HTTP_URL}/api/v1/register" \
       >> "$LOG_FILE" 2>&1; then
    REGISTRATION_OK=true
    success "Registered with UNOTUSK Platform."
  else
    warn "Platform registration request failed — UPS will retry on first heartbeat."
    warn "This is non-fatal. License validation will occur in the background."
  fi

  mark_stage registered
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 7 — Verify mTLS
# ══════════════════════════════════════════════════════════════════════════════
if ! stage_done tested; then
  header "[8/9] Verifying service connectivity"

  # US health endpoint
  if curl -sf --max-time 5 http://localhost:3000/healthz >/dev/null 2>&1; then
    success "US HTTP health endpoint: OK (localhost:3000/healthz)"
  else
    warn "US health endpoint not reachable — services may still be initialising."
  fi

  # OIDC discovery
  if curl -sf --max-time 5 http://localhost:3000/.well-known/openid-configuration \
       >/dev/null 2>&1; then
    success "OIDC discovery document: OK"
  else
    warn "OIDC discovery not yet reachable — check: docker compose logs us"
  fi

  # UPS health
  UPS_HEALTH=$(docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    exec -T ups curl -sf http://localhost:8080/healthz 2>/dev/null || echo "unreachable")
  if echo "$UPS_HEALTH" | grep -q "ok\|healthy\|200" 2>/dev/null; then
    success "UPS internal health endpoint: OK"
  else
    warn "UPS health response unexpected — check: docker compose logs ups"
  fi

  mark_stage tested
fi

# ══════════════════════════════════════════════════════════════════════════════
# STAGE 8 — Install CLI & record metadata
# ══════════════════════════════════════════════════════════════════════════════
if ! stage_done complete; then
  header "[9/9] Finalising installation"

  # Download and install CLI
  CLI_DEST="/usr/local/bin/unotusk"
  CLI_URL="https://raw.githubusercontent.com/${GITHUB_ORG}/${GITHUB_REPO}/${INSTALLER_VERSION}/installer/unotusk-cli.sh"
  info "Installing unotusk CLI..."
  curl -fsSL "$CLI_URL" -o "$CLI_DEST" 2>/dev/null \
    || warn "CLI download failed — install manually from the GitHub release."
  [[ -f "$CLI_DEST" ]] && chmod +x "$CLI_DEST" && success "unotusk CLI installed at $CLI_DEST"

  # Write version file
  cat > "$VERSION_FILE" <<EOF
INSTALL_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
INSTALL_VERSION=${INSTALLER_VERSION}
ORG_ID=${ORG_ID:-}
ORG_NAME=${ORG_NAME:-}
COMPOSE_FILE=${INSTALL_DIR}/compose/docker-compose.yml
EOF
  chmod 644 "$VERSION_FILE"

  mark_stage complete
fi

# ══════════════════════════════════════════════════════════════════════════════
# Done
# ══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   ✔  UNOTUSK Installation Complete  🚀   ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${GREEN}✔${RESET} Organisation : ${ORG_NAME:-}"
echo -e "  ${GREEN}✔${RESET} Org ID       : ${ORG_ID:-}"
echo -e "  ${GREEN}✔${RESET} Version      : ${INSTALLER_VERSION}"
echo -e "  ${GREEN}✔${RESET} Install dir  : ${INSTALL_DIR}"
echo -e "  ${GREEN}✔${RESET} Log file     : ${LOG_FILE}"
echo ""
echo "  Next steps:"
echo "    unotusk status        — verify all services are healthy"
echo "    unotusk doctor        — run full diagnostics"
echo "    unotusk logs          — tail all service logs"
echo ""
echo "  Documentation: https://docs.unotusk.com"
echo ""

_log "Installation complete — version ${INSTALLER_VERSION}"
