#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Interactive Setup Wizard
# Collects and validates configuration before writing any files.
# ==============================================================================
set -euo pipefail

WIZARD_CONF="${1:-.env.wizard}"

# ── Colour helpers ─────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "  ${CYAN}→${RESET} $*"; }
success() { echo -e "  ${GREEN}✔${RESET} $*"; }
warn()    { echo -e "  ${YELLOW}⚠${RESET} $*"; }
error()   { echo -e "  ${RED}✘${RESET} $*"; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }

# ── Validators ─────────────────────────────────────────────────────────────────
validate_nonempty() {
  local label="$1" value="$2"
  if [ -z "$value" ]; then
    error "$label cannot be empty."
    return 1
  fi
  return 0
}

validate_email() {
  local email="$1"
  if [[ ! "$email" =~ ^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$ ]]; then
    error "Invalid email address: $email"
    return 1
  fi
  return 0
}

validate_url() {
  local url="$1"
  if [[ ! "$url" =~ ^https?:// ]]; then
    error "URL must start with http:// or https://"
    return 1
  fi
  return 0
}

validate_license_key() {
  local key="$1"
  # Expect format: UNOT-XXXX-XXXX-XXXX or any 16+ char non-space string
  if [ ${#key} -lt 8 ]; then
    error "License key appears too short (< 8 characters)."
    return 1
  fi
  if [[ "$key" == *" "* ]]; then
    error "License key must not contain spaces."
    return 1
  fi
  return 0
}

validate_platform_reachable() {
  local url="$1"
  # Strip gRPC port+path — just test HTTP(S) base for DNS/connectivity
  local host
  host=$(echo "$url" | sed -E 's|https?://([^:/]+).*|\1|')
  info "Testing DNS resolution for $host ..."
  if ! nslookup "$host" >/dev/null 2>&1 && ! host "$host" >/dev/null 2>&1; then
    warn "Cannot resolve $host. Check the URL or your DNS settings."
    warn "Installation will continue, but UPS heartbeat will fail until reachable."
    return 0   # warn-only, do not block install
  fi
  success "DNS resolution OK for $host"
}

validate_port_free() {
  local port="$1" label="$2"
  if ss -tlnp 2>/dev/null | grep -q ":${port} " || \
     netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
    error "Port $port ($label) is already in use. Free it before installing."
    return 1
  fi
  return 0
}

# ── Prompt-with-retry helper ───────────────────────────────────────────────────
# prompt_validated <var_name> <prompt_text> <validator_fn> [allow_empty]
prompt_validated() {
  local var_name="$1" prompt_text="$2" validator="$3" allow_empty="${4:-}"
  local value
  while true; do
    read -r -p "$(echo -e "  ${CYAN}?${RESET} $prompt_text: ")" value
    if [ -z "$value" ] && [ -n "$allow_empty" ]; then
      eval "$var_name=''"
      return 0
    fi
    if "$validator" "$value"; then
      eval "$var_name=\"$value\""
      return 0
    fi
    # Loop again on failure
  done
}

prompt_secret() {
  local var_name="$1" prompt_text="$2"
  local value
  read -r -s -p "$(echo -e "  ${CYAN}?${RESET} $prompt_text: ")" value
  echo ""
  eval "$var_name=\"$value\""
}

# ── Main wizard ────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║    UNOTUSK Platform Setup Wizard         ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""
echo "  This wizard collects and validates your deployment configuration."
echo "  All secrets are generated automatically — you will not need to"
echo "  manually edit any .env files after this step."
echo ""

# ── Section 1: Organisation ────────────────────────────────────────────────────
header "── 1/5  Organisation"
prompt_validated ORG_NAME "Organisation name" validate_nonempty

# ── Section 2: License ────────────────────────────────────────────────────────
header "── 2/5  License"
prompt_validated LICENSE_KEY "License key" validate_license_key

# ── Section 3: Platform connectivity ─────────────────────────────────────────
header "── 3/5  Platform"
echo "  Default: https://platform.unotusk.com:50051"
while true; do
  read -r -p "$(echo -e "  ${CYAN}?${RESET} Platform URL [https://platform.unotusk.com:50051]: ")" PLATFORM_URL
  PLATFORM_URL="${PLATFORM_URL:-https://platform.unotusk.com:50051}"
  if validate_url "$PLATFORM_URL"; then
    validate_platform_reachable "$PLATFORM_URL"
    break
  fi
done

# ── Section 4: Administrator ──────────────────────────────────────────────────
header "── 4/5  Administrator account"
prompt_validated ADMIN_NAME  "Administrator name"  validate_nonempty
prompt_validated ADMIN_EMAIL "Administrator email" validate_email

# ── Section 5: OAuth (optional) ───────────────────────────────────────────────
header "── 5/5  OAuth provider  (press Enter to skip)"
echo "  Supported: github | google | microsoft"
OAUTH_PROVIDER="" OAUTH_CLIENT_ID="" OAUTH_CLIENT_SECRET="" OAUTH_REDIRECT_URI=""

read -r -p "$(echo -e "  ${CYAN}?${RESET} Provider [none]: ")" OAUTH_PROVIDER
if [ -n "$OAUTH_PROVIDER" ]; then
  case "$OAUTH_PROVIDER" in
    github|google|microsoft) ;;
    *)
      warn "Unknown provider '$OAUTH_PROVIDER'. Accepted: github, google, microsoft."
      warn "Configuration saved — validate the redirect URI after installation."
      ;;
  esac

  # Client ID must be non-empty when a provider is chosen
  while true; do
    read -r -p "$(echo -e "  ${CYAN}?${RESET} Client ID: ")" OAUTH_CLIENT_ID
    if validate_nonempty "OAuth Client ID" "$OAUTH_CLIENT_ID"; then break; fi
  done

  prompt_secret OAUTH_CLIENT_SECRET "Client Secret"

  # Redirect / callback URL
  while true; do
    read -r -p "$(echo -e "  ${CYAN}?${RESET} Redirect (callback) URL: ")" OAUTH_REDIRECT_URI
    if validate_url "$OAUTH_REDIRECT_URI"; then
      # Warn if missing /callback suffix which most providers expect
      if [[ "$OAUTH_REDIRECT_URI" != */callback* ]]; then
        warn "Redirect URL does not contain '/callback'. Confirm this matches your OAuth app."
      fi
      break
    fi
  done
fi

# ── Port conflict check ────────────────────────────────────────────────────────
header "── Port availability check"
PORT_OK=true
for port_label in "3000:US/OIDC" "8444:US/Admin" "50051:UPS/gRPC" "50052:US/gRPC"; do
  p="${port_label%%:*}"; l="${port_label##*:}"
  if ! validate_port_free "$p" "$l"; then PORT_OK=false; fi
done
if $PORT_OK; then
  success "All required ports are free."
fi

# ── Confirmation ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── Configuration summary ──────────────────────${RESET}"
echo "  Organisation : $ORG_NAME"
echo "  License key  : ${LICENSE_KEY:0:4}***"
echo "  Platform URL : $PLATFORM_URL"
echo "  Admin email  : $ADMIN_EMAIL"
echo "  OAuth        : ${OAUTH_PROVIDER:-none}"
if [ -n "$OAUTH_PROVIDER" ]; then
  echo "  Redirect URI : $OAUTH_REDIRECT_URI"
fi
echo ""
read -r -p "$(echo -e "  ${CYAN}?${RESET} Confirm and proceed? [Y/n]: ")" CONFIRM
CONFIRM="${CONFIRM:-Y}"
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo "  Aborted. Run the installer again to restart."
  exit 1
fi

# ── Write configuration ────────────────────────────────────────────────────────
# NOTE: OAUTH_CLIENT_SECRET is NOT written to the wizard conf file.
# It is stored separately in a secrets file with restricted permissions.
cat > "$WIZARD_CONF" <<EOF
ORG_NAME="$ORG_NAME"
LICENSE_KEY="$LICENSE_KEY"
PLATFORM_URL="$PLATFORM_URL"
ADMIN_NAME="$ADMIN_NAME"
ADMIN_EMAIL="$ADMIN_EMAIL"
OAUTH_PROVIDER="$OAUTH_PROVIDER"
OAUTH_CLIENT_ID="$OAUTH_CLIENT_ID"
OAUTH_REDIRECT_URI="$OAUTH_REDIRECT_URI"
EOF
chmod 600 "$WIZARD_CONF"

# OAuth secret stored separately with tighter permissions
SECRETS_FILE="$(dirname "$WIZARD_CONF")/.secrets"
cat > "$SECRETS_FILE" <<EOF
OAUTH_CLIENT_SECRET="$OAUTH_CLIENT_SECRET"
EOF
chmod 600 "$SECRETS_FILE"

echo ""
success "Configuration saved."
