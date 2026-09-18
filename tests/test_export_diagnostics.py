import json
import os
import tarfile
from unittest.mock import patch

from scripts.export_diagnostics import (
    export_diagnostics_bundle,
    get_docker_status,
    sanitize_text,
)


class TestDiagnosticSanitization:
    def test_redacts_database_passwords(self):
        text = "Failed to connect: postgresql+asyncpg://admin:SuperSecretPass123!@10.0.0.59:5432/unotusk"
        clean = sanitize_text(text)
        assert "SuperSecretPass123!" not in clean
        assert "postgresql+asyncpg://admin:[REDACTED]@10.0.0.59:5432/unotusk" in clean

    def test_redacts_redis_passwords(self):
        text = "Redis auth failed on redis://:redisSecretPassword@127.0.0.1:6379/0"
        clean = sanitize_text(text)
        assert "redisSecretPassword" not in clean
        assert "redis://:[REDACTED]@127.0.0.1:6379/0" in clean

    def test_redacts_llm_api_keys(self):
        text = "Loaded keys: gsk_1234567890abcdef and sk-ant-api03-abcdef1234567890"
        clean = sanitize_text(text)
        assert "gsk_1234567890abcdef" not in clean
        assert "sk-ant-api03-abcdef1234567890" not in clean
        assert "[REDACTED-GROQ-KEY]" in clean
        assert "[REDACTED-ANTHROPIC-KEY]" in clean

    def test_redacts_bearer_and_jwts(self):
        jwt_val = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeak"
        text = f"Header: Bearer {jwt_val}"
        clean = sanitize_text(text)
        assert "doNotLeak" not in clean
        assert "Bearer [REDACTED]" in clean


class TestContainerIsolation:
    def test_docker_status_strictly_ignores_foreign_containers(self):
        foreign_mock_output = "\n".join([
            json.dumps({"Names": "unotusk-api", "Image": "unotusk-api:latest", "Status": "Up", "State": "running", "Ports": "0.0.0.0:8000->8000/tcp"}),
            json.dumps({"Names": "unotusk-2-ups-1", "Image": "ups:dev", "Status": "Up", "State": "running", "Ports": "8443->8443/tcp"}),
            json.dumps({"Names": "nammadharani-web-1", "Image": "node:18", "Status": "Up", "State": "running", "Ports": "3000->3000/tcp"}),
            json.dumps({"Names": "supabase_db_unotusk-2", "Image": "supabase:latest", "Status": "Up", "State": "running", "Ports": "5432->5432/tcp"}),
        ])

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = foreign_mock_output

            status = get_docker_status()
            collected_names = [c["name"] for c in status["containers"]]

            assert "unotusk-api" in collected_names
            assert "unotusk-2-ups-1" not in collected_names
            assert "nammadharani-web-1" not in collected_names
            assert "supabase_db_unotusk-2" not in collected_names


class TestDiagnosticBundleExport:
    def test_bundle_creation_and_synthetic_secret_absence(self, tmp_path):
        synthetic_secrets = [
            "sk-ant-api03-SECRET_NEVER_LEAK_ME_12345",
            "gsk_SECRET_GROQ_KEY_DO_NOT_EXPOSE",
            "postgresql+asyncpg://postgres:LEAKY_PASSWORD_999@localhost:5432/db",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        ]

        mock_logs = {
            "api": [
                f"2026-09-18 11:00:00 [INFO] Client connected with token Bearer {synthetic_secrets[3]}",
                f"2026-09-18 11:00:01 [ERROR] DB connection failed {synthetic_secrets[2]}",
            ],
            "worker": [
                f"2026-09-18 11:00:02 [INFO] Groq worker initialized with {synthetic_secrets[1]}",
                f"2026-09-18 11:00:03 [INFO] Claude engine set {synthetic_secrets[0]}",
            ],
        }

        with (
            patch("scripts.export_diagnostics.get_sanitized_logs", return_value={
                k: [sanitize_text(line) for line in v] for k, v in mock_logs.items()
            }),
            patch("scripts.export_diagnostics.get_server_health", return_value={"url": "http://10.0.0.59:8000", "liveness": {"status": "ok"}}),
        ):
            json_path, archive_path, sha256 = export_diagnostics_bundle(
                output_dir=str(tmp_path),
                server_url="http://10.0.0.59:8000",
                create_archive=True,
            )

            assert os.path.exists(json_path)
            assert os.path.exists(archive_path)
            assert len(sha256) == 64

            # Verify contents of JSON
            with open(json_path, encoding="utf-8") as f:
                content = f.read()

            # Ensure 100% absence of all synthetic secrets
            for secret in synthetic_secrets:
                assert secret not in content, f"Synthetic secret '{secret}' found in exported diagnostics!"

            # Verify tar.gz validity
            with tarfile.open(archive_path, "r:gz") as tar:
                names = tar.getnames()
                assert len(names) == 1
                assert names[0].startswith("unotusk_diagnostics_")
                assert names[0].endswith(".json")
