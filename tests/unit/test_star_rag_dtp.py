"""
Unit tests for Structure-Aware STAR-RAG Decoupled Topological Propagation (DTP).
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).
"""

import uuid

from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.dtp_propagator import (
    DecoupledTopologicalPropagator,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraph,
    FunctionGraphEdge,
    FunctionGraphNode,
    GraphNodeType,
    GraphRelationType,
)


def test_dtp_directed_degree_extraction():
    """Verify directed in-degree and out-degree features are correctly computed."""
    dtp = DecoupledTopologicalPropagator(max_hops=3)

    n_a = FunctionGraphNode(node_id="a", name="a", qualified_name="a", node_type=GraphNodeType.FUNCTION, file_path="a.py")
    n_b = FunctionGraphNode(node_id="b", name="b", qualified_name="b", node_type=GraphNodeType.FUNCTION, file_path="b.py")
    n_c = FunctionGraphNode(node_id="c", name="c", qualified_name="c", node_type=GraphNodeType.FUNCTION, file_path="c.py")

    nodes = {"a": n_a, "b": n_b, "c": n_c}
    # a -> b and c -> b (b has in-degree 2, out-degree 0)
    edges = [
        FunctionGraphEdge(source_id="a", target_id="b", relation_type=GraphRelationType.CALLS),
        FunctionGraphEdge(source_id="c", target_id="b", relation_type=GraphRelationType.CALLS),
    ]

    features = dtp.extract_directed_features(nodes, edges)

    assert features["b"].in_degree == 2
    assert features["b"].out_degree == 0
    assert features["b"].directed_ratio == 1.0  # pure sink/target

    assert features["a"].in_degree == 0
    assert features["a"].out_degree == 1
    assert features["a"].directed_ratio == 0.0  # pure source/caller


def test_dtp_multi_order_connectivity_propagation():
    """Verify k-hop reachability probabilities propagate cleanly across graph layers."""
    dtp = DecoupledTopologicalPropagator(max_hops=3, decay_factor=0.8)

    # Chain: a -> b -> c -> d
    node_ids = ["a", "b", "c", "d"]
    nodes = {
        nid: FunctionGraphNode(node_id=nid, name=nid, qualified_name=nid, node_type=GraphNodeType.FUNCTION, file_path=f"{nid}.py")
        for nid in node_ids
    }
    edges = [
        FunctionGraphEdge(source_id="a", target_id="b", relation_type=GraphRelationType.CALLS),
        FunctionGraphEdge(source_id="b", target_id="c", relation_type=GraphRelationType.CALLS),
        FunctionGraphEdge(source_id="c", target_id="d", relation_type=GraphRelationType.CALLS),
    ]

    features = dtp.extract_directed_features(nodes, edges)
    features = dtp.compute_multi_order_connectivity(nodes, edges, seed_node_ids={"a"}, features=features)

    # Hop 1 reachability from a is at b
    assert features["b"].multi_order_reachability.get(1, 0.0) == 1.0
    # Hop 2 reachability from a is at c
    assert features["c"].multi_order_reachability.get(2, 0.0) == 1.0
    # Hop 3 reachability from a is at d
    assert features["d"].multi_order_reachability.get(3, 0.0) == 1.0

    # Closer nodes in propagation get higher decayed structural scores
    assert features["b"].structural_score > features["d"].structural_score


def test_dtp_handles_isolated_and_cyclic_nodes():
    """Verify DTP terminates and scores cleanly without division by zero on cycles or isolated nodes."""
    dtp = DecoupledTopologicalPropagator(max_hops=3)

    nodes = {
        "cycle_1": FunctionGraphNode(node_id="cycle_1", name="c1", qualified_name="c1", node_type=GraphNodeType.FUNCTION, file_path="c.py"),
        "cycle_2": FunctionGraphNode(node_id="cycle_2", name="c2", qualified_name="c2", node_type=GraphNodeType.FUNCTION, file_path="c.py"),
        "isolated": FunctionGraphNode(node_id="isolated", name="iso", qualified_name="iso", node_type=GraphNodeType.FUNCTION, file_path="iso.py"),
    }
    edges = [
        FunctionGraphEdge(source_id="cycle_1", target_id="cycle_2", relation_type=GraphRelationType.CALLS),
        FunctionGraphEdge(source_id="cycle_2", target_id="cycle_1", relation_type=GraphRelationType.CALLS),
    ]

    features = dtp.extract_directed_features(nodes, edges)
    features = dtp.compute_multi_order_connectivity(nodes, edges, seed_node_ids={"cycle_1"}, features=features)

    assert features["isolated"].in_degree == 0
    assert features["isolated"].out_degree == 0
    assert features["isolated"].structural_score == 0.0
    assert features["cycle_1"].structural_score > 0.0
    assert features["cycle_2"].structural_score > 0.0


def test_dtp_scores_candidates_into_signals():
    """Verify propagate_and_score_candidates injects 'dtp_structural' into candidate signals."""
    dtp = DecoupledTopologicalPropagator(max_hops=2)
    graph = FunctionGraph()

    n = FunctionGraphNode(node_id="file:1", name="f1", qualified_name="f1", node_type=GraphNodeType.FILE, file_path="f1.py")
    graph.add_node(n)

    cand = RetrievedCandidate(
        candidate_id="cand_1",
        entity_type="FILE",
        name="f1",
        path="f1.py",
        start_line=1,
        end_line=10,
        content="code",
        file_id=uuid.uuid4(),
        signals={},
        metadata={"is_seed": True},
    )

    cands = dtp.propagate_and_score_candidates([cand], graph, seed_node_ids={"cand_1"})
    assert "dtp_structural" in cands[0].signals
    assert 0.0 <= cands[0].signals["dtp_structural"] <= 1.0
