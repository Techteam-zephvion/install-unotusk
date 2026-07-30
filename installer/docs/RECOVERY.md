# UNOTUSK Platform Disaster Recovery Manual

This document details procedures for backup, restore, version rollbacks, and recovery operations for the UNOTUSK Platform.

---

## Backup Strategy

Backups contain all state components needed to rebuild the system from scratch:
- SQL schemas and data from PostgreSQL (`auth` and `company` databases).
- Local TLS certificates and keys.
- Environment configs (`.env`, `.env.wizard`, `.secrets`).
- Persistent named Docker volumes data (Postgres, Redis, Qdrant, Arize Phoenix, US, UPS, AI PIE).

### Manual Backups
Create a backup at any time by running:
```bash
sudo unotusk backup
```
The script generates a compressed file under `/opt/unotusk/backups/`:
`unotusk_backup_YYYYMMDD_HHMMSS.tar.gz`
Alongside, a `.sha256` file containing the checksum is created.

---

## Restore Procedures

### Automated Restore
Run the restore target by providing the backup file:
```bash
sudo unotusk restore /opt/unotusk/backups/unotusk_backup_20260730_100000.tar.gz
```
The restore utility:
1. Stops all container services.
2. Validates backup file checksum matches the `.sha256` definition.
3. Re-creates configs and certificate folders.
4. Restores raw database and caching volumes.
5. Boots postgres, imports the SQL schema dumps, and boots the rest of the services.

---

## Version Rollbacks

Upgrades automatically create a pre-upgrade backup under `/opt/unotusk/backups/` and a manifest file `/.unotusk-rollback.images`.

If an upgrade fails health checks, an automatic rollback is triggered:
- The system will restore the database to its pre-upgrade state.
- Container image tags are pinned back to the tags specified in the rollback manifest.

To trigger a rollback manually, run:
```bash
sudo unotusk rollback
```
---

## Disaster Recovery Verification Check

Following a restore or rollback, verify the health status:
```bash
sudo unotusk doctor
```
Ensure that the results indicate a healthy status across all containers and integrations.
