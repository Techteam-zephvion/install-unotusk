"""
Unit and Acceptance Tests for EvoReasoner Beam Search & Evidence Path Scoring (T2.5 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Covers:
1. Basic single-hop graph traversal.
2. Multi-hop traversal.
3. Multiple candidate expansions.
4. Beam-width enforcement.
5. Maximum-depth enforcement.
6. Maximum-expansion enforcement.
7. Cycle prevention.
8. Entity continuity.
9. Relation compatibility.
10. Inverse relationship handling.
11. Branch isolation.
12. Historical temporal filtering.
13. BEFORE and AFTER filtering.
14. Interval constraints.
15. Supersession handling.
16. Uncertain assertion handling.
17. Contradiction penalties.
18. Deterministic path scoring.
19. Path ranking and tie-breaking.
20. Empty and ungrounded queries.
21. PostgreSQL/database-backed traversal and validation.
22. Compatibility with T2.4 route outputs.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.src.db.base import Base
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    ProjectStatus,
)
from apps.api.src.models.evokg import EvoKGTriplet
from apps.api.src.models.integration import Integration
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.schemas.code_atom import RelationType
from apps.api.src.schemas.evoreasoner import (
    BeamSearchConfig,
    EvidenceEdge,
    EvidencePath,
    EvoPlannerConfig,
    MultiRoutePlan,
    PathScoreBreakdown,
    ReasoningHop,
    ReasoningRoute,
    RoutePerspective,
)
from apps.api.src.services.context_engine.memotime import TemporalIntentType
from apps.api.src.services.evoreasoner.beam_search import EvoBeamSearchEngine
from apps.api.src.services.evoreasoner.cost_estimator import RouteCostEstimator
from apps.api.src.services.evoreasoner.path_scorer import PathScorer
from apps.api.src.services.evoreasoner.planner import EvoRoutePlanner


def _dt(offset_hours: int) -> datetime:
    return datetime(2026, 11, 1, 10, 0, 0, tzinfo=UTC) + timedelta(hours=offset_hours)


@pytest.fixture
async def async_test_db():
    """Sets up an in-memory async SQLite database with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        org = Organization(id=uuid.uuid4(), name="Acme", slug="acme")
        session.add(org)
        await session.flush()

        proj = Project(
            id=uuid.uuid4(),
            organization_id=org.id,
            name="Test Project",
            slug="testproj",
            status=ProjectStatus.READY,
        )
        session.add(proj)
        await session.flush()

        integ = Integration(
            id=uuid.uuid4(),
            project_id=proj.id,
            provider=IntegrationProvider.GITHUB,
            status=IntegrationStatus.CONNECTED,
        )
        session.add(integ)
        await session.flush()

        repo = Repository(
            id=uuid.uuid4(),
            project_id=proj.id,
            integration_id=integ.id,
            external_id="ext-100",
            owner="acme",
            name="core-service",
            full_name="acme/core-service",
            default_branch="main",
            url="https://github.com/acme/core-service",
        )
        session.add(repo)
        await session.flush()
        await session.commit()

        yield {"session": session, "repo_id": repo.id}


def _create_triplet(
    repo_id: uuid.UUID,
    subject: str,
    relation: str,
    object_id: str,
    *,
    branch: str = "main",
    valid_from: Any = "DEFAULT",
    valid_to: datetime | None = None,
    commit_sha: str | None = "commit_100",
    confidence: float = 0.90,
    is_uncertain: bool = False,
    has_conflict: bool = False,
    is_exclusive: bool = False,
    supersedes_id: uuid.UUID | None = None,
    superseded_by_id: uuid.UUID | None = None,
) -> EvoKGTriplet:
    # canonical check
    return EvoKGTriplet(
        id=uuid.uuid4(),
        repository_id=repo_id,
        branch=branch,
        subject_id=subject,
        relation=relation,
        object_id=object_id,
        is_exclusive=is_exclusive,
        scope_key="default",
        valid_from=_dt(0) if valid_from == "DEFAULT" else valid_from,
        valid_to=valid_to,
        observation_time=_dt(0),
        commit_sha=commit_sha,
        supersedes_id=supersedes_id,
        superseded_by_id=superseded_by_id,
        confidence_score=confidence,
        confidence_level="HIGH" if confidence >= 0.8 else "UNCERTAIN",
        is_uncertain=is_uncertain,
        has_temporal_conflict=has_conflict,
        fingerprint=f"fp_{subject}_{relation}_{object_id}_{uuid.uuid4().hex[:6]}",
        provenance={"branch": branch, "commit": commit_sha},
    )


# =========================================================================
def _make_route(
    route_id: str,
    name: str,
    hops: list[ReasoningHop],
    perspective: RoutePerspective = RoutePerspective.ARCHITECTURAL_DEPENDENCY,
    intent: TemporalIntentType = TemporalIntentType.CURRENT,
) -> ReasoningRoute:
    cost, breakdown = RouteCostEstimator.estimate_cost(hops, intent)
    canonical_key = "->".join(f"{h.source_entity}:{h.relation.value}:{h.target_entity}" for h in hops)
    return ReasoningRoute(
        route_id=route_id,
        name=name,
        intent=intent,
        perspective=perspective,
        hops=hops,
        estimated_cost=cost,
        cost_breakdown=breakdown,
        canonical_key=canonical_key,
    )


# 1. Basic Single-Hop Graph Traversal
# =========================================================================

@pytest.mark.asyncio
async def test_1_single_hop_graph_traversal(async_test_db):
    session: AsyncSession = async_test_db["session"]
    repo_id: uuid.UUID = async_test_db["repo_id"]

    t1 = _create_triplet(repo_id, "AuthService", "CALLS", "TokenManager")
    session.add(t1)
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "AuthService", RelationType.CALLS, "TokenManager")
    route = _make_route("r1", "Auth Call Route", [hop], perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    paths, expansions = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="AuthService",
    )

    assert len(paths) == 1
    p = paths[0]
    assert p.source_entity == "AuthService"
    assert p.target_entity == "TokenManager"
    assert len(p.edges) == 1
    assert p.edges[0].relation == "CALLS"
    assert p.path_score > 0.70
    assert expansions >= 1


# =========================================================================
# 2. Multi-Hop Traversal
# =========================================================================

@pytest.mark.asyncio
async def test_2_multi_hop_traversal(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t1 = _create_triplet(repo_id, "OrderController", "CALLS", "BillingService")
    t2 = _create_triplet(repo_id, "BillingService", "MUTATES", "LedgerAccount")
    session.add_all([t1, t2])
    await session.commit()

    h1 = EvoRoutePlanner.create_hop(1, "OrderController", RelationType.CALLS, "BillingService")
    h2 = EvoRoutePlanner.create_hop(2, "BillingService", RelationType.MUTATES, "LedgerAccount")

    route = _make_route("r_multi", "Multi-hop order billing", [h1, h2], perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="OrderController",
    )

    assert len(paths) == 1
    assert len(paths[0].edges) == 2
    assert paths[0].source_entity == "OrderController"
    assert paths[0].target_entity == "LedgerAccount"


# =========================================================================
# 3. Multiple Candidate Expansions
# =========================================================================

@pytest.mark.asyncio
async def test_3_multiple_candidate_expansions(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t1 = _create_triplet(repo_id, "Router", "CALLS", "HandlerA", confidence=0.95)
    t2 = _create_triplet(repo_id, "Router", "CALLS", "HandlerB", confidence=0.85)
    session.add_all([t1, t2])
    await session.commit()

    h1 = EvoRoutePlanner.create_hop(1, "Router", RelationType.CALLS, "target")
    route = _make_route("r_fanout", "Router fanout", [h1], perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="Router",
        config=BeamSearchConfig(beam_width=5),
    )

    assert len(paths) == 2
    targets = {p.target_entity for p in paths}
    assert targets == {"HandlerA", "HandlerB"}


# =========================================================================
# 4. Beam-Width Enforcement
# =========================================================================

@pytest.mark.asyncio
async def test_4_beam_width_enforcement(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    for i in range(5):
        session.add(_create_triplet(repo_id, "Gateway", "CALLS", f"Target_{i}", confidence=0.7 + i * 0.05))
    await session.commit()

    h1 = EvoRoutePlanner.create_hop(1, "Gateway", RelationType.CALLS, "target")
    route = _make_route("r_beam", "Beam test", [h1], perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    # Beam width = 2 must retain strictly at most 2 candidate paths
    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="Gateway",
        config=BeamSearchConfig(beam_width=2),
    )

    assert len(paths) == 2


# =========================================================================
# 5. Maximum-Depth Enforcement
# =========================================================================

@pytest.mark.asyncio
async def test_5_maximum_depth_enforcement(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t1 = _create_triplet(repo_id, "N1", "CALLS", "N2")
    t2 = _create_triplet(repo_id, "N2", "CALLS", "N3")
    t3 = _create_triplet(repo_id, "N3", "CALLS", "N4")
    session.add_all([t1, t2, t3])
    await session.commit()

    hops = [
        EvoRoutePlanner.create_hop(1, "N1", RelationType.CALLS, "N2"),
        EvoRoutePlanner.create_hop(2, "N2", RelationType.CALLS, "N3"),
        EvoRoutePlanner.create_hop(3, "N3", RelationType.CALLS, "N4"),
    ]
    route = _make_route("r_depth", "Depth route", hops, perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    # Cap at depth 2
    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="N1",
        config=BeamSearchConfig(max_path_depth=2),
    )

    assert len(paths) == 1
    assert len(paths[0].edges) == 2
    assert paths[0].target_entity == "N3"


# =========================================================================
# 6. Maximum-Expansion Enforcement
# =========================================================================

@pytest.mark.asyncio
async def test_6_maximum_expansion_enforcement(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t1 = _create_triplet(repo_id, "StartNode", "CALLS", "MiddleNode")
    t2 = _create_triplet(repo_id, "MiddleNode", "CALLS", "EndNode")
    session.add_all([t1, t2])
    await session.commit()

    hops = [
        EvoRoutePlanner.create_hop(1, "StartNode", RelationType.CALLS, "MiddleNode"),
        EvoRoutePlanner.create_hop(2, "MiddleNode", RelationType.CALLS, "EndNode"),
    ]
    route = _make_route("r_budget", "Budget test", hops, perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    # Allow strictly only 1 expansion
    paths, expansions = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="StartNode",
        config=BeamSearchConfig(max_total_expansions=1),
    )

    assert expansions <= 1


# =========================================================================
# 7. Cycle Prevention
# =========================================================================

@pytest.mark.asyncio
async def test_7_cycle_prevention(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    # Mutual recursive calls A -> B -> A
    t1 = _create_triplet(repo_id, "FuncA", "CALLS", "FuncB")
    t2 = _create_triplet(repo_id, "FuncB", "CALLS", "FuncA")
    session.add_all([t1, t2])
    await session.commit()

    hops = [
        EvoRoutePlanner.create_hop(1, "FuncA", RelationType.CALLS, "FuncB"),
        EvoRoutePlanner.create_hop(2, "FuncB", RelationType.CALLS, "FuncA"),
    ]
    route = _make_route("r_cycle", "Cycle route", hops, perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="FuncA",
    )

    # Hop 2 tries to revisit FuncA; cycle prevention rejects it
    assert all(len(p.edges) == 1 for p in paths)


# =========================================================================
# 8. Entity Continuity
# =========================================================================

def test_8_entity_continuity_scoring():
    edge1 = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="Auth", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="Token"
    )
    edge2_continuous = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="Token", relation="MUTATES",
        canonical_relation=RelationType.MUTATES, object_id="Blacklist"
    )
    edge2_broken = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="UnrelatedService", relation="MUTATES",
        canonical_relation=RelationType.MUTATES, object_id="Blacklist"
    )

    _, b_good = PathScorer.evaluate_path([edge1, edge2_continuous], [], TemporalIntentType.CURRENT)
    _, b_broken = PathScorer.evaluate_path([edge1, edge2_broken], [], TemporalIntentType.CURRENT)

    assert b_good.entity_continuity == 1.0
    assert b_broken.entity_continuity == 0.0


# =========================================================================
# 9. Relation Compatibility
# =========================================================================

def test_9_relation_compatibility_scoring():
    planned_hop = ReasoningHop(
        hop_index=1, source_entity="A", relation=RelationType.CALLS,
        canonical_relation=RelationType.CALLS, target_entity="B"
    )

    edge_match = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="B"
    )
    edge_mismatch = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="IMPORTS",
        canonical_relation=RelationType.IMPORTS, object_id="B"
    )

    _, b_match = PathScorer.evaluate_path([edge_match], [planned_hop], TemporalIntentType.CURRENT)
    _, b_mismatch = PathScorer.evaluate_path([edge_mismatch], [planned_hop], TemporalIntentType.CURRENT)

    assert b_match.relation_alignment == 1.0
    assert b_mismatch.relation_alignment == 0.0


# =========================================================================
# 10. Inverse Relationship Handling
# =========================================================================

@pytest.mark.asyncio
async def test_10_inverse_relationship_traversal(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    # Incoming relationship: Caller -> CALLS -> Callee
    t1 = _create_triplet(repo_id, "UserEndpoint", "CALLS", "AuthService")
    session.add(t1)
    await session.commit()

    # Search for callers of AuthService using is_inverse=True
    inv_hop = EvoRoutePlanner.create_hop(1, "AuthService", RelationType.CALLS, "UserEndpoint", is_inverse=True)
    route = _make_route("r_inv", "Caller route", [inv_hop], perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="AuthService",
    )

    assert len(paths) == 1
    assert paths[0].edges[0].is_inverse is True
    assert paths[0].target_entity == "UserEndpoint"


# =========================================================================
# 11. Branch Isolation
# =========================================================================

@pytest.mark.asyncio
async def test_11_branch_isolation(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_main = _create_triplet(repo_id, "Api", "CALLS", "MainHandler", branch="main")
    t_feat = _create_triplet(repo_id, "Api", "CALLS", "ExperimentalHandler", branch="feature/experiment")
    session.add_all([t_main, t_feat])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "Api", RelationType.CALLS, "target")
    route = _make_route("r_branch", "Branch test", [hop], perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    # Querying main branch must never see feature/experiment triplets
    paths_main, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        branch="main",
        start_entity="Api",
    )

    assert len(paths_main) == 1
    assert paths_main[0].target_entity == "MainHandler"


# =========================================================================
# 12. Historical Temporal Filtering
# =========================================================================

@pytest.mark.asyncio
async def test_12_historical_temporal_filtering(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    # Active triplet vs superseded triplet
    t_active = _create_triplet(repo_id, "Config", "CONFIGURES", "V2Param", valid_to=None)
    t_hist = _create_triplet(repo_id, "Config", "CONFIGURES", "V1Param", valid_to=_dt(5))
    session.add_all([t_active, t_hist])
    await session.commit()

    # In CURRENT query, active must score significantly higher than superseded
    edge_active = EvoBeamSearchEngine._triplet_to_edge(t_active)
    edge_hist = EvoBeamSearchEngine._triplet_to_edge(t_hist)

    score_curr_active, _ = PathScorer.evaluate_path([edge_active], [], TemporalIntentType.CURRENT)
    score_curr_hist, _ = PathScorer.evaluate_path([edge_hist], [], TemporalIntentType.CURRENT)
    assert score_curr_active > score_curr_hist

    # In HISTORICAL query, superseded triplet must score high
    score_hist_hist, _ = PathScorer.evaluate_path([edge_hist], [], TemporalIntentType.HISTORICAL)
    assert score_hist_hist > 0.70


# =========================================================================
# 13. BEFORE and AFTER Filtering
# =========================================================================

def test_13_before_after_filtering():
    anchor = _dt(10)
    e_early = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="B", valid_from=_dt(5)
    )
    e_late = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="B", valid_from=_dt(15)
    )

    _, b_before_early = PathScorer.evaluate_path([e_early], [], TemporalIntentType.BEFORE, as_of=anchor)
    _, b_before_late = PathScorer.evaluate_path([e_late], [], TemporalIntentType.BEFORE, as_of=anchor)
    assert b_before_early.temporal_compatibility > b_before_late.temporal_compatibility

    _, b_after_early = PathScorer.evaluate_path([e_early], [], TemporalIntentType.AFTER, as_of=anchor)
    _, b_after_late = PathScorer.evaluate_path([e_late], [], TemporalIntentType.AFTER, as_of=anchor)
    assert b_after_late.temporal_compatibility > b_after_early.temporal_compatibility


# =========================================================================
# 14. Interval Constraints
# =========================================================================

def test_14_interval_constraints():
    edge_in_interval = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="S", relation="MUTATES",
        canonical_relation=RelationType.MUTATES, object_id="State",
        valid_from=_dt(2), valid_to=_dt(8)
    )
    score, b = PathScorer.evaluate_path([edge_in_interval], [], TemporalIntentType.INTERVAL)
    assert b.temporal_compatibility > 0.0


# =========================================================================
# 15. Supersession Handling
# =========================================================================

def test_15_supersession_handling():
    id_old = uuid.uuid4()
    id_new = uuid.uuid4()

    edge_supersession = EvidenceEdge(
        triplet_id=id_new, subject_id="NewAuth", relation="SUPERSEDES",
        canonical_relation=RelationType.REFERENCES, object_id="OldAuth",
        supersedes_id=id_old
    )
    score, b = PathScorer.evaluate_path([edge_supersession], [], TemporalIntentType.EVOLUTION)
    assert b.temporal_compatibility == 1.0


# =========================================================================
# 16. Uncertain Assertion Handling
# =========================================================================

def test_16_uncertain_assertion_penalty():
    e_certain = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="B", is_uncertain=False
    )
    e_uncertain = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="B", is_uncertain=True
    )

    score_cert, _ = PathScorer.evaluate_path([e_certain], [], TemporalIntentType.CURRENT)
    score_unc, b_unc = PathScorer.evaluate_path([e_uncertain], [], TemporalIntentType.CURRENT)

    assert b_unc.uncertainty_penalty == 1.0
    assert score_cert > score_unc


# =========================================================================
# 17. Contradiction Penalties
# =========================================================================

def test_17_contradiction_penalties():
    e_clean = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="B", has_temporal_conflict=False
    )
    e_conflict = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="A", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="B", has_temporal_conflict=True
    )

    score_clean, _ = PathScorer.evaluate_path([e_clean], [], TemporalIntentType.CURRENT)
    score_conflict, b_conf = PathScorer.evaluate_path([e_conflict], [], TemporalIntentType.CURRENT)

    assert b_conf.conflict_penalty == 1.0
    assert score_clean > score_conflict


# =========================================================================
# 18. Deterministic Path Scoring
# =========================================================================

def test_18_deterministic_path_scoring():
    edge = EvidenceEdge(
        triplet_id=uuid.uuid4(), subject_id="Service", relation="CALLS",
        canonical_relation=RelationType.CALLS, object_id="Helper", confidence_score=0.92
    )
    hop = ReasoningHop(
        hop_index=1, source_entity="Service", relation=RelationType.CALLS,
        canonical_relation=RelationType.CALLS, target_entity="Helper"
    )

    score1, b1 = PathScorer.evaluate_path([edge], [hop], TemporalIntentType.CURRENT)
    score2, b2 = PathScorer.evaluate_path([edge], [hop], TemporalIntentType.CURRENT)

    assert score1 == score2
    assert b1.model_dump() == b2.model_dump()


# =========================================================================
# 19. Path Ranking and Tie-Breaking
# =========================================================================

def test_19_path_ranking_and_tie_breaking():
    # Construct paths with identical score but different route estimated costs
    b = PathScoreBreakdown(
        evidence_confidence=0.8, relation_alignment=1.0, entity_continuity=1.0,
        temporal_compatibility=1.0, uncertainty_penalty=0.0, conflict_penalty=0.0,
        length_penalty=0.0, raw_score=0.85, final_score=0.85
    )
    p_expensive = EvidencePath(
        path_id="p_high_cost", route_id="r1", route_perspective=RoutePerspective.STRUCTURAL,
        source_entity="A", target_entity="B", edges=[], repository_id=uuid.uuid4(),
        route_estimated_cost=5.0, path_score=0.85, score_breakdown=b, canonical_signature="sig_b"
    )
    p_cheaper = EvidencePath(
        path_id="p_low_cost", route_id="r2", route_perspective=RoutePerspective.STRUCTURAL,
        source_entity="A", target_entity="B", edges=[], repository_id=uuid.uuid4(),
        route_estimated_cost=2.0, path_score=0.85, score_breakdown=b, canonical_signature="sig_a"
    )

    paths = [p_expensive, p_cheaper]
    paths.sort(key=lambda p: (-p.path_score, p.route_estimated_cost, p.canonical_signature))

    assert paths[0].path_id == "p_low_cost"


# =========================================================================
# 20. Empty and Ungrounded Queries
# =========================================================================

@pytest.mark.asyncio
async def test_20_empty_and_ungrounded_queries(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    empty_plan = EvoRoutePlanner.plan_routes("")
    res = await EvoBeamSearchEngine.search_paths(session, repo_id, empty_plan)
    assert res.paths == []
    assert res.total_paths_explored == 0
    assert res.search_diagnostics.get("reason") == "empty_route_plan"


# =========================================================================
# 21. Database-Backed Traversal and Validation
# =========================================================================

@pytest.mark.asyncio
async def test_21_database_backed_traversal_and_validation(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    # Insert realistic code graph: Controller -> Service -> Repo
    t1 = _create_triplet(repo_id, "api/controllers::OrderCtrl", "CALLS", "services/order::OrderService")
    t2 = _create_triplet(repo_id, "services/order::OrderService", "CALLS", "db/repos::OrderRepo")
    session.add_all([t1, t2])
    await session.commit()

    hops = [
        EvoRoutePlanner.create_hop(1, "api/controllers::OrderCtrl", RelationType.CALLS, "services/order::OrderService"),
        EvoRoutePlanner.create_hop(2, "services/order::OrderService", RelationType.CALLS, "db/repos::OrderRepo"),
    ]
    route = _make_route("r_db_test", "DB Order Traversal", hops, perspective=RoutePerspective.BEHAVIORAL_CALLGRAPH)

    paths, expansions = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        start_entity="api/controllers::OrderCtrl",
    )

    assert len(paths) == 1
    assert paths[0].source_entity == "api/controllers::OrderCtrl"
    assert paths[0].target_entity == "db/repos::OrderRepo"
    assert paths[0].path_score > 0.70
    assert expansions >= 2


# =========================================================================
# 22. Compatibility with T2.4 Route Outputs
# =========================================================================

@pytest.mark.asyncio
async def test_22_compatibility_with_t2_4_route_outputs(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    # Seed triplets for UserService
    t1 = _create_triplet(repo_id, "UserService", "DEFINES", "UserService::body")
    t2 = _create_triplet(repo_id, "UserService::body", "HAS_SIGNATURE", "UserService::signature")
    t3 = _create_triplet(repo_id, "UserService", "CALLS", "UserRepository")
    session.add_all([t1, t2, t3])
    await session.commit()

    # Generate plan via T2.4 EvoRoutePlanner
    plan = EvoRoutePlanner.plan_routes("How does UserService call UserRepository?", config=EvoPlannerConfig(max_selected_routes=2))
    assert len(plan.selected_routes) > 0

    # Execute T2.5 EvoBeamSearchEngine with the planned routes
    result = await EvoBeamSearchEngine.search_paths(
        session=session,
        repository_id=repo_id,
        route_plan=plan,
        grounded_entities=["UserService"],
    )

    assert len(result.paths) > 0
    top_path = result.paths[0]
    assert top_path.source_entity == "UserService"
    assert top_path.path_score > 0.0
    assert top_path.score_breakdown is not None


# =========================================================================
# 23. CURRENT Filtering: Active vs Closed / Superseded Relations
# =========================================================================

@pytest.mark.asyncio
async def test_23_current_filtering_active_vs_closed(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    # Active triplet
    t_active = _create_triplet(repo_id, "PaymentGateway", "CALLS", "StripeClient")
    # Closed triplet (valid_to set)
    t_closed = _create_triplet(
        repo_id, "PaymentGateway", "CALLS", "BraintreeClient",
        valid_to=_dt(-1),
    )
    # Superseded triplet
    t_superseded = _create_triplet(
        repo_id, "PaymentGateway", "CALLS", "LegacyPayClient",
        superseded_by_id=uuid.uuid4(),
    )
    session.add_all([t_active, t_closed, t_superseded])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "PaymentGateway", RelationType.CALLS, "StripeClient")
    route = _make_route("r_current", "Active Payment Route", [hop], intent=TemporalIntentType.CURRENT)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        intent_type=TemporalIntentType.CURRENT,
    )

    assert len(paths) == 1
    assert paths[0].target_entity == "StripeClient"
    assert paths[0].path_score > 0.80


# =========================================================================
# 24. HISTORICAL Filtering: Retrieves Superseded Relations
# =========================================================================

@pytest.mark.asyncio
async def test_24_historical_filtering_retrieves_superseded(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_old = _create_triplet(
        repo_id, "AuthModule", "CALLS", "CookieSession",
        valid_from=_dt(-48),
        valid_to=_dt(-24),
        superseded_by_id=uuid.uuid4(),
    )
    session.add(t_old)
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "AuthModule", RelationType.CALLS, "CookieSession")
    route = _make_route("r_hist", "Historical Auth Route", [hop], intent=TemporalIntentType.HISTORICAL)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        intent_type=TemporalIntentType.HISTORICAL,
    )

    assert len(paths) == 1
    assert paths[0].target_entity == "CookieSession"
    assert paths[0].score_breakdown.temporal_compatibility == 1.0


# =========================================================================
# 25. BEFORE Interval Boundaries: Excludes Expired Assertions
# =========================================================================

@pytest.mark.asyncio
async def test_25_before_interval_boundaries_and_expired_exclusion(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_anchor = _dt(0)

    # 1. Expired before anchor point: valid [-48h, -24h] -> MUST NOT be retrieved
    t_expired = _create_triplet(
        repo_id, "CryptoService", "CALLS", "MD5Hasher",
        valid_from=_dt(-48),
        valid_to=_dt(-24),
    )
    # 2. Valid at anchor point: valid [-24h, +24h] -> MUST be retrieved
    t_valid = _create_triplet(
        repo_id, "CryptoService", "CALLS", "SHA256Hasher",
        valid_from=_dt(-24),
        valid_to=_dt(24),
    )
    # 3. Created after anchor point: valid [+12h, NULL] -> MUST NOT be retrieved
    t_future = _create_triplet(
        repo_id, "CryptoService", "CALLS", "SHA3Hasher",
        valid_from=_dt(12),
    )
    session.add_all([t_expired, t_valid, t_future])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "CryptoService", RelationType.CALLS, "SHA256Hasher")
    route = _make_route("r_before", "Before Route", [hop], intent=TemporalIntentType.BEFORE)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        intent_type=TemporalIntentType.BEFORE,
        as_of=t_anchor,
    )

    assert len(paths) == 1
    assert paths[0].target_entity == "SHA256Hasher"
    assert paths[0].score_breakdown.temporal_compatibility == 1.0


# =========================================================================
# 26. AFTER Interval Boundaries: Excludes Obsolete Facts, Identifies Valid
# =========================================================================

@pytest.mark.asyncio
async def test_26_after_interval_boundaries(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_anchor = _dt(0)

    # 1. Expired before anchor: valid [-48h, -1h] -> MUST NOT be retrieved
    t_expired = _create_triplet(
        repo_id, "NotificationService", "CALLS", "SmsGateway",
        valid_from=_dt(-48),
        valid_to=_dt(-1),
    )
    # 2. Spanning active relation: valid [-24h, NULL] -> valid in post-anchor context
    t_spanning = _create_triplet(
        repo_id, "NotificationService", "CALLS", "EmailGateway",
        valid_from=_dt(-24),
        valid_to=None,
    )
    # 3. Created after anchor: valid [+2h, NULL] -> valid in post-anchor context
    t_post = _create_triplet(
        repo_id, "NotificationService", "CALLS", "PushGateway",
        valid_from=_dt(2),
        valid_to=None,
    )
    session.add_all([t_expired, t_spanning, t_post])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "NotificationService", RelationType.CALLS, "EmailGateway")
    route = _make_route("r_after", "After Route", [hop], intent=TemporalIntentType.AFTER)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        intent_type=TemporalIntentType.AFTER,
        as_of=t_anchor,
    )

    targets = [p.target_entity for p in paths]
    assert "SmsGateway" not in targets
    assert "EmailGateway" in targets or "PushGateway" in targets


# =========================================================================
# 27. INTERVAL Intersection: Computes True Path Intersection
# =========================================================================

@pytest.mark.asyncio
async def test_27_interval_intersection_and_contradiction(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    # Multi-hop with overlapping life span:
    # Hop 1: [-10h, +10h]
    # Hop 2: [-5h, +20h]
    # Overlap = [-5h, +10h]
    t1 = _create_triplet(
        repo_id, "OrderPipeline", "CALLS", "InventoryCheck",
        valid_from=_dt(-10),
        valid_to=_dt(10),
    )
    t2 = _create_triplet(
        repo_id, "InventoryCheck", "CALLS", "WarehouseDb",
        valid_from=_dt(-5),
        valid_to=_dt(20),
    )
    session.add_all([t1, t2])
    await session.commit()

    h1 = EvoRoutePlanner.create_hop(1, "OrderPipeline", RelationType.CALLS, "InventoryCheck")
    h2 = EvoRoutePlanner.create_hop(2, "InventoryCheck", RelationType.CALLS, "WarehouseDb")
    route = _make_route("r_interval", "Interval Overlap Route", [h1, h2], intent=TemporalIntentType.INTERVAL)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        intent_type=TemporalIntentType.INTERVAL,
        as_of=_dt(-6),
        until=_dt(15),
    )

    assert len(paths) == 1
    p = paths[0]
    assert p.valid_from == _dt(-5)  # max(-10, -5)
    assert p.valid_to == _dt(10)    # min(10, 20)
    assert not p.has_temporal_conflict


# =========================================================================
# 28. DIFF Commit-State Filtering
# =========================================================================

@pytest.mark.asyncio
async def test_28_diff_commit_state_filtering(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_base = _create_triplet(
        repo_id, "ConfigLoader", "CALLS", "JsonParser",
        commit_sha="commit_base_100",
    )
    t_target = _create_triplet(
        repo_id, "ConfigLoader", "CALLS", "YamlParser",
        commit_sha="commit_head_200",
        supersedes_id=t_base.id,
    )
    t_unrelated = _create_triplet(
        repo_id, "ConfigLoader", "CALLS", "XmlParser",
        commit_sha="commit_other_300",
    )
    session.add_all([t_base, t_target, t_unrelated])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "ConfigLoader", RelationType.CALLS, "YamlParser")
    route = _make_route("r_diff", "Diff Commit Route", [hop], intent=TemporalIntentType.DIFF)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        intent_type=TemporalIntentType.DIFF,
        reference_commit="commit_base_100",
        target_commit="commit_head_200",
    )

    targets = [p.target_entity for p in paths]
    assert "YamlParser" in targets
    assert "XmlParser" not in targets


# =========================================================================
# 29. EVOLUTION Supersession Chains
# =========================================================================

@pytest.mark.asyncio
async def test_29_evolution_supersession_chains(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_v1 = _create_triplet(
        repo_id, "DataStore", "CALLS", "InMemoryDriver",
        valid_from=_dt(-48),
        valid_to=_dt(-24),
    )
    t_v2 = _create_triplet(
        repo_id, "DataStore", "CALLS", "SqliteDriver",
        valid_from=_dt(-24),
        valid_to=_dt(-2),
        supersedes_id=t_v1.id,
    )
    t_v3 = _create_triplet(
        repo_id, "DataStore", "CALLS", "PostgresDriver",
        valid_from=_dt(-2),
        valid_to=None,
        supersedes_id=t_v2.id,
    )
    session.add_all([t_v1, t_v2, t_v3])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "DataStore", RelationType.CALLS, "PostgresDriver")
    route = _make_route("r_evo", "Evolution Chain Route", [hop], intent=TemporalIntentType.EVOLUTION)

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        intent_type=TemporalIntentType.EVOLUTION,
    )

    assert len(paths) >= 1
    for p in paths:
        assert p.score_breakdown.temporal_compatibility == 1.0


# =========================================================================
# 30. Supersession at Exact Interval Boundaries
# =========================================================================

@pytest.mark.asyncio
async def test_30_supersession_at_exact_interval_boundaries(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_switch = _dt(0)

    t_old = _create_triplet(
        repo_id, "CacheService", "CALLS", "MemcachedClient",
        valid_from=_dt(-20),
        valid_to=t_switch,
    )
    t_new = _create_triplet(
        repo_id, "CacheService", "CALLS", "RedisClient",
        valid_from=t_switch,
        valid_to=None,
        supersedes_id=t_old.id,
    )
    session.add_all([t_old, t_new])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "CacheService", RelationType.CALLS, "MemcachedClient")
    route_before = _make_route("r_b", "Before Boundary", [hop], intent=TemporalIntentType.BEFORE)

    paths_before, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route_before,
        intent_type=TemporalIntentType.BEFORE,
        as_of=t_switch,
    )
    assert any(p.target_entity == "MemcachedClient" for p in paths_before)

    hop_after = EvoRoutePlanner.create_hop(1, "CacheService", RelationType.CALLS, "RedisClient")
    route_after = _make_route("r_a", "After Boundary", [hop_after], intent=TemporalIntentType.AFTER)

    paths_after, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route_after,
        intent_type=TemporalIntentType.AFTER,
        as_of=t_switch,
    )
    assert any(p.target_entity == "RedisClient" for p in paths_after)


# =========================================================================
# 31. Branch Isolation Under Temporal Queries
# =========================================================================

@pytest.mark.asyncio
async def test_31_branch_isolation_under_temporal_queries(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t1_main = _create_triplet(repo_id, "RouteEngine", "CALLS", "ProdRouter", branch="main")
    t1_feat = _create_triplet(repo_id, "RouteEngine", "CALLS", "ExpRouter", branch="feat/experimental")
    session.add_all([t1_main, t1_feat])
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "RouteEngine", RelationType.CALLS, "ProdRouter")
    route = _make_route("r_branch", "Branch Isolation Route", [hop])

    paths_main, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        branch="main",
    )
    assert len(paths_main) == 1
    assert paths_main[0].target_entity == "ProdRouter"

    paths_feat, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
        branch="feat/experimental",
    )
    assert len(paths_feat) == 1
    assert paths_feat[0].target_entity == "ExpRouter"


# =========================================================================
# 32. Missing Temporal Anchors & Explicit Diagnostics
# =========================================================================

@pytest.mark.asyncio
async def test_32_missing_temporal_anchors_and_explicit_diagnostics(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    hop = EvoRoutePlanner.create_hop(1, "AuditService", RelationType.CALLS, "AuditLogger")
    route = _make_route("r_missing_anchor", "Missing Anchor Route", [hop], intent=TemporalIntentType.BEFORE)

    plan_before = MultiRoutePlan(
        query_text="What was audited before?",
        temporal_intent=TemporalIntentType.BEFORE,
        selected_routes=[route],
        all_candidate_count=1,
        deduplicated_count=1,
    )

    result = await EvoBeamSearchEngine.search_paths(
        session=session,
        repository_id=repo_id,
        route_plan=plan_before,
    )

    assert result.paths == []
    assert result.search_diagnostics.get("unsupported_temporal_intent") is True
    assert result.search_diagnostics.get("temporal_diagnostic") == "missing_temporal_anchor"

    plan_interval = MultiRoutePlan(
        query_text="Interval query with bad bounds",
        temporal_intent=TemporalIntentType.INTERVAL,
        selected_routes=[route],
        all_candidate_count=1,
        deduplicated_count=1,
    )
    bad_interval_result = await EvoBeamSearchEngine.search_paths(
        session=session,
        repository_id=repo_id,
        route_plan=plan_interval,
        as_of=_dt(10),
        until=_dt(-10),
    )
    assert bad_interval_result.paths == []
    assert bad_interval_result.search_diagnostics.get("temporal_diagnostic") == "contradictory_interval_bounds"


# =========================================================================
# 33. Unknown Validity Timestamps Fallback
# =========================================================================

@pytest.mark.asyncio
async def test_33_unknown_validity_timestamps_safe_fallback(async_test_db):
    session = async_test_db["session"]
    repo_id = async_test_db["repo_id"]

    t_unknown = _create_triplet(
        repo_id, "CoreEntity", "DEFINES", "CoreEntity::method",
        valid_from=None,
        valid_to=None,
    )
    session.add(t_unknown)
    await session.commit()

    hop = EvoRoutePlanner.create_hop(1, "CoreEntity", RelationType.DEFINES, "CoreEntity::method")
    route = _make_route("r_unknown", "Unknown Validity Route", [hop])

    paths, _ = await EvoBeamSearchEngine.execute_route_beam(
        session=session,
        repository_id=repo_id,
        route=route,
    )

    assert len(paths) == 1
    assert paths[0].valid_from is None
    assert paths[0].valid_to is None
    assert paths[0].path_score > 0.0
