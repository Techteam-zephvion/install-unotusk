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

# Resolves a usable `gum` binary for the interactive wizard's prompts and
# echoes its path (or "" if unavailable — callers fall back to plain
# read/input prompts, never hard-fail the installer over a UX nicety).
#
# Prefers a system-installed gum already on PATH. Otherwise downloads the
# static binary release directly from GitHub (same fallback pattern
# bootstrap/install.sh already uses for the Docker Compose plugin) rather
# than adding an apt repository — customer machines shouldn't need a new
# trusted repo just to get a nicer prompt, and a single static Go binary
# needs no package manager at all.
GUM_VERSION="0.17.0"
ensure_gum_available() {
  if command -v gum &>/dev/null; then
    command -v gum
    return 0
  fi

  local bin_dir="$INSTALL_DIR/.bin"
  local cached="$bin_dir/gum"
  if [ -x "$cached" ]; then
    echo "$cached"
    return 0
  fi

  local arch
  case "$(uname -m)" in
    x86_64) arch="x86_64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
      log_to_file_warn "Unsupported architecture for gum ($(uname -m)) — falling back to plain prompts."
      return 1
      ;;
  esac

  local tmp_dir
  tmp_dir=$(mktemp -d)
  local tarball="gum_${GUM_VERSION}_Linux_${arch}.tar.gz"
  local url="https://github.com/charmbracelet/gum/releases/download/v${GUM_VERSION}/${tarball}"

  log_to_file_info "Downloading gum ${GUM_VERSION} for the interactive wizard..."
  if ! curl -fsSL "$url" -o "$tmp_dir/$tarball" 2>>"$INSTALL_LOG"; then
    log_to_file_warn "gum download failed — falling back to plain prompts."
    rm -rf "$tmp_dir"
    return 1
  fi

  tar -xzf "$tmp_dir/$tarball" -C "$tmp_dir" 2>>"$INSTALL_LOG"
  local extracted
  extracted=$(find "$tmp_dir" -type f -name gum | head -1)
  if [ -z "$extracted" ]; then
    log_to_file_warn "gum archive didn't contain the expected binary — falling back to plain prompts."
    rm -rf "$tmp_dir"
    return 1
  fi

  mkdir -p "$bin_dir"
  cp "$extracted" "$cached"
  chmod +x "$cached"
  rm -rf "$tmp_dir"

  echo "$cached"
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

  local gum_bin=""
  if [ "${UNATTENDED:-}" != "true" ]; then
    gum_bin="$(ensure_gum_available || true)"
  fi

  # Invoke python to run the interactive wizard dynamically using settings.yaml schema
  python3 -c "
import sys, os, uuid, subprocess, getpass, time

GUM_BIN = '$gum_bin'
GUM_WARNED = False

def mask(val):
    if not val:
        return ''
    if len(val) <= 4:
        return '*' * len(val)
    return val[:4] + ('*' * max(len(val) - 4, 4))

def show_header(text):
    if GUM_BIN:
        subprocess.run([GUM_BIN, 'style', '--border', 'rounded', '--padding', '0 2',
                         '--margin', '1 0', '--bold', '--border-foreground', '212', text])
    else:
        print('\n\033[1m╔══════════════════════════════════════════╗\033[0m')
        print(f'\033[1m║{text:^44}║\033[0m')
        print('\033[1m╚══════════════════════════════════════════╝\033[0m\n')

def ask(header, default='', secret=False):
    global GUM_BIN, GUM_WARNED
    if GUM_BIN:
        cmd = [GUM_BIN, 'input', '--header', header, '--placeholder', 'type here, or Enter to accept default']
        if default:
            cmd += ['--value', default]
        if secret:
            cmd += ['--password']
        started = time.monotonic()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except OSError:
            return ask_plain(header, default, secret)
        elapsed = time.monotonic() - started
        # A real interactive session takes at least a few hundred ms (the
        # time to read the prompt and press a key) — anything faster means
        # gum returned without actually waiting for input at all (seen in
        # some sudo + non-standard-terminal combinations where gum can
        # write to /dev/tty but the read side silently no-ops instead of
        # erroring). Disable gum for the rest of THIS wizard run rather
        # than looping the required-field error forever with no visible prompt.
        if elapsed < 0.3 and not result.stdout.strip():
            if not GUM_WARNED:
                print('  \033[33m⚠ gum isn\\'t receiving interactive input in this terminal — '
                      'switching to plain-text prompts for the rest of setup.\033[0m')
                GUM_WARNED = True
            GUM_BIN = ''
            return ask_plain(header, default, secret)
        if result.returncode != 0:
            print('\nAborted.')
            sys.exit(1)
        return result.stdout.rstrip('\n')
    return ask_plain(header, default, secret)

def ask_plain(header, default, secret):
    prompt = f'  ? {header}'
    if default:
        prompt += f' [{mask(default) if secret else default}]'
    prompt += ': '
    try:
        return getpass.getpass(prompt) if secret else input(prompt)
    except (KeyboardInterrupt, EOFError):
        print('\nAborted.')
        sys.exit(1)

def ask_confirm(prompt_text):
    if GUM_BIN:
        result = subprocess.run([GUM_BIN, 'confirm', prompt_text, '--default'])
        return result.returncode == 0
    try:
        c = input(f'  ? {prompt_text} [Y/n]: ').strip()
    except (KeyboardInterrupt, EOFError):
        print('\nAborted.')
        sys.exit(1)
    return c.lower() in ('', 'y', 'yes')

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
    settings_list = reg.get('settings', [])
    total = len(settings_list)

    answers = {}

    while True:
        answers = {}
        show_header('UNOTUSK Registry Configuration')

        for idx, s in enumerate(settings_list, start=1):
            name = s['name']
            desc = s['description']
            default = s.get('default', '')
            if name in defaults:
                default = defaults[name]

            if s.get('generator') == 'uuid' and not default:
                default = str(uuid.uuid4())

            # GITHUB_CALLBACK_URL has no static safe default — it must
            # point at US's directly-published OAuth port (host 3100, see
            # installer/templates/docker-compose.yml), not the HOSTNAME's
            # bare 443/3000, because Caddy doesn't proxy /auth/* yet
            # (templates/Caddyfile only routes the dead /oidc/* path).
            # Left blank here, a customer will plausibly type
            # http://<hostname> and silently break login.
            if s.get('auto_default') == 'github_callback' and not default:
                callback_host = answers.get('HOSTNAME', 'localhost')
                default = f'http://{callback_host}:3100/auth/callback'

            required = s.get('required', False)
            is_secret = s.get('secret') is True
            env_val = os.environ.get(name, '')
            if env_val:
                default = env_val

            if unattended:
                if required and not default:
                    print(f'Error: Unattended mode but {name} is missing.', file=sys.stderr)
                    sys.exit(1)
                answers[name] = default.strip() if isinstance(default, str) else default
                continue

            val = ''
            while True:
                val = ask(f'[{idx}/{total}] {desc}', default, is_secret)
                # Strip whitespace unconditionally — customers routinely
                # paste secrets/keys with a leading/trailing space or
                # newline picked up from wherever they copied it, and a
                # stray space silently breaks auth (invalid_client, bad
                # signature, etc.) with no useful error at the point of
                # failure. Safe for every field type here, secret or not.
                val = val.strip()
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

        if unattended:
            break

        review_lines = []
        for s in settings_list:
            name = s['name']
            v = answers.get(name, '')
            shown = mask(v) if s.get('secret') is True else v
            review_lines.append(f'{name:<28} {shown}')
        show_header('Configuration review')
        print('\n'.join(f'  {line}' for line in review_lines))
        print('')
        if ask_confirm('Confirm and proceed with this configuration?'):
            break
        print('\n  → Restarting — your previous answers are pre-filled as defaults; press Enter to keep, or type a new value to change.\n')
        defaults = dict(answers)

    with open('$wizard_conf_file', 'w') as f:
        f.write('# UNOTUSK Selections\n')
        for k, v in answers.items():
            f.write(f'{k}=\"{v}\"\n')

    admin_pw = os.environ.get('ADMIN_PASSWORD', '')
    if not unattended:
        pw1 = ask('Administrator Password (leave blank to auto-generate)', '', True).strip()
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
EMPLOYEE_CA_DIR=/app/certs
GITHUB_CLIENT_ID=$GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET=$GITHUB_CLIENT_SECRET
GITHUB_CALLBACK_URL=$GITHUB_CALLBACK_URL
GITHUB_ORG=$GITHUB_ORG
OIDC_PROVIDER=$OIDC_PROVIDER
EOF

  cat > "$INSTALL_DIR/UPS/.env" <<EOF
LOG_LEVEL=info
LICENSE_HEARTBEAT_INTERVAL=60
LICENSE_GRACE_PERIOD=18000
PLATFORM_JWKS_PUSH_URL=${PLATFORM_URL}/internal/orgs/${ORG_ID}/jwks
ORG_ID=$ORG_ID
JWKS_PUSH_SECRET=$JWKS_PUSH_SECRET
ADMIN_USER_IDS=$ADMIN_USER_IDS
EOF

  cat > "$INSTALL_DIR/AI-PIE/.env" <<EOF
LOG_LEVEL=info
ORG_ID=$ORG_ID
QDRANT_API_KEY=$QDRANT_API_KEY
CF_AIG_TOKEN=$CF_AIG_TOKEN
CF_AIG_BASE_URL=$CF_AIG_BASE_URL
VOYAGE_API_KEY=$VOYAGE_API_KEY
GITHUB_APP_ID=$GITHUB_APP_ID
GITHUB_APP_INSTALLATION_ID=$GITHUB_APP_INSTALLATION_ID
GITHUB_APP_PRIVATE_KEY="$GITHUB_APP_PRIVATE_KEY"
GITHUB_ORG=$GITHUB_ORG
JIRA_URL=$JIRA_URL
JIRA_EMAIL=$JIRA_EMAIL
JIRA_TOKEN=$JIRA_TOKEN
JIRA_PROJECT_KEY=$JIRA_PROJECT_KEY
EOF

  # Lock down config permissions immediately
  secure_configuration_files

  write_client_env

  log_to_file_info "Configuration wizard save sequence complete."
}

# UCA (and eventually UAC) resolve their auth/gRPC endpoints from
# /etc/unotusk/client.env (see UCA/src-tauri/src/config.rs::
# deployment_config_paths / apply_config_file) — only filling in vars not
# already set in the process environment, so this is purely a deployment-
# specific override layer, never a substitute for real per-user config.
#
# Without this file, UCA falls back to its compiled-in defaults
# (http://localhost:3000/auth/login etc.), which don't match this
# installer's actual port choices (US's OAuth HTTP port is published on
# host 3100, not 3000 — see templates/docker-compose.yml) and silently
# break login (ERR_CONNECTION_REFUSED) with no indication why.
#
# CLIENT_CRT/CLIENT_KEY are intentionally left unset: US can issue
# per-employee mTLS client certs on demand (POST /client-cert/issue,
# session-gated — see US/src/employee_pki.rs), but UCA doesn't consume
# that endpoint yet (server-side only so far). Until that's built,
# gRPC-dependent features (fetching UPS/US data) won't work even with
# this file in place — only the HTTP-based OAuth login flow does.
write_client_env() {
  log_to_file_info "Writing /etc/unotusk/client.env for desktop client discovery..."

  # AUTH_SAN/COMPANY_SAN are hardcoded to "localhost" because that's the
  # only SAN entry certificates.sh actually bakes into US/UPS's directly-
  # published server certs (see "subjectAltName=DNS:...,DNS:localhost") —
  # it never includes the customer's real $HOSTNAME. Fine for this
  # loopback test deployment; a real non-localhost HOSTNAME would need
  # certificates.sh's SAN generation fixed too before this file would be
  # correct for it. Not attempting that here — separate, larger change.

  local client_env_dir="/etc/unotusk"
  local client_ca_path="$client_env_dir/ca.crt"
  mkdir -p "$client_env_dir"

  # The CA is public (it only signs server certs employees' machines need
  # to trust) — copy it somewhere every local user can read, since
  # US/certs/ca.crt lives inside root-owned $INSTALL_DIR and UCA runs as
  # the logged-in desktop user, not root.
  if [ -f "$INSTALL_DIR/US/certs/ca.crt" ]; then
    cp "$INSTALL_DIR/US/certs/ca.crt" "$client_ca_path"
    chmod 644 "$client_ca_path"
  fi

  cat > "$client_env_dir/client.env" <<EOF
# UNOTUSK Desktop Client Configuration — Generated on $(date -u)
# Consumed by UCA (and eventually UAC) at startup. Do not edit by hand —
# regenerated on every 'unotusk reconfigure' / reinstall.
AUTH_LOGIN_URL=http://${HOSTNAME}:3100/auth/login
AUTH_BASE_URL=http://${HOSTNAME}:3100
AUTH_GRPC_URL=https://${HOSTNAME}:50052
COMPANY_GRPC_URL=https://${HOSTNAME}:50051
AUTH_SAN=localhost
COMPANY_SAN=localhost
UPS_BASE_URL=https://${HOSTNAME}:8443
CA_CERT=$client_ca_path
EOF
  chmod 644 "$client_env_dir/client.env"

  log_to_file_info "/etc/unotusk/client.env written."
}
