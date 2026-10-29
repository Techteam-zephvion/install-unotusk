import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config.settings import settings
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.graph_expander import RelationshipExpander
from apps.api.src.services.context_engine.knowledge_retriever import KnowledgeRetriever
from apps.api.src.services.context_engine.query_analyzer import analyze_query_async
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
        repository_id: uuid.UUID | None = None,
        enable_star_rag: bool | None = None,
        enable_memotime: bool | None = None,
    ) -> GroundedAnswer:
        # 1. Query Analysis
        analyzed = await analyze_query_async(question)

        # 1b. Resolve repository_id if not explicitly provided
        if repository_id is None:
            snap_repo_stmt = select(RepositorySnapshot.repository_id).where(
                RepositorySnapshot.id == snapshot_id
            )
            repository_id = (await session.execute(snap_repo_stmt)).scalar_one_or_none()

        # 1c. Generate Query Embedding for semantic retrieval if not provided
        if query_embedding is None and question:
            try:
                from apps.api.src.services.code_atom.embedding import generate_code_embedding

                query_embedding = generate_code_embedding(question, input_type="query")
            except Exception:
                query_embedding = None

            if query_embedding is None:
                from apps.api.src.services.context_engine.retriever import generate_text_embedding

                query_embedding = generate_text_embedding(question)

        # 2. Multi-Signal Retrieval (Lexical + Vector + Semantic)
        raw_candidates = await MultiSignalRetriever.retrieve_candidates(
            session=session,
            snapshot_id=snapshot_id,
            analyzed_query=analyzed,
            query_embedding=query_embedding,
            repository_id=repository_id,
        )

        # 3. Structural Relationship Expansion (Multi-hop graph traversal)
        expanded_candidates = await RelationshipExpander.expand_candidates(
            session=session,
            snapshot_id=snapshot_id,
            seed_candidates=raw_candidates,
            max_depth=2,
        )

        # 3b. STAR-RAG Temporal Rule Graph Retrieval
        use_star_rag = (
            enable_star_rag
            if enable_star_rag is not None
            else getattr(settings, "STAR_RAG_ENABLED", False)
        )
        star_rag_diagnostics: dict[str, Any] = {}
        star_rag_applied = False
        if use_star_rag:
            try:
                from apps.api.src.services.context_engine.star_rag import StarRagContextService

                star_res = StarRagContextService.run_star_rag_pipeline(
                    candidates=expanded_candidates,
                    analyzed_query=analyzed,
                    query_text=question,
                )
                expanded_candidates = star_res.candidates
                star_rag_applied = not star_res.is_fallback
                star_rag_diagnostics = {
                    "is_fallback": star_res.is_fallback,
                    "fallback_reason": star_res.fallback_reason,
                    "top_rules_count": len(star_res.top_rules),
                    "rule_nodes_count": len(star_res.rule_nodes),
                    "selected_edges_count": len(star_res.selected_edges),
                    "initial_mdl_cost": round(star_res.initial_mdl_cost, 2),
                    "final_mdl_cost": round(star_res.final_mdl_cost, 2),
                }
            except Exception as exc:
                star_rag_applied = False
                star_rag_diagnostics = {
                    "exception_occurred": True,
                    "is_fallback": True,
                    "fallback_reason": str(exc),
                    "error": str(exc),
                }

        # 3c. MemoTime Operator-Aware Temporal Retrieval (arXiv:2510.13614)
        use_memotime = (
            enable_memotime
            if enable_memotime is not None
            else getattr(settings, "MEMOTIME_ENABLED", False)
        )
        memotime_diagnostics: dict[str, Any] = {}
        memotime_success = False
        if use_memotime:
            try:
                from apps.api.src.services.context_engine.memotime import MemoTimeService

                memo_res = MemoTimeService.run_memotime_pipeline(
                    candidates=expanded_candidates,
                    analyzed_query=analyzed,
                    query_text=question,
                )
                expanded_candidates = memo_res.candidates
                memotime_success = not memo_res.is_fallback
                memotime_diagnostics = {
                    "strategy": (
                        memo_res.strategy_used.value
                        if hasattr(memo_res.strategy_used, "value")
                        else str(memo_res.strategy_used)
                    ),
                    "is_fallback": memo_res.is_fallback,
                    "fallback_reason": memo_res.fallback_reason,
                    "applied_signals_count": memo_res.applied_signals_count,
                    **memo_res.diagnostics,
                }
            except Exception as exc:
                memotime_success = False
                memotime_diagnostics = {
                    "exception_occurred": True,
                    "is_fallback": True,
                    "fallback_reason": str(exc),
                    "error": str(exc),
                }

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
                "memotime_used": memotime_success if use_memotime else False,
                "memotime_diagnostics": memotime_diagnostics,
                "star_rag_used": star_rag_applied if use_star_rag else False,
                "star_rag_diagnostics": star_rag_diagnostics,
            }
        )

        return answer
