#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Docker Compose Execution Library
# ==============================================================================

# Run a docker compose command, hiding its stdout/stderr output unless it fails
# Usage: execute_compose [compose_args...]
execute_compose() {
  local args=("$@")
  local temp_log
  temp_log=$(mktemp)
  
  log_to_file_info "Executing: docker compose ${args[*]}"
  
  # Ensure we run from the installation folder where docker-compose.yml resides
  if (cd "$INSTALL_DIR" && docker compose "${args[@]}" > "$temp_log" 2>&1); then
    # Success, remove temporary output log
    rm -f "$temp_log"
    return 0
  else
    # Error occurred, capture log and print it
    local exit_code=$?
    log_to_file_err "Command 'docker compose ${args[*]}' failed with exit code $exit_code."
    
    # Write details to the installation log
    echo "--- Docker Compose Output ---" >> "$INSTALL_LOG"
    cat "$temp_log" >> "$INSTALL_LOG"
    echo "-----------------------------" >> "$INSTALL_LOG"
    
    # Print the logs to stderr so the operator knows what went wrong
    log_error "Docker Compose failed to execute. Output:"
    cat "$temp_log" >&2
    rm -f "$temp_log"
    
    return $exit_code
  fi
}

# Pull down updated images defined in docker-compose.yml and verify their signatures
compose_pull_images() {
  # ── Offline Installation Check ──
  local offline_tar="$INSTALL_DIR/offline/images.tar"
  if [ -f "$offline_tar" ]; then
    log_info "Offline Mode: Loading cached container images from bundle..."
    log_to_file_info "Docker" "Found offline images bundle at $offline_tar. Running docker load..."
    if docker load -i "$offline_tar" &>>"$INSTALL_LOG"; then
      log_success "Offline container images loaded successfully."
      return 0
    else
      log_fatal_err \
        "Failed to load offline container images from archive." \
        "Verify archive integrity and free disk space." \
        "https://docs.unotusk.com/ops/offline-errors" \
        "143"
    fi
  fi

  log_to_file_info "Pulling Docker images from registry..."
  # Pull per-service rather than as one batch: `docker compose pull` (no
  # args) aborts the entire batch on the first failing image, so a private
  # unotusk/* image (not published to any registry yet — tracked gap, needs
  # a CI pipeline pushing to one before this is a real customer-facing
  # install path) would prevent genuinely public images (redis, caddy,
  # postgres, qdrant, phoenix) from ever being attempted.
  local services
  services=$(cd "$INSTALL_DIR" && docker compose config --services 2>/dev/null)
  while IFS= read -r svc; do
    [ -z "$svc" ] && continue
    execute_compose pull "$svc" || log_to_file_warn "Registry pull failed for '$svc' — will check for a locally cached image below."
  done <<< "$services"

  # `--images <service>` includes that service's depends_on closure (e.g.
  # `--images us` also lists postgres), so check the deduplicated whole-file
  # image list once here rather than per-service.
  local missing=()
  local all_images
  all_images=$(cd "$INSTALL_DIR" && docker compose config --images 2>/dev/null)
  while IFS= read -r img; do
    [ -z "$img" ] && continue
    docker image inspect "$img" &>/dev/null || missing+=("$img")
  done <<< "$all_images"

  if [ ${#missing[@]} -ne 0 ]; then
    log_fatal_err \
      "Failed to pull Docker images from registry, and these are missing locally too: ${missing[*]}" \
      "Verify registry connectivity, check DNS resolvers, and try again." \
      "https://docs.unotusk.com/ops/installation#image-pull-errors" \
      "140"
  fi

  # Parse manifest.json and run signature verification checks
  local manifest_path="$INSTALL_DIR/manifest.json"
  if [ ! -f "$manifest_path" ]; then
    manifest_path="$INSTALLER_ROOT/manifest.json"
  fi

  if [ -f "$manifest_path" ] && command -v python3 &>/dev/null; then
    log_to_file_info "Docker" "Validating image signatures from manifest: $manifest_path"
    local images
    images=$(python3 -c "
import json, sys
try:
    with open('$manifest_path') as f:
        data = json.load(f)
        for img in data.get('images', {}).values():
            print(img)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "")

    for img in $images; do
      verify_container_image "$img"
    done
  fi
}

# Verify validity of the docker-compose config
compose_validate_config() {
  log_to_file_info "Validating Docker Compose configuration file..."
  if ! execute_compose config --quiet; then
    log_fatal_err \
      "docker-compose.yml config file is invalid." \
      "Review logs under /var/log/unotusk-install.log and template files." \
      "https://docs.unotusk.com/ops/installation#compose-syntax-errors" \
      "141"
  fi
}
