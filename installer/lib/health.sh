#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Service Health and Diagnostics Library
# ==============================================================================

# Wait for a single service container health status to be 'healthy' or 'running'
# Usage: wait_for_service_health <service_name> <timeout_seconds>
wait_for_service_health() {
  local service="$1"
  local timeout="${2:-120}"
  local elapsed=0
  local interval=5
  local container_id

  # Fetch container ID for service
  container_id=$(cd "$INSTALL_DIR" && docker compose ps -q "$service" 2>/dev/null || true)
  if [ -z "$container_id" ]; then
    log_to_file_err "Health validation: container for '$service' is missing."
    return 1
  fi

  log_to_file_info "Waiting for service '$service' to be healthy (timeout: ${timeout}s)..."

  while [ "$elapsed" -lt "$timeout" ]; do
    local status
    status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$container_id" 2>/dev/null || echo "unknown")

    case "$status" in
      healthy|running)
        log_to_file_info "Service '$service' health check: PASSED ($status)"
        return 0
        ;;
      unhealthy)
        log_to_file_err "Service '$service' reports UNHEALTHY."
        return 1
        ;;
      starting)
        sleep "$interval"
        elapsed=$((elapsed + interval))
        ;;
      *)
        sleep "$interval"
        elapsed=$((elapsed + interval))
        ;;
    esac
  done

  log_to_file_err "Service '$service' did not reach healthy state within ${timeout}s."
  return 1
}

# Verify the mTLS connection between services (US and UPS)
verify_mtls_connectivity() {
  log_to_file_info "Verifying service-to-service mTLS handshakes..."

  # Probe US gRPC port (50052) via openssl s_client from within the UPS container
  # This tests the CA trust and client certificate validation
  local ups_container
  ups_container=$(cd "$INSTALL_DIR" && docker compose ps -q ups 2>/dev/null || true)
  
  if [ -z "$ups_container" ]; then
    log_to_file_warn "mTLS Validation: UPS container is not running yet. Skipping probe (warn-only)."
    return 0
  fi

  log_to_file_info "Executing openssl client probe inside UPS container pointing to US OIDC..."
  
  # Perform a basic gRPC mTLS probe using openssl inside UPS container
  local mtls_ok=0
  if docker exec "$ups_container" sh -c "openssl s_client -connect us:50052 -cert /app/certs/client.crt -key /app/certs/client.key -CAfile /app/certs/ca.crt -brief </dev/null" &>>"$INSTALL_LOG"; then
    mtls_ok=1
  fi

  if [ "$mtls_ok" -eq 1 ]; then
    log_to_file_info "mTLS handshakes between UPS and US: SUCCESS"
    return 0
  else
    log_to_file_warn "gRPC mTLS validation probe failed to complete cleanly. Handshake could be in progress or blocked."
    return 0 # Warn-only to allow self-healing / platform sync
  fi
}

# General health validation check for all stack services
verify_overall_health() {
  log_to_file_info "Running system health verification..."
  local failed_services=()

  # List of services in start order
  local services=(postgres redis qdrant phoenix us ups ai-pie caddy)
  
  for svc in "${services[@]}"; do
    if ! wait_for_service_health "$svc" 30; then
      failed_services+=("$svc")
    fi
  done

  if [ ${#failed_services[@]} -ne 0 ]; then
    log_fatal_err \
      "Services failed health check: ${failed_services[*]}" \
      "Check docker logs for failed services using 'docker compose logs <service>'." \
      "https://docs.unotusk.com/ops/troubleshooting#container-health" \
      "151"
  fi

  log_success "All UNOTUSK services are healthy and running."
}
