"""
Unit tests for StarRagSelectiveRouter.
Verifies selective routing behavior between ATOM and Structure-Aware STAR-RAG.
"""

import uuid

from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.context_engine.star_rag_structure.selective_router import (
    StarRagSelectiveRouter,
)


def _make_candidate(name: str = "TestClass", hop: int = 0) -> RetrievedCandidate:
    return RetrievedCandidate(
        candidate_id=f"cand_{name}",
        entity_type="SYMBOL",
        name=name,
        path=f"apps/api/src/{name.lower()}.py",
        content=f"class {name}: pass",
        start_line=1,
        end_line=10,
        file_id=uuid.uuid4(),
        signals={"symbol_match": 1.0},
        metadata={"relationship_hop": hop},
    )


def test_selective_router_respects_disabled_feature_flag():
    analyzed = AnalyzedQuery(raw_query="trace execution flow", keywords=["trace", "flow"])
    candidates = [_make_candidate()]

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="trace execution flow",
        analyzed_query=analyzed,
        candidates=candidates,
        flag_enabled=False,
        force_star_rag=False,
    )

    assert should_route is False
    assert reason == "feature_flag_disabled"


def test_selective_router_allows_caller_force():
    analyzed = AnalyzedQuery(raw_query="simple query", keywords=["simple"])
    candidates = [_make_candidate()]

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="simple query",
        analyzed_query=analyzed,
        candidates=candidates,
        flag_enabled=False,
        force_star_rag=True,
    )

    assert should_route is True
    assert reason == "forced_by_caller"


def test_selective_router_handles_empty_candidates():
    analyzed = AnalyzedQuery(raw_query="trace execution flow", keywords=["trace", "flow"])

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="trace execution flow",
        analyzed_query=analyzed,
        candidates=[],
        flag_enabled=True,
    )

    assert should_route is False
    assert reason == "no_candidates_available"


def test_selective_router_routes_direct_symbol_to_atom():
    analyzed = AnalyzedQuery(
        raw_query="Where is AuthService defined?",
        keywords=["authservice", "defined"],
        symbol_candidates=["AuthService"],
    )
    candidates = [_make_candidate(name="AuthService")]

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="Where is AuthService defined?",
        analyzed_query=analyzed,
        candidates=candidates,
        flag_enabled=True,
    )

    assert should_route is False
    assert reason == "direct_symbol_lookup_atom"


def test_selective_router_routes_direct_path_to_atom():
    analyzed = AnalyzedQuery(
        raw_query="show settings.py",
        keywords=["settings", "py"],
        path_candidates=["settings.py"],
    )
    candidates = [_make_candidate(name="settings")]

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="show settings.py",
        analyzed_query=analyzed,
        candidates=candidates,
        flag_enabled=True,
    )

    assert should_route is False
    assert reason == "direct_path_lookup_atom"


def test_selective_router_routes_structural_tracing_to_star_rag():
    analyzed = AnalyzedQuery(
        raw_query="Trace the execution flow from ask_project to ProjectContextEngine",
        keywords=["trace", "execution", "flow", "ask_project", "projectcontextengine"],
        symbol_candidates=["ask_project", "ProjectContextEngine"],
    )
    candidates = [_make_candidate(name="ask_project"), _make_candidate(name="ProjectContextEngine")]

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="Trace the execution flow from ask_project to ProjectContextEngine",
        analyzed_query=analyzed,
        candidates=candidates,
        flag_enabled=True,
    )

    assert should_route is True
    assert reason == "structural_tracing_intent"


def test_selective_router_routes_dependency_chain_to_star_rag():
    analyzed = AnalyzedQuery(
        raw_query="What dependencies does CodeGraphCache call?",
        keywords=["dependencies", "codegraphcache", "call"],
        symbol_candidates=["CodeGraphCache"],
    )
    candidates = [_make_candidate(name="CodeGraphCache")]

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="What dependencies does CodeGraphCache call?",
        analyzed_query=analyzed,
        candidates=candidates,
        flag_enabled=True,
    )

    assert should_route is True
    assert reason == "structural_tracing_intent"


def test_selective_router_routes_multi_entity_interaction():
    analyzed = AnalyzedQuery(
        raw_query="How do AuthService and UserRepository interact?",
        keywords=["authservice", "userrepository", "interact"],
        symbol_candidates=["AuthService", "UserRepository"],
    )
    candidates = [_make_candidate(name="AuthService"), _make_candidate(name="UserRepository")]

    should_route, reason = StarRagSelectiveRouter.should_route_to_star_rag(
        query_text="How do AuthService and UserRepository interact?",
        analyzed_query=analyzed,
        candidates=candidates,
        flag_enabled=True,
    )

    assert should_route is True
    assert reason in ("structural_tracing_intent", "multi_entity_relational_intent")
