# UNOTUSK Installer Infrastructure

> **One-command enterprise deployment** — `curl -fsSL https://install.unotusk.com | bash`

This repository hosts the installer infrastructure for the [UNOTUSK](https://unotusk.com) platform. It is served via Vercel on the `install.unotusk.com` custom domain.

---

## Architecture

```
GitHub Repository (unotusk/install)
        │
        ▼
    Vercel CDN
        │  serves bootstrap/install.sh as text/plain
        ▼
install.unotusk.com     ← curl -fsSL https://install.unotusk.com | bash
        │
        ▼
  Bootstrap Script      (~180 lines, OS check + Docker install)
        │  downloads from GitHub Releases
        ▼
  Versioned Tarball     unotusk-installer.tar.gz
        │  SHA-256 verified
        ▼
  Full Installer        installer/install.sh (9 stages, resumable)
        │
        ▼
  /opt/unotusk          Running UNOTUSK Platform
```

---

## Repository Structure

```
install/
├── bootstrap/
│   └── install.sh              # Served at install.unotusk.com (< 200 lines)
│
├── installer/
│   ├── install.sh              # 9-stage versioned installer
│   ├── uninstall.sh            # Safe removal with data protection
│   ├── update.sh               # Rolling update with auto-backup
│   ├── doctor.sh               # Full system diagnostics
│   ├── backup.sh               # pg_dump + config + certs archive
│   ├── restore.sh              # Full restore from backup
│   ├── verify.sh               # Post-install integrity check
│   └── rollback.sh             # Auto-detect and rollback to last backup
│
├── compose/
│   ├── docker-compose.yml      # Production stack (GHCR images)
│   ├── docker-compose.override.yml  # Dev overrides (local builds)
│   └── .env.example            # Documented environment variables
│
├── scripts/
│   └── release.sh              # Tag-and-publish release automation
│
├── docs/
│   ├── deployment.md           # Production deployment guide
│   ├── release-strategy.md     # Versioning and release process
│   └── rollback-strategy.md    # Incident rollback procedures
│
├── .github/
│   └── workflows/
│       └── release.yml         # GitHub Actions: build + publish on tag push
│
├── vercel.json                 # Routes / → bootstrap/install.sh
└── README.md
```

---

## Quick Start

### Customer Installation

```bash
# Interactive (recommended)
curl -fsSL https://install.unotusk.com | bash

# Unattended / automated
export UNATTENDED=1
export UNOTUSK_ORG_NAME="Acme Corp"
export UNOTUSK_LICENSE_KEY="UNOT-XXXX-XXXX-XXXX"
export UNOTUSK_OIDC_ISSUER="https://login.microsoftonline.com/<tenant>/v2.0"
export UNOTUSK_OIDC_CLIENT_ID="your-client-id"
export UNOTUSK_OIDC_CLIENT_SECRET="your-client-secret"
curl -fsSL https://install.unotusk.com | bash
```

### After Installation

```bash
unotusk status       # Service health overview
unotusk doctor       # Full diagnostic report
unotusk logs         # Tail all logs
unotusk update       # Upgrade to latest version
unotusk backup       # Create a backup
unotusk rollback     # Rollback to last backup
unotusk uninstall    # Remove UNOTUSK (data preserved by default)
```

---

## Installer Stages

| Stage | Description |
|-------|-------------|
| 1 | **Validate** — OS, Docker, RAM (3.5 GB min), disk (10 GB min), ports, internet |
| 2 | **Configure** — Interactive wizard or env vars → generates `.env` + secrets |
| 3 | **Certificates** — Local CA, US/UPS/AI-PIE mTLS certs via OpenSSL |
| 4 | **Download** — Fetches `docker-compose.yml` from this repo at the tagged version |
| 5 | **Pull images** — `docker compose pull` all services |
| 6 | **Start** — Health-aware startup: `postgres → qdrant+phoenix → us → ups → ai-pie` |
| 7 | **Register** — License registration ping to UNOTUSK Platform |
| 8 | **Verify** — HTTP endpoint probes + mTLS check |
| 9 | **Finalise** — Installs `unotusk` CLI, writes version file |

The installer is **resumable** — if it fails at any stage, re-running skips completed stages.

---

## Release Strategy

See [docs/release-strategy.md](docs/release-strategy.md) for the full process.

**Quick summary:**

```bash
# 1. Make your changes, commit to main
git commit -am "feat: new feature"
git push origin main

# 2. Create a release
./scripts/release.sh v1.2.0

# GitHub Actions automatically:
#   - Builds unotusk-installer.tar.gz
#   - Generates SHA-256 checksum
#   - Publishes GitHub Release with assets
```

The bootstrap script always fetches `latest` from GitHub Releases unless `UNOTUSK_VERSION` is overridden.

---

## Vercel Deployment

1. Import this repository into Vercel
2. Set the custom domain to `install.unotusk.com`
3. No build command needed — Vercel serves static files
4. The `vercel.json` routes `/` → `bootstrap/install.sh` with `Content-Type: text/plain`

---

## Security

| Mechanism | Implementation |
|-----------|---------------|
| **Transport** | HTTPS-only via Vercel + TLS |
| **Integrity** | SHA-256 checksum verified before execution |
| **Secrets** | Generated fresh per install, stored chmod 600 |
| **mTLS** | Local CA + per-service certificates, never shared |
| **Bash hardening** | `set -Eeuo pipefail` throughout |
| **No data destruction** | Multi-confirm prompts for any destructive action |

---

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Ubuntu 22.04 / Debian 11 | Ubuntu 24.04 LTS |
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8 GB |
| Disk | 10 GB | 50 GB SSD |
| Docker | 24.0+ | Latest stable |
| Internet | Required for install | — |

**Required inbound ports:** `3000`, `8444`, `50051`, `50052`  
**Required outbound:** TCP `443` + `50051` to `platform.unotusk.com`

---

## License

Proprietary — © Zephvion Pvt. Ltd. All rights reserved.
