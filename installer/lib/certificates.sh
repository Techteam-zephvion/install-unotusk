#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Cryptographic Certificates and TLS Library
# ==============================================================================

# Setup directories for certificates
init_cert_directories() {
  mkdir -p "$INSTALL_DIR/US/certs" \
           "$INSTALL_DIR/UPS/certs/platform" \
           "$INSTALL_DIR/AI-PIE/certs/dev" \
           "$INSTALL_DIR/caddy/certs"
}

# Generate cryptographic certificates for services
generate_certificates() {
  log_to_file_info "Starting certificate generation sequence..."
  init_cert_directories

  local cert_marker="$INSTALL_DIR/.certs-generated"
  
  if [ -f "$cert_marker" ]; then
    log_info "Certificates already generated — skipping generation (idempotent)."
    log_to_file_info "Certificates already present, skipping generation."
    return 0
  fi

  log_info "Generating local CA and service certificates..."

  # ── 1. Create Internal Root CA ──
  log_to_file_info "Generating local CA key and root certificate..."
  openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
    -keyout "$INSTALL_DIR/US/certs/ca.key" \
    -out "$INSTALL_DIR/US/certs/ca.crt" \
    -subj "/C=US/O=Unotusk/CN=UnotuskInternalCA" \
    &>>"$INSTALL_LOG" || {
      log_fatal_err \
        "Failed to generate internal CA certificates." \
        "Check openssl installation and permissions on US/certs directory." \
        "https://docs.unotusk.com/ops/security#tls-generation-errors" \
        "150"
    }

  # Copy root CA to other services
  cp "$INSTALL_DIR/US/certs/ca.crt" "$INSTALL_DIR/UPS/certs/ca.crt"
  cp "$INSTALL_DIR/US/certs/ca.crt" "$INSTALL_DIR/AI-PIE/certs/ca.crt"
  cp "$INSTALL_DIR/US/certs/ca.crt" "$INSTALL_DIR/caddy/certs/ca.crt"

  # ── 2. Create Auth Service (US) server certs ──
  log_to_file_info "Generating auth-server certificates..."
  openssl req -newkey rsa:2048 -nodes \
    -keyout "$INSTALL_DIR/US/certs/server.key" \
    -out "$INSTALL_DIR/US/certs/server.csr" \
    -subj "/C=US/O=Unotusk/CN=auth-server" \
    &>>"$INSTALL_LOG"
  
  openssl x509 -req -in "$INSTALL_DIR/US/certs/server.csr" \
    -CA "$INSTALL_DIR/US/certs/ca.crt" \
    -CAkey "$INSTALL_DIR/US/certs/ca.key" \
    -CAcreateserial \
    -out "$INSTALL_DIR/US/certs/server.crt" \
    -days 365 &>>"$INSTALL_LOG"

  # ── 3. Create Company Server (UPS) client certs (for mTLS to US) ──
  log_to_file_info "Generating company-server client certificates..."
  openssl req -newkey rsa:2048 -nodes \
    -keyout "$INSTALL_DIR/UPS/certs/client.key" \
    -out "$INSTALL_DIR/UPS/certs/client.csr" \
    -subj "/C=US/O=Unotusk/CN=company-server" \
    &>>"$INSTALL_LOG"
  
  openssl x509 -req -in "$INSTALL_DIR/UPS/certs/client.csr" \
    -CA "$INSTALL_DIR/US/certs/ca.crt" \
    -CAkey "$INSTALL_DIR/US/certs/ca.key" \
    -CAcreateserial \
    -out "$INSTALL_DIR/UPS/certs/client.crt" \
    -days 365 &>>"$INSTALL_LOG"

  # ── 4. Generate Platform placeholder certs for UPS ──
  # Real certs are pushed during cloud setup; these allow boot without errors
  log_to_file_info "Generating platform client placeholder certificates..."
  openssl req -x509 -newkey rsa:2048 -days 365 -nodes \
    -keyout "$INSTALL_DIR/UPS/certs/platform/client.key" \
    -out "$INSTALL_DIR/UPS/certs/platform/client.crt" \
    -subj "/C=US/O=Unotusk/CN=platform-client-placeholder" \
    &>>"$INSTALL_LOG"
  cp "$INSTALL_DIR/UPS/certs/platform/client.crt" "$INSTALL_DIR/UPS/certs/platform/ca.crt"

  # ── 5. AI-PIE local dev cert (for health check mTLS validation) ──
  log_to_file_info "Generating AI-PIE dev certificates..."
  openssl req -newkey rsa:2048 -nodes \
    -keyout "$INSTALL_DIR/AI-PIE/certs/dev/client.key" \
    -out "$INSTALL_DIR/AI-PIE/certs/dev/client.csr" \
    -subj "/C=US/O=Unotusk/CN=ai-pie" \
    &>>"$INSTALL_LOG"
  
  openssl x509 -req -in "$INSTALL_DIR/AI-PIE/certs/dev/client.csr" \
    -CA "$INSTALL_DIR/US/certs/ca.crt" \
    -CAkey "$INSTALL_DIR/US/certs/ca.key" \
    -CAcreateserial \
    -out "$INSTALL_DIR/AI-PIE/certs/dev/client.pem" \
    -days 365 &>>"$INSTALL_LOG"

  # ── 6. Ingress Certificate Setup (Caddy) ──
  local caddyfile_target="$INSTALL_DIR/templates/Caddyfile"
  if [ -f "$caddyfile_target" ]; then
    cp "$caddyfile_target" "${caddyfile_target}.tmp"
  fi

  case "$CERT_OPTION" in
    selfsigned)
      log_to_file_info "Generating self-signed host certificates for Caddy..."
      openssl req -newkey rsa:2048 -nodes \
        -keyout "$INSTALL_DIR/caddy/certs/server.key" \
        -out "$INSTALL_DIR/caddy/certs/server.csr" \
        -subj "/C=US/O=Unotusk/CN=$HOSTNAME" \
        &>>"$INSTALL_LOG"
      
      openssl x509 -req -in "$INSTALL_DIR/caddy/certs/server.csr" \
        -CA "$INSTALL_DIR/US/certs/ca.crt" \
        -CAkey "$INSTALL_DIR/US/certs/ca.key" \
        -CAcreateserial \
        -out "$INSTALL_DIR/caddy/certs/server.crt" \
        -days 365 &>>"$INSTALL_LOG"

      if [ -f "${caddyfile_target}.tmp" ]; then
        sed -i 's|# #TLS_CONFIG#|tls /etc/caddy/certs/server.crt /etc/caddy/certs/server.key|' "${caddyfile_target}.tmp"
      fi
      ;;
    custom)
      log_warn "Operator specified custom certificate option."
      log_info "Please copy your domain certificates to:"
      log_info "  $INSTALL_DIR/caddy/certs/server.crt"
      log_info "  $INSTALL_DIR/caddy/certs/server.key"
      
      # Generate placeholders in case user didn't copy them yet
      if [ ! -f "$INSTALL_DIR/caddy/certs/server.key" ]; then
        log_to_file_info "Custom certs missing, creating temporary self-signed fallback..."
        openssl req -x509 -newkey rsa:2048 -days 30 -nodes \
          -keyout "$INSTALL_DIR/caddy/certs/server.key" \
          -out "$INSTALL_DIR/caddy/certs/server.crt" \
          -subj "/C=US/O=Unotusk/CN=$HOSTNAME-custom-fallback" \
          &>>"$INSTALL_LOG"
      fi

      if [ -f "${caddyfile_target}.tmp" ]; then
        sed -i 's|# #TLS_CONFIG#|tls /etc/caddy/certs/server.crt /etc/caddy/certs/server.key|' "${caddyfile_target}.tmp"
      fi
      ;;
    letsencrypt)
      log_to_file_info "Let's Encrypt selected; TLS will be managed automatically by Caddy."
      if [ -f "${caddyfile_target}.tmp" ]; then
        sed -i 's|# #TLS_CONFIG#||' "${caddyfile_target}.tmp"
      fi
      ;;
  esac

  if [ -f "${caddyfile_target}.tmp" ]; then
    mv "${caddyfile_target}.tmp" "$caddyfile_target"
  fi

  # Ensure read-only by container processes
  log_to_file_info "Securing certificate keys (chmod 644/600)..."
  find "$INSTALL_DIR" -name "*.key" -exec chmod 644 {} + 2>/dev/null || true
  find "$INSTALL_DIR" -name "*.crt" -exec chmod 644 {} + 2>/dev/null || true
  find "$INSTALL_DIR" -name "*.pem" -exec chmod 644 {} + 2>/dev/null || true

  touch "$cert_marker"
  log_success "Certificates generated and configured."
}
