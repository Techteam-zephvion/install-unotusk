"""
Tests for ATOM Real-Repository Quality and Code Retrieval Evaluation (Phase 14).

Validates end-to-end performance against 10 genuine git commits and developer queries:
1. ATOM Fact Extraction (Precision, Recall, F1 >= 0.90)
2. ATOM Temporal Relationship Extraction (Precision, Recall, F1 >= 0.90)
3. Temporal Invariants (Zero invented timestamps, cessation tracking)
4. End-to-End Retrieval (MRR >= 0.85, Recall@3 >= 0.90, Recall@5 >= 0.90)
5. Provenance Survival (100% preservation of commit SHA and line ranges)
6. Extraction Stability (Jaccard similarity = 1.0 across repeated runs)
7. Processing Latency (< 50ms per diff)
8. Embedding Provider Reality Check (voyage-code-2 spec, development fallback, pgvector)
"""

import pytest

from scripts.evaluate_real_repo_atom import run_real_repo_evaluation
from tests.fixtures.atom_real_repo_dataset import get_real_repo_dataset


@pytest.fixture(scope="module")
def real_repo_eval():
    """Runs the full real-repository evaluation suite and caches results."""
    import asyncio

    return asyncio.run(run_real_repo_evaluation())


def test_real_repo_dataset_loaded():
    """Verifies that all 10 curated real repository cases are properly loaded."""
    cases = get_real_repo_dataset()
    assert len(cases) == 10
    categories = {c.category for c in cases}
    expected_categories = {
        "method_call",
        "removal",
        "method_replacement",
        "imports_refactor",
        "configuration",
        "admin_guard",
        "rbac_isolation",
        "file_rename",
        "pipeline_integration",
        "scope_resolution",
    }
    assert expected_categories.issubset(categories)
    for c in cases:
        assert c.commit.commit_sha
        assert c.commit.raw_diff
        assert c.retrieval_query
        assert len(c.expected_retrieval_targets) > 0


def test_real_repo_fact_extraction(real_repo_eval):
    """Verifies semantic fact extraction quality on real repository commits."""
    facts = real_repo_eval["atom_extraction_metrics"]["fact_extraction"]
    assert facts["precision"] >= 0.90
    assert facts["recall"] >= 0.90
    assert facts["f1_score"] >= 0.90
    assert facts["false_positives"] == 0
    assert facts["false_negatives"] == 0


def test_real_repo_relation_extraction(real_repo_eval):
    """Verifies temporal relationship extraction quality on real repository commits."""
    rels = real_repo_eval["atom_extraction_metrics"]["relation_extraction"]
    assert rels["precision"] >= 0.90
    assert rels["recall"] >= 0.90
    assert rels["f1_score"] >= 0.90
    assert rels["false_positives"] == 0
    assert rels["false_negatives"] == 0


def test_real_repo_temporal_correctness(real_repo_eval):
    """Verifies temporal validity start, end, and zero timestamp invention."""
    temporal = real_repo_eval["atom_extraction_metrics"]["temporal_correctness"]
    assert temporal["temporal_accuracy"] >= 0.90
    assert temporal["invented_timestamps"] == 0
    assert temporal["ended_relations_identified"] >= 1


def test_real_repo_retrieval_performance(real_repo_eval):
    """Verifies end-to-end code retrieval metrics on developer queries."""
    retrieval = real_repo_eval["retrieval_evaluation"]
    assert retrieval["mean_reciprocal_rank"] >= 0.85
    assert retrieval["recall_at_1"] >= 0.80
    assert retrieval["recall_at_3"] >= 0.90
    assert retrieval["recall_at_5"] >= 0.90
    assert retrieval["provenance_survival_rate"] == 1.0


def test_real_repo_extraction_stability(real_repo_eval):
    """Verifies deterministic stability across repeated runs on real commits."""
    stability = real_repo_eval["atom_extraction_metrics"]["extraction_stability"]
    assert stability["fact_jaccard"] == 1.0
    assert stability["relation_jaccard"] == 1.0


def test_real_repo_processing_latency(real_repo_eval):
    """Verifies that decomposition and resolution latency remains < 50ms per commit."""
    latencies = real_repo_eval["atom_extraction_metrics"]["latency_ms"]
    assert latencies["total_mean_ms"] < 50.0
    assert latencies["decomposition_mean_ms"] < 30.0
    assert latencies["resolution_mean_ms"] < 10.0


def test_embedding_provider_reality_check(real_repo_eval):
    """Verifies embedding provider configuration, fallback mode, and vector storage."""
    emb = real_repo_eval["embedding_provider_verification"]
    assert emb["voyage_target_model"] == "voyage-code-2"
    assert emb["voyage_target_dimension"] == 1536
    assert "PostgreSQL 16 + pgvector" in emb["database_storage_layer"]
    assert emb["fallback_mode_active"] is True
    assert emb["live_credentials_available"] is False
    assert "Qdrant discarded" in emb["external_vector_db_discarded"]
