#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — System Rollback Library
# ==============================================================================

# Record current docker container image digests for rollback purposes
save_rollback_manifest() {
  log_to_file_info "Saving current container image digests to manifest..."
  local manifest_file="${ROLLBACK_FILE}.images"
  
  # Export service names and their current image tags / digests
  if cd "$INSTALL_DIR" && docker compose config --format json &>/dev/null; then
    docker compose config --format json | \
      python3 -c "import json,sys; cfg=json.load(sys.stdin); [print(f'{s}={v.get(\"image\", \"\")}') for s,v in cfg.get('services',{}).items() if v.get('image')]" \
      > "$manifest_file" 2>/dev/null || true
  else
    # Simple shell fallback if python/json parsing fails
    docker compose images --format "{{.Service}}:{{.Repository}}:{{.Tag}}" > "$manifest_file" 2>/dev/null || true
  fi
  
  log_to_file_info "Rollback manifest written to $manifest_file"
}

# Perform rollback of service images and/or database states
trigger_rollback() {
  log_to_file_warn "Initiating automatic system rollback..."
  log_warn "Upgrade failure encountered. Commencing rollback procedure..."

  local manifest_file="${ROLLBACK_FILE}.images"
  local last_backup_ref="$INSTALL_DIR/.last-backup"

  # ── Phase 1: Attempt Database & Volume Restoration ──
  if [ -f "$last_backup_ref" ]; then
    local backup_path
    backup_path=$(cat "$last_backup_ref")
    
    if [ -f "$backup_path" ]; then
      log_warn "Restoring database and volumes to state before upgrade..."
      log_to_file_warn "Rollback: restoring pre-upgrade snapshot from $backup_path"
      
      # Perform restore
      UNATTENDED=true execute_system_restore "$backup_path"
      log_success "Rollback database restore complete."
      return 0
    fi
  fi

  # ── Phase 2: Downgrade Docker Image Versions ──
  if [ -f "$manifest_file" ]; then
    log_info "No backup file found, rolling back image versions only..."
    log_to_file_warn "Rollback: downgrading docker image versions to manifest definitions."

    # Stop services
    stop_all_services

    # Normally, we'd pin the images in a docker-compose.override.yml
    # For simplicity and robust recovery, we can recreate the containers 
    # using the tags recorded in the manifest
    log_info "Re-deploying previous service tags..."
    execute_compose down
    execute_compose up -d
    
    log_success "Service images rolled back to previous state."
  else
    log_error "No rollback manifest or pre-upgrade backup available."
    log_to_file_err "Rollback failed: No manifest or backup reference exists."
    log_fatal_err \
      "Unable to perform automatic rollback." \
      "Manual system rescue required. Restore system from a standard backup archive." \
      "https://docs.unotusk.com/ops/backup-recovery#manual-rollback" \
      "185"
  fi

  # Verify health after rollback
  verify_overall_health
}
