import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.api.exceptions import BadRequestException, ForbiddenException, NotFoundException
from apps.api.src.models.conversation import Conversation
from apps.api.src.models.enums import SnapshotStatus
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.message import Message
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.intelligence import (
    ContextCandidateDebug,
    ContextSearchResponse,
    ConversationRead,
    EvidenceItem,
    GroundedAnswerResponse,
    MessageRead,
)
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.context_engine.graph_expander import RelationshipExpander
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import MultiSignalRetriever


def utc_now() -> datetime:
    return datetime.now(UTC)


class IntelligenceService:
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
            .order_by(RepositorySnapshot.created_at.desc())
            .limit(1)
        )
        res = await session.execute(stmt)
        snap = res.scalar_one_or_none()
        if snap is None:
            raise BadRequestException(
                code="NO_INDEXED_SNAPSHOT",
                message="Project repository has not been indexed yet. Please ingest a repository first.",
            )
        return snap

    @classmethod
    async def ask_question(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        question: str,
        conversation_id: uuid.UUID | None = None,
    ) -> GroundedAnswerResponse:
        project = await cls._verify_project_access(session, user_id, project_id)
        snapshot = await cls._get_active_snapshot(session, project_id)

        # 1. Resolve or create Conversation
        if conversation_id:
            conv_stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.project_id == project.id,
            )
            conv_res = await session.execute(conv_stmt)
            conversation = conv_res.scalar_one_or_none()
            if conversation is None:
                raise NotFoundException(
                    code="CONVERSATION_NOT_FOUND",
                    message="Specified conversation not found",
                )
        else:
            # Generate brief title from first 6 words of question
            title_words = question.split()[:6]
            title = " ".join(title_words)
            if len(question.split()) > 6:
                title += "..."

            conversation = Conversation(
                id=uuid.uuid4(),
                project_id=project.id,
                user_id=user_id,
                title=title or "Project Q&A",
            )
            session.add(conversation)
            await session.flush()

        # 2. Record User Message
        user_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role="user",
            content=question,
            evidence=[],
            related_entities=[],
            confidence=None,
            debug_signals={},
            created_at=utc_now(),
        )
        session.add(user_msg)
        await session.flush()

        # 3. Retrieve prior conversation history for context continuity
        history_stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.id != user_msg.id,
            )
            .order_by(Message.created_at.asc())
            .limit(6)
        )
        history_res = await session.execute(history_stmt)
        history_turns = [
            {"role": m.role, "content": m.content}
            for m in history_res.scalars().all()
        ]

        # 4. Run Grounded Investigation via ProjectContextEngine
        engine = ProjectContextEngine()
        grounded_answer = await engine.investigate(
            session=session,
            snapshot_id=snapshot.id,
            question=question,
            conversation_history=history_turns,
            project_id=project.id,
        )

        # 5. Persist Assistant Message
        assistant_msg = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role="assistant",
            content=grounded_answer.content,
            evidence=grounded_answer.evidence,
            related_entities=grounded_answer.related_entities,
            confidence=grounded_answer.confidence,
            debug_signals=grounded_answer.debug_signals,
            created_at=utc_now(),
        )
        session.add(assistant_msg)
        conversation.updated_at = utc_now()
        await session.commit()

        evidence_items = [
            EvidenceItem(
                type=e.get("type", "file"),
                file=e.get("file", ""),
                symbol=e.get("symbol"),
                lines=e.get("lines"),
                relevance=e.get("relevance", 0.0),
                snippet=e.get("snippet"),
            )
            for e in grounded_answer.evidence
        ]

        return GroundedAnswerResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            role="assistant",
            content=grounded_answer.content,
            evidence=evidence_items,
            related_entities=grounded_answer.related_entities,
            confidence=grounded_answer.confidence,
            debug_signals=grounded_answer.debug_signals,
            created_at=assistant_msg.created_at,
        )

    @classmethod
    async def create_conversation(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        title: str | None = None,
        initial_question: str | None = None,
    ) -> ConversationRead:
        project = await cls._verify_project_access(session, user_id, project_id)

        conv_title = title or (initial_question[:40] if initial_question else "New Conversation")
        conversation = Conversation(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=user_id,
            title=conv_title,
        )
        session.add(conversation)
        await session.commit()

        return ConversationRead(
            id=conversation.id,
            project_id=project.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=0,
        )

    @classmethod
    async def list_conversations(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> list[ConversationRead]:
        project = await cls._verify_project_access(session, user_id, project_id)

        stmt = (
            select(
                Conversation,
                func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.project_id == project.id)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
        )
        res = await session.execute(stmt)

        results = []
        for conv, count in res.all():
            results.append(
                ConversationRead(
                    id=conv.id,
                    project_id=conv.project_id,
                    title=conv.title,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                    message_count=count,
                )
            )
        return results

    @classmethod
    async def get_conversation_messages(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> list[MessageRead]:
        project = await cls._verify_project_access(session, user_id, project_id)

        # Verify conversation belongs to project
        conv_stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.project_id == project.id,
        )
        conv_res = await session.execute(conv_stmt)
        if conv_res.scalar_one_or_none() is None:
            raise NotFoundException(
                code="CONVERSATION_NOT_FOUND",
                message="Conversation not found",
            )

        msg_stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        msg_res = await session.execute(msg_stmt)
        messages = msg_res.scalars().all()

        output = []
        for m in messages:
            ev_items = [
                EvidenceItem(
                    type=e.get("type", "file"),
                    file=e.get("file", ""),
                    symbol=e.get("symbol"),
                    lines=e.get("lines"),
                    relevance=e.get("relevance", 0.0),
                    snippet=e.get("snippet"),
                )
                for e in (m.evidence or [])
            ]
            output.append(
                MessageRead(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    evidence=ev_items,
                    related_entities=m.related_entities or [],
                    confidence=m.confidence,
                    debug_signals=m.debug_signals or {},
                    created_at=m.created_at,
                )
            )
        return output

    @classmethod
    async def debug_search_context(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        query: str,
    ) -> ContextSearchResponse:
        await cls._verify_project_access(session, user_id, project_id)
        snapshot = await cls._get_active_snapshot(session, project_id)

        analyzed = analyze_query(query)
        raw = await MultiSignalRetriever.retrieve_candidates(session, snapshot.id, analyzed)
        expanded = await RelationshipExpander.expand_candidates(session, snapshot.id, raw)
        ranked = MultiSignalRanker.rank_candidates(expanded, analyzed)

        debug_candidates = [
            ContextCandidateDebug(
                name=r.candidate.name,
                entity_type=r.candidate.entity_type,
                path=r.candidate.path,
                lines=f"{r.candidate.start_line}-{r.candidate.end_line}",
                score=r.score,
                reasons=r.matched_reasons,
                snippet=r.candidate.content[:300],
            )
            for r in ranked[:15]
        ]

        return ContextSearchResponse(
            query=query,
            keywords=analyzed.keywords,
            symbol_candidates=analyzed.symbol_candidates,
            candidates_count=len(ranked),
            ranked_candidates=debug_candidates,
        )
