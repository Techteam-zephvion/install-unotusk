import uuid
from collections import defaultdict

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.discovery_run import DiscoveryRun
from apps.api.src.models.enums import FindingCategory, FindingStatus, KnowledgeStatus
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.finding import Finding
from apps.api.src.models.knowledge import ProjectKnowledge
from apps.api.src.models.project import Project
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.report_engine.base import FactData


class FactBuilder:
    @staticmethod
    async def build_facts(
        session: AsyncSession,
        project_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        discovery_run_id: uuid.UUID | None = None,
    ) -> FactData:
        # 1. Project & Snapshot
        project_stmt = select(Project).where(Project.id == project_id)
        project_res = await session.execute(project_stmt)
        project = project_res.scalar_one()

        snapshot_stmt = select(RepositorySnapshot).where(RepositorySnapshot.id == snapshot_id)
        snapshot_res = await session.execute(snapshot_stmt)
        snapshot = snapshot_res.scalar_one()

        # 2. Files
        files_stmt = (
            select(RepositoryFile)
            .where(RepositoryFile.snapshot_id == snapshot_id)
            .order_by(RepositoryFile.path)
        )
        files_res = await session.execute(files_stmt)
        files = list(files_res.scalars().all())

        file_by_id = {f.id: f for f in files}
        file_by_path = {f.path: f for f in files}

        # Metrics
        language_counts: dict[str, int] = defaultdict(int)
        total_lines = 0
        total_bytes = 0
        for f in files:
            if f.language:
                language_counts[f.language] += 1
            total_lines += f.line_count or 0
            total_bytes += f.size_bytes or 0

        # 3. Symbols
        file_ids = [f.id for f in files]
        symbols: list[CodeSymbol] = []
        dependencies: list[CodeDependency] = []

        if file_ids:
            symbols_stmt = (
                select(CodeSymbol).where(CodeSymbol.file_id.in_(file_ids)).order_by(CodeSymbol.name)
            )
            symbols_res = await session.execute(symbols_stmt)
            symbols = list(symbols_res.scalars().all())

            # 4. Dependencies
            deps_stmt = (
                select(CodeDependency)
                .where(CodeDependency.source_file_id.in_(file_ids))
                .order_by(CodeDependency.line_number)
            )
            deps_res = await session.execute(deps_stmt)
            dependencies = list(deps_res.scalars().all())

        # 5. Findings
        findings_stmt = (
            select(Finding)
            .where(
                Finding.project_id == project_id,
                Finding.snapshot_id == snapshot_id,
                Finding.status != FindingStatus.DISMISSED,
            )
            .order_by(desc(Finding.score))
        )
        findings_res = await session.execute(findings_stmt)
        findings = list(findings_res.scalars().all())

        # 6. Discovery Run
        discovery_run = None
        if discovery_run_id:
            run_stmt = select(DiscoveryRun).where(DiscoveryRun.id == discovery_run_id)
            run_res = await session.execute(run_stmt)
            discovery_run = run_res.scalar_one_or_none()
        elif findings and findings[0].discovery_run_id:
            run_stmt = select(DiscoveryRun).where(DiscoveryRun.id == findings[0].discovery_run_id)
            run_res = await session.execute(run_stmt)
            discovery_run = run_res.scalar_one_or_none()
        else:
            latest_run_stmt = (
                select(DiscoveryRun)
                .where(
                    DiscoveryRun.project_id == project_id, DiscoveryRun.snapshot_id == snapshot_id
                )
                .order_by(desc(DiscoveryRun.created_at))
                .limit(1)
            )
            latest_run_res = await session.execute(latest_run_stmt)
            discovery_run = latest_run_res.scalar_one_or_none()

        # 7. Compute Dependency & Consumer Maps
        file_consumers: dict[str, set[str]] = defaultdict(set)
        external_packages: set[str] = set()

        for dep in dependencies:
            src_file = file_by_id.get(dep.source_file_id)
            src_path = src_file.path if src_file else "unknown"

            if dep.external_package:
                external_packages.add(dep.external_package)

            target_path = None
            if dep.target_file_id and dep.target_file_id in file_by_id:
                target_path = file_by_id[dep.target_file_id].path
            elif dep.external_package:
                candidate = dep.external_package.replace(".", "/")
                for path in file_by_path:
                    if candidate in path:
                        target_path = path
                        break

            if target_path and target_path != src_path:
                file_consumers[target_path].add(src_path)

        # 8. Compute Symbol Consumer Estimates
        symbol_consumers: dict[str, int] = defaultdict(int)
        for sym in symbols:
            # Check findings for exact consumer counts from coupling analyzer
            for f in findings:
                if f.category == FindingCategory.COUPLING and sym.name in f.title:
                    for ev in f.evidence:
                        if ev.get("symbol") == sym.name and "consumers_count" in ev:
                            symbol_consumers[sym.name] = int(ev["consumers_count"])
                            break
            # If not in findings, default to file consumers of its defining file
            if sym.name not in symbol_consumers and sym.file_id in file_by_id:
                sym_file_path = file_by_id[sym.file_id].path
                symbol_consumers[sym.name] = len(file_consumers.get(sym_file_path, set()))

        # 9. Extract Cycles from findings
        cycles: list[list[str]] = []
        for f in findings:
            if f.category == FindingCategory.CIRCULAR_DEPENDENCY:
                for ev in f.evidence:
                    if "cycle" in ev and isinstance(ev["cycle"], list):
                        cycles.append(ev["cycle"])
                    elif "target" in ev and "file" in ev:
                        cycles.append([ev["file"], ev["target"]])

        # 10. Load Active Customer Knowledge
        knowledge_stmt = select(ProjectKnowledge).where(
            ProjectKnowledge.project_id == project_id,
            ProjectKnowledge.status == KnowledgeStatus.ACTIVE,
        )
        knowledge_res = await session.execute(knowledge_stmt)
        knowledge_items = list(knowledge_res.scalars().all())

        return FactData(
            project=project,
            snapshot=snapshot,
            files=files,
            symbols=symbols,
            dependencies=dependencies,
            findings=findings,
            discovery_run=discovery_run,
            language_counts=dict(language_counts),
            total_lines=total_lines,
            total_bytes=total_bytes,
            file_by_id=file_by_id,
            file_by_path=file_by_path,
            file_consumers=file_consumers,
            symbol_consumers=dict(symbol_consumers),
            external_packages=external_packages,
            cycles=cycles,
            knowledge_items=knowledge_items,
        )
