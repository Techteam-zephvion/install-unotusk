from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from apps.api.src.config.settings import settings

try:
    from pgvector.asyncpg import register_vector
    _HAS_PGVECTOR_ASYNCPG = True
except ImportError:
    _HAS_PGVECTOR_ASYNCPG = False

engine_kwargs = {"echo": settings.DEBUG}
if settings.APP_ENV == "test":
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

# Engine configuration
try:
    engine = create_async_engine(
        settings.DATABASE_URL,
        **engine_kwargs,
    )

    if _HAS_PGVECTOR_ASYNCPG and hasattr(engine, "sync_engine"):
        @event.listens_for(engine.sync_engine, "connect")
        def _register_pgvector_codecs(dbapi_connection, connection_record):
            if hasattr(dbapi_connection, "run_async"):
                async def _register(conn):
                    try:
                        await register_vector(conn)
                    except Exception:
                        pass
                try:
                    dbapi_connection.run_async(_register)
                except Exception:
                    pass

    # Async session factory
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
except Exception:
    engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
