#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Logging and Error Handling Library
# ==============================================================================

# Default installation log file path
DEFAULT_LOG_FILE="/var/log/unotusk-install.log"
INSTALL_LOG="${INSTALL_LOG:-$DEFAULT_LOG_FILE}"

# Setup log file permissions and existence safely
init_logging() {
  local log_dir
  log_dir=$(dirname "$INSTALL_LOG")
  
  # Fallback immediately if target log directory is not writable and file doesn't exist
  if [ ! -d "$log_dir" ] || [ ! -w "$log_dir" ]; then
    if [ ! -f "$INSTALL_LOG" ] || [ ! -w "$INSTALL_LOG" ]; then
      INSTALL_LOG="/tmp/unotusk-install.log"
      log_dir="/tmp"
    fi
  fi

  if [ ! -f "$INSTALL_LOG" ]; then
    touch "$INSTALL_LOG" 2>/dev/null || INSTALL_LOG="/tmp/unotusk-install.log"
  fi

  # Double check writability of the resolved file
  if [ ! -w "$INSTALL_LOG" ]; then
    INSTALL_LOG="/tmp/unotusk-install.log"
    touch "$INSTALL_LOG" 2>/dev/null || true
  fi
  
  # Ensure only root/restricted access since secrets might be logged (though we avoid logging secrets)
  chmod 600 "$INSTALL_LOG" 2>/dev/null || true
}

# Write message to the log file in JSON Lines (JSONL) format
# Usage: write_log "LEVEL" "Module" "Message"
write_log() {
  local level="$1"
  local module="$2"
  shift 2
  local msg="$*"
  
  # Escape quotes for JSON safety
  local escaped_msg
  escaped_msg=$(echo "$msg" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' 2>/dev/null || echo "$msg")
  
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  
  # Write structured JSON to log file
  printf '{"timestamp":"%s","level":"%s","module":"%s","message":"%s"}\n' \
    "$timestamp" "$level" "$module" "$escaped_msg" >> "$INSTALL_LOG"
}

# Log helper wrappers supporting optional module tagging
log_to_file_info()  {
  if [ "$#" -ge 2 ]; then
    write_log "INFO" "$1" "${@:2}"
  else
    write_log "INFO" "core" "$1"
  fi
}
log_to_file_warn()  {
  if [ "$#" -ge 2 ]; then
    write_log "WARN" "$1" "${@:2}"
  else
    write_log "WARN" "core" "$1"
  fi
}
log_to_file_err()   {
  if [ "$#" -ge 2 ]; then
    write_log "ERROR" "$1" "${@:2}"
  else
    write_log "ERROR" "core" "$1"
  fi
}
log_to_file_debug() {
  if [ "$#" -ge 2 ]; then
    write_log "DEBUG" "$1" "${@:2}"
  else
    write_log "DEBUG" "core" "$1"
  fi
}

# Structured exit on error
# Usage: log_fatal_err "Reason" "Possible Fix" "Documentation Link" "Exit Code"
log_fatal_err() {
  local reason="$1"
  local fix="$2"
  local doc_link="$3"
  local code="${4:-1}"

  log_to_file_err "FATAL ERROR (Exit Code: $code): $reason. Suggested Fix: $fix. Docs: $doc_link"

  # Print structured block to stdout/stderr
  echo "" >&2
  echo -e "${RED}${BOLD}✘ ERROR: Operation Failed${RESET}" >&2
  echo -e "  ${BOLD}Reason:${RESET}         $reason" >&2
  echo -e "  ${BOLD}Possible Fix:${RESET}   $fix" >&2
  echo -e "  ${BOLD}Documentation:${RESET}  $doc_link" >&2
  echo -e "  ${BOLD}Exit Code:${RESET}      $code" >&2
  echo "" >&2

  exit "$code"
}

# Initialize logging when this library is sourced
init_logging
