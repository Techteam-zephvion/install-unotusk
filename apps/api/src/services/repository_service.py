import os
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import (
    ForbiddenException,
    NotFoundException,
)
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    ProjectStatus,
    SnapshotStatus,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.schemas.context import (
    CodeChunkRead,
    DependencyRead,
    FileDetailRead,
    FileRead,
    ProjectContextMetrics,
    ProjectRepositoryContext,
    SymbolRead,
)
from apps.api.src.schemas.repository import RepositoryRead, RepositorySelectRequest
from apps.api.src.schemas.snapshot import IngestTriggerResponse, SnapshotRead
from apps.api.src.services.github_client import GitHubClient
from apps.api.src.workers.dispatcher import TaskDispatcher


class RepositoryService:
    @staticmethod
    async def _verify_project_access(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Project:
        proj_query = select(Project).where(Project.id == project_id)
        proj_res = await session.execute(proj_query)
        project = proj_res.scalar_one_or_none()
        if project is None:
            raise NotFoundException(code="PROJECT_NOT_FOUND", message="Project not found")

        # Verify membership in parent organization
        mem_query = select(OrganizationMembership).where(
            OrganizationMembership.organization_id == project.organization_id,
            OrganizationMembership.user_id == user_id,
        )
        mem_res = await session.execute(mem_query)
        if mem_res.scalar_one_or_none() is None:
            raise ForbiddenException(
                code="ORGANIZATION_ACCESS_DENIED",
                message="You do not have access to this project",
            )

        return project

    @staticmethod
    async def connect_github(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        github_token: str | None = None,
    ) -> dict:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        effective_token = github_token or os.getenv("GITHUB_TOKEN")
        client = GitHubClient(token=effective_token)
        user_profile = await client.verify_token()

        # Find or create integration
        int_query = select(Integration).where(
            Integration.project_id == project.id,
            Integration.provider == IntegrationProvider.GITHUB,
        )
        int_res = await session.execute(int_query)
        integration = int_res.scalar_one_or_none()

        if integration is None:
            integration = Integration(
                project_id=project.id,
                provider=IntegrationProvider.GITHUB,
                status=IntegrationStatus.CONNECTED,
                external_id=str(user_profile.get("id")),
                integration_metadata={
                    "username": user_profile.get("login"),
                    "github_token": effective_token,
                },
            )
            session.add(integration)
        else:
            integration.status = IntegrationStatus.CONNECTED
            integration.external_id = str(user_profile.get("id"))
            integration.integration_metadata = {
                "username": user_profile.get("login"),
                "github_token": effective_token,
            }

        await session.commit()

        return {
            "status": "connected",
            "provider": "GITHUB",
            "username": user_profile.get("login"),
            "integration_id": str(integration.id),
        }

    @staticmethod
    async def list_available_repositories(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> list[dict]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        int_query = select(Integration).where(
            Integration.project_id == project.id,
            Integration.provider == IntegrationProvider.GITHUB,
        )
        int_res = await session.execute(int_query)
        integration = int_res.scalar_one_or_none()

        token = None
        if integration and integration.integration_metadata:
            token = integration.integration_metadata.get("github_token")
        if not token:
            token = os.getenv("GITHUB_TOKEN")

        client = GitHubClient(token=token)
        return await client.list_repositories()

    @staticmethod
    async def select_repository(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        data: RepositorySelectRequest,
    ) -> RepositoryRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        int_query = select(Integration).where(
            Integration.project_id == project.id,
            Integration.provider == IntegrationProvider.GITHUB,
        )
        int_res = await session.execute(int_query)
        integration = int_res.scalar_one_or_none()

        if integration is None:
            integration = Integration(
                project_id=project.id,
                provider=IntegrationProvider.GITHUB,
                status=IntegrationStatus.CONNECTED,
                external_id=data.external_id,
                integration_metadata={},
            )
            session.add(integration)
            await session.flush()

        # Check existing repository record
        repo_query = select(Repository).where(
            Repository.project_id == project.id,
            Repository.external_id == data.external_id,
        )
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalar_one_or_none()

        if repo is None:
            repo = Repository(
                project_id=project.id,
                integration_id=integration.id,
                provider=IntegrationProvider.GITHUB,
                external_id=data.external_id,
                owner=data.owner,
                name=data.name,
                full_name=data.full_name,
                default_branch=data.default_branch,
                url=data.url,
                is_private=data.is_private,
                repo_metadata={"description": data.description},
            )
            session.add(repo)
        else:
            repo.owner = data.owner
            repo.name = data.name
            repo.full_name = data.full_name
            repo.default_branch = data.default_branch
            repo.url = data.url
            repo.is_private = data.is_private

        project.status = ProjectStatus.CONNECTING
        await session.commit()
        await session.refresh(repo)

        return RepositoryRead.model_validate(repo)

    @staticmethod
    async def trigger_ingestion(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        repository_id: uuid.UUID,
        override_local_dir: str | None = None,
    ) -> IngestTriggerResponse:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        repo_query = select(Repository).where(
            Repository.id == repository_id,
            Repository.project_id == project.id,
        )
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalar_one_or_none()
        if repo is None:
            raise NotFoundException(code="REPOSITORY_NOT_FOUND", message="Repository not found")

        # Create new Snapshot
        snapshot = RepositorySnapshot(
            repository_id=repo.id,
            branch=repo.default_branch,
            status=SnapshotStatus.QUEUED,
        )
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)

        # Enqueue background task
        try:
            await TaskDispatcher.enqueue(
                task_name="ingest_repository",
                payload={
                    "snapshot_id": str(snapshot.id),
                    "override_local_dir": override_local_dir,
                },
            )
        except Exception:
            # If Redis connection fails in testing environment, run synchronously as fallback
            from apps.api.src.services.ingestion_service import IngestionService

            await IngestionService.run_ingestion(snapshot.id, override_local_dir=override_local_dir)

        return IngestTriggerResponse(
            snapshot_id=snapshot.id,
            status=SnapshotStatus.QUEUED,
            message="Repository ingestion started successfully",
        )

    @staticmethod
    async def get_ingestion_status(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        ingestion_id: uuid.UUID,
    ) -> SnapshotRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = (
            select(RepositorySnapshot)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(
                RepositorySnapshot.id == ingestion_id,
                Repository.project_id == project.id,
            )
        )
        res = await session.execute(query)
        snapshot = res.scalar_one_or_none()
        if snapshot is None:
            raise NotFoundException(
                code="INGESTION_NOT_FOUND", message="Ingestion snapshot not found"
            )

        return SnapshotRead.model_validate(snapshot)

    @staticmethod
    async def get_repository_context(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ProjectRepositoryContext:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        # Fetch repository
        repo_query = (
            select(Repository)
            .where(Repository.project_id == project.id)
            .order_by(Repository.created_at.desc())
        )
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalars().first()

        if repo is None:
            return ProjectRepositoryContext(repository=None, active_snapshot=None)

        # Fetch latest snapshot
        snap_query = (
            select(RepositorySnapshot)
            .where(RepositorySnapshot.repository_id == repo.id)
            .order_by(RepositorySnapshot.created_at.desc())
        )
        snap_res = await session.execute(snap_query)
        snapshot = snap_res.scalars().first()

        metrics = ProjectContextMetrics()

        if snapshot is not None:
            # Deterministic metrics
            # Total files
            f_count = await session.execute(
                select(func.count(RepositoryFile.id)).where(
                    RepositoryFile.snapshot_id == snapshot.id
                )
            )
            metrics.total_files = f_count.scalar() or 0

            # Language breakdown
            lang_query = (
                select(RepositoryFile.language, func.count(RepositoryFile.id))
                .where(RepositoryFile.snapshot_id == snapshot.id)
                .group_by(RepositoryFile.language)
            )
            lang_res = await session.execute(lang_query)
            dist = {row[0]: row[1] for row in lang_res.all()}
            metrics.language_distribution = dist
            metrics.languages_count = len(dist)

            # Symbols count
            sym_count = await session.execute(
                select(func.count(CodeSymbol.id))
                .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
                .where(RepositoryFile.snapshot_id == snapshot.id)
            )
            metrics.symbols_count = sym_count.scalar() or 0

            # Dependencies count
            dep_count = await session.execute(
                select(func.count(CodeDependency.id))
                .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
                .where(RepositoryFile.snapshot_id == snapshot.id)
            )
            metrics.dependencies_count = dep_count.scalar() or 0

        return ProjectRepositoryContext(
            repository=RepositoryRead.model_validate(repo) if repo else None,
            active_snapshot=SnapshotRead.model_validate(snapshot) if snapshot else None,
            metrics=metrics,
        )

    @staticmethod
    async def list_files(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        limit: int = 500,
    ) -> list[FileRead]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = (
            select(RepositoryFile)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(Repository.project_id == project.id)
            .order_by(RepositorySnapshot.created_at.desc(), RepositoryFile.path.asc())
            .limit(limit)
        )
        res = await session.execute(query)
        files = res.scalars().all()
        return [FileRead.model_validate(f) for f in files]

    @staticmethod
    async def list_symbols(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        limit: int = 500,
    ) -> list[SymbolRead]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = (
            select(CodeSymbol, RepositoryFile.path)
            .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(Repository.project_id == project.id)
            .order_by(RepositorySnapshot.created_at.desc(), CodeSymbol.qualified_name.asc())
            .limit(limit)
        )
        res = await session.execute(query)
        symbols = []
        for sym, file_path in res.all():
            read_obj = SymbolRead.model_validate(sym)
            read_obj.file_path = file_path
            symbols.append(read_obj)
        return symbols

    @staticmethod
    async def list_dependencies(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        limit: int = 500,
    ) -> list[DependencyRead]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        query = (
            select(CodeDependency, RepositoryFile.path)
            .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(Repository.project_id == project.id)
            .order_by(RepositorySnapshot.created_at.desc(), CodeDependency.line_number.asc())
            .limit(limit)
        )
        res = await session.execute(query)
        deps = []
        for dep, source_path in res.all():
            read_obj = DependencyRead.model_validate(dep)
            read_obj.source_path = source_path
            deps.append(read_obj)
        return deps

    @staticmethod
    async def get_file_detail(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> FileDetailRead:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        f_query = (
            select(RepositoryFile)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(
                RepositoryFile.id == file_id,
                Repository.project_id == project.id,
            )
        )
        f_res = await session.execute(f_query)
        file = f_res.scalar_one_or_none()
        if file is None:
            raise NotFoundException(code="FILE_NOT_FOUND", message="File not found in project")

        # Get symbols in this file
        sym_query = (
            select(CodeSymbol)
            .where(CodeSymbol.file_id == file.id)
            .order_by(CodeSymbol.start_line.asc())
        )
        sym_res = await session.execute(sym_query)
        symbols = []
        for s in sym_res.scalars().all():
            read_sym = SymbolRead.model_validate(s)
            read_sym.file_path = file.path
            symbols.append(read_sym)

        # Get outgoing dependencies
        out_dep_query = (
            select(CodeDependency, RepositoryFile.path)
            .outerjoin(RepositoryFile, RepositoryFile.id == CodeDependency.target_file_id)
            .where(CodeDependency.source_file_id == file.id)
            .order_by(CodeDependency.line_number.asc())
        )
        out_res = await session.execute(out_dep_query)
        outgoing_deps = []
        for dep, target_path in out_res.all():
            d = DependencyRead.model_validate(dep)
            d.source_path = file.path
            d.target_path = target_path
            outgoing_deps.append(d)

        # Get incoming references (files that depend on this file)
        in_dep_query = (
            select(CodeDependency, RepositoryFile.path)
            .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
            .where(CodeDependency.target_file_id == file.id)
            .order_by(CodeDependency.line_number.asc())
        )
        in_res = await session.execute(in_dep_query)
        incoming_refs = []
        for dep, source_path in in_res.all():
            d = DependencyRead.model_validate(dep)
            d.source_path = source_path
            d.target_path = file.path
            incoming_refs.append(d)

        # Get code chunks
        chunk_query = (
            select(CodeChunk)
            .where(CodeChunk.file_id == file.id)
            .order_by(CodeChunk.start_line.asc())
        )
        chunk_res = await session.execute(chunk_query)
        chunks = [CodeChunkRead.model_validate(c) for c in chunk_res.scalars().all()]

        full_content = None
        if chunks:
            file_chunks = [c for c in chunks if c.chunk_type == "file"]
            if file_chunks:
                full_content = file_chunks[0].content
            else:
                full_content = "\n\n".join([c.content for c in chunks])

        return FileDetailRead(
            file=FileRead.model_validate(file),
            symbols=symbols,
            outgoing_dependencies=outgoing_deps,
            incoming_references=incoming_refs,
            chunks=chunks,
            full_content=full_content,
        )
