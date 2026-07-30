#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Plugin Framework Orchestrator
# ==============================================================================

# Dynamic list to hold active plugin names
ACTIVE_PLUGINS=()

# Discover and load all integration plugins
load_plugins() {
  log_to_file_info "Plugins" "Scanning integrations plugins..."
  ACTIVE_PLUGINS=()
  
  local search_dir="$INSTALL_DIR/integrations"
  if [ ! -d "$search_dir" ]; then
    search_dir="$INSTALLER_ROOT/integrations"
  fi

  [ -d "$search_dir" ] || return 0

  # Source all integration plugin files
  for plugin_script in "$search_dir"/*/*.sh; do
    if [ -f "$plugin_script" ]; then
      # Extract plugin name from folder
      local p_name
      p_name=$(basename "$(dirname "$plugin_script")")
      
      log_to_file_info "Plugins" "Loading plugin: $p_name from $plugin_script"
      
      # Source the script
      # shellcheck disable=SC1090
      if source "$plugin_script"; then
        ACTIVE_PLUGINS+=("$p_name")
      else
        log_to_file_err "Plugins" "Failed to source plugin script: $plugin_script"
      fi
    fi
  done
}

# Run install hook across all plugins
run_plugins_install() {
  load_plugins
  for p in "${ACTIVE_PLUGINS[@]}"; do
    local hook="${p}_install"
    if command -v "$hook" &>/dev/null; then
      log_info "Plugin: running install hook for '$p'..."
      "$hook"
    fi
  done
}

# Run configure hook across all plugins
run_plugins_configure() {
  load_plugins
  for p in "${ACTIVE_PLUGINS[@]}"; do
    local hook="${p}_configure"
    if command -v "$hook" &>/dev/null; then
      log_to_file_info "Plugins" "Running configure hook for $p"
      "$hook"
    fi
  done
}

# Run validate hook across all plugins
run_plugins_validate() {
  load_plugins
  for p in "${ACTIVE_PLUGINS[@]}"; do
    local hook="${p}_validate"
    if command -v "$hook" &>/dev/null; then
      log_to_file_info "Plugins" "Running validate hook for $p"
      if ! "$hook"; then
        log_to_file_err "Plugins" "Validation hook for plugin '$p' returned exit code failure."
      fi
    fi
  done
}

# Run health hook across all plugins
run_plugins_health() {
  load_plugins
  local fails=0
  for p in "${ACTIVE_PLUGINS[@]}"; do
    local hook="${p}_health"
    if command -v "$hook" &>/dev/null; then
      log_to_file_info "Plugins" "Running health check hook for $p"
      if ! "$hook"; then
        log_warn "Plugin health check failed: $p"
        fails=$((fails + 1))
      fi
    fi
  done
  return "$fails"
}

# Run uninstall hook across all plugins
run_plugins_uninstall() {
  load_plugins
  for p in "${ACTIVE_PLUGINS[@]}"; do
    local hook="${p}_uninstall"
    if command -v "$hook" &>/dev/null; then
      log_info "Plugin: running uninstall hook for '$p'..."
      "$hook"
    fi
  done
}
