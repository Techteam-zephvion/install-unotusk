"""
Multi-Signal Concept Clusterer and Graph Partitioner.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept (OntoRAG arXiv:2506.00664).

Provides:
1. Lexical subword token decomposition (camelCase / snake_case).
2. Structural file/namespace path proximity scoring.
3. Deterministic semantic embedding cosine similarity.
4. Composite multi-signal similarity evaluation.
5. Graph community detection via deterministic label propagation / connected components
   (Disclosed label: LIGHTWEIGHT_DETERMINISTIC_GRAPH_PARTITIONER).
6. Concept deduplication and evidence-preserving merging.
"""

import logging
import os
import re
from collections import defaultdict
from typing import Any

from apps.api.src.services.context_engine.retriever import (
    compute_cosine_similarity,
    generate_text_embedding,
)
from experiments.e2_ontology_guided_extraction.schema import (
    CandidateConcept,
    EvidenceProvenance,
    ProposalStatus,
)

logger = logging.getLogger(__name__)


def split_identifier_tokens(name: str) -> set[str]:
    """
    Decomposes camelCase, PascalCase, and snake_case identifiers into normalized tokens.
    E.g. 'StripePaymentService' -> {'stripe', 'payment', 'service'}
    E.g. 'verify_auth_token' -> {'verify', 'auth', 'token'}
    """
    if not name or not isinstance(name, str):
        return set()

    # Replace non-alphanumeric characters with spaces
    cleaned = re.sub(r"[^A-Za-z0-9]", " ", name)
    # Split camelCase / PascalCase transitions
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1 \2", cleaned)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s1)

    tokens = {t.lower() for t in s2.split() if len(t) > 1}
    return tokens


def compute_token_jaccard(tokens1: set[str], tokens2: set[str]) -> float:
    """Computes Jaccard similarity between two token sets."""
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


def compute_path_proximity(path1: str, path2: str) -> float:
    """
    Computes structural directory/module hierarchy proximity.
    Returns 1.0 for identical parent paths, proportional to common ancestor depth.
    """
    if not path1 or not path2:
        return 0.0

    p1 = os.path.normpath(path1).replace("\\", "/").strip("/").split("/")
    p2 = os.path.normpath(path2).replace("\\", "/").strip("/").split("/")

    # Remove filename if paths point to files
    dir1 = p1[:-1] if len(p1) > 1 else p1
    dir2 = p2[:-1] if len(p2) > 1 else p2

    common_prefix = 0
    for a, b in zip(dir1, dir2, strict=False):
        if a.lower() == b.lower():
            common_prefix += 1
        else:
            break

    total = len(dir1) + len(dir2)
    if total == 0:
        return 1.0
    return (2.0 * common_prefix) / total


class ConceptClusterer:
    """
    Multi-signal concept clustering and graph community detection engine.
    Adapts OntoRAG (arXiv:2506.00664 §3.2-3.3) for Code Lane AST and entity inputs.
    """

    PARTITIONER_LABEL = "LIGHTWEIGHT_DETERMINISTIC_GRAPH_PARTITIONER"

    def __init__(
        self,
        similarity_threshold: float = 0.70,
        token_weight: float = 0.40,
        path_weight: float = 0.30,
        embedding_weight: float = 0.30,
    ):
        if not (0.0 <= similarity_threshold <= 1.0):
            raise ValueError(f"Similarity threshold must be in [0, 1], got {similarity_threshold}")
        total_w = token_weight + path_weight + embedding_weight
        if abs(total_w - 1.0) > 1e-4:
            # Normalize weights
            token_weight /= total_w
            path_weight /= total_w
            embedding_weight /= total_w

        self.threshold = similarity_threshold
        self.w_token = token_weight
        self.w_path = path_weight
        self.w_embedding = embedding_weight
        self._embedding_cache: dict[str, list[float]] = {}

    def _get_embedding(self, text: str) -> list[float]:
        if text not in self._embedding_cache:
            self._embedding_cache[text] = generate_text_embedding(text, dim=1536)
        return self._embedding_cache[text]

    def compute_entity_similarity(
        self,
        name1: str,
        path1: str,
        name2: str,
        path2: str,
        context1: str = "",
        context2: str = "",
    ) -> float:
        """
        Computes composite multi-signal similarity between two code entities.
        Combines lexical token Jaccard, namespace path proximity, and semantic vector similarity.
        """
        if name1.strip().lower() == name2.strip().lower():
            return 1.0

        # 1. Lexical token Jaccard
        tokens1 = split_identifier_tokens(name1)
        tokens2 = split_identifier_tokens(name2)
        token_sim = compute_token_jaccard(tokens1, tokens2)

        # 2. Structural path proximity
        path_sim = compute_path_proximity(path1, path2)

        # 3. Vector embedding cosine similarity
        text1 = f"{name1} {path1} {context1}".strip()
        text2 = f"{name2} {path2} {context2}".strip()
        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)
        vec_sim = compute_cosine_similarity(emb1, emb2)

        composite = (
            self.w_token * token_sim +
            self.w_path * path_sim +
            self.w_embedding * vec_sim
        )
        return max(0.0, min(1.0, composite))

    def cluster_entities(
        self,
        entities: list[dict[str, Any]],
        threshold: float | None = None,
    ) -> list[list[dict[str, Any]]]:
        """
        Clusters entities into groups exceeding the similarity threshold.
        Uses LIGHTWEIGHT_DETERMINISTIC_GRAPH_PARTITIONER (connected components on thresholded affinity graph).
        """
        tau = threshold if threshold is not None else self.threshold
        n = len(entities)
        if n == 0:
            return []
        if n == 1:
            return [entities]

        # Build adjacency graph
        adj: dict[int, list[int]] = defaultdict(list)
        for i in range(n):
            for j in range(i + 1, n):
                e1 = entities[i]
                e2 = entities[j]
                sim = self.compute_entity_similarity(
                    name1=e1.get("name", ""),
                    path1=e1.get("file_path", ""),
                    name2=e2.get("name", ""),
                    path2=e2.get("file_path", ""),
                    context1=e1.get("description", "") or e1.get("type", ""),
                    context2=e2.get("description", "") or e2.get("type", ""),
                )
                if sim >= tau:
                    adj[i].append(j)
                    adj[j].append(i)

        # Deterministic Connected Components search
        visited: set[int] = set()
        clusters: list[list[dict[str, Any]]] = []

        for i in range(n):
            if i not in visited:
                component: list[int] = []
                queue = [i]
                visited.add(i)

                while queue:
                    curr = queue.pop(0)
                    component.append(curr)
                    for neighbor in sorted(adj[curr]):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                # Sort component indices for deterministic output
                clusters.append([entities[idx] for idx in sorted(component)])

        return clusters

    def merge_candidate_concepts(
        self,
        concepts: list[CandidateConcept],
        threshold: float | None = None,
    ) -> list[CandidateConcept]:
        """
        Identifies near-duplicate candidate concepts and merges them.
        Preserves all source evidence, entity names, and provenance spans.
        Status remains PROPOSED_PENDING_REVIEW.
        """
        if not concepts:
            return []

        entity_records = []
        for c in concepts:
            primary_path = c.evidence[0].file_path if c.evidence else ""
            entity_records.append({
                "concept": c,
                "name": c.name,
                "file_path": primary_path,
                "description": c.description,
                "type": c.category.value,
            })

        cluster_groups = self.cluster_entities(entity_records, threshold=threshold)
        merged_concepts: list[CandidateConcept] = []

        for group in cluster_groups:
            if len(group) == 1:
                merged_concepts.append(group[0]["concept"])
                continue

            # Merge group into a single consolidated CandidateConcept
            base_concepts: list[CandidateConcept] = [item["concept"] for item in group]

            # Choose canonical name: longest/most descriptive architectural name
            canonical_concept = max(
                base_concepts,
                key=lambda x: (len(x.name), len(x.evidence), x.confidence),
            )

            # Combine entity names and types
            all_source_names = sorted(
                list({name for c in base_concepts for name in c.source_entity_names})
            )
            all_source_types = sorted(
                list({t for c in base_concepts for t in c.source_entity_types})
            )

            # Combine evidence uniquely
            seen_evidence = set()
            merged_evidence: list[EvidenceProvenance] = []
            for c in base_concepts:
                for ev in c.evidence:
                    ev_key = (ev.file_path, ev.start_line, ev.end_line, ev.symbol_name)
                    if ev_key not in seen_evidence:
                        seen_evidence.add(ev_key)
                        merged_evidence.append(ev)

            # Merged confidence is the weighted average
            avg_conf = sum(c.confidence for c in base_concepts) / len(base_concepts)

            # Merged attributes
            merged_attrs: dict[str, Any] = {}
            for c in base_concepts:
                merged_attrs.update(c.attributes)
            merged_attrs["merged_concept_count"] = len(base_concepts)
            merged_attrs["merged_from_ids"] = [c.concept_id for c in base_concepts]

            merged = CandidateConcept(
                concept_id=canonical_concept.concept_id,
                name=canonical_concept.name,
                category=canonical_concept.category,
                parent_concept_id=canonical_concept.parent_concept_id,
                description=canonical_concept.description or f"Consolidated concept for {', '.join(all_source_names[:3])}",
                source_entity_names=all_source_names,
                source_entity_types=all_source_types,
                confidence=round(avg_conf, 4),
                status=ProposalStatus.PROPOSED_PENDING_REVIEW,
                evidence=merged_evidence,
                attributes=merged_attrs,
                v1_base_mapping=canonical_concept.v1_base_mapping,
            )
            merged_concepts.append(merged)

        return merged_concepts
