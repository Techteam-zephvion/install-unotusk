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
from apps.api.src.schemas.repository import (
    GitHubConnectRequest,
    RepositoryRead,
    RepositorySelectRequest,
)
from apps.api.src.schemas.snapshot import IngestTriggerResponse, SnapshotRead
from apps.api.src.services.repository_service import RepositoryService

router = APIRouter(prefix="/projects/{project_id}", tags=["Repository & Context"])


@router.post("/github/connect")
async def connect_github(
    project_id: uuid.UUID,
    data: GitHubConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await RepositoryService.connect_github(db, current_user.id, project_id, data.github_token)


@router.get("/repositories")
async def list_available_repositories(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await RepositoryService.list_available_repositories(db, current_user.id, project_id)


@router.post("/repositories/select", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def select_repository(
    project_id: uuid.UUID,
    data: RepositorySelectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RepositoryRead:
    return await RepositoryService.select_repository(db, current_user.id, project_id, data)


@router.post("/repositories/{repository_id}/ingest", response_model=IngestTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingest(
    project_id: uuid.UUID,
    repository_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IngestTriggerResponse:
    return await RepositoryService.trigger_ingestion(db, current_user.id, project_id, repository_id)


@router.get("/ingestions/{ingestion_id}", response_model=SnapshotRead)
async def get_ingestion_status(
    project_id: uuid.UUID,
    ingestion_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SnapshotRead:
    return await RepositoryService.get_ingestion_status(db, current_user.id, project_id, ingestion_id)


@router.get("/repository", response_model=ProjectRepositoryContext)
async def get_repository_context(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRepositoryContext:
    return await RepositoryService.get_repository_context(db, current_user.id, project_id)


@router.get("/files", response_model=list[FileRead])
async def list_files(
    project_id: uuid.UUID,
    limit: int = Query(default=500, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FileRead]:
    return await RepositoryService.list_files(db, current_user.id, project_id, limit=limit)


@router.get("/files/{file_id}", response_model=FileDetailRead)
async def get_file_detail(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileDetailRead:
    return await RepositoryService.get_file_detail(db, current_user.id, project_id, file_id)


@router.get("/symbols", response_model=list[SymbolRead])
async def list_symbols(
    project_id: uuid.UUID,
    limit: int = Query(default=500, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SymbolRead]:
    return await RepositoryService.list_symbols(db, current_user.id, project_id, limit=limit)


@router.get("/dependencies", response_model=list[DependencyRead])
async def list_dependencies(
    project_id: uuid.UUID,
    limit: int = Query(default=500, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DependencyRead]:
    return await RepositoryService.list_dependencies(db, current_user.id, project_id, limit=limit)


@router.post("/repository/reindex", response_model=IngestTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def reindex_repository(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IngestTriggerResponse:
    ctx = await RepositoryService.get_repository_context(db, current_user.id, project_id)
    if not ctx.repository:
        from apps.api.src.api.exceptions import NotFoundException
        raise NotFoundException(code="NO_CONNECTED_REPOSITORY", message="No repository connected to re-index")
    return await RepositoryService.trigger_ingestion(db, current_user.id, project_id, ctx.repository.id)
