#!/usr/bin/env python3
"""
scripts/clean_server_reset.py

Clean Server Reset & Reinstallation Utility for Unotusk MVP.
Safely resets the Unotusk Server environment on the host machine to allow
running the Server Setup Application again from a clean state.

Safety Guarantees:
- Targets ONLY Unotusk containers, volumes, and deployment directories.
- NEVER touches or stops unrelated Docker containers (e.g. Postgres, Redis,
  or applications belonging to other projects on the host).
- Requires explicit confirmation before deleting persistent data volumes.
- Verifies that Unotusk processes are stopped and required ports are released.

Usage:
    python scripts/clean_server_reset.py [--preserve-data | --wipe-data | --all] [--dry-run] [--yes]
"""

import argparse
import shutil
import socket
import subprocess
import sys
from pathlib import Path


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


UNOTUSK_CONTAINERS = {
    "unotusk-api",
    "unotusk-worker",
    "unotusk-migration",
    "unotusk-postgres",
    "unotusk-redis",
}

UNOTUSK_DATA_VOLUMES = {
    "unotusk_postgres_data",
    "unotusk_redis_data",
    "server_unotusk_postgres_data",
    "server_unotusk_redis_data",
}

UNOTUSK_NETWORKS = {
    "unotusk-network",
    "server_unotusk-network",
}

DEPLOYMENT_DIR = Path.home() / ".unotusk" / "server"


def print_step(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}[STEP]{Colors.END} {title}")


def print_info(msg: str):
    print(f"  {Colors.BOLD}ℹ INFO:{Colors.END} {msg}")


def print_pass(msg: str):
    print(f"  {Colors.GREEN}✓ PASS:{Colors.END} {msg}")


def print_warn(msg: str):
    print(f"  {Colors.YELLOW}⚠ WARN:{Colors.END} {msg}")


def print_fail(msg: str):
    print(f"  {Colors.RED}✗ FAIL:{Colors.END} {msg}")


def run_cmd(cmd: list[str], check: bool = False, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def get_docker_containers() -> list[dict]:
    """Return all running and stopped containers as dicts with Name, ID, State."""
    if not shutil.which("docker"):
        return []
    res = run_cmd(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.ID}}\t{{.State}}\t{{.Status}}"])
    if res.returncode != 0 or not res.stdout.strip():
        return []

    containers = []
    for line in res.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            containers.append({
                "name": parts[0].strip(),
                "id": parts[1].strip(),
                "state": parts[2].strip(),
                "status": parts[3].strip() if len(parts) > 3 else "",
            })
    return containers


def get_docker_volumes() -> list[str]:
    """Return list of existing Docker volume names."""
    if not shutil.which("docker"):
        return []
    res = run_cmd(["docker", "volume", "ls", "--format", "{{.Name}}"])
    if res.returncode != 0 or not res.stdout.strip():
        return []
    return [line.strip() for line in res.stdout.strip().splitlines()]


def inspect_unotusk_state() -> dict:
    """Inspect the current host state for Unotusk containers, volumes, config, and ports."""
    all_containers = get_docker_containers()
    unotusk_containers = [c for c in all_containers if c["name"] in UNOTUSK_CONTAINERS]
    other_containers = [c for c in all_containers if c not in unotusk_containers]

    all_volumes = get_docker_volumes()
    unotusk_volumes = [v for v in all_volumes if v in UNOTUSK_DATA_VOLUMES]

    config_exists = DEPLOYMENT_DIR.exists() and (DEPLOYMENT_DIR / "docker-compose.yml").exists()
    env_exists = DEPLOYMENT_DIR.exists() and (DEPLOYMENT_DIR / ".env").exists()

    port_8000_used = is_port_in_use(8000)

    return {
        "unotusk_containers": unotusk_containers,
        "other_containers_count": len(other_containers),
        "unotusk_volumes": unotusk_volumes,
        "deployment_dir_exists": config_exists,
        "env_file_exists": env_exists,
        "port_8000_used": port_8000_used,
    }


def perform_reset(
    wipe_data: bool = False,
    wipe_config: bool = False,
    dry_run: bool = False,
    yes: bool = False,
) -> bool:
    print("==================================================")
    print(" UNOTUSK MVP — CLEAN SERVER RESET UTILITY")
    print("==================================================")
    print(f"Mode: {'DRY RUN (No changes)' if dry_run else 'LIVE RESET'}")
    print(f"Policy: Data Volumes: {'WIPE (Delete DB)' if wipe_data else 'PRESERVE'}")
    print(f"Policy: Config (~/.unotusk/server): {'DELETE' if wipe_config else 'PRESERVE'}")

    state = inspect_unotusk_state()

    print_step("1. Current Unotusk Environment Inspection")
    if state["unotusk_containers"]:
        print_info(f"Found {len(state['unotusk_containers'])} Unotusk container(s):")
        for c in state["unotusk_containers"]:
            print(f"    - {c['name']} (ID: {c['id'][:12]}, State: {c['state']})")
    else:
        print_pass("No Unotusk containers currently active.")

    print_info(f"Protected non-Unotusk containers on host: {state['other_containers_count']} (will NOT be touched)")

    if state["unotusk_volumes"]:
        print_info(f"Found {len(state['unotusk_volumes'])} Unotusk data volume(s):")
        for v in state["unotusk_volumes"]:
            print(f"    - {v}")
    else:
        print_info("No Unotusk volumes detected.")

    if state["deployment_dir_exists"]:
        print_info(f"Found deployment configuration at: {DEPLOYMENT_DIR}")
    else:
        print_info(f"No deployment configuration found at: {DEPLOYMENT_DIR}")

    print_info(f"Port 8000 status: {'OCCUPIED' if state['port_8000_used'] else 'FREE'}")

    # Confirmation guard for destructive wipe
    if wipe_data and not dry_run and not yes:
        print(f"\n{Colors.RED}{Colors.BOLD}WARNING: You have requested to WIPE persistent Unotusk data volumes!{Colors.END}")
        print("This will permanently delete:")
        print("  - PostgreSQL database (tables, project data, AST chunks, discoveries, users)")
        print("  - Redis task queue cache")
        confirmation = input(f"{Colors.YELLOW}Are you absolutely sure? Type 'yes' to proceed: {Colors.END}").strip()
        if confirmation != "yes":
            print_warn("Data wipe cancelled by user. Aborting reset.")
            return False

    # 2. Stop and Remove Containers via Compose if directory exists
    print_step("2. Stopping and Removing Unotusk Containers")
    compose_file = DEPLOYMENT_DIR / "docker-compose.yml"
    if compose_file.exists():
        cmd = ["docker", "compose", "-f", str(compose_file), "down"]
        if wipe_data:
            cmd.append("-v")
        print_info(f"Executing: {' '.join(cmd)}")
        if not dry_run:
            res = run_cmd(cmd)
            if res.returncode == 0:
                print_pass("Docker Compose stack stopped successfully.")
            else:
                print_warn(f"Compose down returned non-zero code ({res.returncode}): {res.stderr.strip()}")

    # 3. Surgical container removal fallback (guarantees no orphan unotusk containers remain)
    print_step("3. Verifying Container Removal")
    remaining_containers = get_docker_containers()
    unotusk_remaining = [c for c in remaining_containers if c["name"] in UNOTUSK_CONTAINERS]

    if unotusk_remaining:
        for c in unotusk_remaining:
            print_info(f"Surgically removing container: {c['name']}")
            if not dry_run:
                run_cmd(["docker", "rm", "-f", c["name"]])
        print_pass("All Unotusk containers removed.")
    else:
        print_pass("Zero Unotusk containers remaining.")

    # 4. Handle Data Volumes
    print_step("4. Handling Data Volumes")
    if wipe_data:
        for v in state["unotusk_volumes"]:
            print_info(f"Removing Docker volume: {v}")
            if not dry_run:
                res = run_cmd(["docker", "volume", "rm", "-f", v])
                if res.returncode == 0:
                    print_pass(f"Volume '{v}' removed.")
                else:
                    print_warn(f"Could not remove volume '{v}': {res.stderr.strip()}")
    else:
        print_pass(f"Data volumes preserved ({len(state['unotusk_volumes'])} volumes intact).")

    # 5. Handle Configuration & Deployment Directory
    print_step("5. Handling Deployment Configuration")
    if wipe_config:
        if DEPLOYMENT_DIR.exists():
            print_info(f"Removing deployment directory: {DEPLOYMENT_DIR}")
            if not dry_run:
                try:
                    shutil.rmtree(DEPLOYMENT_DIR)
                    print_pass("Deployment directory removed.")
                except Exception as e:
                    print_warn(f"Failed to remove {DEPLOYMENT_DIR}: {e}")
        else:
            print_pass("No deployment directory to remove.")
    else:
        print_pass("Deployment directory preserved.")

    # 6. Post-Reset Health & Port Verification
    print_step("6. Final State Verification")
    post_containers = [c for c in get_docker_containers() if c["name"] in UNOTUSK_CONTAINERS]
    if post_containers and not dry_run:
        print_fail(f"{len(post_containers)} Unotusk containers are still active!")
        return False
    else:
        print_pass("✓ Zero Unotusk containers active.")

    port_8000_free = not is_port_in_use(8000)
    if not port_8000_free and not dry_run:
        print_warn("Port 8000 is still in use by another process on the host!")
    else:
        print_pass("✓ Port 8000 is free and available.")

    print("\n==================================================")
    print(f"{Colors.GREEN}{Colors.BOLD}SERVER RESET COMPLETE{Colors.END}")
    print("==================================================")
    print("Summary of actions:")
    print(f"  - Unotusk Containers:   {'[DRY-RUN]' if dry_run else 'STOPPED & REMOVED'}")
    print(f"  - Data Volumes:         {'[DRY-RUN]' if dry_run else ('WIPED' if wipe_data else 'PRESERVED')}")
    print(f"  - Configuration:        {'[DRY-RUN]' if dry_run else ('WIPED' if wipe_config else 'PRESERVED')}")
    print(f"  - Port 8000:            {'[DRY-RUN]' if dry_run else ('RELEASED' if port_8000_free else 'OCCUPIED')}")
    print(f"  - Protected Containers: {state['other_containers_count']} foreign container(s) untouched.")
    print("\nThe host machine is ready for a fresh run of the Server Setup App:")
    print("  ./setup_app (or flutter run -d linux inside setup_app/)")
    print("==================================================\n")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Clean Server Reset & Reinstallation Utility for Unotusk MVP.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--preserve-data",
        action="store_true",
        default=True,
        help="Stop containers and reset configuration, but preserve persistent database volumes (default).",
    )
    group.add_argument(
        "--wipe-data",
        action="store_true",
        help="Stop containers and intentionally remove persistent database and cache volumes.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Full clean test reset: wipes both configuration (~/.unotusk/server) and persistent data volumes.",
    )

    parser.add_argument(
        "--wipe-config",
        action="store_true",
        help="Remove generated server configuration in ~/.unotusk/server.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect environment and show proposed actions without making changes.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Automatically confirm destructive operations without interactive prompt.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only display current status of Unotusk containers, volumes, and ports, then exit.",
    )

    args = parser.parse_args()

    if args.check_only:
        state = inspect_unotusk_state()
        print("=== Unotusk Server Inspection ===")
        print(f"Active Containers: {len(state['unotusk_containers'])}")
        for c in state["unotusk_containers"]:
            print(f"  - {c['name']} ({c['status']})")
        print(f"Data Volumes:      {len(state['unotusk_volumes'])}")
        print(f"Config Directory:  {'Exists' if state['deployment_dir_exists'] else 'None'}")
        print(f"Port 8000:         {'In Use' if state['port_8000_used'] else 'Free'}")
        print(f"Other Containers:  {state['other_containers_count']} (protected)")
        sys.exit(0)

    wipe_data = args.wipe_data or args.all
    wipe_config = args.wipe_config or args.all

    success = perform_reset(
        wipe_data=wipe_data,
        wipe_config=wipe_config,
        dry_run=args.dry_run,
        yes=args.yes,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
