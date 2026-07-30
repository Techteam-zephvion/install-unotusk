#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Platform — Main Installation Entrypoint
# Usage: sudo ./install.sh
# ==============================================================================
set -euo pipefail

# Find script directory and load core common bootsrapper
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$SRC_DIR/lib/common.sh"
# shellcheck source=lib/validation.sh
source "$SRC_DIR/lib/validation.sh"
# shellcheck source=lib/filesystem.sh
source "$SRC_DIR/lib/filesystem.sh"
# shellcheck source=lib/network.sh
source "$SRC_DIR/lib/network.sh"
# shellcheck source=lib/docker.sh
source "$SRC_DIR/lib/docker.sh"
# shellcheck source=lib/compose.sh
source "$SRC_DIR/lib/compose.sh"
# shellcheck source=lib/configuration.sh
source "$SRC_DIR/lib/configuration.sh"
# shellcheck source=lib/certificates.sh
source "$SRC_DIR/lib/certificates.sh"
# shellcheck source=lib/registration.sh
source "$SRC_DIR/lib/registration.sh"
# shellcheck source=lib/health.sh
source "$SRC_DIR/lib/health.sh"
# shellcheck source=lib/services.sh
source "$SRC_DIR/lib/services.sh"
# shellcheck source=lib/cli.sh
source "$SRC_DIR/lib/cli.sh"

main() {
  # Display header banner
  log_title "UNOTUSK Platform Installer"

  # ── Phase 0: Privilege Check ──
  check_root

  # ── Phase 1: Idempotency / Existing Install Check ──
  if [ -f "$VERSION_FILE" ]; then
    local installed_ver
    installed_ver=$(grep '^INSTALL_VERSION=' "$VERSION_FILE" | cut -d= -f2- || echo "unknown")
    
    log_warn "An existing UNOTUSK installation was detected!"
    echo "     Location:        $INSTALL_DIR"
    echo "     Version:         $installed_ver"
    echo ""
    echo "  What would you like to do?"
    echo "    1) Upgrade        — pull updated containers, run migrations, restart"
    echo "    2) Reconfigure    — launch wizard to change settings"
    echo "    3) Repair         — re-install CLI and templates, keep data intact"
    echo "    4) Reinstall      — full reinstall, preserve existing DB volume data"
    echo "    5) Remove         — uninstall UNOTUSK from this server"
    echo "    6) Abort          — exit without changes"
    echo ""
    
    local option=""
    read -r -p "  Select an option [1-6]: " option
    case "$option" in
      1)
        log_info "Executing upgrade sequence..."
        exec bash "$SRC_DIR/upgrade.sh"
        ;;
      2)
        log_info "Running reconfiguration..."
        run_config_wizard
        # Run plugins configure hook
        run_plugins_configure
        start_all_services
        exit 0
        ;;
      3)
        log_info "Repairing installer and CLI configurations..."
        setup_install_directory
        deploy_installer_resources
        install_unotusk_cli
        log_success "CLI and service templates repaired."
        exit 0
        ;;
      4)
        log_warn "Full reinstall will re-create stack templates. Data volumes will not be removed."
        local conf=""
        read -r -p "  Continue? [y/N]: " conf
        [[ "$conf" =~ ^[Yy]$ ]] || { log_info "Operation aborted."; exit 0; }
        # Fallthrough to normal install sequence
        ;;
      5)
        log_info "Running uninstall..."
        exec bash "$SRC_DIR/uninstall.sh"
        ;;
      *)
        log_info "Exiting installation."
        exit 0
        ;;
      esac
  fi

  # ── Phase 2: Environment Validations ──
  log_header "[1/6] Environment Validation Checks"
  validate_os
  validate_arch
  validate_resources
  validate_dependencies
  validate_docker_engine
  validate_docker_compose
  validate_ingress_ports
  validate_outbound_connectivity "https://registry-1.docker.io"
  log_success "Validation checks passed."

  # ── Phase 3: Filesystem & Paths Setup ──
  log_header "[2/6] Preparing Filesystem Paths"
  setup_install_directory
  deploy_installer_resources
  # Execute plugins install hook
  run_plugins_install
  log_success "Filesystem structure ready."

  # ── Phase 4: Interactive Setup Wizard ──
  log_header "[3/6] Setup Wizard Configuration"
  run_config_wizard
  # Run plugins configure and validate hooks
  run_plugins_configure
  run_plugins_validate

  # ── Phase 5: TLS & Cryptographic Material ──
  log_header "[4/6] Provisioning Cryptographic Certificates"
  generate_certificates

  # ── Phase 6: Cloud Platform Registration ──
  log_header "[5/6] Registering Deployment Organization"
  register_deployment

  # ── Phase 7: Launch Service Stack ──
  log_header "[6/6] Launching Docker Service Stack"
  # Verify compose syntax
  compose_validate_config
  # Pull images
  compose_pull_images
  # Startup containers
  start_all_services
  # Verify mTLS
  verify_mtls_connectivity
  # Verify health
  verify_overall_health
  # Run plugins health check hook
  run_plugins_health

  # ── Systemd Integration ──
  log_header "Installing Systemd Integration"
  if [ -f "$INSTALL_DIR/systemd/unotusk.service" ]; then
    cp "$INSTALL_DIR/systemd/unotusk.service" /etc/systemd/system/unotusk.service
    systemctl daemon-reload
    systemctl enable unotusk.service &>>"$INSTALL_LOG" || true
    log_success "unotusk systemd service unit registered."
  fi

  # ── CLI Binary Registration ──
  install_unotusk_cli

  # Write version metadata
  cat > "$VERSION_FILE" <<EOF
INSTALL_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
INSTALL_VERSION=2.0.0-modular
ORG_ID=$ORG_ID
ORG_NAME=$ORG_NAME
EOF

  # Complete summary
  echo ""
  log_title "UNOTUSK Installation Completed Successfully!"
  echo "  Run 'unotusk status' to check service containers status."
  echo "  Run 'unotusk doctor' to execute complete host diagnostics."
  echo "  Consult docs/INSTALL.md or docs/TROUBLESHOOTING.md for details."
  echo ""
}

main "$@"
