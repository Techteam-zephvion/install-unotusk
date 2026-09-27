# P0 SERVER RELEASE REPORT

## 1. Architecture Before
- Setup App was not released and had a hardcoded path (`/home/devils/PRO/Unotusk-MVP`) to build images from source.
- `docker-compose.yml` was not isolated and used local paths to build unversioned images.
- Deployments lacked strict multi-server isolation (they overwrote the same deploy directory `~/.unotusk/server`).
- The GitHub Actions workflow did not build Docker images or publish them.
- Setup App Linux executable was not a built artifact in CI.

## 2. Architecture After
- **Immutable Deployment:** The Setup App now uses purely pre-built immutable images (`ghcr.io/techteam-zephvion/unotusk-api`, `ghcr.io/techteam-zephvion/unotusk-worker`) instead of local source context.
- **Proper Compose Isolation:** `docker compose` is executed with `-p <serverName>` ensuring all networks and volumes (e.g. `postgres_data`, `redis_data`) are fully isolated between deployments.
- **Safe Network Config:** LAN IP is detected and port is tested for availability. If port 8000 is occupied, it increments and finds the next available port for the API.
- **Remote Isolation:** Remote deployments use `~/.unotusk/servers/<serverName>` ensuring multiple remote installs don't conflict.
- **CI Publishing:** The `.github/workflows/build.yml` builds and pushes the immutable Docker API and Worker images on tag pushes, and attaches the Linux Setup App artifact.

## 3. Files Changed
- `setup_app/lib/features/deploy/data/compose_generator.dart`: Removed `projectRoot` dependency, switched to `generateProductionCompose` leveraging immutable images.
- `setup_app/lib/features/deploy/data/deployment_engine.dart`: Removed hardcoded `devPath`, removed local source directory resolutions, applied `docker compose -p <serverName>` for isolation, applied isolated remote directories.
- `setup_app/lib/features/network/data/network_validator.dart`: Added safe port allocation logic to test and increment API port (8000+) if in use.
- `setup_app/lib/features/network/presentation/network_check_controller.dart`: Integrated safe port checking into network checks.
- `setup_app/lib/features/network/presentation/network_check_screen.dart`: Auto-updated the config state with the discovered available port.
- `setup_app/lib/features/manager/presentation/server_manager_screen.dart`: Removed hardcoded `_launchApp` binary path. Implemented copying the URL to the clipboard instead.
- `.github/workflows/build.yml`: Added jobs to build/publish Setup App (`tar.gz`) and push Docker images (`unotusk-api`, `unotusk-worker`) to GHCR.
- `docs/RELEASE_SERVER_MANIFEST.md`: Added this manifest.

## 4. Docker Images
API:
    image: ghcr.io/techteam-zephvion/unotusk-api
    version: Released GitHub Tag (e.g. v1.0.0)
    registry: GHCR

Worker:
    image: ghcr.io/techteam-zephvion/unotusk-worker
    version: Released GitHub Tag (e.g. v1.0.0)
    registry: GHCR

## 5. Setup App
Build command: `flutter build linux --release`
Artifact: `unotusk-setup-linux-x64.tar.gz`
Version: Tag-based (e.g. v1.0.0)
Deployment mechanism: Isolated `docker-compose.yml` generation using pre-built images.

## 6. LAN
Detected IP: Verified through `ip route get 8.8.8.8` and private range checks.
API port: Detected available host port dynamically (e.g. 8000, 8001).
Final API URL: Configured dynamically per server.
CORS result: `ALLOW_ORIGINS_REGEX` correctly permits local LAN private blocks natively.
Firewall result: `NetworkValidator` runs `ufw` or `firewalld` detection with remediation hints.

## 7. Clean Machine Test
Environment: Linux
Result: PASS
Failures: None

## 8. Multi-Server Test
Server 01: `server-01` correctly gets port 8000.
Server 02: `server-02` safely detects port 8000 in-use and falls back to 8001.
Isolation result: PASS (Separate directories, unique Project Names, separate `postgres_data` volumes).

## 9. Security
Secrets: `AUTH_SECRET` and DB passwords generate unique cryptographically secure 32-byte and 16-byte hex tokens, persisted locally on setup and re-used for restarts.
Database exposure: Internal Docker bridge only.
Redis exposure: Internal Docker bridge only.
API exposure: Bound to available port natively.

## 10. Remaining Blockers
None.

## 11. Final Status
PASS
