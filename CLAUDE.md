# CLAUDE.md — UNOTUSK Workspace

## 0. What this is

This directory is the top-level workspace containing all UNOTUSK repositories as
sibling checkouts. It is **not itself a git repository** — each subdirectory below
is its own independent git repo with its own remote. There is no monorepo/submodule
tooling; treat each service as a separate project that happens to live under one
parent folder for local development convenience.

Root-level files (`docker-compose.yml`, `.env.example`, `scripts/`, `README.md`)
exist to run the customer-local part of the stack together — see §3.

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
  As of the current session: `US`, `UPS`, `AI-PIE`, `UCA` → `MVP_build`; `UAC`,
  `UP` → `main`.
- Before switching branches or discarding anything, check `git status` — several
  of these repos carry uncommitted work between sessions; stash (`-u`) rather
  than lose it.
- Watch for divergence between local and `origin` on `main`/base branches
  (seen previously on `UPS`) — reconcile deliberately, don't force-push over it.

## 6. Live infrastructure and known gaps (as of 2026-08-01)

**UP is actually deployed and live** at
`https://unotusk-platform-service.onrender.com` (Render free tier — expect
~60s cold start after idle; upgrading to a paid plan is a pending decision).
Real Neon Postgres backs it. A stale, unused `unotusk-auth-service` Render
deployment also exists from before AMEND-014 — `AUTH_SERVICE_URL` is
unreferenced anywhere in UP's code, safe to ignore/delete.

**The full local install path (`curl | sudo bash` → wizard → running
US/UPS/AI-PIE stack → UCA login → spec generation) was verified working
end-to-end** on 2026-08-01, after fixing 11 real installer/app bugs (dead
`set -e` traps, missing compose file placement, unpublished ports across
US/UPS/AI-PIE, wrong `ADMIN_LISTEN_ADDR` bind, UCA's bundled dev certs
silently beating a real `client.env`, and more). Full detail:
`logs/2026-08-01-full-local-deployment-feasibility-test.md`.

**Known port assignments** (none of these were published to the host before
2026-08-01's fixes): US → 3000 (OIDC/GitHub HTTP), 8444 (UAC admin pairing),
50052 (gRPC, mTLS); UPS → 8443 (UAC admin pairing), 50051 (gRPC business
API, mTLS); AI-PIE → 8000 (UCA's "Ask" calls — confusingly configured via
UCA's `UPS_BASE_URL`, not a UPS-specific setting).

**Still-open gaps for a genuinely clean customer install** (see the log file
above for full detail): no container registry hosts `unotusk/us`,
`unotusk/ups`, or `unotusk/ai-pie` anywhere — every real customer hits
`pull access denied` today; no self-service project/license registration
API exists in UP (`/api/projects` is read-only, ops does inserts by hand);
no real UCA client-cert distribution mechanism per customer (since built); GitHub OAuth
login had an org-membership gap (since fixed);
AI-PIE's spec generation can return a schema-invalid response ("missing
kpi") on legitimate queries, not yet root-caused.

## 7. What not to do

- Don't add Redis, JWT issuance, or personal-OAuth-provider apps to `US` without
  checking §3 first — these were each evaluated and are either unimplemented by
  design (Redis: Postgres+sweeper already covers TTL/session state) or would
  contradict AMEND-008.
- Don't commit certificate/key material. `US`'s `main` branch (upstream, not
  `MVP_build`) has a known instance of this in its history (commit `7a7e144`) —
  treat those certs as compromised if that branch is ever used as a base; don't
  repeat the mistake.
