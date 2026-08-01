#!/usr/bin/env bash
set -euo pipefail

# Colors
RED=$(tput setaf 1 2>/dev/null || echo '')
GREEN=$(tput setaf 2 2>/dev/null || echo '')
YELLOW=$(tput setaf 3 2>/dev/null || echo '')
CYAN=$(tput setaf 6 2>/dev/null || echo '')
BOLD=$(tput bold 2>/dev/null || echo '')
RESET=$(tput sgr0 2>/dev/null || echo '')

INSTALL_DIR="/opt/unotusk"
VERBOSE=0
JUNIT_OUTPUT=""
LOG_FILE="logs/security.log"

# Parse arguments
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
      echo "${RED}Unknown argument: $1${RESET}"
      exit 1
      ;;
  esac
done

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"
# Clear log file
> "$LOG_FILE"

log() {
  echo -e "[$1] $2" | tee -a "$LOG_FILE"
}

PASSED=0
FAILED=0
SKIPPED=0
declare -a RESULTS_TABLE

# JUnit XML output string
JUNIT_TESTCASES=""

skip_test() {
  return 254
}

run_test() {
  local test_name="$1"
  local cmd="$2"
  local notes="${3:-}"
  
  if [ $VERBOSE -eq 1 ]; then
    echo -e "${CYAN}Running $test_name...${RESET}"
  fi
  
  local output
  local rc=0
  
  # Run command and capture output and exit code
  output=$(eval "$cmd" 2>&1) || rc=$?
  
  if [ $rc -eq 0 ]; then
    ((PASSED++))
    RESULTS_TABLE+=("${GREEN}PASS${RESET} | $test_name | $notes")
    log "PASS" "$test_name"
    
    JUNIT_TESTCASES+="  <testcase name=\"$test_name\" classname=\"SecurityTests\" />\n"
  elif [ $rc -eq 254 ]; then
    ((SKIPPED++))
    RESULTS_TABLE+=("${YELLOW}SKIP${RESET} | $test_name | $notes")
    log "SKIP" "$test_name: $output"
    
    JUNIT_TESTCASES+="  <testcase name=\"$test_name\" classname=\"SecurityTests\">\n    <skipped message=\"$output\" />\n  </testcase>\n"
  else
    ((FAILED++))
    RESULTS_TABLE+=("${RED}FAIL${RESET} | $test_name | $notes")
    log "FAIL" "$test_name: $output"
    
    JUNIT_TESTCASES+="  <testcase name=\"$test_name\" classname=\"SecurityTests\">\n    <failure message=\"Test failed\"><![CDATA[$output]]></failure>\n  </testcase>\n"
  fi
}

echo -e "${BOLD}Running UNOTUSK Security Validation Tests...${RESET}"
echo -e "Install Directory: ${CYAN}$INSTALL_DIR${RESET}"
echo

# --- File Permission Tests ---
run_test "sec_env_root_chmod" "[ -f \"$INSTALL_DIR/.env\" ] && stat -c '%a' \"$INSTALL_DIR/.env\" | grep -q '600'"
run_test "sec_env_us_chmod" "[ -f \"$INSTALL_DIR/US/.env\" ] && stat -c '%a' \"$INSTALL_DIR/US/.env\" | grep -q '600'"
run_test "sec_env_ups_chmod" "[ -f \"$INSTALL_DIR/UPS/.env\" ] && stat -c '%a' \"$INSTALL_DIR/UPS/.env\" | grep -q '600'"
run_test "sec_env_aipie_chmod" "[ -f \"$INSTALL_DIR/AI-PIE/.env\" ] && stat -c '%a' \"$INSTALL_DIR/AI-PIE/.env\" | grep -q '600'"

run_test "sec_key_us_server" "[ -f \"$INSTALL_DIR/US/certs/server.key\" ] && stat -c '%a' \"$INSTALL_DIR/US/certs/server.key\" | grep -q '644'"
run_test "sec_key_ups_client" "[ -f \"$INSTALL_DIR/UPS/certs/client.key\" ] && stat -c '%a' \"$INSTALL_DIR/UPS/certs/client.key\" | grep -q '644'"
run_test "sec_key_platform_client" "[ -f \"$INSTALL_DIR/UPS/certs/platform/client.key\" ] && stat -c '%a' \"$INSTALL_DIR/UPS/certs/platform/client.key\" | grep -q '644'"

run_test "sec_no_world_write" "
  failed=0
  while read -r f; do
    mode=\$(stat -c '%a' \"\$f\" 2>/dev/null || true)
    if [ -n \"\$mode\" ]; then
      last_char=\"\${mode: -1}\"
      if [[ \"\$last_char\" != '0' && \"\$last_char\" != '4' ]]; then
        echo \"\$f has permissive mode: \$mode\"
        failed=1
      fi
    fi
  done < <(find \"$INSTALL_DIR\" -type f \( -name '*.key' -o -name '*.crt' \) 2>/dev/null)
  exit \$failed
"

run_test "sec_oauth_secret_chmod" "
  if [ -f \"$INSTALL_DIR/.oauth.secret\" ]; then 
    stat -c '%a' \"$INSTALL_DIR/.oauth.secret\" | grep -q '600'
  else 
    skip_test
  fi
" "Skipped if missing"

# --- Secret Exposure Tests ---
run_test "sec_no_password_in_logs" "! grep -R -E 'POSTGRES_PASSWORD=|PLATFORM_LICENSE_KEY=' \"$INSTALL_DIR/logs/\" 2>/dev/null"
run_test "sec_no_private_key_in_logs" "! grep -R 'BEGIN.*PRIVATE KEY' \"$INSTALL_DIR/logs/\" 2>/dev/null"
run_test "sec_license_key_not_in_log" "! grep -R 'LIC-' \"$INSTALL_DIR/logs/\" 2>/dev/null"

# --- Container Security Tests ---
run_test "sec_no_new_privileges_us" "cd \"$INSTALL_DIR\" && docker inspect \$(docker compose ps -q us) | grep -q '\"no-new-privileges:true\"'"
run_test "sec_no_new_privileges_ups" "cd \"$INSTALL_DIR\" && docker inspect \$(docker compose ps -q ups) | grep -q '\"no-new-privileges:true\"'"
run_test "sec_no_new_privileges_aipie" "cd \"$INSTALL_DIR\" && docker inspect \$(docker compose ps -q ai-pie) | grep -q '\"no-new-privileges:true\"'"
run_test "sec_non_root_us" "cd \"$INSTALL_DIR\" && ! docker compose exec -T us id -u | grep -q '^0$'"
run_test "sec_non_root_ups" "cd \"$INSTALL_DIR\" && ! docker compose exec -T ups id -u | grep -q '^0$'"

# --- TLS/Certificate Tests ---
run_test "sec_cert_min_keysize_us" "openssl x509 -in \"$INSTALL_DIR/US/certs/server.crt\" -noout -text 2>/dev/null | grep -A1 'Public-Key' | grep -q -E '2048 bit|4096 bit'"
run_test "sec_cert_min_keysize_ups" "openssl x509 -in \"$INSTALL_DIR/UPS/certs/client.crt\" -noout -text 2>/dev/null | grep -A1 'Public-Key' | grep -q -E '2048 bit|4096 bit'"
run_test "sec_ca_not_expired" "openssl x509 -in \"$INSTALL_DIR/US/certs/ca.crt\" -noout -checkend 0 2>/dev/null"
run_test "sec_cert_us_not_expired" "openssl x509 -in \"$INSTALL_DIR/US/certs/server.crt\" -noout -checkend 0 2>/dev/null"
run_test "sec_cert_ups_not_expired" "openssl x509 -in \"$INSTALL_DIR/UPS/certs/client.crt\" -noout -checkend 0 2>/dev/null"

# --- Dependency Audit Tests ---
run_test "sec_rust_audit_us" "
  if command -v cargo-audit >/dev/null 2>&1; then
    cd \"$INSTALL_DIR/US\" && cargo audit
  else
    echo 'cargo-audit not installed'
    skip_test
  fi
" "Requires cargo-audit"

run_test "sec_rust_audit_ups" "
  if command -v cargo-audit >/dev/null 2>&1; then
    cd \"$INSTALL_DIR/UPS\" && cargo audit
  else
    echo 'cargo-audit not installed'
    skip_test
  fi
" "Requires cargo-audit"

run_test "sec_python_audit_aipie" "
  if cd \"$INSTALL_DIR\" && docker compose ps -q ai-pie >/dev/null 2>&1; then
    if docker compose exec -T ai-pie command -v pip-audit >/dev/null 2>&1; then
      docker compose exec -T ai-pie pip-audit
    elif docker compose exec -T ai-pie command -v safety >/dev/null 2>&1; then
      docker compose exec -T ai-pie safety check
    else
      echo 'No audit tool found (pip-audit/safety) in container'
      skip_test
    fi
  else
    echo 'ai-pie container not running'
    skip_test
  fi
" "Requires pip-audit or safety"

# --- Network Isolation Tests ---
run_test "sec_ups_not_host_exposed_8080" "cd \"$INSTALL_DIR\" && ! docker compose ps ups 2>/dev/null | grep -q '8080->8080'"
run_test "sec_aipie_not_host_exposed" "cd \"$INSTALL_DIR\" && ! docker compose ps ai-pie 2>/dev/null | grep -q -- '->'"
run_test "sec_qdrant_not_host_exposed" "cd \"$INSTALL_DIR\" && ! docker compose ps qdrant 2>/dev/null | grep -q -- '->'"
run_test "sec_postgres_not_host_exposed" "cd \"$INSTALL_DIR\" && ! docker compose ps postgres 2>/dev/null | grep -q -- '->'"

# --- JWT Validation Tests ---
run_test "sec_jwt_none_algorithm_rejected" "
  status=\$(curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer eyJhbGciOiJub25lIn0=.eyJzdWIiOiJ0ZXN0IiwiZXhwIjo5OTk5OTk5OTk5fQ==.' http://localhost:3000/api/me)
  [ \"\$status\" -eq 401 ]
"

run_test "sec_expired_jwt_rejected" "
  status=\$(curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ==.sig' http://localhost:3000/api/me)
  [ \"\$status\" -eq 401 ]
"

echo
echo -e "${BOLD}Summary Table${RESET}"
echo "----------------------------------------------------------------------"
printf "%-18s | %-32s | %s\n" "Result" "Test Name" "Notes"
echo "----------------------------------------------------------------------"
for res in "${RESULTS_TABLE[@]}"; do
  # Extract parts
  IFS='|' read -r result name notes <<< "$res"
  printf "%-27s | %-32s | %s\n" "$result" "$name" "$notes"
done
echo "----------------------------------------------------------------------"
echo -e "Total Passed:  ${GREEN}$PASSED${RESET}"
echo -e "Total Failed:  ${RED}$FAILED${RESET}"
echo -e "Total Skipped: ${YELLOW}$SKIPPED${RESET}"
echo

if [ -n "$JUNIT_OUTPUT" ]; then
  mkdir -p "\$(dirname \"\$JUNIT_OUTPUT\")"
  TOTAL_TESTS=\$((PASSED + FAILED + SKIPPED))
  cat > "$JUNIT_OUTPUT" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="SecurityTests" tests="$TOTAL_TESTS" failures="$FAILED" skipped="$SKIPPED">
$JUNIT_TESTCASES  </testsuite>
</testsuites>
EOF
  echo -e "${CYAN}Wrote JUnit XML to $JUNIT_OUTPUT${RESET}"
fi

if [ $FAILED -gt 0 ]; then
  exit 1
fi
exit 0
