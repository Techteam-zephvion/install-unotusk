"""
Granular Evidence Path Constructor for Structure-Aware STAR-RAG.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).

Connects ranked candidates to topic entities using explicit, validated,
directed evidence paths with function-level and file-level provenance.
"""

from __future__ import annotations

import uuid

from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraph,
    FunctionGraphEdge,
    GranularEvidenceHop,
    GranularEvidencePath,
)


class GranularEvidencePathBuilder:
    """
    Constructs multi-hop evidence paths between seed/topic entities and retrieved candidates.
    Supports function-level CALLS paths as well as file-level IMPORTS paths.
    """

    def __init__(self, max_path_depth: int = 4, max_paths_per_candidate: int = 3):
        self.max_path_depth = max_path_depth
        self.max_paths_per_candidate = max_paths_per_candidate

    def find_paths_between(
        self,
        graph: FunctionGraph,
        source_id: str,
        target_id: str,
    ) -> list[list[FunctionGraphEdge]]:
        """
        Finds all simple directed paths between source_id and target_id up to max_path_depth.
        Cycle-safe via visited path tracking.
        """
        if source_id == target_id:
            return []

        paths: list[list[FunctionGraphEdge]] = []
        queue: list[tuple[str, list[FunctionGraphEdge], set[str]]] = [
            (source_id, [], {source_id})
        ]

        while queue and len(paths) < self.max_paths_per_candidate:
            curr_node, curr_path, visited = queue.pop(0)

            if len(curr_path) >= self.max_path_depth:
                continue

            for edge in graph.out_edges.get(curr_node, []):
                next_node = edge.target_id
                if next_node == target_id:
                    paths.append(curr_path + [edge])
                    if len(paths) >= self.max_paths_per_candidate:
                        break
                elif next_node not in visited and len(curr_path) + 1 < self.max_path_depth:
                    new_visited = set(visited)
                    new_visited.add(next_node)
                    queue.append((next_node, curr_path + [edge], new_visited))

        return paths

    def build_evidence_paths_for_candidates(
        self,
        candidates: list[RetrievedCandidate],
        graph: FunctionGraph,
        seed_node_ids: set[str],
    ) -> list[GranularEvidencePath]:
        """
        Discovers and constructs verifiable evidence paths from seed entities to each candidate.
        Attaches the best path into candidate.metadata['relationship_path'] and alternatives.
        """
        evidence_paths: list[GranularEvidencePath] = []

        for cand in candidates:
            # Determine candidate graph node ID
            candidate_node_ids = [
                cand.candidate_id,
                f"sym:{cand.symbol_id}" if cand.symbol_id else None,
                f"file:{cand.file_id}" if cand.file_id else None,
                f"{cand.path}::{cand.name}",
            ]
            valid_cand_ids = [cid for cid in candidate_node_ids if cid and cid in graph.nodes]
            if not valid_cand_ids:
                continue

            target_id = valid_cand_ids[0]

            # If candidate was already a seed, record direct seed status
            if target_id in seed_node_ids or cand.metadata.get("is_seed"):
                continue

            all_raw_paths: list[list[FunctionGraphEdge]] = []
            for seed_id in seed_node_ids:
                if seed_id in graph.nodes:
                    found = self.find_paths_between(graph, seed_id, target_id)
                    all_raw_paths.extend(found)
                    if len(all_raw_paths) >= self.max_paths_per_candidate:
                        break

            if not all_raw_paths:
                continue

            # Sort paths by length (shortest first)
            all_raw_paths.sort(key=len)

            cand_alt_paths: list[str] = []
            primary_path_str: str | None = None

            for p_idx, edge_chain in enumerate(all_raw_paths):
                hops: list[GranularEvidenceHop] = []
                path_tokens: list[str] = []

                for h_idx, e in enumerate(edge_chain):
                    src_n = graph.nodes.get(e.source_id)
                    tgt_n = graph.nodes.get(e.target_id)

                    src_name = src_n.name if src_n else e.source_id
                    tgt_name = tgt_n.name if tgt_n else e.target_id

                    src_file = src_n.file_path if src_n else e.source_file
                    tgt_file = tgt_n.file_path if tgt_n else e.target_file

                    rel_str = e.relation_type.value if hasattr(e.relation_type, "value") else str(e.relation_type)

                    hop = GranularEvidenceHop(
                        hop_index=h_idx,
                        source_node_id=e.source_id,
                        source_name=src_name,
                        source_file=src_file,
                        relation=rel_str,
                        target_node_id=e.target_id,
                        target_name=tgt_name,
                        target_file=tgt_file,
                        line_number=e.line_number,
                    )
                    hops.append(hop)

                    if h_idx == 0:
                        path_tokens.append(f"{src_file}:{src_name}")
                    path_tokens.append(f"-> [{rel_str}] ->")
                    path_tokens.append(f"{tgt_file}:{tgt_name}")

                full_path_str = " ".join(path_tokens)

                if p_idx == 0:
                    primary_path_str = full_path_str
                else:
                    cand_alt_paths.append(full_path_str)

                path_id = f"path:{uuid.uuid4().hex[:12]}"
                evidence_path = GranularEvidencePath(
                    path_id=path_id,
                    source_entity=hops[0].source_name if hops else "",
                    target_entity=hops[-1].target_name if hops else "",
                    hops=hops,
                    full_path_str=full_path_str,
                    confidence=1.0 - (0.15 * (len(hops) - 1)),
                    provenance={
                        "source_file": hops[0].source_file if hops else "",
                        "target_file": hops[-1].target_file if hops else "",
                        "hop_count": len(hops),
                    },
                )
                evidence_paths.append(evidence_path)

            # Update candidate metadata with validated provenance paths
            if primary_path_str:
                cand.metadata["relationship_path"] = primary_path_str
                cand.metadata["relationship_hop"] = len(all_raw_paths[0])
                cand.metadata["connected_from"] = all_raw_paths[0][0].source_id
                cand.metadata["retrieval_reason"] = f"STAR-RAG verified path ({len(all_raw_paths[0])} hops)"
                if cand_alt_paths:
                    existing_alts = list(cand.metadata.get("alternative_paths", []))
                    for ap in cand_alt_paths:
                        if ap not in existing_alts:
                            existing_alts.append(ap)
                    cand.metadata["alternative_paths"] = existing_alts

        return evidence_paths
