"""
Comprehensive regression test suite for Structure-Aware STAR-RAG Performance Remediation
and ATOM Ranking Preservation.
"""

import uuid

from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.cache import CodeGraphCache
from apps.api.src.services.context_engine.star_rag_structure.dtp_propagator import (
    DecoupledTopologicalPropagator,
)
from apps.api.src.services.context_engine.star_rag_structure.snr_router import (
    SemanticNoiseRouter,
)
from apps.api.src.services.context_engine.star_rag_structure.ssaf_fusion import (
    SemanticStructuralAdaptiveFusion,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraph,
    FunctionGraphEdge,
    FunctionGraphNode,
    GraphNodeType,
    GraphRelationType,
)

# ==============================================================================
# 1. RANKING REGRESSION TESTS
# ==============================================================================


def test_ranking_exact_symbol_match_outranks_utility_hub():
    """
    Critical regression test:
    An exact symbol match (e.g. MultiSignalRetriever) must NOT be overtaken
    by a highly connected architectural utility hub (e.g. settings.py) even
    if the utility hub has a maximum structural score of 1.0.
    """
    ssaf = SemanticStructuralAdaptiveFusion(max_structural_weight=0.15)
    query_text = "Where is MultiSignalRetriever defined and how does retrieve_candidates work?"
    analyzed = analyze_query(query_text)

    cand_target = RetrievedCandidate(
        candidate_id="target_sym",
        entity_type="SYMBOL",
        name="MultiSignalRetriever",
        path="apps/api/src/services/context_engine/retriever.py",
        start_line=15,
        end_line=120,
        content="class MultiSignalRetriever:\n    def retrieve_candidates(self): pass",
        file_id=uuid.uuid4(),
        signals={"symbol_match": 1.0, "vector_similarity": 0.82, "dtp_structural": 0.05},
    )

    cand_utility_hub = RetrievedCandidate(
        candidate_id="hub_settings",
        entity_type="FILE",
        name="settings.py",
        path="apps/api/src/config/settings.py",
        start_line=1,
        end_line=100,
        content="class Settings:\n    APP_NAME = 'Unotusk'",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.35, "dtp_structural": 1.0},
    )

    ranked, results = ssaf.fuse_and_rank_candidates(
        candidates=[cand_utility_hub, cand_target],
        query_text=query_text,
        analyzed_query=analyzed,
    )

    assert len(ranked) == 2
    assert ranked[0].candidate.candidate_id == "target_sym", (
        f"Expected exact symbol candidate to win, but {ranked[0].candidate.name} won with score {ranked[0].score}"
    )
    assert ranked[0].score > ranked[1].score


def test_ranking_exact_path_match_preserved():
    """Verify that an exact path candidate match is preserved and remains top-ranked."""
    ssaf = SemanticStructuralAdaptiveFusion()
    query_text = "Look up auth_service.py"
    analyzed = analyze_query(query_text)

    cand_path = RetrievedCandidate(
        candidate_id="auth_file",
        entity_type="FILE",
        name="auth_service.py",
        path="apps/api/src/services/auth_service.py",
        start_line=1,
        end_line=200,
        content="class AuthService: pass",
        file_id=uuid.uuid4(),
        signals={"file_match": 1.0, "vector_similarity": 0.70, "dtp_structural": 0.20},
    )

    cand_other = RetrievedCandidate(
        candidate_id="other_file",
        entity_type="FILE",
        name="session.py",
        path="apps/api/src/db/session.py",
        start_line=1,
        end_line=50,
        content="AsyncSessionLocal = None",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.30, "dtp_structural": 0.90},
    )

    ranked, _ = ssaf.fuse_and_rank_candidates([cand_other, cand_path], query_text, analyzed)
    assert ranked[0].candidate.candidate_id == "auth_file"


def test_ranking_dtp_contribution_is_strictly_bounded():
    """Verify that structural boost cannot exceed max_structural_weight."""
    max_weight = 0.15
    ssaf = SemanticStructuralAdaptiveFusion(max_structural_weight=max_weight)
    query_text = "General search query"
    analyzed = analyze_query(query_text)

    cand = RetrievedCandidate(
        candidate_id="c1",
        entity_type="CHUNK",
        name="sample_func",
        path="service.py",
        start_line=1,
        end_line=10,
        content="def sample_func(): pass",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.60, "dtp_structural": 1.0},
    )

    ranked, results = ssaf.fuse_and_rank_candidates([cand], query_text, analyzed)
    res = results[0]
    # Check baseline ATOM score vs fused score delta
    atom_base = MultiSignalRanker.rank_candidates([cand], analyzed, noise_threshold=0.0)[0].score
    delta = res.fused_score - atom_base
    assert delta <= max_weight + 1e-4, f"Structural delta {delta} exceeded max bound {max_weight}"


# ==============================================================================
# 2. DTP HUB ATTENUATION TESTS
# ==============================================================================


def test_dtp_hub_attenuation_suppresses_high_degree_sinks():
    """Verify high-degree utility sinks receive lower structural scores than specific targets."""
    dtp = DecoupledTopologicalPropagator(max_hops=2, hub_attenuation=True, attenuation_factor=0.75)

    nodes = {
        "seed": FunctionGraphNode(node_id="seed", name="caller", qualified_name="caller", node_type=GraphNodeType.FUNCTION, file_path="svc.py"),
        "hub": FunctionGraphNode(node_id="hub", name="settings", qualified_name="settings", node_type=GraphNodeType.FILE, file_path="settings.py"),
        "target": FunctionGraphNode(node_id="target", name="callee", qualified_name="callee", node_type=GraphNodeType.FUNCTION, file_path="target.py"),
    }
    # Create 20 callers to 'hub' to simulate an architectural sink
    edges = [
        FunctionGraphEdge(source_id="seed", target_id="hub", relation_type=GraphRelationType.IMPORTS),
        FunctionGraphEdge(source_id="seed", target_id="target", relation_type=GraphRelationType.CALLS),
    ]
    for i in range(20):
        extra_id = f"other_caller_{i}"
        nodes[extra_id] = FunctionGraphNode(node_id=extra_id, name=extra_id, qualified_name=extra_id, node_type=GraphNodeType.FUNCTION, file_path=f"other_{i}.py")
        edges.append(FunctionGraphEdge(source_id=extra_id, target_id="hub", relation_type=GraphRelationType.IMPORTS))

    features = dtp.extract_directed_features(nodes, edges)
    features = dtp.compute_multi_order_connectivity(nodes, edges, seed_node_ids={"seed"}, features=features)

    # In-degree of hub is 21; in-degree of target is 1
    assert features["hub"].in_degree == 21
    assert features["target"].in_degree == 1

    # With hub attenuation, target has a higher structural score than the utility hub
    assert features["target"].structural_score > features["hub"].structural_score, (
        f"Target score ({features['target'].structural_score}) should exceed hub score ({features['hub'].structural_score})"
    )


def test_dtp_seed_node_is_never_penalized_by_hub_attenuation():
    """Verify that a central node that IS the direct seed does not get attenuated."""
    dtp = DecoupledTopologicalPropagator(hub_attenuation=True, attenuation_factor=0.75)

    nodes = {
        "seed_service": FunctionGraphNode(node_id="seed_service", name="auth", qualified_name="auth", node_type=GraphNodeType.CLASS, file_path="auth.py"),
    }
    # Give seed_service in_degree = 30
    edges = []
    for i in range(30):
        cid = f"caller_{i}"
        nodes[cid] = FunctionGraphNode(node_id=cid, name=cid, qualified_name=cid, node_type=GraphNodeType.FUNCTION, file_path="call.py")
        edges.append(FunctionGraphEdge(source_id=cid, target_id="seed_service", relation_type=GraphRelationType.CALLS))

    features = dtp.extract_directed_features(nodes, edges)
    features = dtp.compute_multi_order_connectivity(nodes, edges, seed_node_ids={"seed_service"}, features=features)

    # Direct seed node must retain strong structural score (>= 0.50) despite high in-degree
    assert features["seed_service"].structural_score >= 0.50


# ==============================================================================
# 3. SSAF FUSION & CONFLICT TESTS
# ==============================================================================


def test_ssaf_conflict_suppresses_irrelevant_hub_boost():
    """Verify that an irrelevant candidate with high structural score gets 0 boost."""
    ssaf = SemanticStructuralAdaptiveFusion(conflict_threshold=0.40)
    query_text = "Show billing subscription checkout workflow"
    analyzed = analyze_query(query_text)

    # Utility hub with zero semantic match to 'billing' or 'subscription'
    cand_irrelevant_hub = RetrievedCandidate(
        candidate_id="exceptions_py",
        entity_type="FILE",
        name="exceptions.py",
        path="apps/api/src/core/exceptions.py",
        start_line=1,
        end_line=50,
        content="class UnotuskException(Exception): pass",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.15, "dtp_structural": 0.95},
    )

    ranked, results = ssaf.fuse_and_rank_candidates([cand_irrelevant_hub], query_text, analyzed)
    res = results[0]

    # Because baseline ATOM score is very low (< 0.25) and conflict detected, struct boost must be 0
    assert res.is_conflict is True
    assert "Conflict: Structural graph hub with low semantic relevance" in " ".join(res.explanation)
    assert res.fused_score <= 0.25


def test_ssaf_structural_boost_breaks_ties_between_relevant_candidates():
    """
    Verify that when two candidates have similar semantic scores, the candidate
    with structural graph connectivity receives a bounded boost and wins.
    """
    ssaf = SemanticStructuralAdaptiveFusion(max_structural_weight=0.15)
    query_text = "Trace execution flow of query processing"
    analyzed = analyze_query(query_text)

    # Candidate A: connected in call chain
    cand_a = RetrievedCandidate(
        candidate_id="cand_connected",
        entity_type="CHUNK",
        name="execute_query",
        path="query_runner.py",
        start_line=1,
        end_line=20,
        content="def execute_query(): pass",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.70, "dtp_structural": 0.85},
    )

    # Candidate B: disconnected file with similar semantic similarity
    cand_b = RetrievedCandidate(
        candidate_id="cand_disconnected",
        entity_type="CHUNK",
        name="query_helper",
        path="utils/query_helper.py",
        start_line=1,
        end_line=20,
        content="def query_helper(): pass",
        file_id=uuid.uuid4(),
        signals={"vector_similarity": 0.70, "dtp_structural": 0.0},
    )

    ranked, _ = ssaf.fuse_and_rank_candidates([cand_b, cand_a], query_text, analyzed)
    assert ranked[0].candidate.candidate_id == "cand_connected"
    assert ranked[0].score > ranked[1].score


# ==============================================================================
# 4. CODE GRAPH CACHE TESTS
# ==============================================================================


def test_code_graph_cache_store_and_retrieve():
    """Verify that FunctionGraph can be cached and retrieved identically."""
    import asyncio

    async def _run():
        snapshot_id = uuid.uuid4()
        commit_sha = "test-sha-12345"

        graph = FunctionGraph()
        n = FunctionGraphNode(
            node_id="node1",
            name="test_func",
            qualified_name="test_func",
            node_type=GraphNodeType.FUNCTION,
            file_path="test.py",
            start_line=10,
            end_line=25,
        )
        graph.add_node(n)
        e = FunctionGraphEdge(
            source_id="node1",
            target_id="node2",
            relation_type=GraphRelationType.CALLS,
            line_number=15,
            source_file="test.py",
        )
        graph.add_edge(e)

        # Store in cache
        await CodeGraphCache.set_graph(snapshot_id, commit_sha, graph)

        # Retrieve from cache
        retrieved = await CodeGraphCache.get_graph(snapshot_id, commit_sha)
        assert retrieved is not None
        assert len(retrieved.nodes) == 1
        assert "node1" in retrieved.nodes
        assert retrieved.nodes["node1"].start_line == 10
        assert len(retrieved.edges) == 1
        assert retrieved.edges[0].relation_type == GraphRelationType.CALLS

        # Invalidate cache
        await CodeGraphCache.invalidate_graph(snapshot_id)
        # Check that in-memory tier is purged
        mem_key = CodeGraphCache._make_key(snapshot_id, commit_sha)
        assert mem_key not in CodeGraphCache._MEMORY_GRAPH_CACHE if hasattr(CodeGraphCache, "_MEMORY_GRAPH_CACHE") else True

    asyncio.run(_run())


# ==============================================================================
# 5. SNR ROUTING OPTIMIZATION TESTS
# ==============================================================================


def test_snr_memoizes_target_evaluations_and_deduplicates_edges():
    """Verify that SNR memoizes target similarity and deduplicates duplicate edges."""
    snr = SemanticNoiseRouter(noise_threshold=0.30)

    nodes = {
        "src1": FunctionGraphNode(node_id="src1", name="src1", qualified_name="src1", node_type=GraphNodeType.FUNCTION, file_path="src1.py"),
        "src2": FunctionGraphNode(node_id="src2", name="src2", qualified_name="src2", node_type=GraphNodeType.FUNCTION, file_path="src2.py"),
        "tgt": FunctionGraphNode(node_id="tgt", name="validate_token", qualified_name="validate_token", node_type=GraphNodeType.FUNCTION, file_path="auth.py"),
    }
    # Multiple edges pointing to the same target node 'tgt'
    edges = [
        FunctionGraphEdge(source_id="src1", target_id="tgt", relation_type=GraphRelationType.CALLS),
        FunctionGraphEdge(source_id="src2", target_id="tgt", relation_type=GraphRelationType.CALLS),
        # Duplicate edge
        FunctionGraphEdge(source_id="src1", target_id="tgt", relation_type=GraphRelationType.CALLS),
    ]

    query_text = "validate user token authentication"
    accepted, decisions = snr.route_and_filter_edges(edges, nodes, query_text, query_embedding=None)

    # Duplicate edge was pruned during routing
    assert len(decisions) == 2
    assert len(accepted) == 2
    # Target similarity was cached
    assert "tgt" in snr._target_sim_cache
