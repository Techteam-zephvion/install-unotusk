import contextvars
import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to hold request correlation ID across async tasks
current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_request_id", default=""
)

# Universal regex sanitization patterns for secrets
SENSITIVE_PATTERNS = [
    # Database connection URLs with passwords (handles usernames or empty usernames, e.g. redis://:pass@)
    (
        re.compile(
            r"((?:postgresql(?:\+asyncpg)?|redis)://[^\s:@/]*:)(.*)(@(?:\[[0-9a-fA-F:]+\]|[\w.\-]+)(?::\d+)?(?:/[^\s]*)?)",
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\3",
    ),
    # LLM API keys
    (re.compile(r"gsk_[A-Za-z0-9_]{8,}", re.IGNORECASE), "[REDACTED-KEY]"),
    (re.compile(r"sk-ant-[A-Za-z0-9_.\-]{8,}", re.IGNORECASE), "[REDACTED-KEY]"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}", re.IGNORECASE), "[REDACTED-KEY]"),
    # Bearer tokens & JWTs
    (
        re.compile(r"Bearer\s+[A-Za-z0-9\-_.=]+", re.IGNORECASE),
        "Bearer [REDACTED]",
    ),
    (
        re.compile(r"eyJ[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_.+/=]*"),
        "[REDACTED-JWT]",
    ),
    # Key-value secrets (JSON, env, query params)
    (
        re.compile(
            r'("?(?:password|secret|token|api[_-]?key)"?\s*[:=]\s*["\']?)[^"\'\s,]{4,}(["\']?)',
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\2",
    ),
]


def sanitize_log_message(text: str) -> str:
    """Sanitize secrets from a string using comprehensive regex replacements."""
    if not text:
        return text
    sanitized = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class SecretSanitizingFilter(logging.Filter):
    """Logging filter that sanitizes secret tokens and injects correlation ID."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Inject correlation ID
        req_id = current_request_id.get()
        record.request_id = req_id if req_id else "-"

        # Sanitize message string
        if isinstance(record.msg, str):
            record.msg = sanitize_log_message(record.msg)

        # Sanitize record arguments if present
        if record.args:
            def _clean_arg(val, key_name: str | None = None):
                if key_name and any(
                    s in key_name.lower()
                    for s in ("password", "secret", "token", "key", "auth")
                ):
                    return "[REDACTED]"
                if isinstance(val, str):
                    return sanitize_log_message(val)
                elif isinstance(val, dict):
                    return {k: _clean_arg(v, key_name=str(k)) for k, v in val.items()}
                elif isinstance(val, (list, tuple)):
                    return type(val)(_clean_arg(v) for v in val)
                return val

            if isinstance(record.args, tuple):
                record.args = tuple(_clean_arg(arg) for arg in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: _clean_arg(v, key_name=str(k)) for k, v in record.args.items()}

        return True


class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        req_id = getattr(record, "request_id", "-")
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": req_id,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exception"] = sanitize_log_message(
                self.formatException(record.exc_info)
            )

        return json.dumps(log_entry)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware that injects X-Request-ID and logs structured HTTP access metrics."""

    def __init__(self, app, logger: logging.Logger | None = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger("unotusk.access")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate X-Request-ID
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())

        # Bind to async context
        token = current_request_id.set(req_id)

        # Client IP extraction (handles proxies / LAN forwarders)
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "unknown"

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            response.headers["X-Request-ID"] = req_id

            # Access log
            self.logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms) [client={client_ip}] [req_id={req_id}]",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "client_ip": client_ip,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.logger.error(
                f"{request.method} {request.url.path} failed after {duration_ms}ms: {exc}",
                exc_info=True,
            )
            raise
        finally:
            current_request_id.reset(token)


def setup_server_logging(use_json: bool = False) -> None:
    """Initialize root and application loggers with secret sanitization."""
    root_logger = logging.getLogger()
    sanitizer = SecretSanitizingFilter()

    # Add filter to root logger and existing handlers
    root_logger.addFilter(sanitizer)
    for handler in root_logger.handlers:
        handler.addFilter(sanitizer)
        if use_json:
            handler.setFormatter(StructuredJSONFormatter())
