"""
Structure-Aware STAR-RAG Package.
Reference: Electronics 2026, 15(22), 5289 (Zhong et al., 13 Nov 2026).
"""

from apps.api.src.services.context_engine.star_rag_structure.config import (
    StructureAwareStarRagConfig,
)
from apps.api.src.services.context_engine.star_rag_structure.dtp_propagator import (
    DecoupledTopologicalPropagator,
)
from apps.api.src.services.context_engine.star_rag_structure.evidence_paths import (
    GranularEvidencePathBuilder,
)
from apps.api.src.services.context_engine.star_rag_structure.graph_extractor import (
    CodeGraphExtractor,
)
from apps.api.src.services.context_engine.star_rag_structure.service import (
    StructureAwareStarRagService,
)
from apps.api.src.services.context_engine.star_rag_structure.snr_router import (
    SemanticNoiseRouter,
)
from apps.api.src.services.context_engine.star_rag_structure.ssaf_fusion import (
    SemanticStructuralAdaptiveFusion,
)
from apps.api.src.services.context_engine.star_rag_structure.types import (
    DTPNodeFeatures,
    FunctionGraph,
    FunctionGraphEdge,
    FunctionGraphNode,
    GranularEvidenceHop,
    GranularEvidencePath,
    GraphNodeType,
    GraphRelationType,
    SNREdgeDecision,
    SSAFFusionResult,
    StructureAwareStarRagResult,
)

__all__ = [
    "CodeGraphExtractor",
    "DTPNodeFeatures",
    "DecoupledTopologicalPropagator",
    "FunctionGraph",
    "FunctionGraphEdge",
    "FunctionGraphNode",
    "GranularEvidenceHop",
    "GranularEvidencePath",
    "GranularEvidencePathBuilder",
    "GraphNodeType",
    "GraphRelationType",
    "SNREdgeDecision",
    "SSAFFusionResult",
    "SemanticNoiseRouter",
    "SemanticStructuralAdaptiveFusion",
    "StructureAwareStarRagConfig",
    "StructureAwareStarRagResult",
    "StructureAwareStarRagService",
]
