"""
Structure-Aware STAR-RAG Service Orchestrator.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).

Integrates:
1. AST Function-Level & Dependency Graph Construction.
2. SNR — Semantic Noise Routing on graph edges before aggregation.
3. DTP — Decoupled Topological Propagation for directed & multi-order structural scoring.
4. SSAF — Semantic-Structural Adaptive Fusion for query-conditioned candidate ranking.
5. Granular Evidence Path Construction with verifiable code provenance.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.dtp_propagator import (
    DecoupledTopologicalPropagator,
)
from apps.api.src.services.context_engine.star_rag_structure.evidence_paths import (
    GranularEvidencePathBuilder,
)
from apps.api.src.services.context_engine.star_rag_structure.graph_extractor import (
    CodeGraphExtractor,
)
from apps.api.src.services.context_engine.star_rag_structure.snr_router import (
    SemanticNoiseRouter,
)
from apps.api.src.services.context_engine.star_rag_structure.ssaf_fusion import (
    SemanticStructuralAdaptiveFusion,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraph,
    StructureAwareStarRagResult,
)

logger = logging.getLogger(__name__)


class StructureAwareStarRagService:
    """
    Main orchestration service for the Structure-Aware STAR-RAG pipeline.
    """

    @classmethod
    async def run_pipeline_async(
        cls,
        candidates: list[RetrievedCandidate],
        query_text: str,
        analyzed_query: AnalyzedQuery | None = None,
        query_embedding: list[float] | None = None,
        session: AsyncSession | None = None,
        snapshot_id: uuid.UUID | None = None,
        enable_snr: bool = True,
        enable_dtp: bool = True,
        enable_ssaf: bool = True,
    ) -> tuple[list[RankedCandidate], StructureAwareStarRagResult]:
        """
        Executes the full Structure-Aware STAR-RAG retrieval pipeline.
        Returns the ranked candidates and full diagnostic telemetry.
        """
        if not candidates:
            res = StructureAwareStarRagResult(
                candidates=[],
                is_fallback=True,
                fallback_reason="Empty candidate list provided to STAR-RAG",
            )
            return [], res

        try:
            # 1. Graph Construction / Retrieval: Use multi-tier cache (Memory + Redis)
            graph = None
            cache_hit = False
            if snapshot_id is not None and getattr(settings, "STRUCTURE_AWARE_GRAPH_CACHE_ENABLED", True):
                from apps.api.src.services.context_engine.star_rag_structure.cache import (
                    CodeGraphCache,
                )

                graph = await CodeGraphCache.get_graph(
                    snapshot_id=snapshot_id,
                    session=session,
                )
                if graph is not None and len(graph.nodes) > 0:
                    cache_hit = True

            if graph is None:
                if session is not None and snapshot_id is not None:
                    file_ids = [c.file_id for c in candidates if c.file_id]
                    graph = await CodeGraphExtractor.build_graph_for_snapshot(
                        session=session,
                        snapshot_id=snapshot_id,
                        file_ids=file_ids,
                    )
                else:
                    graph = FunctionGraph()

            # Ensure all candidates have a corresponding node in the graph
            for cand in candidates:
                if cand.candidate_id not in graph.nodes:
                    from apps.api.src.services.context_engine.star_rag_structure.types import (
                        FunctionGraphNode,
                        GraphNodeType,
                    )
                    n_type = GraphNodeType.FUNCTION if cand.entity_type == "SYMBOL" else GraphNodeType.FILE
                    graph.add_node(
                        FunctionGraphNode(
                            node_id=cand.candidate_id,
                            name=cand.name,
                            qualified_name=cand.path,
                            node_type=n_type,
                            file_path=cand.path,
                            file_id=cand.file_id,
                            symbol_id=cand.symbol_id,
                        )
                    )

            # Identify seed node IDs from top initial candidates
            seed_ids: set[str] = set()
            for cand in candidates[:5]:
                seed_ids.add(cand.candidate_id)
                if cand.symbol_id:
                    seed_ids.add(f"sym:{cand.symbol_id}")
                if cand.file_id:
                    seed_ids.add(f"file:{cand.file_id}")
                seed_ids.add(f"{cand.path}::{cand.name}")

            # 2. Semantic Noise Routing (SNR)
            snr_decisions = []
            active_edges = graph.edges
            if enable_snr:
                snr_threshold = getattr(settings, "STRUCTURE_AWARE_SNR_THRESHOLD", 0.30)
                snr_router = SemanticNoiseRouter(noise_threshold=snr_threshold)
                active_edges, snr_decisions = snr_router.route_and_filter_edges(
                    edges=graph.edges,
                    nodes=graph.nodes,
                    query_text=query_text,
                    query_embedding=query_embedding,
                    analyzed_query=analyzed_query,
                    seed_node_ids=seed_ids,
                )
                # Update graph with noise-filtered edges
                graph.edges = active_edges
                graph.out_edges = {}
                graph.in_edges = {}
                for e in active_edges:
                    graph.out_edges.setdefault(e.source_id, []).append(e)
                    graph.in_edges.setdefault(e.target_id, []).append(e)

            # 3. Decoupled Topological Propagation (DTP) with Hub Attenuation
            dtp_features = {}
            if enable_dtp:
                max_hops = getattr(settings, "STRUCTURE_AWARE_DTP_MAX_DEPTH", 3)
                dtp_decay = getattr(settings, "STRUCTURE_AWARE_DTP_DECAY", 0.75)
                hub_attenuation = getattr(settings, "STRUCTURE_AWARE_DTP_HUB_ATTENUATION", True)
                attenuation_factor = getattr(settings, "STRUCTURE_AWARE_DTP_KAPPA", 0.75)
                dtp = DecoupledTopologicalPropagator(
                    max_hops=max_hops,
                    decay_factor=dtp_decay,
                    hub_attenuation=hub_attenuation,
                    attenuation_factor=attenuation_factor,
                )
                dtp_features = dtp.extract_directed_features(graph.nodes, graph.edges)
                dtp_features = dtp.compute_multi_order_connectivity(
                    graph.nodes, graph.edges, seed_ids, dtp_features
                )
                candidates = dtp.propagate_and_score_candidates(
                    candidates=candidates,
                    graph=graph,
                    seed_node_ids=seed_ids,
                )

            # 4. Granular Evidence Path Construction
            path_builder = GranularEvidencePathBuilder(max_path_depth=4)
            evidence_paths = path_builder.build_evidence_paths_for_candidates(
                candidates=candidates,
                graph=graph,
                seed_node_ids=seed_ids,
            )

            # 5. Semantic-Structural Adaptive Fusion (SSAF)
            ranked_candidates: list[RankedCandidate]
            ssaf_results = []
            if enable_ssaf:
                conflict_thresh = getattr(settings, "STRUCTURE_AWARE_SSAF_CONFLICT_THRESHOLD", 0.40)
                max_struct_weight = getattr(settings, "STRUCTURE_AWARE_SSAF_STRUCTURAL_WEIGHT", 0.15)
                ssaf = SemanticStructuralAdaptiveFusion(
                    conflict_threshold=conflict_thresh,
                    max_structural_weight=max_struct_weight,
                )
                ranked_candidates, ssaf_results = ssaf.fuse_and_rank_candidates(
                    candidates=candidates,
                    query_text=query_text,
                    analyzed_query=analyzed_query,
                )
            else:
                from apps.api.src.services.context_engine.ranker import MultiSignalRanker

                ranked_candidates = MultiSignalRanker.rank_candidates(
                    candidates=candidates,
                    analyzed_query=analyzed_query or AnalyzedQuery(raw_query=query_text),
                )

            diagnostics = {
                "nodes_count": len(graph.nodes),
                "total_edges": len(graph.edges),
                "snr_filtered_edges": len(snr_decisions) - len(active_edges),
                "evidence_paths_found": len(evidence_paths),
                "ssaf_conflicts_detected": sum(1 for s in ssaf_results if s.is_conflict),
                "graph_cache_hit": cache_hit,
                "hub_attenuation_enabled": getattr(settings, "STRUCTURE_AWARE_DTP_HUB_ATTENUATION", True),
                "snr_enabled": enable_snr,
                "dtp_enabled": enable_dtp,
                "ssaf_enabled": enable_ssaf,
            }

            result_obj = StructureAwareStarRagResult(
                candidates=[r.candidate for r in ranked_candidates],
                snr_decisions=snr_decisions,
                dtp_features=dtp_features,
                ssaf_results=ssaf_results,
                evidence_paths=evidence_paths,
                diagnostics=diagnostics,
                is_fallback=False,
            )
            return ranked_candidates, result_obj

        except Exception as exc:
            logger.error("Error in Structure-Aware STAR-RAG pipeline: %s", exc, exc_info=True)
            from apps.api.src.services.context_engine.ranker import MultiSignalRanker
            fallback_ranked = MultiSignalRanker.rank_candidates(
                candidates=candidates,
                analyzed_query=analyzed_query or AnalyzedQuery(raw_query=query_text),
            )
            res = StructureAwareStarRagResult(
                candidates=[r.candidate for r in fallback_ranked],
                is_fallback=True,
                fallback_reason=str(exc),
                diagnostics={"exception": str(exc)},
            )
            return fallback_ranked, res
