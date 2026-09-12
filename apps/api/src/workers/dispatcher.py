import asyncio
import json
import uuid
from typing import Any

import redis.asyncio as aioredis

from apps.api.src.config.settings import settings


class TaskDispatcher:
    _redis: aioredis.Redis | None = None
    _loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    def get_redis(cls) -> aioredis.Redis:
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if cls._redis is None or cls._loop != current_loop:
            cls._loop = current_loop
            cls._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
        return cls._redis

    @classmethod
    async def close(cls) -> None:
        if cls._redis is not None:
            await cls._redis.aclose()
            cls._redis = None
            cls._loop = None

    @classmethod
    async def enqueue(
        cls,
        task_name: str,
        payload: dict[str, Any],
        queue: str = "unotusk_tasks",
    ) -> str:
        r = cls.get_redis()
        task_id = str(uuid.uuid4())
        task_data = {
            "id": task_id,
            "name": task_name,
            "payload": payload,
            "status": "QUEUED",
        }
        # Save initial task status
        await r.set(f"task:{task_id}", json.dumps(task_data), ex=3600)
        # Push to queue
        await r.lpush(queue, json.dumps(task_data))
        return task_id

    @classmethod
    async def get_status(cls, task_id: str) -> dict[str, Any] | None:
        r = cls.get_redis()
        data = await r.get(f"task:{task_id}")
        if data is None:
            return None
        return json.loads(data)
