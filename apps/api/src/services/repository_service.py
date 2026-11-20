import os
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import (
    ForbiddenException,
    NotFoundException,
)
from apps.api.src.core.security_vault import decrypt_secret, encrypt_secret
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    KnowledgeCategory,
    KnowledgeStatus,
    MembershipRole,
    ProjectStatus,
    SnapshotStatus,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.finding import Finding
from apps.api.src.models.integration import Integration
from apps.api.src.models.knowledge import ProjectKnowledge
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
            # In single-tenant MVP, grant verified user automatic membership
            auto_mem = OrganizationMembership(
                id=uuid.uuid4(),
                organization_id=project.organization_id,
                user_id=user_id,
                role=MembershipRole.MEMBER,
            )
            session.add(auto_mem)
            await session.commit()

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
                    "github_token": encrypt_secret(effective_token),
                },
            )
            session.add(integration)
        else:
            integration.status = IntegrationStatus.CONNECTED
            integration.external_id = str(user_profile.get("id"))
            integration.integration_metadata = {
                "username": user_profile.get("login"),
                "github_token": encrypt_secret(effective_token),
            }

        await session.commit()

        return {
            "status": "connected",
            "provider": "GITHUB",
            "username": user_profile.get("login"),
            "integration_id": str(integration.id),
        }

    @staticmethod
    async def list_project_integrations(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> list[dict]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        # 1. Fetch real integrations from the database
        int_query = select(Integration).where(Integration.project_id == project.id)
        int_res = await session.execute(int_query)
        integrations = {
            (integ.provider.value if hasattr(integ.provider, "value") else str(integ.provider)).upper(): integ
            for integ in int_res.scalars().all()
        }

        # 2. Fetch repository info if any
        repo_query = (
            select(Repository)
            .where(Repository.project_id == project.id)
            .order_by(Repository.created_at.desc())
        )
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalars().first()

        # Define standard supported integrations and resolve their real-time state
        standard_apps = [
            {"name": "GitHub", "provider": "GITHUB", "icon": "GH"},
            {"name": "Jira", "provider": "JIRA", "icon": "JR"},
            {"name": "Confluence", "provider": "CONFLUENCE", "icon": "CF"},
            {"name": "Linear", "provider": "LINEAR", "icon": "LN"},
            {"name": "Slack", "provider": "SLACK", "icon": "SL"},
            {"name": "GitLab", "provider": "GITLAB", "icon": "GL"},
            {"name": "PagerDuty", "provider": "PAGERDUTY", "icon": "PD"},
        ]

        out = []
        for app in standard_apps:
            provider_key = app["provider"]
            integ = integrations.get(provider_key)

            is_connected = False
            details = "Not configured"
            external_id = None
            url = None

            if provider_key == "GITHUB":
                if repo is not None or (integ and integ.status == IntegrationStatus.CONNECTED):
                    is_connected = True
                    repo_name = repo.full_name if repo else (integ.integration_metadata.get("username") if integ else "Connected")
                    details = f"Repository: {repo_name}" if repo else "Account Connected"
                    external_id = repo.external_id if repo else (integ.external_id if integ else None)
                    url = repo.url if repo else None
            elif integ and integ.status == IntegrationStatus.CONNECTED:
                is_connected = True
                details = integ.integration_metadata.get("name", "Connected")
                external_id = integ.external_id

            out.append({
                "name": app["name"],
                "icon": app["icon"],
                "provider": provider_key,
                "status": "Connected" if is_connected else "Not connected",
                "details": details,
                "is_connected": is_connected,
                "external_id": external_id,
                "url": url,
                "connected_at": integ.created_at.isoformat() if (integ and is_connected and hasattr(integ, "created_at") and integ.created_at) else None,
            })

        return out

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
            encrypted_token = integration.integration_metadata.get("github_token")
            token = decrypt_secret(encrypted_token) if encrypted_token else None
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

        token = os.getenv("GITHUB_TOKEN")
        if integration is None:
            integration = Integration(
                project_id=project.id,
                provider=IntegrationProvider.GITHUB,
                status=IntegrationStatus.CONNECTED,
                external_id=data.external_id,
                integration_metadata={"github_token": encrypt_secret(token)} if token else {},
            )
            session.add(integration)
            await session.flush()
        elif token and not (integration.integration_metadata or {}).get("github_token"):
            meta = dict(integration.integration_metadata or {})
            meta["github_token"] = encrypt_secret(token)
            integration.integration_metadata = meta

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
            repo_name = project.slug or project.name.lower().replace(" ", "-")
            repo = Repository(
                id=uuid.uuid4(),
                project_id=project.id,
                provider=IntegrationProvider.GITHUB,
                external_id=f"repo-{repo_name}",
                owner="Techteam-zephvion",
                name=repo_name,
                full_name=f"Techteam-zephvion/{repo_name}",
                default_branch="main",
                url=f"https://github.com/Techteam-zephvion/{repo_name}",
                is_private=False,
            )
            session.add(repo)
            await session.flush()

        # Fetch latest snapshot
        snap_query = (
            select(RepositorySnapshot)
            .where(RepositorySnapshot.repository_id == repo.id)
            .order_by(RepositorySnapshot.created_at.desc())
        )
        snap_res = await session.execute(snap_query)
        snapshot = snap_res.scalars().first()

        if snapshot is None:
            snapshot = RepositorySnapshot(
                id=uuid.uuid4(),
                repository_id=repo.id,
                branch=repo.default_branch or "main",
                status=SnapshotStatus.QUEUED,
            )
            session.add(snapshot)
            await session.commit()
            await session.refresh(snapshot)

            from apps.api.src.services.ingestion_service import IngestionService
            await IngestionService.run_ingestion(snapshot.id)
            await session.refresh(snapshot)

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

            # Total SLOC
            sloc_count = await session.execute(
                select(func.coalesce(func.sum(RepositoryFile.line_count), 0)).where(
                    RepositoryFile.snapshot_id == snapshot.id
                )
            )
            metrics.total_sloc = int(sloc_count.scalar() or 0)

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

            # Findings count
            find_count = await session.execute(
                select(func.count(Finding.id)).where(
                    Finding.project_id == project.id
                )
            )
            metrics.total_findings = find_count.scalar() or 0

        return ProjectRepositoryContext(
            repository=RepositoryRead.model_validate(repo) if repo else None,
            active_snapshot=SnapshotRead.model_validate(snapshot) if snapshot else None,
            metrics=metrics,
        )

    @staticmethod
    async def _get_latest_snapshot(
        session: AsyncSession,
        project_id: uuid.UUID,
    ) -> RepositorySnapshot | None:
        repo_query = (
            select(Repository)
            .where(Repository.project_id == project_id)
            .order_by(Repository.created_at.desc())
        )
        repo_res = await session.execute(repo_query)
        repo = repo_res.scalars().first()
        if repo is None:
            return None

        snap_query = (
            select(RepositorySnapshot)
            .where(RepositorySnapshot.repository_id == repo.id)
            .order_by(RepositorySnapshot.created_at.desc())
        )
        snap_res = await session.execute(snap_query)
        return snap_res.scalars().first()

    @staticmethod
    async def list_files(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        limit: int = 500,
    ) -> list[FileRead]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)

        snapshot = await RepositoryService._get_latest_snapshot(session, project.id)
        if snapshot is None:
            repo_query = select(Repository).where(Repository.project_id == project.id).order_by(Repository.created_at.desc())
            repo = (await session.execute(repo_query)).scalars().first()
            if repo is None:
                repo_name = project.slug or project.name.lower().replace(" ", "-")
                repo = Repository(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    provider=IntegrationProvider.GITHUB,
                    external_id=f"repo-{repo_name}",
                    owner="Techteam-zephvion",
                    name=repo_name,
                    full_name=f"Techteam-zephvion/{repo_name}",
                    default_branch="main",
                    url=f"https://github.com/Techteam-zephvion/{repo_name}",
                    is_private=False,
                )
                session.add(repo)
                await session.flush()

            snapshot = RepositorySnapshot(
                id=uuid.uuid4(),
                repository_id=repo.id,
                branch=repo.default_branch or "main",
                status=SnapshotStatus.QUEUED,
            )
            session.add(snapshot)
            await session.commit()
            await session.refresh(snapshot)

            from apps.api.src.services.ingestion_service import IngestionService
            await IngestionService.run_ingestion(snapshot.id)
            await session.refresh(snapshot)

        query = (
            select(RepositoryFile)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(
                Repository.project_id == project.id,
                RepositorySnapshot.id == snapshot.id,
            )
            .order_by(RepositorySnapshot.created_at.desc(), RepositoryFile.path.asc())
            .limit(limit)
        )
        res = await session.execute(query)
        files = res.scalars().all()

        if not files:
            from apps.api.src.services.ingestion_service import IngestionService
            await IngestionService.run_ingestion(snapshot.id)
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

        snapshot = await RepositoryService._get_latest_snapshot(session, project.id)
        if snapshot is None:
            return []

        query = (
            select(CodeSymbol, RepositoryFile.path)
            .join(RepositoryFile, RepositoryFile.id == CodeSymbol.file_id)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(
                Repository.project_id == project.id,
                RepositorySnapshot.id == snapshot.id,
            )
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

        snapshot = await RepositoryService._get_latest_snapshot(session, project.id)
        if snapshot is None:
            return []

        query = (
            select(CodeDependency, RepositoryFile.path)
            .join(RepositoryFile, RepositoryFile.id == CodeDependency.source_file_id)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(
                Repository.project_id == project.id,
                RepositorySnapshot.id == snapshot.id,
            )
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
            select(RepositoryFile, Repository, RepositorySnapshot)
            .join(RepositorySnapshot, RepositorySnapshot.id == RepositoryFile.snapshot_id)
            .join(Repository, Repository.id == RepositorySnapshot.repository_id)
            .where(
                RepositoryFile.id == file_id,
                Repository.project_id == project.id,
            )
        )
        f_res = await session.execute(f_query)
        row = f_res.first()
        if row is None:
            raise NotFoundException(code="FILE_NOT_FOUND", message="File not found in project")
        file, repo, snapshot = row

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

        # 1. Attempt raw file retrieval directly from persistent git clone / disk
        full_content = None
        repo_dir = RepositoryService._resolve_repo_working_dir(repo)
        if repo_dir and os.path.exists(repo_dir):
            file_on_disk = os.path.join(repo_dir, file.path)
            if os.path.exists(file_on_disk) and os.path.isfile(file_on_disk):
                try:
                    with open(file_on_disk, "r", encoding="utf-8", errors="replace") as f:
                        full_content = f.read()
                except Exception as read_err:
                    logger.warning("Could not read file from disk %s: %s", file_on_disk, read_err)

            if full_content is None and snapshot and snapshot.commit_sha:
                try:
                    from apps.api.src.services.git_operations import GitOperationsService

                    raw = await GitOperationsService.get_file_content_at_commit(
                        repo_dir, snapshot.commit_sha, file.path
                    )
                    if raw is not None:
                        full_content = raw
                except Exception as git_err:
                    logger.debug("Git show fallback failed: %s", git_err)

        # 2. Fallback to database chunks if disk/git mirror is unavailable
        if full_content is None and chunks:
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

    @staticmethod
    async def sync_github_issues(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        repository_id: uuid.UUID,
        issues_data: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)
        repo_q = select(Repository).where(
            Repository.id == repository_id,
            Repository.project_id == project.id,
        )
        repo_res = await session.execute(repo_q)
        repo = repo_res.scalar_one_or_none()
        if not repo:
            raise NotFoundException(code="REPOSITORY_NOT_FOUND", message="Repository not found")

        # Retrieve integration token if available
        raw_issues = issues_data
        if raw_issues is None:
            token = os.getenv("GITHUB_TOKEN")
            int_query = select(Integration).where(
                Integration.project_id == project.id,
                Integration.provider == IntegrationProvider.GITHUB,
            )
            int_res = await session.execute(int_query)
            integration = int_res.scalar_one_or_none()
            if integration and integration.integration_metadata:
                encrypted_token = integration.integration_metadata.get("github_token")
                token = decrypt_secret(encrypted_token) if encrypted_token else token

            client = GitHubClient(token=token)
            try:
                raw_issues = await client.list_issues(owner=repo.owner, repo=repo.name)
            except Exception:
                raw_issues = []

        synced_records = []
        for issue in (raw_issues or []):
            num = issue.get("number")
            title = issue.get("title", "")
            content = issue.get("body") or f"Issue #{num}: {title}"
            is_pr = issue.get("is_pull_request", False)
            ref_type = "GITHUB_PR" if is_pr else "GITHUB_ISSUE"
            ref_id = f"#{num}"

            # Check if already exists for this project
            existing_q = select(ProjectKnowledge).where(
                ProjectKnowledge.project_id == project.id,
                ProjectKnowledge.source_type == "GITHUB",
                ProjectKnowledge.source_reference_type == ref_type,
                ProjectKnowledge.source_reference_id == ref_id,
            )
            existing = (await session.execute(existing_q)).scalar_one_or_none()

            meta = {
                "issue_number": num,
                "external_id": issue.get("id"),
                "url": issue.get("html_url"),
                "labels": issue.get("labels", []),
                "author": issue.get("author"),
                "is_pull_request": is_pr,
            }

            # Generate embedding
            try:
                from apps.api.src.services.code_atom.embedding import generate_code_embedding

                emb = generate_code_embedding(f"{title}\n{content}", input_type="document")
                if emb:
                    meta["embedding"] = emb
            except Exception:
                pass

            now = datetime.now(UTC)
            full_title = f"Issue #{num}: {title}" if not title.startswith(f"Issue #{num}") else title

            category = (
                KnowledgeCategory.CONSTRAINT
                if any(w in title.lower() for w in ("security", "auth", "limit", "rate", "constraint"))
                else KnowledgeCategory.BUSINESS_RULE
            )

            if existing is None:
                new_item = ProjectKnowledge(
                    id=uuid.uuid4(),
                    project_id=project.id,
                    created_by=user_id,
                    category=category,
                    title=full_title,
                    content=content,
                    status=KnowledgeStatus.ACTIVE,
                    source_type="GITHUB",
                    source_reference_type=ref_type,
                    source_reference_id=ref_id,
                    knowledge_metadata=meta,
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_item)
                synced_records.append(
                    {"id": str(new_item.id), "number": num, "status": "created", "title": full_title}
                )
            else:
                existing.title = full_title
                existing.content = content
                existing.knowledge_metadata = meta
                existing.updated_at = now
                synced_records.append(
                    {"id": str(existing.id), "number": num, "status": "updated", "title": full_title}
                )

        await session.commit()
        return synced_records

    @staticmethod
    def _resolve_repo_working_dir(repo: Repository) -> str:
        cache_base = os.getenv("UNOTUSK_REPOS_DIR", "/tmp/unotusk-repos")
        slug = repo.full_name.replace("/", "_") if repo.full_name else repo.name
        for candidate_name in [slug, repo.name]:
            candidate = os.path.join(cache_base, candidate_name)
            if os.path.exists(candidate) and os.path.isdir(candidate):
                return candidate
        if os.path.exists(".git"):
            return os.getcwd()
        return os.path.join(cache_base, slug)

    @staticmethod
    async def get_git_branches(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> dict[str, Any]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)
        repo_query = select(Repository).where(Repository.project_id == project.id)
        repo = (await session.execute(repo_query)).scalar_one_or_none()
        if repo is None:
            return {"branches": ["main"], "current": "main"}

        repo_dir = RepositoryService._resolve_repo_working_dir(repo)
        from apps.api.src.services.git_operations import GitOperationsService

        branches = await GitOperationsService.list_branches(repo_dir)
        current = await GitOperationsService.get_current_branch(repo_dir)
        return {"branches": branches, "current": current}

    @staticmethod
    async def get_git_diff(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        base_ref: str = "HEAD~1",
        head_ref: str = "HEAD",
    ) -> dict[str, Any]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)
        repo_query = select(Repository).where(Repository.project_id == project.id)
        repo = (await session.execute(repo_query)).scalar_one_or_none()
        if repo is None:
            return {"success": False, "error": "No connected repository", "diff": "", "files_changed": []}

        repo_dir = RepositoryService._resolve_repo_working_dir(repo)
        from apps.api.src.services.git_operations import GitOperationsService

        return await GitOperationsService.get_diff(repo_dir, base_ref, head_ref)

    @staticmethod
    async def get_git_log(
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        count: int = 20,
        branch: str = "HEAD",
    ) -> list[dict[str, Any]]:
        project = await RepositoryService._verify_project_access(session, user_id, project_id)
        repo_query = select(Repository).where(Repository.project_id == project.id)
        repo = (await session.execute(repo_query)).scalar_one_or_none()
        if repo is None:
            return []

        repo_dir = RepositoryService._resolve_repo_working_dir(repo)
        from apps.api.src.services.git_operations import GitOperationsService

        return await GitOperationsService.get_commit_log(repo_dir, max_count=count, branch=branch)
