#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Platform — System Diagnostics and Health Check (Doctor)
# Usage: sudo ./doctor.sh
# ==============================================================================
set -euo pipefail

# Sourcing libraries
INSTALL_DIR="${INSTALL_DIR:-/opt/unotusk}"
LIB_DIR="$INSTALL_DIR/lib"

if [ -d "$LIB_DIR" ]; then
  # shellcheck source=lib/common.sh
  source "$LIB_DIR/common.sh"
else
  # Local source context fallback
  SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  # shellcheck source=lib/common.sh
  source "$SRC_DIR/lib/common.sh"
fi

main() {
  log_title "UNOTUSK Platform Diagnostics"

  local fails=0
  local warns=0

  # Helper to print check results
  print_result() {
    local status="$1"
    local component="$2"
    local desc="$3"
    
    case "$status" in
      PASS)
        echo -e "  [${GREEN}PASS${RESET}]  $component: $desc"
        ;;
      WARN)
        echo -e "  [${YELLOW}WARN${RESET}]  $component: $desc"
        warns=$((warns + 1))
        ;;
      FAIL)
        echo -e "  [${RED}FAIL${RESET}]  $component: $desc"
        fails=$((fails + 1))
        ;;
    esac
  }

  # ── 1. Host Infrastructure Checks ──
  log_header "── Host Infrastructure"

  # Docker running check
  if docker info &>/dev/null; then
    print_result PASS "Docker daemon" "Running and responsive"
  else
    print_result FAIL "Docker daemon" "Daemon is offline or unresponsive"
  fi

  # Docker version check
  local docker_ver
  docker_ver=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "0")
  local docker_major
  docker_major=$(echo "$docker_ver" | cut -d. -f1)
  if [ "$docker_major" -ge 24 ]; then
    print_result PASS "Docker version" "$docker_ver (minimum required: 24.0)"
  else
    print_result FAIL "Docker version" "$docker_ver is below the minimum (24.0)"
  fi

  # Docker Compose check
  if docker compose version &>/dev/null; then
    local compose_ver
    compose_ver=$(docker compose version --short 2>/dev/null)
    print_result PASS "Docker Compose" "Installed ($compose_ver)"
  else
    print_result FAIL "Docker Compose" "Compose CLI plugin is not installed"
  fi

  # CPU cores check
  local cores
  cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
  if [ "$cores" -ge 2 ]; then
    print_result PASS "CPU cores" "$cores cores available"
  else
    print_result WARN "CPU cores" "1 CPU core detected (2+ recommended)"
  fi

  # Disk space check
  if command -v df &>/dev/null; then
    local free_disk
    free_disk=$(df -m "$INSTALL_DIR" | awk 'NR==2 {print $4}')
    if [ "$free_disk" -ge 10240 ]; then
      print_result PASS "Disk space" "${free_disk}MB free (Passed)"
    elif [ "$free_disk" -ge 5120 ]; then
      print_result WARN "Disk space" "${free_disk}MB free (Less than 10GB recommended)"
    else
      print_result FAIL "Disk space" "${free_disk}MB free (Critically low, <5GB)"
    fi
  else
    print_result WARN "Disk space" "Could not read disk space (df missing)"
  fi

  # Memory check
  if command -v free &>/dev/null; then
    local free_ram
    free_ram=$(free -m | awk '/^Mem:/ {print $2}')
    if [ "$free_ram" -ge 4096 ]; then
      print_result PASS "System memory" "${free_ram}MB total RAM"
    else
      print_result WARN "System memory" "${free_ram}MB total RAM (recommended: 4096MB+)"
    fi
  else
    print_result WARN "System memory" "Could not read RAM info (free missing)"
  fi

  # Clock Sync check
  if command -v timedatectl &>/dev/null; then
    local ntp_sync
    ntp_sync=$(timedatectl show --property=NTPSynchronized --value 2>/dev/null || echo "unknown")
    if [ "$ntp_sync" = "yes" ]; then
      print_result PASS "System clock sync" "NTP synchronization active"
    else
      print_result WARN "System clock sync" "NTP is not synced. JWT validation errors may occur"
    fi
  else
    print_result WARN "System clock sync" "Clock sync status unverified (timedatectl missing)"
  fi

  # ── 2. Configuration Checks ──
  log_header "── Configuration & Secrets"
  for file_path in .env .env.wizard .secrets .unotusk-version; do
    if [ -f "$INSTALL_DIR/$file_path" ]; then
      local perms
      perms=$(stat -c "%a" "$INSTALL_DIR/$file_path" 2>/dev/null || stat -f "%Lp" "$INSTALL_DIR/$file_path" 2>/dev/null || echo "777")
      if [ "$perms" = "600" ] || [ "$perms" = "400" ]; then
        print_result PASS "$file_path" "File exists and permissions are secure ($perms)"
      else
        print_result WARN "$file_path" "File permissions are too open ($perms, recommended 600)"
      fi
    else
      print_result FAIL "$file_path" "Configuration file is missing!"
    fi
  done

  # ── 3. Container Status Checks ──
  log_header "── Running Containers"
  local containers=(postgres redis qdrant phoenix us ups ai-pie caddy)
  for container in "${containers[@]}"; do
    local c_id
    c_id=$(cd "$INSTALL_DIR" && docker compose ps -q "$container" 2>/dev/null || true)
    if [ -z "$c_id" ]; then
      print_result FAIL "$container container" "Container is not deployed"
      continue
    fi
    
    local health_status
    health_status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$c_id" 2>/dev/null || echo "unknown")
    local state
    state=$(docker inspect --format='{{.State.Status}}' "$c_id" 2>/dev/null || echo "unknown")

    if [ "$state" = "running" ] && { [ "$health_status" = "healthy" ] || [ "$health_status" = "running" ]; }; then
      print_result PASS "$container container" "Active and $health_status"
    else
      print_result FAIL "$container container" "Status is $state ($health_status)"
    fi
  done

  # ── 4. Endpoints & Integrations ──
  log_header "── Ingress & Network Connectors"

  # Test host resolution of local domain
  if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    if nslookup "$HOSTNAME" &>/dev/null || host "$HOSTNAME" &>/dev/null || [ "$HOSTNAME" = "localhost" ]; then
      print_result PASS "Ingress hostname" "$HOSTNAME resolves correctly"
    else
      print_result WARN "Ingress hostname" "Cannot resolve domain '$HOSTNAME' locally"
    fi
    
    # Platform connectivity
    local platform_host
    platform_host=$(echo "$PLATFORM_URL" | sed -E 's|https?://([^:/]+).*|\1|')
    if nslookup "$platform_host" &>/dev/null || host "$platform_host" &>/dev/null; then
      print_result PASS "Platform lookup" "$platform_host resolves correctly"
    else
      print_result FAIL "Platform lookup" "Cannot resolve platform server domain '$platform_host'"
    fi
  else
    print_result WARN "Ingress hostname" "Environment settings missing, skipping DNS tests"
  fi

  # ── 5. SSL & Certificates Expiry ──
  log_header "── Certificate Lifespans"
  local certs=(
    "US/certs/ca.crt:Internal CA"
    "US/certs/server.crt:Auth Server"
    "UPS/certs/client.crt:Company Client"
    "caddy/certs/server.crt:Ingress Server"
  )
  for cert_meta in "${certs[@]}"; do
    local path="${cert_meta%%:*}"
    local label="${cert_meta##*:}"
    
    if [ -f "$INSTALL_DIR/$path" ]; then
      local expiry
      expiry=$(openssl x509 -enddate -noout -in "$INSTALL_DIR/$path" 2>/dev/null | cut -d= -f2 || echo "")
      if [ -n "$expiry" ]; then
        local expiry_epoch
        expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo 0)
        local now_epoch
        now_epoch=$(date +%s)
        local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))
        
        if [ "$days_left" -gt 30 ]; then
          print_result PASS "$label Cert" "Expires in $days_left days ($expiry)"
        elif [ "$days_left" -gt 0 ]; then
          print_result WARN "$label Cert" "Expires soon ($days_left days left, renew soon)"
        else
          print_result FAIL "$label Cert" "EXPIRED on $expiry"
        fi
      else
        print_result WARN "$label Cert" "Could not parse certificate enddate"
      fi
    else
      if [ "$path" = "caddy/certs/server.crt" ] && [ "${CERT_OPTION:-}" = "letsencrypt" ]; then
        print_result PASS "$label Cert" "Managed automatically by Let's Encrypt / Caddy"
      else
        print_result WARN "$label Cert" "Certificate file is missing: $path"
      fi
    fi
  done

  # ── Summary Report ──
  echo ""
  log_header "── Summary Results"
  if [ "$fails" -gt 0 ]; then
    echo -e "${RED}${BOLD}Diagnostics found $fails critical issue(s) and $warns warning(s).${RESET}"
    echo "  Consult docs/TROUBLESHOOTING.md to debug issues."
    exit 1
  elif [ "$warns" -gt 0 ]; then
    echo -e "${YELLOW}${BOLD}Diagnostics found $warns warning(s). All critical services are online.${RESET}"
    exit 0
  else
    echo -e "${GREEN}${BOLD}All checks passed successfully. System is completely healthy.${RESET}"
    exit 0
  fi
}

main "$@"
