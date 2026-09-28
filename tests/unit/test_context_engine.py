import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import SymbolType
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.graph_expander import RelationshipExpander
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import (
    MultiSignalRetriever,
    RetrievedCandidate,
    compute_cosine_similarity,
)
from apps.api.src.services.llm.claude import ClaudeProvider


def test_multi_signal_ranker_prioritizes_exact_symbol_match():
    query = analyze_query("How does UserService work?")
    dummy_file_id = uuid.uuid4()

    cand1 = RetrievedCandidate(
        candidate_id="sym:1",
        entity_type="SYMBOL",
        name="UserService",
        path="src/services/user.ts",
        start_line=10,
        end_line=50,
        content="class UserService {\n  findUser() {}\n}",
        file_id=dummy_file_id,
        signals={"symbol_match": 1.2},
    )

    cand2 = RetrievedCandidate(
        candidate_id="file:2",
        entity_type="FILE",
        name="user.ts",
        path="src/services/user.ts",
        start_line=1,
        end_line=60,
        content="// File content",
        file_id=dummy_file_id,
        signals={"file_match": 0.7},
    )

    ranked = MultiSignalRanker.rank_candidates([cand2, cand1], query)

    assert len(ranked) == 2
    # Exact symbol candidate should be ranked first with highest score
    assert ranked[0].candidate.name == "UserService"
    assert ranked[0].score >= ranked[1].score


def test_context_assembler_respects_budget():
    dummy_file_id = uuid.uuid4()
    query = analyze_query("search")

    candidates = [
        RetrievedCandidate(
            candidate_id=f"chunk:{i}",
            entity_type="CHUNK",
            name=f"Function_{i}",
            path=f"src/file_{i}.ts",
            start_line=1,
            end_line=20,
            content=f"function body {i} " * 50,
            file_id=dummy_file_id,
            signals={"content_match": 0.8},
        )
        for i in range(20)
    ]

    ranked = MultiSignalRanker.rank_candidates(candidates, query)
    # Set a tiny max_tokens budget (e.g. 50 tokens ~ 200 chars)
    assembled = ContextAssembler.assemble_context(ranked, max_tokens=50)

    assert assembled.candidate_count >= 3  # Minimum floor guarantee
    assert len(assembled.evidence_items) >= 3
    assert len(assembled.related_entities) >= 3


def test_compute_cosine_similarity():
    assert compute_cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert compute_cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert compute_cosine_similarity([], []) == 0.0
    assert compute_cosine_similarity([1.0, 2.0], [1.0]) == 0.0


@pytest.mark.asyncio
async def test_multi_signal_retriever_vector_similarity():
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_chunk = CodeChunk(
        id=chunk_id,
        snapshot_id=snapshot_id,
        file_id=file_id,
        name="login_handler",
        path="src/auth.py",
        content="def login_handler(): pass",
        start_line=1,
        end_line=5,
        embedding=[0.9, 0.1, 0.0],
    )

    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "embedding" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [mock_chunk]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    analyzed = analyze_query("authentication")
    candidates = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=snapshot_id,
        analyzed_query=analyzed,
        query_embedding=[0.9, 0.1, 0.0],
    )

    vec_cands = [c for c in candidates if "vector_similarity" in c.signals]
    assert len(vec_cands) >= 1
    assert vec_cands[0].signals["vector_similarity"] == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_relationship_expander_inbound_and_outbound_resolution():
    snapshot_id = uuid.uuid4()
    seed_file_id = uuid.uuid4()
    target_file_id = uuid.uuid4()
    caller_file_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id=f"file:{seed_file_id}",
        entity_type="FILE",
        name="auth_service.py",
        path="src/auth_service.py",
        start_line=1,
        end_line=100,
        content="// AuthService",
        file_id=seed_file_id,
    )

    file_seed = RepositoryFile(
        id=seed_file_id,
        snapshot_id=snapshot_id,
        path="src/auth_service.py",
        filename="auth_service.py",
        line_count=100,
    )
    file_target = RepositoryFile(
        id=target_file_id,
        snapshot_id=snapshot_id,
        path="src/models/user.py",
        filename="user.py",
        line_count=50,
    )
    file_caller = RepositoryFile(
        id=caller_file_id,
        snapshot_id=snapshot_id,
        path="src/api/auth_routes.py",
        filename="auth_routes.py",
        line_count=80,
    )

    outbound_dep = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=seed_file_id,
        target_file_id=target_file_id,
        line_number=5,
    )
    inbound_dep = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=caller_file_id,
        target_file_id=seed_file_id,
        line_number=12,
    )

    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "code_symbols" in stmt_str:
            mock_res.all.return_value = []
        elif "code_dependencies" in stmt_str and "code_dependencies.target_file_id" in stmt_str:
            # Hop 1 dependency query
            mock_res.all.return_value = [
                (outbound_dep, file_seed, file_target),
                (inbound_dep, file_caller, file_seed),
            ]
        elif "code_dependencies" in stmt_str:
            # Hop 2 dependency query
            mock_res.all.return_value = []
        else:
            mock_res.scalars.return_value.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=2,
    )

    dep_cands = [c for c in expanded if c.entity_type == "DEPENDENCY"]
    assert len(dep_cands) >= 2

    outbound_cands = [c for c in dep_cands if "Outbound" in c.content]
    inbound_cands = [c for c in dep_cands if "Inbound" in c.content]

    assert len(outbound_cands) == 1
    assert "src/auth_service.py -> src/models/user.py" in outbound_cands[0].content

    assert len(inbound_cands) == 1
    assert "src/api/auth_routes.py imports src/auth_service.py" in inbound_cands[0].content

    # Check that connected files were added to expanded candidates
    file_cands = [c for c in expanded if c.entity_type == "FILE"]
    paths = {c.path for c in file_cands}
    assert "src/models/user.py" in paths
    assert "src/api/auth_routes.py" in paths


@pytest.mark.asyncio
async def test_relationship_expander_2_hop_traversal():
    snapshot_id = uuid.uuid4()
    seed_file_id = uuid.uuid4()
    hop1_file_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id=f"file:{seed_file_id}",
        entity_type="FILE",
        name="main.py",
        path="src/main.py",
        start_line=1,
        end_line=20,
        content="// Main",
        file_id=seed_file_id,
    )

    file_seed = RepositoryFile(
        id=seed_file_id,
        snapshot_id=snapshot_id,
        path="src/main.py",
        filename="main.py",
    )
    file_hop1 = RepositoryFile(
        id=hop1_file_id,
        snapshot_id=snapshot_id,
        path="src/service.py",
        filename="service.py",
    )

    dep_hop1 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=seed_file_id,
        target_file_id=hop1_file_id,
        line_number=3,
    )

    hop2_symbol = CodeSymbol(
        id=uuid.uuid4(),
        file_id=hop1_file_id,
        name="do_work",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="service.do_work",
        start_line=10,
        end_line=20,
    )

    session = AsyncMock()
    symbol_query_count = 0

    def execute_side_effect(stmt):
        nonlocal symbol_query_count
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "code_symbols" in stmt_str:
            symbol_query_count += 1
            if symbol_query_count == 1:
                # Hop 1 symbols for seed
                mock_res.all.return_value = []
            else:
                # Hop 2 symbols for connected hop1 file
                mock_res.all.return_value = [(hop2_symbol, file_hop1)]
        elif "code_dependencies" in stmt_str and "code_dependencies.target_file_id" in stmt_str:
            # Hop 1 dependencies
            mock_res.all.return_value = [(dep_hop1, file_seed, file_hop1)]
        elif "code_dependencies" in stmt_str:
            # Hop 2 dependencies
            mock_res.all.return_value = []
        else:
            mock_res.scalars.return_value.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=2,
    )

    # Verify that hop 2 symbol was discovered
    hop2_cands = [c for c in expanded if "graph_expansion_hop2" in c.signals]
    assert len(hop2_cands) >= 1
    assert any(c.name == "do_work" for c in hop2_cands)


def test_multi_signal_ranker_incorporates_vector_and_semantic_signals():
    query = analyze_query("authentication")
    file_id = uuid.uuid4()

    cand_vector = RetrievedCandidate(
        candidate_id="chunk:v",
        entity_type="CHUNK",
        name="auth_check",
        path="src/auth.py",
        start_line=1,
        end_line=10,
        content="def auth_check(): return True",
        file_id=file_id,
        signals={"vector_similarity": 0.95, "semantic_match": 0.95},
    )

    cand_plain = RetrievedCandidate(
        candidate_id="chunk:p",
        entity_type="CHUNK",
        name="random_code",
        path="src/other.py",
        start_line=1,
        end_line=10,
        content="x = 1",
        file_id=file_id,
        signals={"content_match": 0.2},
    )

    ranked = MultiSignalRanker.rank_candidates([cand_plain, cand_vector], query)
    assert ranked[0].candidate.candidate_id == "chunk:v"
    assert any("Vector semantic similarity" in r for r in ranked[0].matched_reasons)


@pytest.mark.asyncio
async def test_claude_provider_offline_fallback():
    provider = ClaudeProvider(api_key=None)

    evidence = [
        {
            "type": "symbol",
            "file": "src/auth/service.py",
            "symbol": "AuthService",
            "lines": "10-45",
            "relevance": 0.95,
            "snippet": "class AuthService: pass",
        }
    ]

    answer = await provider.generate_grounded_answer(
        question="How does authentication work?",
        project_context="### [SYMBOL] src/auth/service.py\nclass AuthService: pass",
        evidence_items=evidence,
        related_entities=["AuthService"],
    )

    assert answer.confidence == "HIGH"
    assert "AuthService" in answer.content
    assert "src/auth/service.py" in answer.content
    assert len(answer.evidence) == 1
