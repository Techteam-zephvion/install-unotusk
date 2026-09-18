import json
import logging

import pytest
from fastapi.testclient import TestClient

from apps.api.src.core.logging import (
    SecretSanitizingFilter,
    StructuredJSONFormatter,
    current_request_id,
    sanitize_log_message,
)
from apps.api.src.main import app


class TestSecretSanitization:
    def test_redacts_postgresql_connection_string(self):
        msg = "Connecting to postgresql+asyncpg://unotusk_user:P@ssw0rd!@10.0.0.59:5432/unotusk_db"
        sanitized = sanitize_log_message(msg)
        assert "P@ssw0rd!" not in sanitized
        assert "Connecting to postgresql+asyncpg://unotusk_user:[REDACTED]@10.0.0.59:5432/unotusk_db" == sanitized

    def test_redacts_redis_connection_string(self):
        msg = "Connecting to redis://:mypassword123@10.0.0.59:6379/0"
        sanitized = sanitize_log_message(msg)
        assert "mypassword123" not in sanitized
        assert "Connecting to redis://:[REDACTED]@10.0.0.59:6379/0" == sanitized

    def test_redacts_anthropic_api_key(self):
        msg = "Invoking Claude with key sk-ant-api03-abcdef1234567890"
        sanitized = sanitize_log_message(msg)
        assert "sk-ant-api03" not in sanitized
        assert "[REDACTED-KEY]" in sanitized

    def test_redacts_groq_api_key(self):
        msg = "Invoking Groq with key gsk_AbCdEf1234567890xyz"
        sanitized = sanitize_log_message(msg)
        assert "gsk_AbCdEf" not in sanitized
        assert "[REDACTED-KEY]" in sanitized

    def test_redacts_bearer_token(self):
        msg = "Request Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature"
        sanitized = sanitize_log_message(msg)
        assert "doNotLeakThisSignature" not in sanitized
        assert "Bearer [REDACTED]" in sanitized

    def test_redacts_raw_jwt(self):
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        msg = f"Extracted token {jwt_token} from payload"
        sanitized = sanitize_log_message(msg)
        assert jwt_token not in sanitized
        assert "[REDACTED-JWT]" in sanitized

    def test_redacts_key_value_passwords(self):
        msg = '{"user": "dev@acme.com", "password": "supersecretpassword", "token": "temp_sec_token"}'
        sanitized = sanitize_log_message(msg)
        assert "supersecretpassword" not in sanitized
        assert "temp_sec_token" not in sanitized
        assert '"password": "[REDACTED]"' in sanitized


class TestSecretSanitizingFilter:
    def test_sanitizes_log_record_message(self):
        f = SecretSanitizingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="Error connecting to postgresql://admin:secretPass@localhost/db",
            args=(),
            exc_info=None,
        )
        assert f.filter(record) is True
        assert "secretPass" not in record.msg
        assert "postgresql://admin:[REDACTED]@localhost/db" in record.msg

    def test_sanitizes_log_record_args_dict(self):
        f = SecretSanitizingFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="User failed auth: %s",
            args=({"password": "rawPassword123"},),
            exc_info=None,
        )
        assert f.filter(record) is True
        assert record.args["password"] == "[REDACTED]"

    def test_injects_correlation_id_into_record(self):
        f = SecretSanitizingFilter()
        token = current_request_id.set("corr-uuid-456")
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname=__file__,
                lineno=10,
                msg="Operation done",
                args=(),
                exc_info=None,
            )
            assert f.filter(record) is True
            assert record.request_id == "corr-uuid-456"
        finally:
            current_request_id.reset(token)


class TestStructuredJSONFormatter:
    def test_formats_valid_json_with_correlation_id(self):
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname=__file__,
            lineno=25,
            msg="High latency observed",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-999-abc"

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["level"] == "WARNING"
        assert data["logger"] == "test_logger"
        assert data["message"] == "High latency observed"
        assert data["request_id"] == "req-999-abc"
        assert "timestamp" in data


class TestRequestTracingMiddleware:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_generates_request_id_when_missing(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert len(req_id) >= 16

    def test_propagates_incoming_request_id(self, client):
        custom_id = "pilot-test-lan-client-001"
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == custom_id
