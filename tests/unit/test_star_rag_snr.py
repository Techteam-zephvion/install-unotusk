"""
Unit tests for Structure-Aware STAR-RAG Semantic Noise Routing (SNR).
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).
"""

from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.retriever import generate_text_embedding
from apps.api.src.services.context_engine.star_rag_structure.snr_router import (
    SemanticNoiseRouter,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    FunctionGraphEdge,
    FunctionGraphNode,
    GraphNodeType,
    GraphRelationType,
)


def test_snr_accepts_semantically_relevant_edge():
    """Verify SNR gate accepts edge whose target is relevant to payment failure query."""
    router = SemanticNoiseRouter(noise_threshold=0.30)
    query = "Find the functions responsible for processing payment failures."
    analyzed = analyze_query(query)
    q_emb = generate_text_embedding(query)

    src = FunctionGraphNode(
        node_id="services/payment.py::process_payment",
        name="process_payment",
        qualified_name="process_payment",
        node_type=GraphNodeType.FUNCTION,
        file_path="services/payment.py",
    )
    tgt = FunctionGraphNode(
        node_id="services/payment.py::handle_payment_failure",
        name="handle_payment_failure",
        qualified_name="handle_payment_failure",
        node_type=GraphNodeType.FUNCTION,
        file_path="services/payment.py",
        signature="def handle_payment_failure(charge_id: str, error: Exception):",
        content="def handle_payment_failure(charge_id: str, error: Exception): pass",
    )
    edge = FunctionGraphEdge(
        source_id=src.node_id,
        target_id=tgt.node_id,
        relation_type=GraphRelationType.CALLS,
        line_number=45,
    )

    decision = router.evaluate_edge(
        edge=edge,
        query_text=query,
        query_embedding=q_emb,
        source_node=src,
        target_node=tgt,
        analyzed_query=analyzed,
    )

    assert decision.is_accepted is True
    assert decision.gate_weight >= 0.30
    assert decision.rejection_reason is None


def test_snr_suppresses_irrelevant_edge_as_semantic_noise():
    """Verify SNR gate suppresses edge to unrelated utility module as noise."""
    router = SemanticNoiseRouter(noise_threshold=0.30)
    query = "Find the functions responsible for processing payment failures."
    analyzed = analyze_query(query)
    q_emb = generate_text_embedding(query)

    src = FunctionGraphNode(
        node_id="services/payment.py::process_payment",
        name="process_payment",
        qualified_name="process_payment",
        node_type=GraphNodeType.FUNCTION,
        file_path="services/payment.py",
    )
    tgt = FunctionGraphNode(
        node_id="utils/date_utils.py::format_date_iso",
        name="format_date_iso",
        qualified_name="format_date_iso",
        node_type=GraphNodeType.FUNCTION,
        file_path="utils/date_utils.py",
        signature="def format_date_iso(dt: datetime) -> str:",
        content="def format_date_iso(dt: datetime) -> str: return dt.isoformat()",
    )
    edge = FunctionGraphEdge(
        source_id=src.node_id,
        target_id=tgt.node_id,
        relation_type=GraphRelationType.IMPORTS,
        line_number=5,
    )

    decision = router.evaluate_edge(
        edge=edge,
        query_text=query,
        query_embedding=q_emb,
        source_node=src,
        target_node=tgt,
        analyzed_query=analyzed,
    )

    assert decision.is_accepted is False
    assert decision.semantic_relevance < 0.30
    assert "Suppressed as semantic noise" in str(decision.rejection_reason)


def test_snr_preserves_seed_edges_unconditionally():
    """Verify seed-to-seed edges are always retained regardless of query text."""
    router = SemanticNoiseRouter(noise_threshold=0.80)  # Very high threshold
    query = "unrelated query about css styling"

    edge = FunctionGraphEdge(
        source_id="seed_a",
        target_id="seed_b",
        relation_type=GraphRelationType.CALLS,
    )
    nodes = {
        "seed_a": FunctionGraphNode(node_id="seed_a", name="seed_a", qualified_name="seed_a", node_type=GraphNodeType.FUNCTION, file_path="a.py"),
        "seed_b": FunctionGraphNode(node_id="seed_b", name="seed_b", qualified_name="seed_b", node_type=GraphNodeType.FUNCTION, file_path="b.py"),
    }

    filtered_edges, decisions = router.route_and_filter_edges(
        edges=[edge],
        nodes=nodes,
        query_text=query,
        query_embedding=None,
        seed_node_ids={"seed_a", "seed_b"},
    )

    assert len(filtered_edges) == 1
    assert decisions[0].is_accepted is True
    assert "seed-to-seed" in str(decisions[0].rejection_reason)


def test_snr_handles_missing_embeddings_via_lexical_overlap():
    """Verify SNR falls back cleanly to lexical token matching when query_embedding is None."""
    router = SemanticNoiseRouter(noise_threshold=0.25)
    query = "authenticate token verification"

    src = FunctionGraphNode(node_id="src", name="src", qualified_name="src", node_type=GraphNodeType.FUNCTION, file_path="src.py")
    tgt = FunctionGraphNode(
        node_id="auth",
        name="authenticate",
        qualified_name="authenticate",
        node_type=GraphNodeType.FUNCTION,
        file_path="auth.py",
        content="def authenticate(token: str): pass",
    )
    edge = FunctionGraphEdge(source_id="src", target_id="auth", relation_type=GraphRelationType.CALLS)

    decision = router.evaluate_edge(
        edge=edge,
        query_text=query,
        query_embedding=None,
        source_node=src,
        target_node=tgt,
    )

    assert decision.is_accepted is True
    assert decision.gate_weight > 0.0
