#!/usr/bin/env python3
"""
scripts/verify_lan_connectivity.py

LAN Connectivity Verification Probe & Preflight Check for Unotusk MVP.
Runs comprehensive diagnostics on the Linux server host prior to running multi-client pilot tests:
1. Detects primary RFC 1918 private LAN IP address.
2. Checks port 8000 binding (0.0.0.0:8000 vs 127.0.0.1:8000).
3. Tests HTTP GET /health and /health/ready on the LAN IP.
4. Simulates CORS preflight OPTIONS request from a remote LAN employee client.
5. Checks local firewall status (UFW / iptables) for port 8000 accessibility.
6. Displays actionable pass/fail diagnosis and employee connection URL.

Usage:
    python3 scripts/verify_lan_connectivity.py [--port 8000] [--ip <override_ip>]
"""

import argparse
import ipaddress
import json
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request

VIRTUAL_IFACE_PREFIXES = (
    "docker",
    "br-",
    "veth",
    "virbr",
    "lxcbr",
    "tailscale",
    "wg",
    "tun",
    "tap",
    "lo",
)


RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def is_rfc1918_private(ip_str: str) -> bool:
    """Check if an IPv4 address is strictly within RFC 1918 private ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.version != 4:
            return False
        return any(ip in net for net in RFC1918_NETWORKS)
    except ValueError:
        return False


def detect_primary_lan_ip() -> tuple[str | None, str | None]:
    """
    Detect primary active LAN IPv4 address and interface name.
    Returns (ip, iface_name) or (None, None).
    """
    # 1. Try socket routing probe (does not send packets outside, just queries kernel routing table)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            cand = s.getsockname()[0]
            if is_rfc1918_private(cand):
                return cand, "auto-route"
    except Exception:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.168.255.255", 1))
            cand = s.getsockname()[0]
            if is_rfc1918_private(cand):
                return cand, "auto-route"
    except Exception:
        pass

    # 2. Try parsing ip addr on Linux
    if shutil.which("ip"):
        try:
            res = subprocess.run(["ip", "-j", "addr"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                interfaces = json.loads(res.stdout)
                # Prioritize Wi-Fi and Ethernet
                for iface in sorted(interfaces, key=lambda x: 0 if any(x.get("ifname", "").startswith(p) for p in ("wl", "eth", "en")) else 1):
                    name = iface.get("ifname", "")
                    if any(name.startswith(p) for p in VIRTUAL_IFACE_PREFIXES):
                        continue
                    for addr in iface.get("addr_info", []):
                        if addr.get("family") == "inet":
                            cand_ip = addr.get("local", "")
                            if is_rfc1918_private(cand_ip):
                                return cand_ip, name
        except Exception:
            pass

    return None, None


def check_port_binding(port: int = 8000) -> dict:
    """Check if the port is bound and listening on 0.0.0.0 or 127.0.0.1."""
    status = {
        "listening": False,
        "bind_all": False,
        "details": "",
    }

    # Use ss or netstat if available
    if shutil.which("ss"):
        try:
            res = subprocess.run(["ss", "-tulpn"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if f":{port} " in line or f":{port}\t" in line:
                        status["listening"] = True
                        if "0.0.0.0" in line or "*:" in line or "[::]" in line:
                            status["bind_all"] = True
                            status["details"] = line.strip()
                            break
                        else:
                            status["details"] = line.strip()
        except Exception:
            pass

    if not status["listening"]:
        # Fallback to local connect check
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    status["listening"] = True
                    status["details"] = "Reachable on 127.0.0.1"
        except Exception:
            pass

    return status


def probe_http_endpoint(url: str, headers: dict | None = None, method: str = "GET") -> tuple[bool, int, str]:
    """Execute HTTP probe and return (success, status_code, response_body_or_error)."""
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "Unotusk-LAN-Probe"}, method=method)
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return (resp.status == 200, resp.status, body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else str(e)
        return (False, e.code, body)
    except Exception as e:
        return (False, 0, str(e))


def probe_cors_preflight(server_url: str, client_origin: str) -> tuple[bool, str]:
    """Verify CORS preflight OPTIONS request returns appropriate headers for LAN client."""
    headers = {
        "Origin": client_origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization,Content-Type,X-Request-ID",
        "User-Agent": "Unotusk-LAN-CORS-Probe",
    }
    try:
        req = urllib.request.Request(f"{server_url}/health", headers=headers, method="OPTIONS")
        with urllib.request.urlopen(req, timeout=3) as resp:
            allow_origin = resp.headers.get("access-control-allow-origin")
            allow_creds = resp.headers.get("access-control-allow-credentials")
            if allow_origin in (client_origin, "*") and (allow_creds == "true" or allow_origin == "*"):
                return True, f"Allowed origin: {allow_origin}, allow-credentials: {allow_creds}"
            return False, f"CORS headers mismatch: allow-origin={allow_origin}, allow-credentials={allow_creds}"
    except Exception as e:
        return False, f"OPTIONS request failed: {e}"


def check_firewall_status(port: int = 8000) -> str:
    """Check UFW / iptables to warn if port 8000 might be blocked."""
    if shutil.which("ufw"):
        try:
            res = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                if "inactive" in res.stdout.lower():
                    return "UFW inactive (all ports open)"
                elif f"{port}" in res.stdout:
                    return f"UFW active, port {port} rule found"
                else:
                    return f"WARNING: UFW active, ensure port {port} is allowed: sudo ufw allow {port}/tcp"
        except Exception:
            pass
    return "Firewall inspection skipped (standard Linux stack)"


def run_full_preflight(lan_ip_override: str | None = None, port: int = 8000) -> dict:
    """Run all preflight checks and return structured diagnostic results."""
    results = {
        "lan_ip": None,
        "interface": None,
        "is_private_rfc1918": False,
        "port_bound": False,
        "bind_all_interfaces": False,
        "health_ok": False,
        "ready_ok": False,
        "cors_ok": False,
        "firewall_info": "",
        "employee_url": None,
        "all_passed": False,
    }

    # 1. Detect LAN IP
    if lan_ip_override:
        ip = lan_ip_override
        iface = "manual-override"
    else:
        ip, iface = detect_primary_lan_ip()

    results["lan_ip"] = ip
    results["interface"] = iface
    results["is_private_rfc1918"] = is_rfc1918_private(ip) if ip else False

    # 2. Check Port Binding
    binding = check_port_binding(port)
    results["port_bound"] = binding["listening"]
    results["bind_all_interfaces"] = binding["bind_all"]

    # 3. Server Probes
    if ip and binding["listening"]:
        server_url = f"http://{ip}:{port}"
        results["employee_url"] = server_url

        # Health probe
        h_ok, _, _ = probe_http_endpoint(f"{server_url}/health")
        results["health_ok"] = h_ok

        # Ready probe
        r_ok, _, _ = probe_http_endpoint(f"{server_url}/health/ready")
        results["ready_ok"] = r_ok

        # CORS probe from synthetic remote employee laptop
        test_client_origin = "http://10.0.0.120:3000" if ip.startswith("10.") else "http://192.168.1.120:3000"
        c_ok, _ = probe_cors_preflight(server_url, test_client_origin)
        results["cors_ok"] = c_ok
    else:
        results["employee_url"] = f"http://localhost:{port}"

    # 4. Firewall check
    results["firewall_info"] = check_firewall_status(port)

    # Summary pass
    results["all_passed"] = bool(
        results["is_private_rfc1918"]
        and results["port_bound"]
        and results["health_ok"]
        and results["ready_ok"]
        and results["cors_ok"]
    )

    return results


def main():
    parser = argparse.ArgumentParser(description="Unotusk MVP LAN Connectivity Verification Probe")
    parser.add_argument("--port", type=int, default=8000, help="Port to probe (default: 8000)")
    parser.add_argument("--ip", type=str, default=None, help="Override detected LAN IP")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    results = run_full_preflight(lan_ip_override=args.ip, port=args.port)

    if args.json:
        print(json.dumps(results, indent=2))
        sys.exit(0 if results["all_passed"] else 1)

    print("================================================================")
    print(" UNOTUSK MVP — LAN CONNECTIVITY VERIFICATION PREFLIGHT")
    print("================================================================")
    print(f"Target Service: Unotusk API on Port {args.port}\n")

    # Step 1: IP Detection
    if results["is_private_rfc1918"]:
        print(f" [PASS] Primary LAN IP Detected: {results['lan_ip']} (interface: {results['interface']})")
    elif results["lan_ip"]:
        print(f" [WARN] Detected IP {results['lan_ip']} is not standard RFC 1918 private address")
    else:
        print(" [FAIL] No active RFC 1918 LAN interface detected. Connect to Wi-Fi/Ethernet.")

    # Step 2: Port Binding
    if results["port_bound"]:
        bind_scope = "0.0.0.0 (All interfaces - LAN Reachable)" if results["bind_all_interfaces"] else "Local only"
        print(f" [PASS] Port {args.port} is Listening ({bind_scope})")
    else:
        print(f" [FAIL] Port {args.port} is NOT listening. Start server with: docker compose up -d")

    # Step 3: Health Probes
    if results["health_ok"]:
        print(f" [PASS] HTTP GET {results['employee_url']}/health -> 200 OK")
    else:
        print(f" [FAIL] HTTP GET {results['employee_url']}/health failed")

    if results["ready_ok"]:
        print(f" [PASS] HTTP GET {results['employee_url']}/health/ready -> 200 OK")
    else:
        print(f" [FAIL] HTTP GET {results['employee_url']}/health/ready failed")

    # Step 4: CORS Preflight
    if results["cors_ok"]:
        print(" [PASS] CORS Preflight OPTIONS from LAN client origin accepted")
    else:
        print(" [FAIL] CORS Preflight OPTIONS failed or disallowed for LAN client origin")

    # Step 5: Firewall
    print(f" [INFO] Firewall Status: {results['firewall_info']}")

    print("----------------------------------------------------------------")
    if results["all_passed"]:
        print(" ✓ ALL CHECKS PASSED: Server is fully ready for multi-client LAN pilot!")
        print("\n Connect Employee Apps (Windows/macOS) using this Server URL:")
        print(f"   --> {results['employee_url']}")
        print("================================================================")
        sys.exit(0)
    else:
        print(" ✗ PREFLIGHT FAILED: Please address the failing checks above.")
        print("================================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()
