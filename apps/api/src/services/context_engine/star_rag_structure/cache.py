"""
Ingestion-Time and Query-Time Code Graph Cache for Structure-Aware STAR-RAG.

Manages serialization, Redis persistence, and in-memory caching of FunctionGraph
representations associated with repository snapshots and commit identities.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.star_rag_structure.types import FunctionGraph

logger = logging.getLogger(__name__)

# Bounded in-memory graph cache: cache_key -> FunctionGraph
_MEMORY_CACHE_MAX_ENTRIES = 10
_MEMORY_GRAPH_CACHE: dict[str, FunctionGraph] = {}


class CodeGraphCache:
    """
    Two-tier (Memory + Redis) cache for AST function and dependency graphs.
    Eliminates request-time AST parsing and database graph construction overhead.
    """

    CACHE_TTL_SECONDS = 7 * 86400  # 7 days

    @classmethod
    def _make_key(cls, snapshot_id: uuid.UUID, commit_sha: str | None = None) -> str:
        sha_str = commit_sha.strip() if commit_sha and commit_sha.strip() else "latest"
        return f"starrag:graph:{snapshot_id}:{sha_str}"

    @classmethod
    async def _get_redis_client(cls) -> Any | None:
        if aioredis is None:
            return None
        try:
            return aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
            )
        except Exception as e:
            logger.debug("Failed to initialize Redis client for graph cache: %s", e)
            return None

    @classmethod
    async def get_graph(
        cls,
        snapshot_id: uuid.UUID,
        commit_sha: str | None = None,
        session: AsyncSession | None = None,
    ) -> FunctionGraph | None:
        """
        Retrieves the cached FunctionGraph for the given snapshot.
        Checks in-memory tier first, then Redis, and falls back to DB construction if needed.
        """
        key = cls._make_key(snapshot_id, commit_sha)

        # Tier 1: In-memory cache (<0.1ms)
        if key in _MEMORY_GRAPH_CACHE:
            logger.debug("CodeGraphCache Tier 1 HIT for key %s", key)
            return _MEMORY_GRAPH_CACHE[key]

        # Tier 2: Redis cache (~2-5ms)
        r = await cls._get_redis_client()
        if r is not None:
            try:
                cached_json = await r.get(key)
                if cached_json:
                    logger.debug("CodeGraphCache Tier 2 (Redis) HIT for key %s", key)
                    data = json.loads(cached_json)
                    graph = FunctionGraph.from_dict(data)
                    cls._store_in_memory(key, graph)
                    await r.aclose()
                    return graph
            except Exception as e:
                logger.warning("Error reading graph from Redis for key %s: %s", key, e)
            finally:
                try:
                    await r.aclose()
                except Exception:
                    pass

        # Tier 3: Database construction fallback if session provided
        if session is not None:
            logger.info("CodeGraphCache MISS for %s; building from database snapshot", key)
            from apps.api.src.services.context_engine.star_rag_structure.graph_extractor import (
                CodeGraphExtractor,
            )

            graph = await CodeGraphExtractor.build_graph_for_snapshot(
                session=session,
                snapshot_id=snapshot_id,
                file_ids=None,
                max_files=200,
            )
            if graph.nodes:
                await cls.set_graph(snapshot_id, commit_sha, graph)
            return graph

        return None

    @classmethod
    async def set_graph(
        cls,
        snapshot_id: uuid.UUID,
        commit_sha: str | None,
        graph: FunctionGraph,
    ) -> None:
        """
        Persists a FunctionGraph in memory and Redis with TTL.
        """
        key = cls._make_key(snapshot_id, commit_sha)

        # Store in Tier 1 memory
        cls._store_in_memory(key, graph)

        # Store in Tier 2 Redis
        r = await cls._get_redis_client()
        if r is not None:
            try:
                data = graph.to_dict()
                serialized = json.dumps(data)
                await r.set(key, serialized, ex=cls.CACHE_TTL_SECONDS)
                logger.debug(
                    "Cached FunctionGraph in Redis for %s (%d nodes, %d edges)",
                    key,
                    len(graph.nodes),
                    len(graph.edges),
                )
            except Exception as e:
                logger.warning("Failed to serialize and cache graph in Redis for %s: %s", key, e)
            finally:
                try:
                    await r.aclose()
                except Exception:
                    pass

    @classmethod
    def _store_in_memory(cls, key: str, graph: FunctionGraph) -> None:
        if len(_MEMORY_GRAPH_CACHE) >= _MEMORY_CACHE_MAX_ENTRIES:
            # Evict oldest entry (FIFO)
            first_key = next(iter(_MEMORY_GRAPH_CACHE))
            _MEMORY_GRAPH_CACHE.pop(first_key, None)
        _MEMORY_GRAPH_CACHE[key] = graph

    @classmethod
    async def invalidate_graph(cls, snapshot_id: uuid.UUID) -> None:
        """
        Invalidates all cached graph representations for a repository snapshot.
        """
        prefix = f"starrag:graph:{snapshot_id}:"
        # Invalidate memory
        keys_to_pop = [k for k in _MEMORY_GRAPH_CACHE if k.startswith(prefix)]
        for k in keys_to_pop:
            _MEMORY_GRAPH_CACHE.pop(k, None)

        # Invalidate Redis
        r = await cls._get_redis_client()
        if r is not None:
            try:
                pattern = f"{prefix}*"
                cursor = 0
                while True:
                    cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        await r.delete(*keys)
                    if cursor == 0:
                        break
                logger.info("Invalidated Redis graph cache for snapshot %s", snapshot_id)
            except Exception as e:
                logger.warning("Error invalidating Redis cache for %s: %s", snapshot_id, e)
            finally:
                try:
                    await r.aclose()
                except Exception:
                    pass

    @classmethod
    async def precompute_for_snapshot(
        cls,
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        commit_sha: str | None = None,
    ) -> FunctionGraph:
        """
        Executes ingestion-time graph construction:
        Extracts repository files, AST symbols, and dependencies, and writes the complete
        FunctionGraph to the multi-tier cache.
        """
        from apps.api.src.services.context_engine.star_rag_structure.graph_extractor import (
            CodeGraphExtractor,
        )

        logger.info(
            "Precomputing AST FunctionGraph during ingestion for snapshot %s (commit %s)",
            snapshot_id,
            commit_sha,
        )
        graph = await CodeGraphExtractor.build_graph_for_snapshot(
            session=session,
            snapshot_id=snapshot_id,
            file_ids=None,
            max_files=500,
        )
        await cls.set_graph(snapshot_id, commit_sha, graph)
        return graph
