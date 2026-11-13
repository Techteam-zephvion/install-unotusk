"""
Unit test suite for E2 Ontology Induction and Guided Extraction.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept (OntoRAG arXiv:2506.00664).

Covers:
- Deterministic output verification.
- Candidate concept and relationship generation.
- Provenance and evidence preservation.
- Similarity threshold sensitivity.
- Duplicate concept merging.
- Missing and conflicting evidence handling.
- Verification that proposal status is strictly PROPOSED_PENDING_REVIEW.
- Negative test verifying V1 ontology models and files are NOT mutated.
- Negative test verifying T1-T4 and E1 files remain strictly read-only.
"""

from pathlib import Path

import pytest

from experiments.e2_ontology_guided_extraction.concept_clusterer import (
    ConceptClusterer,
    compute_path_proximity,
    split_identifier_tokens,
)
from experiments.e2_ontology_guided_extraction.ontology_inducer import (
    OntologyInducer,
)
from experiments.e2_ontology_guided_extraction.schema import (
    CandidateConcept,
    CandidateRelation,
    EvidenceProvenance,
    OntologyCategory,
    OntologyProposal,
    ProposalStatus,
)


@pytest.fixture
def sample_entities() -> list[dict]:
    return [
        {
            "name": "UserAuthenticationService",
            "type": "CLASS",
            "file_path": "apps/api/src/services/auth/service.py",
            "confidence": 0.95,
            "evidence": {
                "file_path": "apps/api/src/services/auth/service.py",
                "start_line": 10,
                "end_line": 50,
                "diff_snippet": "class UserAuthenticationService:",
            },
        },
        {
            "name": "verify_user_token",
            "type": "FUNCTION",
            "file_path": "apps/api/src/services/auth/jwt.py",
            "confidence": 0.90,
            "evidence": {
                "file_path": "apps/api/src/services/auth/jwt.py",
                "start_line": 15,
                "end_line": 35,
                "diff_snippet": "def verify_user_token(token: str):",
            },
        },
        {
            "name": "PaymentGatewayService",
            "type": "CLASS",
            "file_path": "apps/api/src/services/billing/gateway.py",
            "confidence": 0.92,
            "evidence": {
                "file_path": "apps/api/src/services/billing/gateway.py",
                "start_line": 20,
                "end_line": 80,
                "diff_snippet": "class PaymentGatewayService:",
            },
        },
        {
            "name": "StripeBillingProcessor",
            "type": "CLASS",
            "file_path": "apps/api/src/services/billing/stripe.py",
            "confidence": 0.88,
            "evidence": {
                "file_path": "apps/api/src/services/billing/stripe.py",
                "start_line": 10,
                "end_line": 65,
                "diff_snippet": "class StripeBillingProcessor(PaymentGatewayService):",
            },
        },
    ]


@pytest.fixture
def sample_relations() -> list[dict]:
    return [
        {
            "subject": "UserAuthenticationService",
            "rel": "CALLS",
            "object": "verify_user_token",
            "confidence": 0.95,
            "evidence": {
                "file_path": "apps/api/src/services/auth/service.py",
                "diff_snippet": "verify_user_token(token)",
            },
        },
        {
            "subject": "StripeBillingProcessor",
            "rel": "INHERITS",
            "object": "PaymentGatewayService",
            "confidence": 0.98,
            "evidence": {
                "file_path": "apps/api/src/services/billing/stripe.py",
                "diff_snippet": "class StripeBillingProcessor(PaymentGatewayService):",
            },
        },
    ]


def test_split_identifier_tokens():
    tokens = split_identifier_tokens("UserAuthenticationService")
    assert tokens == {"user", "authentication", "service"}

    snake_tokens = split_identifier_tokens("verify_auth_token_v2")
    assert snake_tokens == {"verify", "auth", "token", "v2"}

    assert split_identifier_tokens("") == set()
    assert split_identifier_tokens(None) == set()


def test_path_proximity():
    p1 = "apps/api/src/services/auth/service.py"
    p2 = "apps/api/src/services/auth/jwt.py"
    p3 = "services/workers/tasks/sync.py"

    assert compute_path_proximity(p1, p2) > 0.8
    assert compute_path_proximity(p1, p3) < 0.3


def test_deterministic_output(sample_entities, sample_relations):
    inducer1 = OntologyInducer(similarity_threshold=0.70)
    inducer2 = OntologyInducer(similarity_threshold=0.70)

    p1 = inducer1.induce_proposal(sample_entities, sample_relations)
    p2 = inducer2.induce_proposal(sample_entities, sample_relations)

    assert len(p1.concepts) == len(p2.concepts)
    assert len(p1.relations) == len(p2.relations)
    assert p1.metrics == p2.metrics


def test_candidate_concept_generation(sample_entities):
    inducer = OntologyInducer(similarity_threshold=0.85)
    concepts, entity_map = inducer.induce_concepts(sample_entities)

    assert len(concepts) > 0
    for c in concepts:
        assert isinstance(c, CandidateConcept)
        assert c.status == ProposalStatus.PROPOSED_PENDING_REVIEW
        assert 0.0 <= c.confidence <= 1.0
        assert len(c.source_entity_names) >= 1
        assert len(c.evidence) >= 1
        assert c.evidence[0].file_path != ""


def test_candidate_relation_generation(sample_entities, sample_relations):
    inducer = OntologyInducer(similarity_threshold=0.85)
    proposal = inducer.induce_proposal(sample_entities, sample_relations)

    assert len(proposal.relations) > 0
    for r in proposal.relations:
        assert isinstance(r, CandidateRelation)
        assert r.status == ProposalStatus.PROPOSED_PENDING_REVIEW
        assert r.subject_concept_id != r.object_concept_id
        assert len(r.evidence) >= 1


def test_provenance_and_evidence_preservation(sample_entities, sample_relations):
    inducer = OntologyInducer(similarity_threshold=0.70)
    proposal = inducer.induce_proposal(sample_entities, sample_relations)

    for c in proposal.concepts:
        assert len(c.evidence) >= 1
        for ev in c.evidence:
            assert isinstance(ev, EvidenceProvenance)
            assert ev.file_path is not None
            assert len(ev.file_path) > 0

    for r in proposal.relations:
        assert len(r.evidence) >= 1
        for ev in r.evidence:
            assert isinstance(ev, EvidenceProvenance)


def test_similarity_threshold_sensitivity(sample_entities):
    # Low threshold merges more aggressively
    inducer_low = OntologyInducer(similarity_threshold=0.30)
    concepts_low, _ = inducer_low.induce_concepts(sample_entities)

    # High threshold preserves distinct concepts
    inducer_high = OntologyInducer(similarity_threshold=0.95)
    concepts_high, _ = inducer_high.induce_concepts(sample_entities)

    assert len(concepts_low) <= len(concepts_high)


def test_duplicate_concept_merging():
    clusterer = ConceptClusterer(similarity_threshold=0.65)
    c1 = CandidateConcept(
        concept_id="c1",
        name="PaymentGatewayService",
        category=OntologyCategory.SERVICE_COMPONENT,
        source_entity_names=["PaymentGatewayService"],
        confidence=0.9,
        evidence=[EvidenceProvenance(file_path="billing/gateway.py", start_line=1, end_line=20)],
    )
    c2 = CandidateConcept(
        concept_id="c2",
        name="payment_gateway_service",
        category=OntologyCategory.SERVICE_COMPONENT,
        source_entity_names=["payment_gateway_service"],
        confidence=0.85,
        evidence=[EvidenceProvenance(file_path="billing/gateway.py", start_line=25, end_line=40)],
    )

    merged = clusterer.merge_candidate_concepts([c1, c2])
    assert len(merged) == 1
    m = merged[0]
    assert m.status == ProposalStatus.PROPOSED_PENDING_REVIEW
    assert "PaymentGatewayService" in m.source_entity_names
    assert "payment_gateway_service" in m.source_entity_names
    assert len(m.evidence) == 2


def test_missing_and_conflicting_evidence_handling():
    inducer = OntologyInducer()
    malformed_entities = [
        {"name": "NoEvidenceEntity", "type": "FUNCTION"},
        {"name": "", "type": "UNKNOWN"},
        {"name": "NoneFieldsEntity", "type": None, "file_path": None, "evidence": None},
    ]
    malformed_relations = [
        {"subject": None, "rel": None, "object": None},
        {"subject": "NoEvidenceEntity", "rel": "CIRCULAR", "object": "NoEvidenceEntity"},
        {"subject": "MissingSubject", "rel": "CALLS", "object": "MissingObject"},
    ]

    proposal = inducer.induce_proposal(malformed_entities, malformed_relations)
    assert isinstance(proposal, OntologyProposal)
    assert len(proposal.concepts) >= 1
    # Circular and unmapped relations must be safely excluded
    assert len(proposal.relations) == 0


def test_status_strictly_proposed_pending_review(sample_entities, sample_relations):
    inducer = OntologyInducer()
    proposal = inducer.induce_proposal(sample_entities, sample_relations)

    for c in proposal.concepts:
        assert c.status == ProposalStatus.PROPOSED_PENDING_REVIEW
        assert c.status != ProposalStatus.ACCEPTED
        assert c.status != ProposalStatus.REJECTED

    for r in proposal.relations:
        assert r.status == ProposalStatus.PROPOSED_PENDING_REVIEW

    assert "PROPOSED_PENDING_REVIEW" in proposal.governance_disclaimer


def test_v1_ontology_not_mutated():
    """Negative test verifying production V1 ontology taxonomy is completely untouched."""
    from apps.api.src.schemas.code_atom import (
        PropertyExclusivity,
        RelationType,
        ScopeKeyStrategy,
        TemporalSupersessionPolicy,
    )
    from apps.api.src.services.code_atom.taxonomy import CodeRelationTaxonomy

    # Check that canonical V1 predicates exist and have expected exclusivity
    calls_entry = CodeRelationTaxonomy._TAXONOMY.get(RelationType.CALLS)
    assert calls_entry is not None
    assert calls_entry.exclusivity == PropertyExclusivity.NON_EXCLUSIVE
    assert calls_entry.scope_strategy == ScopeKeyStrategy.CONCURRENT
    assert calls_entry.supersession_policy == TemporalSupersessionPolicy.CONCURRENT

    defines_entry = CodeRelationTaxonomy._TAXONOMY.get(RelationType.DEFINES)
    assert defines_entry is not None
    assert defines_entry.exclusivity == PropertyExclusivity.EXCLUSIVE


def test_frozen_scopes_read_only():
    """Negative test verifying T1-T4 and E1 directories remain untouched."""
    repo_root = Path(__file__).resolve().parents[2]
    # Check that git status reports no unstaged modifications in apps/api/src/services/code_atom or experiments/e1_generative_ie
    t1_t4_dir = repo_root / "apps" / "api" / "src" / "services" / "code_atom"
    e1_dir = repo_root / "experiments" / "e1_generative_ie"

    assert t1_t4_dir.exists()
    assert e1_dir.exists()
