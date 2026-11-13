"""
E1 -> E2 -> E3 Integrated Research Pipeline Orchestration.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.

Executes the genuine data flow:
GitCommitArtifact -> E1 Extractor & Grounding Validator -> E1ExtractionResult
  -> E2 Ontology Inducer -> OntologyProposal
    -> E3 Sparse Confidence Engine -> E3AssessmentResult
"""

import asyncio
from pathlib import Path
from typing import Any

from apps.api.src.schemas.code_atom import GitCommitArtifact
from experiments.e1_generative_ie.extractor import E1Extractor
from experiments.e1_generative_ie.schema import E1ExtractionResult
from experiments.e2_ontology_guided_extraction.ontology_inducer import OntologyInducer
from experiments.e2_ontology_guided_extraction.schema import OntologyProposal
from experiments.e3_sparse_confidence.confidence_engine import SparseConfidenceEngine
from experiments.e3_sparse_confidence.schema import E3AssessmentResult


async def run_e1_e2_e3_pipeline(
    commits: list[GitCommitArtifact],
    similarity_threshold: float = 0.70,
    output_path: str | Path | None = None,
    engine: SparseConfidenceEngine | None = None,
    budget_label: str = "custom",
) -> tuple[list[E1ExtractionResult], OntologyProposal, E3AssessmentResult]:
    """
    Executes the real, connected E1 -> E2 -> E3 pipeline without mocks or hardcoded data.

    1. E1: Extracts grounded facts from real Git commit diffs.
    2. E2: Induces candidate ontology concepts and relationships from E1 facts.
    3. E3: Assesses unsupervised confidence and evidence sufficiency across facts and proposals.
    """
    if not commits:
        raise ValueError("Cannot run pipeline with empty commits list")

    extractor = E1Extractor()
    e1_results: list[E1ExtractionResult] = []

    # 1. E1 Extraction Phase
    for commit in commits:
        result = await extractor.extract_m1_generative_ie(commit)
        e1_results.append(result)

    # Aggregate extracted entities & relations
    aggregated_entities = [ent for r in e1_results for ent in r.entities]
    aggregated_relations = [rel for r in e1_results for rel in r.relations]

    # 2. E2 Ontology Induction Phase
    inducer = OntologyInducer(similarity_threshold=similarity_threshold)
    proposal = inducer.induce_proposal(
        entities=aggregated_entities,
        relations=aggregated_relations,
        threshold=similarity_threshold,
    )

    # 3. E3 Confidence Scoring Phase
    confidence_engine = engine or SparseConfidenceEngine()
    assessment = confidence_engine.evaluate_project(
        commits=commits,
        e1_results=e1_results,
        proposals=[proposal],
        budget_label=budget_label,
    )

    # 4. Optional Persistence and Round-Trip Validation
    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        serialized = assessment.model_dump_json(indent=2)
        out_p.write_text(serialized, encoding="utf-8")

        # Validate round-trip deserialization immediately
        reloaded = E3AssessmentResult.model_validate_json(serialized)
        assert reloaded.assessment_id == assessment.assessment_id
        assert len(reloaded.entity_assessments) == len(assessment.entity_assessments)

    return e1_results, proposal, assessment


def run_pipeline_sync(
    commits: list[GitCommitArtifact],
    similarity_threshold: float = 0.70,
    output_path: str | Path | None = None,
    engine: SparseConfidenceEngine | None = None,
    budget_label: str = "custom",
) -> tuple[list[E1ExtractionResult], OntologyProposal, E3AssessmentResult]:
    """Synchronous convenience wrapper for run_e1_e2_e3_pipeline."""
    return asyncio.run(
        run_e1_e2_e3_pipeline(
            commits=commits,
            similarity_threshold=similarity_threshold,
            output_path=output_path,
            engine=engine,
            budget_label=budget_label,
        )
    )


def evaluate_evidence_budgets(
    commits: list[GitCommitArtifact],
    budgets: list[int] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Evaluates evidence budgets at controlled downsampled commit levels:
    1 commit, 2 commits, 3 commits, 5 commits, 10 commits.
    """
    budget_list = budgets if budgets is not None else [1, 2, 3, 5, 10]
    results: dict[str, dict[str, Any]] = {}
    engine = SparseConfidenceEngine()

    for k in budget_list:
        slice_commits = commits[:k]
        if not slice_commits:
            continue
        label = f"{k}_commits" if k > 1 else "1_commit"
        _, _, assess = run_pipeline_sync(slice_commits, engine=engine, budget_label=label)
        p = assess.project_assessment
        results[label] = {
            "budget": k,
            "commit_count": p.commit_count,
            "total_facts": p.total_entities_evaluated + p.total_relations_evaluated + p.total_events_evaluated,
            "concepts_induced": p.total_concepts_evaluated,
            "sufficiency": p.evidence_sufficiency.value,
            "sparsity_index": p.sparsity_index,
            "overall_score": p.overall_confidence_score,
            "overall_level": p.overall_confidence_level.value,
            "abstention_rate": p.abstention_rate,
            "contradiction_count": p.contradiction_count,
        }

    return results


if __name__ == "__main__":
    import argparse

    from experiments.e1_generative_ie.data.dataset import load_e1_dataset

    parser = argparse.ArgumentParser(description="E1 -> E2 -> E3 Integrated Research Pipeline")
    parser.add_argument("--budget", type=int, default=5, help="Number of commits to evaluate (default: 5)")
    parser.add_argument("--out", type=str, default="scratch/e3_assessment.json", help="Output path for JSON assessment")
    args = parser.parse_args()

    ds = load_e1_dataset()
    selected_commits = [tc.commit for tc in ds[: args.budget]]

    print(f"Running E1 -> E2 -> E3 pipeline for {len(selected_commits)} commits...")
    e1_res, e2_prop, e3_assess = run_pipeline_sync(
        commits=selected_commits,
        output_path=args.out,
        budget_label=f"{args.budget}_commits",
    )

    p = e3_assess.project_assessment
    print("\n--- Pipeline Complete ---")
    print(f"E1 Extracted Facts: {p.total_entities_evaluated} entities, {p.total_relations_evaluated} relations")
    print(f"E2 Candidate Concepts: {p.total_concepts_evaluated} concepts, {p.total_relationships_evaluated} relations")
    print(f"E3 Evidence Sufficiency: {p.evidence_sufficiency.value} (Sparsity: {p.sparsity_index:.2f})")
    print(f"E3 Project Confidence: {p.overall_confidence_score:.3f} ({p.overall_confidence_level.value})")
    print(f"Assessment saved to: {args.out}")
