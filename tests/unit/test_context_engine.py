import uuid

import pytest

from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
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
