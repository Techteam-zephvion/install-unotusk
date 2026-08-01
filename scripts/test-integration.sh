#!/usr/bin/env bash
# /home/devils/PRO/Unotusk/scripts/test-integration.sh

# Color palette
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
BOLD="\033[1m"
RESET="\033[0m"

INSTALL_DIR="/opt/unotusk"
VERBOSE=0
JUNIT_OUTPUT=""

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=1
      shift
      ;;
    --junit-output)
      JUNIT_OUTPUT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0
declare -a RESULTS=()
declare -A TEST_OUTPUTS=()

pass() {
  local name="$1"
  echo -e "  [${GREEN}PASS${RESET}] $name"
  TESTS_PASSED=$((TESTS_PASSED+1))
  RESULTS+=("$name|PASS")
}

fail() {
  local name="$1"
  local msg="${2:-}"
  echo -e "  [${RED}FAIL${RESET}] $name"
  [[ -n "$msg" ]] && echo -e "         Reason:\n$msg" | sed 's/^/         /'
  TESTS_FAILED=$((TESTS_FAILED+1))
  RESULTS+=("$name|FAIL")
  TEST_OUTPUTS["$name"]="$msg"
}

skip() {
  local name="$1"
  local msg="${2:-}"
  echo -e "  [${YELLOW}SKIP${RESET}] $name"
  TESTS_SKIPPED=$((TESTS_SKIPPED+1))
  RESULTS+=("$name|SKIP")
  TEST_OUTPUTS["$name"]="$msg"
}

run_test() {
  local test_func="$1"
  echo -e "${CYAN}Running $test_func...${RESET}"
  local result_file
  result_file=$(mktemp)
  local exit_code=0
  
  if (
    set -e
    "$test_func"
  ) > "$result_file" 2>&1; then
    pass "$test_func"
    [[ "$VERBOSE" == "1" ]] && cat "$result_file"
  else
    exit_code=$?
    if [[ $exit_code -eq 77 ]]; then
      skip "$test_func" "$(<"$result_file")"
    else
      fail "$test_func" "$(<"$result_file")"
    fi
  fi
  rm -f "$result_file"
}

# ----------------- TESTS -----------------

auth_us_healthz() {
  curl -sf http://localhost:3000/healthz >/dev/null
}

auth_us_readyz() {
  curl -sf http://localhost:3000/readyz >/dev/null
}

auth_oidc_discovery() {
  curl -sf http://localhost:3000/.well-known/openid-configuration | grep -q '"issuer"'
}

auth_jwks_endpoint() {
  curl -sf http://localhost:3000/.well-known/jwks.json | grep -q '"keys"'
}

auth_invalid_token() {
  local code
  code=$(curl -s -w "%{http_code}" -o /dev/null -H "Authorization: Bearer invalid.token.here" http://localhost:3000/api/me)
  [[ "$code" == "401" ]]
}

auth_missing_token() {
  local code
  code=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:3000/api/me)
  [[ "$code" == "401" ]]
}

license_status_endpoint() {
  curl -sf http://localhost:3000/license/status | grep -q '"status"'
}

license_status_valid_values() {
  local status
  status=$(curl -sf http://localhost:3000/license/status | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "")
  [[ "$status" =~ ^(normal|grace|degraded|hard_blocked|unknown)$ ]]
}

license_ups_healthz() {
  cd "$INSTALL_DIR" || exit 1
  docker compose exec -T ups curl -sf http://localhost:8080/healthz >/dev/null
}

aipie_health() {
  cd "$INSTALL_DIR" || exit 1
  docker compose exec -T ai-pie curl -sf http://localhost:8000/health | grep -q 'ok'
}

aipie_license_gate_check() {
  cd "$INSTALL_DIR" || exit 1
  docker inspect -f '{{.State.Status}}' $(docker compose ps -q ai-pie | head -n 1) | grep -q 'running'
}

infra_postgres_ready() {
  cd "$INSTALL_DIR" || exit 1
  docker compose exec -T postgres pg_isready -U unotusk
}

infra_qdrant_reachable() {
  cd "$INSTALL_DIR" || exit 1
  docker compose exec -T ai-pie curl -sf http://qdrant:6333/healthz >/dev/null
}

infra_phoenix_reachable() {
  cd "$INSTALL_DIR" || exit 1
  docker compose exec -T ai-pie curl -sf http://phoenix:6006/healthz >/dev/null
}

infra_auth_db_exists() {
  cd "$INSTALL_DIR" || exit 1
  docker compose exec -T postgres psql -U unotusk -d auth -c 'SELECT 1' >/dev/null
}

infra_company_db_exists() {
  cd "$INSTALL_DIR" || exit 1
  docker compose exec -T postgres psql -U unotusk -d company -c 'SELECT 1' >/dev/null
}

cli_status_exits_zero() {
  unotusk status >/dev/null
}

cli_doctor_runs() {
  unotusk doctor >/dev/null || { local code=$?; [[ $code -le 1 ]]; }
}

cert_us_server_valid() {
  [[ -f "$INSTALL_DIR/US/certs/server.crt" ]] || { echo "File not found: $INSTALL_DIR/US/certs/server.crt"; exit 1; }
  openssl x509 -in "$INSTALL_DIR/US/certs/server.crt" -noout -checkend 0
}

cert_ups_client_valid() {
  [[ -f "$INSTALL_DIR/UPS/certs/client.crt" ]] || { echo "File not found: $INSTALL_DIR/UPS/certs/client.crt"; exit 1; }
  openssl x509 -in "$INSTALL_DIR/UPS/certs/client.crt" -noout -checkend 0
}

cert_platform_client_valid() {
  [[ -f "$INSTALL_DIR/UPS/certs/platform/client.crt" ]] || { echo "File not found: $INSTALL_DIR/UPS/certs/platform/client.crt"; exit 1; }
  openssl x509 -in "$INSTALL_DIR/UPS/certs/platform/client.crt" -noout -checkend 0
}

# ----------------- MAIN -----------------

echo -e "${BOLD}Starting Integration Tests...${RESET}"

tests=(
  auth_us_healthz
  auth_us_readyz
  auth_oidc_discovery
  auth_jwks_endpoint
  auth_invalid_token
  auth_missing_token
  license_status_endpoint
  license_status_valid_values
  license_ups_healthz
  aipie_health
  aipie_license_gate_check
  infra_postgres_ready
  infra_qdrant_reachable
  infra_phoenix_reachable
  infra_auth_db_exists
  infra_company_db_exists
  cli_status_exits_zero
  cli_doctor_runs
  cert_us_server_valid
  cert_ups_client_valid
  cert_platform_client_valid
)

for t in "${tests[@]}"; do
  run_test "$t"
done

echo ""
echo -e "${BOLD}--- Test Summary ---${RESET}"
for res in "${RESULTS[@]}"; do
  name="${res%%|*}"
  status="${res##*|}"
  if [[ "$status" == "PASS" ]]; then
    echo -e "${GREEN}PASS${RESET} $name"
  elif [[ "$status" == "FAIL" ]]; then
    echo -e "${RED}FAIL${RESET} $name"
  else
    echo -e "${YELLOW}SKIP${RESET} $name"
  fi
done
echo "Total: ${#tests[@]} | Passed: $TESTS_PASSED | Failed: $TESTS_FAILED | Skipped: $TESTS_SKIPPED"

if [[ -n "$JUNIT_OUTPUT" ]]; then
  echo '<?xml version="1.0" encoding="UTF-8"?>' > "$JUNIT_OUTPUT"
  echo "<testsuite name=\"integration-tests\" tests=\"${#tests[@]}\" failures=\"$TESTS_FAILED\" skipped=\"$TESTS_SKIPPED\">" >> "$JUNIT_OUTPUT"
  for res in "${RESULTS[@]}"; do
    name="${res%%|*}"
    status="${res##*|}"
    echo "  <testcase name=\"$name\" classname=\"integration\">" >> "$JUNIT_OUTPUT"
    if [[ "$status" == "FAIL" ]]; then
      escaped_out=$(echo -e "${TEST_OUTPUTS["$name"]:-}" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
      echo "    <failure message=\"Test failed\"><![CDATA[$escaped_out]]></failure>" >> "$JUNIT_OUTPUT"
    elif [[ "$status" == "SKIP" ]]; then
      echo "    <skipped/>" >> "$JUNIT_OUTPUT"
    fi
    echo "  </testcase>" >> "$JUNIT_OUTPUT"
  done
  echo "</testsuite>" >> "$JUNIT_OUTPUT"
fi

if [[ $TESTS_FAILED -gt 0 ]]; then
  exit 1
fi
exit 0
