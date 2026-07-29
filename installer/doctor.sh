#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Doctor — System Diagnostics
#  Usage: unotusk doctor
# ==============================================================================
set -Eeuo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
LOG_FILE="/var/log/unotusk-install.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

pass()  { echo -e "  ${GREEN}✔${RESET}  $*"; }
fail_c(){ echo -e "  ${RED}✘${RESET}  $*"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn()  { echo -e "  ${YELLOW}⚠${RESET}  $*"; WARN_COUNT=$((WARN_COUNT + 1)); }
info()  { echo -e "  ${CYAN}→${RESET}  $*"; }
header(){ echo -e "\n${BOLD}── $* ──────────────────────────────────────${RESET}"; }

FAIL_COUNT=0
WARN_COUNT=0

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       UNOTUSK System Diagnostics         ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

_compose() {
  docker compose \
    -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" \
    "$@"
}

# ── Installation ───────────────────────────────────────────────────────────────
header "Installation"
if [[ -d "$INSTALL_DIR" ]]; then
  pass "Install directory exists: $INSTALL_DIR"
else
  fail_c "Install directory missing: $INSTALL_DIR"
fi

VERSION_FILE="${INSTALL_DIR}/.unotusk-version"
if [[ -f "$VERSION_FILE" ]]; then
  VERSION=$(grep '^INSTALL_VERSION=' "$VERSION_FILE" | cut -d= -f2 || echo "?")
  INSTALL_DATE=$(grep '^INSTALL_DATE=' "$VERSION_FILE" | cut -d= -f2 || echo "?")
  pass "Version: $VERSION (installed: $INSTALL_DATE)"
else
  fail_c "Version file missing — installation may be incomplete."
fi

# ── Docker ────────────────────────────────────────────────────────────────────
header "Docker"
if command -v docker &>/dev/null; then
  DOCKER_VER=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")
  pass "Docker Engine: $DOCKER_VER"
else
  fail_c "Docker not found."
fi

if docker compose version &>/dev/null; then
  pass "Docker Compose plugin: $(docker compose version --short 2>/dev/null || echo 'present')"
else
  fail_c "Docker Compose plugin not found."
fi

# ── Service health ─────────────────────────────────────────────────────────────
header "Service health"
SERVICES=(postgres qdrant phoenix us ups ai-pie)
for svc in "${SERVICES[@]}"; do
  STATUS=$(_compose ps "$svc" --format "{{.State}}" 2>/dev/null || echo "not_found")
  HEALTH=$(_compose ps "$svc" --format "{{.Health}}" 2>/dev/null || echo "")

  case "$STATUS" in
    running)
      case "$HEALTH" in
        healthy|"") pass "$svc: running" ;;
        unhealthy)  fail_c "$svc: UNHEALTHY — run: docker compose logs $svc" ;;
        starting)   warn "$svc: starting (health check pending)" ;;
        *)          pass "$svc: running (no healthcheck)" ;;
      esac
      ;;
    exited|stopped) fail_c "$svc: stopped — run: unotusk start" ;;
    not_found)      fail_c "$svc: container not found" ;;
    *)              warn "$svc: unknown state ($STATUS)" ;;
  esac
done

# ── HTTP endpoints ────────────────────────────────────────────────────────────
header "HTTP endpoints"
HTTP_CHECKS=(
  "US health:         http://localhost:3000/healthz"
  "OIDC discovery:    http://localhost:3000/.well-known/openid-configuration"
  "OIDC JWKS:         http://localhost:3000/.well-known/jwks.json"
)
for check in "${HTTP_CHECKS[@]}"; do
  label="${check%%:*}"
  url=$(echo "$check" | awk '{print $NF}')
  HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
  if [[ "$HTTP_CODE" == "200" ]]; then
    pass "$label — HTTP $HTTP_CODE"
  else
    fail_c "$label — HTTP $HTTP_CODE (expected 200)"
  fi
done

# ── Ports ─────────────────────────────────────────────────────────────────────
header "Port bindings"
REQUIRED_PORTS=(3000 8444 50051 50052)
for port in "${REQUIRED_PORTS[@]}"; do
  if ss -tlnp 2>/dev/null | grep -q ":${port} "; then
    pass "Port $port is bound (UNOTUSK service listening)"
  else
    warn "Port $port not bound — service may be down or not yet started."
  fi
done

# ── Certificates ──────────────────────────────────────────────────────────────
header "Certificates"
CERT_PATHS=(
  "${INSTALL_DIR}/US/certs/ca.crt"
  "${INSTALL_DIR}/US/certs/server.crt"
  "${INSTALL_DIR}/UPS/certs/client.crt"
  "${INSTALL_DIR}/AI-PIE/certs/dev/client.pem"
)
for cert in "${CERT_PATHS[@]}"; do
  if [[ -f "$cert" ]]; then
    EXPIRY=$(openssl x509 -in "$cert" -noout -enddate 2>/dev/null | cut -d= -f2 || echo "?")
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
    if [[ $DAYS_LEFT -lt 30 ]]; then
      warn "$(basename "$cert"): expires in ${DAYS_LEFT} days ($EXPIRY)"
    else
      pass "$(basename "$cert"): valid (${DAYS_LEFT} days remaining)"
    fi
  else
    fail_c "Certificate missing: $cert"
  fi
done

# ── Disk & memory ─────────────────────────────────────────────────────────────
header "System resources"
FREE_DISK=$(df -m "$INSTALL_DIR" | awk 'NR==2 {print $4}')
if [[ $FREE_DISK -lt 2048 ]]; then
  warn "Low disk space: ${FREE_DISK}MB free"
else
  pass "Disk: ${FREE_DISK}MB free"
fi

if command -v free &>/dev/null; then
  FREE_RAM=$(free -m | awk '/^Mem:/ {print $7}')
  if [[ $FREE_RAM -lt 512 ]]; then
    warn "Low available RAM: ${FREE_RAM}MB"
  else
    pass "RAM: ${FREE_RAM}MB available"
  fi
fi

# ── License connectivity ───────────────────────────────────────────────────────
header "Platform connectivity"
if [[ -f "${INSTALL_DIR}/.env" ]]; then
  # shellcheck source=/dev/null
  source "${INSTALL_DIR}/.env"
  PLATFORM_HOST=$(echo "${PLATFORM_URL:-}" | sed -E 's|https?://([^:/]+).*|\1|')
  if [[ -n "$PLATFORM_HOST" ]]; then
    if curl -sf --max-time 8 "https://${PLATFORM_HOST}" >/dev/null 2>&1; then
      pass "Platform reachable: $PLATFORM_HOST"
    else
      warn "Cannot reach Platform host: $PLATFORM_HOST"
      warn "License heartbeat may fail. Check firewall / DNS."
    fi
  fi
fi

# ── Log file ──────────────────────────────────────────────────────────────────
header "Logging"
if [[ -f "$LOG_FILE" ]]; then
  LOG_LINES=$(wc -l < "$LOG_FILE")
  LOG_SIZE=$(du -sh "$LOG_FILE" | cut -f1)
  pass "Log file: $LOG_FILE ($LOG_SIZE, $LOG_LINES lines)"
else
  warn "Log file not found: $LOG_FILE"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── Summary ─────────────────────────────────────────────${RESET}"
if [[ $FAIL_COUNT -eq 0 && $WARN_COUNT -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}All checks passed. System is healthy.${RESET}"
elif [[ $FAIL_COUNT -eq 0 ]]; then
  echo -e "  ${YELLOW}${BOLD}${WARN_COUNT} warning(s) — review above.${RESET}"
else
  echo -e "  ${RED}${BOLD}${FAIL_COUNT} failure(s), ${WARN_COUNT} warning(s) — action required.${RESET}"
fi
echo ""
[[ $FAIL_COUNT -gt 0 ]] && exit 1 || exit 0
