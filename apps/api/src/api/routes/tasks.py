from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.exceptions import NotFoundException
from apps.api.src.models.user import User
from apps.api.src.workers.dispatcher import TaskDispatcher

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class PingTaskRequest(BaseModel):
    message: str = "health-check"


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/ping", response_model=TaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ping_task(
    payload: PingTaskRequest,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task_id = await TaskDispatcher.enqueue(
        "ping", {"message": payload.message, "user_id": str(current_user.id)}
    )
    return TaskResponse(
        task_id=task_id,
        status="QUEUED",
        message="Ping task enqueued successfully",
    )


@router.get("/{task_id}", response_model=dict[str, Any])
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    task = await TaskDispatcher.get_status(task_id)
    if task is None:
        raise NotFoundException(code="TASK_NOT_FOUND", message="Background task not found")
    return task
