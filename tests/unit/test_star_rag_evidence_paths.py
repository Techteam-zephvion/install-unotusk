"""
Unit tests for Structure-Aware STAR-RAG Granular Evidence Path Construction.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).
"""

import uuid

from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.evidence_paths import (
    GranularEvidencePathBuilder,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraph,
    FunctionGraphEdge,
    FunctionGraphNode,
    GraphNodeType,
    GraphRelationType,
)


def test_evidence_paths_multi_hop_discovery():
    """Verify directed multi-hop evidence path between seed and candidate is found and formatted."""
    builder = GranularEvidencePathBuilder(max_path_depth=4)
    graph = FunctionGraph()

    # Create 3-hop chain: api -> svc -> repo
    n1 = FunctionGraphNode(node_id="api", name="checkout", qualified_name="checkout", node_type=GraphNodeType.FUNCTION, file_path="api.py", start_line=10)
    n2 = FunctionGraphNode(node_id="svc", name="process", qualified_name="process", node_type=GraphNodeType.FUNCTION, file_path="svc.py", start_line=25)
    n3 = FunctionGraphNode(node_id="repo", name="persist", qualified_name="persist", node_type=GraphNodeType.FUNCTION, file_path="repo.py", start_line=40)

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    graph.add_edge(FunctionGraphEdge(source_id="api", target_id="svc", relation_type=GraphRelationType.CALLS, line_number=15))
    graph.add_edge(FunctionGraphEdge(source_id="svc", target_id="repo", relation_type=GraphRelationType.CALLS, line_number=30))

    cand = RetrievedCandidate(
        candidate_id="repo",
        entity_type="SYMBOL",
        name="persist",
        path="repo.py",
        start_line=40,
        end_line=50,
        content="def persist(): pass",
        file_id=uuid.uuid4(),
    )

    paths = builder.build_evidence_paths_for_candidates(
        candidates=[cand],
        graph=graph,
        seed_node_ids={"api"},
    )

    assert len(paths) >= 1
    primary_path = paths[0]
    assert primary_path.source_entity == "checkout"
    assert primary_path.target_entity == "persist"
    assert len(primary_path.hops) == 2
    assert "api.py:checkout -> [CALLS] -> svc.py:process -> [CALLS] -> repo.py:persist" in primary_path.full_path_str
    assert cand.metadata.get("relationship_hop") == 2


def test_evidence_paths_cycle_prevention():
    """Verify cyclic edges do not cause infinite loops in path finding."""
    builder = GranularEvidencePathBuilder(max_path_depth=4)
    graph = FunctionGraph()

    n_a = FunctionGraphNode(node_id="a", name="a", qualified_name="a", node_type=GraphNodeType.FUNCTION, file_path="a.py")
    n_b = FunctionGraphNode(node_id="b", name="b", qualified_name="b", node_type=GraphNodeType.FUNCTION, file_path="b.py")
    graph.add_node(n_a)
    graph.add_node(n_b)

    # a -> b and b -> a (cycle)
    graph.add_edge(FunctionGraphEdge(source_id="a", target_id="b", relation_type=GraphRelationType.CALLS))
    graph.add_edge(FunctionGraphEdge(source_id="b", target_id="a", relation_type=GraphRelationType.CALLS))

    raw_paths = builder.find_paths_between(graph, "a", "b")
    assert len(raw_paths) == 1
    assert len(raw_paths[0]) == 1  # direct 1-hop path, avoids infinite cycling
