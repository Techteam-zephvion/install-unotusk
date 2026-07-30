#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Automated CI Test Runner
# ==============================================================================
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER_ROOT="$(dirname "$TEST_DIR")"

# Source colors/logging
# shellcheck source=lib/colors.sh
source "$INSTALLER_ROOT/lib/colors.sh"
# shellcheck source=lib/logging.sh
source "$INSTALLER_ROOT/lib/logging.sh"

log_title "UNOTUSK CI Automated Test Runner"

failures=0

run_test() {
  local desc="$1"
  shift
  local cmd=("$@")
  
  log_info "Running test: $desc ..."
  if "${cmd[@]}"; then
    log_success "PASS: $desc"
  else
    log_error "FAIL: $desc"
    failures=$((failures + 1))
  fi
}

# Test 1: Bash syntax checks
test_syntax() {
  find "$INSTALLER_ROOT" -name "*.sh" -exec bash -n {} \;
}

# Test 2: manifest.json structural validity
test_manifest_structure() {
  python3 -c "
import json
with open('$INSTALLER_ROOT/manifest.json') as f:
    data = json.load(f)
    assert 'version' in data
    assert 'images' in data
    assert 'templates' in data
"
}

# Test 3: settings.yaml format verification
test_settings_format() {
  python3 -c "
with open('$INSTALLER_ROOT/settings.yaml') as f:
    content = f.read()
    assert 'settings:' in content
    assert 'ORG_NAME' in content
"
}

# Test 4: Structured log validation
test_json_logging() {
  local test_log="/tmp/unotusk-test-log.json"
  rm -f "$test_log"
  INSTALL_LOG="$test_log" write_log "INFO" "testing" "This is a log message"
  
  # Assert file is valid JSON
  python3 -c "
import json
with open('$test_log') as f:
    data = json.loads(f.readline())
    assert data['level'] == 'INFO'
    assert data['module'] == 'testing'
    assert data['message'] == 'This is a log message'
"
  rm -f "$test_log"
}

# Execute tests
run_test "Verify Shell Script Syntax" test_syntax
run_test "Verify Version Manifest JSON structure" test_manifest_structure
run_test "Verify Settings YAML format" test_settings_format
run_test "Verify JSON Structured Logging output" test_json_logging

echo ""
if [ "$failures" -eq 0 ]; then
  log_success "All automated validation checks PASSED."
  exit 0
else
  log_error "CI Test Suite completed with $failures failure(s)."
  exit 1
fi
