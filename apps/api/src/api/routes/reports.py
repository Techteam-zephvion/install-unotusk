import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.models.user import User
from apps.api.src.schemas.report import (
    ReportListItemResponse,
    ReportResponse,
    ReportTriggerResponse,
)
from apps.api.src.services.report_service import ReportService

router = APIRouter()


@router.post(
    "/projects/{project_id}/reports",
    response_model=ReportTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate a new project intelligence report",
)
async def generate_report(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportTriggerResponse:
    return await ReportService.trigger_report(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/reports",
    response_model=list[ReportListItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List all intelligence reports generated for a project",
)
async def list_reports(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReportListItemResponse]:
    return await ReportService.list_reports(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/reports/latest",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the latest intelligence report for a project",
)
async def get_latest_report(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    return await ReportService.get_latest_report(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
    )


@router.get(
    "/projects/{project_id}/reports/{report_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a specific intelligence report by ID",
)
async def get_report(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    return await ReportService.get_report(
        session=db,
        user_id=current_user.id,
        project_id=project_id,
        report_id=report_id,
    )
