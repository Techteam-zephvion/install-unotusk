#!/usr/bin/env bash
# ==============================================================================
# UNOTUSK Installer — Configuration Wizard and Environment Assembly Library
# ==============================================================================

# Helper to generate strong passwords
generate_secure_token() {
  head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24
}

# Helper to generate uuid
generate_uuid_v4() {
  if command -v uuidgen &>/dev/null; then
    uuidgen | tr '[:upper:]' '[:lower:]'
  else
    cat /proc/sys/kernel/random/uuid 2>/dev/null || echo "org-$(date +%s)"
  fi
}

# Validator functions
validate_nonempty_val() {
  [ -n "$1" ]
}

validate_email_val() {
  [[ "$1" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]
}

validate_url_val() {
  [[ "$1" =~ ^https?:// ]]
}

# Prompt helper with default value
# Usage: prompt_input <var_name> <prompt_text> <default_val> [validator_func]
prompt_input() {
  local var_name="$1"
  local prompt_text="$2"
  local default_val="$3"
  local validator="${4:-}"
  local val=""

  while true; do
    if [ -n "$default_val" ]; then
      read -r -p "  ? $prompt_text [$default_val]: " val
      val="${val:-$default_val}"
    else
      read -r -p "  ? $prompt_text: " val
    fi

    if [ -n "$validator" ]; then
      if "$validator" "$val"; then
        eval "$var_name=\"$val\""
        break
      else
        log_error "Invalid input format. Please try again."
      fi
    else
      if [ -n "$val" ]; then
        eval "$var_name=\"$val\""
        break
      else
        log_error "Value cannot be empty."
      fi
    fi
  done
}

# Run the Configuration Wizard
run_config_wizard() {
  log_to_file_info "Starting Configuration Wizard..."

  # Verify python3 is installed
  if ! command -v python3 &>/dev/null; then
    log_fatal_err "python3 is required to parse settings schema." "Install python3 (standard library)." "https://docs.unotusk.com/ops/installation" "135"
  fi

  local wizard_conf_file="$WIZARD_CONF"
  local secrets_file="$SECRETS_FILE"
  local settings_registry="$INSTALL_DIR/settings.yaml"
  if [ ! -f "$settings_registry" ]; then
    settings_registry="$INSTALLER_ROOT/settings.yaml"
  fi

  log_to_file_info "Parsing settings registry: $settings_registry"

  # Invoke python to run the interactive wizard dynamically using settings.yaml schema
  python3 -c "
import sys, os, uuid

def parse_yaml(filepath):
    settings = []
    current = {}
    if not os.path.exists(filepath):
        print(f'Error: Registry file {filepath} not found.', file=sys.stderr)
        sys.exit(1)
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('- name:'):
                if current:
                    settings.append(current)
                current = {'name': line.split(':', 1)[1].strip()}
            elif ':' in line and current:
                k, v = line.split(':', 1)
                k = k.strip()
                v = v.strip().strip('\"').strip(\"'\")
                if v == 'true': v = True
                elif v == 'false': v = False
                current[k] = v
        if current:
            settings.append(current)
    return {'settings': settings}

def run():
    reg = parse_yaml('$settings_registry')
    defaults = {}
    if os.path.exists('$wizard_conf_file'):
        with open('$wizard_conf_file') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    defaults[k] = v.strip('\"').strip(\"'\")
    
    unattended = os.environ.get('UNATTENDED', '') == 'true'
    answers = {}
    print('\n\033[1m╔══════════════════════════════════════════╗\033[0m')
    print('\033[1m║    UNOTUSK Registry Configuration        ║\033[0m')
    print('\033[1m╚══════════════════════════════════════════╝\033[0m\n')
    
    for s in reg.get('settings', []):
        name = s['name']
        desc = s['description']
        default = s.get('default', '')
        if name in defaults:
            default = defaults[name]
            
        if s.get('generator') == 'uuid' and not default:
            default = str(uuid.uuid4())
            
        required = s.get('required', False)
        env_val = os.environ.get(name, '')
        if env_val:
            default = env_val
            
        if unattended:
            if required and not default:
                print(f'Error: Unattended mode but {name} is missing.', file=sys.stderr)
                sys.exit(1)
            answers[name] = default
            continue
            
        val = ''
        while True:
            prompt = f'  ? {desc}'
            if default:
                prompt += f' [{default}]'
            prompt += ': '
            try:
                val = input(prompt).strip()
            except (KeyboardInterrupt, EOFError):
                print('\nAborted.')
                sys.exit(1)
            if not val:
                val = default
            if required and not val:
                print('  \033[31m✘ Error: This field is required.\033[0m')
                continue
            
            fmt = s.get('format', '')
            if val:
                if fmt == 'email' and '@' not in val:
                    print('  \033[31m✘ Error: Invalid email format.\033[0m')
                    continue
                if fmt == 'url' and not val.startswith(('http://', 'https://')):
                    print('  \033[31m✘ Error: URL must start with http:// or https://\033[0m')
                    continue
            answers[name] = val
            break
            
    with open('$wizard_conf_file', 'w') as f:
        f.write('# UNOTUSK Selections\n')
        for k, v in answers.items():
            f.write(f'{k}=\"{v}\"\n')
            
    admin_pw = os.environ.get('ADMIN_PASSWORD', '')
    if not unattended:
        import getpass
        pw1 = getpass.getpass('  ? Administrator Password: ')
        if pw1:
            admin_pw = pw1
        else:
            import secrets
            admin_pw = secrets.token_hex(16)
            print(f'  → Generated secure admin password: {admin_pw}')
    else:
        if not admin_pw:
            import secrets
            admin_pw = secrets.token_hex(16)

    with open('$secrets_file', 'w') as f:
        f.write(f'ADMIN_PASSWORD=\"{admin_pw}\"\n')

run()
" || {
    log_fatal_err "Setup wizard failed to execute successfully." "Check Python environment or syntax of settings.yaml." "https://docs.unotusk.com" "136"
  }

  # Load generated answers into local scope to perform save_configuration
  # shellcheck source=/dev/null
  source "$WIZARD_CONF"
  # shellcheck source=/dev/null
  source "$SECRETS_FILE"

  save_configuration
}

# Write answers to state files and compile final .env
save_configuration() {
  log_to_file_info "Saving user configurations to configuration files..."

  # Save wizard history
  cat > "$WIZARD_CONF" <<EOF
# UNOTUSK Wizard Selections — Saved on $(date -u)
ORG_NAME="$ORG_NAME"
ORG_ID="$ORG_ID"
LICENSE_KEY="$LICENSE_KEY"
PLATFORM_URL="$PLATFORM_URL"
GITHUB_CLIENT_ID="$GITHUB_CLIENT_ID"
GITHUB_CLIENT_SECRET="$GITHUB_CLIENT_SECRET"
GITHUB_CALLBACK_URL="$GITHUB_CALLBACK_URL"
GITHUB_ORG="$GITHUB_ORG"
JIRA_URL="$JIRA_URL"
OIDC_PROVIDER="$OIDC_PROVIDER"
ADMIN_EMAIL="$ADMIN_EMAIL"
TIMEZONE="$TIMEZONE"
HOSTNAME="$HOSTNAME"
CERT_OPTION="$CERT_OPTION"
EOF

  # Save credentials safely
  cat > "$SECRETS_FILE" <<EOF
# UNOTUSK Admin Credentials
ADMIN_PASSWORD="$ADMIN_PASSWORD"
EOF

  # Compile root .env file
  # If secrets already generated, preserve them to remain idempotent
  local pg_pw q_key r_pw j_sec
  if [ -f "$ENV_FILE" ]; then
    pg_pw=$(grep '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d= -f2- || true)
    q_key=$(grep '^QDRANT_API_KEY=' "$ENV_FILE" | cut -d= -f2- || true)
    r_pw=$(grep '^REDIS_PASSWORD=' "$ENV_FILE" | cut -d= -f2- || true)
    j_sec=$(grep '^JWKS_PUSH_SECRET=' "$ENV_FILE" | cut -d= -f2- || true)
  fi

  POSTGRES_PASSWORD="${pg_pw:-$(generate_secure_token)}"
  QDRANT_API_KEY="${q_key:-$(generate_secure_token)}"
  REDIS_PASSWORD="${r_pw:-$(generate_secure_token)}"
  JWKS_PUSH_SECRET="${j_sec:-$(generate_secure_token)}"

  # US requires TOKEN_ENC_KEY: a base64-encoded 32-byte AES-256-GCM key for
  # encrypting GitHub/OIDC tokens at rest. generate_secure_token() strips to
  # alphanumeric and truncates to 24 chars — not valid base64, not 32 bytes.
  # Needs its own generator, and the same idempotent-preserve pattern as the
  # secrets above (rotating it on every reconfigure would invalidate every
  # stored token).
  local token_enc_key
  if [ -f "$INSTALL_DIR/US/.env" ]; then
    token_enc_key=$(grep '^TOKEN_ENC_KEY=' "$INSTALL_DIR/US/.env" | cut -d= -f2- || true)
  fi
  TOKEN_ENC_KEY="${token_enc_key:-$(openssl rand -base64 32)}"

  # Write main stack configuration env file
  cat > "$ENV_FILE" <<EOF
# UNOTUSK System Configuration — Generated on $(date -u)
# DO NOT EDIT THIS FILE DIRECTLY. USE 'unotusk reconfigure' TO MANAGE.

# Distro Context
ORG_NAME=$ORG_NAME
ORG_ID=$ORG_ID
PLATFORM_URL=$PLATFORM_URL
PLATFORM_LICENSE_KEY=$LICENSE_KEY

# Infrastructure Secrets
POSTGRES_USER=unotusk
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=unotusk
REDIS_PASSWORD=$REDIS_PASSWORD
QDRANT_API_KEY=$QDRANT_API_KEY

# Security & Tokens
JWKS_PUSH_SECRET=$JWKS_PUSH_SECRET
PLATFORM_TOKEN_AUDIENCE=platform.unotusk.com
PLATFORM_JWKS_PUSH_URL=${PLATFORM_URL}/internal/orgs/${ORG_ID}/jwks

# Ingress
HOSTNAME=$HOSTNAME
CERT_OPTION=$CERT_OPTION
TIMEZONE=$TIMEZONE

# Integrations
GITHUB_ORG=$GITHUB_ORG
JIRA_URL=$JIRA_URL
OIDC_PROVIDER=$OIDC_PROVIDER
ADMIN_EMAIL=$ADMIN_EMAIL
LOG_LEVEL=info
EOF

  # Write configurations for individual docker contexts
  #
  # CA_CERT/GRPC_TLS_CERT/GRPC_TLS_KEY: generate_certificates() (§ below)
  # writes these to US/certs/{ca,server}.{crt,key}, mounted read-only into
  # the container at /app/certs — these are Config::from_env()'s required()
  # fields, with no default, so without these three lines US crashes at
  # boot on "missing required env var: CA_CERT" before it ever reaches
  # auth-mechanism config.
  #
  # GitHub OAuth, not OIDC: /oidc/* has no route wiring in US's router
  # (AMEND-008's migration was never finished — GitHub OAuth is what's
  # actually live). The previous OIDC_CLIENT_ID/OIDC_REDIRECT_URI values
  # here were placeholders that were never a working OIDC client, and
  # OIDC_ISSUER/OIDC_CLIENT_SECRET were never written at all — Config::
  # from_env() required all four unconditionally, so every install crashed
  # regardless of which auth mechanism was intended.
  cat > "$INSTALL_DIR/US/.env" <<EOF
LOG_LEVEL=info
PLATFORM_TOKEN_AUDIENCE=platform.unotusk.com
ORG_ID=$ORG_ID
ORG_NAME=$ORG_NAME
TOKEN_ENC_KEY=$TOKEN_ENC_KEY
CA_CERT=/app/certs/ca.crt
GRPC_TLS_CERT=/app/certs/server.crt
GRPC_TLS_KEY=/app/certs/server.key
GITHUB_CLIENT_ID=$GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET=$GITHUB_CLIENT_SECRET
GITHUB_CALLBACK_URL=$GITHUB_CALLBACK_URL
OIDC_PROVIDER=$OIDC_PROVIDER
EOF

  cat > "$INSTALL_DIR/UPS/.env" <<EOF
LOG_LEVEL=info
LICENSE_HEARTBEAT_INTERVAL=60
LICENSE_GRACE_PERIOD=18000
PLATFORM_JWKS_PUSH_URL=${PLATFORM_URL}/internal/orgs/${ORG_ID}/jwks
ORG_ID=$ORG_ID
JWKS_PUSH_SECRET=$JWKS_PUSH_SECRET
EOF

  cat > "$INSTALL_DIR/AI-PIE/.env" <<EOF
LOG_LEVEL=info
GITHUB_ORG=$GITHUB_ORG
JIRA_URL=$JIRA_URL
EOF

  # Lock down config permissions immediately
  secure_configuration_files
  
  log_to_file_info "Configuration wizard save sequence complete."
}
