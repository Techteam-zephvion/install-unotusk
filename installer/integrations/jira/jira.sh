#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Integration Plugin — Jira
# ==============================================================================

jira_install() {
  log_to_file_info "Plugin: jira" "Installing Jira integration plugin..."
  mkdir -p "$INSTALL_DIR/integrations/jira"
}

jira_configure() {
  log_to_file_info "Plugin: jira" "Configuring Jira integration plugin..."
  if [ -n "${JIRA_URL:-}" ]; then
    log_to_file_info "Plugin: jira" "Jira API target set to: $JIRA_URL"
  fi
}

jira_validate() {
  log_to_file_info "Plugin: jira" "Validating Jira integration parameters..."
  if [ -n "${JIRA_URL:-}" ]; then
    local host
    host=$(echo "$JIRA_URL" | sed -E 's|https?://([^:/]+).*|\1|')
    if nslookup "$host" &>/dev/null || host "$host" &>/dev/null; then
      log_to_file_info "Plugin: jira" "Jira host '$host' resolved successfully"
      return 0
    else
      log_to_file_warn "Plugin: jira" "Unable to resolve Jira host '$host'."
      return 0
    fi
  fi
  return 0
}

jira_health() {
  log_to_file_info "Plugin: jira" "Evaluating Jira plugin status..."
  if [ -n "${JIRA_URL:-}" ]; then
    return 0
  fi
  return 0
}

jira_uninstall() {
  log_to_file_info "Plugin: jira" "Uninstalling Jira integration plugin..."
  rm -rf "$INSTALL_DIR/integrations/jira"
}
