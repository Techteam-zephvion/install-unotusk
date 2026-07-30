#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Wrapper — Log Rotation Utility
# ==============================================================================
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
# Sourcing helpers
# shellcheck source=lib/common.sh
source "$INSTALL_DIR/lib/common.sh"

MAX_BACKUPS=5
MAX_SIZE_BYTES=10485760 # 10MB

rotate_file() {
  local target_file="$1"
  [ -f "$target_file" ] || return 0
  
  local file_size
  file_size=$(stat -c "%s" "$target_file" 2>/dev/null || stat -f "%z" "$target_file" 2>/dev/null || echo 0)
  
  if [ "$file_size" -gt "$MAX_SIZE_BYTES" ]; then
    log_to_file_info "Rotating file $target_file (size: $file_size bytes)..."
    
    # Remove oldest backup
    if [ -f "${target_file}.${MAX_BACKUPS}" ]; then
      rm -f "${target_file}.${MAX_BACKUPS}"
    fi

    # Shift backups: .4 -> .5, .3 -> .4 ...
    for i in $(seq $((MAX_BACKUPS - 1)) -1 1); do
      if [ -f "${target_file}.${i}" ]; then
        mv "${target_file}.${i}" "${target_file}.$((i + 1))"
      fi
    done

    # Move current log
    mv "$target_file" "${target_file}.1"
    
    # Re-create empty file with secure permissions
    touch "$target_file"
    chmod 600 "$target_file"
    
    # Compress the rotated backup in the background
    gzip -f "${target_file}.1" 2>/dev/null || true
    
    log_to_file_info "File rotation completed: ${target_file}.1.gz created."
  fi
}

log_to_file_info "Executing log rotation check..."

# Rotate main install log
rotate_file "$INSTALL_LOG"

# Rotate service stdout logs
if [ -d "$LOG_DIR" ]; then
  for lf in "$LOG_DIR"/*.log; do
    [ -f "$lf" ] || continue
    rotate_file "$lf"
  done
fi

log_to_file_info "Log rotation run completed."
