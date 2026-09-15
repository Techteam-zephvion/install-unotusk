import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import BadRequestException, ForbiddenException, NotFoundException
from apps.api.src.models.discovery_run import DiscoveryRun
from apps.api.src.models.enums import (
    DiscoveryJobStatus,
    FindingCategory,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    SnapshotStatus,
)
from apps.api.src.models.finding import Finding
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.discovery import (
    DiscoverSummaryResponse,
    DiscoveryRunResponse,
    DiscoveryTriggerResponse,
    FindingResponse,
)
from apps.api.src.workers.dispatcher import TaskDispatcher


def utc_now() -> datetime:
    return datetime.now(UTC)


class DiscoveryService:
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
            # Check if project exists
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
                message="No ingested repository snapshot found. Ingest the repository before running discovery.",
            )
        return snapshot

    @classmethod
    async def list_findings(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        category: FindingCategory | None = None,
        severity: FindingSeverity | None = None,
        status: FindingStatus | None = None,
        confidence: FindingConfidence | None = None,
    ) -> list[FindingResponse]:
        await cls._verify_project_access(session, user_id, project_id)

        stmt = select(Finding).where(Finding.project_id == project_id)
        if category:
            stmt = stmt.where(Finding.category == category)
        if severity:
            stmt = stmt.where(Finding.severity == severity)
        if status:
            stmt = stmt.where(Finding.status == status)
        if confidence:
            stmt = stmt.where(Finding.confidence == confidence)

        stmt = stmt.order_by(desc(Finding.score), desc(Finding.created_at))
        res = await session.execute(stmt)
        findings = res.scalars().all()
        return [FindingResponse.model_validate(f) for f in findings]

    @classmethod
    async def get_finding(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        finding_id: uuid.UUID,
    ) -> FindingResponse:
        await cls._verify_project_access(session, user_id, project_id)

        stmt = select(Finding).where(
            Finding.id == finding_id,
            Finding.project_id == project_id,
        )
        res = await session.execute(stmt)
        finding = res.scalar_one_or_none()
        if finding is None:
            raise NotFoundException(
                code="FINDING_NOT_FOUND",
                message="Discovery finding not found",
            )
        return FindingResponse.model_validate(finding)

    @classmethod
    async def update_finding_status(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        finding_id: uuid.UUID,
        status: FindingStatus,
    ) -> FindingResponse:
        await cls._verify_project_access(session, user_id, project_id)

        stmt = select(Finding).where(
            Finding.id == finding_id,
            Finding.project_id == project_id,
        )
        res = await session.execute(stmt)
        finding = res.scalar_one_or_none()
        if finding is None:
            raise NotFoundException(
                code="FINDING_NOT_FOUND",
                message="Discovery finding not found",
            )

        finding.status = status
        finding.updated_at = utc_now()
        await session.commit()
        await session.refresh(finding)
        return FindingResponse.model_validate(finding)

    @classmethod
    async def trigger_discovery(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> DiscoveryTriggerResponse:
        await cls._verify_project_access(session, user_id, project_id)
        snapshot = await cls._get_active_snapshot(session, project_id)

        # Create discovery run record
        discovery_run = DiscoveryRun(
            id=uuid.uuid4(),
            project_id=project_id,
            snapshot_id=snapshot.id,
            status=DiscoveryJobStatus.QUEUED,
            progress=0,
            findings_count=0,
            started_at=utc_now(),
        )
        session.add(discovery_run)
        await session.commit()

        # Enqueue discovery task to Redis
        try:
            task_id = await TaskDispatcher.enqueue(
                task_name="discover_project",
                payload={
                    "project_id": str(project_id),
                    "snapshot_id": str(snapshot.id),
                    "discovery_run_id": str(discovery_run.id),
                },
            )
        except Exception:
            # If redis is unreachable or in direct synchronous mode, run immediately
            from apps.api.src.services.discovery_engine.engine import ProjectDiscoveryEngine

            await ProjectDiscoveryEngine.run_discovery(
                project_id=project_id,
                snapshot_id=snapshot.id,
                discovery_run_id=discovery_run.id,
                session=session,
            )
            task_id = str(uuid.uuid4())

        return DiscoveryTriggerResponse(
            task_id=task_id,
            discovery_run_id=discovery_run.id,
            status=DiscoveryJobStatus.QUEUED,
            message="Project discovery analysis successfully queued",
        )

    @classmethod
    async def get_discovery_summary(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> DiscoverSummaryResponse:
        await cls._verify_project_access(session, user_id, project_id)

        # Count open findings by severity
        count_stmt = (
            select(Finding.severity, func.count(Finding.id))
            .where(Finding.project_id == project_id, Finding.status == FindingStatus.OPEN)
            .group_by(Finding.severity)
        )
        res = await session.execute(count_stmt)
        counts = dict(res.all())

        crit_count = counts.get(FindingSeverity.CRITICAL, 0)
        high_count = counts.get(FindingSeverity.HIGH, 0)
        med_count = counts.get(FindingSeverity.MEDIUM, 0)
        low_count = counts.get(FindingSeverity.LOW, 0) + counts.get(FindingSeverity.INFO, 0)
        total = sum(counts.values())

        # Fetch latest discovery run
        latest_run_stmt = (
            select(DiscoveryRun)
            .where(DiscoveryRun.project_id == project_id)
            .order_by(desc(DiscoveryRun.created_at))
            .limit(1)
        )
        run_res = await session.execute(latest_run_stmt)
        latest_run = run_res.scalar_one_or_none()

        return DiscoverSummaryResponse(
            total_findings=total,
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            latest_run=DiscoveryRunResponse.model_validate(latest_run) if latest_run else None,
        )
