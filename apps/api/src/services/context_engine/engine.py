import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.graph_expander import RelationshipExpander
from apps.api.src.services.context_engine.knowledge_retriever import KnowledgeRetriever
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import MultiSignalRetriever
from apps.api.src.services.llm.base import GroundedAnswer, LLMProvider
from apps.api.src.services.llm.factory import get_llm_provider


class ProjectContextEngine:
    def __init__(self, llm_provider: LLMProvider | None = None):
        self.llm_provider = llm_provider or get_llm_provider()

    async def investigate(
        self,
        session: AsyncSession,
        snapshot_id: uuid.UUID,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
        project_id: uuid.UUID | None = None,
    ) -> GroundedAnswer:
        # 1. Query Analysis
        analyzed = analyze_query(question)

        # 2. Multi-Signal Retrieval
        raw_candidates = await MultiSignalRetriever.retrieve_candidates(
            session=session,
            snapshot_id=snapshot_id,
            analyzed_query=analyzed,
        )

        # 3. Structural Relationship Expansion (1 hop)
        expanded_candidates = await RelationshipExpander.expand_candidates(
            session=session,
            snapshot_id=snapshot_id,
            seed_candidates=raw_candidates,
        )

        # 4. Multi-Signal Ranking
        ranked = MultiSignalRanker.rank_candidates(
            candidates=expanded_candidates,
            analyzed_query=analyzed,
        )

        # 5. Context Assembly & Budgeting
        assembled = ContextAssembler.assemble_context(ranked_candidates=ranked)

        # 5b. Retrieve Customer Project Knowledge
        if project_id is None:
            snap_stmt = (
                select(Repository.project_id)
                .join(RepositorySnapshot, RepositorySnapshot.repository_id == Repository.id)
                .where(RepositorySnapshot.id == snapshot_id)
            )
            project_id = (await session.execute(snap_stmt)).scalar_one_or_none()

        knowledge_context = ""
        knowledge_records = []
        if project_id is not None:
            knowledge_context, knowledge_records = await KnowledgeRetriever.retrieve_project_knowledge(
                session=session,
                project_id=project_id,
                analyzed_query=analyzed,
            )

        full_prompt_context = assembled.prompt_context
        if knowledge_context:
            full_prompt_context = f"{knowledge_context}\n\n## REPOSITORY CODE EVIDENCE\n{assembled.prompt_context}"

        # 6. LLM Grounded Synthesis (Claude or deterministic offline)
        answer = await self.llm_provider.generate_grounded_answer(
            question=question,
            project_context=full_prompt_context,
            evidence_items=assembled.evidence_items,
            related_entities=assembled.related_entities,
            conversation_history=conversation_history,
        )

        # Attach retrieval debug signals
        answer.debug_signals.update(
            {
                "keywords": analyzed.keywords,
                "symbols_detected": analyzed.symbol_candidates,
                "paths_detected": analyzed.path_candidates,
                "candidates_retrieved": len(raw_candidates),
                "candidates_expanded": len(expanded_candidates),
                "customer_knowledge_count": len(knowledge_records),
                "top_score": ranked[0].score if ranked else 0.0,
            }
        )

        return answer
