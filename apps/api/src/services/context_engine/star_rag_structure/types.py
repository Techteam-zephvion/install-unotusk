"""
STAR-RAG Structure-Aware Graph Retrieval Data Types.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from apps.api.src.services.context_engine.retriever import RetrievedCandidate


class GraphNodeType(str, Enum):
    FILE = "FILE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    MODULE = "MODULE"


class GraphRelationType(str, Enum):
    CALLS = "CALLS"
    DEFINES = "DEFINES"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    REFERENCES = "REFERENCES"


@dataclass
class FunctionGraphNode:
    """Represents a fine-grained node (function, method, class, or file) in the code graph."""

    node_id: str
    name: str
    qualified_name: str
    node_type: GraphNodeType
    file_path: str
    start_line: int = 1
    end_line: int = 1
    file_id: uuid.UUID | None = None
    symbol_id: uuid.UUID | None = None
    signature: str = ""
    content: str = ""
    commit_sha: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FunctionGraphEdge:
    """Represents a directed edge between two code graph nodes."""

    source_id: str
    target_id: str
    relation_type: GraphRelationType
    line_number: int = 1
    source_file: str = ""
    target_file: str = ""
    confidence: float = 1.0
    is_uncertain: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FunctionGraph:
    """In-memory or queried directed graph of fine-grained code entities and relations."""

    nodes: dict[str, FunctionGraphNode] = field(default_factory=dict)
    edges: list[FunctionGraphEdge] = field(default_factory=list)
    out_edges: dict[str, list[FunctionGraphEdge]] = field(default_factory=dict)
    in_edges: dict[str, list[FunctionGraphEdge]] = field(default_factory=dict)

    def add_node(self, node: FunctionGraphNode) -> None:
        self.nodes[node.node_id] = node
        if node.node_id not in self.out_edges:
            self.out_edges[node.node_id] = []
        if node.node_id not in self.in_edges:
            self.in_edges[node.node_id] = []

    def add_edge(self, edge: FunctionGraphEdge) -> None:
        self.edges.append(edge)
        self.out_edges.setdefault(edge.source_id, []).append(edge)
        self.in_edges.setdefault(edge.target_id, []).append(edge)


@dataclass
class SNREdgeDecision:
    """Outcome of evaluating an edge via Semantic Noise Routing (SNR)."""

    edge: FunctionGraphEdge
    gate_weight: float
    semantic_relevance: float
    is_accepted: bool
    rejection_reason: str | None = None


@dataclass
class DTPNodeFeatures:
    """Decoupled Topological Propagation features for a single graph node."""

    node_id: str
    in_degree: int
    out_degree: int
    directed_ratio: float  # d_in / (d_in + d_out + eps)
    density: float         # log(1 + d_in + d_out)
    multi_order_reachability: dict[int, float] = field(default_factory=dict)  # hop -> prob
    structural_score: float = 0.0


@dataclass
class SSAFFusionResult:
    """Result of Semantic-Structural Adaptive Fusion for a single candidate."""

    candidate_id: str
    candidate_name: str
    semantic_score: float
    structural_score: float
    adaptive_beta: float  # weight on semantic stream; (1 - beta) is on structural
    fused_score: float
    is_conflict: bool
    explanation: list[str] = field(default_factory=list)


@dataclass
class GranularEvidenceHop:
    """A single hop in a function-level evidence path."""

    hop_index: int
    source_node_id: str
    source_name: str
    source_file: str
    relation: str
    target_node_id: str
    target_name: str
    target_file: str
    line_number: int = 1


@dataclass
class GranularEvidencePath:
    """Validated multi-hop evidence path connecting a topic entity to a candidate."""

    path_id: str
    source_entity: str
    target_entity: str
    hops: list[GranularEvidenceHop]
    full_path_str: str
    confidence: float = 1.0
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class StructureAwareStarRagResult:
    """Comprehensive diagnostic result from a Structure-Aware STAR-RAG retrieval run."""

    candidates: list[RetrievedCandidate]
    snr_decisions: list[SNREdgeDecision] = field(default_factory=list)
    dtp_features: dict[str, DTPNodeFeatures] = field(default_factory=dict)
    ssaf_results: list[SSAFFusionResult] = field(default_factory=list)
    evidence_paths: list[GranularEvidencePath] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    is_fallback: bool = False
    fallback_reason: str | None = None
