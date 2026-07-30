#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Platform — Platform Upgrade Utility
# Usage: sudo ./upgrade.sh [--channel stable|lts|beta|nightly]
# ==============================================================================
set -euo pipefail

# Sourcing libraries
INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
LIB_DIR="$INSTALL_DIR/lib"

if [ -d "$LIB_DIR" ]; then
  # shellcheck source=lib/common.sh
  source "$LIB_DIR/common.sh"
  # shellcheck source=lib/compose.sh
  source "$LIB_DIR/compose.sh"
  # shellcheck source=lib/backup.sh
  source "$LIB_DIR/backup.sh"
  # shellcheck source=lib/rollback.sh
  source "$LIB_DIR/rollback.sh"
  # shellcheck source=lib/health.sh
  source "$LIB_DIR/health.sh"
  # shellcheck source=lib/services.sh
  source "$LIB_DIR/services.sh"
  # shellcheck source=lib/restore.sh
  source "$LIB_DIR/restore.sh"
else
  # Local source context fallback
  SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SRC_DIR/lib/common.sh"
  # shellcheck source=lib/compose.sh
  source "$SRC_DIR/lib/compose.sh"
  # shellcheck source=lib/backup.sh
  source "$SRC_DIR/lib/backup.sh"
  # shellcheck source=lib/rollback.sh
  source "$SRC_DIR/lib/rollback.sh"
  # shellcheck source=lib/health.sh
  source "$SRC_DIR/lib/health.sh"
  # shellcheck source=lib/services.sh
  source "$SRC_DIR/lib/services.sh"
  # shellcheck source=lib/restore.sh
  source "$SRC_DIR/lib/restore.sh"
fi

main() {
  log_title "UNOTUSK Platform Upgrade Utility"

  # Privilege Check
  check_root

  # ── Parse Channel Option ──
  local channel="stable"
  while [ $# -gt 0 ]; do
    case "$1" in
      --channel)
        if [ -n "${2:-}" ]; then
          channel="$2"
          shift 2
        else
          log_fatal_err "--channel requires an argument (stable|lts|beta|nightly)." "Re-run specifying a channel." "https://docs.unotusk.com" "10"
        fi
        ;;
      *)
        shift
        ;;
    esac
  done

  log_info "Target upgrade channel: $channel"

  # Fetch remote manifest for this channel if online
  local manifest_url="https://install.unotusk.com/manifests/${channel}.json"
  log_to_file_info "Upgrades" "Pulling update channel manifest from $manifest_url"
  if curl -sf --max-time 10 "$manifest_url" -o "$INSTALL_DIR/manifest.json.tmp" 2>/dev/null; then
    mv "$INSTALL_DIR/manifest.json.tmp" "$INSTALL_DIR/manifest.json"
    log_success "Updated version manifest loaded from '$channel' channel."
  else
    log_warn "Could not fetch remote version manifest for channel '$channel'. Utilizing local manifest."
    log_to_file_warn "Upgrades" "Remote manifest download failed for channel $channel, utilizing local manifest cache."
  fi

  # Get Current version
  local current_ver="unknown"
  if [ -f "$VERSION_FILE" ]; then
    current_ver=$(grep '^INSTALL_VERSION=' "$VERSION_FILE" | cut -d= -f2- || echo "unknown")
  fi
  log_info "Current installed version: $current_ver"

  # ── 1. Create Rollback Manifest ──
  log_info "Creating upgrade rollback manifest..."
  save_rollback_manifest

  # ── 2. Run Pre-Upgrade System Backup ──
  log_info "Creating pre-upgrade snapshot backup..."
  execute_system_backup

  # Store the name of the last generated backup so rollback can target it
  local last_backup_file
  last_backup_file=$(ls -1t "$BACKUP_DIR"/unotusk_backup_*.tar.gz 2>/dev/null | head -1 || echo "")
  if [ -f "$last_backup_file" ]; then
    echo "$last_backup_file" > "$INSTALL_DIR/.last-backup"
    log_to_file_info "Stored pre-upgrade backup reference: $last_backup_file"
  fi

  # ── 3. Pull New Container Images ──
  log_info "Pulling updated Docker container images..."
  compose_pull_images

  # ── 4. Boot PostgreSQL Database to Execute Migrations ──
  log_info "Starting Postgres database to apply migrations..."
  if ! execute_compose up -d postgres; then
    log_to_file_err "PostgreSQL failed to boot during upgrade."
    trigger_rollback
    exit 1
  fi
  if ! wait_for_service_health postgres 90; then
    log_to_file_err "Database did not report healthy, rolling back."
    trigger_rollback
    exit 1
  fi

  # ── 5. Run Database Schema Migrations ──
  log_info "Running schema migrations..."
  if [ -f "$INSTALL_DIR/scripts/migrate.sh" ]; then
    if ! bash "$INSTALL_DIR/scripts/migrate.sh" &>>"$INSTALL_LOG"; then
      log_to_file_err "Database migration script failed, rolling back."
      trigger_rollback
      exit 1
    fi
    log_success "Database migrations applied successfully."
  else
    log_warn "Migration script missing. Skipping explicit migration phase."
  fi

  # ── 6. Deploy Updated Containers Stack ──
  log_info "Deploying updated containers..."
  if ! start_all_services; then
    log_to_file_err "Failed to restart containers during upgrade. Starting rollback."
    trigger_rollback
    exit 1
  fi

  # ── 7. Verify Health Validation Checks ──
  log_info "Verifying health checks after upgrade..."
  if ! verify_overall_health; then
    log_to_file_err "Post-upgrade health verification failed. Starting rollback."
    trigger_rollback
    exit 1
  fi

  # Update version file metadata
  if [ -f "$VERSION_FILE" ]; then
    local new_ver
    new_ver=$(date +%Y%m%d)
    sed -i "s/^INSTALL_VERSION=.*/INSTALL_VERSION=${new_ver}-upgrade/" "$VERSION_FILE" || true
  fi

  # Remove rollback helper artifacts on successful upgrade
  rm -f "$INSTALL_DIR/.last-backup"
  rm -f "${ROLLBACK_FILE}.images"

  log_title "Upgrade Completed Successfully!"
  echo ""
}

main "$@"
