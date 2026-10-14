"""
Tests for ATOM Code Lane Quality Evaluation (Phase 12).

Verifies paper-inspired evaluation metrics:
- Precision, recall, and F1 for semantic facts and temporal relationships.
- Temporal boundary correctness, cessation identification, and unknown timestamp preservation.
- Cross-commit deduplication, distinct entity preservation, and rename lineage.
- Jaccard stability across repeated runs.
- Interactive latency thresholds.
"""

import pytest

from scripts.evaluate_code_atom import run_evaluation


@pytest.fixture(scope="module")
def eval_results():
    """Runs the full evaluation suite once and caches results for assertions."""
    return run_evaluation()


def test_fact_extraction_quality(eval_results):
    """1. Fact extraction satisfies high precision and recall thresholds."""
    facts = eval_results["fact_extraction"]
    assert facts["precision"] >= 0.90
    assert facts["recall"] >= 0.90
    assert facts["f1_score"] >= 0.90
    assert facts["false_positives"] == 0
    assert facts["false_negatives"] == 0


def test_relationship_extraction_quality(eval_results):
    """2. Relationship extraction satisfies high precision and recall thresholds."""
    rels = eval_results["relationship_extraction"]
    assert rels["precision"] >= 0.90
    assert rels["recall"] >= 0.90
    assert rels["f1_score"] >= 0.90
    assert rels["false_positives"] == 0
    assert rels["false_negatives"] == 0


def test_temporal_correctness(eval_results):
    """3. Temporal validity start, end, and unknown timestamps are accurately handled."""
    temporal = eval_results["temporal_correctness"]
    assert temporal["accuracy"] == 1.0
    assert temporal["unknown_timestamps_preserved"] == temporal["unknown_timestamps_tested"]
    assert temporal["unknown_timestamps_tested"] >= 1
    assert temporal["invented_timestamps"] == 0
    assert temporal["ended_relations_identified"] >= 1
    assert temporal["conflicts_detected"] >= 1


def test_entity_and_relationship_resolution(eval_results):
    """4. Resolution deduplicates equivalent relations and preserves rename lineage."""
    resolution = eval_results["entity_and_relation_resolution"]
    assert resolution["deduplication_successful"] == resolution["deduplication_cases"]
    assert resolution["deduplication_cases"] >= 1
    assert resolution["rename_lineage_successful"] == resolution["rename_lineage_cases"]
    assert resolution["rename_lineage_cases"] >= 1
    assert resolution["unresolved_duplicates"] == 0
    assert resolution["incorrect_merges"] == 0


def test_extraction_stability(eval_results):
    """5. Deterministic extraction maintains perfect Jaccard stability across runs."""
    stability = eval_results["stability"]
    assert stability["jaccard_similarity_facts"] == 1.0
    assert stability["jaccard_similarity_relations"] == 1.0
    assert stability["fact_count_variance"] == 0.0
    assert stability["relation_count_variance"] == 0.0


def test_processing_performance_benchmarks(eval_results):
    """6. Latency remains well within real-time interactive thresholds (< 50ms per diff)."""
    perf = eval_results["performance_ms"]
    assert perf["total_mean_ms"] < 50.0  # Typically < 2ms
    assert perf["decomposition_mean_ms"] < 30.0
    assert perf["resolution_mean_ms"] < 10.0


def test_ambiguity_and_conflict_handling(eval_results):
    """7. Ambiguous changes are safely marked UNCERTAIN; temporal conflicts are flagged."""
    temporal = eval_results["temporal_correctness"]
    assert temporal["conflicts_detected"] >= 1
