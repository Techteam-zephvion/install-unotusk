import re
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
        enable_evoreasoner: bool | None = None,
        enable_structure_aware_star_rag: bool | None = None,
        force_structure_aware_star_rag: bool = False,
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
        use_star_rag_flag = (
            enable_star_rag
            if enable_star_rag is not None
            else getattr(settings, "STAR_RAG_ENABLED", False)
        )
        from apps.api.src.services.context_engine.star_rag import (
            StarRagContextService,
            TemporalStarRagRouter,
        )

        should_route_temporal, temporal_route_reason = (
            TemporalStarRagRouter.should_route_to_temporal_star_rag(
                query_text=question,
                analyzed_query=analyzed,
                flag_enabled=use_star_rag_flag,
                force_temporal_star_rag=(enable_star_rag is True),
            )
        )

        star_rag_diagnostics: dict[str, Any] = {
            "routing_decision": temporal_route_reason,
            "selective_routing_applied": True,
        }
        star_rag_applied = False
        temporal_star_rag_evidence: list[dict[str, Any]] = []

        if should_route_temporal:
            try:
                star_res = await StarRagContextService.run_star_rag_pipeline_async(
                    candidates=expanded_candidates,
                    analyzed_query=analyzed,
                    query_text=question,
                    session=session,
                    snapshot_id=snapshot_id,
                    repository_id=repository_id,
                )
                expanded_candidates = star_res.candidates
                star_rag_applied = not star_res.is_fallback
                star_rag_diagnostics.update(
                    {
                        "is_fallback": star_res.is_fallback,
                        "fallback_reason": star_res.fallback_reason,
                        "top_rules_count": len(star_res.top_rules),
                        "rule_nodes_count": len(star_res.rule_nodes),
                        "selected_edges_count": len(star_res.selected_edges),
                        "initial_mdl_cost": round(star_res.initial_mdl_cost, 2),
                        "final_mdl_cost": round(star_res.final_mdl_cost, 2),
                        "ranked_events_count": len(star_res.ranked_events),
                        "temporal_evidence_count": len(star_res.temporal_evidence),
                    }
                )
                if not star_res.is_fallback and star_res.temporal_evidence:
                    temporal_star_rag_evidence = star_res.temporal_evidence
            except Exception as exc:
                star_rag_applied = False
                star_rag_diagnostics.update(
                    {
                        "exception_occurred": True,
                        "is_fallback": True,
                        "fallback_reason": str(exc),
                        "error": str(exc),
                    }
                )
        else:
            star_rag_diagnostics.update(
                {
                    "is_fallback": True,
                    "fallback_reason": temporal_route_reason,
                }
            )

        # 3c. MemoTime Operator-Aware Temporal Retrieval (arXiv:2510.13614: "MemoTime: Memory-Augmented Temporal Knowledge Graph Enhanced Large Language Model Reasoning")
        use_memotime = (
            enable_memotime
            if enable_memotime is not None
            else getattr(settings, "MEMOTIME_ENABLED", False)
        )
        memotime_diagnostics: dict[str, Any] = {}
        memotime_success = False
        if use_memotime:
            try:
                from apps.api.src.services.context_engine.memotime import (
                    MemoTimeExperienceStore,
                    MemoTimeService,
                )

                experiences = []
                if repository_id is not None and session is not None:
                    experiences = await MemoTimeExperienceStore.retrieve_relevant_experiences_async(
                        session=session,
                        repository_id=repository_id,
                        branch="main",
                        target_entities=analyzed.symbol_candidates if analyzed else None,
                        intent_type=(
                            analyzed.structured_temporal_intent.intent_type.value
                            if analyzed and analyzed.structured_temporal_intent
                            else None
                        ),
                    )

                memo_res = MemoTimeService.run_memotime_pipeline(
                    candidates=expanded_candidates,
                    analyzed_query=analyzed,
                    query_text=question,
                    experiences=experiences,
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
                    "reused_experiences_count": len(memo_res.experiences_used),
                    **memo_res.diagnostics,
                }

                # Persist high-confidence verified reasoning trace to experience memory
                if (
                    memo_res.new_experience_candidate
                    and repository_id is not None
                    and session is not None
                ):
                    await MemoTimeExperienceStore.record_verified_experience_async(
                        session=session,
                        repository_id=repository_id,
                        branch="main",
                        query_text=memo_res.new_experience_candidate.query_text,
                        intent_type=memo_res.new_experience_candidate.intent_type,
                        target_entities=memo_res.new_experience_candidate.target_entities,
                        commit_sha=memo_res.new_experience_candidate.commit_sha,
                        valid_from=memo_res.new_experience_candidate.valid_from,
                        valid_to=memo_res.new_experience_candidate.valid_to,
                        verified_outcome=memo_res.new_experience_candidate.verified_outcome,
                        confidence_score=memo_res.new_experience_candidate.confidence_score,
                        is_verified=memo_res.new_experience_candidate.is_verified,
                        attribution=memo_res.new_experience_candidate.attribution,
                    )
            except Exception as exc:
                memotime_success = False
                memotime_diagnostics = {
                    "exception_occurred": True,
                    "is_fallback": True,
                    "fallback_reason": str(exc),
                    "error": str(exc),
                }

        # 4. Multi-Signal Ranking or Structure-Aware STAR-RAG (Selective Intent Routing)
        star_rag_flag = (
            enable_structure_aware_star_rag
            if enable_structure_aware_star_rag is not None
            else getattr(settings, "STRUCTURE_AWARE_STAR_RAG_ENABLED", False)
        )

        from apps.api.src.services.context_engine.star_rag_structure.selective_router import (
            StarRagSelectiveRouter,
        )

        should_route_star, route_reason = StarRagSelectiveRouter.should_route_to_star_rag(
            query_text=question,
            analyzed_query=analyzed,
            candidates=expanded_candidates,
            flag_enabled=star_rag_flag,
            force_star_rag=force_structure_aware_star_rag,
        )

        struct_star_rag_applied = False
        struct_star_rag_diagnostics: dict[str, Any] = {
            "routing_decision": route_reason,
            "selective_routing_applied": True,
        }
        struct_evidence_paths: list[Any] = []

        if should_route_star:
            try:
                from apps.api.src.services.context_engine.star_rag_structure.service import (
                    StructureAwareStarRagService,
                )

                ranked, star_struct_res = await StructureAwareStarRagService.run_pipeline_async(
                    candidates=expanded_candidates,
                    query_text=question,
                    analyzed_query=analyzed,
                    query_embedding=query_embedding,
                    session=session,
                    snapshot_id=snapshot_id,
                    enable_snr=getattr(settings, "STRUCTURE_AWARE_SNR_ENABLED", True),
                    enable_dtp=getattr(settings, "STRUCTURE_AWARE_DTP_ENABLED", True),
                    enable_ssaf=getattr(settings, "STRUCTURE_AWARE_SSAF_ENABLED", True),
                )
                struct_star_rag_applied = not star_struct_res.is_fallback
                struct_star_rag_diagnostics.update(
                    {
                        "is_fallback": star_struct_res.is_fallback,
                        "fallback_reason": star_struct_res.fallback_reason,
                        **star_struct_res.diagnostics,
                    }
                )
                if not star_struct_res.is_fallback and star_struct_res.evidence_paths:
                    struct_evidence_paths = star_struct_res.evidence_paths
            except Exception as exc:
                struct_star_rag_applied = False
                struct_star_rag_diagnostics.update(
                    {
                        "exception_occurred": True,
                        "is_fallback": True,
                        "fallback_reason": str(exc),
                        "error": str(exc),
                    }
                )
                ranked = MultiSignalRanker.rank_candidates(
                    candidates=expanded_candidates,
                    analyzed_query=analyzed,
                )
        else:
            ranked = MultiSignalRanker.rank_candidates(
                candidates=expanded_candidates,
                analyzed_query=analyzed,
            )

        # 4b. EvoReasoner Multi-Route Planning, Beam Search & Proof-Chain Aggregation (arXiv:2509.15464)
        use_evoreasoner = (
            enable_evoreasoner
            if enable_evoreasoner is not None
            else getattr(settings, "EVOREASONER_ENABLED", False)
        )
        proof_chains = []
        evoreasoner_applied = False
        evoreasoner_diagnostics: dict[str, Any] = {}

        if use_evoreasoner and repository_id is not None:
            try:
                from apps.api.src.services.evoreasoner.aggregator import ProofChainAggregator
                from apps.api.src.services.evoreasoner.beam_search import EvoBeamSearchEngine
                from apps.api.src.services.evoreasoner.planner import EvoRoutePlanner

                # Identify seed entities from query analysis and top retrieved candidates
                seed_entities = list(analyzed.symbol_candidates)
                if not seed_entities and ranked:
                    for r in ranked[:3]:
                        if r.candidate.name and r.candidate.name not in ("dependency", "import"):
                            seed_entities.append(r.candidate.name)

                # Generate bounded multi-route plan
                plan = EvoRoutePlanner.generate_multi_route_plan(
                    query_text=question,
                    seed_entities=seed_entities,
                )

                if plan.selected_routes:
                    search_res = await EvoBeamSearchEngine.search_paths(
                        session=session,
                        plan=plan,
                        repository_id=repository_id,
                        branch="main",
                    )

                    if search_res.paths:
                        agg_res = ProofChainAggregator.aggregate_paths(
                            paths=search_res.paths,
                            query_text=question,
                            temporal_intent=plan.temporal_intent,
                            repository_id=repository_id,
                            branch="main",
                        )
                        proof_chains = agg_res.chains
                        evoreasoner_applied = len(proof_chains) > 0
                        evoreasoner_diagnostics = {
                            "routes_planned": len(plan.selected_routes),
                            "paths_explored": search_res.total_paths_explored,
                            "paths_found": len(search_res.paths),
                            "proof_chains_aggregated": len(proof_chains),
                            "rejected_paths": agg_res.rejected_paths_count,
                            "deduplicated_chains": agg_res.deduplicated_chains_count,
                            **agg_res.aggregation_diagnostics,
                        }
                    else:
                        evoreasoner_diagnostics = {
                            "routes_planned": len(plan.selected_routes),
                            "paths_found": 0,
                            "search_diagnostics": search_res.search_diagnostics,
                        }
                else:
                    evoreasoner_diagnostics = {
                        "routes_planned": 0,
                        "fallback_reason": "no_routes_generated",
                    }
            except Exception as exc:
                evoreasoner_applied = False
                evoreasoner_diagnostics = {
                    "exception_occurred": True,
                    "error": str(exc),
                }

        # 5. Context Assembly & Budgeting
        assembled = ContextAssembler.assemble_context(
            ranked_candidates=ranked,
            proof_chains=proof_chains,
            evidence_paths=struct_evidence_paths,
            temporal_evidence=temporal_star_rag_evidence,
        )

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
                query_embedding=query_embedding,
                ranked_candidates=ranked,
            )

        # 5c. Global Repository Architecture Skeleton (Macro/Architecture Context Injection)
        skeleton_context = ""
        if analyzed.is_architectural_query or len(ranked) < 5:
            try:
                from apps.api.src.services.context_engine.skeleton import RepositorySkeletonBuilder

                skeleton_context = await RepositorySkeletonBuilder.build_skeleton(
                    session=session,
                    snapshot_id=snapshot_id,
                )
            except Exception:
                skeleton_context = ""

        # Convert retrieved knowledge and integration records into evidence items
        knowledge_evidence_items: list[dict[str, Any]] = []
        for rec in knowledge_records:
            source_type = rec.get("source_type") or "CUSTOMER"
            is_integration = source_type.upper() in ("GITHUB", "INTEGRATION") or bool(
                rec.get("source_reference_type")
            )
            ev_type = "integration" if is_integration else "knowledge"
            ref_type = rec.get("source_reference_type")
            ref_id = rec.get("source_reference_id")

            rec_score = float(rec.get("score", 1.0))
            norm_rel = min(1.0, max(0.2, round(rec_score / 15.0, 2)))

            file_identifier = (
                rec.get("related_file_path")
                or f"{source_type.lower()}/{ref_id or rec.get('title', 'note')}"
            )
            symbol_identifier = rec.get("related_symbol") or rec.get("title")

            item_dict: dict[str, Any] = {
                "type": ev_type,
                "file": file_identifier,
                "symbol": symbol_identifier,
                "lines": None,
                "relevance": norm_rel,
                "snippet": rec.get("content"),
                "source_type": source_type,
                "source_reference_type": ref_type,
                "source_reference_id": ref_id,
                "category": rec.get("category"),
                "title": rec.get("title"),
                "retrieval_reason": f"Project {ev_type} retrieval (score {rec_score})",
                "provenance": {
                    "id": rec.get("id"),
                    "source_type": source_type,
                    "source_reference_type": ref_type,
                    "source_reference_id": ref_id,
                    "title": rec.get("title"),
                    "category": rec.get("category"),
                    "knowledge_metadata": rec.get("knowledge_metadata", {}),
                },
            }
            knowledge_evidence_items.append(item_dict)
            if symbol_identifier and symbol_identifier not in assembled.related_entities:
                assembled.related_entities.append(symbol_identifier)

        # Check for explicit issue/PR requests that have no matching records
        query_explicit_issue_refs = set(
            re.findall(r"(?:#|issue\s*#?|pr\s*#?|pull\s*#?|ticket\s*#?)\s*(\d+)", question, re.IGNORECASE)
        )
        if query_explicit_issue_refs:
            matched_issue_refs = {
                str(rec.get("source_reference_id", "")).lstrip("#").strip()
                for rec in knowledge_records
                if rec.get("source_reference_id")
            }
            unmatched_requested_refs = query_explicit_issue_refs - matched_issue_refs
            if unmatched_requested_refs:
                GENERIC_TOKENS = {
                    "issue", "pr", "pull", "request", "ticket", "task", "say", "about",
                    "what", "how", "why", "when", "does", "the", "for", "and", "or", "to", "in"
                }
                meaningful_kws = [
                    k.lower() for k in analyzed.keywords
                    if k.lower() not in GENERIC_TOKENS and k not in query_explicit_issue_refs and len(k) > 1
                ]
                has_code_grounding = any(
                    any(kw in c.name.lower() or kw in c.path.lower() or (c.content and kw in c.content.lower()) for kw in meaningful_kws)
                    for c in raw_candidates
                )
                if not has_code_grounding:
                    missing_str = ", ".join([f"#{r}" for r in sorted(unmatched_requested_refs)])
                    abstention_content = (
                        f"### Insufficient Evidence\n\n"
                        f"I searched the project context and connected integrations for **{missing_str}** "
                        f"('{question}'), but did not find matching issues, pull requests, or specifications.\n\n"
                        f"No matching integration records or implementation code were found in the project."
                    )
                    return GroundedAnswer(
                        content=abstention_content,
                        evidence=[],
                        related_entities=[],
                        confidence="LOW",
                        debug_signals={
                            "is_abstention": True,
                            "missing_integration_reference": list(unmatched_requested_refs),
                            "synthesis_gated": True,
                            "model": getattr(self.llm_provider, "model_name", "grounded-engine"),
                            "provider": getattr(self.llm_provider, "provider_name", "offline"),
                        },
                    )

        # Merge evidence items: prioritize integration/knowledge if relevant, or combine with code
        if knowledge_evidence_items:
            has_strong_knowledge = any(k.get("score", 0.0) >= 5.0 for k in knowledge_records)
            has_explicit_ref = any(
                k.get("source_reference_id") and k["source_reference_id"].lower() in question.lower()
                for k in knowledge_records
            )
            if has_strong_knowledge or has_explicit_ref or not assembled.evidence_items:
                all_evidence_items = knowledge_evidence_items + assembled.evidence_items
            else:
                all_evidence_items = assembled.evidence_items + knowledge_evidence_items
        else:
            all_evidence_items = assembled.evidence_items

        assembled.evidence_items = all_evidence_items

        full_prompt_context = assembled.prompt_context
        if skeleton_context:
            full_prompt_context = f"{skeleton_context}\n\n## DETAILED REPOSITORY CODE EVIDENCE\n{full_prompt_context}"
        if knowledge_context:
            if full_prompt_context:
                full_prompt_context = f"{knowledge_context}\n\n{full_prompt_context}"
            else:
                full_prompt_context = knowledge_context

        # 6. LLM Grounded Synthesis (Claude, Groq, or deterministic offline)
        answer = await self.llm_provider.generate_grounded_answer(
            question=question,
            project_context=full_prompt_context,
            evidence_items=all_evidence_items,
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
                "is_architectural_query": analyzed.is_architectural_query,
                "skeleton_injected": bool(skeleton_context),
                "vector_search_used": has_vector,
                "semantic_search_used": has_semantic,
                "graph_traversal_depth": 2,
                "candidates_retrieved": len(raw_candidates),
                "candidates_expanded": len(expanded_candidates),
                "customer_knowledge_count": len(knowledge_records),
                "top_score": ranked[0].score if ranked else 0.0,
                "memotime_used": memotime_success if use_memotime else False,
                "memotime_diagnostics": memotime_diagnostics,
                "star_rag_used": star_rag_applied if should_route_temporal else False,
                "star_rag_diagnostics": star_rag_diagnostics,
                "star_rag_temporal_evidence_count": len(temporal_star_rag_evidence),
                "star_rag_temporal_routing_decision": temporal_route_reason,
                "structure_aware_star_rag_used": (
                    struct_star_rag_applied if should_route_star else False
                ),
                "structure_aware_star_rag_diagnostics": struct_star_rag_diagnostics,
                "star_rag_evidence_paths_count": len(struct_evidence_paths),
                "star_rag_routing_decision": route_reason,
                "evoreasoner_used": evoreasoner_applied if use_evoreasoner else False,
                "evoreasoner_diagnostics": evoreasoner_diagnostics,
                "proof_chains_count": len(proof_chains),
                "synthesis_gated": answer.debug_signals.get("is_abstention", False),
            }
        )

        return answer
