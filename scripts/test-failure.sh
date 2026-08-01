#!/usr/bin/env bash
# /home/devils/PRO/Unotusk/scripts/test-failure.sh

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

# trap for cleanup
cleanup() {
  echo -e "\n${BOLD}${YELLOW}Cleaning up / Restoring State...${RESET}"
  cd "$INSTALL_DIR" || exit 0
  docker compose up -d || true
}
trap cleanup EXIT

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

failure_kill_us_recovers() {
  cd "$INSTALL_DIR" || exit 1
  docker compose stop us
  ! curl -sf http://localhost:3000/healthz >/dev/null
  docker compose start us
  local recovered=0
  for i in {1..24}; do
    if curl -sf http://localhost:3000/healthz >/dev/null; then
      recovered=1
      break
    fi
    sleep 5
  done
  [[ $recovered -eq 1 ]] || { echo "Failed to recover US"; exit 1; }
}

failure_kill_ups_recovers() {
  cd "$INSTALL_DIR" || exit 1
  docker compose stop ups
  # Verify UPS stops responding
  ! docker compose exec -T us curl -sf http://ups:8080/healthz >/dev/null
  docker compose start ups
  local recovered=0
  for i in {1..24}; do
    if docker compose exec -T ups curl -sf http://localhost:8080/healthz >/dev/null; then
      recovered=1
      break
    fi
    sleep 5
  done
  [[ $recovered -eq 1 ]] || { echo "Failed to recover UPS"; exit 1; }
  # Verify license status accessible via US
  curl -sf http://localhost:3000/license/status | grep -q '"status"'
}

failure_kill_aipie_recovers() {
  cd "$INSTALL_DIR" || exit 1
  docker compose stop ai-pie
  ! docker compose exec -T us curl -sf http://ai-pie:8000/health >/dev/null
  docker compose start ai-pie
  local recovered=0
  for i in {1..36}; do
    if docker compose exec -T ai-pie curl -sf http://localhost:8000/health >/dev/null; then
      recovered=1
      break
    fi
    sleep 5
  done
  [[ $recovered -eq 1 ]] || { echo "Failed to recover AI-PIE"; exit 1; }
  docker compose exec -T ai-pie curl -sf http://localhost:8000/health | grep -q 'ok'
}

failure_kill_postgres_recovers() {
  cd "$INSTALL_DIR" || exit 1
  docker compose stop postgres
  # Wait for postgres to be fully stopped
  sleep 2
  # US should fail readyz (or similar checks might fail)
  ! curl -sf http://localhost:3000/readyz >/dev/null || echo "Warning: readyz didn't fail"
  docker compose start postgres
  # restart dependent services in order
  docker compose restart ups
  sleep 2
  docker compose restart us
  sleep 2
  docker compose restart ai-pie
  
  local recovered=0
  for i in {1..24}; do
    if curl -sf http://localhost:3000/healthz >/dev/null; then
      recovered=1
      break
    fi
    sleep 5
  done
  [[ $recovered -eq 1 ]] || { echo "Failed to recover US after DB bounce"; exit 1; }
  
  docker compose exec -T ai-pie curl -sf http://localhost:8000/health | grep -q 'ok'
}

failure_grace_period_behavior() {
  local status
  status=$(curl -sf http://localhost:3000/license/status | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "")
  if [[ "$status" == "grace" ]]; then
    curl -sf http://localhost:3000/healthz >/dev/null
  else
    echo "License not in grace mode. Skipping."
    exit 77
  fi
}

failure_expired_jwt() {
  # Header: alg=HS256, typ=JWT. Payload: exp=1516239022 (year 2018).
  local TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
  local code
  code=$(curl -s -w "%{http_code}" -o /dev/null -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/me)
  [[ "$code" == "401" ]] || { echo "Expected 401, got $code"; exit 1; }
}

failure_invalid_jwt_signature() {
  # Valid structure, large exp, wrong sig
  local TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjk5OTk5OTk5OTl9.invalid_signature_here_1234567890"
  local code
  code=$(curl -s -w "%{http_code}" -o /dev/null -H "Authorization: Bearer $TOKEN" http://localhost:3000/api/me)
  [[ "$code" == "401" ]] || { echo "Expected 401, got $code"; exit 1; }
}

failure_env_permissions() {
  [[ -f "$INSTALL_DIR/.env" ]] || exit 77
  local perms
  perms=$(stat -c '%a' "$INSTALL_DIR/.env")
  [[ "$perms" == "600" ]] || { echo "Expected 600, got $perms"; exit 1; }
}

failure_key_permissions_warning() {
  local out
  out=$(find "$INSTALL_DIR" -type f -name "*.key" -exec stat -c '%a %n' {} \; | awk '$1 < 644 {print}')
  if [[ -n "$out" ]]; then
    echo "WARNING: Some key files have permissions tighter than 644:"
    echo "$out"
  fi
  exit 0
}

# ----------------- MAIN -----------------

echo -e "${BOLD}Starting Failure & Resilience Tests...${RESET}"

tests=(
  failure_kill_us_recovers
  failure_kill_ups_recovers
  failure_kill_aipie_recovers
  failure_kill_postgres_recovers
  failure_grace_period_behavior
  failure_expired_jwt
  failure_invalid_jwt_signature
  failure_env_permissions
  failure_key_permissions_warning
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
  echo "<testsuite name=\"failure-tests\" tests=\"${#tests[@]}\" failures=\"$TESTS_FAILED\" skipped=\"$TESTS_SKIPPED\">" >> "$JUNIT_OUTPUT"
  for res in "${RESULTS[@]}"; do
    name="${res%%|*}"
    status="${res##*|}"
    echo "  <testcase name=\"$name\" classname=\"failure\">" >> "$JUNIT_OUTPUT"
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
