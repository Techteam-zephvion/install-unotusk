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
        query_embedding: list[float] | None = None,
        thinking_tier: str | None = None,
    ) -> GroundedAnswer:
        # 1. Query Analysis
        analyzed = analyze_query(question)

        # 1b. Generate Query Embedding for semantic retrieval if not provided
        if query_embedding is None and question:
            from apps.api.src.services.context_engine.retriever import generate_text_embedding

            query_embedding = generate_text_embedding(question)

        # 2. Multi-Signal Retrieval (Lexical + Vector + Semantic)
        raw_candidates = await MultiSignalRetriever.retrieve_candidates(
            session=session,
            snapshot_id=snapshot_id,
            analyzed_query=analyzed,
            query_embedding=query_embedding,
        )

        # 3. Structural Relationship Expansion (Multi-hop graph traversal)
        expanded_candidates = await RelationshipExpander.expand_candidates(
            session=session,
            snapshot_id=snapshot_id,
            seed_candidates=raw_candidates,
            max_depth=2,
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
            (
                knowledge_context,
                knowledge_records,
            ) = await KnowledgeRetriever.retrieve_project_knowledge(
                session=session,
                project_id=project_id,
                analyzed_query=analyzed,
            )

        full_prompt_context = assembled.prompt_context
        if knowledge_context:
            full_prompt_context = (
                f"{knowledge_context}\n\n## REPOSITORY CODE EVIDENCE\n{assembled.prompt_context}"
            )

        # 6. LLM Grounded Synthesis (Claude, Groq, or deterministic offline)
        answer = await self.llm_provider.generate_grounded_answer(
            question=question,
            project_context=full_prompt_context,
            evidence_items=assembled.evidence_items,
            related_entities=assembled.related_entities,
            conversation_history=conversation_history,
            thinking_tier=thinking_tier,
        )

        # Attach retrieval debug signals
        has_vector = any("vector_similarity" in c.signals for c in raw_candidates)
        has_semantic = any("semantic_match" in c.signals for c in raw_candidates)
        answer.debug_signals.update(
            {
                "keywords": analyzed.keywords,
                "symbols_detected": analyzed.symbol_candidates,
                "paths_detected": analyzed.path_candidates,
                "concept_keywords": analyzed.concept_keywords,
                "vector_search_used": has_vector,
                "semantic_search_used": has_semantic,
                "graph_traversal_depth": 2,
                "candidates_retrieved": len(raw_candidates),
                "candidates_expanded": len(expanded_candidates),
                "customer_knowledge_count": len(knowledge_records),
                "top_score": ranked[0].score if ranked else 0.0,
            }
        )

        return answer
