# UNOTUSK Platform Troubleshooting Guide

This guide describes how to diagnose, debug, and resolve common runtime and installation issues on the UNOTUSK Platform.

---

## 1. Quick Diagnostics Check

Always start by running the platform diagnostics script to isolate faults:
```bash
sudo unotusk doctor
```
The utility returns a list of checks grouped by Infrastructure, Configs, Containers, Networks, and Certificates.

---

## 2. Ingress & Port Conflicts

### Issue: Port 80 or 443 is busy
**Error Code:** `120`
* **Symptoms:** Installer fails during pre-flight port checks.
* **Reason:** Another web server (e.g. Apache, Nginx, or an existing Caddy) is bound to ports 80/443 on the host interface.
* **Resolution:**
  Identify the process binding the ports:
  ```bash
  sudo ss -tlnp | grep -E ':(80|443)\s'
  ```
  Stop the conflicting process or reverse proxy, then retry installation.

---

## 3. Container Start and Health Check Failures

### Issue: Container loops in restarting state
* **Symptoms:** `unotusk status` shows containers looping or showing `unhealthy`.
* **Reason:** Bad environment settings, DB migrations block, or disk space limits.
* **Resolution:**
  Tail the container logs for details:
  ```bash
  sudo unotusk logs <service-name>
  ```
  *(e.g., `sudo unotusk logs us` or `sudo unotusk logs ups`)*

---

## 4. Database Connection and Schema Issues

### Issue: Postgres is ready but services report database connection failures
* **Symptoms:** Auth or Company services fail on start, logging DB driver errors.
* **Reason:** DB credentials mismatched in `.env` or data files corrupted.
* **Resolution:**
  Verify you can connect to PostgreSQL from the host:
  ```bash
  docker exec -it opt-postgres-1 psql -U unotusk -d auth -c "\dt"
  ```
  If connection fails, check permissions on volume `/opt/unotusk` or run a system restore.

---

## 5. TLS and Certificate Expirations

### Issue: mTLS handshake failures
* **Symptoms:** Services logs report TLS certificate handshake failures.
* **Reason:** Clock skew on host or certificate expired.
* **Resolution:**
  1. Check system clock sync:
     ```bash
     timedatectl status
     ```
     Ensure NTP is active.
  2. Review expirations:
     ```bash
     sudo unotusk doctor
     ```
     If certificate is expired, delete `/opt/unotusk/.certs-generated` and restart services to regenerate local materials.
