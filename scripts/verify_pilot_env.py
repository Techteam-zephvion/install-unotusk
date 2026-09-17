#!/usr/bin/env python3
"""
scripts/verify_pilot_env.py

Pilot Environment Verification & Pre-flight Diagnostics Tool for Unotusk MVP.
Audits:
1. Host system prerequisites (CPU, RAM, Disk, OS).
2. Container runtime (Docker daemon connectivity, Docker Compose v2).
3. Port binding safety & collision checks (8000, 5432, 6379).
4. Release artifacts integrity (tarballs and SHA-256 checksums in dist/).
5. Server configuration & secret hygiene (.env mode 0600, non-default secrets).
6. Live server health probes (/health and /health/ready) if running.

Usage:
    python scripts/verify_pilot_env.py [--server-url http://localhost:8000]
"""

import argparse
import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import urllib.error
import urllib.request


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_step(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}[STEP]{Colors.END} {title}")


def print_pass(msg: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.END} {msg}")


def print_warn(msg: str):
    print(f"  {Colors.YELLOW}⚠ WARN:{Colors.END} {msg}")


def print_fail(msg: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.END} {msg}")


def check_host_resources() -> bool:
    print_step("Checking Host System & Hardware Resources")
    success = True

    # Python Version
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        print_pass(f"Python runtime: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    else:
        print_fail(f"Python 3.10+ required, found {py_ver.major}.{py_ver.minor}")
        success = False

    # Disk Space (Root / Current Dir)
    try:
        total, used, free = shutil.disk_usage(".")
        free_gb = free // (2**30)
        if free_gb >= 10:
            print_pass(f"Available disk space: {free_gb} GB (minimum 10 GB required)")
        elif free_gb >= 5:
            print_warn(f"Available disk space is low: {free_gb} GB (recommend >= 20 GB for pilot)")
        else:
            print_fail(f"Insufficient disk space: {free_gb} GB free")
            success = False
    except Exception as e:
        print_warn(f"Could not inspect disk usage: {e}")

    # Memory Check (Linux /proc/meminfo)
    if os.path.exists("/proc/meminfo"):
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_kb = int(line.split()[1])
                        mem_gb = mem_kb / (1024 * 1024)
                        if mem_gb >= 3.5:
                            print_pass(f"Total system memory: {mem_gb:.1f} GB (minimum 4 GB)")
                        else:
                            print_warn(f"System memory is below 4 GB ({mem_gb:.1f} GB). Workloads may be constrained.")
                        break
        except Exception:
            pass

    return success


def check_docker_prerequisites() -> bool:
    print_step("Checking Docker Engine & Compose Availability")
    success = True

    # Docker CLI & Daemon
    docker_path = shutil.which("docker")
    if not docker_path:
        print_fail("Docker executable not found in PATH.")
        return False

    try:
        res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            print_pass("Docker Engine is installed and daemon is responding.")
        else:
            print_fail("Docker daemon is not running or accessible without root.")
            success = False
    except Exception as e:
        print_fail(f"Failed to communicate with Docker: {e}")
        success = False

    # Docker Compose v2
    try:
        res = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            ver = res.stdout.strip()
            print_pass(f"Docker Compose plugin detected: {ver}")
        else:
            print_fail("Docker Compose v2 (`docker compose`) not available.")
            success = False
    except Exception as e:
        print_fail(f"Failed to execute docker compose: {e}")
        success = False

    return success


def check_port_availability() -> bool:
    print_step("Checking Port Collision & Binding Safety")
    ports = [
        (8000, "API Gateway / HTTP"),
        (5432, "PostgreSQL (Internal)"),
        (6379, "Redis Cache (Internal)"),
    ]
    all_free = True

    for port, desc in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        res = s.connect_ex(("127.0.0.1", port))
        s.close()
        if res == 0:
            print_warn(f"Port {port} ({desc}) is currently in use. (Normal if server is already running).")
        else:
            print_pass(f"Port {port} ({desc}) is free and available for binding.")

    return all_free


def check_release_artifacts() -> bool:
    print_step("Auditing Distribution Artifacts in dist/")
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "dist")
    dist_dir = os.path.abspath(dist_dir)

    if not os.path.isdir(dist_dir):
        print_fail(f"dist/ directory does not exist at {dist_dir}")
        return False

    client_tar = os.path.join(dist_dir, "unotusk-client-linux-x64-v0.1.0.tar.gz")
    setup_tar = os.path.join(dist_dir, "unotusk-server-setup-linux-x64-v0.1.0.tar.gz")
    checksums_file = os.path.join(dist_dir, "checksums.txt")

    success = True
    for path, name in [(client_tar, "Employee Client Bundle"), (setup_tar, "Server Setup App Bundle")]:
        if os.path.isfile(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print_pass(f"{name} found ({size_mb:.1f} MB): {os.path.basename(path)}")
        else:
            print_fail(f"{name} missing: {path}")
            success = False

    if os.path.isfile(checksums_file):
        print_pass("Checksum file found: dist/checksums.txt")
        # Verify checksums
        try:
            with open(checksums_file) as f:
                lines = f.readlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    expected_hash, fname = parts[0], parts[1]
                    fpath = os.path.join(dist_dir, fname)
                    if os.path.isfile(fpath):
                        hasher = hashlib.sha256()
                        with open(fpath, "rb") as af:
                            while chunk := af.read(65536):
                                hasher.update(chunk)
                        calc_hash = hasher.hexdigest()
                        if calc_hash == expected_hash:
                            print_pass(f"Checksum verified for {fname}")
                        else:
                            print_fail(f"Checksum mismatch for {fname}")
                            success = False
        except Exception as e:
            print_warn(f"Could not verify checksums: {e}")
    else:
        print_warn("No checksums.txt in dist/ to verify integrity.")

    return success


def check_env_security() -> bool:
    print_step("Auditing Environment Configuration & Secrets")
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_file = os.path.join(root_dir, ".env")

    if not os.path.isfile(env_file):
        print_warn("No root .env file found. (.env.example is present for deployment).")
        return True

    # Check file mode
    mode = stat.S_IMODE(os.stat(env_file).st_mode)
    if mode == 0o600:
        print_pass(f".env permissions are restrictive ({oct(mode)})")
    else:
        print_warn(f".env permissions are {oct(mode)} (recommend chmod 0600 .env for pilot)")

    # Read and inspect secrets
    try:
        with open(env_file) as f:
            content = f.read()

        if "insecure-dev-secret" in content:
            print_warn("AUTH_SECRET uses development placeholder. Generate secure secret for production pilot.")
        else:
            print_pass("AUTH_SECRET is non-default.")

        if "POSTGRES_PASSWORD=postgres" in content:
            print_warn("POSTGRES_PASSWORD is set to default 'postgres'. Change for external pilot.")
        else:
            print_pass("POSTGRES_PASSWORD is customized.")
    except Exception as e:
        print_warn(f"Could not inspect .env contents: {e}")

    return True


def check_live_server(server_url: str) -> bool:
    print_step(f"Probing Live Server Health at {server_url}")
    # 1. Liveness /health
    try:
        req = urllib.request.Request(f"{server_url}/health", headers={"User-Agent": "Unotusk-Pilot-Verifier"})
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode())
                print_pass(f"/health probe OK: version={data.get('version')}, env={data.get('environment')}")
            else:
                print_fail(f"/health returned HTTP {res.status}")
                return False
    except urllib.error.URLError as e:
        print_warn(f"Live server not responding at {server_url}/health ({e}). (Server may not be started yet).")
        return False
    except Exception as e:
        print_warn(f"Server check encountered error: {e}")
        return False

    # 2. Readiness /health/ready
    try:
        req = urllib.request.Request(f"{server_url}/health/ready", headers={"User-Agent": "Unotusk-Pilot-Verifier"})
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode())
                status = data.get("status")
                db = data.get("database")
                redis = data.get("redis")
                if status == "ready":
                    print_pass(f"/health/ready probe OK: database={db}, redis={redis}")
                    return True
                else:
                    print_warn(f"/health/ready degraded: database={db}, redis={redis}")
                    return False
    except Exception as e:
        print_warn(f"/health/ready probe error: {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description="Unotusk MVP Pilot Environment Verification")
    parser.add_argument("--server-url", default=os.environ.get("UNOTUSK_SERVER_URL", "http://localhost:8000"), help="Unotusk server URL to probe")
    args = parser.parse_args()

    print("==================================================================")
    print(f"{Colors.BOLD}UNOTUSK MVP — PILOT ENVIRONMENT VERIFICATION & PRE-FLIGHT{Colors.END}")
    print("==================================================================")

    res_host = check_host_resources()
    res_docker = check_docker_prerequisites()
    res_ports = check_port_availability()
    res_dist = check_release_artifacts()
    res_env = check_env_security()
    res_server = check_live_server(args.server_url)

    print("\n==================================================================")
    print(f"{Colors.BOLD}PILOT PRE-FLIGHT SUMMARY:{Colors.END}")
    print(f"  - Host System Resources:       {'PASS' if res_host else 'FAIL'}")
    print(f"  - Docker & Compose Runtime:    {'PASS' if res_docker else 'FAIL'}")
    print(f"  - Network & Port Availability: {'PASS' if res_ports else 'PASS (WITH WARNINGS)'}")
    print(f"  - Release Artifacts & Hashes:  {'PASS' if res_dist else 'FAIL'}")
    print(f"  - Configuration & Security:    {'PASS' if res_env else 'WARN'}")
    print(f"  - Live Server Probes:          {'ONLINE' if res_server else 'STANDBY / OFFLINE'}")
    print("==================================================================")

    if res_host and res_docker and res_dist:
        print(f"\n{Colors.GREEN}{Colors.BOLD}ENVIRONMENT READINESS: READY FOR PILOT CUSTOMER DEPLOYMENT{Colors.END}\n")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}ENVIRONMENT READINESS: BLOCKED — RESOLVE FAILED CHECKS ABOVE{Colors.END}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
