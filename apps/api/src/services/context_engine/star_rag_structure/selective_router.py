"""
Selective Intent Router for ATOM and Structure-Aware STAR-RAG.

Evaluates user query intent, extracted code symbols, paths, and candidate signals
to decide whether a query requires Structure-Aware graph retrieval (SNR + DTP + SSAF)
or is optimally served by authoritative Baseline ATOM retrieval.

Expected Principles:
1. When STRUCTURE_AWARE_STAR_RAG_ENABLED is False (and not forced), STAR-RAG never executes.
2. Direct symbol, method, or file path lookups are served by ATOM without graph overhead.
3. Structural questions (execution flows, call hierarchies, cross-module dependencies,
   subsystem interactions) are routed to Structure-Aware STAR-RAG.
4. Decision is fully observable via structured logs and debug telemetry.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
    from apps.api.src.services.context_engine.retriever import RetrievedCandidate

logger = logging.getLogger(__name__)

# Core keywords signaling structural, execution-flow, or relational intent
STRUCTURAL_KEYWORDS: frozenset[str] = frozenset(
    {
        "trace",
        "tracing",
        "flow",
        "call",
        "calls",
        "caller",
        "callers",
        "callee",
        "callees",
        "called",
        "calling",
        "invoke",
        "invokes",
        "invoked",
        "invoking",
        "invocation",
        "depend",
        "depends",
        "dependency",
        "dependencies",
        "hierarchy",
        "lifecycle",
        "pipeline",
        "execution",
        "architecture",
        "subsystem",
        "interaction",
        "interactions",
        "interact",
        "interacts",
        "chain",
        "chains",
        "connection",
        "connections",
        "connected",
        "dataflow",
        "dispatch",
        "orchestrat",
        "orchestration",
        "relationship",
        "relationships",
        "graph",
    }
)


class StarRagSelectiveRouter:
    """
    Lightweight, observable router governing when Structure-Aware STAR-RAG executes.
    """

    @classmethod
    def should_route_to_star_rag(
        cls,
        query_text: str,
        analyzed_query: AnalyzedQuery | None,
        candidates: list[RetrievedCandidate] | None,
        flag_enabled: bool,
        force_star_rag: bool = False,
    ) -> tuple[bool, str]:
        """
        Determines whether to execute Structure-Aware STAR-RAG.

        Returns:
            (should_route, routing_reason)
        """
        # Principle 1: Safety Gate — if flag is disabled and not forced, strictly use ATOM
        if not flag_enabled and not force_star_rag:
            return False, "feature_flag_disabled"

        # Explicit test force bypasses heuristics for isolated testing
        if force_star_rag:
            return True, "forced_by_caller"

        # If candidates are empty, no graph routing can occur
        if not candidates:
            return False, "no_candidates_available"

        raw_lower = query_text.lower()
        query_tokens = set(raw_lower.replace("_", " ").replace(".", " ").split())

        # Check for presence of structural intent keywords
        has_structural_keyword = bool(STRUCTURAL_KEYWORDS.intersection(query_tokens))
        if analyzed_query and not has_structural_keyword:
            has_structural_keyword = any(
                kw in STRUCTURAL_KEYWORDS for kw in analyzed_query.keywords
            )

        # Principle 2: Direct Symbol or Path Lookups without structural intent -> ATOM
        # If the user specifically asks for a single function/class or file path,
        # ATOM's exact relational index and +1.5 boost deliver superior precision.
        has_exact_symbol = bool(analyzed_query and analyzed_query.symbol_candidates)
        has_exact_path = bool(analyzed_query and analyzed_query.path_candidates)
        word_count = len(query_text.split())

        if (has_exact_symbol or has_exact_path) and not has_structural_keyword:
            # Query is concise and targeted (<= 8 words) with specific symbol/file
            if word_count <= 8:
                reason = (
                    "direct_symbol_lookup_atom"
                    if has_exact_symbol
                    else "direct_path_lookup_atom"
                )
                logger.info(
                    "Selective router: Query '%s' routed to ATOM (%s)",
                    query_text[:50],
                    reason,
                )
                return False, reason

        # Principle 3: Structural, Execution Flow, or Multi-Hop Queries -> STAR-RAG
        if has_structural_keyword:
            logger.info(
                "Selective router: Query '%s' routed to STAR-RAG (structural_tracing_intent)",
                query_text[:50],
            )
            return True, "structural_tracing_intent"

        # Principle 4: Multi-Entity Relational Inquiries (e.g. "How does A interact with B")
        if analyzed_query and len(analyzed_query.symbol_candidates) >= 2:
            logger.info(
                "Selective router: Query '%s' routed to STAR-RAG (multi_entity_relational_intent)",
                query_text[:50],
            )
            return True, "multi_entity_relational_intent"

        # Principle 5: Complex Semantic / Architectural Queries
        # If candidates contain multi-hop relationships and broad concept keywords
        if analyzed_query and analyzed_query.concept_keywords:
            has_relational_candidates = any(
                c.metadata.get("relationship_hop", 0) > 0 for c in candidates
            )
            if has_relational_candidates:
                logger.info(
                    "Selective router: Query '%s' routed to STAR-RAG (architectural_subsystem_intent)",
                    query_text[:50],
                )
                return True, "architectural_subsystem_intent"

        # Default fallback: Standard ATOM lexical/vector retrieval
        logger.info(
            "Selective router: Query '%s' routed to ATOM (standard_retrieval_atom)",
            query_text[:50],
        )
        return False, "standard_retrieval_atom"
