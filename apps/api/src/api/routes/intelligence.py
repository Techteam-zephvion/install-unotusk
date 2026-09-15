import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.user import User
from apps.api.src.schemas.intelligence import (
    ContextSearchRequest,
    ContextSearchResponse,
    ConversationCreate,
    ConversationRead,
    GroundedAnswerResponse,
    GroundedAskRequest,
    MessageRead,
)
from apps.api.src.services.intelligence_service import IntelligenceService

router = APIRouter()


@router.post(
    "/projects/{project_id}/ask",
    response_model=GroundedAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a grounded question about the project",
)
async def ask_project(
    project_id: uuid.UUID,
    payload: GroundedAskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroundedAnswerResponse:
    return await IntelligenceService.ask_question(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        question=payload.question,
        conversation_id=payload.conversation_id,
    )


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread for the project",
)
async def create_conversation(
    project_id: uuid.UUID,
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationRead:
    return await IntelligenceService.create_conversation(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        title=payload.title,
        initial_question=payload.initial_question,
    )


@router.get(
    "/projects/{project_id}/conversations",
    response_model=list[ConversationRead],
    summary="List all conversation threads for a project",
)
async def list_conversations(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationRead]:
    return await IntelligenceService.list_conversations(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/conversations/{conversation_id}",
    response_model=list[MessageRead],
    summary="Get all messages and evidence for a conversation",
)
async def get_conversation_messages(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    return await IntelligenceService.get_conversation_messages(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        conversation_id=conversation_id,
    )


@router.post(
    "/projects/{project_id}/conversations/{conversation_id}/messages",
    response_model=GroundedAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Post a user message to a conversation thread and generate a grounded response",
)
async def post_conversation_message(
    project_id: uuid.UUID,
    conversation_id: uuid.UUID,
    payload: GroundedAskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroundedAnswerResponse:
    return await IntelligenceService.ask_question(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        question=payload.question,
        conversation_id=conversation_id,
    )


@router.post(
    "/projects/{project_id}/context/search",
    response_model=ContextSearchResponse,
    summary="Developer debug endpoint for Context Engine retrieval & ranking signals",
    description="Available in development/test environments only. Returns 403 in production.",
)
async def debug_search_context(
    project_id: uuid.UUID,
    payload: ContextSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ContextSearchResponse:
    from fastapi import HTTPException

    from apps.api.src.config.settings import settings

    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=403,
            detail="Debug endpoints are not available in production deployments.",
        )
    return await IntelligenceService.debug_search_context(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        query=payload.query,
    )
