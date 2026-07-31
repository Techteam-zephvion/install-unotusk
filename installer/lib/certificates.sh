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
  # -addext (not just -x509's implicit defaults): plain `openssl req -x509`
  # produces an X.509v1 certificate with no extensions. rustls (every Rust
  # TLS client/server in this stack — tonic's gRPC mTLS listeners
  # especially) rejects v1 certs outright with "UnsupportedCertVersion" —
  # confirmed this breaks the US<->UPS gRPC mTLS handshake universally.
  # basicConstraints=CA:TRUE is also what actually makes this a valid CA
  # rather than just a self-signed leaf cert.
  log_to_file_info "Generating local CA key and root certificate..."
  openssl req -x509 -newkey rsa:4096 -days 3650 -nodes \
    -keyout "$INSTALL_DIR/US/certs/ca.key" \
    -out "$INSTALL_DIR/US/certs/ca.crt" \
    -subj "/C=US/O=Unotusk/CN=UnotuskInternalCA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
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
  # -addext on the CSR + -copy_extensions=copy on the signing step: carries
  # basicConstraints/keyUsage/extendedKeyUsage/subjectAltName through to the
  # signed cert, producing a v3 cert rustls/tonic will accept — see the CA
  # generation step above for why v1 (the default) breaks mTLS entirely.
  log_to_file_info "Generating auth-server certificates..."
  openssl req -newkey rsa:2048 -nodes \
    -keyout "$INSTALL_DIR/US/certs/server.key" \
    -out "$INSTALL_DIR/US/certs/server.csr" \
    -subj "/C=US/O=Unotusk/CN=auth-server" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth,clientAuth" \
    -addext "subjectAltName=DNS:auth-server,DNS:us,DNS:localhost" \
    &>>"$INSTALL_LOG"

  openssl x509 -req -in "$INSTALL_DIR/US/certs/server.csr" \
    -CA "$INSTALL_DIR/US/certs/ca.crt" \
    -CAkey "$INSTALL_DIR/US/certs/ca.key" \
    -CAcreateserial \
    -copy_extensions=copy \
    -out "$INSTALL_DIR/US/certs/server.crt" \
    -days 365 &>>"$INSTALL_LOG"

  # ── 3. Create Company Server (UPS) client certs (for mTLS to US) ──
  log_to_file_info "Generating company-server client certificates..."
  openssl req -newkey rsa:2048 -nodes \
    -keyout "$INSTALL_DIR/UPS/certs/client.key" \
    -out "$INSTALL_DIR/UPS/certs/client.csr" \
    -subj "/C=US/O=Unotusk/CN=company-server" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=clientAuth" \
    -addext "subjectAltName=DNS:company-server,DNS:ups" \
    &>>"$INSTALL_LOG"

  openssl x509 -req -in "$INSTALL_DIR/UPS/certs/client.csr" \
    -CA "$INSTALL_DIR/US/certs/ca.crt" \
    -CAkey "$INSTALL_DIR/US/certs/ca.key" \
    -CAcreateserial \
    -copy_extensions=copy \
    -out "$INSTALL_DIR/UPS/certs/client.crt" \
    -days 365 &>>"$INSTALL_LOG"

  # ── 4. Generate Platform placeholder certs for UPS ──
  # Real certs are pushed during cloud setup; these allow boot without errors
  log_to_file_info "Generating platform client placeholder certificates..."
  openssl req -x509 -newkey rsa:2048 -days 365 -nodes \
    -keyout "$INSTALL_DIR/UPS/certs/platform/client.key" \
    -out "$INSTALL_DIR/UPS/certs/platform/client.crt" \
    -subj "/C=US/O=Unotusk/CN=platform-client-placeholder" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=clientAuth" \
    &>>"$INSTALL_LOG"
  cp "$INSTALL_DIR/UPS/certs/platform/client.crt" "$INSTALL_DIR/UPS/certs/platform/ca.crt"

  # ── 5. AI-PIE local dev cert (for health check mTLS validation) ──
  log_to_file_info "Generating AI-PIE dev certificates..."
  openssl req -newkey rsa:2048 -nodes \
    -keyout "$INSTALL_DIR/AI-PIE/certs/dev/client.key" \
    -out "$INSTALL_DIR/AI-PIE/certs/dev/client.csr" \
    -subj "/C=US/O=Unotusk/CN=ai-pie" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=clientAuth,serverAuth" \
    -addext "subjectAltName=DNS:ai-pie" \
    &>>"$INSTALL_LOG"

  openssl x509 -req -in "$INSTALL_DIR/AI-PIE/certs/dev/client.csr" \
    -CA "$INSTALL_DIR/US/certs/ca.crt" \
    -CAkey "$INSTALL_DIR/US/certs/ca.key" \
    -CAcreateserial \
    -copy_extensions=copy \
    -out "$INSTALL_DIR/AI-PIE/certs/dev/client.pem" \
    -days 365 &>>"$INSTALL_LOG"

  # ── 5b. AI-PIE auth-client cert (AMEND-007 — AI-PIE validates bearer
  # tokens against US's auth gRPC directly, mTLS-enforced unconditionally
  # by US's gRPC listener). Distinct from the dev cert above (UPS
  # health-check path) — this was never generated at all before, so
  # AUTH_GRPC_ENDPOINT connections from AI-PIE to US had no client identity
  # to mTLS-handshake with.
  log_to_file_info "Generating AI-PIE auth-client certificates..."
  mkdir -p "$INSTALL_DIR/AI-PIE/certs/auth-client"
  openssl req -newkey rsa:2048 -nodes \
    -keyout "$INSTALL_DIR/AI-PIE/certs/auth-client/key.pem" \
    -out "$INSTALL_DIR/AI-PIE/certs/auth-client/cert.csr" \
    -subj "/C=US/O=Unotusk/CN=ai-pie-auth-client" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=clientAuth" \
    &>>"$INSTALL_LOG"

  openssl x509 -req -in "$INSTALL_DIR/AI-PIE/certs/auth-client/cert.csr" \
    -CA "$INSTALL_DIR/US/certs/ca.crt" \
    -CAkey "$INSTALL_DIR/US/certs/ca.key" \
    -CAcreateserial \
    -copy_extensions=copy \
    -out "$INSTALL_DIR/AI-PIE/certs/auth-client/cert.pem" \
    -days 365 &>>"$INSTALL_LOG"
  cp "$INSTALL_DIR/US/certs/ca.crt" "$INSTALL_DIR/AI-PIE/certs/auth-client/ca.pem"

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
        -addext "basicConstraints=critical,CA:FALSE" \
        -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
        -addext "extendedKeyUsage=serverAuth" \
        -addext "subjectAltName=DNS:$HOSTNAME" \
        &>>"$INSTALL_LOG"

      openssl x509 -req -in "$INSTALL_DIR/caddy/certs/server.csr" \
        -CA "$INSTALL_DIR/US/certs/ca.crt" \
        -CAkey "$INSTALL_DIR/US/certs/ca.key" \
        -CAcreateserial \
        -copy_extensions=copy \
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
          -addext "basicConstraints=critical,CA:FALSE" \
          -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
          -addext "extendedKeyUsage=serverAuth" \
          -addext "subjectAltName=DNS:$HOSTNAME" \
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
