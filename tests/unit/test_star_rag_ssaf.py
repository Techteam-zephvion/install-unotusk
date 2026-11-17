"""
Unit tests for Structure-Aware STAR-RAG Semantic-Structural Adaptive Fusion (SSAF).
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).
"""

import uuid

from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.ssaf_fusion import (
    SemanticStructuralAdaptiveFusion,
)


def test_ssaf_adapts_to_structural_tracing_query():
    """Verify SSAF shifts adaptive weight towards the structural stream for tracing queries."""
    ssaf = SemanticStructuralAdaptiveFusion()
    query = "Trace the dependency chain between payment API and ledger database."
    analyzed = analyze_query(query)

    # Candidate with strong structural graph score but moderate semantic
    cand_struct = RetrievedCandidate(
        candidate_id="cand_struct",
        entity_type="CHUNK",
        name="ledger_repo",
        path="db/ledger.py",
        start_line=1,
        end_line=20,
        content="class LedgerRepo: pass",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.40, "dtp_structural": 0.85},
    )

    ranked, results = ssaf.fuse_and_rank_candidates([cand_struct], query, analyzed)

    res = results[0]
    # For a structural query, adaptive beta (semantic weight) should be lower than default 0.55
    assert res.adaptive_beta < 0.50
    # Structural weight (1 - beta) > 0.50
    assert (1.0 - res.adaptive_beta) > 0.50
    assert "Structural/Dependency tracing prioritized" in " ".join(res.explanation)


def test_ssaf_adapts_to_conceptual_semantic_query():
    """Verify SSAF shifts adaptive weight towards the semantic stream for conceptual queries."""
    ssaf = SemanticStructuralAdaptiveFusion()
    query = "Explain the business logic and meaning of transaction fees."
    analyzed = analyze_query(query)

    cand_sem = RetrievedCandidate(
        candidate_id="cand_sem",
        entity_type="CHUNK",
        name="calculate_fee",
        path="services/fee.py",
        start_line=1,
        end_line=20,
        content="def calculate_fee(): pass",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.90, "dtp_structural": 0.20},
    )

    ranked, results = ssaf.fuse_and_rank_candidates([cand_sem], query, analyzed)

    res = results[0]
    # For conceptual query, adaptive beta (semantic weight) should be high
    assert res.adaptive_beta > 0.55
    assert "Conceptual/Semantic search prioritized" in " ".join(res.explanation)


def test_ssaf_detects_semantic_structural_conflict():
    """Verify SSAF detects conflict when semantic and structural scores diverge strongly."""
    ssaf = SemanticStructuralAdaptiveFusion(conflict_threshold=0.40)
    query = "Find transaction ledger sync service."

    # Disconnected semantic candidate
    cand_conflict = RetrievedCandidate(
        candidate_id="cand_conflict",
        entity_type="CHUNK",
        name="ledger_sync",
        path="ledger.py",
        start_line=1,
        end_line=10,
        content="def ledger_sync(): pass",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.95, "content_match": 1.4, "dtp_structural": 0.05},
    )

    ranked, results = ssaf.fuse_and_rank_candidates([cand_conflict], query)

    res = results[0]
    assert res.is_conflict is True
    assert "Conflict: High semantic match with sparse/disconnected graph topology" in " ".join(res.explanation)


def test_ssaf_deterministic_ranking_stability():
    """Verify ranking is stable and reproducible across repeated runs."""
    ssaf = SemanticStructuralAdaptiveFusion()
    query = "Authenticate user credentials."

    cand_1 = RetrievedCandidate(
        candidate_id="c1",
        entity_type="CHUNK",
        name="auth_service",
        path="auth.py",
        start_line=1,
        end_line=10,
        content="auth",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.85, "dtp_structural": 0.70},
    )
    cand_2 = RetrievedCandidate(
        candidate_id="c2",
        entity_type="CHUNK",
        name="other_service",
        path="other.py",
        start_line=1,
        end_line=10,
        content="other",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.30, "dtp_structural": 0.40},
    )

    ranked_a, _ = ssaf.fuse_and_rank_candidates([cand_1, cand_2], query)
    ranked_b, _ = ssaf.fuse_and_rank_candidates([cand_2, cand_1], query)

    assert [r.candidate.candidate_id for r in ranked_a] == ["c1", "c2"]
    assert [r.candidate.candidate_id for r in ranked_b] == ["c1", "c2"]
    assert ranked_a[0].score == ranked_b[0].score
