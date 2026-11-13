"""
Comprehensive Test Suite for E3 Sparse-Project Confidence Scoring.
Part of Unotusk AI-PIE Code Lane Research Proof of Concept.

Validates:
1. High-quality direct evidence evaluation.
2. Sparse but valid single-commit evidence handling.
3. Missing provenance penalties and abstention.
4. Duplicate evidence handling and redundancy penalty.
5. Contradictory relationship detection and penalties.
6. Cross-commit and cross-file corroboration scoring.
7. Structural consistency and circular dependency detection.
8. Keyword pseudo-F1 ground-truth proxy calculation.
9. Deterministic repeated execution stability.
10. Round-trip JSON serialization and validation.
11. Real end-to-end integration: Commit -> E1 -> E2 -> E3.
"""

import pytest

from experiments.e1_generative_ie.data.dataset import load_e1_dataset
from experiments.e1_generative_ie.schema import (
    E1Entity,
    E1EntityType,
    E1ExtractionResult,
    E1Relation,
    E1RelationType,
    E1SourceEvidence,
    ValidationStatus,
)
from experiments.e2_ontology_guided_extraction.schema import (
    CandidateConcept,
    ProposalStatus,
)
from experiments.e3_sparse_confidence import metrics
from experiments.e3_sparse_confidence.confidence_engine import SparseConfidenceEngine
from experiments.e3_sparse_confidence.pipeline import run_e1_e2_e3_pipeline
from experiments.e3_sparse_confidence.schema import (
    ConfidenceLevel,
    E3AssessmentResult,
    SufficiencyLevel,
)


def test_high_quality_direct_evidence():
    """Verifies that an entity with complete provenance, valid syntax, and diff match scores HIGH."""
    ev = E1SourceEvidence(
        file_path="apps/api/src/services/scorer.py",
        start_line=12,
        end_line=24,
        diff_snippet="def calculate_score(val): return val * 1.5",
        grounded_tokens=["calculate_score", "val"],
    )
    ent = E1Entity(
        entity_id="ent_001",
        entity_name="calculate_score",
        entity_type=E1EntityType.FUNCTION.value,
        file_path="apps/api/src/services/scorer.py",
        evidence=ev,
    )

    engine = SparseConfidenceEngine()
    assessment = engine.evaluate_entity(ent, diff_text="def calculate_score(val): return val * 1.5")

    assert assessment.confidence_score >= 0.75
    assert assessment.confidence_level == ConfidenceLevel.HIGH
    assert assessment.is_abstention is False
    assert assessment.metric_scores.provenance_completeness >= 0.85
    assert assessment.metric_scores.term_frequency_coherence == 1.0


def test_sparse_single_commit_not_penalized_for_sparsity():
    """
    In sparse software projects, high direct evidence in 1 commit must score HIGH,
    not artificially depressed just because total commit count is 1.
    """
    ev = E1SourceEvidence(
        file_path="services/workers/queue.py",
        start_line=45,
        end_line=50,
        diff_snippet="class RedisClient:\n    async def connect(self): pass",
        grounded_tokens=["RedisClient", "connect"],
    )
    ent = E1Entity(
        entity_id="ent_002",
        entity_name="RedisClient",
        entity_type=E1EntityType.CLASS.value,
        file_path="services/workers/queue.py",
        evidence=ev,
    )

    engine = SparseConfidenceEngine()
    assessment = engine.evaluate_entity(ent, diff_text="class RedisClient:\n    async def connect(self): pass")

    # Direct fact confidence remains HIGH
    assert assessment.confidence_score >= 0.75
    assert assessment.confidence_level == ConfidenceLevel.HIGH


def test_missing_provenance_penalties_and_abstention():
    """Verifies that missing file path or lines severely penalizes confidence and triggers abstention."""
    ev = E1SourceEvidence(
        file_path="",  # Missing file path
        start_line=None,  # Missing line numbers
        end_line=None,
        diff_snippet="",
        grounded_tokens=[],
    )
    ent = E1Entity(
        entity_id="ent_bad",
        entity_name="GhostFunction",
        entity_type=E1EntityType.FUNCTION.value,
        file_path="",
        evidence=ev,
    )

    engine = SparseConfidenceEngine()
    assessment = engine.evaluate_entity(ent, diff_text="some diff")

    assert assessment.confidence_score < 0.50
    assert assessment.is_abstention is True
    assert assessment.confidence_level == ConfidenceLevel.INSUFFICIENT_EVIDENCE
    assert any("Incomplete source file" in s for s in assessment.missing_signals)


def test_duplicate_evidence_redundancy_penalty():
    """
    Verifies that identical facts repeated from the same evidence span incur
    a redundancy penalty rather than being credited as independent corroboration.
    """
    ev = E1SourceEvidence(
        file_path="apps/api/src/main.py",
        start_line=10,
        end_line=20,
        diff_snippet="app = FastAPI()",
        grounded_tokens=["app"],
    )
    ent1 = E1Entity(entity_id="e1", entity_name="app", entity_type=E1EntityType.SERVICE.value, file_path="apps/api/src/main.py", evidence=ev)
    ent2 = E1Entity(entity_id="e2", entity_name="app", entity_type=E1EntityType.SERVICE.value, file_path="apps/api/src/main.py", evidence=ev)

    engine = SparseConfidenceEngine()
    assessment = engine.evaluate_entity(ent1, occurrences=[ent1, ent2])

    assert assessment.metric_scores.redundancy_penalty > 0.0
    # Both from same file and line, so independent sources count is 1
    assert assessment.independent_sources_count == 1


def test_cross_file_independent_corroboration():
    """Verifies that occurrences across multiple distinct files receive increased corroboration scores."""
    ev1 = E1SourceEvidence(file_path="apps/api/src/auth.py", start_line=10, end_line=15, diff_snippet="BearerAuth")
    ev2 = E1SourceEvidence(file_path="tests/unit/test_auth.py", start_line=5, end_line=10, diff_snippet="BearerAuth")
    ev3 = E1SourceEvidence(file_path="apps/api/src/router.py", start_line=20, end_line=25, diff_snippet="BearerAuth")

    score, n_files, _ = metrics.compute_corroboration_score([
        E1Entity(entity_id="e1", entity_name="BearerAuth", file_path="apps/api/src/auth.py", evidence=ev1),
        E1Entity(entity_id="e2", entity_name="BearerAuth", file_path="tests/unit/test_auth.py", evidence=ev2),
        E1Entity(entity_id="e3", entity_name="BearerAuth", file_path="apps/api/src/router.py", evidence=ev3),
    ])

    assert n_files == 3
    assert score == 1.00


def test_contradictory_relationship_detection():
    """Verifies that reciprocal contradictory relations (e.g. mutual REPLACES) trigger contradiction penalty."""
    ev = E1SourceEvidence(file_path="apps/api/src/services/auth.py", start_line=1, end_line=10, diff_snippet="auth")
    rel1 = E1Relation(
        relation_id="r1",
        subject="BearerAuth",
        relation_type=E1RelationType.REPLACES.value,
        object="LegacySessionAuth",
        evidence=ev,
    )
    rel2 = E1Relation(
        relation_id="r2",
        subject="LegacySessionAuth",
        relation_type=E1RelationType.REPLACES.value,
        object="BearerAuth",
        evidence=ev,
    )

    penalty, contradictions = metrics.detect_contradictions([rel1, rel2])

    assert penalty > 0.0
    assert len(contradictions) >= 1
    assert any("Contradictory reciprocal REPLACES" in c for c in contradictions)

    engine = SparseConfidenceEngine()
    assessment = engine.evaluate_relation(rel1, all_relations=[rel1, rel2])
    assert assessment.is_abstention is True
    assert len(assessment.contradictions) > 0


def test_structural_consistency_and_hierarchy():
    """Verifies that circular containment or self-referential relations trigger structural penalties."""
    ev = E1SourceEvidence(file_path="test.py", start_line=1, end_line=5, diff_snippet="code")
    rel_self = E1Relation(relation_id="rs", subject="ModuleA", relation_type="DEFINES", object="ModuleA", evidence=ev)

    score, violations = metrics.compute_structural_consistency([rel_self])
    assert score < 1.0
    assert any("Self-referencing" in v for v in violations)


def test_keyword_pseudo_f1_calculation():
    """Verifies keyword pseudo-F1 computation as an explicitly labeled proxy."""
    diff = """
    @@ -1,5 +1,6 @@
    +def calculate_tax(amount):
    +    return amount * 0.2
    """
    res = metrics.compute_keyword_pseudo_f1(diff, ["calculate_tax"])
    assert res["pseudo_precision"] == 1.0
    assert res["pseudo_recall"] > 0.0
    assert res["pseudo_f1"] > 0.0


def test_deterministic_repeated_execution():
    """Verifies that running the confidence engine repeatedly produces bit-for-bit identical scores."""
    ev = E1SourceEvidence(
        file_path="apps/api/src/routers/repos.py",
        start_line=20,
        end_line=30,
        diff_snippet="@router.get('/repos')\ndef list_repos(): pass",
        grounded_tokens=["router", "list_repos"],
    )
    ent = E1Entity(entity_id="e_det", entity_name="list_repos", entity_type=E1EntityType.API.value, file_path="apps/api/src/routers/repos.py", evidence=ev)

    engine = SparseConfidenceEngine()
    run1 = engine.evaluate_entity(ent, diff_text="def list_repos(): pass")
    run2 = engine.evaluate_entity(ent, diff_text="def list_repos(): pass")

    assert run1.confidence_score == run2.confidence_score
    assert run1.metric_scores.provenance_completeness == run2.metric_scores.provenance_completeness
    assert run1.metric_scores.term_frequency_coherence == run2.metric_scores.term_frequency_coherence


def test_serialization_and_round_trip(tmp_path):
    """Verifies that E3AssessmentResult serializes to JSON and reloads without loss."""
    ds = load_e1_dataset()
    tc = ds[0]
    engine = SparseConfidenceEngine()

    res = E1ExtractionResult(
        commit_sha=tc.commit.commit_sha,
        commit_message=tc.commit.commit_message,
        entities=[
            E1Entity(
                entity_id="e1",
                entity_name="scorer",
                entity_type=E1EntityType.MODULE.value,
                file_path="apps/api/src/services/scorer.py",
                evidence=E1SourceEvidence(file_path="apps/api/src/services/scorer.py", start_line=1, end_line=10, diff_snippet="def f(): pass"),
            )
        ],
    )

    assessment = engine.evaluate_project(commits=[tc.commit], e1_results=[res], budget_label="test_run")
    json_path = tmp_path / "assessment.json"
    json_path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")

    reloaded = E3AssessmentResult.model_validate_json(json_path.read_text(encoding="utf-8"))
    assert reloaded.assessment_id == assessment.assessment_id
    assert len(reloaded.entity_assessments) == 1
    assert reloaded.project_assessment.commit_count == 1
    assert reloaded.project_assessment.evidence_sufficiency == SufficiencyLevel.SPARSE


@pytest.mark.asyncio
async def test_real_e1_e2_e3_pipeline_integration(tmp_path):
    """
    Genuine end-to-end integration test:
    GitCommitArtifact -> E1Extractor -> E2OntologyInducer -> E3SparseConfidenceEngine.
    """
    ds = load_e1_dataset()
    # Use real test cases from the dataset
    sample_commits = [ds[0].commit, ds[1].commit]

    out_file = tmp_path / "pipeline_result.json"

    e1_results, proposal, assessment = await run_e1_e2_e3_pipeline(
        commits=sample_commits,
        similarity_threshold=0.70,
        output_path=out_file,
        budget_label="2_commits_integration",
    )

    # 1. E1 assertions
    assert len(e1_results) == 2
    for r in e1_results:
        assert isinstance(r, E1ExtractionResult)
        assert len(r.entities) >= 1
        assert all(e.validation_status == ValidationStatus.VALIDATED for e in r.entities)

    # 2. E2 assertions
    assert len(proposal.concepts) >= 1
    for c in proposal.concepts:
        assert isinstance(c, CandidateConcept)
        assert c.status == ProposalStatus.PROPOSED_PENDING_REVIEW

    # 3. E3 assertions
    assert isinstance(assessment, E3AssessmentResult)
    assert assessment.project_assessment.commit_count == 2
    assert len(assessment.entity_assessments) == sum(len(r.entities) for r in e1_results)
    assert assessment.project_assessment.overall_confidence_score > 0.0

    # 4. Persistence validation
    assert out_file.exists()
    reloaded = E3AssessmentResult.model_validate_json(out_file.read_text(encoding="utf-8"))
    assert reloaded.assessment_id == assessment.assessment_id
    assert reloaded.project_assessment.overall_confidence_level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
