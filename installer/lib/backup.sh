#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — System Backup Library
# ==============================================================================

# Run system backup and save archive in backups folder
execute_system_backup() {
  log_to_file_info "Initiating system backup procedure..."
  log_info "Creating a complete UNOTUSK backup..."

  local timestamp
  timestamp=$(date +%Y%m%d_%H%M%S)
  local backup_archive="$BACKUP_DIR/unotusk_backup_${timestamp}.tar.gz"
  local staging_dir="$BACKUP_DIR/staging_${timestamp}"

  # Ensure folders exist
  mkdir -p "$staging_dir/db" \
           "$staging_dir/certs" \
           "$staging_dir/config" \
           "$staging_dir/volumes" \
           "$staging_dir/logs"

  # ── 1. PostgreSQL DB Dump ──
  log_to_file_info "Dumping databases..."
  log_info "Extracting PostgreSQL database states..."
  
  local db_container
  db_container=$(cd "$INSTALL_DIR" && docker compose ps -q postgres 2>/dev/null || true)
  
  if [ -n "$db_container" ] && docker ps --format '{{.ID}}' | grep -q "$db_container"; then
    # PostgreSQL is running, extract SQL dumps
    docker exec -t "$db_container" pg_dump -U unotusk auth > "$staging_dir/db/auth.sql" 2>/dev/null || \
      log_to_file_warn "Auth database dump did not finish cleanly (may not exist)."
    docker exec -t "$db_container" pg_dump -U unotusk company > "$staging_dir/db/company.sql" 2>/dev/null || \
      log_to_file_warn "Company database dump did not finish cleanly (may not exist)."
    log_to_file_info "PostgreSQL dumps successfully created."
  else
    log_warn "Postgres container is offline. Volume snapshot will capture database state, skipping SQL dump."
    log_to_file_warn "PostgreSQL offline, bypassing SQL dump."
  fi

  # ── 2. Configuration Files ──
  log_to_file_info "Backing up configuration and secret files..."
  for f in "$ENV_FILE" "$WIZARD_CONF" "$SECRETS_FILE" "$OAUTH_SECRET_FILE" "$VERSION_FILE"; do
    if [ -f "$f" ]; then
      cp "$f" "$staging_dir/config/"
    fi
  done
  # Service local configs
  for service in US UPS AI-PIE; do
    if [ -f "$INSTALL_DIR/$service/.env" ]; then
      mkdir -p "$staging_dir/config/$service"
      cp "$INSTALL_DIR/$service/.env" "$staging_dir/config/$service/"
    fi
  done

  # ── 3. TLS Certificates ──
  log_to_file_info "Backing up system cert structures..."
  for cert_path in US/certs UPS/certs AI-PIE/certs caddy/certs; do
    if [ -d "$INSTALL_DIR/$cert_path" ]; then
      local dest
      dest="$staging_dir/certs/$(echo "$cert_path" | tr '/' '_')"
      mkdir -p "$dest"
      cp -r "$INSTALL_DIR/$cert_path/"* "$dest/" 2>/dev/null || true
    fi
  done

  # ── 4. Volume Snapshots ──
  log_info "Snapshotting persistent volumes..."
  
  # Fetch project folder name for volume prefixes
  local project_name
  project_name=$(basename "$INSTALL_DIR")
  
  # List of volumes to backup
  local volumes=(
    "${project_name}_postgres_data:postgres_data"
    "${project_name}_qdrant_data:qdrant_data"
    "${project_name}_phoenix_data:phoenix_data"
    "${project_name}_us_data:us_data"
    "${project_name}_ups_data:ups_data"
    "${project_name}_ai_pie_data:ai_pie_data"
  )

  for item in "${volumes[@]}"; do
    local vol="${item%%:*}"
    local name="${item##*:}"
    log_to_file_info "Snapshotting volume $vol as $name..."

    # Use a temporary docker container to archive volume
    if docker run --rm \
      -v "$vol:/volume_data:ro" \
      -v "$staging_dir/volumes:/backup_target" \
      alpine tar -czf "/backup_target/${name}.tar.gz" -C /volume_data . 2>/dev/null; then
      log_to_file_info "Volume snapshot successful: $vol"
    else
      log_to_file_warn "Failed to create raw snapshot of volume $vol. Container data may be locked."
    fi
  done

  # ── 5. System Logs ──
  log_to_file_info "Archiving current system logs..."
  if [ -d "$LOG_DIR" ]; then
    cp -r "$LOG_DIR/"* "$staging_dir/logs/" 2>/dev/null || true
  fi

  # ── 6. Assemble Archive ──
  log_info "Assembling final backup archive..."
  if ! tar -czf "$backup_archive" -C "$BACKUP_DIR" "staging_${timestamp}" 2>/dev/null; then
    rm -rf "$staging_dir"
    log_fatal_err \
      "Backup compression phase failed." \
      "Verify write access and available disk space in $BACKUP_DIR." \
      "https://docs.unotusk.com/ops/backup-recovery#compression-failed" \
      "180"
  fi

  # Cleanup staging directory
  rm -rf "$staging_dir"

  # Restrict permissions
  chmod 600 "$backup_archive"

  # Generate sha256 checksum
  local sha
  sha=$(sha256sum "$backup_archive" | awk '{print $1}')
  echo "$sha" > "${backup_archive}.sha256"

  log_success "Backup file created: $backup_archive"
  log_info "Backup SHA256 Checksum: $sha"
  log_to_file_info "System backup finished. File: $backup_archive, SHA256: $sha"
  
  return 0
}
