"""
Ontology Inducer Engine for Code Lane.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept (OntoRAG arXiv:2506.00664).

Ingests extracted code entities, relations, and atomic facts, and induces:
1. Candidate ontology concepts with evidence grounding.
2. Candidate semantic and architectural relationships.
3. Multi-level hierarchical taxonomy (Domain -> Subsystem -> Component -> Member).
4. Strict governance gating: all artifacts marked PROPOSED_PENDING_REVIEW.
5. Zero mutation of immutable V1 ontology.
"""

import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from experiments.e2_ontology_guided_extraction.concept_clusterer import (
    ConceptClusterer,
)
from experiments.e2_ontology_guided_extraction.schema import (
    CandidateConcept,
    CandidateRelation,
    CandidateRelationType,
    EvidenceProvenance,
    OntologyCategory,
    OntologyProposal,
    ProposalStatus,
    TaxonomyNode,
)

logger = logging.getLogger(__name__)


# Category inference rules from entity types and symbol patterns
CATEGORY_PATTERNS: list[tuple[str, OntologyCategory]] = [
    (r"(?i)(auth|token|jwt|crypto|security|verify|validate|permission|role|guard)", OntologyCategory.SECURITY_VALIDATION),
    (r"(?i)(db|database|repository|dao|table|migration|datastore|postgres|sql|cache|redis|store)", OntologyCategory.DATA_ACCESS),
    (r"(?i)(config|settings|env|flag|constant|option|parameter)", OntologyCategory.INFRASTRUCTURE_CONFIG),
    (r"(?i)(service|manager|controller|orchestrator|processor|handler|pipeline|engine)", OntologyCategory.SERVICE_COMPONENT),
    (r"(?i)(test|mock|fixture|suite|benchmark|assert)", OntologyCategory.SERVICE_COMPONENT),
]

RELATION_MAPPING: dict[str, CandidateRelationType] = {
    "CALLS": CandidateRelationType.CALLS,
    "IMPORTS": CandidateRelationType.DEPENDS_ON,
    "DEPENDS_ON": CandidateRelationType.DEPENDS_ON,
    "INHERITS": CandidateRelationType.SPECIALIZES,
    "DEFINES": CandidateRelationType.COMPOSED_OF,
    "CONFIGURES": CandidateRelationType.CONFIGURES,
    "VALIDATES": CandidateRelationType.VALIDATES,
    "MUTATES": CandidateRelationType.MODIFIES,
    "MODIFIES": CandidateRelationType.MODIFIES,
    "TESTS": CandidateRelationType.TESTS,
    "REFERENCES": CandidateRelationType.DEPENDS_ON,
    "REPLACES": CandidateRelationType.SPECIALIZES,
    "SUPERSEDES": CandidateRelationType.SPECIALIZES,
}


def infer_concept_category(name: str, entity_type: str, file_path: str = "") -> OntologyCategory:
    """Infers the high-level ontology category using multi-signal heuristics."""
    context = f"{name} {entity_type} {file_path}"
    import re
    for pattern, cat in CATEGORY_PATTERNS:
        if re.search(pattern, context):
            return cat

    type_upper = entity_type.upper()
    if type_upper in ("CONFIG_PARAM", "CONFIG"):
        return OntologyCategory.INFRASTRUCTURE_CONFIG
    if type_upper in ("DATASTORE", "TABLE"):
        return OntologyCategory.DATA_ACCESS
    if type_upper in ("SERVICE", "API"):
        return OntologyCategory.SERVICE_COMPONENT
    if type_upper in ("FUNCTION", "METHOD"):
        return OntologyCategory.OPERATION_MEMBER
    if type_upper in ("MODULE", "PACKAGE", "FILE"):
        return OntologyCategory.DOMAIN_SUBSYSTEM

    return OntologyCategory.SERVICE_COMPONENT


class OntologyInducer:
    """
    Code Lane Ontology Induction Engine.
    Implements OntoRAG concept extraction, clustering, relationship induction,
    and hierarchical taxonomy synthesis.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.70,
        clusterer: ConceptClusterer | None = None,
        max_hierarchy_depth: int = 4,
    ):
        self.threshold = similarity_threshold
        self.clusterer = clusterer or ConceptClusterer(similarity_threshold=similarity_threshold)
        self.max_hierarchy_depth = max_hierarchy_depth

    def _normalize_evidence(self, raw_evidence: Any, default_path: str = "") -> list[EvidenceProvenance]:
        """Converts raw evidence into standardized EvidenceProvenance models."""
        provenance_list: list[EvidenceProvenance] = []
        if not raw_evidence:
            if default_path:
                provenance_list.append(EvidenceProvenance(file_path=default_path))
            return provenance_list

        if isinstance(raw_evidence, list):
            for item in raw_evidence:
                provenance_list.extend(self._normalize_evidence(item, default_path))
            return provenance_list

        if isinstance(raw_evidence, EvidenceProvenance):
            return [raw_evidence]

        # Handle dict or E1SourceEvidence-like object
        if hasattr(raw_evidence, "file_path"):
            provenance_list.append(EvidenceProvenance(
                file_path=getattr(raw_evidence, "file_path", default_path),
                start_line=getattr(raw_evidence, "start_line", None),
                end_line=getattr(raw_evidence, "end_line", None),
                diff_snippet=getattr(raw_evidence, "diff_snippet", ""),
                grounded_tokens=getattr(raw_evidence, "grounded_tokens", []),
            ))
        elif isinstance(raw_evidence, dict):
            provenance_list.append(EvidenceProvenance(
                file_path=raw_evidence.get("file_path", default_path),
                start_line=raw_evidence.get("start_line"),
                end_line=raw_evidence.get("end_line"),
                commit_sha=raw_evidence.get("commit_sha"),
                diff_snippet=raw_evidence.get("diff_snippet", ""),
                symbol_name=raw_evidence.get("symbol_name"),
                grounded_tokens=raw_evidence.get("grounded_tokens", []),
            ))
        elif isinstance(raw_evidence, str):
            provenance_list.append(EvidenceProvenance(
                file_path=default_path or "unknown",
                diff_snippet=raw_evidence,
            ))

        return provenance_list

    def induce_concepts(
        self,
        entities: list[Any],
        threshold: float | None = None,
    ) -> tuple[list[CandidateConcept], dict[str, str]]:
        """
        Extracts candidate concepts from raw entities and clusters near-duplicates.
        Returns:
            (candidate_concepts, entity_name_to_concept_id_mapping)
        """
        tau = threshold if threshold is not None else self.threshold
        if not entities:
            return [], {}

        # 1. Transform raw entities to standardized records
        entity_records: list[dict[str, Any]] = []
        for e in entities:
            name = getattr(e, "entity_name", None) or getattr(e, "name", None) or (e.get("name") if isinstance(e, dict) else str(e))
            etype = getattr(e, "entity_type", None) or getattr(e, "type", None) or (e.get("type") if isinstance(e, dict) else "UNKNOWN")
            fpath = getattr(e, "file_path", "") or (e.get("file_path", "") if isinstance(e, dict) else "")
            ev = getattr(e, "evidence", None) or (e.get("evidence") if isinstance(e, dict) else None)
            conf = getattr(e, "confidence", 0.8) or (e.get("confidence", 0.8) if isinstance(e, dict) else 0.8)

            evidence_items = self._normalize_evidence(ev, default_path=fpath)

            entity_records.append({
                "name": str(name),
                "type": str(etype),
                "file_path": str(fpath),
                "confidence": float(conf),
                "evidence": evidence_items,
                "category": infer_concept_category(str(name), str(etype), str(fpath)),
            })

        # 2. Cluster entities
        clusters = self.clusterer.cluster_entities(entity_records, threshold=tau)

        candidate_concepts: list[CandidateConcept] = []
        entity_to_concept_map: dict[str, str] = {}

        for group in clusters:
            if not group:
                continue

            # Select canonical representative
            # Prioritize class/service over function/method, and longer name
            def rep_key(item: dict[str, Any]) -> tuple[int, int, float]:
                type_score = 3 if item["type"] in ("SERVICE", "CLASS") else (2 if item["type"] in ("MODULE", "FILE") else 1)
                return (type_score, len(item["name"]), item["confidence"])

            rep = max(group, key=rep_key)
            concept_id = f"concept_{uuid.uuid4().hex[:12]}"

            all_names = sorted(list({item["name"] for item in group}))
            all_types = sorted(list({item["type"] for item in group}))

            all_evidence: list[EvidenceProvenance] = []
            seen_ev = set()
            for item in group:
                for ev in item["evidence"]:
                    ev_key = (ev.file_path, ev.start_line, ev.end_line, ev.symbol_name, ev.diff_snippet[:30])
                    if ev_key not in seen_ev:
                        seen_ev.add(ev_key)
                        all_evidence.append(ev)

            avg_conf = sum(item["confidence"] for item in group) / len(group)
            canonical_name = rep["name"]

            # Map all entity names in this group to the concept ID
            for name in all_names:
                entity_to_concept_map[name] = concept_id

            concept = CandidateConcept(
                concept_id=concept_id,
                name=canonical_name,
                category=rep["category"],
                description=f"Induced concept representing {canonical_name} ({', '.join(all_types)})",
                source_entity_names=all_names,
                source_entity_types=all_types,
                confidence=round(avg_conf, 4),
                status=ProposalStatus.PROPOSED_PENDING_REVIEW,
                evidence=all_evidence,
                attributes={
                    "cluster_size": len(group),
                    "primary_file": rep["file_path"],
                },
                v1_base_mapping=rep["type"],
            )
            candidate_concepts.append(concept)

        return candidate_concepts, entity_to_concept_map

    def induce_relations(
        self,
        raw_relations: list[Any],
        entity_to_concept_map: dict[str, str],
        concepts_by_id: dict[str, CandidateConcept],
    ) -> list[CandidateRelation]:
        """
        Maps raw entity relations to candidate concept relationships.
        Aggregates evidence and preserves PROPOSED_PENDING_REVIEW governance.
        """
        if not raw_relations:
            return []

        # Deduplicate and aggregate relations between concept pairs
        rel_key_map: dict[tuple[str, str, CandidateRelationType], list[dict[str, Any]]] = defaultdict(list)

        for r in raw_relations:
            subj = getattr(r, "subject", None) or (r.get("subject") if isinstance(r, dict) else None)
            rel_type_str = (
                getattr(r, "relation_type", None) or
                getattr(r, "rel", None) or
                (r.get("relation_type") or r.get("rel") if isinstance(r, dict) else None) or
                "REFERENCES"
            )
            obj = getattr(r, "object", None) or getattr(r, "obj", None) or (r.get("object") or r.get("obj") if isinstance(r, dict) else None)
            ev = getattr(r, "evidence", None) or (r.get("evidence") if isinstance(r, dict) else None)
            conf = getattr(r, "confidence", 0.8) or (r.get("confidence", 0.8) if isinstance(r, dict) else 0.8)

            if not subj or not obj:
                continue

            subj_cid = entity_to_concept_map.get(str(subj))
            obj_cid = entity_to_concept_map.get(str(obj))

            # Skip self-relations or relations to unmapped concepts
            if not subj_cid or not obj_cid or subj_cid == obj_cid:
                continue

            mapped_type = RELATION_MAPPING.get(str(rel_type_str).upper(), CandidateRelationType.DEPENDS_ON)
            evidence_items = self._normalize_evidence(ev)

            rel_key_map[(subj_cid, obj_cid, mapped_type)].append({
                "confidence": float(conf),
                "evidence": evidence_items,
            })

        candidate_relations: list[CandidateRelation] = []

        for (subj_cid, obj_cid, rel_type), occurrences in rel_key_map.items():
            combined_evidence: list[EvidenceProvenance] = []
            seen_ev = set()
            for occ in occurrences:
                for ev in occ["evidence"]:
                    ev_key = (ev.file_path, ev.start_line, ev.end_line, ev.diff_snippet[:30])
                    if ev_key not in seen_ev:
                        seen_ev.add(ev_key)
                        combined_evidence.append(ev)

            avg_conf = sum(occ["confidence"] for occ in occurrences) / len(occurrences)

            cand_rel = CandidateRelation(
                relation_id=f"rel_{uuid.uuid4().hex[:12]}",
                subject_concept_id=subj_cid,
                relation_type=rel_type,
                object_concept_id=obj_cid,
                confidence=round(avg_conf, 4),
                status=ProposalStatus.PROPOSED_PENDING_REVIEW,
                evidence=combined_evidence,
                is_exclusive=False,
            )
            candidate_relations.append(cand_rel)

        return candidate_relations

    def build_taxonomy_hierarchy(
        self,
        concepts: list[CandidateConcept],
        relations: list[CandidateRelation],
    ) -> list[TaxonomyNode]:
        """
        Organizes candidate concepts into a multi-level hierarchical taxonomy.
        (Domain -> Subsystem -> Component -> Member).
        Ensures acyclic tree topology.
        """
        if not concepts:
            return []

        # Group concepts by primary file path prefix to identify top-level domains
        domain_groups: dict[str, list[CandidateConcept]] = defaultdict(list)
        for c in concepts:
            primary_path = c.attributes.get("primary_file", "") or (c.evidence[0].file_path if c.evidence else "")
            path_parts = primary_path.replace("\\", "/").strip("/").split("/")

            if len(path_parts) >= 2:
                # Top 2 directories form the domain root (e.g., 'apps/api' or 'services/workers')
                domain_name = "/".join(path_parts[:2])
            elif len(path_parts) == 1 and path_parts[0]:
                domain_name = path_parts[0]
            else:
                domain_name = c.category.value

            domain_groups[domain_name].append(c)

        taxonomy_roots: list[TaxonomyNode] = []

        for domain_name, dom_concepts in domain_groups.items():
            domain_node = TaxonomyNode(
                concept_id=f"domain_{uuid.uuid4().hex[:8]}",
                name=f"Domain::{domain_name}",
                category=OntologyCategory.DOMAIN_SUBSYSTEM.value,
                level=0,
                children=[],
            )

            # Sub-group by category
            cat_groups: dict[OntologyCategory, list[CandidateConcept]] = defaultdict(list)
            for c in dom_concepts:
                cat_groups[c.category].append(c)

            for cat, cat_concepts in cat_groups.items():
                cat_node = TaxonomyNode(
                    concept_id=f"subsystem_{uuid.uuid4().hex[:8]}",
                    name=f"{domain_name}::{cat.value}",
                    category=cat.value,
                    level=1,
                    children=[],
                )

                for c in cat_concepts:
                    comp_node = TaxonomyNode(
                        concept_id=c.concept_id,
                        name=c.name,
                        category=c.category.value,
                        level=2,
                        children=[],
                    )
                    # If this concept merged multiple operations, add them as level 3 children
                    if len(c.source_entity_names) > 1:
                        for sub_name in c.source_entity_names:
                            if sub_name != c.name:
                                comp_node.children.append(TaxonomyNode(
                                    concept_id=f"leaf_{uuid.uuid4().hex[:8]}",
                                    name=sub_name,
                                    category=OntologyCategory.OPERATION_MEMBER.value,
                                    level=3,
                                    children=[],
                                ))

                    cat_node.children.append(comp_node)

                domain_node.children.append(cat_node)

            taxonomy_roots.append(domain_node)

        return taxonomy_roots

    def induce_proposal(
        self,
        entities: list[Any],
        relations: list[Any] | None = None,
        threshold: float | None = None,
    ) -> OntologyProposal:
        """
        Executes complete end-to-end ontology induction pipeline:
        1. Induces candidate concepts and clusters duplicates.
        2. Induces candidate relationships between concepts.
        3. Builds multi-level hierarchical taxonomy.
        4. Calculates quality metrics.
        5. Packages into OntologyProposal with PROPOSED_PENDING_REVIEW status.
        """
        tau = threshold if threshold is not None else self.threshold
        concepts, entity_to_concept_map = self.induce_concepts(entities, threshold=tau)
        concepts_by_id = {c.concept_id: c for c in concepts}

        candidate_relations = self.induce_relations(
            raw_relations=relations or [],
            entity_to_concept_map=entity_to_concept_map,
            concepts_by_id=concepts_by_id,
        )

        taxonomy = self.build_taxonomy_hierarchy(concepts, candidate_relations)

        # Calculate metrics
        total_raw_entities = len(entities)
        induced_concept_count = len(concepts)
        redundancy_reduction = (
            (1.0 - (induced_concept_count / total_raw_entities))
            if total_raw_entities > 0 else 0.0
        )

        evidence_backed_concepts = sum(1 for c in concepts if len(c.evidence) > 0)
        evidence_coverage = (
            (evidence_backed_concepts / induced_concept_count)
            if induced_concept_count > 0 else 1.0
        )

        metrics = {
            "total_raw_entities": total_raw_entities,
            "induced_concept_count": induced_concept_count,
            "redundancy_reduction_ratio": round(redundancy_reduction, 4),
            "candidate_relation_count": len(candidate_relations),
            "evidence_coverage_ratio": round(evidence_coverage, 4),
            "taxonomy_root_count": len(taxonomy),
            "similarity_threshold": tau,
        }

        return OntologyProposal(
            proposal_id=f"proposal_{uuid.uuid4().hex[:12]}",
            created_at=datetime.now(UTC),
            concepts=concepts,
            relations=candidate_relations,
            taxonomy_roots=taxonomy,
            clustering_threshold=tau,
            metrics=metrics,
        )
