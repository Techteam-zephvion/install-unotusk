import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.enums import KnowledgeCategory, KnowledgeStatus
from apps.api.src.models.user import User
from apps.api.src.schemas.knowledge import (
    KnowledgeCreateRequest,
    KnowledgeListResponse,
    KnowledgeResponse,
    KnowledgeUpdateRequest,
)
from apps.api.src.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["knowledge"])


@router.post("", response_model=KnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_project_knowledge(
    project_id: uuid.UUID,
    request: KnowledgeCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    return await KnowledgeService.create_knowledge(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        data=request,
    )


@router.get("", response_model=KnowledgeListResponse)
async def list_project_knowledge(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: KnowledgeStatus | None = Query(None, description="Filter by status"),
    category: KnowledgeCategory | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search term across title, content, symbols"),
) -> KnowledgeListResponse:
    items = await KnowledgeService.list_knowledge(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        status=status,
        category=category,
        search=search,
    )
    return KnowledgeListResponse(items=items, total=len(items))


@router.get("/{knowledge_id}", response_model=KnowledgeResponse)
async def get_project_knowledge(
    project_id: uuid.UUID,
    knowledge_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    return await KnowledgeService.get_knowledge(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        knowledge_id=knowledge_id,
    )


@router.patch("/{knowledge_id}", response_model=KnowledgeResponse)
async def update_project_knowledge(
    project_id: uuid.UUID,
    knowledge_id: uuid.UUID,
    request: KnowledgeUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    return await KnowledgeService.update_knowledge(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        knowledge_id=knowledge_id,
        data=request,
    )


@router.post("/{knowledge_id}/archive", response_model=KnowledgeResponse)
async def archive_project_knowledge(
    project_id: uuid.UUID,
    knowledge_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    return await KnowledgeService.archive_knowledge(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        knowledge_id=knowledge_id,
    )


@router.post("/{knowledge_id}/restore", response_model=KnowledgeResponse)
async def restore_project_knowledge(
    project_id: uuid.UUID,
    knowledge_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeResponse:
    return await KnowledgeService.restore_knowledge(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        knowledge_id=knowledge_id,
    )
