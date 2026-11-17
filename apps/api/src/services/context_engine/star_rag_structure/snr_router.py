"""
Semantic Noise Routing (SNR) for Structure-Aware STAR-RAG.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).

Applies question-conditioned semantic gates to filter and suppress weakly relevant
or noisy graph edges prior to neighborhood aggregation during graph expansion.
"""

from __future__ import annotations

import math
import re

from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.retriever import (
    compute_cosine_similarity,
    generate_text_embedding,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraphEdge,
    FunctionGraphNode,
    GraphRelationType,
    SNREdgeDecision,
)


class SemanticNoiseRouter:
    """
    Evaluates semantic message relevance along graph edges conditioned on the user query.
    Implements the SNR gate formulation:
        alpha_ij = sigma(W_g * [h_i || e_ij || q])
    combined with semantic similarity modulation to suppress noise before aggregation.
    """

    def __init__(
        self,
        noise_threshold: float = 0.30,
        semantic_weight: float = 0.70,
        temperature: float = 1.0,
    ):
        self.noise_threshold = noise_threshold
        self.semantic_weight = semantic_weight
        self.temperature = max(1e-4, temperature)
        self._target_sim_cache: dict[str, float] = {}
        self._target_emb_cache: dict[str, list[float]] = {}
        # Relation type base priors
        self.relation_priors: dict[GraphRelationType, float] = {
            GraphRelationType.CALLS: 0.85,
            GraphRelationType.DEFINES: 0.80,
            GraphRelationType.INHERITS: 0.75,
            GraphRelationType.IMPORTS: 0.60,
            GraphRelationType.REFERENCES: 0.65,
        }

    def _compute_lexical_overlap(self, text: str, query_tokens: list[str]) -> float:
        """Calculates token overlap ratio when vector embeddings are unavailable."""
        if not text or not query_tokens:
            return 0.0
        text_lower = text.lower()
        words = re.findall(r"[a-z0-9_]+", text_lower)
        if not words:
            return 0.0
        matches = sum(1 for q in query_tokens if any(q in w for w in words))
        return min(1.0, matches / max(1, len(query_tokens)))

    def evaluate_edge(
        self,
        edge: FunctionGraphEdge,
        query_text: str,
        query_embedding: list[float] | None,
        source_node: FunctionGraphNode | None,
        target_node: FunctionGraphNode | None,
        analyzed_query: AnalyzedQuery | None = None,
    ) -> SNREdgeDecision:
        """
        Evaluates question-conditioned gate on a directed graph edge.
        Returns SNREdgeDecision with acceptance status, score, and explanation.
        """
        q_tokens: list[str] = []
        if analyzed_query and analyzed_query.keywords:
            q_tokens = [k.lower() for k in analyzed_query.keywords]
        else:
            q_tokens = [w.lower() for w in re.findall(r"[a-z0-9_]+", query_text) if len(w) > 2]

        # 1. Target node semantic score against query (memoized per target node)
        target_sem_sim = 0.0
        target_desc = ""
        cache_key = target_node.node_id if target_node else edge.target_id
        if cache_key in self._target_sim_cache:
            target_sem_sim = self._target_sim_cache[cache_key]
        elif target_node:
            target_desc = f"{target_node.name} {target_node.qualified_name} {target_node.signature} {target_node.content}"
            tgt_meta_emb = target_node.metadata.get("embedding") if target_node.metadata else None
            if tgt_meta_emb and query_embedding and len(tgt_meta_emb) == len(query_embedding):
                target_sem_sim = compute_cosine_similarity(query_embedding, tgt_meta_emb)
            elif query_embedding:
                if target_node.node_id in self._target_emb_cache:
                    target_emb = self._target_emb_cache[target_node.node_id]
                else:
                    target_emb = generate_text_embedding(target_desc)
                    self._target_emb_cache[target_node.node_id] = target_emb
                target_sem_sim = compute_cosine_similarity(query_embedding, target_emb)
            else:
                target_sem_sim = self._compute_lexical_overlap(target_desc, q_tokens)
            self._target_sim_cache[cache_key] = target_sem_sim
        else:
            # External or unresolved target: evaluate based on edge target identifier
            target_desc = edge.target_id.split("::")[-1]
            target_sem_sim = self._compute_lexical_overlap(target_desc, q_tokens)
            self._target_sim_cache[cache_key] = target_sem_sim

        # 2. Relation prior
        rel_prior = self.relation_priors.get(edge.relation_type, 0.60)

        # 3. Question-conditioned gate formulation: alpha = sigma(logit / temperature)
        # Logit blends semantic similarity, relation affinity, and query intent
        sim_component = target_sem_sim
        logit = (sim_component * 2.5) + (rel_prior * 0.8) - 1.5

        # Query keyword, symbol, or path match boost (ignore single-char noise)
        if analyzed_query:
            target_name_lower = target_desc.lower()
            if any(len(s) >= 2 and s.lower() in target_name_lower for s in analyzed_query.symbol_candidates):
                logit += 1.8
            if any(len(p) >= 2 and p.lower() in target_name_lower for p in analyzed_query.path_candidates):
                logit += 1.2
            if any(
                len(k) >= 3 and (k.lower() in target_name_lower or k.lower().rstrip("s") in target_name_lower)
                for k in analyzed_query.keywords
            ):
                logit += 1.2

        # Sigmoid gate calculation
        try:
            gate_alpha = 1.0 / (1.0 + math.exp(-logit / self.temperature))
        except OverflowError:
            gate_alpha = 1.0 if logit > 0 else 0.0

        # Effective semantic relevance
        relevance = (self.semantic_weight * gate_alpha) + ((1.0 - self.semantic_weight) * max(0.0, target_sem_sim))

        is_accepted = relevance >= self.noise_threshold
        rejection_reason = None
        if not is_accepted:
            rejection_reason = (
                f"Suppressed as semantic noise: target '{target_desc[:40]}' "
                f"relevance ({relevance:.3f}) below threshold ({self.noise_threshold:.3f})"
            )

        return SNREdgeDecision(
            edge=edge,
            gate_weight=gate_alpha,
            semantic_relevance=relevance,
            is_accepted=is_accepted,
            rejection_reason=rejection_reason,
        )

    def route_and_filter_edges(
        self,
        edges: list[FunctionGraphEdge],
        nodes: dict[str, FunctionGraphNode],
        query_text: str,
        query_embedding: list[float] | None,
        analyzed_query: AnalyzedQuery | None = None,
        seed_node_ids: set[str] | None = None,
    ) -> tuple[list[FunctionGraphEdge], list[SNREdgeDecision]]:
        """
        Applies SNR to a collection of edges during graph traversal.
        Preserves edges connecting seed nodes unconditionally to maintain baseline connectivity.
        """
        accepted_edges: list[FunctionGraphEdge] = []
        all_decisions: list[SNREdgeDecision] = []
        seeds = seed_node_ids or set()
        seen_edges: set[tuple[str, str, str]] = set()

        for edge in edges:
            rel_str = edge.relation_type.value if hasattr(edge.relation_type, "value") else str(edge.relation_type)
            edge_key = (edge.source_id, edge.target_id, rel_str)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            # Unconditionally accept seed-to-seed core edges
            if edge.source_id in seeds and edge.target_id in seeds:
                dec = SNREdgeDecision(
                    edge=edge,
                    gate_weight=1.0,
                    semantic_relevance=1.0,
                    is_accepted=True,
                    rejection_reason="Unconditional seed-to-seed edge preservation",
                )
                accepted_edges.append(edge)
                all_decisions.append(dec)
                continue

            src_node = nodes.get(edge.source_id)
            tgt_node = nodes.get(edge.target_id)

            decision = self.evaluate_edge(
                edge=edge,
                query_text=query_text,
                query_embedding=query_embedding,
                source_node=src_node,
                target_node=tgt_node,
                analyzed_query=analyzed_query,
            )
            all_decisions.append(decision)

            if decision.is_accepted:
                accepted_edges.append(edge)

        return accepted_edges, all_decisions
