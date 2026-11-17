"""
Decoupled Topological Propagation (DTP) for Structure-Aware STAR-RAG.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).

Extracts directed degree distributions and multi-order graph connectivity features
and propagates structural context through a separate channel independent of text semantics.
"""

from __future__ import annotations

import math

from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.types import (
    DTPNodeFeatures,
    FunctionGraph,
    FunctionGraphEdge,
    FunctionGraphNode,
)


class DecoupledTopologicalPropagator:
    """
    Computes decoupled topological features on the code graph:
    1. Directed degrees: in-degree, out-degree, and directionality ratio.
    2. Multi-order transition connectivity across k-hop paths.
    3. Dedicated structural propagation score independent of text embeddings.
    """

    def __init__(
        self,
        max_hops: int = 3,
        decay_factor: float = 0.75,
        in_degree_weight: float = 0.60,
        out_degree_weight: float = 0.40,
    ):
        self.max_hops = max_hops
        self.decay_factor = decay_factor
        self.in_degree_weight = in_degree_weight
        self.out_degree_weight = out_degree_weight

    def extract_directed_features(
        self,
        nodes: dict[str, FunctionGraphNode],
        edges: list[FunctionGraphEdge],
    ) -> dict[str, DTPNodeFeatures]:
        """
        Extracts in-degree, out-degree, directional ratio, and log-density for all nodes.
        """
        in_degrees: dict[str, int] = {nid: 0 for nid in nodes}
        out_degrees: dict[str, int] = {nid: 0 for nid in nodes}

        for edge in edges:
            if edge.source_id in out_degrees:
                out_degrees[edge.source_id] += 1
            if edge.target_id in in_degrees:
                in_degrees[edge.target_id] += 1

        features: dict[str, DTPNodeFeatures] = {}
        for nid in nodes:
            d_in = in_degrees[nid]
            d_out = out_degrees[nid]
            total = d_in + d_out
            dir_ratio = d_in / max(1e-4, float(total))
            density = math.log1p(total)

            features[nid] = DTPNodeFeatures(
                node_id=nid,
                in_degree=d_in,
                out_degree=d_out,
                directed_ratio=dir_ratio,
                density=density,
                multi_order_reachability={},
                structural_score=0.0,
            )

        return features

    def compute_multi_order_connectivity(
        self,
        nodes: dict[str, FunctionGraphNode],
        edges: list[FunctionGraphEdge],
        seed_node_ids: set[str],
        features: dict[str, DTPNodeFeatures],
    ) -> dict[str, DTPNodeFeatures]:
        """
        Propagates structural information across multi-order hops from seed nodes.
        Computes k-hop reachability distributions and structural context scores.
        """
        if not nodes:
            return features

        # Build adjacency mapping: source -> list of targets
        adj: dict[str, list[str]] = {nid: [] for nid in nodes}
        for edge in edges:
            if edge.source_id in adj and edge.target_id in nodes:
                adj[edge.source_id].append(edge.target_id)

        # Initialize distribution at seed nodes
        valid_seeds = [s for s in seed_node_ids if s in nodes]
        if not valid_seeds:
            # If no seed in graph, uniform initialization across all nodes
            init_val = 1.0 / max(1, len(nodes))
            current_prob = {nid: init_val for nid in nodes}
        else:
            init_val = 1.0 / len(valid_seeds)
            current_prob = {nid: (init_val if nid in valid_seeds else 0.0) for nid in nodes}

        # Multi-order propagation iterations (layer l from 1 to max_hops)
        for hop in range(1, self.max_hops + 1):
            next_prob: dict[str, float] = {nid: 0.0 for nid in nodes}

            for u, prob_u in current_prob.items():
                if prob_u <= 1e-6:
                    continue
                neighbors = adj.get(u, [])
                if neighbors:
                    out_deg = len(neighbors)
                    p_trans = prob_u / out_deg
                    for v in neighbors:
                        next_prob[v] += p_trans
                else:
                    # Self-loop retention on sinks
                    next_prob[u] += prob_u * 0.5

            # Record k-hop reachability in node features
            for nid, prob in next_prob.items():
                if nid in features:
                    features[nid].multi_order_reachability[hop] = prob

            current_prob = next_prob

        # Calculate final decoupled structural score for each node
        for _nid, feat in features.items():
            hop_sum = 0.0
            for hop, p in feat.multi_order_reachability.items():
                hop_weight = self.decay_factor ** (hop - 1)
                hop_sum += p * hop_weight

            # Normalize degree component: hubs and incoming targets get structural credit
            degree_factor = (
                self.in_degree_weight * math.tanh(feat.in_degree / 3.0)
                + self.out_degree_weight * math.tanh(feat.out_degree / 5.0)
            )

            # Combined decoupled structural score bounded in [0.0, 1.0]
            raw_struct = (hop_sum * 0.70) + (degree_factor * 0.30)
            feat.structural_score = min(1.0, round(raw_struct, 4))

        return features

    def propagate_and_score_candidates(
        self,
        candidates: list[RetrievedCandidate],
        graph: FunctionGraph,
        seed_node_ids: set[str],
    ) -> list[RetrievedCandidate]:
        """
        Attaches decoupled structural score to candidate signals under 'dtp_structural'.
        """
        features = self.extract_directed_features(graph.nodes, graph.edges)
        features = self.compute_multi_order_connectivity(
            graph.nodes, graph.edges, seed_node_ids, features
        )

        for cand in candidates:
            # Map candidate to graph node ID: check file, symbol, or chunk prefix
            matched_score = 0.0
            possible_ids = [
                cand.candidate_id,
                f"sym:{cand.symbol_id}" if cand.symbol_id else None,
                f"file:{cand.file_id}" if cand.file_id else None,
                f"{cand.path}::{cand.name}",
            ]
            for pid in possible_ids:
                if pid and pid in features:
                    matched_score = max(matched_score, features[pid].structural_score)

            # If node had zero in/out degrees but is a direct seed candidate
            if matched_score == 0.0 and cand.metadata.get("is_seed"):
                matched_score = 0.40  # Seed baseline topological prior

            cand.signals["dtp_structural"] = round(matched_score, 4)

        return candidates
