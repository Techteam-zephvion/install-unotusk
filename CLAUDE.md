# CLAUDE.md — Unotusk MVP (demo track)

## 0. What this is

A **separate, simplified MVP** built to demo to a client/investor. It is not
the V1 product — the full architecture (US/UPS/AI-PIE/UP/UCA/UAC, OIDC
federation, licensing, degraded mode, mTLS mesh) lives at
`~/PRO/Unotusk-2` and stays there as the headstart for V1. This repo
deliberately throws away that complexity to get a working demo fast.

**Process: waterfall.** Each phase below should be finished and confirmed
working before moving to the next — no parallel half-finished phases.

## 1. Stack

- **Frontend**: Flutter (`app/`) — single codebase, role-based routing
  (employee view vs. admin view), not two separate apps.
- **Auth**: a small Node.js/Express service (`auth-service/`) — email+password,
  bcrypt hashing, JWT (HS256), Postgres. No OIDC, no mTLS, no federation. Issues
  tokens matching AI-PIE's built-in `mvp_jwt` auth path exactly (claims `sub`,
  `role`) — see `~/PRO/Unotusk-2/AI-PIE/src/aipie/api/auth/identity.py`.
- **Intelligence engine**: reuses `~/PRO/Unotusk-2/AI-PIE` as-is. The MVP
  auth service issues its own JWTs; if AI-PIE's endpoints currently expect
  UPS-issued tokens or UPS/licensing calls, those call sites need to be
  identified and stubbed/bypassed for standalone use — not yet done, see
  Open Items.

## 2. Explicitly out of scope for MVP

- No licensing / entitlement checks.
- No degraded mode.
- No mTLS or certificate provisioning.
- No OIDC/enterprise IdP federation — plain email+password only.
- No multi-tenant customer-hosted deployment model — single instance is fine.

Do not port these in from `Unotusk-2` "for consistency." If the demo later
needs one of these, treat it as a new decision, not a default.

## 3. Layout

```
Unotusk-MVP/
├── app/            Flutter app (employee + admin views)
└── auth-service/   Express auth service (JWT, Postgres)
    └── src/
        ├── index.ts              Express bootstrap
        ├── routes/auth.ts        /auth/signup, /auth/login, /auth/me, /auth/admin/users
        ├── middleware/           requireAuth, requireAdmin
        ├── lib/                  password hashing + JWT issue/verify
        └── db/                   Postgres pool + schema/migration
```

## 4. Running locally

```bash
# auth service
cd auth-service
docker compose up -d      # Postgres
cp .env.example .env      # set JWT_SECRET to match AI-PIE's MVP_JWT_SECRET
npm install
npm run dev                # http://localhost:8080

# flutter app
cd app
flutter pub get
flutter run
```

Default JWT secret is a dev placeholder (`.env.example`) — fine for a demo,
not for anything beyond it. It must match AI-PIE's `MVP_JWT_SECRET` exactly
for `AUTH_MODE=mvp_jwt` to work — see `~/PRO/Unotusk-2/AI-PIE/.env.example`.

## 5. Open items

- AI-PIE integration: not yet wired. Need to check AI-PIE's auth
  expectations (does it validate UPS-issued tokens specifically, or accept
  any bearer JWT?) and adjust either AI-PIE's verification or this
  service's token format to match.
- Admin views in Flutter: routing scaffolded via `role` claim in the JWT,
  actual admin screens not yet built.
- No CI, no deployment target chosen yet (Render/Railway/local for the
  demo — undecided).

## 6. Relationship to Unotusk-2

Treat `~/PRO/Unotusk-2` as read-only reference for now. If something built
here proves out and should graduate into V1 (e.g. a UI flow, a feature),
port the *idea*, not the shortcut auth — V1 keeps AMEND-008's OIDC
federation requirement.
