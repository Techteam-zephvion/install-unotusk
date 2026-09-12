import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.session import AsyncSessionLocal
from apps.api.src.models.enums import ReportStatus
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.services.report_engine.fact_builder import FactBuilder
from apps.api.src.services.report_engine.interpretation_engine import InterpretationEngine
from apps.api.src.services.report_engine.synthesizer import ClaudeReportSynthesizer

logger = logging.getLogger("unotusk-report")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectReportEngine:
    @classmethod
    async def generate_report(
        cls,
        project_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        discovery_run_id: uuid.UUID | None = None,
        report_id: uuid.UUID | None = None,
        session: AsyncSession | None = None,
    ) -> ProjectIntelligenceReport:
        if session is not None:
            return await cls._execute_generation(
                session=session,
                project_id=project_id,
                snapshot_id=snapshot_id,
                discovery_run_id=discovery_run_id,
                report_id=report_id,
            )

        async with AsyncSessionLocal() as db:
            return await cls._execute_generation(
                session=db,
                project_id=project_id,
                snapshot_id=snapshot_id,
                discovery_run_id=discovery_run_id,
                report_id=report_id,
            )

    @classmethod
    async def _execute_generation(
        cls,
        session: AsyncSession,
        project_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        discovery_run_id: uuid.UUID | None = None,
        report_id: uuid.UUID | None = None,
    ) -> ProjectIntelligenceReport:
        logger.info(f"Starting Project Intelligence Report generation for project {project_id}")

        # 1. Fetch or create report record
        report: ProjectIntelligenceReport
        if report_id:
            stmt = select(ProjectIntelligenceReport).where(ProjectIntelligenceReport.id == report_id)
            res = await session.execute(stmt)
            report = res.scalar_one()
            report.status = ReportStatus.GENERATING
        else:
            report = ProjectIntelligenceReport(
                id=uuid.uuid4(),
                project_id=project_id,
                snapshot_id=snapshot_id,
                discovery_run_id=discovery_run_id,
                status=ReportStatus.GENERATING,
                report_version="1.0.0",
                summary="",
                report_data={},
                generated_at=utc_now(),
            )
            session.add(report)

        await session.commit()
        await session.refresh(report)

        try:
            # 2. Deterministic Fact Building
            facts = await FactBuilder.build_facts(
                session=session,
                project_id=project_id,
                snapshot_id=snapshot_id,
                discovery_run_id=discovery_run_id,
            )

            # 3. Interpretation & Structure Assembly
            doc = InterpretationEngine.build_report_document(facts)

            # 4. Optional Constrained Synthesis with Offline Fallback
            synthesizer = ClaudeReportSynthesizer()
            enhanced_doc = await synthesizer.synthesize(doc)

            # 5. Persist Completed Report
            report.status = ReportStatus.COMPLETED
            report.summary = enhanced_doc.executive_summary.project_summary
            report.report_data = enhanced_doc.model_dump()
            report.generated_at = utc_now()
            report.discovery_run_id = facts.discovery_run.id if facts.discovery_run else None

            await session.commit()
            await session.refresh(report)
            logger.info(f"Report {report.id} completed successfully for project {project_id}")
            return report

        except Exception as exc:
            logger.error(f"Report generation failed for project {project_id}: {exc}", exc_info=True)
            report.status = ReportStatus.FAILED
            report.error_message = str(exc)
            await session.commit()
            await session.refresh(report)
            raise
