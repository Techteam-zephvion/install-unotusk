from unittest.mock import MagicMock, patch

from scripts.verify_lan_connectivity import (
    check_port_binding,
    detect_primary_lan_ip,
    is_rfc1918_private,
    probe_cors_preflight,
    probe_http_endpoint,
    run_full_preflight,
)


class TestRfc1918Validation:
    def test_identifies_private_ipv4_addresses(self):
        assert is_rfc1918_private("10.0.0.59") is True
        assert is_rfc1918_private("10.254.1.100") is True
        assert is_rfc1918_private("192.168.1.15") is True
        assert is_rfc1918_private("172.16.5.20") is True
        assert is_rfc1918_private("172.31.255.254") is True

    def test_rejects_loopback_and_public_ips(self):
        assert is_rfc1918_private("127.0.0.1") is False
        assert is_rfc1918_private("8.8.8.8") is False
        assert is_rfc1918_private("1.1.1.1") is False
        assert is_rfc1918_private("169.254.1.1") is False  # Link-local is RFC 3927, not 1918
        assert is_rfc1918_private("invalid-ip") is False
        assert is_rfc1918_private("") is False


class TestLanDetection:
    def test_detect_primary_lan_ip_via_routing_probe(self):
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ("10.0.0.59", 54321)

        with patch("socket.socket") as mock_socket_cls:
            mock_socket_cls.return_value.__enter__.return_value = mock_sock
            ip, iface = detect_primary_lan_ip()
            assert ip == "10.0.0.59"
            assert iface == "auto-route"


class TestPortBinding:
    def test_detects_listening_port_via_socket_probe(self):
        with patch("socket.socket") as mock_socket_cls:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0
            mock_socket_cls.return_value.__enter__.return_value = mock_sock

            with patch("shutil.which", return_value=None):
                status = check_port_binding(8000)
                assert status["listening"] is True


class TestCorsAndHttpProbe:
    def test_cors_preflight_accepts_matching_origin(self):
        mock_resp = MagicMock()
        mock_resp.headers = {
            "access-control-allow-origin": "http://10.0.0.120:3000",
            "access-control-allow-credentials": "true",
        }

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            ok, msg = probe_cors_preflight("http://10.0.0.59:8000", "http://10.0.0.120:3000")
            assert ok is True
            assert "Allowed origin" in msg

    def test_cors_preflight_rejects_missing_headers(self):
        mock_resp = MagicMock()
        mock_resp.headers = {}

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            ok, msg = probe_cors_preflight("http://10.0.0.59:8000", "http://10.0.0.120:3000")
            assert ok is False
            assert "mismatch" in msg

    def test_http_probe_returns_true_on_200(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "ok"}'

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            ok, status, body = probe_http_endpoint("http://10.0.0.59:8000/health")
            assert ok is True
            assert status == 200
            assert "status" in body


class TestFullPreflight:
    def test_run_full_preflight_passes_when_all_services_ok(self):
        with (
            patch("scripts.verify_lan_connectivity.detect_primary_lan_ip", return_value=("10.0.0.59", "wlo1")),
            patch("scripts.verify_lan_connectivity.check_port_binding", return_value={"listening": True, "bind_all": True, "details": ""}),
            patch("scripts.verify_lan_connectivity.probe_http_endpoint", return_value=(True, 200, '{"status": "ok"}')),
            patch("scripts.verify_lan_connectivity.probe_cors_preflight", return_value=(True, "Allowed")),
            patch("scripts.verify_lan_connectivity.check_firewall_status", return_value="UFW inactive"),
        ):
            results = run_full_preflight()
            assert results["all_passed"] is True
            assert results["lan_ip"] == "10.0.0.59"
            assert results["employee_url"] == "http://10.0.0.59:8000"
            assert results["port_bound"] is True
            assert results["cors_ok"] is True
