#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Network Validation Library
# ==============================================================================

# Check port availability on host. Returns 0 if free, 1 if in use.
# Usage: check_port_free <port> <label>
check_port_free() {
  local port="$1"
  local label="$2"
  local in_use=0

  log_to_file_info "Checking availability of port $port ($label)..."

  # Use ss or netstat if available, or try opening a local socket test
  if command -v ss &>/dev/null; then
    if ss -tlnp 2>/dev/null | grep -q -E ":${port}\s"; then
      in_use=1
    fi
  elif command -v netstat &>/dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q -E ":${port}\s"; then
      in_use=1
    fi
  else
    # Fallback to bash socket if possible
    if (exec 3<>/dev/tcp/127.0.0.1/"$port") &>/dev/null; then
      exec 3>&-
      in_use=1
    fi
  fi

  if [ "$in_use" -eq 1 ]; then
    # Check if the process using it is a docker-proxy of our own stack
    # (during updates/reruns, this is expected and fine)
    local proc_info=""
    if command -v ss &>/dev/null; then
      proc_info=$(ss -tlnp "sport = :$port" 2>/dev/null)
    fi
    
    if [[ "$proc_info" == *"docker-proxy"* ]]; then
      log_to_file_info "Port $port is in use by Docker (presumably UNOTUSK proxy, allowing)."
      return 0
    fi
    
    return 1
  fi

  return 0
}

# Verify required inbound ports (80 and 443) are available
validate_ingress_ports() {
  log_to_file_info "Validating ingress ports (80 and 443)..."
  local conflicts=0

  if ! check_port_free 80 "HTTP Port"; then
    log_to_file_err "Port 80 is currently in use."
    conflicts=$((conflicts + 1))
  fi

  if ! check_port_free 443 "HTTPS Port"; then
    log_to_file_err "Port 443 is currently in use."
    conflicts=$((conflicts + 1))
  fi

  if [ "$conflicts" -ne 0 ]; then
    log_fatal_err \
      "Required ports (80/443) are occupied by another process." \
      "Stop any existing reverse proxy (e.g. Nginx, Apache) or conflicting services before installing." \
      "https://docs.unotusk.com/ops/installation#port-conflicts" \
      "120"
  fi
  
  log_to_file_info "Ingress ports 80/443 validation: Passed"
}

# Test outbound internet/dependency connectivity. Advisory only (no
# log_fatal_err path) — must never return non-zero, since a bare non-zero
# return from a top-level call under this script's `set -e` aborts the
# entire install with no visible error.
validate_outbound_connectivity() {
  local target_url="${1:-https://registry-1.docker.io}"
  log_to_file_info "Testing outbound connection to $target_url..."

  # Deliberately no -f: registries like registry-1.docker.io return 401/404
  # on an unauthenticated root request even when fully reachable — curl -f
  # treats that as a failure. We only care that the TCP/TLS handshake and
  # HTTP response happened at all, not the status code.
  if ! curl -s --max-time 10 -o /dev/null "$target_url"; then
    local host
    host=$(echo "$target_url" | sed -E 's|https?://([^:/]+).*|\1|')

    log_to_file_warn "Outbound connection to $target_url failed. Testing DNS resolution for $host..."

    if ! nslookup "$host" &>/dev/null && ! host "$host" &>/dev/null; then
      log_warn "DNS lookup failed for '$host'. Verify internet access and DNS resolvers."
    else
      log_to_file_info "DNS resolution for $host: Success"
    fi
    return 0
  fi

  log_to_file_info "Outbound connectivity to $target_url: Passed"
  return 0
}
