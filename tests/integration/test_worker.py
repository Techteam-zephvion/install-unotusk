import json

import pytest
import redis.asyncio as aioredis

from apps.api.src.config.settings import settings
from apps.api.src.workers.dispatcher import TaskDispatcher
from services.workers.worker import process_task


@pytest.mark.asyncio
async def test_worker_pipeline_execution():
    # Verify Redis connectivity
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
    except Exception:
        pytest.skip("Local Redis server not accessible from host test runner")

    try:
        # 1. API enqueues task
        test_queue = "test_worker_queue"
        task_id = await TaskDispatcher.enqueue(
            task_name="ping",
            payload={"message": "automated-test-run"},
            queue=test_queue,
        )
        assert task_id is not None

        # Check queued status
        initial_status = await TaskDispatcher.get_status(task_id)
        assert initial_status["status"] == "QUEUED"

        # 2. Worker pops task from queue
        popped = await r.brpop(test_queue, timeout=2)
        assert popped is not None
        _, raw_task = popped
        task_data = json.loads(raw_task)

        # 3. Worker processes task
        await process_task(task_data, r)

        # 4. Verify completed status and output
        final_status = await TaskDispatcher.get_status(task_id)
        assert final_status["status"] == "COMPLETED"
        assert final_status["result"]["pong"] is True
        assert final_status["result"]["echo"] == "automated-test-run"

    finally:
        await r.aclose()
