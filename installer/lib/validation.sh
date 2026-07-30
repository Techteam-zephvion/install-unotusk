#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Environment Validation Library
# ==============================================================================

# Minimum limits
MIN_RAM_MB=4096
MIN_DISK_MB=10240
MIN_CPU_CORES=2
MIN_DOCKER_VERSION=24

# OS and Distro Validation
# Supports Ubuntu 24.04+, Debian 12+, Pop!_OS
validate_os() {
  log_to_file_info "Validating Operating System Distro..."
  
  if [ ! -f /etc/os-release ]; then
    log_warn "Could not read /etc/os-release. System compatibility is unverified."
    return 0
  fi
  
  # Source release info
  # shellcheck disable=SC1091
  DISTRO_ID=$(. /etc/os-release && echo "$ID")
  # shellcheck disable=SC1091
  DISTRO_VERSION=$(. /etc/os-release && echo "$VERSION_ID")
  
  case "$DISTRO_ID" in
    ubuntu)
      # Extract major version
      local major
      major=$(echo "$DISTRO_VERSION" | cut -d. -f1)
      if [ "$major" -lt 24 ]; then
        log_warn "Ubuntu version detected: $DISTRO_VERSION. Officially supports Ubuntu 24.04+."
      else
        log_to_file_info "OS Validation: Ubuntu $DISTRO_VERSION detected (Supported)"
      fi
      ;;
    debian)
      local major
      major=$(echo "$DISTRO_VERSION" | cut -d. -f1)
      if [ "$major" -lt 12 ]; then
        log_warn "Debian version detected: $DISTRO_VERSION. Officially supports Debian 12+."
      else
        log_to_file_info "OS Validation: Debian $DISTRO_VERSION detected (Supported)"
      fi
      ;;
    pop)
      log_to_file_info "OS Validation: Pop!_OS detected (Supported)"
      ;;
    *)
      log_warn "Distro '$DISTRO_ID $DISTRO_VERSION' is not officially supported. (Ubuntu 24.04 / Debian 12+ recommended)"
      ;;
  esac
  return 0
}

# CPU Architecture Validation
# Supports amd64 (x86_64) and arm64 (aarch64)
validate_arch() {
  log_to_file_info "Validating CPU Architecture..."
  local arch
  arch=$(uname -m)
  
  case "$arch" in
    x86_64)
      log_to_file_info "Architecture Validation: x86_64/amd64 detected (Supported)"
      ;;
    aarch64|arm64)
      log_to_file_info "Architecture Validation: arm64/aarch64 detected (Supported)"
      ;;
    *)
      log_fatal_err \
        "Architecture '$arch' is not supported." \
        "UNOTUSK requires an amd64 (x86_64) or arm64 CPU architecture." \
        "https://docs.unotusk.com/ops/requirements#cpu-architectures" \
        "101"
      ;;
  esac
}

# Hardware Resource Validation (RAM, Disk, CPU Cores)
validate_resources() {
  log_to_file_info "Validating Hardware Resources..."

  # 1. CPU Cores
  local cores
  cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
  if [ "$cores" -lt "$MIN_CPU_CORES" ]; then
    log_warn "Detected $cores CPU cores. recommended minimum is $MIN_CPU_CORES cores."
  else
    log_to_file_info "Resource Validation: $cores CPU cores (Passed)"
  fi

  # 2. Memory check (RAM)
  if command -v free &>/dev/null; then
    local total_ram
    total_ram=$(free -m | awk '/^Mem:/ {print $2}')
    if [ "$total_ram" -lt "$MIN_RAM_MB" ]; then
      log_warn "Detected ${total_ram}MB RAM. recommended minimum is ${MIN_RAM_MB}MB."
    else
      log_to_file_info "Resource Validation: ${total_ram}MB RAM (Passed)"
    fi
  else
    log_warn "Unable to verify memory size ('free' command missing)."
  fi

  # 3. Disk space check
  # Check free space in installer parent dir
  local check_dir
  check_dir=$(dirname "$INSTALL_DIR")
  mkdir -p "$check_dir" 2>/dev/null || true
  
  if command -v df &>/dev/null; then
    local free_disk
    free_disk=$(df -m "$check_dir" | awk 'NR==2 {print $4}')
    if [ "$free_disk" -lt "$MIN_DISK_MB" ]; then
      log_fatal_err \
        "Insufficient disk space: ${free_disk}MB free." \
        "Free up disk space to meet the minimum of ${MIN_DISK_MB}MB (10GB)." \
        "https://docs.unotusk.com/ops/requirements#storage" \
        "102"
    else
      log_to_file_info "Resource Validation: ${free_disk}MB free disk space (Passed)"
    fi
  else
    log_warn "Unable to verify disk space ('df' command missing)."
  fi
}

# Validate pre-requisite host binaries
validate_dependencies() {
  log_to_file_info "Validating prerequisite binaries..."
  local missing_tools=()
  
  for tool in curl openssl nslookup tar gzip; do
    if ! command -v "$tool" &>/dev/null; then
      missing_tools+=("$tool")
    fi
  done

  if [ ${#missing_tools[@]} -ne 0 ]; then
    log_fatal_err \
      "Prerequisite command-line tools are missing: ${missing_tools[*]}" \
      "Install the missing utilities using your system packet manager (e.g., 'apt install -y ${missing_tools[*]}')." \
      "https://docs.unotusk.com/ops/installation#prerequisites" \
      "103"
  fi
  log_to_file_info "Prerequisite tools validation: Passed"
}
