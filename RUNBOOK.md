# Unotusk MVP Runbook

This runbook covers the operational deployment and management of the Unotusk Single-Tenant MVP.

## 1. Quick Start

### Starting the Server
The entire backend stack is containerized using Docker Compose.

```bash
docker compose up -d
```
This will start:
- `unotusk-postgres` (Database)
- `unotusk-redis` (Message Broker)
- `unotusk-api` (FastAPI Backend, Port 8000)
- `unotusk-worker` (Background Job Processor)
- `unotusk-web` (Next.js Dashboard, Port 3000)

### Resetting Server Data
If you need to wipe the database and start fresh:
```bash
./scripts/clean_server_reset.sh --wipe-data
```

## 2. Client Deployment

### Building the Linux Client
Run the packaging script to generate the client distribution:
```bash
./scripts/package_release.sh
```
This will output a `unotusk-employee-linux-x64.tar.gz` to the `dist/` folder.

### Setup Website (Vercel)
The `install.unotusk.com` landing page is located in `apps/install-site/`. 
It's a static HTML page optimized for Vercel deployment. Connect the Vercel project to this repository and set the Root Directory to `apps/install-site`.

## 3. Operations & Diagnostics

### Exporting Diagnostics
To generate a sanitized support bundle for troubleshooting:
```bash
python3 scripts/export_diagnostics.py --server-url http://localhost:8000
```
This creates an archive in the `diagnostics/` folder.

For a detailed LAN Pilot operation guide, see [`docs/LAN_PILOT_RUNBOOK.md`](docs/LAN_PILOT_RUNBOOK.md).
