# CLAUDE.md — UNOTUSK Workspace

## 0. What this is

This directory **is itself a git repository** — `install-unotusk`, public
since 2026-08-03. Each subdirectory below (`US`, `UPS`, `AI-PIE`, `UCA`,
`UAC`, `UP`) is its own independent, separately-owned git repo, most of
them private — they show up here as gitlinks (bare commit-SHA pointers,
the same mechanism git submodules use), so this repo being public does not
expose any of their source. There is no monorepo/submodule tooling beyond
that; treat each service as a separate project that happens to live nested
under this one for local development convenience.

**This file is public.** Anything written into it should read like
appropriate public engineering documentation — architecture facts,
deployment topology, ops conventions — not an internal incident writeup or
a vulnerability play-by-play. Detailed session/work logs are kept locally
only (`logs/`, gitignored here) and never committed to this repo.

Root-level files (`docker-compose.yml`, `.env.example`, `scripts/`,
`README.md`, `install.sh`, `installer/`, `dist/`) belong to
`install-unotusk` itself and exist to run the customer-local part of the
stack together, and to package the real customer-facing installer — see §3.

## 1. Architecture — Hybrid Deployment

```
                    Internet
                         |
                  Cloudflare DNS
                         |
                platform.unotusk.com
                         |
                      Render
                         |
                 UNOTUSK Platform (UP)
                         |
                  Neon PostgreSQL
                         ^
                         |
                License heartbeat (outbound only)
                         |
──────────────────────────────────────────────────
            Customer Infrastructure (Docker Compose)

        US (Auth Service)  -- exposed --
                |
                v
        UPS (Company Server) -- license/degraded-mode source of truth
                |
                v
              AI PIE (intelligence engine)
                |
          Qdrant + Postgres + Phoenix
```

- **Platform (`UP`)** is the only cloud-hosted service (Render + Neon). It never
  has inbound access into any customer's infrastructure — outbound-only license
  heartbeat from UPS is the sole connection between the two worlds.
- **US, UPS, AI-PIE** are customer-local, single-tenant (one deployment per
  customer), run together via the root `docker-compose.yml`.
- **UAC / UCA** are frontend clients (Tauri) — admin console and employee client
  respectively — not containerized here; they connect to US/UPS over the network.

## 2. Repositories

| Dir | Role | Remote | Language | Deployment |
|---|---|---|---|---|
| `US/` | Auth Service — OIDC federation, sessions, UNOTUSK access tokens | `Anikethanshetty/Unotusk-Auth-server` | Rust (axum + tonic) | Customer Docker Compose |
| `UPS/` | Company Server — licensing, Degraded Mode, UAC admin pairing | `Anikethanshetty/Unotusk-Company-Server` | Rust | Customer Docker Compose |
| `AI-PIE/` | Intelligence engine — ingestion, spec/report generation, ontology | `Techteam-zephvion/AI-PIE` | Python (FastAPI) | Customer Docker Compose |
| `UP/` | Platform — license issuance, `Client` management | `Techteam-zephvion/UP` | Rust | Render + Neon (cloud only) |
| `UCA/` | Employee client (Tauri) | `Techteam-zephvion/Unotusk` | TypeScript/Next.js + Tauri | Customer network |
| `UAC/` | Admin console (Tauri) | `Techteam-zephvion/UnotuskAdminConsole` | TypeScript/Next.js + Tauri | Customer network |

Each repo has its own `CLAUDE.md`/`AGENTS.md` with project-specific detail — read
the relevant one before working inside that directory. `US/` and `UPS/`'s
`CLAUDE.md` are currently RTK-tool + graphify boilerplate only (no architecture
notes); `UCA/CLAUDE.md` and `AI-PIE/CLAUDE.md` have substantive per-repo docs.

## 3. Canonical architecture record — read before proposing architecture changes

`docs/UNOTUSK_FILES/UNOTUSK_AMENDMENT_LOG.md` is the **single source of truth**
for every accepted deviation from the original locked V1 architecture. If a
spec, a milestone doc, or a README disagrees with the amendment log, the
amendment log wins. Key accepted decisions relevant to auth/deployment:

- **AMEND-006**: customer-hosted persistent server per client (not per-laptop).
- **AMEND-008**: auth is a dedicated Rust Auth Service (`US`) performing **OIDC
  federation to the customer's own enterprise IdP** (Entra/Okta/Google
  Workspace) — explicitly *not* "pluggable personal GitHub/Google OAuth."
  Reason: personal OAuth verifies an individual, not org membership, and has no
  central revocation. `US` mints opaque session tokens, not a custom JWT format.
- **AMEND-001**: Docker Compose packaging (not Hetzner-hosted).

Before implementing anything that looks like a new auth mechanism, a JWT
format, or a change to which services talk to which, check the amendment log
first — a milestone spec that seems to contradict it needs a new amendment
(status `DRAFT`) before implementation, not silent reinterpretation.

## 4. Local development

```bash
cp .env.example .env                      # POSTGRES_PASSWORD, PLATFORM_URL, PLATFORM_LICENSE_KEY
cp US/.env.example US/.env
cp UPS/.env.example UPS/.env
cp AI-PIE/.env.example AI-PIE/.env
# place mTLS certs: US/certs/, UPS/certs/ (+ UPS/certs/platform/), AI-PIE/certs/
docker compose up -d
docker compose ps      # all healthy within ~60s
```

Only `US` publishes ports to the host (3000 OIDC HTTP, 8444 UAC admin pairing).
`UPS`, `AI-PIE`, Postgres, Qdrant, Phoenix are internal-only on the
`unotusk_internal` bridge network. **`UP` (Platform) is deliberately not in this
compose file** — it's cloud/Render-only by design; see root `README.md` for the
Render deployment steps.

Two separate mTLS trust domains exist — don't conflate them: the shared local
dev CA (US↔UPS↔UAC) and a second Platform-issued CA/cert pair
(`UPS/certs/platform/*`) for UPS↔Platform license heartbeat only.

## 5. Git conventions in this workspace

- Per-repo work branches follow `claude/local-work-YYYY-MM-DD` or a named
  milestone branch (e.g. `MVP_build`) — check `git branch --show-current` in
  each repo rather than assuming; branches are not synchronized across repos.
  As of 2026-08-03: `US`, `UPS`, `AI-PIE` → `MVP_build`; `UCA`, `UAC`, `UP`,
  and this workspace's own `install-unotusk` repo → `main`.
- Before switching branches or discarding anything, check `git status` — several
  of these repos carry uncommitted work between sessions; stash (`-u`) rather
  than lose it.
- Watch for divergence between local and `origin` on `main`/base branches
  (seen previously on `UPS`) — reconcile deliberately, don't force-push over it.

## 6. Live infrastructure and status (as of 2026-08-03)

**UP is deployed and live** at
`https://unotusk-platform-service.onrender.com` (Render free tier — expect
~60s cold start after idle; upgrading to a paid plan is a pending decision,
not yet made). Real Neon Postgres backs it. A stale, unused
`unotusk-auth-service` Render deployment also exists from before AMEND-014
— unreferenced anywhere in UP's code, safe to ignore/delete.

**The full local install path** (`curl | sudo bash` → wizard → running
US/UPS/AI-PIE stack → UCA login → spec generation) has been verified
working end-to-end. Container images for all three services publish to
GHCR via each repo's own `.github/workflows/publish.yml` and pull
publicly (`ghcr.io/anikethanshetty/unotusk-auth-server`,
`ghcr.io/anikethanshetty/unotusk-company-server`,
`ghcr.io/techteam-zephvion/ai-pie`) — `installer/manifest.json` and
`installer/templates/docker-compose.yml` reference these directly.

**Auth**: GitHub OAuth login (still the live path — `US/src/legacy/`, not
`/oidc/*`; AMEND-008's OIDC migration is not finished, and stale
doc-comments in that directory claiming it's "deprecated/unmounted" are
wrong — check `US/src/http/mod.rs`'s router before trusting those
comments) enforces org membership as of 2026-08-03; `GITHUB_ORG` is a
required config/wizard field whenever GitHub OAuth is configured.

**Employee client certs**: `US` can issue per-employee mTLS client
certificates on demand (`POST /client-cert/issue`, session-gated),
signed by a CA dedicated to that purpose and kept separate from the
shared US↔UPS↔AI-PIE mesh CA (see `US/src/employee_pki.rs`'s doc comment
for the reasoning). `installer/lib/certificates.sh` provisions this CA at
install time. UCA's own consumption of this endpoint (requesting and
using a cert) is not built yet — server-side only so far.

**Self-service project registration**: `UP`'s `POST /api/projects`
finds-or-creates the organization/ups_instance and grants the creating
employee membership in one call — no PM/admin UI for this yet, API only.

**Known port assignments**: US → 3000 (OIDC/GitHub HTTP), 8444 (UAC admin
pairing), 50052 (gRPC, mTLS); UPS → 8443 (UAC admin pairing), 50051 (gRPC
business API, mTLS); AI-PIE → 8000 (UCA's "Ask" calls — configured via
UCA's `UPS_BASE_URL`, not a UPS-specific setting).

**Still open**: no production GitHub App registered yet for AI-PIE
ingestion auth (the code path for it is complete and prefers it over a raw
token automatically once configured); Render free-tier cold starts vs.
self-hosting on a VPS is an undecided cost/ops tradeoff; UCA/UAC currently
have no public release/download mechanism a customer could use directly.

## 7. What not to do

- Don't add Redis, JWT issuance, or personal-OAuth-provider apps to `US` without
  checking §3 first — these were each evaluated and are either unimplemented by
  design (Redis: Postgres+sweeper already covers TTL/session state) or would
  contradict AMEND-008.
- Don't commit certificate/key material. `US`'s `main` branch (upstream, not
  `MVP_build`) has a known instance of this in its history (commit `7a7e144`) —
  treat those certs as compromised if that branch is ever used as a base; don't
  repeat the mistake.
