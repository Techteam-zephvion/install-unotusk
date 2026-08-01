# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0-rc1] — 2026-07-29
### Added
- **Fingerprint mismatch hard-block enforcement** (UNOTUSK_LICENSE_DEGRADED_MODE §3)
- `hard_blocked` state in license status API
- `project_fingerprint` field in ValidateLicense protocol
- `/etc/machine-id` based fingerprint in UPS heartbeat
- `block_reason` in ValidateLicense response
- M5 integration test suite (`scripts/test-integration.sh`)
- M5 failure test suite (`scripts/test-failure.sh`)
- Security validation script (`scripts/test-security.sh`)
- Installation Guide (`docs/Install_Guide.md`)
- Administrator Guide (`docs/Admin_Guide.md`)
- Troubleshooting Guide (`docs/Troubleshooting.md`)
- GHCR Docker image publishing workflow
- Manual Release Checklist (`docs/Release_Checklist.md`)

### Fixed
- JWT key backup gap — `us_data` volume now explicitly snapshotted in `unotusk backup`; restore includes volume restoration.
- Platform-facing `ValidateLicense` now rejects fingerprint mismatches with immediate hard block.
- Bootstrap version stamp now writes `0.2.0-rc1` (was `1.0.0` placeholder).
- `unotusk doctor` now checks UPS health via internal docker network (not just host-exposed port).
- `unotusk update` rollback now correctly reads rollback manifest before re-running docker compose.

### Changed
- `ValidateLicenseRequest` proto extended with `project_fingerprint` field (backward-compatible, empty string = fingerprint not registered = no mismatch check).
- `ValidateLicenseResponse` proto extended with `block_reason` enum and `hard_blocked` bool.
- `/license/status` response now includes `hard_blocked` field.

### Known Limitations
- UP Platform `AuthLayer` still requires reachable `AUTH_GRPC_ENDPOINT` for all RPCs except `ValidateLicense` (Platform admin RPCs return UNAVAILABLE until Platform gets internal auth — see README §Technical Debt).
- Fingerprint registration is currently a manual ops step (no automated registration UI).
- ARM64/Apple Silicon installer untested.
- mTLS private keys must be host-chmod'd to 644 (see Troubleshooting).
- Platform dummy certs used for UPS→Platform mTLS until real certs provisioned at onboarding.

## [0.1.0-beta] — 2026-07-29
### Added
- US Auth Service (Rust/axum+tonic, OIDC federation, mTLS sessions)
- UPS Company Server (Rust, license heartbeat, Degraded Mode state machine, ClientService gRPC)
- AI-PIE Intelligence Engine (Python/FastAPI, repository ingestion, knowledge graph, Qdrant embeddings, spec+report generation)
- UP Platform (Rust, Render+Neon, project directory, JWKS push)
- Docker Compose stack with health-aware startup ordering
- `install.sh` installer with interactive wizard
- `unotusk` CLI (start/stop/restart/status/logs/update/backup/restore/doctor/reconfigure/rollback/uninstall)
- mTLS between all services with auto-generated local CA
- Degraded Mode (connectivity-loss grace period: 5 hours → degraded read-only)
- Operations Manual
