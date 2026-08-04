# UNOTUSK — End-to-End Install Manual

A single walkthrough from `curl | bash` on a fresh customer machine to a
working UCA (employee) and UAC (admin) desktop client. For local
development instead of a customer-style install, see `DEVELOPMENT.md`. For
architecture background, see `CLAUDE.md`.

This repo (`install-unotusk`) is what actually ships to customers — the
`US`, `UPS`, `AI-PIE`, `UP`, `UCA`, `UAC` directories are separate,
independently-owned repos checked out here as gitlinks for convenience;
each also has its own `manual.md` covering build/run/config details
specific to that service.

---

## 0. What gets installed where

```
Customer server (Linux, Docker)          Employee/admin laptops
┌─────────────────────────────┐          ┌─────────────────┐
│ US   (auth)     :3100/50052 │◄────────►│ UCA  (employee)  │
│ UPS  (company)  :50051      │◄────────►│ UAC  (admin)     │
│ AI-PIE (intel)  :8000       │          └─────────────────┘
│ Postgres, Qdrant, Phoenix,  │
│ Redis  (internal only)      │
└──────────────┬──────────────┘
               │ outbound-only license heartbeat + JWKS push
               ▼
      UP (Platform) — Render + Neon, cloud-only
      https://unotusk-platform-service.onrender.com
```

`UP` is never installed locally — it's a permanent cloud service this repo's
installer talks to, not something `docker-compose.yml` starts.

---

## 1. Server-side install (US + UPS + AI-PIE via Docker Compose)

### 1.1 One-command path (what customers actually run)

```bash
curl -fsSL https://install.unotusk.com | bash
```

This hits `bootstrap/install.sh` (served by Vercel from this repo, see
`vercel.json`), which OS-checks, installs Docker if missing, downloads the
versioned installer tarball from GitHub Releases, verifies its SHA-256,
unpacks it, and hands off to `installer/install.sh` — a 9-stage resumable
installer. For unattended/scripted installs, set env vars before piping:

```bash
export UNATTENDED=1
export UNOTUSK_ORG_NAME="Acme Corp"
export UNOTUSK_LICENSE_KEY="UNOT-XXXX-XXXX-XXXX"
export UNOTUSK_OIDC_ISSUER="https://login.microsoftonline.com/<tenant>/v2.0"
export UNOTUSK_OIDC_CLIENT_ID="your-client-id"
export UNOTUSK_OIDC_CLIENT_SECRET="your-client-secret"
curl -fsSL https://install.unotusk.com | bash
```

Note: as of 2026-08-04 the *live* auth path is still GitHub OAuth
(`US/src/legacy/`), not OIDC — see `CLAUDE.md` §6. The wizard below
collects OIDC fields for the eventual AMEND-008 migration but the GitHub
OAuth fields (`GITHUB_CLIENT_ID`/`SECRET`/`CALLBACK_URL`/`ORG`) are what
actually gate login today.

### 1.2 What the installer's interactive wizard asks for

Driven by `installer/settings.yaml` (rendered via `gum` if available,
plain `read` prompts otherwise — see `installer/lib/configuration.sh`):

- `ORG_NAME`, `ORG_ID`, `LICENSE_KEY`, `PLATFORM_URL`
- `HOSTNAME`, `TIMEZONE`, `CERT_OPTION` (self-signed dev CA vs. bring-your-own)
- `ADMIN_EMAIL`
- `OIDC_PROVIDER` (future path) plus the GitHub OAuth fields that are
  live today: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`,
  `GITHUB_CALLBACK_URL`, `ADMIN_USER_IDS`, `GITHUB_ORG` (required —
  gates login to members of this GitHub org)
- Optional integrations: `CF_AIG_TOKEN`/`CF_AIG_BASE_URL` (Cloudflare AI
  Gateway), `VOYAGE_API_KEY`, `GITHUB_APP_ID`/`GITHUB_APP_PRIVATE_KEY`/
  `GITHUB_APP_INSTALLATION_ID` (preferred ingestion auth for AI-PIE once
  registered), `JIRA_URL`/`JIRA_EMAIL`/`JIRA_TOKEN`/`JIRA_PROJECT_KEY`

### 1.3 What the 9-stage installer does

`installer/install.sh` sources `installer/lib/{common,validation,
filesystem,network,docker,compose,configuration,certificates,
registration,health,services,cli}.sh` and:

1. Root/privilege check, idempotency check (detects an existing install
   and offers upgrade/reconfigure/repair/reinstall/remove/abort)
2. Filesystem layout under `/opt/unotusk`
3. Docker install/verification
4. Wizard → writes config
5. mTLS certificate generation (`installer/lib/certificates.sh`) — shared
   mesh CA for US↔UPS↔AI-PIE↔UCA/UAC, plus a **separate** Platform-issued
   CA/cert pair for UPS↔UP heartbeat only. These are two distinct trust
   domains — don't reuse one for the other.
6. Renders `templates/docker-compose.yml` with real image tags from
   `installer/manifest.json` (`ghcr.io/anikethanshetty/unotusk-auth-server`,
   `ghcr.io/anikethanshetty/unotusk-company-server`,
   `ghcr.io/techteam-zephvion/ai-pie`, plus `postgres:16-alpine`,
   `redis:7-alpine`, `qdrant/qdrant:v1.15.1`, `arizephoenix/phoenix`,
   `caddy:2.7-alpine`)
7. `docker compose up -d`
8. Health checks (`installer/lib/health.sh`)
9. Registration with `UP` (license activation, org creation)

Verify: `docker compose ps` — all services healthy within ~60s.

### 1.4 The `unotusk` CLI (installed to PATH)

```bash
unotusk status              # docker compose ps
unotusk logs [service]      # tail logs, all or one service
unotusk doctor              # full diagnostics
unotusk health               # quick health check
unotusk backup / restore     # pg_dump + config + certs archive
unotusk update                # rolling update, auto-backup first
unotusk rollback              # revert to last backup
unotusk uninstall
unotusk pair us|ups           # print a 10-minute, single-use pairing code
                               # for UAC's "Connect Auth Service" /
                               # "Pair with your UPS instance" screens
```

`unotusk pair` calls a loopback-only endpoint inside the container
(`POST http://127.0.0.1:<port>/internal/pairing-code`) — it cannot be
triggered remotely, only via `docker exec` from the CLI.

### 1.5 Manual/local-dev path (not the customer path)

For iterating on this repo itself rather than a real customer install,
see `DEVELOPMENT.md` §3 — `cp .env.example .env` (+ per-service `.env`
files), then `docker compose up -d` directly using the root
`docker-compose.yml`. This is deliberately separate from
`installer/install.sh`; don't confuse the two (see `CLAUDE.md` §2 repo
table and `DEVELOPMENT.md` §1's warning about the older root `install.sh`).

---

## 2. Employee client (UCA) — build, install, configure

Full detail: `UCA/manual.md`. Summary:

```bash
cd UCA
npm install
npx tauri build     # release build; or `npx tauri dev` for hot reload,
                     # or `npm run dev` for Next.js-frontend-only iteration
sudo dpkg -i src-tauri/target/release/bundle/deb/*.deb
```

Configuration lives at `/etc/unotusk/client.env`, generated by the
installer's `write_client_env()` (`installer/lib/configuration.sh`) — not
hand-edited on a real install. Key fields: `CA_CERT`/`CLIENT_CRT`/
`CLIENT_KEY` (mesh CA bootstrap client cert, required even to call US's
`ExchangeRef`), `PLATFORM_BASE_URL` (must be the real Render URL, not the
placeholder domain), `UPS_BASE_URL` (must point at AI-PIE's port 8000 —
"Ask" always targets AI-PIE, never UPS's own port despite the variable
name), `UPS_CA_CERT`/`UPS_CLIENT_CRT`/`UPS_CLIENT_KEY` (AI-PIE's own dev
CA, separate from the mesh CA).

**Gotcha:** `client.env` is read once at process startup. After editing
it, fully kill the process (`pkill -9 -f zephvion`) before relaunching —
closing the window isn't enough, and a second launch while an old process
is still alive silently no-ops.

Debug logs: `DEBUG_FLOW=1 RUST_LOG=debug /usr/bin/zephvion > /tmp/zephvion.log 2>&1 &`

---

## 3. Admin client (UAC) — build, install, configure

Full detail: `UAC/manual.md`. Same Tauri v2 build workflow as UCA
(`npm install`, `npx tauri build`, `dpkg -i`). Pairs with US and UPS via
`unotusk pair us` / `unotusk pair ups` (§1.4) rather than manual PEM paste.

---

## 4. Verifying a clean install end-to-end

1. `unotusk status` — all containers healthy
2. `unotusk pair us` and `unotusk pair ups` — get pairing codes
3. Launch UAC, redeem both codes, confirm employee directory loads
4. Launch UCA, log in via GitHub OAuth (must be a member of the
   configured `GITHUB_ORG`), confirm project list loads (this is the
   step that fails first if `PLATFORM_BASE_URL` is wrong)
5. Run an "Ask" / spec-generation request in UCA — exercises the
   UCA→AI-PIE path and confirms `UPS_BASE_URL`/AI-PIE certs are correct

---

## 5. Where to go deeper

| Topic | Doc |
|---|---|
| Architecture, amendment log, live infra status | `CLAUDE.md` |
| Local dev loop, port reference, `client.env` troubleshooting table | `DEVELOPMENT.md` |
| Per-service build/run/config | `US/manual.md`, `UPS/manual.md`, `AI-PIE/manual.md`, `UP/manual.md`, `UCA/manual.md`, `UAC/manual.md` |
| Installer internals | `installer/docs/`, `installer/lib/*.sh` |
