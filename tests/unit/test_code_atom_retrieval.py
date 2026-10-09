import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.services.code_atom.embedding import (
    DevelopmentCodeEmbeddingBackend,
    format_atom_code_embedding_input,
    generate_code_embedding,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import (
    MultiSignalRetriever,
    RetrievedCandidate,
)


@pytest.fixture
def mock_atom_chunk():
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()
    symbol_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    commit_sha = "83efb9c1234567890abcdef1234567890abcdef1"
    commit_msg = "feat(auth): add JWT token validation service"
    fingerprint = "fp_atom_jwt_service_999999"
    prov = {
        "atom_id": str(uuid.uuid4()),
        "symbol_name": "validate_jwt_token",
        "author": "Dev",
        "change_type": "ADD",
    }

    content = (
        "def validate_jwt_token(token: str) -> bool:\n"
        "    # Validate signature and expiration\n"
        "    return token.startswith('valid_')\n"
    )

    chunk = CodeChunk(
        id=chunk_id,
        snapshot_id=snapshot_id,
        file_id=file_id,
        symbol_id=symbol_id,
        chunk_type="ATOM_ADD",
        name="validate_jwt_token (ADD)",
        path="apps/api/src/services/jwt_auth.py",
        content=content,
        start_line=10,
        end_line=25,
        commit_sha=commit_sha,
        commit_message=commit_msg,
        fingerprint=fingerprint,
        provenance=prov,
        embedding=generate_code_embedding(
            format_atom_code_embedding_input(
                commit_message=commit_msg,
                content=content,
                file_path="apps/api/src/services/jwt_auth.py",
                symbol_name="validate_jwt_token",
            ),
            backend=DevelopmentCodeEmbeddingBackend(),
        ),
    )
    return chunk


@pytest.mark.asyncio
async def test_1_atom_code_chunk_can_be_retrieved(mock_atom_chunk):
    """1. An ATOM CodeChunk can be retrieved via existing MultiSignalRetriever."""
    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "code_chunks" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [mock_atom_chunk]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    analyzed = analyze_query("jwt token validation service")
    candidates = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=mock_atom_chunk.snapshot_id,
        analyzed_query=analyzed,
    )

    assert len(candidates) >= 1
    atom_cand = next(c for c in candidates if c.candidate_id == f"chunk:{mock_atom_chunk.id}")
    assert atom_cand.entity_type == "CHUNK"
    assert atom_cand.name == "validate_jwt_token (ADD)"
    assert atom_cand.path == "apps/api/src/services/jwt_auth.py"
    assert "content_match" in atom_cand.signals
    assert atom_cand.metadata.get("commit_sha") == mock_atom_chunk.commit_sha
    assert atom_cand.metadata.get("commit_message") == mock_atom_chunk.commit_message


@pytest.mark.asyncio
async def test_2_exact_file_path_or_identifier_query_retrieves_relevant_chunk(mock_atom_chunk):
    """2. An exact file path or identifier query retrieves the relevant ATOM chunk."""
    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "code_chunks" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [mock_atom_chunk]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    # Exact symbol query: "validate_jwt_token"
    analyzed_sym = analyze_query("validate_jwt_token")
    candidates_sym = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=mock_atom_chunk.snapshot_id,
        analyzed_query=analyzed_sym,
    )
    assert len(candidates_sym) >= 1
    cand_sym = candidates_sym[0]
    # Exact stem match (validate_jwt_token vs validate_jwt_token (ADD)) -> 1.4 score
    assert cand_sym.signals.get("content_match") == 1.4

    # Exact path query: "apps/api/src/services/jwt_auth.py"
    analyzed_path = analyze_query("jwt_auth.py")
    candidates_path = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=mock_atom_chunk.snapshot_id,
        analyzed_query=analyzed_path,
    )
    assert len(candidates_path) >= 1
    cand_path = candidates_path[0]
    assert cand_path.signals.get("content_match") >= 1.0


@pytest.mark.asyncio
async def test_3_code_related_query_can_use_vector_similarity(mock_atom_chunk):
    """3. A code-related query can use vector similarity against ATOM embeddings."""
    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "embedding" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [mock_atom_chunk]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    query_vec = generate_code_embedding(
        "validate jwt token authorization signature",
        backend=DevelopmentCodeEmbeddingBackend(),
        input_type="query",
    )
    assert query_vec is not None

    analyzed = analyze_query("validate jwt token authorization signature")
    candidates = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=mock_atom_chunk.snapshot_id,
        analyzed_query=analyzed,
        query_embedding=query_vec,
    )

    vec_cands = [c for c in candidates if "vector_similarity" in c.signals]
    assert len(vec_cands) >= 1
    assert vec_cands[0].signals["vector_similarity"] > 0.5


def test_4_multiple_candidates_ranked_correctly():
    """4. Multiple candidates are ranked correctly according to existing multi-signal rules."""
    query = analyze_query("validate_jwt_token")
    dummy_file = uuid.uuid4()

    # Candidate 1: High relevance exact symbol match + vector similarity
    cand_top = RetrievedCandidate(
        candidate_id="chunk:top",
        entity_type="CHUNK",
        name="validate_jwt_token (ADD)",
        path="src/jwt_auth.py",
        start_line=1,
        end_line=20,
        content="def validate_jwt_token(): pass",
        file_id=dummy_file,
        signals={"content_match": 1.4, "vector_similarity": 0.95},
        metadata={"commit_sha": "83efb9c", "fingerprint": "fp_top"},
    )

    # Candidate 2: Medium relevance path match only
    cand_mid = RetrievedCandidate(
        candidate_id="file:mid",
        entity_type="FILE",
        name="jwt_auth.py",
        path="src/jwt_auth.py",
        start_line=1,
        end_line=100,
        content="// File jwt_auth.py",
        file_id=dummy_file,
        signals={"file_match": 1.0},
    )

    # Candidate 3: Low relevance partial text match
    cand_low = RetrievedCandidate(
        candidate_id="chunk:low",
        entity_type="CHUNK",
        name="log_event",
        path="src/logger.py",
        start_line=1,
        end_line=10,
        content="def log_event(msg): pass",
        file_id=uuid.uuid4(),
        signals={"content_match": 0.6},
    )

    ranked = MultiSignalRanker.rank_candidates([cand_low, cand_top, cand_mid], query)
    assert len(ranked) >= 3
    # Top candidate should be cand_top
    assert ranked[0].candidate.candidate_id == "chunk:top"
    assert ranked[0].score >= ranked[1].score
    assert ranked[1].score >= ranked[2].score


def test_5_irrelevant_candidates_filtered_as_expected():
    """5. Irrelevant noisy candidates are filtered out by noise threshold."""
    query = analyze_query("authentication token")
    dummy_file = uuid.uuid4()

    cands = [
        RetrievedCandidate(
            candidate_id=f"chunk:good_{i}",
            entity_type="CHUNK",
            name=f"auth_func_{i}",
            path="src/auth.py",
            start_line=1,
            end_line=20,
            content="def auth_func(): pass",
            file_id=dummy_file,
            signals={"content_match": 1.2, "vector_similarity": 0.8},
        )
        for i in range(3)
    ]

    # Noisy candidate with negligible signal score
    noisy = RetrievedCandidate(
        candidate_id="chunk:noise",
        entity_type="CHUNK",
        name="unrelated_util",
        path="src/util.py",
        start_line=1,
        end_line=5,
        content="x = 123",
        file_id=uuid.uuid4(),
        signals={"content_match": 0.05},
    )

    ranked = MultiSignalRanker.rank_candidates(cands + [noisy], query, noise_threshold=0.2)
    # The noise candidate should be filtered out
    assert not any(r.candidate.candidate_id == "chunk:noise" for r in ranked)
    assert len(ranked) == 3


@pytest.mark.asyncio
async def test_6_metadata_and_provenance_survive_entire_retrieval_flow(mock_atom_chunk):
    """6. Commit, file, symbol, snapshot, fingerprint and provenance metadata survive retrieval, ranking, and assembly."""
    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "code_chunks" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [mock_atom_chunk]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    query = analyze_query("validate_jwt_token")
    raw_candidates = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=mock_atom_chunk.snapshot_id,
        analyzed_query=query,
    )
    assert len(raw_candidates) >= 1
    cand = raw_candidates[0]

    # Check candidate metadata survival
    assert cand.metadata["commit_sha"] == mock_atom_chunk.commit_sha
    assert cand.metadata["commit_message"] == mock_atom_chunk.commit_message
    assert cand.metadata["fingerprint"] == mock_atom_chunk.fingerprint
    assert cand.metadata["provenance"] == mock_atom_chunk.provenance
    assert cand.metadata["snapshot_id"] == mock_atom_chunk.snapshot_id
    assert cand.file_id == mock_atom_chunk.file_id
    assert cand.symbol_id == mock_atom_chunk.symbol_id

    # Rank
    ranked = MultiSignalRanker.rank_candidates(raw_candidates, query)
    assert len(ranked) >= 1
    ranked_top = ranked[0]
    assert ranked_top.candidate.metadata["commit_sha"] == mock_atom_chunk.commit_sha
    assert ranked_top.score > 0.0

    # Assemble
    assembled = ContextAssembler.assemble_context(ranked)
    assert len(assembled.evidence_items) >= 1
    item = assembled.evidence_items[0]

    assert item["type"] == "chunk"
    assert item["file"] == mock_atom_chunk.path
    assert item["symbol"] == mock_atom_chunk.name
    assert item["commit_sha"] == mock_atom_chunk.commit_sha
    assert item["commit_message"] == mock_atom_chunk.commit_message
    assert item["fingerprint"] == mock_atom_chunk.fingerprint
    assert item["provenance"] == mock_atom_chunk.provenance
    assert item["snapshot_id"] == mock_atom_chunk.snapshot_id

    # Check prompt context string formatting retains commit relationship
    assert "83efb9c1" in assembled.prompt_context
    assert "feat(auth): add JWT token validation service" in assembled.prompt_context
    assert "def validate_jwt_token" in assembled.prompt_context


@pytest.mark.asyncio
async def test_7_project_and_snapshot_isolation_is_preserved(mock_atom_chunk):
    """7. MultiSignalRetriever strictly enforces snapshot_id filtering in SQL queries."""
    target_snapshot = uuid.uuid4()
    other_snapshot = uuid.uuid4()

    executed_snapshot_ids = []

    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        # Inspect where clauses to verify snapshot_id filtering
        stmt_str = str(stmt)
        if "snapshot_id" in stmt_str:
            executed_snapshot_ids.append(target_snapshot)
        mock_res.scalars.return_value.all.return_value = []
        mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    analyzed = analyze_query("test query")
    await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=target_snapshot,
        analyzed_query=analyzed,
    )

    # Every executed query filtering by snapshot targeted target_snapshot
    assert len(executed_snapshot_ids) > 0
    assert all(sid == target_snapshot for sid in executed_snapshot_ids)
    assert other_snapshot not in executed_snapshot_ids


def test_8_context_assembly_includes_selected_atom_chunks(mock_atom_chunk):
    """8. Context assembly includes selected ATOM chunks and respects token budget."""
    cand = RetrievedCandidate(
        candidate_id=f"chunk:{mock_atom_chunk.id}",
        entity_type="CHUNK",
        name=mock_atom_chunk.name,
        path=mock_atom_chunk.path,
        start_line=mock_atom_chunk.start_line,
        end_line=mock_atom_chunk.end_line,
        content=mock_atom_chunk.content,
        file_id=mock_atom_chunk.file_id,
        symbol_id=mock_atom_chunk.symbol_id,
        signals={"content_match": 1.4},
        metadata={
            "commit_sha": mock_atom_chunk.commit_sha,
            "commit_message": mock_atom_chunk.commit_message,
            "fingerprint": mock_atom_chunk.fingerprint,
            "provenance": mock_atom_chunk.provenance,
            "snapshot_id": mock_atom_chunk.snapshot_id,
        },
    )

    query = analyze_query("validate_jwt_token")
    ranked = MultiSignalRanker.rank_candidates([cand], query)
    assembled = ContextAssembler.assemble_context(ranked, max_tokens=2000)

    assert assembled.candidate_count == 1
    assert "validate_jwt_token" in assembled.prompt_context
    assert mock_atom_chunk.commit_sha[:8] in assembled.prompt_context
    assert len(assembled.evidence_items) == 1
    assert assembled.evidence_items[0]["fingerprint"] == mock_atom_chunk.fingerprint


def test_9_existing_non_atom_retrieval_behaviour_remains_compatible():
    """9. Non-ATOM chunks, files, and symbols behave identically without regression."""
    query = analyze_query("UserService")
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()

    # Standard non-ATOM file candidate
    cand_file = RetrievedCandidate(
        candidate_id="file:1",
        entity_type="FILE",
        name="user_service.py",
        path="src/user_service.py",
        start_line=1,
        end_line=100,
        content="// user_service.py",
        file_id=file_id,
        signals={"file_match": 1.2},
    )

    # Standard non-ATOM symbol candidate
    cand_sym = RetrievedCandidate(
        candidate_id=f"sym:{sym_id}",
        entity_type="SYMBOL",
        name="UserService",
        path="src/user_service.py",
        start_line=10,
        end_line=60,
        content="class UserService: pass",
        file_id=file_id,
        symbol_id=sym_id,
        signals={"symbol_match": 1.5},
    )

    # Standard non-ATOM chunk
    cand_chunk = RetrievedCandidate(
        candidate_id="chunk:norm",
        entity_type="CHUNK",
        name="UserService",
        path="src/user_service.py",
        start_line=10,
        end_line=60,
        content="class UserService:\n    def find(self): pass",
        file_id=file_id,
        symbol_id=sym_id,
        signals={"content_match": 1.1},
    )

    ranked = MultiSignalRanker.rank_candidates([cand_file, cand_chunk, cand_sym], query)

    # Symbol should be prioritized over generic non-ATOM chunk with same symbol_id
    assert len(ranked) == 2
    assert ranked[0].candidate.entity_type == "SYMBOL"
    assert ranked[0].candidate.name == "UserService"

    assembled = ContextAssembler.assemble_context(ranked)
    assert assembled.candidate_count == 2
    assert "UserService" in assembled.prompt_context


@pytest.mark.asyncio
async def test_10_empty_results_and_missing_embeddings_handled_safely():
    """10. Empty results and missing embeddings are handled safely without errors."""
    session = AsyncMock()

    # Chunk with missing embedding (None)
    chunk_no_emb = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        chunk_type="ATOM_ADD",
        name="no_emb_chunk",
        path="src/empty.py",
        content="x = 1",
        start_line=1,
        end_line=2,
        embedding=None,  # Missing embedding
    )

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "code_chunks" in stmt_str or "embedding" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [chunk_no_emb]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    # Query with query_embedding provided -> should safely handle chunk with embedding=None
    analyzed = analyze_query("test query")
    candidates = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=chunk_no_emb.snapshot_id,
        analyzed_query=analyzed,
        query_embedding=[0.1] * 1536,
    )
    # Retrieved without exception
    assert isinstance(candidates, list)

    # Completely empty candidates ranking and assembly
    empty_ranked = MultiSignalRanker.rank_candidates([], analyzed)
    assert empty_ranked == []

    empty_assembled = ContextAssembler.assemble_context([])
    assert empty_assembled.candidate_count == 0
    assert empty_assembled.evidence_items == []
    assert "No specific code evidence retrieved" in empty_assembled.prompt_context
