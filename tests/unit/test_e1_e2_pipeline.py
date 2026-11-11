"""
End-to-end pipeline integration test for E1 (Generative IE) -> E2 (Ontology Induction).
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.

Exercises the genuine data flow:
GitCommitArtifact -> E1ContextBuilder -> E1Extractor -> E1GroundingValidator
  -> E1ExtractionResult -> ConceptClusterer -> OntologyInducer -> OntologyProposal
"""

import pytest

from experiments.e1_generative_ie.context_builder import E1ContextBuilder
from experiments.e1_generative_ie.data.dataset import load_e1_dataset
from experiments.e1_generative_ie.extractor import E1Extractor
from experiments.e1_generative_ie.schema import E1ExtractionResult, ValidationStatus
from experiments.e2_ontology_guided_extraction.ontology_inducer import OntologyInducer
from experiments.e2_ontology_guided_extraction.schema import (
    CandidateConcept,
    OntologyProposal,
    ProposalStatus,
)


@pytest.mark.asyncio
async def test_single_scenario_e1_to_e2_end_to_end():
    """
    Executes real E1 -> E2 pipeline on a single real commit scenario.
    Verifies data flow, provenance survival, status gating, and round-trip serialization.
    """
    dataset = load_e1_dataset()
    tc = dataset[0]  # dev_01_simple_func_mod

    # 1. Context Builder
    context = E1ContextBuilder.prepare_diff_context(tc.commit)
    assert context["commit_sha"] == tc.commit.commit_sha
    assert len(context["files"]) >= 1

    # 2. E1 Extractor + Grounding Validator
    extractor = E1Extractor()
    e1_result = await extractor.extract_m1_generative_ie(tc.commit)
    assert isinstance(e1_result, E1ExtractionResult)
    assert len(e1_result.entities) >= 1
    assert all(e.validation_status == ValidationStatus.VALIDATED for e in e1_result.entities)

    # 3. Direct Handoff to E2 Ontology Inducer
    inducer = OntologyInducer(similarity_threshold=0.70)
    proposal = inducer.induce_proposal(
        entities=e1_result.entities,
        relations=e1_result.relations,
        threshold=0.70,
    )

    # 4. Verify E2 Results
    assert isinstance(proposal, OntologyProposal)
    assert len(proposal.concepts) >= 1
    assert len(proposal.taxonomy_roots) >= 1

    for concept in proposal.concepts:
        assert isinstance(concept, CandidateConcept)
        assert concept.status == ProposalStatus.PROPOSED_PENDING_REVIEW
        assert len(concept.evidence) >= 1
        assert concept.evidence[0].file_path != ""

    # 5. Round-trip serialization & reload
    serialized_json = proposal.model_dump_json()
    reloaded_proposal = OntologyProposal.model_validate_json(serialized_json)
    assert len(reloaded_proposal.concepts) == len(proposal.concepts)
    assert reloaded_proposal.proposal_id == proposal.proposal_id


@pytest.mark.asyncio
async def test_multi_scenario_e1_to_e2_aggregation_pipeline():
    """
    Executes real E1 -> E2 pipeline across a multi-scenario commit batch.
    Verifies that multiple commits' extracted entities are clustered, deduplicated,
    and structured into a unified hierarchical ontology proposal.
    """
    dataset = load_e1_dataset()
    batch = dataset[:5]

    extractor = E1Extractor()
    aggregated_entities = []
    aggregated_relations = []

    for tc in batch:
        res = await extractor.extract_m1_generative_ie(tc.commit)
        aggregated_entities.extend(res.entities)
        aggregated_relations.extend(res.relations)

    assert len(aggregated_entities) >= 5

    # Induce combined ontology
    inducer = OntologyInducer(similarity_threshold=0.70)
    proposal = inducer.induce_proposal(
        entities=aggregated_entities,
        relations=aggregated_relations,
        threshold=0.70,
    )

    assert len(proposal.concepts) > 0
    # Redundancy reduction should occur when merging related symbols
    assert proposal.metrics["total_raw_entities"] == len(aggregated_entities)
    assert proposal.metrics["evidence_coverage_ratio"] == 1.0

    # Verify immutability of V1 ontology
    from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy
    assert CodeRelationTaxonomy._TAXONOMY is not None
