#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — CLI Orchestrator Library
# ==============================================================================

# Install the global unotusk CLI wrapper
install_unotusk_cli() {
  log_to_file_info "Registering unotusk command line tool..."
  
  local target_bin="/usr/local/bin/unotusk"
  local source_script="$INSTALL_DIR/scripts/unotusk-cli.sh"

  if [ -f "$source_script" ]; then
    chmod +x "$source_script"
    ln -sf "$source_script" "$target_bin"
    log_success "CLI globally installed at $target_bin"
    log_to_file_info "Symlinked $source_script to $target_bin successfully."
  else
    log_to_file_err "CLI Script not found at $source_script."
  fi
}

# Display help and usage instructions
show_cli_usage() {
  echo ""
  log_header "UNOTUSK Platform CLI — Management Console"
  echo "  Usage: unotusk <command> [options]"
  echo ""
  echo "  Service Management:"
  echo "    start                 Start all platform services"
  echo "    stop                  Stop all platform services"
  echo "    restart               Restart platform services"
  echo "    status                Show status of all containers"
  echo "    logs [service]        Display live docker logs"
  echo ""
  echo "  Maintenance & Operations:"
  echo "    doctor                Execute system diagnostics check"
  echo "    health                Quick health evaluation"
  echo "    backup                Create a complete platform backup"
  echo "    restore <path>        Restore state from a backup archive"
  echo "    update                Upgrade platform services securely"
  echo "    rollback              Trigger rollback to previous state"
  echo "    uninstall             Remove UNOTUSK from this server"
  echo ""
}

# CLI command dispatcher logic
dispatch_cli_command() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    start)
      start_all_services
      ;;
    stop)
      stop_all_services
      ;;
    restart)
      restart_all_services
      ;;
    status)
      log_header "UNOTUSK Platform Container Status"
      (cd "$INSTALL_DIR" && docker compose ps)
      ;;
    logs)
      local svc="${1:-}"
      if [ -n "$svc" ]; then
        (cd "$INSTALL_DIR" && docker compose logs -f "$svc")
      else
        (cd "$INSTALL_DIR" && docker compose logs -f)
      fi
      ;;
    doctor)
      # Run diagnostic doctor checks (sourced from doctor script)
      if [ -f "$INSTALL_DIR/doctor.sh" ]; then
        bash "$INSTALL_DIR/doctor.sh"
      else
        log_error "doctor.sh not found in $INSTALL_DIR."
      fi
      ;;
    health)
      verify_overall_health
      ;;
    backup)
      execute_system_backup
      ;;
    restore)
      local bk_file="${1:-}"
      if [ -z "$bk_file" ]; then
        log_error "Please specify backup file path."
        echo "Usage: unotusk restore /opt/unotusk/backups/unotusk_backup_timestamp.tar.gz"
        exit 1
      fi
      execute_system_restore "$bk_file"
      ;;
    update)
      if [ -f "$INSTALL_DIR/upgrade.sh" ]; then
        bash "$INSTALL_DIR/upgrade.sh"
      else
        log_error "upgrade.sh not found in $INSTALL_DIR."
      fi
      ;;
    rollback)
      trigger_rollback
      ;;
    uninstall)
      if [ -f "$INSTALL_DIR/uninstall.sh" ]; then
        bash "$INSTALL_DIR/uninstall.sh"
      else
        log_error "uninstall.sh not found in $INSTALL_DIR."
      fi
      ;;
    help|--help|-h|"")
      show_cli_usage
      ;;
    *)
      log_error "Unknown CLI command: '$cmd'."
      show_cli_usage
      exit 1
      ;;
  esac
}
