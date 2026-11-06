"""
Unit tests for E1 Generative Information Extraction Proof of Concept.
Verifies schema compliance, context builder, grounding validator, and extraction configurations.
"""

import pytest

from experiments.e1_generative_ie.benchmark import E1BenchmarkRunner
from experiments.e1_generative_ie.data.dataset import load_e1_dataset
from experiments.e1_generative_ie.schema import (
    E1Entity,
    E1EntityType,
    E1Event,
    E1EventType,
    E1ExtractionResult,
    E1Relation,
    E1RelationType,
    E1SourceEvidence,
)
from experiments.e1_generative_ie.validator import E1GroundingValidator


def test_e1_schema_instantiation():
    """Verifies that E1 Pydantic models validate and serialize properly."""
    evidence = E1SourceEvidence(
        file_path="apps/api/src/services/auth.py",
        start_line=10,
        end_line=25,
        diff_snippet="+ def verify_token(): pass",
        grounded_tokens=["verify_token", "auth"],
    )

    entity = E1Entity(
        entity_id="ent-123",
        entity_type=E1EntityType.FUNCTION.value,
        entity_name="verify_token",
        file_path="apps/api/src/services/auth.py",
        evidence=evidence,
    )

    relation = E1Relation(
        relation_id="rel-123",
        subject="AuthService",
        relation_type=E1RelationType.CALLS.value,
        object="verify_token",
        evidence=evidence,
    )

    event = E1Event(
        event_id="evt-123",
        event_type=E1EventType.BEHAVIOR_CHANGED.value,
        trigger_statement="Update auth token validation logic",
        target_component="AuthService",
        evidence=evidence,
    )

    result = E1ExtractionResult(
        commit_sha="a1b2c3d4",
        commit_message="feat(auth): enhance token verification",
        entities=[entity],
        relations=[relation],
        events=[event],
    )

    assert result.commit_sha == "a1b2c3d4"
    assert len(result.entities) == 1
    assert result.entities[0].entity_name == "verify_token"
    assert result.relations[0].relation_type == "CALLS"
    assert result.events[0].event_type == "BEHAVIOR_CHANGED"
    assert result.schema_version == "1.0.0"


def test_e1_grounding_validator():
    """Verifies that ungrounded tokens are rejected and grounded tokens are accepted."""
    validator = E1GroundingValidator()

    raw_diff = (
        "--- a/service.py\n"
        "+++ b/service.py\n"
        "@@ -1,3 +1,4 @@\n"
        "+def calculate_tax(amount: float):\n"
        "+    return amount * 0.15\n"
    )
    msg = "feat: calculate tax for orders"

    # Grounded entity
    good_entity = E1Entity(
        entity_id="e1",
        entity_type="FUNCTION",
        entity_name="calculate_tax",
        file_path="service.py",
        evidence=E1SourceEvidence(file_path="service.py", diff_snippet="calculate_tax"),
    )

    # Hallucinated entity not present in diff or commit message
    spurious_entity = E1Entity(
        entity_id="e2",
        entity_type="CLASS",
        entity_name="StripePaymentGatewayProxy",
        file_path="service.py",
        evidence=E1SourceEvidence(file_path="service.py", diff_snippet="StripePaymentGatewayProxy"),
    )

    res = E1ExtractionResult(
        commit_sha="112233",
        commit_message=msg,
        entities=[good_entity, spurious_entity],
    )

    validated = validator.validate_result(res, raw_diff, msg)
    assert len(validated.entities) == 1
    assert validated.entities[0].entity_name == "calculate_tax"
    assert any("StripePaymentGatewayProxy" in w for w in validated.warnings)


def test_e1_abstention_on_trivial_diff():
    """Verifies that empty or whitespace-only diffs trigger abstention."""
    validator = E1GroundingValidator()
    trivial_diff = (
        "--- a/test.py\n"
        "+++ b/test.py\n"
        "@@ -1,2 +1,2 @@\n"
        "-x = 1   \n"
        "+x = 1\n"
    )
    msg = "cleanup whitespace"

    res = E1ExtractionResult(
        commit_sha="998877",
        commit_message=msg,
        entities=[
            E1Entity(
                entity_id="e1",
                entity_type="OTHER",
                entity_name="test.py",
                file_path="test.py",
                evidence=E1SourceEvidence(file_path="test.py"),
            )
        ],
    )

    validated = validator.validate_result(res, trivial_diff, msg)
    assert validated.abstention_triggered is True
    assert len(validated.entities) == 0


def test_e1_dataset_integrity():
    """Verifies that the 40-scenario evaluation corpus is loaded and split cleanly."""
    cases = load_e1_dataset()
    assert len(cases) == 40

    dev_cases = [c for c in cases if c.split == "dev"]
    eval_cases = [c for c in cases if c.split == "eval"]

    assert len(dev_cases) == 20
    assert len(eval_cases) == 20

    # Ensure unique IDs
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids))


@pytest.mark.asyncio
async def test_e1_benchmark_runner_execution():
    """Verifies that benchmark runner executes without crash on dev split."""
    runner = E1BenchmarkRunner()
    results = await runner.run_benchmark(split="dev")

    assert "M0_ATOM_Baseline" in results
    assert "M1_Generative_IE" in results
    assert "M2_Constrained_Decoding" in results

    for _name, br in results.items():
        assert br.total_cases == 20
        assert br.schema_validity_rate == 1.0
        assert br.evidence_grounding_accuracy == 1.0
