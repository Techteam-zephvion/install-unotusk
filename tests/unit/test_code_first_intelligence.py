import uuid

from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


def test_code_first_ranker_boosts_ast_code_over_readme():
    """
    Verifies that when asking a technical implementation question,
    actual source code AST symbols are boosted while README.md is demoted.
    """
    file_id = uuid.uuid4()

    # Candidate 1: README.md file chunk containing high-level textual descriptions
    readme_candidate = RetrievedCandidate(
        candidate_id="readme_chunk",
        entity_type="CHUNK",
        file_id=file_id,
        path="README.md",
        name="Project Overview",
        content="# Payment Processing System\nThis project handles billing and customer payments through stripe gateways.",
        start_line=1,
        end_line=25,
        signals={"file_match": 1.0, "content_match": 1.0},
        metadata={"chunk_type": "MARKDOWN"},
    )

    # Candidate 2: Actual source code class definition in Python
    code_candidate = RetrievedCandidate(
        candidate_id="code_chunk",
        entity_type="CHUNK",
        file_id=file_id,
        path="src/billing/gateway.py",
        name="PaymentGateway",
        content="class PaymentGateway:\n    def process_charge(self, customer_id: str, amount: int):\n        return self.client.charge(customer_id, amount)",
        start_line=10,
        end_line=30,
        symbol_id=uuid.uuid4(),
        signals={"symbol_match": 1.0, "content_match": 0.8},
        metadata={"chunk_type": "CLASS"},
    )

    # Query asking how payment processing is implemented
    query = AnalyzedQuery(
        raw_query="How does payment processing work and what methods are implemented?",
        keywords=["payment", "processing", "methods", "implemented"],
        symbol_candidates=["PaymentGateway"],
        concept_keywords=["payment", "billing"],
    )

    ranked = MultiSignalRanker.rank_candidates([readme_candidate, code_candidate], query)

    assert len(ranked) == 2
    # The code candidate must outrank the README candidate
    assert ranked[0].candidate.candidate_id == "code_chunk"
    assert "AST code definition boost (CLASS)" in ranked[0].matched_reasons

    # The README candidate must have the demotion reason
    readme_ranked = next(r for r in ranked if r.candidate.candidate_id == "readme_chunk")
    assert any("demoted" in reason.lower() for reason in readme_ranked.matched_reasons)
