import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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
    services,
    tasks,
    webhooks,
)
from apps.api.src.config.settings import settings
from apps.api.src.core.data_plane_gateway import DataPlaneGatewayMiddleware
from apps.api.src.core.data_plane_middleware import DataPlaneSecurityMiddleware
from apps.api.src.core.logging import RequestTracingMiddleware, setup_server_logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
setup_server_logging()
logger = logging.getLogger("unotusk-api")


async def bootstrap_data_plane_on_startup() -> None:
    import urllib.parse
    import uuid

    import httpx
    from sqlalchemy import select

    from apps.api.src.core.federation import (
        derive_canonical_project_id,
        sign_cluster_sync_payload,
    )
    from apps.api.src.db.session import AsyncSessionLocal
    from apps.api.src.models.enums import (
        IntegrationProvider,
        IntegrationStatus,
        ProjectStatus,
    )
    from apps.api.src.models.integration import Integration
    from apps.api.src.models.organization import Organization
    from apps.api.src.models.project import Project
    from apps.api.src.models.repository import Repository
    from apps.api.src.models.snapshot import RepositorySnapshot
    from apps.api.src.services.repository_service import RepositoryService
    from apps.api.src.services.slug import slugify

    if AsyncSessionLocal is None:
        return

    async with AsyncSessionLocal() as session:
        org_q = select(Organization).limit(1)
        org = (await session.execute(org_q)).scalar_one_or_none()
        if org is None:
            org = Organization(
                name="Acme Corporation", slug=settings.DATA_PLANE_ORG_SLUG
            )
            session.add(org)
            await session.flush()

        repo_url = (settings.TARGET_REPO_URL or "").strip()
        parsed = urllib.parse.urlparse(repo_url).path.strip("/").split("/")
        owner = parsed[-2] if len(parsed) >= 2 else "default"
        default_name = settings.DATA_PLANE_PROJECT_SLUG or "project"
        raw_name = (
            parsed[-1].removesuffix(".git")
            if len(parsed) >= 2 and parsed[-1]
            else default_name
        )
        proj_slug = settings.DATA_PLANE_PROJECT_SLUG or slugify(raw_name)
        canonical_id = (
            uuid.UUID(settings.DATA_PLANE_PROJECT_ID)
            if settings.DATA_PLANE_PROJECT_ID
            else derive_canonical_project_id(
                settings.DATA_PLANE_ORG_SLUG, proj_slug
            )
        )

        proj = await session.get(Project, canonical_id)
        if proj is None:
            proj = (
                await session.execute(
                    select(Project).where(
                        Project.organization_id == org.id,
                        Project.slug == proj_slug,
                    )
                )
            ).scalar_one_or_none()
        if proj is None:
            proj = Project(
                id=canonical_id,
                organization_id=org.id,
                name=raw_name,
                slug=proj_slug,
                status=ProjectStatus.CREATED,
                port=settings.SERVER_PORT or settings.PORT,
            )
            session.add(proj)
            await session.commit()
        else:
            if settings.SERVER_PORT or settings.PORT:
                proj.port = settings.SERVER_PORT or settings.PORT
            await session.commit()

        # Lock DataPlaneSecurityMiddleware to canonical ID & slug immediately
        settings.DATA_PLANE_PROJECT_ID = str(proj.id)
        settings.DATA_PLANE_PROJECT_SLUG = proj.slug

        if repo_url:
            ig_q = select(Integration).where(Integration.project_id == proj.id)
            integ = (await session.execute(ig_q)).scalars().first()
            if integ is None:
                integ = Integration(
                    project_id=proj.id,
                    provider=IntegrationProvider.GITHUB,
                    status=IntegrationStatus.CONNECTED,
                    metadata={},
                )
                session.add(integ)
                await session.flush()

            rp_q = select(Repository).where(Repository.project_id == proj.id)
            repo = (await session.execute(rp_q)).scalars().first()
            if repo is None:
                repo = Repository(
                    project_id=proj.id,
                    integration_id=integ.id,
                    provider=IntegrationProvider.GITHUB,
                    external_id=f"{owner}_{raw_name}",
                    owner=owner,
                    name=raw_name,
                    full_name=f"{owner}/{raw_name}",
                    default_branch="main",
                    url=repo_url,
                    is_private=False,
                )
                session.add(repo)
                await session.commit()

            sn_q = select(RepositorySnapshot).where(
                RepositorySnapshot.repository_id == repo.id
            )
            snap = (await session.execute(sn_q)).scalars().first()
            if snap is None:
                try:
                    await RepositoryService.trigger_ingestion_system(
                        session, proj.id, repo.id
                    )
                except Exception as ing_err:
                    logger.warning("Ingestion trigger deferred or failed: %s", ing_err)

        # Register canonical project_id & port with Control Plane via HMAC
        active_port = settings.SERVER_PORT or settings.PORT
        if settings.CONTROL_PLANE_URL and active_port != 28000:
            payload = {
                "servers": [{
                    "project_id": str(proj.id),
                    "name": proj.name,
                    "slug": proj.slug,
                    "port": active_port,
                    "state": "running",
                    "repo_url": repo_url or None,
                }]
            }
            ts, sig, raw_body = sign_cluster_sync_payload(payload)
            sync_url = (
                f"{settings.CONTROL_PLANE_URL.rstrip('/')}"
                "/api/v1/projects/sync-servers"
            )
            hdrs = {
                "Content-Type": "application/json",
                "X-Unotusk-Timestamp": ts,
                "X-Unotusk-Cluster-Signature": sig,
            }
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(sync_url, content=raw_body, headers=hdrs)
            except Exception as sync_err:
                logger.warning("Sync heartbeat deferred: %s", sync_err)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    try:
        from sqlalchemy import text
        from apps.api.src.db.session import engine
        if engine:
            async with engine.begin() as conn:
                await conn.execute(
                    text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;")
                )
                await conn.execute(
                    text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN NOT NULL DEFAULT FALSE;")
                )
                await conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_conversations_is_archived ON conversations (is_archived);")
                )
                await conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_conversations_is_pinned ON conversations (is_pinned);")
                )
    except Exception as e:
        logger.warning(f"Database column self-check notice: {e}")

    if settings.TARGET_REPO_URL or settings.is_data_plane:
        await bootstrap_data_plane_on_startup()
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

# Response Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Data Plane Reverse-Proxy Gateway (active on Control Plane, proxies to Data Planes)
app.add_middleware(DataPlaneGatewayMiddleware)

# Data Plane Container-Level Authorization & Boundary Middleware (active on Data Plane)
app.add_middleware(DataPlaneSecurityMiddleware)

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
for r in [
    health.router,
    auth.router,
    organizations.router,
    projects.router,
    repository.router,
    intelligence.router,
    discovery.router,
    reports.router,
    knowledge.router,
    services.router,
    tasks.router,
    webhooks.router,
]:
    app.include_router(r, prefix=settings.API_V1_PREFIX)
    app.include_router(r)
