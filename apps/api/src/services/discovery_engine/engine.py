import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.db.session import AsyncSessionLocal
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.discovery_run import DiscoveryRun
from apps.api.src.models.enums import DiscoveryJobStatus, FindingStatus, KnowledgeStatus
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.finding import Finding
from apps.api.src.models.knowledge import ProjectKnowledge
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.discovery_engine.architecture_analyzer import ArchitectureAnalyzer
from apps.api.src.services.discovery_engine.base import CandidateFinding, DiscoveryContext
from apps.api.src.services.discovery_engine.change_risk_analyzer import ChangeRiskAnalyzer
from apps.api.src.services.discovery_engine.circular_dependency_analyzer import (
    CircularDependencyAnalyzer,
)
from apps.api.src.services.discovery_engine.coupling_analyzer import CouplingAnalyzer
from apps.api.src.services.discovery_engine.deduplicator import deduplicate_findings
from apps.api.src.services.discovery_engine.documentation_gap_analyzer import (
    DocumentationGapAnalyzer,
)
from apps.api.src.services.discovery_engine.duplication_analyzer import DuplicationAnalyzer
from apps.api.src.services.discovery_engine.legacy_analyzer import LegacyAnalyzer
from apps.api.src.services.discovery_engine.ranker import rank_findings
from apps.api.src.services.discovery_engine.synthesizer import FindingSynthesizer
from apps.api.src.services.discovery_engine.test_gap_analyzer import TestGapAnalyzer
from apps.api.src.services.discovery_engine.unused_code_analyzer import UnusedCodeAnalyzer

logger = logging.getLogger("unotusk-discovery")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProjectDiscoveryEngine:
    @classmethod
    async def run_discovery(
        cls,
        project_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        discovery_run_id: uuid.UUID | None = None,
        session: AsyncSession | None = None,
    ) -> list[Finding]:
        """Execute all analyzers, rank candidates, and persist discoveries."""
        if session is not None:
            return await cls._execute_pipeline(session, project_id, snapshot_id, discovery_run_id)

        async with AsyncSessionLocal() as db:
            return await cls._execute_pipeline(db, project_id, snapshot_id, discovery_run_id)

    @classmethod
    async def _execute_pipeline(
        cls,
        session: AsyncSession,
        project_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        discovery_run_id: uuid.UUID | None = None,
    ) -> list[Finding]:
        logger.info(f"Starting Project Discovery for project={project_id}, snapshot={snapshot_id}")

        # 1. Fetch or create DiscoveryRun record
        discovery_run = None
        if discovery_run_id:
            run_query = select(DiscoveryRun).where(DiscoveryRun.id == discovery_run_id)
            run_res = await session.execute(run_query)
            discovery_run = run_res.scalar_one_or_none()

        if discovery_run is None:
            discovery_run = DiscoveryRun(
                id=discovery_run_id or uuid.uuid4(),
                project_id=project_id,
                snapshot_id=snapshot_id,
                status=DiscoveryJobStatus.ANALYZING,
                progress=10,
                findings_count=0,
                started_at=utc_now(),
            )
            session.add(discovery_run)
        else:
            discovery_run.status = DiscoveryJobStatus.ANALYZING
            discovery_run.progress = 10
        await session.commit()

        try:
            # 2. Load Snapshot Data from DB
            files_q = select(RepositoryFile).where(RepositoryFile.snapshot_id == snapshot_id)
            files_res = await session.execute(files_q)
            files = list(files_res.scalars().all())

            symbols_q = (
                select(CodeSymbol)
                .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                .where(RepositoryFile.snapshot_id == snapshot_id)
            )
            symbols_res = await session.execute(symbols_q)
            symbols = list(symbols_res.scalars().all())

            deps_q = (
                select(CodeDependency)
                .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
                .where(RepositoryFile.snapshot_id == snapshot_id)
            )
            deps_res = await session.execute(deps_q)
            deps = list(deps_res.scalars().all())

            chunks_q = select(CodeChunk).where(CodeChunk.snapshot_id == snapshot_id)
            chunks_res = await session.execute(chunks_q)
            chunks = list(chunks_res.scalars().all())

            # 3. Assemble DiscoveryContext
            ctx = DiscoveryContext(
                project_id=project_id,
                snapshot_id=snapshot_id,
                files=files,
                symbols=symbols,
                dependencies=deps,
                chunks=chunks,
            )

            discovery_run.progress = 25
            await session.commit()

            # 4. Instantiate Analyzers
            analyzers = [
                CircularDependencyAnalyzer(),
                CouplingAnalyzer(),
                ChangeRiskAnalyzer(),
                UnusedCodeAnalyzer(),
                DocumentationGapAnalyzer(),
                DuplicationAnalyzer(),
                ArchitectureAnalyzer(),
                LegacyAnalyzer(),
                TestGapAnalyzer(),
            ]

            # 5. Run Analyzers
            candidate_lists = await asyncio.gather(
                *[analyzer.analyze(ctx) for analyzer in analyzers],
                return_exceptions=True,
            )

            all_candidates: list[CandidateFinding] = []
            for i, res in enumerate(candidate_lists):
                if isinstance(res, Exception):
                    logger.error(
                        f"Analyzer {analyzers[i].__class__.__name__} failed: {res}", exc_info=True
                    )
                elif isinstance(res, list):
                    all_candidates.extend(res)

            discovery_run.progress = 60
            await session.commit()

            # 6. Deduplicate & Rank
            deduped = deduplicate_findings(all_candidates)
            ranked = rank_findings(deduped)

            discovery_run.status = DiscoveryJobStatus.FINALIZING
            discovery_run.progress = 80
            await session.commit()

            # 7. Synthesize Explanations & Recommendations (incorporating Customer Knowledge)
            knowledge_q = select(ProjectKnowledge).where(
                ProjectKnowledge.project_id == project_id,
                ProjectKnowledge.status == KnowledgeStatus.ACTIVE,
            )
            knowledge_res = await session.execute(knowledge_q)
            active_knowledge = list(knowledge_res.scalars().all())

            synthesizer = FindingSynthesizer()
            final_candidates = await synthesizer.enhance_recommendations(
                ranked, active_knowledge=active_knowledge
            )

            # 8. Persist Findings
            # Clean up older OPEN findings for this snapshot so rerunning replaces them
            del_stmt = (
                delete(Finding)
                .where(Finding.snapshot_id == snapshot_id)
                .where(Finding.status == FindingStatus.OPEN)
            )
            await session.execute(del_stmt)

            created_findings: list[Finding] = []
            for c in final_candidates:
                safe_title = c.title if len(c.title) <= 255 else (c.title[:251] + "...")
                finding = Finding(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    discovery_run_id=discovery_run.id,
                    category=c.category,
                    title=safe_title,
                    description=c.description,
                    why_it_matters=c.why_it_matters,
                    severity=c.severity,
                    confidence=c.confidence,
                    status=FindingStatus.OPEN,
                    score=c.score,
                    recommendation=c.recommendation,
                    evidence=c.evidence,
                    related_entities=c.related_entities,
                    finding_metadata=c.metadata,
                )
                session.add(finding)
                created_findings.append(finding)

            discovery_run.status = DiscoveryJobStatus.COMPLETED
            discovery_run.progress = 100
            discovery_run.findings_count = len(created_findings)
            discovery_run.completed_at = utc_now()
            await session.commit()

            logger.info(
                f"Discovery completed successfully for project {project_id}: "
                f"{len(created_findings)} findings saved."
            )
            return created_findings

        except Exception as e:
            logger.error(f"Discovery pipeline failed: {e}", exc_info=True)
            try:
                await session.rollback()
                discovery_run.status = DiscoveryJobStatus.FAILED
                discovery_run.error_message = str(e)[:1000]
                discovery_run.completed_at = utc_now()
                await session.commit()
            except Exception as commit_err:
                logger.error(f"Failed to record discovery failure status: {commit_err}")
            raise
