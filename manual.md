# manual.md — install-unotusk

This is the installer-infrastructure repo itself: the code that produces
`curl -fsSL https://install.unotusk.com | bash` and turns it into a
running UNOTUSK stack on a customer's server. For the *narrative*
walkthrough of a clean install (curl → wizard → running stack → UCA/UAC),
see `MANUAL.md` in this same directory. This file documents the repo's
own layout, how to build/test/release it, and how the local checkouts of
the six other repos (`US`, `UPS`, `AI-PIE`, `UP`, `UCA`, `UAC`) relate to
it.

## What's actually in this repo vs. what's a gitlink

Only the root-level files belong to `install-unotusk` itself:
`docker-compose.yml`, `.env.example`, `install.sh`, `installer/`,
`bootstrap/`, `compose/`, `scripts/`, `dist/`, `README.md`,
`DEVELOPMENT.md`, `CLAUDE.md`. `US/ UPS/ AI-PIE/ UP/ UCA/ UAC/` are
separate, independently-owned git repos checked out here as gitlinks
(bare commit-SHA pointers) purely for local-dev convenience — this repo
being public does not expose their source. See `CLAUDE.md` §0/§2.

**Two separate install paths exist in this repo — don't conflate them:**

- `installer/` — the real customer-facing installer (wizard, cert
  generation, docker-compose template rendering, `unotusk` CLI). This is
  what `bootstrap/install.sh` downloads and runs.
- Root `install.sh` + `scripts/` — an older, local-dev-only install path,
  not what customers get, has known bugs of its own.

## Building / packaging a release

```bash
scripts/release.sh          # tag-and-publish automation — packages
                             # installer/ into a versioned tarball,
                             # publishes to GitHub Releases
```

CI (`.github/workflows/`) builds and publishes on tag push. The bootstrap
script served at `install.unotusk.com` (via Vercel, routed by
`vercel.json`) downloads the tarball, verifies its SHA-256, then hands off
to `installer/install.sh`.

## Testing the installer locally

```bash
installer/tests/            # test scripts for installer stages
installer/doctor.sh          # can also be run standalone against an
                              # existing /opt/unotusk install for diagnostics
```

For iterating on the installer itself, run it against a disposable VM or
container rather than a real machine — it writes to `/opt/unotusk`,
installs Docker if missing, and registers with the live Platform (`UP`)
unless pointed at a non-production `PLATFORM_URL`.

## Running the full stack for local development

This is different from running the installer — see `DEVELOPMENT.md` §3
for the direct-compose path (`cp .env.example .env` + per-service
`.env` files + `docker compose up -d` using the root `docker-compose.yml`
directly, bypassing the wizard/installer entirely).

## Deploying this repo's own Vercel-hosted bootstrap page

```bash
vercel deploy            # preview
vercel deploy --prod     # production, updates install.unotusk.com
```

`vercel.json` routes `/` to `bootstrap/install.sh` as `text/plain`, which
is what makes `curl -fsSL https://install.unotusk.com` work.

## Related docs

- `MANUAL.md` — combined end-to-end install walkthrough (curl → UCA/UAC)
- `DEVELOPMENT.md` — local dev loop, port reference, `client.env` troubleshooting
- `CLAUDE.md` — architecture, amendment log, live infra status
- `README.md` — original quickstart / repo structure overview
- Per-service manuals: `US/manual.md`, `UPS/manual.md`, `AI-PIE/manual.md`,
  `UP/manual.md`, `UCA/manual.md`, `UAC/manual.md`
