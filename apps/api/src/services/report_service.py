import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import BadRequestException, ForbiddenException, NotFoundException
from apps.api.src.models.discovery_run import DiscoveryRun
from apps.api.src.models.enums import ReportStatus, SnapshotStatus
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.project import Project
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.report import (
    ReportListItemResponse,
    ReportResponse,
    ReportTriggerResponse,
)
from apps.api.src.workers.dispatcher import TaskDispatcher


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReportService:
    @staticmethod
    async def _verify_project_access(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Project:
        stmt = (
            select(Project)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Project.organization_id,
            )
            .where(
                Project.id == project_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        res = await session.execute(stmt)
        project = res.scalar_one_or_none()
        if project is None:
            exists_stmt = select(Project).where(Project.id == project_id)
            exists_res = await session.execute(exists_stmt)
            if exists_res.scalar_one_or_none() is not None:
                raise ForbiddenException(
                    code="ORGANIZATION_ACCESS_DENIED",
                    message="You do not have access to this project",
                )
            raise NotFoundException(
                code="PROJECT_NOT_FOUND",
                message="Project does not exist",
            )
        return project

    @staticmethod
    async def _get_active_snapshot(
        session: AsyncSession,
        project_id: uuid.UUID,
    ) -> RepositorySnapshot:
        stmt = (
            select(RepositorySnapshot)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(
                Repository.project_id == project_id,
                RepositorySnapshot.status == SnapshotStatus.COMPLETED,
            )
            .order_by(desc(RepositorySnapshot.created_at))
            .limit(1)
        )
        res = await session.execute(stmt)
        snapshot = res.scalar_one_or_none()
        if snapshot is None:
            raise BadRequestException(
                code="NO_COMPLETED_SNAPSHOT",
                message="No ingested repository snapshot found. Ingest the repository before generating a report.",
            )
        return snapshot

    @classmethod
    async def trigger_report(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ReportTriggerResponse:
        await cls._verify_project_access(session, user_id, project_id)
        snapshot = await cls._get_active_snapshot(session, project_id)

        # Look for latest discovery run
        run_stmt = (
            select(DiscoveryRun)
            .where(
                DiscoveryRun.project_id == project_id,
                DiscoveryRun.snapshot_id == snapshot.id,
            )
            .order_by(desc(DiscoveryRun.created_at))
            .limit(1)
        )
        run_res = await session.execute(run_stmt)
        discovery_run = run_res.scalar_one_or_none()

        # Create queued report record
        report = ProjectIntelligenceReport(
            id=uuid.uuid4(),
            project_id=project_id,
            snapshot_id=snapshot.id,
            discovery_run_id=discovery_run.id if discovery_run else None,
            status=ReportStatus.QUEUED,
            report_version="1.0.0",
            summary="",
            report_data={},
            generated_at=utc_now(),
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)

        # Dispatch background task
        task_id = await TaskDispatcher.enqueue(
            "generate_report",
            {
                "project_id": str(project_id),
                "snapshot_id": str(snapshot.id),
                "discovery_run_id": str(discovery_run.id) if discovery_run else None,
                "report_id": str(report.id),
            },
        )

        return ReportTriggerResponse(
            task_id=task_id,
            report_id=report.id,
            status=ReportStatus.QUEUED,
            message="Project intelligence report generation task enqueued.",
        )

    @classmethod
    async def list_reports(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> list[ReportListItemResponse]:
        await cls._verify_project_access(session, user_id, project_id)
        stmt = (
            select(ProjectIntelligenceReport)
            .where(ProjectIntelligenceReport.project_id == project_id)
            .order_by(desc(ProjectIntelligenceReport.created_at))
        )
        res = await session.execute(stmt)
        reports = res.scalars().all()
        return [ReportListItemResponse.model_validate(r) for r in reports]

    @classmethod
    async def get_latest_report(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ReportResponse:
        await cls._verify_project_access(session, user_id, project_id)
        stmt = (
            select(ProjectIntelligenceReport)
            .where(
                ProjectIntelligenceReport.project_id == project_id,
                ProjectIntelligenceReport.status == ReportStatus.COMPLETED,
            )
            .order_by(desc(ProjectIntelligenceReport.generated_at))
            .limit(1)
        )
        res = await session.execute(stmt)
        report = res.scalar_one_or_none()
        if report is None:
            # Check if there is a generating/queued report
            pending_stmt = (
                select(ProjectIntelligenceReport)
                .where(ProjectIntelligenceReport.project_id == project_id)
                .order_by(desc(ProjectIntelligenceReport.created_at))
                .limit(1)
            )
            pending_res = await session.execute(pending_stmt)
            pending = pending_res.scalar_one_or_none()
            if pending:
                return ReportResponse.model_validate(pending)
            raise NotFoundException(
                code="REPORT_NOT_FOUND",
                message="No intelligence reports have been generated yet for this project.",
            )
        return ReportResponse.model_validate(report)

    @classmethod
    async def get_report(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> ReportResponse:
        await cls._verify_project_access(session, user_id, project_id)
        stmt = select(ProjectIntelligenceReport).where(
            ProjectIntelligenceReport.id == report_id,
            ProjectIntelligenceReport.project_id == project_id,
        )
        res = await session.execute(stmt)
        report = res.scalar_one_or_none()
        if report is None:
            raise NotFoundException(
                code="REPORT_NOT_FOUND",
                message=f"Report with ID '{report_id}' was not found for this project.",
            )
        return ReportResponse.model_validate(report)
