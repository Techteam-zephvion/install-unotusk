import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import ForbiddenException, NotFoundException
from apps.api.src.models.enums import KnowledgeCategory, KnowledgeStatus
from apps.api.src.models.finding import Finding
from apps.api.src.models.knowledge import ProjectKnowledge
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.project import Project
from apps.api.src.models.user import User
from apps.api.src.schemas.knowledge import (
    KnowledgeCreateRequest,
    KnowledgeResponse,
    KnowledgeUpdateRequest,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class KnowledgeService:
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

    @classmethod
    async def create_knowledge(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        data: KnowledgeCreateRequest,
    ) -> KnowledgeResponse:
        project = await cls._verify_project_access(session, user_id, project_id)

        # If finding_id is provided, verify it belongs to this project
        if data.related_finding_id:
            finding_q = select(Finding).where(
                Finding.id == data.related_finding_id,
                Finding.project_id == project.id,
            )
            finding_res = await session.execute(finding_q)
            if finding_res.scalar_one_or_none() is None:
                data.related_finding_id = None

        # Ensure embedding is generated for persistent RAG retrieval
        meta = dict(data.knowledge_metadata or {})
        if "embedding" not in meta:
            try:
                from apps.api.src.services.code_atom.embedding import generate_code_embedding

                embed_text = f"{data.title}\n{data.content}"
                emb = generate_code_embedding(embed_text, input_type="document")
                if emb:
                    meta["embedding"] = emb
            except Exception:
                pass

        effective_source_type = getattr(data, "source_type", None) or "CUSTOMER"

        item = ProjectKnowledge(
            id=uuid.uuid4(),
            project_id=project.id,
            created_by=user_id,
            category=data.category,
            title=data.title,
            content=data.content,
            status=KnowledgeStatus.ACTIVE,
            source_type=effective_source_type,
            source_reference_type=data.source_reference_type,
            source_reference_id=data.source_reference_id,
            related_file_path=data.related_file_path,
            related_symbol=data.related_symbol,
            related_finding_id=data.related_finding_id,
            related_entity_type=data.related_entity_type,
            related_entity_id=data.related_entity_id,
            knowledge_metadata=meta,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)

        # Get creator email if available
        user_res = await session.execute(select(User.email).where(User.id == user_id))
        creator_email = user_res.scalar_one_or_none()

        return KnowledgeResponse(
            id=item.id,
            project_id=item.project_id,
            created_by=item.created_by,
            creator_email=creator_email,
            category=item.category,
            title=item.title,
            content=item.content,
            status=item.status,
            source_type=item.source_type,
            source_reference_type=item.source_reference_type,
            source_reference_id=item.source_reference_id,
            related_file_path=item.related_file_path,
            related_symbol=item.related_symbol,
            related_finding_id=item.related_finding_id,
            related_entity_type=item.related_entity_type,
            related_entity_id=item.related_entity_id,
            knowledge_metadata=item.knowledge_metadata,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @classmethod
    async def list_knowledge(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        status: KnowledgeStatus | None = None,
        category: KnowledgeCategory | None = None,
        search: str | None = None,
    ) -> list[KnowledgeResponse]:
        project = await cls._verify_project_access(session, user_id, project_id)

        stmt = (
            select(ProjectKnowledge, User.email)
            .outerjoin(User, User.id == ProjectKnowledge.created_by)
            .where(ProjectKnowledge.project_id == project.id)
        )

        if status is not None:
            stmt = stmt.where(ProjectKnowledge.status == status)

        if category is not None:
            stmt = stmt.where(ProjectKnowledge.category == category)

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    ProjectKnowledge.title.ilike(pattern),
                    ProjectKnowledge.content.ilike(pattern),
                    ProjectKnowledge.related_symbol.ilike(pattern),
                    ProjectKnowledge.related_file_path.ilike(pattern),
                )
            )

        stmt = stmt.order_by(desc(ProjectKnowledge.created_at))
        res = await session.execute(stmt)
        rows = res.all()

        results: list[KnowledgeResponse] = []
        for item, email in rows:
            results.append(
                KnowledgeResponse(
                    id=item.id,
                    project_id=item.project_id,
                    created_by=item.created_by,
                    creator_email=email,
                    category=item.category,
                    title=item.title,
                    content=item.content,
                    status=item.status,
                    source_type=item.source_type,
                    source_reference_type=item.source_reference_type,
                    source_reference_id=item.source_reference_id,
                    related_file_path=item.related_file_path,
                    related_symbol=item.related_symbol,
                    related_finding_id=item.related_finding_id,
                    related_entity_type=item.related_entity_type,
                    related_entity_id=item.related_entity_id,
                    knowledge_metadata=item.knowledge_metadata,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
            )
        return results

    @classmethod
    async def get_knowledge(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        knowledge_id: uuid.UUID,
    ) -> KnowledgeResponse:
        project = await cls._verify_project_access(session, user_id, project_id)

        stmt = (
            select(ProjectKnowledge, User.email)
            .outerjoin(User, User.id == ProjectKnowledge.created_by)
            .where(
                ProjectKnowledge.id == knowledge_id,
                ProjectKnowledge.project_id == project.id,
            )
        )
        res = await session.execute(stmt)
        row = res.one_or_none()
        if row is None:
            raise NotFoundException(
                code="KNOWLEDGE_NOT_FOUND",
                message="Project knowledge item not found",
            )
        item, email = row
        return KnowledgeResponse(
            id=item.id,
            project_id=item.project_id,
            created_by=item.created_by,
            creator_email=email,
            category=item.category,
            title=item.title,
            content=item.content,
            status=item.status,
            source_type=item.source_type,
            source_reference_type=item.source_reference_type,
            source_reference_id=item.source_reference_id,
            related_file_path=item.related_file_path,
            related_symbol=item.related_symbol,
            related_finding_id=item.related_finding_id,
            related_entity_type=item.related_entity_type,
            related_entity_id=item.related_entity_id,
            knowledge_metadata=item.knowledge_metadata,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @classmethod
    async def update_knowledge(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        knowledge_id: uuid.UUID,
        data: KnowledgeUpdateRequest,
    ) -> KnowledgeResponse:
        project = await cls._verify_project_access(session, user_id, project_id)

        stmt = select(ProjectKnowledge).where(
            ProjectKnowledge.id == knowledge_id,
            ProjectKnowledge.project_id == project.id,
        )
        res = await session.execute(stmt)
        item = res.scalar_one_or_none()
        if item is None:
            raise NotFoundException(
                code="KNOWLEDGE_NOT_FOUND",
                message="Project knowledge item not found",
            )

        content_changed = False
        if data.title is not None and data.title != item.title:
            item.title = data.title
            content_changed = True
        if data.content is not None and data.content != item.content:
            item.content = data.content
            content_changed = True
        if data.category is not None:
            item.category = data.category
        if data.status is not None:
            item.status = data.status
        if getattr(data, "source_type", None) is not None:
            item.source_type = data.source_type
        if getattr(data, "source_reference_type", None) is not None:
            item.source_reference_type = data.source_reference_type
        if getattr(data, "source_reference_id", None) is not None:
            item.source_reference_id = data.source_reference_id
        if data.related_file_path is not None:
            item.related_file_path = data.related_file_path
        if data.related_symbol is not None:
            item.related_symbol = data.related_symbol
        if data.related_finding_id is not None:
            item.related_finding_id = data.related_finding_id
        if data.related_entity_type is not None:
            item.related_entity_type = data.related_entity_type
        if data.related_entity_id is not None:
            item.related_entity_id = data.related_entity_id
        if data.knowledge_metadata is not None:
            item.knowledge_metadata = dict(data.knowledge_metadata)

        # Re-compute embedding if content or title changed, or if embedding missing
        meta = dict(item.knowledge_metadata or {})
        if content_changed or "embedding" not in meta:
            try:
                from apps.api.src.services.code_atom.embedding import generate_code_embedding

                embed_text = f"{item.title}\n{item.content}"
                emb = generate_code_embedding(embed_text, input_type="document")
                if emb:
                    meta["embedding"] = emb
                    item.knowledge_metadata = meta
            except Exception:
                pass

        item.updated_at = utc_now()
        await session.commit()
        await session.refresh(item)

        user_res = await session.execute(select(User.email).where(User.id == item.created_by))
        email = user_res.scalar_one_or_none()

        return KnowledgeResponse(
            id=item.id,
            project_id=item.project_id,
            created_by=item.created_by,
            creator_email=email,
            category=item.category,
            title=item.title,
            content=item.content,
            status=item.status,
            source_type=item.source_type,
            source_reference_type=item.source_reference_type,
            source_reference_id=item.source_reference_id,
            related_file_path=item.related_file_path,
            related_symbol=item.related_symbol,
            related_finding_id=item.related_finding_id,
            related_entity_type=item.related_entity_type,
            related_entity_id=item.related_entity_id,
            knowledge_metadata=item.knowledge_metadata,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @classmethod
    async def archive_knowledge(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        knowledge_id: uuid.UUID,
    ) -> KnowledgeResponse:
        return await cls.update_knowledge(
            session=session,
            user_id=user_id,
            project_id=project_id,
            knowledge_id=knowledge_id,
            data=KnowledgeUpdateRequest(status=KnowledgeStatus.ARCHIVED),
        )

    @classmethod
    async def restore_knowledge(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        knowledge_id: uuid.UUID,
    ) -> KnowledgeResponse:
        return await cls.update_knowledge(
            session=session,
            user_id=user_id,
            project_id=project_id,
            knowledge_id=knowledge_id,
            data=KnowledgeUpdateRequest(status=KnowledgeStatus.ACTIVE),
        )
