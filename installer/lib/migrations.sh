#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Database Schema Migrations Driver
# ==============================================================================

# Parse migrations manifest and run pending SQL migrations
execute_database_migrations() {
  log_to_file_info "Migrations" "Checking for pending database schema migrations..."
  log_info "Evaluating database schema migrations..."

  local migrations_manifest="$INSTALL_DIR/migrations/manifest.yaml"
  if [ ! -f "$migrations_manifest" ]; then
    migrations_manifest="$INSTALLER_ROOT/migrations/manifest.yaml"
  fi

  if [ ! -f "$migrations_manifest" ]; then
    log_to_file_info "Migrations" "No migrations manifest found. Skipping migrations step."
    return 0
  fi

  local db_container
  db_container=$(cd "$INSTALL_DIR" && docker compose ps -q postgres 2>/dev/null || true)
  if [ -z "$db_container" ]; then
    log_fatal_err "PostgreSQL container is offline. Migrations cannot be executed." "Ensure Postgres container is running." "https://docs.unotusk.com" "161"
  fi

  # Create history table if not exists in both databases
  for db_name in auth company; do
    log_to_file_info "Migrations" "Initializing history tracker table on logical database '$db_name'..."
    docker exec -i "$db_container" psql -U unotusk -d "$db_name" -c "
      CREATE TABLE IF NOT EXISTS schema_migration_history (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255) UNIQUE NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    " &>>"$INSTALL_LOG"
  done

  # Parse manifest line by line to discover SQL files
  local sql_files
  sql_files=$(grep 'file:' "$migrations_manifest" | awk '{print $2}' | tr -d '"' | tr -d "'" || echo "")

  for sql_file in $sql_files; do
    local full_path="$INSTALL_DIR/migrations/$sql_file"
    if [ ! -f "$full_path" ]; then
      full_path="$INSTALLER_ROOT/migrations/$sql_file"
    fi
    
    [ -f "$full_path" ] || continue

    # Check if migration has already been run for both databases
    for db_name in auth company; do
      local check_run
      check_run=$(docker exec -i "$db_container" psql -U unotusk -d "$db_name" -t -c "
        SELECT 1 FROM schema_migration_history WHERE filename = '$sql_file';
      " | tr -d ' ' || echo "0")

      if [ "$check_run" = "1" ]; then
        log_to_file_info "Migrations" "Migration $sql_file already applied on $db_name (idempotent skip)."
      else
        log_info "Applying migration $sql_file to $db_name database..."
        log_to_file_info "Migrations" "Executing DDL script: $full_path against $db_name"
        
        # Run SQL migration script
        if docker exec -i "$db_container" psql -U unotusk -d "$db_name" < "$full_path" &>>"$INSTALL_LOG"; then
          # Record success in migration history
          docker exec -i "$db_container" psql -U unotusk -d "$db_name" -c "
            INSERT INTO schema_migration_history (filename) VALUES ('$sql_file');
          " &>>"$INSTALL_LOG"
          log_success "Applied schema migration: $sql_file to $db_name"
        else
          log_fatal_err \
            "Database schema migration script '$sql_file' failed to compile on '$db_name' database." \
            "Review SQL statements syntax and database connection status." \
            "https://docs.unotusk.com/ops/db-trouble#migrations-error" \
            "181"
        fi
      fi
    done
  done

  log_to_file_info "Migrations" "Database schema migrations completed successfully."
}
