#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Filesystem and Path Management Library
# ==============================================================================

# Ensure directory is writable or create it
setup_install_directory() {
  log_to_file_info "Preparing filesystem directories at $INSTALL_DIR..."
  
  # Ensure base folder exists
  if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR" 2>/dev/null || {
      log_fatal_err \
        "Failed to create directory $INSTALL_DIR." \
        "Verify root permissions and filesystem write capabilities." \
        "https://docs.unotusk.com/ops/installation#filesystem-errors" \
        "110"
    }
  fi

  # Verify write access
  if ! touch "$INSTALL_DIR/.write-test" 2>/dev/null; then
    log_fatal_err \
      "Installation directory $INSTALL_DIR is not writable." \
      "Run the installer as root or grant write access to $INSTALL_DIR." \
      "https://docs.unotusk.com/ops/installation#filesystem-errors" \
      "111"
  fi
  rm -f "$INSTALL_DIR/.write-test"

  # Create required subdirectories under /opt/unotusk
  mkdir -p "$LOG_DIR" \
           "$BACKUP_DIR" \
           "$INSTALL_DIR/templates" \
           "$INSTALL_DIR/lib" \
           "$INSTALL_DIR/systemd" \
           "$INSTALL_DIR/scripts" \
           "$INSTALL_DIR/docs" \
           "$INSTALL_DIR/integrations" \
           "$INSTALL_DIR/migrations" \
           "$INSTALL_DIR/US/certs" \
           "$INSTALL_DIR/UPS/certs/platform" \
           "$INSTALL_DIR/AI-PIE/certs/dev" \
           "$INSTALL_DIR/caddy/certs"

  # Set secure permissions on target folders
  chmod 755 "$INSTALL_DIR"
  chmod 700 "$BACKUP_DIR"
  chmod 755 "$LOG_DIR"

  log_to_file_info "Directory structure created successfully under $INSTALL_DIR."
}

# Copy installation files from source package to opt/unotusk
deploy_installer_resources() {
  log_to_file_info "Deploying installer resources to $INSTALL_DIR..."

  # Copy settings and manifests files
  cp "$INSTALLER_ROOT/manifest.json" "$INSTALL_DIR/manifest.json" 2>/dev/null || true
  cp "$INSTALLER_ROOT/settings.yaml" "$INSTALL_DIR/settings.yaml" 2>/dev/null || true

  # Copy libraries
  cp -r "$INSTALLER_ROOT/lib/"* "$INSTALL_DIR/lib/"
  
  # Copy templates
  cp -r "$INSTALLER_ROOT/templates/"* "$INSTALL_DIR/templates/" 2>/dev/null || true

  # execute_compose (compose.sh) runs `docker compose` from $INSTALL_DIR with
  # no -f flag, so it needs docker-compose.yml directly there — not just
  # inside templates/. Every relative volume path in the file (./US/certs,
  # ./scripts/init-databases.sh, ./templates/Caddyfile, ...) assumes
  # $INSTALL_DIR itself is the compose project directory, so this must be a
  # copy at $INSTALL_DIR root, not a move out of templates/.
  cp "$INSTALLER_ROOT/templates/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml"

  # Copy scripts
  cp -r "$INSTALLER_ROOT/scripts/"* "$INSTALL_DIR/scripts/" 2>/dev/null || true

  # Copy systemd
  cp -r "$INSTALLER_ROOT/systemd/"* "$INSTALL_DIR/systemd/" 2>/dev/null || true

  # Copy docs
  cp -r "$INSTALLER_ROOT/docs/"* "$INSTALL_DIR/docs/" 2>/dev/null || true

  # Copy integrations
  cp -r "$INSTALLER_ROOT/integrations/"* "$INSTALL_DIR/integrations/" 2>/dev/null || true

  # Copy migrations
  cp -r "$INSTALLER_ROOT/migrations/"* "$INSTALL_DIR/migrations/" 2>/dev/null || true

  # Re-apply executable permissions where necessary
  chmod +x "$INSTALL_DIR/scripts/"*.sh 2>/dev/null || true
  chmod +x "$INSTALL_DIR/integrations/"*/*.sh 2>/dev/null || true
  chmod +x "$INSTALL_DIR/"*.sh 2>/dev/null || true
  
  log_to_file_info "Installer files copied and structured."
}

# Enforce secure permission settings on config files
secure_configuration_files() {
  log_to_file_info "Applying secure permissions to credentials and configurations..."
  
  for f in "$ENV_FILE" "$WIZARD_CONF" "$SECRETS_FILE" "$OAUTH_SECRET_FILE"; do
    if [ -f "$f" ]; then
      chmod 600 "$f"
      log_to_file_info "Permissions set: chmod 600 for $f"
    fi
  done
}
