"""
Comprehensive Unit Tests for EvoReasoner Proof-Chain Aggregation & ContextAssembler Integration (T2.6).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Covers:
1. Proof-chain schemas and validation (tests 1-8).
2. Multi-path proof aggregation (tests 9-16).
3. ContextAssembler integration (tests 17-24).
4. End-to-end query pipeline integration (tests 25-30).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.schemas.code_atom import RelationType
from apps.api.src.schemas.evoreasoner import (
    EvidenceEdge,
    EvidencePath,
    PathScoreBreakdown,
    ProofAggregationConfig,
    RoutePerspective,
)
from apps.api.src.services.context_engine.assembler import AssembledContext, ContextAssembler
from apps.api.src.services.context_engine.engine import ProjectContextEngine
from apps.api.src.services.context_engine.memotime import TemporalIntentType
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.evoreasoner.aggregator import ProofChainAggregator
from apps.api.src.services.evoreasoner.validator import ProofChainValidator
from apps.api.src.services.llm.base import GroundedAnswer


def _dt(days: int = 0) -> datetime:
    return datetime(2026, 1, 1, 12, 0, tzinfo=UTC) + timedelta(days=days)


def _create_mock_edge(
    subject: str,
    relation: str = "CALLS",
    object_id: str = "target",
    canonical_relation: RelationType = RelationType.CALLS,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    commit_sha: str | None = "c0ffee01",
    branch: str = "main",
    confidence: float = 0.95,
    is_uncertain: bool = False,
    has_conflict: bool = False,
    conflict_detail: str | None = None,
    is_exclusive: bool = False,
    is_inverse: bool = False,
    superseded_by_id: uuid.UUID | None = None,
) -> EvidenceEdge:
    return EvidenceEdge(
        triplet_id=uuid.uuid4(),
        subject_id=subject,
        relation=relation,
        canonical_relation=canonical_relation,
        object_id=object_id,
        valid_from=valid_from or _dt(0),
        valid_to=valid_to,
        observation_time=_dt(0),
        commit_sha=commit_sha,
        branch=branch,
        confidence_score=confidence,
        is_uncertain=is_uncertain,
        has_temporal_conflict=has_conflict,
        conflict_detail=conflict_detail,
        is_exclusive=is_exclusive,
        scope_key="default",
        is_inverse=is_inverse,
        superseded_by_id=superseded_by_id,
        provenance={"file": "src/core.py"},
    )


def _create_mock_path(
    edges: list[EvidenceEdge],
    repository_id: uuid.UUID,
    branch: str = "main",
    score: float = 0.85,
    perspective: RoutePerspective = RoutePerspective.STRUCTURAL,
) -> EvidencePath:
    source = edges[0].subject_id if edges else "src"
    target = edges[-1].object_id if edges else "dst"
    return EvidencePath(
        path_id=f"path_{uuid.uuid4().hex[:6]}",
        route_id="route_mock",
        route_perspective=perspective,
        source_entity=source,
        target_entity=target,
        edges=edges,
        repository_id=repository_id,
        branch=branch,
        path_score=score,
        score_breakdown=PathScoreBreakdown(
            evidence_confidence=0.90,
            relation_alignment=0.85,
            entity_continuity=1.0,
            temporal_compatibility=1.0,
            uncertainty_penalty=0.0,
            conflict_penalty=0.0,
            length_penalty=0.05,
            raw_score=score,
            final_score=score,
        ),
    )


def _create_mock_candidate(
    name: str = "UserService",
    content: str = "class UserService:\n    pass\n",
    score: float = 0.88,
    repo_id: uuid.UUID | None = None,
) -> RankedCandidate:
    cand = RetrievedCandidate(
        candidate_id=str(uuid.uuid4()),
        entity_type="SYMBOL",
        name=name,
        path=f"src/{name.lower()}.py",
        start_line=1,
        end_line=10,
        content=content,
        file_id=uuid.uuid4(),
        metadata={
            "repository_id": str(repo_id or uuid.uuid4()),
            "commit_sha": "abc12345",
            "is_current": True,
        },
    )
    return RankedCandidate(candidate=cand, score=score, matched_reasons=["exact_match"])


# =========================================================================
# 1. Proof-chain schemas and validation (Tests 1-8)
# =========================================================================


def test_1_valid_single_path_proof_chain():
    repo_id = uuid.uuid4()
    edge = _create_mock_edge("AuthService", "CALLS", "TokenManager")
    path = _create_mock_path([edge], repo_id)

    ok, reason, chain = ProofChainValidator.validate_and_convert_path(path, expected_repo_id=repo_id)

    assert ok is True
    assert reason is None
    assert chain is not None
    assert chain.source_entity == "AuthService"
    assert chain.target_entity == "TokenManager"
    assert len(chain.hops) == 1
    assert chain.hops[0].relation == "CALLS"
    assert chain.direction == "forward"
    assert chain.has_conflict is False
    assert chain.has_uncertain_evidence is False
    assert chain.proof_score == path.path_score


def test_2_multi_hop_entity_continuity():
    repo_id = uuid.uuid4()
    e1 = _create_mock_edge("NodeA", "CALLS", "NodeB")
    e2 = _create_mock_edge("NodeB", "IMPORTS", "NodeC")
    e3 = _create_mock_edge("NodeC", "EXTENDS", "NodeD", canonical_relation=RelationType.INHERITS)
    path = _create_mock_path([e1, e2, e3], repo_id)

    ok, reason, chain = ProofChainValidator.validate_and_convert_path(path, expected_repo_id=repo_id)

    assert ok is True
    assert chain is not None
    assert len(chain.hops) == 3
    assert chain.source_entity == "NodeA"
    assert chain.target_entity == "NodeD"
    assert chain.hops[0].target_entity == chain.hops[1].source_entity == "NodeB"
    assert chain.hops[1].target_entity == chain.hops[2].source_entity == "NodeC"


def test_3_disconnected_path_rejection():
    repo_id = uuid.uuid4()
    e1 = _create_mock_edge("NodeA", "CALLS", "NodeB")
    # Disconnected hop: starts at UnrelatedX instead of NodeB
    e2 = _create_mock_edge("UnrelatedX", "CALLS", "NodeC")
    path = _create_mock_path([e1, e2], repo_id)

    ok, reason, chain = ProofChainValidator.validate_and_convert_path(path, expected_repo_id=repo_id)

    assert ok is False
    assert "broken_entity_continuity" in reason
    assert chain is None


def test_4_direction_validation():
    repo_id = uuid.uuid4()
    # 1. Forward
    ef = _create_mock_edge("A", "CALLS", "B", is_inverse=False)
    _, _, chain_f = ProofChainValidator.validate_and_convert_path(_create_mock_path([ef], repo_id), repo_id)
    assert chain_f.direction == "forward"

    # 2. Inverse
    ei = _create_mock_edge("B", "CALLED_BY", "A", is_inverse=True)
    _, _, chain_i = ProofChainValidator.validate_and_convert_path(_create_mock_path([ei], repo_id), repo_id)
    assert chain_i.direction == "inverse"

    # 3. Bidirectional (mixed)
    e_mix1 = _create_mock_edge("A", "CALLS", "B", is_inverse=False)
    e_mix2 = _create_mock_edge("B", "DEFINED_BY", "C", is_inverse=True)
    _, _, chain_m = ProofChainValidator.validate_and_convert_path(_create_mock_path([e_mix1, e_mix2], repo_id), repo_id)
    assert chain_m.direction == "bidirectional"


def test_5_repository_and_branch_isolation():
    repo_a = uuid.uuid4()
    repo_b = uuid.uuid4()

    edge = _create_mock_edge("A", "CALLS", "B", branch="feature")
    path = _create_mock_path([edge], repository_id=repo_a, branch="feature")

    # Mismatch repository
    ok_repo, reason_repo, _ = ProofChainValidator.validate_and_convert_path(path, expected_repo_id=repo_b, expected_branch="feature")
    assert ok_repo is False
    assert "repository_mismatch" in reason_repo

    # Mismatch branch
    ok_branch, reason_branch, _ = ProofChainValidator.validate_and_convert_path(path, expected_repo_id=repo_a, expected_branch="main")
    assert ok_branch is False
    assert "branch_mismatch" in reason_branch


def test_6_temporal_validity_intersection():
    repo_id = uuid.uuid4()
    # e1 valid [t0 -> t10], e2 valid [t5 -> t15] -> intersection is [t5 -> t10]
    e1 = _create_mock_edge("A", "CALLS", "B", valid_from=_dt(0), valid_to=_dt(10))
    e2 = _create_mock_edge("B", "CALLS", "C", valid_from=_dt(5), valid_to=_dt(15))
    path = _create_mock_path([e1, e2], repo_id)

    ok, _, chain = ProofChainValidator.validate_and_convert_path(
        path, repo_id, temporal_intent=TemporalIntentType.INTERVAL
    )
    assert ok is True
    assert chain.valid_from == _dt(5)
    assert chain.valid_to == _dt(10)
    assert chain.has_conflict is False

    # Contradictory interval: e3 valid [t0 -> t3], e4 valid [t7 -> t10] -> intersection [t7 -> t3] (empty/contradictory)
    e3 = _create_mock_edge("X", "CALLS", "Y", valid_from=_dt(0), valid_to=_dt(3))
    e4 = _create_mock_edge("Y", "CALLS", "Z", valid_from=_dt(7), valid_to=_dt(10))
    path_contra = _create_mock_path([e3, e4], repo_id)

    ok_c, _, chain_c = ProofChainValidator.validate_and_convert_path(
        path_contra, repo_id, temporal_intent=TemporalIntentType.INTERVAL
    )
    assert ok_c is True
    assert chain_c.has_conflict is True
    assert any("contradictory_validity_interval" in r for r in chain_c.conflict_reasons)


def test_7_supersession_and_contradiction_handling():
    repo_id = uuid.uuid4()
    # Edge that was superseded
    sup_id = uuid.uuid4()
    edge = _create_mock_edge(
        "OldFunc", "RETURNS", "int",
        valid_from=_dt(0), valid_to=_dt(5),
        superseded_by_id=sup_id,
        has_conflict=True,
        conflict_detail="Superseded by string return type in c0ffee02",
    )
    path = _create_mock_path([edge], repo_id)

    ok, _, chain = ProofChainValidator.validate_and_convert_path(path, repo_id, temporal_intent=TemporalIntentType.HISTORICAL)
    assert ok is True
    assert chain.is_historical is True
    assert chain.has_conflict is True
    assert any("Superseded" in r for r in chain.conflict_reasons)


def test_8_provenance_preservation():
    repo_id = uuid.uuid4()
    edge = _create_mock_edge("ModuleA", "IMPORTS", "ModuleB", commit_sha="commit_9999")
    path = _create_mock_path([edge], repo_id)

    _, _, chain = ProofChainValidator.validate_and_convert_path(path, repo_id)
    assert "commit_9999" in chain.commit_shas
    assert edge.triplet_id in chain.supporting_triplet_ids
    assert path.path_id in chain.constituent_path_ids
    assert chain.hops[0].provenance.get("file") == "src/core.py"


# =========================================================================
# 2. Multi-path proof aggregation (Tests 9-16)
# =========================================================================


def test_9_equivalent_chain_deduplication():
    repo_id = uuid.uuid4()
    # Two separate paths asserting the same A -> CALLS -> B
    e1 = _create_mock_edge("ServiceA", "CALLS", "ServiceB", confidence=0.90)
    p1 = _create_mock_path([e1], repo_id, score=0.80)

    e2 = _create_mock_edge("ServiceA", "CALLS", "ServiceB", confidence=0.95)
    p2 = _create_mock_path([e2], repo_id, score=0.85)

    res = ProofChainAggregator.aggregate_paths([p1, p2], repository_id=repo_id)

    assert len(res.chains) == 1
    assert res.deduplicated_chains_count == 1
    best_chain = res.chains[0]
    # Includes both constituent path IDs
    assert p1.path_id in best_chain.constituent_path_ids
    assert p2.path_id in best_chain.constituent_path_ids
    # Corroboration bonus applied: base max(0.80, 0.85) + 0.05 bonus
    assert best_chain.proof_score >= 0.90


def test_10_complementary_path_aggregation():
    repo_id = uuid.uuid4()
    # Path 1: ServiceA -> ServiceB
    e1 = _create_mock_edge("ServiceA", "CALLS", "ServiceB", valid_from=_dt(0), valid_to=_dt(20))
    p1 = _create_mock_path([e1], repo_id, score=0.85)

    # Path 2: ServiceB -> DatabaseC
    e2 = _create_mock_edge("ServiceB", "CALLS", "DatabaseC", valid_from=_dt(5), valid_to=_dt(25))
    p2 = _create_mock_path([e2], repo_id, score=0.80)

    res = ProofChainAggregator.aggregate_paths([p1, p2], repository_id=repo_id)

    # Generated composite chain ServiceA -> DatabaseC
    endpoints = {(c.source_entity, c.target_entity) for c in res.chains}
    assert ("ServiceA", "DatabaseC") in endpoints
    comp_chain = next(c for c in res.chains if c.source_entity == "ServiceA" and c.target_entity == "DatabaseC")
    assert len(comp_chain.hops) == 2
    assert comp_chain.hops[0].target_entity == comp_chain.hops[1].source_entity == "ServiceB"
    assert comp_chain.valid_from == _dt(5)
    assert comp_chain.valid_to == _dt(20)


def test_11_preservation_of_distinct_explanations():
    repo_id = uuid.uuid4()
    # Route 1: A -> B -> C
    e1 = _create_mock_edge("CompA", "CALLS", "CompB")
    e2 = _create_mock_edge("CompB", "CALLS", "CompC")
    p1 = _create_mock_path([e1, e2], repo_id, score=0.90)

    # Route 2: A -> D -> C (distinct explanation)
    e3 = _create_mock_edge("CompA", "CALLS", "CompD")
    e4 = _create_mock_edge("CompD", "CALLS", "CompC")
    p2 = _create_mock_path([e3, e4], repo_id, score=0.88)

    res = ProofChainAggregator.aggregate_paths([p1, p2], repository_id=repo_id)

    # Both explanations must be preserved
    assert len(res.chains) == 2
    intermediates = [{h.target_entity for h in c.hops[:-1]} for c in res.chains]
    assert {"CompB"} in intermediates
    assert {"CompD"} in intermediates


def test_12_conflicting_evidence_handling():
    repo_id = uuid.uuid4()
    # Exclusive relation: ReturnType
    # Chain 1: get_id RETURNS int
    e1 = _create_mock_edge("get_id", "RETURNS", "int", canonical_relation=RelationType.DEFINES_RETURN_TYPE, is_exclusive=True)
    p1 = _create_mock_path([e1], repo_id, score=0.90)

    # Chain 2: get_id RETURNS str (conflict with e1)
    e2 = _create_mock_edge("get_id", "RETURNS", "str", canonical_relation=RelationType.DEFINES_RETURN_TYPE, is_exclusive=True)
    p2 = _create_mock_path([e2], repo_id, score=0.85)

    res = ProofChainAggregator.aggregate_paths([p1, p2], repository_id=repo_id)

    # Both must be preserved, none discarded
    assert len(res.chains) == 2
    for c in res.chains:
        assert c.has_conflict is True
        assert any("exclusive_relation_conflict" in r for r in c.conflict_reasons)
        # Conflict penalty applied (0.20 deduction)
        assert c.proof_score <= 0.70


def test_13_deterministic_ranking():
    repo_id = uuid.uuid4()
    p_high = _create_mock_path([_create_mock_edge("HighSrc", "CALLS", "HighDst")], repo_id, score=0.95)
    p_mid = _create_mock_path([_create_mock_edge("MidSrc", "CALLS", "MidDst")], repo_id, score=0.75)
    p_low = _create_mock_path([_create_mock_edge("LowSrc", "CALLS", "LowDst")], repo_id, score=0.50)

    # Supply in scrambled order
    res = ProofChainAggregator.aggregate_paths([p_low, p_high, p_mid], repository_id=repo_id)

    scores = [c.proof_score for c in res.chains]
    assert scores == sorted(scores, reverse=True)
    assert res.chains[0].source_entity == "HighSrc"


def test_14_bounded_aggregation():
    repo_id = uuid.uuid4()
    paths = [
        _create_mock_path([_create_mock_edge(f"Src_{i}", "CALLS", f"Dst_{i}")], repo_id, score=0.50 + i * 0.05)
        for i in range(10)
    ]
    cfg = ProofAggregationConfig(max_proof_chains=4)
    res = ProofChainAggregator.aggregate_paths(paths, repository_id=repo_id, config=cfg)

    assert len(res.chains) == 4
    assert res.chains[0].source_entity == "Src_9"


def test_15_empty_and_invalid_path_handling():
    repo_id = uuid.uuid4()
    # Empty
    res_empty = ProofChainAggregator.aggregate_paths([], repository_id=repo_id)
    assert len(res_empty.chains) == 0
    assert res_empty.rejected_paths_count == 0

    # Malformed (broken continuity)
    bad_edge1 = _create_mock_edge("A", "CALLS", "B")
    bad_edge2 = _create_mock_edge("X", "CALLS", "Y")
    bad_path = _create_mock_path([bad_edge1, bad_edge2], repo_id)

    res_bad = ProofChainAggregator.aggregate_paths([bad_path], repository_id=repo_id)
    assert len(res_bad.chains) == 0
    assert res_bad.rejected_paths_count == 1


def test_16_uncertain_evidence_preservation():
    repo_id = uuid.uuid4()
    edge = _create_mock_edge("GuessedFunc", "CALLS", "GuessedTarget", confidence=0.45, is_uncertain=True)
    path = _create_mock_path([edge], repo_id, score=0.80)

    res = ProofChainAggregator.aggregate_paths([path], repository_id=repo_id)
    assert len(res.chains) == 1
    chain = res.chains[0]
    assert chain.has_uncertain_evidence is True
    assert any("uncertain" in r for r in chain.uncertainty_reasons)
    # Uncertainty penalty applied (0.10 deduction)
    assert chain.proof_score == round(0.80 - 0.10, 4)
    assert "[UNCERTAIN]" in chain.explanation


# =========================================================================
# 3. ContextAssembler integration (Tests 17-24)
# =========================================================================


def test_17_proof_chain_inclusion_when_enabled():
    repo_id = uuid.uuid4()
    edge = _create_mock_edge("OrderService", "CALLS", "PaymentGateway")
    _, _, chain = ProofChainValidator.validate_and_convert_path(_create_mock_path([edge], repo_id), repo_id)

    cand = _create_mock_candidate("OrderService", repo_id=repo_id)
    assembled: AssembledContext = ContextAssembler.assemble_context(
        ranked_candidates=[cand],
        proof_chains=[chain],
    )

    assert assembled.proof_chain_count == 1
    assert len(assembled.proof_chains) == 1
    assert "## EVOREASONER GROUNDED PROOF CHAINS" in assembled.prompt_context
    assert "[PROOF CHAIN] OrderService -> PaymentGateway" in assembled.prompt_context
    assert any(e.get("type") == "proof_chain" for e in assembled.evidence_items)
    assert "PaymentGateway" in assembled.related_entities


def test_18_existing_behavior_when_disabled():
    repo_id = uuid.uuid4()
    cand = _create_mock_candidate("OrderService", repo_id=repo_id)

    # Calling assemble_context without proof_chains
    assembled: AssembledContext = ContextAssembler.assemble_context(
        ranked_candidates=[cand],
    )

    assert assembled.proof_chain_count == 0
    assert len(assembled.proof_chains) == 0
    assert "## EVOREASONER GROUNDED PROOF CHAINS" not in assembled.prompt_context
    assert "## REPOSITORY CODE EVIDENCE" not in assembled.prompt_context
    assert assembled.candidate_count == 1


def test_19_existing_context_contract_compatibility():
    cand = _create_mock_candidate("ContractCheck")
    assembled = ContextAssembler.assemble_context([cand])

    assert hasattr(assembled, "prompt_context")
    assert hasattr(assembled, "evidence_items")
    assert hasattr(assembled, "related_entities")
    assert hasattr(assembled, "total_characters")
    assert hasattr(assembled, "candidate_count")
    assert hasattr(assembled, "proof_chains")
    assert hasattr(assembled, "proof_chain_count")


def test_20_context_size_budget_enforcement():
    repo_id = uuid.uuid4()
    chains = []
    for i in range(10):
        edge = _create_mock_edge(f"SuperLongServiceName_{i}", "CALLS", f"VeryLongTargetEndpointName_{i}")
        _, _, ch = ProofChainValidator.validate_and_convert_path(_create_mock_path([edge], repo_id), repo_id)
        chains.append(ch)

    cands = [_create_mock_candidate(f"Cand_{i}", content="Content " * 100) for i in range(5)]

    # Tight token budget (e.g. 500 tokens = ~2000 chars)
    assembled = ContextAssembler.assemble_context(
        ranked_candidates=cands,
        max_tokens=500,
        proof_chains=chains,
    )

    # Proof chains are bounded and do not crowd out code candidates
    assert assembled.candidate_count >= 3
    assert assembled.proof_chain_count < len(chains)


def test_21_duplicate_evidence_handling():
    repo_id = uuid.uuid4()
    # Candidate for DatabasePool
    cand = _create_mock_candidate("DatabasePool", content="class DatabasePool:\n    def connect(self): pass\n")

    # Proof chain referring to DatabasePool
    edge = _create_mock_edge("AppServer", "CALLS", "DatabasePool")
    _, _, chain = ProofChainValidator.validate_and_convert_path(_create_mock_path([edge], repo_id), repo_id)

    assembled = ContextAssembler.assemble_context(
        ranked_candidates=[cand],
        proof_chains=[chain],
    )

    # DatabasePool is not duplicated as raw code inside proof chain
    proof_section = assembled.prompt_context.split("## REPOSITORY CODE EVIDENCE")[0]
    assert "class DatabasePool:" not in proof_section
    assert "### [PROOF CHAIN] AppServer -> DatabasePool" in proof_section


def test_22_correct_source_attribution():
    repo_id = uuid.uuid4()
    edge = _create_mock_edge("Worker", "CALLS", "JobQueue", commit_sha="abcdef12")
    _, _, chain = ProofChainValidator.validate_and_convert_path(_create_mock_path([edge], repo_id), repo_id)

    assembled = ContextAssembler.assemble_context([], proof_chains=[chain])

    proof_item = next(e for e in assembled.evidence_items if e.get("type") == "proof_chain")
    assert proof_item["source_entity"] == "Worker"
    assert proof_item["target_entity"] == "JobQueue"
    assert "abcdef12" in proof_item["commit_shas"]
    assert str(edge.triplet_id) in proof_item["supporting_triplet_ids"]


def test_23_historical_evidence_labelling():
    repo_id = uuid.uuid4()
    edge = _create_mock_edge("OldEngine", "CALLS", "DeprecatedStorage", valid_to=_dt(5))
    _, _, chain = ProofChainValidator.validate_and_convert_path(
        _create_mock_path([edge], repo_id), repo_id, temporal_intent=TemporalIntentType.HISTORICAL
    )

    assembled = ContextAssembler.assemble_context([], proof_chains=[chain])

    assert "Temporal Status: HISTORICAL" in assembled.prompt_context
    proof_item = assembled.evidence_items[0]
    assert proof_item["is_historical"] is True


def test_24_no_cross_repository_or_cross_branch_leakage():
    repo_a = uuid.uuid4()
    repo_b = uuid.uuid4()

    edge_leak = _create_mock_edge("LeakA", "CALLS", "LeakB", branch="dev")
    path_leak = _create_mock_path([edge_leak], repository_id=repo_b, branch="dev")

    # Aggregator with expected repo_a and main branch
    res = ProofChainAggregator.aggregate_paths([path_leak], repository_id=repo_a, branch="main")

    assert len(res.chains) == 0
    assert res.rejected_paths_count == 1


# =========================================================================
# 4. End-to-end query pipeline integration (Tests 25-30)
# =========================================================================


@pytest.mark.asyncio
async def test_25_end_to_end_current_query_with_grounded_proof_chain():
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="UserService invokes TokenManager for authentication.",
            confidence=0.92,
            evidence=[],
            related_entities=["UserService", "TokenManager"],
            debug_signals={},
        )
    )

    engine = ProjectContextEngine(llm_provider=mock_llm)

    # Mock DB session
    session = AsyncMock()

    # Create edge & path
    edge = _create_mock_edge("UserService", "CALLS", "TokenManager")
    path = _create_mock_path([edge], repo_id)

    # Patch retriever, ranker, and EvoBeamSearchEngine
    from unittest.mock import patch
    with (
        patch("apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_retriever,
        patch("apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates", new_callable=AsyncMock) as mock_expander,
        patch("apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_kr,
        patch("apps.api.src.services.evoreasoner.beam_search.EvoBeamSearchEngine.search_paths", new_callable=AsyncMock) as mock_beam,
    ):
        mock_retriever.return_value = [_create_mock_candidate("UserService", repo_id=repo_id).candidate]
        mock_expander.return_value = [_create_mock_candidate("UserService", repo_id=repo_id).candidate]
        mock_kr.return_value = ("", [])

        from apps.api.src.schemas.evoreasoner import PathSearchResult
        mock_beam.return_value = PathSearchResult(
            query_text="How does UserService authenticate?",
            temporal_intent=TemporalIntentType.CURRENT,
            repository_id=repo_id,
            branch="main",
            paths=[path],
            total_paths_explored=1,
        )

        answer = await engine.investigate(
            session=session,
            snapshot_id=snap_id,
            question="How does UserService authenticate?",
            repository_id=repo_id,
            enable_evoreasoner=True,
        )

        assert answer.debug_signals.get("evoreasoner_used") is True
        assert answer.debug_signals.get("proof_chains_count") == 1
        # Check LLM prompt context received proof chain
        call_kwargs = mock_llm.generate_grounded_answer.call_args.kwargs
        assert "## EVOREASONER GROUNDED PROOF CHAINS" in call_kwargs["project_context"]
        assert "UserService -> TokenManager" in call_kwargs["project_context"]


@pytest.mark.asyncio
async def test_26_end_to_end_historical_query_using_memotime():
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Historically, LegacyAuth was used.",
            confidence=0.88,
            evidence=[],
            related_entities=["LegacyAuth"],
            debug_signals={},
        )
    )

    engine = ProjectContextEngine(llm_provider=mock_llm)
    session = AsyncMock()

    edge = _create_mock_edge("UserService", "CALLS", "LegacyAuth", valid_to=_dt(10))
    path = _create_mock_path([edge], repo_id)

    from unittest.mock import patch
    with (
        patch("apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_retriever,
        patch("apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates", new_callable=AsyncMock) as mock_expander,
        patch("apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_kr,
        patch("apps.api.src.services.evoreasoner.beam_search.EvoBeamSearchEngine.search_paths", new_callable=AsyncMock) as mock_beam,
    ):
        mock_retriever.return_value = [_create_mock_candidate("UserService", repo_id=repo_id).candidate]
        mock_expander.return_value = [_create_mock_candidate("UserService", repo_id=repo_id).candidate]
        mock_kr.return_value = ("", [])

        from apps.api.src.schemas.evoreasoner import PathSearchResult
        mock_beam.return_value = PathSearchResult(
            query_text="What authentication did UserService use previously?",
            temporal_intent=TemporalIntentType.HISTORICAL,
            repository_id=repo_id,
            branch="main",
            paths=[path],
            total_paths_explored=1,
        )

        answer = await engine.investigate(
            session=session,
            snapshot_id=snap_id,
            question="What authentication did UserService use previously?",
            repository_id=repo_id,
            enable_evoreasoner=True,
            enable_memotime=True,
        )

        assert answer.debug_signals.get("evoreasoner_used") is True
        call_kwargs = mock_llm.generate_grounded_answer.call_args.kwargs
        assert "Temporal Status: HISTORICAL" in call_kwargs["project_context"]


@pytest.mark.asyncio
async def test_27_end_to_end_diff_query_across_two_commits():
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Diff between commits shows switch to ModernHandler.",
            confidence=0.90,
            evidence=[],
            related_entities=["ModernHandler"],
            debug_signals={},
        )
    )

    engine = ProjectContextEngine(llm_provider=mock_llm)
    session = AsyncMock()

    e1 = _create_mock_edge("Router", "CALLS", "OldHandler", commit_sha="commit_aaa", valid_to=_dt(5))
    e2 = _create_mock_edge("Router", "CALLS", "ModernHandler", commit_sha="commit_bbb", valid_from=_dt(5))
    p1 = _create_mock_path([e1], repo_id)
    p2 = _create_mock_path([e2], repo_id)

    from unittest.mock import patch
    with (
        patch("apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_retriever,
        patch("apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates", new_callable=AsyncMock) as mock_expander,
        patch("apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_kr,
        patch("apps.api.src.services.evoreasoner.beam_search.EvoBeamSearchEngine.search_paths", new_callable=AsyncMock) as mock_beam,
    ):
        mock_retriever.return_value = []
        mock_expander.return_value = []
        mock_kr.return_value = ("", [])

        from apps.api.src.schemas.evoreasoner import PathSearchResult
        mock_beam.return_value = PathSearchResult(
            query_text="What changed between commit_aaa and commit_bbb?",
            temporal_intent=TemporalIntentType.DIFF,
            repository_id=repo_id,
            branch="main",
            paths=[p1, p2],
            total_paths_explored=2,
        )

        answer = await engine.investigate(
            session=session,
            snapshot_id=snap_id,
            question="What changed between commit_aaa and commit_bbb?",
            repository_id=repo_id,
            enable_evoreasoner=True,
        )

        assert answer.debug_signals.get("evoreasoner_used") is True
        call_kwargs = mock_llm.generate_grounded_answer.call_args.kwargs
        context = call_kwargs["project_context"]
        assert "commit_a" in context
        assert "commit_b" in context


@pytest.mark.asyncio
async def test_28_end_to_end_evolution_query_using_supersession_history():
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Pipeline evolved from v1 to v2 to v3.",
            confidence=0.91,
            evidence=[],
            related_entities=["DataPipeline"],
            debug_signals={},
        )
    )

    engine = ProjectContextEngine(llm_provider=mock_llm)
    session = AsyncMock()

    # Multi-hop evolution path
    e1 = _create_mock_edge("DataPipeline", "EVOLVED_TO", "PipelineV2", commit_sha="sha_v1")
    e2 = _create_mock_edge("PipelineV2", "EVOLVED_TO", "PipelineV3", commit_sha="sha_v2")
    path = _create_mock_path([e1, e2], repo_id, perspective=RoutePerspective.TEMPORAL_LINEAGE)

    from unittest.mock import patch
    with (
        patch("apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_retriever,
        patch("apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates", new_callable=AsyncMock) as mock_expander,
        patch("apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_kr,
        patch("apps.api.src.services.evoreasoner.beam_search.EvoBeamSearchEngine.search_paths", new_callable=AsyncMock) as mock_beam,
    ):
        mock_retriever.return_value = []
        mock_expander.return_value = []
        mock_kr.return_value = ("", [])

        from apps.api.src.schemas.evoreasoner import PathSearchResult
        mock_beam.return_value = PathSearchResult(
            query_text="How did DataPipeline evolve over time?",
            temporal_intent=TemporalIntentType.EVOLUTION,
            repository_id=repo_id,
            branch="main",
            paths=[path],
            total_paths_explored=1,
        )

        answer = await engine.investigate(
            session=session,
            snapshot_id=snap_id,
            question="How did DataPipeline evolve over time?",
            repository_id=repo_id,
            enable_evoreasoner=True,
        )

        assert answer.debug_signals.get("evoreasoner_used") is True
        call_kwargs = mock_llm.generate_grounded_answer.call_args.kwargs
        assert "DataPipeline -> PipelineV3" in call_kwargs["project_context"]
        assert "sha_v1" in call_kwargs["project_context"]


@pytest.mark.asyncio
async def test_29_end_to_end_query_with_conflicting_evidence():
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Evidence contains conflicting return types.",
            confidence=0.70,
            evidence=[],
            related_entities=["calculate_tax"],
            debug_signals={},
        )
    )

    engine = ProjectContextEngine(llm_provider=mock_llm)
    session = AsyncMock()

    # Conflicting return types
    e1 = _create_mock_edge("calculate_tax", "RETURNS", "float", canonical_relation=RelationType.DEFINES_RETURN_TYPE, is_exclusive=True)
    e2 = _create_mock_edge("calculate_tax", "RETURNS", "Decimal", canonical_relation=RelationType.DEFINES_RETURN_TYPE, is_exclusive=True)
    p1 = _create_mock_path([e1], repo_id)
    p2 = _create_mock_path([e2], repo_id)

    from unittest.mock import patch
    with (
        patch("apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_retriever,
        patch("apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates", new_callable=AsyncMock) as mock_expander,
        patch("apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_kr,
        patch("apps.api.src.services.evoreasoner.beam_search.EvoBeamSearchEngine.search_paths", new_callable=AsyncMock) as mock_beam,
    ):
        mock_retriever.return_value = []
        mock_expander.return_value = []
        mock_kr.return_value = ("", [])

        from apps.api.src.schemas.evoreasoner import PathSearchResult
        mock_beam.return_value = PathSearchResult(
            query_text="What does calculate_tax return?",
            temporal_intent=TemporalIntentType.CURRENT,
            repository_id=repo_id,
            branch="main",
            paths=[p1, p2],
            total_paths_explored=2,
        )

        answer = await engine.investigate(
            session=session,
            snapshot_id=snap_id,
            question="What does calculate_tax return?",
            repository_id=repo_id,
            enable_evoreasoner=True,
        )

        assert answer.debug_signals.get("evoreasoner_used") is True
        call_kwargs = mock_llm.generate_grounded_answer.call_args.kwargs
        context = call_kwargs["project_context"]
        assert "Conflict Warning" in context


@pytest.mark.asyncio
async def test_30_end_to_end_query_without_sufficient_evidence():
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    mock_llm = MagicMock()
    mock_llm.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="I don't have sufficient evidence to answer.",
            confidence=0.10,
            evidence=[],
            related_entities=[],
            debug_signals={"is_abstention": True},
        )
    )

    engine = ProjectContextEngine(llm_provider=mock_llm)
    session = AsyncMock()

    from unittest.mock import patch
    with (
        patch("apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_retriever,
        patch("apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates", new_callable=AsyncMock) as mock_expander,
        patch("apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_kr,
        patch("apps.api.src.services.evoreasoner.beam_search.EvoBeamSearchEngine.search_paths", new_callable=AsyncMock) as mock_beam,
    ):
        mock_retriever.return_value = []
        mock_expander.return_value = []
        mock_kr.return_value = ("", [])

        from apps.api.src.schemas.evoreasoner import PathSearchResult
        mock_beam.return_value = PathSearchResult(
            query_text="NonExistentQuery",
            temporal_intent=TemporalIntentType.CURRENT,
            repository_id=repo_id,
            branch="main",
            paths=[],
            total_paths_explored=0,
        )

        answer = await engine.investigate(
            session=session,
            snapshot_id=snap_id,
            question="NonExistentQuery",
            repository_id=repo_id,
            enable_evoreasoner=True,
        )

        assert answer.debug_signals.get("evoreasoner_used") is False
        assert answer.debug_signals.get("proof_chains_count") == 0
        call_kwargs = mock_llm.generate_grounded_answer.call_args.kwargs
        assert "No specific code evidence retrieved" in call_kwargs["project_context"]
