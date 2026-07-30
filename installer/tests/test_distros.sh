#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — CI Distros Mock Check
# ==============================================================================
set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER_ROOT="$(dirname "$TEST_DIR")"

# Source the main common bootstrap library
# shellcheck source=lib/common.sh
source "$INSTALLER_ROOT/lib/common.sh"
# shellcheck source=lib/validation.sh
source "$INSTALLER_ROOT/lib/validation.sh"

log_title "UNOTUSK CI OS & Distro Validation Checks"

test_os_mock() {
  local mock_distro="$1"
  local mock_version="$2"
  log_info "Mocking Environment: OS=$mock_distro, VERSION=$mock_version..."

  # Run validation
  DISTRO_ID="$mock_distro" DISTRO_VERSION="$mock_version" validate_os
}

# Run mock checks
test_os_mock "ubuntu" "24.04"
test_os_mock "ubuntu" "22.04" # Should trigger supported warning
test_os_mock "debian" "12"
test_os_mock "debian" "11" # Should trigger supported warning
test_os_mock "pop" "22.04"
test_os_mock "rhel" "9" # Unsupported distro warning check

log_success "Distro validation tests finished."
