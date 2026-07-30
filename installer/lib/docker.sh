#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Docker and Environment Configuration Library
# ==============================================================================

# Verify Docker engine is installed and running
validate_docker_engine() {
  log_to_file_info "Validating Docker Engine..."

  # 1. Check if docker is in PATH
  if ! command -v docker &>/dev/null; then
    log_fatal_err \
      "Docker Engine is not installed or not in PATH." \
      "Install Docker Engine (v24.0+) on this host before proceeding." \
      "https://docs.docker.com/engine/install/" \
      "130"
  fi

  # 2. Check if Docker daemon is running
  if ! docker info &>/dev/null; then
    log_fatal_err \
      "Docker daemon is not running." \
      "Start the Docker service (e.g., 'sudo systemctl start docker') and try again." \
      "https://docs.docker.com/config/daemon/" \
      "131"
  fi

  # 3. Check Docker major version
  local version
  version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
  local major
  major=$(echo "$version" | cut -d. -f1)
  
  if [ "$major" -lt "$MIN_DOCKER_VERSION" ]; then
    log_fatal_err \
      "Docker version $version is below the minimum required version ($MIN_DOCKER_VERSION)." \
      "Upgrade Docker Engine to version 24.0 or newer." \
      "https://docs.unotusk.com/ops/requirements#docker-engine" \
      "132"
  fi

  log_to_file_info "Docker Engine validation: version $version (Passed)"
}

# Verify Docker Compose v2 plugin is installed
validate_docker_compose() {
  log_to_file_info "Validating Docker Compose CLI Plugin..."

  if ! docker compose version &>/dev/null; then
    log_fatal_err \
      "Docker Compose V2 plugin is not installed." \
      "Install the 'docker-compose-plugin' packages (v2.0+) on this server." \
      "https://docs.docker.com/compose/install/linux/" \
      "133"
  fi
  
  local compose_ver
  compose_ver=$(docker compose version --short 2>/dev/null || echo "unknown")
  log_to_file_info "Docker Compose plugin validation: version $compose_ver (Passed)"
}

# Verify container image signature using Cosign (if installed) or Docker Content Trust
verify_container_image() {
  local image="$1"
  log_to_file_info "Docker" "Verifying signature for image: $image"

  # Check if cosign is available
  if command -v cosign &>/dev/null; then
    local pub_key="$INSTALL_DIR/certs/cosign.pub"
    log_info "Verifying signature for $image via Cosign..."
    
    if [ -f "$pub_key" ]; then
      if cosign verify --key "$pub_key" "$image" &>>"$INSTALL_LOG"; then
        log_success "Cosign signature validation PASSED: $image"
        return 0
      else
        log_fatal_err \
          "Docker image verification check FAILED: $image signature is invalid." \
          "Ensure container image registry hasn't been tampered with or DNS hijacked." \
          "https://docs.unotusk.com/ops/security#signature-failed" \
          "138"
      fi
    else
      log_warn "Cosign verification key missing at $pub_key. Skipping cryptographic verification."
    fi
  else
    # Enable Docker Content Trust as fallback
    log_to_file_info "Docker" "Cosign CLI not found. Enforcing Docker Content Trust rule."
    export DOCKER_CONTENT_TRUST=1
  fi
  return 0
}
