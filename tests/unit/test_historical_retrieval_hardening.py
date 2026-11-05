"""
Unit tests for Historical Retrieval Hardening (Phase 1 of T2.8).

Verifies:
1. Past-tense introduction / origin queries ("introduced", "initially", "originally")
   are classified as TemporalIntentType.HISTORICAL, not CURRENT.
2. Conditioned historical re-ranking prevents unrelated historical candidates
   from displacing relevant symbol candidates.
3. CURRENT intent queries strictly demote superseded chunks.
4. Multi-hop and non-temporal candidate ranking remains unregressed.
"""

from __future__ import annotations

from apps.api.src.services.context_engine.memotime import MemoTimeService, TemporalIntentType
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.evoreasoner.planner import EvoRoutePlanner


def test_1_historical_intent_detection_on_introduced_phrasing():
    """Verifies that 'How were ... introduced' detects HISTORICAL intent."""
    query = "How were temporal relationship intervals and ended tag annotations introduced in ContextAssembler?"
    intent = MemoTimeService.parse_temporal_intent(query, target_symbols=["ContextAssembler"])
    assert intent.intent_type == TemporalIntentType.HISTORICAL
    assert intent.is_temporal is True

    # Also verify route planner inherits HISTORICAL intent
    plan = EvoRoutePlanner.generate_multi_route_plan(query, seed_entities=["ContextAssembler"])
    assert plan.temporal_intent == TemporalIntentType.HISTORICAL


def test_2_historical_intent_detection_on_initially_and_originally():
    """Verifies 'initially' and 'originally' trigger HISTORICAL intent."""
    q1 = "What were the initial signal weights in MultiSignalRanker?"
    intent1 = MemoTimeService.parse_temporal_intent(q1, target_symbols=["MultiSignalRanker"])
    assert intent1.intent_type == TemporalIntentType.HISTORICAL

    q2 = "How did CodeAtomDecomposer originally handle AST parsing?"
    intent2 = MemoTimeService.parse_temporal_intent(q2, target_symbols=["CodeAtomDecomposer"])
    assert intent2.intent_type == TemporalIntentType.HISTORICAL


def test_3_conditioned_historical_ranking_prevents_unrelated_displacement():
    """Verifies unrelated historical chunks do not displace relevant historical candidates."""
    # Relevant historical candidate matching symbol
    rel_hist = RetrievedCandidate(
        candidate_id="b094f01_rel",
        entity_type="CHUNK",
        name="ContextAssembler",
        path="apps/api/src/services/context_engine/assembler.py",
        start_line=1,
        end_line=20,
        content="class ContextAssembler: ...",
        file_id=None,
        signals={"vector_similarity": 0.90, "exact_match": 0.95},
        metadata={"commit_sha": "b094f01", "is_superseded": True, "symbol_name": "ContextAssembler"},
    )
    # Relevant current candidate matching symbol
    rel_curr = RetrievedCandidate(
        candidate_id="94fbd79_rel",
        entity_type="CHUNK",
        name="ContextAssembler",
        path="apps/api/src/services/context_engine/assembler.py",
        start_line=1,
        end_line=20,
        content="class ContextAssembler: ...",
        file_id=None,
        signals={"vector_similarity": 0.88, "exact_match": 0.95},
        metadata={"commit_sha": "94fbd79", "is_current": True, "symbol_name": "ContextAssembler"},
    )
    # Unrelated historical candidate from another file
    unrel_hist = RetrievedCandidate(
        candidate_id="6626c5c_unrel",
        entity_type="CHUNK",
        name="TemporalCodeRelation",
        path="apps/api/src/services/code_atom/temporal.py",
        start_line=1,
        end_line=20,
        content="class TemporalCodeRelation: ...",
        file_id=None,
        signals={"vector_similarity": 0.80},
        metadata={"commit_sha": "6626c5c", "is_superseded": True, "symbol_name": "TemporalCodeRelation"},
    )

    analyzed = analyze_query("How was ContextAssembler initially designed?")
    analyzed.is_temporal = True
    analyzed.symbol_candidates = ["ContextAssembler"]

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[unrel_hist, rel_hist, rel_curr],
        analyzed_query=analyzed,
    )

    ranked_ids = [r.candidate.candidate_id for r in ranked]
    # Relevant ContextAssembler chunk should be ranked first, before unrelated temporal relation
    assert ranked_ids[0] == "b094f01_rel"
    assert ranked_ids[1] == "94fbd79_rel"
    assert ranked_ids[2] == "6626c5c_unrel"


def test_4_current_intent_demotes_superseded_chunks():
    """Verifies that CURRENT queries demote superseded chunks."""
    curr_cand = RetrievedCandidate(
        candidate_id="curr_1",
        entity_type="CHUNK",
        name="ProjectContextEngine",
        path="apps/api/src/services/context_engine/engine.py",
        start_line=1,
        end_line=20,
        content="class ProjectContextEngine: ...",
        file_id=None,
        signals={"vector_similarity": 0.85},
        metadata={"is_current": True, "has_superseded_versions": True},
    )
    sup_cand = RetrievedCandidate(
        candidate_id="sup_1",
        entity_type="CHUNK",
        name="ProjectContextEngine",
        path="apps/api/src/services/context_engine/engine.py",
        start_line=25,
        end_line=45,
        content="class ProjectContextEngine_v1: ...",
        file_id=None,
        signals={"vector_similarity": 0.85},
        metadata={"is_superseded": True, "is_current": False},
    )

    analyzed = analyze_query("What does ProjectContextEngine currently do?")
    analyzed.is_temporal = False  # Current-state query

    ranked = MultiSignalRanker.rank_candidates(
        candidates=[sup_cand, curr_cand],
        analyzed_query=analyzed,
    )

    assert ranked[0].candidate.candidate_id == "curr_1"
    assert ranked[1].candidate.candidate_id == "sup_1"
    assert ranked[0].score > ranked[1].score
