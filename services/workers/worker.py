import asyncio
import json
import logging
import os
import signal
import sys
import uuid
from typing import Any
import redis.asyncio as aioredis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("unotusk-worker")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("QUEUE_NAME", "unotusk_tasks")


async def process_task(task_data: dict[str, Any], r: aioredis.Redis) -> None:
    task_id = task_data.get("id")
    task_name = task_data.get("name")
    payload = task_data.get("payload", {})
    logger.info(f"Processing task {task_id} of type '{task_name}'")

    # Update status to PROCESSING
    task_data["status"] = "PROCESSING"
    await r.set(f"task:{task_id}", json.dumps(task_data), ex=3600)

    try:
        if task_name == "ping":
            result = {
                "pong": True,
                "echo": payload.get("message", "hello"),
                "worker_status": "healthy",
            }
        elif task_name == "ingest_repository":
            snapshot_id_str = payload.get("snapshot_id")
            override_dir = payload.get("override_local_dir")
            if snapshot_id_str:
                from apps.api.src.services.ingestion_service import IngestionService
                await IngestionService.run_ingestion(
                    uuid.UUID(snapshot_id_str),
                    override_local_dir=override_dir,
                )
            result = {
                "ingestion_triggered": True,
                "snapshot_id": snapshot_id_str,
            }
        else:
            result = {"unknown_task": True}

        task_data["status"] = "COMPLETED"
        task_data["result"] = result
        await r.set(f"task:{task_id}", json.dumps(task_data), ex=3600)
        logger.info(f"Task {task_id} completed successfully")

    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}", exc_info=True)
        task_data["status"] = "FAILED"
        task_data["error"] = str(exc)
        await r.set(f"task:{task_id}", json.dumps(task_data), ex=3600)


async def run_worker() -> None:
    logger.info(f"Starting worker on queue '{QUEUE_NAME}', connecting to {REDIS_URL}...")
    r = aioredis.from_url(REDIS_URL, decode_responses=True)

    running = True

    def handle_stop(*args: Any) -> None:
        nonlocal running
        logger.info("Shutdown signal received, stopping worker...")
        running = False

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_stop)
        except NotImplementedError:
            pass

    try:
        while running:
            popped = await r.brpop(QUEUE_NAME, timeout=2)
            if popped:
                _, raw_data = popped
                try:
                    task_data = json.loads(raw_data)
                    await process_task(task_data, r)
                except Exception as e:
                    logger.error(f"Error parsing task: {e}")
    finally:
        await r.aclose()
        logger.info("Worker stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(run_worker())
