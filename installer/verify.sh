#!/usr/bin/env bash
# ==============================================================================
#  UNOTUSK Verify — Post-install integrity check
#  Usage: unotusk verify
# ==============================================================================
set -Eeuo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
LOG_FILE="/var/log/unotusk-install.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

pass()    { echo -e "  ${GREEN}✔${RESET}  $*"; }
fail_c()  { echo -e "  ${RED}✘${RESET}  $*"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
warn()    { echo -e "  ${YELLOW}⚠${RESET}  $*"; }
info()    { echo -e "  ${CYAN}→${RESET}  $*"; }
header()  { echo -e "\n${BOLD}── $* ${RESET}"; }

FAIL_COUNT=0

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║       UNOTUSK Verification               ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── Required files ─────────────────────────────────────────────────────────────
header "Required files"
REQUIRED_FILES=(
  "${INSTALL_DIR}/.env"
  "${INSTALL_DIR}/.unotusk-version"
  "${INSTALL_DIR}/compose/docker-compose.yml"
  "${INSTALL_DIR}/US/certs/ca.crt"
  "${INSTALL_DIR}/US/certs/server.crt"
  "${INSTALL_DIR}/UPS/certs/client.crt"
  "${INSTALL_DIR}/AI-PIE/certs/dev/client.pem"
)
for f in "${REQUIRED_FILES[@]}"; do
  [[ -f "$f" ]] && pass "${f##*/}" || fail_c "Missing: $f"
done

# ── Service containers ────────────────────────────────────────────────────────
header "Container states"
_compose() {
  docker compose -f "${INSTALL_DIR}/compose/docker-compose.yml" \
    --env-file "${INSTALL_DIR}/.env" "$@"
}
for svc in postgres qdrant phoenix us ups ai-pie; do
  STATE=$(_compose ps "$svc" --format "{{.State}}" 2>/dev/null || echo "missing")
  [[ "$STATE" == "running" ]] && pass "$svc: running" || fail_c "$svc: $STATE"
done

# ── HTTP checks ───────────────────────────────────────────────────────────────
header "HTTP endpoints"
declare -A ENDPOINTS=(
  ["US /healthz"]="http://localhost:3000/healthz"
  ["US /readyz"]="http://localhost:3000/readyz"
  ["OIDC discovery"]="http://localhost:3000/.well-known/openid-configuration"
  ["JWKS endpoint"]="http://localhost:3000/.well-known/jwks.json"
)
for label in "${!ENDPOINTS[@]}"; do
  CODE=$(curl -so /dev/null -w "%{http_code}" --max-time 5 "${ENDPOINTS[$label]}" 2>/dev/null || echo "000")
  [[ "$CODE" == "200" ]] && pass "$label — $CODE" || fail_c "$label — HTTP $CODE (expected 200)"
done

# ── mTLS certificate chain ────────────────────────────────────────────────────
header "Certificate chain"
CA_CERT="${INSTALL_DIR}/US/certs/ca.crt"
for cert_file in \
  "${INSTALL_DIR}/US/certs/server.crt" \
  "${INSTALL_DIR}/UPS/certs/client.crt" \
  "${INSTALL_DIR}/AI-PIE/certs/dev/client.pem"; do
  if [[ -f "$cert_file" && -f "$CA_CERT" ]]; then
    if openssl verify -CAfile "$CA_CERT" "$cert_file" >/dev/null 2>&1; then
      pass "$(basename "$cert_file") — chain valid"
    else
      fail_c "$(basename "$cert_file") — chain verification FAILED"
    fi
  else
    fail_c "$(basename "$cert_file") — file missing"
  fi
done

# ── Secrets not defaults ──────────────────────────────────────────────────────
header "Secret sanity"
if [[ -f "${INSTALL_DIR}/.env" ]]; then
  # shellcheck source=/dev/null
  source "${INSTALL_DIR}/.env"
  [[ "${POSTGRES_PASSWORD:-}" != "changeme" ]] && pass "POSTGRES_PASSWORD is not default" || fail_c "POSTGRES_PASSWORD is still default!"
  [[ ${#POSTGRES_PASSWORD:-} -ge 16 ]] && pass "POSTGRES_PASSWORD length OK" || fail_c "POSTGRES_PASSWORD too short"
  [[ -n "${JWKS_PUSH_SECRET:-}" ]] && pass "JWKS_PUSH_SECRET is set" || fail_c "JWKS_PUSH_SECRET not set"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if [[ $FAIL_COUNT -eq 0 ]]; then
  echo -e "  ${GREEN}${BOLD}All verification checks passed.${RESET}"
else
  echo -e "  ${RED}${BOLD}${FAIL_COUNT} verification check(s) FAILED.${RESET}"
fi
echo ""
[[ $FAIL_COUNT -gt 0 ]] && exit 1 || exit 0
