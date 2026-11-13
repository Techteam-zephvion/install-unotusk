"""
E3 Sparse Confidence Engine.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.

Implements transparent, multi-signal confidence and sufficiency assessment
for sparse software projects, adapting arXiv:2510.01792.
"""

import uuid
from typing import Any

from experiments.e1_generative_ie.schema import E1Entity, E1Event, E1ExtractionResult, E1Relation
from experiments.e2_ontology_guided_extraction.schema import (
    CandidateConcept,
    CandidateRelation,
    OntologyProposal,
)
from experiments.e3_sparse_confidence import metrics
from experiments.e3_sparse_confidence.schema import (
    ConceptConfidenceAssessment,
    ConfidenceLevel,
    E3AssessmentResult,
    EntityConfidenceAssessment,
    EventConfidenceAssessment,
    MetricScores,
    ProjectConfidenceAssessment,
    RelationConfidenceAssessment,
    RelationshipConfidenceAssessment,
)


class SparseConfidenceEngine:
    """
    Transparent confidence scoring engine for Code Lane extraction and ontology induction.
    Evaluates evidence reliability, consistency, and sufficiency under sparse commit conditions.
    """

    DEFAULT_WEIGHTS = {
        "provenance_completeness": 0.30,
        "term_frequency_coherence": 0.25,
        "intra_block_coherence": 0.20,
        "structural_consistency": 0.15,
        "corroboration_score": 0.10,
    }

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        high_threshold: float = 0.75,
        medium_threshold: float = 0.50,
        low_threshold: float = 0.25,
        ablation_disabled_metrics: set[str] | None = None,
    ):
        self.weights = dict(weights or self.DEFAULT_WEIGHTS)
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.low_threshold = low_threshold
        self.ablation_disabled = set(ablation_disabled_metrics or [])

    def _normalize_weights(self) -> dict[str, float]:
        """Recalculates weights excluding disabled ablation metrics."""
        active = {k: v for k, v in self.weights.items() if k not in self.ablation_disabled}
        total = sum(active.values())
        if total <= 0:
            return {k: 1.0 / len(active) for k in active}
        return {k: v / total for k, v in active.items()}

    def _score_to_level(self, score: float, is_abstaining: bool) -> ConfidenceLevel:
        if is_abstaining or score < self.low_threshold:
            return ConfidenceLevel.INSUFFICIENT_EVIDENCE
        if score >= self.high_threshold:
            return ConfidenceLevel.HIGH
        if score >= self.medium_threshold:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def evaluate_entity(
        self,
        entity: E1Entity,
        diff_text: str = "",
        occurrences: list[E1Entity] | None = None,
    ) -> EntityConfidenceAssessment:
        """Evaluates confidence for an individual E1 extracted entity."""
        ev = entity.evidence
        active_weights = self._normalize_weights()

        # 1. Provenance
        prov_score = 1.0 if "provenance_completeness" in self.ablation_disabled else metrics.compute_provenance_completeness(ev)

        # 2. Term frequency coherence
        diff_content = diff_text or (ev.diff_snippet if ev else "")
        tf_score = 1.0 if "term_frequency_coherence" in self.ablation_disabled else metrics.compute_term_frequency_coherence(entity.entity_name, diff_content)

        # 3. Intra-block coherence
        intra_score = 1.0 if "intra_block_coherence" in self.ablation_disabled else metrics.compute_intra_block_coherence(entity.entity_type, entity.entity_name)

        # 4. Structural consistency (default 1.0 for atomic entity)
        struct_score = 1.0

        # 5. Corroboration across occurrences
        occ_list = occurrences or [entity]
        corrob_score, n_files, n_commits = (
            (0.50, 1, 1)
            if "corroboration_score" in self.ablation_disabled
            else metrics.compute_corroboration_score(occ_list)
        )

        # 6. Redundancy penalty
        red_penalty = 0.0
        if "redundancy_penalty" not in self.ablation_disabled and occurrences and len(occurrences) > 1:
            red_penalty, _ = metrics.compute_redundancy_penalty(
                occurrences,
                key_fn=lambda e: f"{e.entity_name}::{e.file_path}::{e.evidence.start_line}",
            )

        metric_scores = MetricScores(
            provenance_completeness=prov_score,
            term_frequency_coherence=tf_score,
            intra_block_coherence=intra_score,
            structural_consistency=struct_score,
            corroboration_score=corrob_score,
            redundancy_penalty=red_penalty,
            contradiction_penalty=0.0,
            coverage_ratio=1.0,
        )

        # Combine weighted components
        base_score = (
            active_weights.get("provenance_completeness", 0.0) * prov_score
            + active_weights.get("term_frequency_coherence", 0.0) * tf_score
            + active_weights.get("intra_block_coherence", 0.0) * intra_score
            + active_weights.get("structural_consistency", 0.0) * struct_score
            + active_weights.get("corroboration_score", 0.0) * corrob_score
        )
        final_score = max(0.0, min(1.0, base_score * (1.0 - red_penalty)))

        missing_signals: list[str] = []
        if prov_score < 0.50:
            missing_signals.append("Incomplete source file or line-range provenance")
        if tf_score < 0.30:
            missing_signals.append("Low term alignment with diff vocabulary")
        if len(occ_list) == 1 and n_commits <= 1:
            missing_signals.append("Single-observation fact (no cross-commit corroboration)")

        is_abstention = prov_score < 0.20 or final_score < self.low_threshold
        level = self._score_to_level(final_score, is_abstention)

        explanation = (
            f"Entity '{entity.entity_name}' scored {final_score:.3f} ({level.value}). "
            f"Provenance: {prov_score:.2f}, TF-Coherence: {tf_score:.2f}, Corroboration: {corrob_score:.2f} "
            f"({n_files} files, {n_commits} commits)."
        )

        return EntityConfidenceAssessment(
            entity_id=entity.entity_id,
            entity_name=entity.entity_name,
            entity_type=entity.entity_type,
            confidence_score=round(final_score, 4),
            confidence_level=level,
            is_abstention=is_abstention,
            metric_scores=metric_scores,
            supporting_evidence_count=len(occ_list),
            independent_sources_count=max(n_files, n_commits),
            missing_signals=missing_signals,
            contradictions=[],
            explanation=explanation,
        )

    def evaluate_relation(
        self,
        relation: E1Relation,
        diff_text: str = "",
        all_relations: list[E1Relation] | None = None,
    ) -> RelationConfidenceAssessment:
        """Evaluates confidence for an individual E1 extracted relation."""
        ev = relation.evidence
        active_weights = self._normalize_weights()
        rel_list = all_relations or [relation]

        # 1. Provenance
        prov_score = 1.0 if "provenance_completeness" in self.ablation_disabled else metrics.compute_provenance_completeness(ev)

        # 2. Term frequency coherence (subject + object alignment with diff)
        diff_content = diff_text or (ev.diff_snippet if ev else "")
        tf_subj = metrics.compute_term_frequency_coherence(relation.subject, diff_content)
        tf_obj = metrics.compute_term_frequency_coherence(relation.object, diff_content)
        tf_score = 1.0 if "term_frequency_coherence" in self.ablation_disabled else round((tf_subj + tf_obj) / 2.0, 4)

        # 3. Intra-block coherence
        intra_score = (
            1.0
            if "intra_block_coherence" in self.ablation_disabled
            else metrics.compute_intra_block_coherence(
                relation.relation_type,
                name=f"{relation.subject}->{relation.object}",
                subject_or_target=relation.subject,
                object_name=relation.object,
            )
        )

        # 4. Structural consistency & cycle detection
        struct_score, struct_violations = (
            (1.0, [])
            if "structural_consistency" in self.ablation_disabled
            else metrics.compute_structural_consistency(rel_list)
        )

        # 5. Corroboration score
        same_pair = [r for r in rel_list if r.subject == relation.subject and r.object == relation.object]
        corrob_score, n_files, n_commits = (
            (0.50, 1, 1)
            if "corroboration_score" in self.ablation_disabled
            else metrics.compute_corroboration_score(same_pair)
        )

        # 6. Contradictions & conflicts
        contra_penalty, contra_list = (
            (0.0, [])
            if "contradiction_penalty" in self.ablation_disabled
            else metrics.detect_contradictions(rel_list)
        )

        metric_scores = MetricScores(
            provenance_completeness=prov_score,
            term_frequency_coherence=tf_score,
            intra_block_coherence=intra_score,
            structural_consistency=struct_score,
            corroboration_score=corrob_score,
            redundancy_penalty=0.0,
            contradiction_penalty=contra_penalty,
            coverage_ratio=1.0,
        )

        base_score = (
            active_weights.get("provenance_completeness", 0.0) * prov_score
            + active_weights.get("term_frequency_coherence", 0.0) * tf_score
            + active_weights.get("intra_block_coherence", 0.0) * intra_score
            + active_weights.get("structural_consistency", 0.0) * struct_score
            + active_weights.get("corroboration_score", 0.0) * corrob_score
        )
        final_score = max(0.0, min(1.0, base_score - contra_penalty))

        missing_signals: list[str] = []
        if prov_score < 0.50:
            missing_signals.append("Incomplete relation provenance evidence")
        if tf_score < 0.40:
            missing_signals.append("Subject or object symbol not strongly grounded in diff")

        contradictions = struct_violations + [c for c in contra_list if relation.subject in c or relation.object in c]
        is_abstention = prov_score < 0.20 or final_score < self.low_threshold or len(contradictions) > 0
        level = self._score_to_level(final_score, is_abstention)

        explanation = (
            f"Relation ({relation.subject} -[{relation.relation_type}]-> {relation.object}) "
            f"scored {final_score:.3f} ({level.value}). "
            f"Provenance: {prov_score:.2f}, Structural: {struct_score:.2f}, Contradictions: {len(contradictions)}."
        )

        return RelationConfidenceAssessment(
            relation_id=relation.relation_id,
            subject=relation.subject,
            relation_type=relation.relation_type,
            object=relation.object,
            confidence_score=round(final_score, 4),
            confidence_level=level,
            is_abstention=is_abstention,
            metric_scores=metric_scores,
            supporting_evidence_count=len(same_pair),
            independent_sources_count=max(n_files, n_commits),
            missing_signals=missing_signals,
            contradictions=contradictions,
            explanation=explanation,
        )

    def evaluate_event(
        self,
        event: E1Event,
        diff_text: str = "",
    ) -> EventConfidenceAssessment:
        """Evaluates confidence for an individual E1 extracted event."""
        ev = event.evidence
        active_weights = self._normalize_weights()

        prov_score = 1.0 if "provenance_completeness" in self.ablation_disabled else metrics.compute_provenance_completeness(ev)
        diff_content = diff_text or (ev.diff_snippet if ev else "")
        tf_score = 1.0 if "term_frequency_coherence" in self.ablation_disabled else metrics.compute_term_frequency_coherence(event.target_component, diff_content)
        intra_score = 1.0 if "intra_block_coherence" in self.ablation_disabled else metrics.compute_intra_block_coherence(event.event_type, event.target_component)

        metric_scores = MetricScores(
            provenance_completeness=prov_score,
            term_frequency_coherence=tf_score,
            intra_block_coherence=intra_score,
            structural_consistency=1.0,
            corroboration_score=0.50,
            redundancy_penalty=0.0,
            contradiction_penalty=0.0,
            coverage_ratio=1.0,
        )

        final_score = (
            active_weights.get("provenance_completeness", 0.0) * prov_score
            + active_weights.get("term_frequency_coherence", 0.0) * tf_score
            + active_weights.get("intra_block_coherence", 0.0) * intra_score
        )
        final_score = max(0.0, min(1.0, final_score))

        missing_signals: list[str] = []
        if not event.trigger_statement:
            missing_signals.append("Missing explicit trigger statement for event")

        is_abstention = prov_score < 0.20 or final_score < self.low_threshold
        level = self._score_to_level(final_score, is_abstention)

        return EventConfidenceAssessment(
            event_id=event.event_id,
            event_type=event.event_type,
            target_component=event.target_component,
            confidence_score=round(final_score, 4),
            confidence_level=level,
            is_abstention=is_abstention,
            metric_scores=metric_scores,
            missing_signals=missing_signals,
            contradictions=[],
            explanation=f"Event '{event.event_type}' on '{event.target_component}' scored {final_score:.3f} ({level.value}).",
        )

    def evaluate_concept(
        self,
        concept: CandidateConcept,
        all_concepts: list[CandidateConcept] | None = None,
    ) -> ConceptConfidenceAssessment:
        """Evaluates confidence for an E2 induced candidate concept."""
        active_weights = self._normalize_weights()
        c_list = all_concepts or [concept]

        # 1. Provenance over all constituent evidence items
        ev_scores = [metrics.compute_provenance_completeness(e) for e in concept.evidence]
        prov_score = sum(ev_scores) / len(ev_scores) if ev_scores else 0.50

        # 2. Term frequency coherence across source entity names
        tf_score = 0.85
        if concept.source_entity_names:
            overlap_scores = [
                metrics.compute_term_frequency_coherence(name, concept.name)
                for name in concept.source_entity_names
            ]
            tf_score = sum(overlap_scores) / len(overlap_scores)

        # 3. Intra-block coherence
        intra_score = metrics.compute_intra_block_coherence(concept.category.value, concept.name)

        # 4. Structural consistency with concept taxonomy
        struct_score, struct_violations = metrics.compute_structural_consistency(
            relations=[],
            concepts=c_list,
        )

        # 5. Corroboration across unique files
        unique_files = {e.file_path for e in concept.evidence if e.file_path}
        corrob_score, n_files, n_commits = metrics.compute_corroboration_score(concept.evidence)

        # 6. Redundancy penalty (if multiple concepts share identical source entities)
        red_penalty = 0.0
        if len(c_list) > 1:
            red_penalty, _ = metrics.compute_redundancy_penalty(
                c_list,
                key_fn=lambda c: f"{c.name}::{c.category.value}",
            )

        metric_scores = MetricScores(
            provenance_completeness=prov_score,
            term_frequency_coherence=tf_score,
            intra_block_coherence=intra_score,
            structural_consistency=struct_score,
            corroboration_score=corrob_score,
            redundancy_penalty=red_penalty,
            contradiction_penalty=0.0,
            coverage_ratio=1.0,
        )

        base_score = (
            active_weights.get("provenance_completeness", 0.0) * prov_score
            + active_weights.get("term_frequency_coherence", 0.0) * tf_score
            + active_weights.get("intra_block_coherence", 0.0) * intra_score
            + active_weights.get("structural_consistency", 0.0) * struct_score
            + active_weights.get("corroboration_score", 0.0) * corrob_score
        )
        final_score = max(0.0, min(1.0, base_score * (1.0 - red_penalty)))

        missing_signals: list[str] = []
        if len(concept.source_entity_names) <= 1 and len(unique_files) <= 1:
            missing_signals.append("Isolated single-symbol concept (candidate for inlining)")

        is_abstention = final_score < self.low_threshold or len(struct_violations) > 0
        level = self._score_to_level(final_score, is_abstention)

        explanation = (
            f"Candidate Concept '{concept.name}' scored {final_score:.3f} ({level.value}). "
            f"Derived from {len(concept.source_entity_names)} entities across {len(unique_files)} files."
        )

        return ConceptConfidenceAssessment(
            concept_id=concept.concept_id,
            concept_name=concept.name,
            category=concept.category.value,
            confidence_score=round(final_score, 4),
            confidence_level=level,
            is_abstention=is_abstention,
            metric_scores=metric_scores,
            member_entities_count=len(concept.source_entity_names),
            independent_files_count=len(unique_files),
            missing_signals=missing_signals,
            contradictions=struct_violations,
            explanation=explanation,
        )

    def evaluate_candidate_relation(
        self,
        candidate_rel: CandidateRelation,
        all_candidate_rels: list[CandidateRelation] | None = None,
    ) -> RelationshipConfidenceAssessment:
        """Evaluates confidence for an E2 induced candidate relationship."""
        active_weights = self._normalize_weights()
        rel_list = all_candidate_rels or [candidate_rel]

        # 1. Provenance over constituent evidence
        ev_scores = [metrics.compute_provenance_completeness(e) for e in candidate_rel.evidence]
        prov_score = sum(ev_scores) / len(ev_scores) if ev_scores else 0.50

        # 2. Structural consistency
        struct_score, struct_violations = metrics.compute_structural_consistency(rel_list)

        # 3. Contradictions
        contra_penalty, contra_list = metrics.detect_contradictions(rel_list)

        # 4. Corroboration
        corrob_score, n_files, n_commits = metrics.compute_corroboration_score(candidate_rel.evidence)

        metric_scores = MetricScores(
            provenance_completeness=prov_score,
            term_frequency_coherence=1.0,
            intra_block_coherence=1.0,
            structural_consistency=struct_score,
            corroboration_score=corrob_score,
            redundancy_penalty=0.0,
            contradiction_penalty=contra_penalty,
            coverage_ratio=1.0,
        )

        base_score = (
            active_weights.get("provenance_completeness", 0.0) * prov_score
            + active_weights.get("structural_consistency", 0.0) * struct_score
            + active_weights.get("corroboration_score", 0.0) * corrob_score
            + 0.20  # baseline relationship coherence
        )
        final_score = max(0.0, min(1.0, base_score - contra_penalty))

        contradictions = struct_violations + [
            c for c in contra_list if candidate_rel.subject_concept_id in c or candidate_rel.object_concept_id in c
        ]
        is_abstention = final_score < self.low_threshold or len(contradictions) > 0
        level = self._score_to_level(final_score, is_abstention)

        explanation = (
            f"Candidate Relation ({candidate_rel.subject_concept_id} -[{candidate_rel.relation_type.value}]-> "
            f"{candidate_rel.object_concept_id}) scored {final_score:.3f} ({level.value})."
        )

        return RelationshipConfidenceAssessment(
            relation_id=candidate_rel.relation_id,
            subject_concept_id=candidate_rel.subject_concept_id,
            relation_type=candidate_rel.relation_type.value,
            object_concept_id=candidate_rel.object_concept_id,
            confidence_score=round(final_score, 4),
            confidence_level=level,
            is_abstention=is_abstention,
            metric_scores=metric_scores,
            independent_evidence_count=max(n_files, 1),
            missing_signals=[],
            contradictions=contradictions,
            explanation=explanation,
        )

    def evaluate_project(
        self,
        commits: list[Any],
        e1_results: list[E1ExtractionResult] | None = None,
        proposals: list[OntologyProposal] | None = None,
        budget_label: str = "full",
    ) -> E3AssessmentResult:
        """
        Global evaluation across all evaluated commits, E1 results, and E2 proposals.
        Handles sparse-project conditions and downsampling budgets (1, 2, 3, 5, 10 commits).
        """
        assessment_id = f"e3_assess_{uuid.uuid4().hex[:12]}"
        commit_shas = [getattr(c, "commit_sha", str(c)) for c in commits]

        all_e1 = e1_results or []
        all_proposals = proposals or []

        # Collect all items
        entities: list[E1Entity] = []
        relations: list[E1Relation] = []
        events: list[E1Event] = []
        for r in all_e1:
            entities.extend(r.entities)
            relations.extend(r.relations)
            events.extend(r.events)

        concepts: list[CandidateConcept] = []
        candidate_rels: list[CandidateRelation] = []
        for p in all_proposals:
            concepts.extend(p.concepts)
            candidate_rels.extend(p.relations)

        # 1. Evaluate entities
        entity_assessments: list[EntityConfidenceAssessment] = []
        for ent in entities:
            same_entities = [e for e in entities if e.entity_name == ent.entity_name]
            entity_assessments.append(self.evaluate_entity(ent, occurrences=same_entities))

        # 2. Evaluate relations
        relation_assessments: list[RelationConfidenceAssessment] = []
        for rel in relations:
            relation_assessments.append(self.evaluate_relation(rel, all_relations=relations))

        # 3. Evaluate events
        event_assessments: list[EventConfidenceAssessment] = []
        for ev in events:
            event_assessments.append(self.evaluate_event(ev))

        # 4. Evaluate E2 concepts
        concept_assessments: list[ConceptConfidenceAssessment] = []
        for c in concepts:
            concept_assessments.append(self.evaluate_concept(c, all_concepts=concepts))

        # 5. Evaluate E2 candidate relations
        relationship_assessments: list[RelationshipConfidenceAssessment] = []
        for cr in candidate_rels:
            relationship_assessments.append(self.evaluate_candidate_relation(cr, all_candidate_rels=candidate_rels))

        # 6. Global sufficiency and sparsity assessment
        total_facts = len(entities) + len(relations) + len(events)
        total_files = len({e.file_path for e in entities if e.file_path})
        total_diff_chars = sum(len(getattr(c, "raw_diff", "") or "") for c in commits)

        sufficiency, sparsity = metrics.compute_evidence_sufficiency(
            commit_count=len(commits),
            file_count=total_files,
            fact_count=total_facts,
            diff_chars_count=total_diff_chars,
        )

        # Aggregate confidence scores
        all_scores = [a.confidence_score for a in entity_assessments + relation_assessments + event_assessments]
        if concept_assessments:
            all_scores.extend(a.confidence_score for a in concept_assessments)
        if relationship_assessments:
            all_scores.extend(a.confidence_score for a in relationship_assessments)

        if all_scores:
            overall_score = round(sum(all_scores) / len(all_scores), 4)
        else:
            overall_score = 0.0

        abstentions = sum(1 for a in entity_assessments + relation_assessments if a.is_abstention)
        abstention_rate = round(abstentions / max(1, len(entity_assessments) + len(relation_assessments)), 4)

        all_contradictions = [c for a in relation_assessments + relationship_assessments for c in a.contradictions]

        overall_level = self._score_to_level(overall_score, is_abstaining=(abstention_rate > 0.40))

        # Aggregate metric averages
        agg_metrics: dict[str, float] = {}
        for m in (
            "provenance_completeness",
            "term_frequency_coherence",
            "intra_block_coherence",
            "structural_consistency",
            "corroboration_score",
            "redundancy_penalty",
            "contradiction_penalty",
        ):
            vals = [
                getattr(a.metric_scores, m)
                for a in entity_assessments + relation_assessments
                if hasattr(a, "metric_scores")
            ]
            agg_metrics[m] = round(sum(vals) / len(vals), 4) if vals else 0.0

        explanation = (
            f"Project assessment ({budget_label}): {len(commits)} commits, {total_files} files, {total_facts} facts. "
            f"Sufficiency: {sufficiency.value} (Sparsity index: {sparsity:.2f}). "
            f"Overall confidence: {overall_score:.3f} ({overall_level.value}). "
            f"Abstention rate: {abstention_rate:.1%}, Contradictions: {len(all_contradictions)}."
        )

        project_assessment = ProjectConfidenceAssessment(
            project_id="code_lane_sparse_project",
            commit_shas=commit_shas,
            commit_count=len(commits),
            total_entities_evaluated=len(entities),
            total_relations_evaluated=len(relations),
            total_events_evaluated=len(events),
            total_concepts_evaluated=len(concepts),
            total_relationships_evaluated=len(candidate_rels),
            overall_confidence_score=overall_score,
            overall_confidence_level=overall_level,
            evidence_sufficiency=sufficiency,
            sparsity_index=sparsity,
            aggregate_metric_averages=agg_metrics,
            abstention_rate=abstention_rate,
            contradiction_count=len(all_contradictions),
            evidence_budget_label=budget_label,
            explanation=explanation,
        )

        return E3AssessmentResult(
            assessment_id=assessment_id,
            commit_shas=commit_shas,
            project_assessment=project_assessment,
            entity_assessments=entity_assessments,
            relation_assessments=relation_assessments,
            event_assessments=event_assessments,
            concept_assessments=concept_assessments,
            relationship_assessments=relationship_assessments,
            metadata={
                "sparsity_index": sparsity,
                "evidence_sufficiency": sufficiency.value,
                "budget_label": budget_label,
            },
            ablation_active={m: (m not in self.ablation_disabled) for m in self.DEFAULT_WEIGHTS},
        )
