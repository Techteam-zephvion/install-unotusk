import uuid

from fastapi import APIRouter, Depends, Query, status
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
