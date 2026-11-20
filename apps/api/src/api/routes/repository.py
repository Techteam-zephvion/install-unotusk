import asyncio
from datetime import datetime, timezone
import json
import uuid

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.user import User
from apps.api.src.schemas.context import (
    DependencyRead,
    FileDetailRead,
    FileRead,
    ProjectRepositoryContext,
    SymbolRead,
)
from apps.api.src.schemas.graph import GraphResponse
from apps.api.src.schemas.repository import (
    GitHubConnectRequest,
    RepositoryRead,
    RepositorySelectRequest,
)
from apps.api.src.schemas.snapshot import IngestTriggerResponse, SnapshotRead
from apps.api.src.services.graph_service import GraphService
from apps.api.src.services.project_service import ProjectService
from apps.api.src.services.repository_service import RepositoryService

router = APIRouter(prefix="/projects/{project_id}", tags=["Repository & Context"])


@router.post("/github/connect")
async def connect_github(
    project_id: str,
    data: GitHubConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.connect_github(
        db, current_user.id, resolved_id, data.github_token
    )


@router.get("/integrations", response_model=list[dict])
async def list_project_integrations(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.list_project_integrations(db, current_user.id, resolved_id)


@router.get("/repositories")
async def list_available_repositories(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.list_available_repositories(db, current_user.id, resolved_id)


@router.post(
    "/repositories/select", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED
)
async def select_repository(
    project_id: str,
    data: RepositorySelectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryRead:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.select_repository(db, current_user.id, resolved_id, data)


@router.post(
    "/repositories/{repository_id}/ingest",
    response_model=IngestTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ingest(
    project_id: str,
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IngestTriggerResponse:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.trigger_ingestion(db, current_user.id, resolved_id, repository_id)


@router.post(
    "/repositories/{repository_id}/sync-issues",
    status_code=status.HTTP_200_OK,
    summary="Synchronize GitHub repository issues and requirements into project intelligence context",
)
async def sync_repository_issues(
    project_id: str,
    repository_id: uuid.UUID,
    payload: dict | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    issues_data = (payload or {}).get("issues") if payload else None
    return await RepositoryService.sync_github_issues(
        db, current_user.id, resolved_id, repository_id, issues_data=issues_data
    )


@router.get("/ingestions/{ingestion_id}", response_model=SnapshotRead)
async def get_ingestion_status(
    project_id: str,
    ingestion_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SnapshotRead:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.get_ingestion_status(
        db, current_user.id, resolved_id, ingestion_id
    )


@router.get("/ingestion/stream")
async def stream_ingestion_progress(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Server-Sent Events (SSE) stream yielding real-time ingestion status and progress."""
    resolved_id = await ProjectService.resolve_project_id(db, project_id)

    async def event_generator():
        phase_map = {
            "QUEUED": (0, 0.05, "Ingestion queued in background worker"),
            "CLONING": (1, 0.20, "Fetching Git tree and verifying commit references"),
            "SCANNING": (2, 0.40, "Enumerating directories and filtering source files"),
            "PARSING": (3, 0.65, "Extracting AST functions, classes, and imports"),
            "INDEXING": (4, 0.85, "Generating vector embeddings and graph edges"),
            "COMPLETED": (5, 1.0, "Intelligence Engine Online"),
            "READY": (5, 1.0, "Intelligence Engine Online"),
            "FAILED": (-1, 0.0, "Ingestion failed or stopped"),
        }

        for _ in range(180):  # Keep SSE connection open for up to 3 minutes
            try:
                ctx = await RepositoryService.get_repository_context(db, current_user.id, resolved_id)
                snapshot = ctx.active_snapshot

                status_val = "READY"
                if snapshot:
                    status_val = (
                        snapshot.status.value
                        if hasattr(snapshot.status, "value")
                        else str(snapshot.status)
                    )
                status_upper = status_val.upper()

                phase_idx, progress_pct, phase_desc = phase_map.get(
                    status_upper, (0, 0.1, status_upper)
                )

                total_files = getattr(snapshot, "total_files", 0) or 0
                processed_files = (
                    getattr(snapshot, "processed_files", 0)
                    or getattr(snapshot, "parsed_files", 0)
                    or 0
                )

                if total_files > 0 and status_upper in ("PARSING", "SCANNING", "INDEXING"):
                    dynamic_pct = min(0.95, max(progress_pct, processed_files / total_files))
                else:
                    dynamic_pct = progress_pct

                payload = {
                    "project_id": str(resolved_id),
                    "status": status_upper,
                    "phase": phase_idx,
                    "progress": round(dynamic_pct, 3),
                    "phase_description": phase_desc,
                    "commit_sha": snapshot.commit_sha if snapshot else None,
                    "branch": snapshot.branch if snapshot else "main",
                    "total_files": total_files,
                    "processed_files": processed_files,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                yield f"data: {json.dumps(payload)}\n\n"

                if status_upper in ("READY", "COMPLETED", "FAILED"):
                    await asyncio.sleep(4)
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                yield f"data: {json.dumps({'status': 'ERROR', 'error': str(e)})}\n\n"
                await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/repository", response_model=ProjectRepositoryContext)
async def get_repository_context(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRepositoryContext:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.get_repository_context(db, current_user.id, resolved_id)


@router.get("/files", response_model=list[FileRead])
async def list_files(
    project_id: str,
    limit: int = Query(default=500, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FileRead]:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.list_files(db, current_user.id, resolved_id, limit=limit)


@router.get("/files/{file_id}", response_model=FileDetailRead)
async def get_file_detail(
    project_id: str,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileDetailRead:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.get_file_detail(db, current_user.id, resolved_id, file_id)


@router.get("/symbols", response_model=list[SymbolRead])
async def list_symbols(
    project_id: str,
    limit: int = Query(default=500, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SymbolRead]:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.list_symbols(db, current_user.id, resolved_id, limit=limit)


@router.get("/dependencies", response_model=list[DependencyRead])
async def list_dependencies(
    project_id: str,
    limit: int = Query(default=500, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DependencyRead]:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.list_dependencies(db, current_user.id, resolved_id, limit=limit)


@router.post(
    "/repository/reindex",
    response_model=IngestTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reindex_repository(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IngestTriggerResponse:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    ctx = await RepositoryService.get_repository_context(db, current_user.id, resolved_id)
    if not ctx.repository:
        from apps.api.src.api.exceptions import NotFoundException

        raise NotFoundException(
            code="NO_CONNECTED_REPOSITORY", message="No repository connected to re-index"
        )
    return await RepositoryService.trigger_ingestion(
        db, current_user.id, resolved_id, ctx.repository.id
    )


@router.get("/graph", response_model=GraphResponse)
async def get_project_graph(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GraphResponse:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await GraphService.get_project_graph(db, current_user.id, resolved_id)


@router.get("/git/branches")
async def get_git_branches(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.get_git_branches(db, current_user.id, resolved_id)


@router.get("/git/diff")
async def get_git_diff(
    project_id: str,
    base: str = Query(default="HEAD~1"),
    head: str = Query(default="HEAD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.get_git_diff(db, current_user.id, resolved_id, base_ref=base, head_ref=head)


@router.get("/git/log")
async def get_git_log(
    project_id: str,
    count: int = Query(default=20, ge=1, le=100),
    branch: str = Query(default="HEAD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    resolved_id = await ProjectService.resolve_project_id(db, project_id)
    return await RepositoryService.get_git_log(db, current_user.id, resolved_id, count=count, branch=branch)
