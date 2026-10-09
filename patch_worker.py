import re

with open("services/workers/worker.py", "r") as f:
    content = f.read()

helper = """
async def delayed_requeue(task_data: dict[str, Any], r: aioredis.Redis, attempt: int) -> None:
    await asyncio.sleep(2 ** attempt)
    await r.lpush(QUEUE_NAME, json.dumps(task_data))

async def process_task"""

content = content.replace("async def process_task", helper)

content = content.replace(
    "await asyncio.sleep(2 ** attempt)  # Simple exponential backoff before requeueing\n            await r.lpush(QUEUE_NAME, json.dumps(task_data))",
    "asyncio.create_task(delayed_requeue(task_data, r, attempt))"
)

with open("services/workers/worker.py", "w") as f:
    f.write(content)

