import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.database import get_db
from apps.api.src.config.settings import settings
from apps.api.src.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        environment=settings.APP_ENV,
    )


@router.get("/health/ready", response_model=ReadyResponse)
async def ready_check(db: AsyncSession = Depends(get_db)) -> ReadyResponse:
    # Check Database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"unhealthy: {type(e).__name__}"

    # Check Redis
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"unhealthy: {type(e).__name__}"

    return ReadyResponse(
        status="ready" if db_status == "connected" and redis_status == "connected" else "degraded",
        database=db_status,
        redis=redis_status,
    )
