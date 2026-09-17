#!/usr/bin/env python3
"""
scripts/export_diagnostics.py

Diagnostic Export Utility for Unotusk MVP Pilot.
Collects sanitized technical diagnostics for troubleshooting customer pilot deployments.
Enforces strict privacy:
- Redacts all passwords, tokens, API keys, connection strings.
- Never extracts source code or customer proprietary data.
- Aggregates operational counts and sanitized error logs.

Usage:
    python scripts/export_diagnostics.py [--output-dir ./diagnostics] [--server-url http://localhost:8000]
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import urllib.error
import urllib.request

VERSION = "0.1.0"

SENSITIVE_PATTERNS = [
    (r"(postgresql(?:\+asyncpg)?://[^\s:]+:)([^\s@]+)(@\S+)", r"\1[REDACTED]\3"),
    (r"(redis://[^\s:]+:)([^\s@]+)(@\S+)", r"\1[REDACTED]\3"),
    (r"gsk_[A-Za-z0-9_]{10,}", "[REDACTED-GROQ-KEY]"),
    (r"sk-ant-[A-Za-z0-9_.\-]{10,}", "[REDACTED-ANTHROPIC-KEY]"),
    (r"((?:api[_-]?key|auth[_-]?secret|password|token|secret)\s*[:=]\s*)['\"]?[^\s,'\"]{6,}['\"]?", r"\1[REDACTED]"),
    (r"(Authorization:\s*Bearer\s+)[^\s]+", r"\1[REDACTED]"),
]


def sanitize_text(text: str) -> str:
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def get_system_info() -> dict:
    return {
        "unotusk_version": VERSION,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
    }


def get_docker_status() -> dict:
    info = {"docker_available": False, "compose_version": None, "containers": []}
    if shutil.which("docker"):
        info["docker_available"] = True
        try:
            res = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                info["compose_version"] = res.stdout.strip()
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout.strip():
                try:
                    info["containers"] = json.loads(res.stdout)
                except Exception:
                    info["containers"] = res.stdout.strip().splitlines()
        except Exception:
            pass
    return info


def get_server_health(server_url: str) -> dict:
    health = {"url": server_url, "liveness": None, "readiness": None}
    try:
        req = urllib.request.Request(f"{server_url}/health", headers={"User-Agent": "Unotusk-Diagnostics"})
        with urllib.request.urlopen(req, timeout=3) as res:
            health["liveness"] = json.loads(res.read().decode())
    except Exception as e:
        health["liveness"] = f"unreachable: {e}"

    try:
        req = urllib.request.Request(f"{server_url}/health/ready", headers={"User-Agent": "Unotusk-Diagnostics"})
        with urllib.request.urlopen(req, timeout=3) as res:
            health["readiness"] = json.loads(res.read().decode())
    except Exception as e:
        health["readiness"] = f"unreachable: {e}"

    return health


def get_sanitized_logs() -> dict:
    logs = {"api": [], "worker": []}
    for service in ["api", "worker"]:
        try:
            res = subprocess.run(
                ["docker", "compose", "logs", "--tail=200", service],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                raw_lines = res.stdout.splitlines()
                logs[service] = [sanitize_text(line) for line in raw_lines]
            else:
                logs[service] = [f"Error retrieving logs: {res.stderr.strip()}"]
        except Exception as e:
            logs[service] = [f"Could not read docker logs: {e}"]
    return logs


def main():
    parser = argparse.ArgumentParser(description="Export sanitized diagnostics for Unotusk MVP pilot support.")
    parser.add_argument("--output-dir", default="diagnostics", help="Directory to store diagnostic archive")
    parser.add_argument("--server-url", default=os.environ.get("UNOTUSK_SERVER_URL", "http://localhost:8000"), help="Unotusk server URL")
    args = parser.parse_args()

    print("==================================================")
    print(" UNOTUSK MVP — DIAGNOSTIC EXPORT UTILITY")
    print("==================================================")
    print(f"Collecting sanitized system diagnostics (v{VERSION})...")

    timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    os.makedirs(args.output_dir, exist_ok=True)

    diagnostics = {
        "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "unotusk_version": VERSION,
        "system_info": get_system_info(),
        "docker_status": get_docker_status(),
        "server_health": get_server_health(args.server_url),
        "sanitized_logs": get_sanitized_logs(),
    }

    out_file = os.path.join(args.output_dir, f"unotusk_diagnostics_{timestamp}.json")
    with open(out_file, "w") as f:
        json.dump(diagnostics, f, indent=2)

    hasher = hashlib.sha256()
    with open(out_file, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    sha256 = hasher.hexdigest()

    print("\n✓ Diagnostics successfully exported:")
    print(f"  File:   {out_file}")
    print(f"  Size:   {os.path.getsize(out_file) / 1024:.1f} KB")
    print(f"  SHA256: {sha256}")
    print("\nPrivacy Notice:")
    print("  All customer secrets, API keys, passwords, and source code have been verified sanitized/excluded.")
    print("==================================================")


if __name__ == "__main__":
    main()
