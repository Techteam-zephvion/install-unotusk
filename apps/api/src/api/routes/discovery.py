import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.enums import (
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
)
from apps.api.src.models.user import User
from apps.api.src.schemas.discovery import (
    DiscoverSummaryResponse,
    DiscoveryTriggerResponse,
    FindingResponse,
    FindingUpdateStatusRequest,
)
from apps.api.src.services.discovery_service import DiscoveryService

router = APIRouter()


@router.get(
    "/projects/{project_id}/findings",
    response_model=list[FindingResponse],
    status_code=status.HTTP_200_OK,
    summary="List all findings discovered for a project",
)
async def list_findings(
    project_id: uuid.UUID,
    category: FindingCategory | None = Query(None, description="Filter by finding category"),
    severity: FindingSeverity | None = Query(None, description="Filter by finding severity"),
    status: FindingStatus | None = Query(None, description="Filter by finding status"),
    confidence: FindingConfidence | None = Query(None, description="Filter by finding confidence"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FindingResponse]:
    return await DiscoveryService.list_findings(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        category=category,
        severity=severity,
        status=status,
        confidence=confidence,
    )


@router.get(
    "/projects/{project_id}/findings/{finding_id}",
    response_model=FindingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detail of a specific finding",
)
async def get_finding(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    return await DiscoveryService.get_finding(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        finding_id=finding_id,
    )


@router.patch(
    "/projects/{project_id}/findings/{finding_id}",
    response_model=FindingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update finding status (OPEN, ACKNOWLEDGED, DISMISSED, RESOLVED)",
)
async def update_finding_status(
    project_id: uuid.UUID,
    finding_id: uuid.UUID,
    payload: FindingUpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FindingResponse:
    return await DiscoveryService.update_finding_status(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        finding_id=finding_id,
        status=payload.status,
    )


@router.post(
    "/projects/{project_id}/discover",
    response_model=DiscoveryTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger proactive project discovery analysis",
)
async def trigger_discovery(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscoveryTriggerResponse:
    return await DiscoveryService.trigger_discovery(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/discover/status",
    response_model=DiscoverSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get discovery overview, finding counts, and latest run status",
)
async def get_discovery_status(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DiscoverSummaryResponse:
    return await DiscoveryService.get_discovery_summary(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
    )
