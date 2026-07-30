#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — System Restore Library
# ==============================================================================

# Verify sha256 checksum integrity of backup file
verify_backup_integrity() {
  local backup_file="$1"
  log_to_file_info "Validating backup integrity for $backup_file..."

  if [ ! -f "$backup_file" ]; then
    log_fatal_err \
      "Backup file '$backup_file' does not exist." \
      "Verify the file path and try again." \
      "https://docs.unotusk.com/ops/backup-recovery#file-not-found" \
      "190"
  fi

  local sha_file="${backup_file}.sha256"
  if [ -f "$sha_file" ]; then
    local expected_sha
    expected_sha=$(cat "$sha_file" | awk '{print $1}')
    local actual_sha
    actual_sha=$(sha256sum "$backup_file" | awk '{print $1}')
    
    if [ "$expected_sha" != "$actual_sha" ]; then
      log_fatal_err \
        "Backup archive checksum mismatch." \
        "The backup file may be corrupted. Expected: $expected_sha, Actual: $actual_sha" \
        "https://docs.unotusk.com/ops/backup-recovery#checksum-mismatch" \
        "191"
    fi
    log_to_file_info "Checksum verification: SUCCESS"
  else
    log_warn "SHA256 checksum file missing. Proceeding without checksum validation."
  fi
}

# Execute platform restore using backup package
# Usage: execute_system_restore <backup_archive_path>
execute_system_restore() {
  local archive_path="$1"
  
  # Validate file exists and is readable
  verify_backup_integrity "$archive_path"

  if [ -z "${UNATTENDED:-}" ]; then
    echo ""
    log_warn "WARNING: This restore procedure will overwrite current system databases, configs and volumes."
    read -r -p "  Are you sure you want to proceed? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      log_info "Restore operation aborted by operator."
      exit 0
    fi
  fi

  log_info "Executing system restore from $archive_path..."
  log_to_file_info "Starting restore operation..."

  # Create staging workspace
  local staging_dir
  staging_dir=$(mktemp -d)
  
  log_to_file_info "Staging directory created at $staging_dir"

  # Extract tarball
  log_to_file_info "Extracting backup archive..."
  if ! tar -xzf "$archive_path" -C "$staging_dir"; then
    rm -rf "$staging_dir"
    log_fatal_err "Failed to extract backup archive." "Verify zip utility and file health." "https://docs.unotusk.com/ops/backup-recovery#extraction-error" "192"
  fi

  # Find internal payload staging subdirectory
  local payload_dir
  payload_dir=$(find "$staging_dir" -mindepth 1 -maxdepth 1 -type d | head -1)
  if [ -z "$payload_dir" ]; then
    rm -rf "$staging_dir"
    log_fatal_err "Backup file structure is invalid." "Ensure backup file was created by a valid backup command." "https://docs.unotusk.com/ops/backup-recovery#invalid-structure" "193"
  fi

  # Stop stack to release file locks on volumes
  log_info "Stopping platform container stack..."
  stop_all_services

  # ── 1. Restore configuration files ──
  log_to_file_info "Restoring configuration files..."
  if [ -d "$payload_dir/config" ]; then
    cp -f "$payload_dir/config/.env" "$ENV_FILE" 2>/dev/null || true
    cp -f "$payload_dir/config/.env.wizard" "$WIZARD_CONF" 2>/dev/null || true
    cp -f "$payload_dir/config/.secrets" "$SECRETS_FILE" 2>/dev/null || true
    cp -f "$payload_dir/config/.oauth.secret" "$OAUTH_SECRET_FILE" 2>/dev/null || true
    cp -f "$payload_dir/config/.unotusk-version" "$VERSION_FILE" 2>/dev/null || true
    
    # Restore service envs
    for service in US UPS AI-PIE; do
      if [ -f "$payload_dir/config/$service/.env" ]; then
        mkdir -p "$INSTALL_DIR/$service"
        cp -f "$payload_dir/config/$service/.env" "$INSTALL_DIR/$service/.env"
      fi
    done
  fi

  # ── 2. Restore TLS Certificates ──
  log_to_file_info "Restoring TLS certificates..."
  if [ -d "$payload_dir/certs" ]; then
    for src in "$payload_dir/certs"/*; do
      if [ -d "$src" ]; then
        local target_folder
        target_folder=$(basename "$src" | tr '_' '/')
        mkdir -p "$INSTALL_DIR/$target_folder"
        cp -rf "$src/"* "$INSTALL_DIR/$target_folder/" 2>/dev/null || true
      fi
    done
  fi

  # ── 3. Restore Volumes ──
  log_info "Restoring persistent volumes..."
  local project_name
  project_name=$(basename "$INSTALL_DIR")
  
  if [ -d "$payload_dir/volumes" ]; then
    for archive in "$payload_dir/volumes"/*.tar.gz; do
      [ -f "$archive" ] || continue
      local vol_name
      vol_name=$(basename "$archive" .tar.gz)
      local full_vol_name="${project_name}_${vol_name}"

      log_to_file_info "Restoring volume data for $full_vol_name..."
      # Create volume if missing
      docker volume create "$full_vol_name" &>>"$INSTALL_LOG"

      # Re-hydrate volume data
      docker run --rm \
        -v "$full_vol_name:/volume_data" \
        -v "$payload_dir/volumes:/backup_source:ro" \
        alpine sh -c "rm -rf /volume_data/* && tar -xzf /backup_source/${vol_name}.tar.gz -C /volume_data" &>>"$INSTALL_LOG"
    done
  fi

  # ── 4. Re-boot database and restore SQL dumps ──
  log_info "Initializing databases..."
  execute_compose up -d postgres
  if ! wait_for_service_health postgres 90; then
    rm -rf "$staging_dir"
    log_fatal_err "PostgreSQL database failed to start during restore." "Check Postgres logs." "https://docs.unotusk.com/ops/db-trouble" "194"
  fi

  if [ -f "$payload_dir/db/auth.sql" ]; then
    log_to_file_info "Restoring 'auth' schema..."
    docker exec -i "$(cd "$INSTALL_DIR" && docker compose ps -q postgres)" psql -U unotusk -d auth < "$payload_dir/db/auth.sql" &>>"$INSTALL_LOG" || \
      log_to_file_warn "Failed to restore SQL dump on 'auth' database."
  fi

  if [ -f "$payload_dir/db/company.sql" ]; then
    log_to_file_info "Restoring 'company' schema..."
    docker exec -i "$(cd "$INSTALL_DIR" && docker compose ps -q postgres)" psql -U unotusk -d company < "$payload_dir/db/company.sql" &>>"$INSTALL_LOG" || \
      log_to_file_warn "Failed to restore SQL dump on 'company' database."
  fi

  # Clean staging directory
  rm -rf "$staging_dir"

  # Secure permissions
  secure_configuration_files

  # Restart all other services
  log_info "Starting platform services..."
  start_all_services

  log_success "System restore completed successfully."
  return 0
}
