import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.src.api.exceptions import AppException
from apps.api.src.api.routes import (
    auth,
    discovery,
    health,
    intelligence,
    knowledge,
    organizations,
    projects,
    reports,
    repository,
    tasks,
)
from apps.api.src.config.settings import settings
from apps.api.src.core.logging import RequestTracingMiddleware, setup_server_logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
setup_server_logging()
logger = logging.getLogger("unotusk-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG or settings.APP_ENV == "development" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Correlation & Request Tracing Middleware
app.add_middleware(RequestTracingMiddleware)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3})(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Standard Error Handlers
@app.exception_handler(AppException)
async def handle_app_exception(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = ".".join([str(part) for part in err.get("loc", [])])
        errors.append({"field": loc, "issue": err.get("msg")})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": errors,
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException):
    code = "HTTP_ERROR"
    if exc.status_code == 404:
        code = "NOT_FOUND"
    elif exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "details": None,
            }
        },
    )


@app.exception_handler(Exception)
async def handle_generic_exception(request: Request, exc: Exception):
    import re

    exc_str = str(exc)
    # Sanitize sensitive patterns from exception messages before logging.
    # This prevents passwords, API keys, and connection strings from appearing in logs.
    _SENSITIVE_PATTERNS = [
        (r"(postgresql(?:\+asyncpg)?://[^\s:]+:)([^\s@]+)(@\S+)", r"\1[REDACTED]\3"),
        (r"(redis://[^\s:]+:)([^\s@]+)(@\S+)", r"\1[REDACTED]\3"),
        (r"gsk_[A-Za-z0-9_]{10,}", "[REDACTED]"),
        (r"sk-ant-[A-Za-z0-9_.\-]{10,}", "[REDACTED]"),
        (r"((?:api[_-]?key|auth[_-]?secret|password|token)\s*=\s*)\S{6,}", r"\1[REDACTED]"),
    ]
    sanitized = exc_str
    for pattern, replacement in _SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    # In production, suppress detailed tracebacks (exc_info) to avoid leaking internals.
    include_traceback = settings.APP_ENV != "production" or settings.DEBUG
    logger.error(f"Unhandled server error: {sanitized}", exc_info=include_traceback)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
                "details": None,
            }
        },
    )


# Register Routers
app.include_router(health.router)
for r in [
    auth.router,
    organizations.router,
    projects.router,
    repository.router,
    intelligence.router,
    discovery.router,
    reports.router,
    knowledge.router,
    tasks.router,
]:
    app.include_router(r, prefix=settings.API_V1_PREFIX)
    app.include_router(r)
