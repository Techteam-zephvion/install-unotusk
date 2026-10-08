import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.src.db.base import Base
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.code_atom import (
    AtomicCodeChange,
    GitCommitArtifact,
)
from apps.api.src.services.code_atom.chunk_mapper import (
    map_atomic_code_change_to_code_chunk,
    resolve_and_map_atomic_changes,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.code_atom.embedding import (
    embed_atomic_code_chunk,
    format_atom_code_embedding_input,
    generate_atom_code_embedding,
)
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.retriever import (
    MultiSignalRetriever,
    compute_cosine_similarity,
    generate_text_embedding,
)

SAMPLE_DIFF = """diff --git a/src/auth/service.py b/src/auth/service.py
index 1111111..2222222 100644
--- a/src/auth/service.py
+++ b/src/auth/service.py
@@ -10,4 +10,6 @@ def verify_session(session_id: str) -> bool:
     if not session_id:
         return False
+    if session_id.startswith("test_override_"):
+        return True
     return session_store.check(session_id)
"""


def _create_sample_atomic_change(
    commit_sha: str = "abc1234567890abcdef1234567890abcdef123456",
    commit_msg: str = "feat(auth): add test override for session verification",
    symbol_name: str = "verify_session",
) -> AtomicCodeChange:
    decomposer = CodeAtomDecomposer()
    catalog = [
        {
            "id": uuid.uuid4(),
            "name": symbol_name,
            "symbol_type": "FUNCTION",
            "file_path": "src/auth/service.py",
            "start_line": 10,
            "end_line": 20,
        }
    ]
    commit = GitCommitArtifact(
        commit_sha=commit_sha,
        commit_message=commit_msg,
        raw_diff=SAMPLE_DIFF,
    )
    res = decomposer.decompose(commit, symbol_catalog=catalog)
    return res.changes[0]


def test_1_atom_code_chunk_gets_an_embedding():
    """1. ATOM CodeChunk gets an embedding when mapped with compute_embedding=True."""
    change = _create_sample_atomic_change()
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=True,
    )

    assert chunk.embedding is not None
    assert isinstance(chunk.embedding, list)
    assert len(chunk.embedding) > 0


def test_2_correct_embedding_dimension():
    """2. Correct embedding dimension: exactly 1536 elements and normalized."""
    change = _create_sample_atomic_change()
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=True,
    )

    assert len(chunk.embedding) == 1536
    # Verify L2 normalization: sum(x^2) ≈ 1.0
    norm = sum(x * x for x in chunk.embedding) ** 0.5
    assert norm == pytest.approx(1.0, rel=1e-3)


@pytest.mark.asyncio
async def test_3_embedding_persistence():
    """3. Embedding persistence: persists successfully into CodeChunk with CompatibleVector."""
    # Use SQLite in-memory engine where CompatibleVector falls back cleanly to JSON
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn,
                tables=[
                    RepositorySnapshot.__table__,
                    RepositoryFile.__table__,
                    CodeChunk.__table__,
                ],
            )
        )

    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    change = _create_sample_atomic_change()
    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=True,
    )

    async with session_factory() as session:
        snap = RepositorySnapshot(id=snap_id, repository_id=repo_id, commit_sha="abc1234")
        rf = RepositoryFile(
            id=file_id,
            snapshot_id=snap_id,
            path="src/auth/service.py",
            filename="service.py",
            extension=".py",
            content_hash="hash1",
        )
        session.add_all([snap, rf, chunk])
        await session.commit()

    # Re-read chunk in a fresh session and verify embedding vector persisted
    async with session_factory() as session:
        reloaded = await session.get(CodeChunk, chunk.id)
        assert reloaded is not None
        assert reloaded.embedding is not None
        assert len(reloaded.embedding) == 1536
        assert reloaded.embedding[0] == pytest.approx(chunk.embedding[0], abs=1e-5)
        assert reloaded.commit_sha == change.commit_sha
        assert reloaded.fingerprint == change.fingerprint

    await engine.dispose()


def test_4_commit_and_code_change_context_included_in_embedding_input():
    """4. Commit + code-change context is included in embedding input while chunk content is unchanged."""
    change = _create_sample_atomic_change(
        commit_msg="security(session): enforce verification override tokens",
        symbol_name="verify_session",
    )
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=True,
    )

    # Embedding input representation contains commit message, file path, symbol, and diff
    emb_text = format_atom_code_embedding_input(
        commit_message=change.commit_message,
        content=change.raw_content,
        file_path=change.file_path,
        symbol_name=change.symbol_name,
    )

    assert "security(session): enforce verification override tokens" in emb_text
    assert "File: src/auth/service.py" in emb_text
    assert "Symbol: verify_session" in emb_text
    assert "test_override_" in emb_text

    # Original CodeChunk content must remain untouched (exact raw diff content)
    assert chunk.content == change.raw_content
    assert chunk.content.startswith("@@")

    # Embedding input generation is strictly deterministic
    repeat_text = format_atom_code_embedding_input(
        commit_message=change.commit_message,
        content=change.raw_content,
        file_path=change.file_path,
        symbol_name=change.symbol_name,
    )
    assert emb_text == repeat_text


def test_5_fingerprint_unchanged():
    """5. Fingerprint remains completely unchanged before and after embedding generation."""
    change = _create_sample_atomic_change()
    initial_fp = change.fingerprint
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    # Map with compute_embedding=False
    chunk_no_emb = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=False,
    )
    assert chunk_no_emb.fingerprint == initial_fp

    # Map with compute_embedding=True
    chunk_with_emb = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=True,
    )
    assert chunk_with_emb.fingerprint == initial_fp

    # Post-hoc embed_atomic_code_chunk
    embed_atomic_code_chunk(chunk_no_emb)
    assert chunk_no_emb.fingerprint == initial_fp


def test_6_provenance_unchanged():
    """6. Full structured provenance is preserved and untouched by embedding."""
    change = _create_sample_atomic_change()
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=True,
    )

    assert chunk.provenance is not None
    assert chunk.provenance["commit_message"] == change.commit_message
    assert chunk.provenance["file_path"] == "src/auth/service.py"
    assert chunk.provenance["symbol_name"] == "verify_session"
    assert chunk.provenance["atom_id"] == change.id
    assert chunk.provenance["fingerprint"] == change.fingerprint
    assert chunk.commit_sha == change.commit_sha


@pytest.mark.asyncio
async def test_7_repeated_processing_is_safe_and_reuses_existing_chunks():
    """7. Repeated processing is safe, avoids redundant re-embedding, and does not duplicate chunks."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    change = _create_sample_atomic_change()
    files_map = {"src/auth/service.py": RepositoryFile(id=file_id, snapshot_id=snap_id, path="src/auth/service.py")}

    # First pass: map and generate embedding
    chunks_run1 = resolve_and_map_atomic_changes(
        changes=[change],
        snapshot_id=snap_id,
        files_map=files_map,
        compute_embedding=True,
    )
    assert len(chunks_run1) == 1
    first_chunk = chunks_run1[0]
    assert first_chunk.embedding is not None

    # Second pass: supply existing chunk map by fingerprint
    existing_map = {first_chunk.fingerprint: first_chunk}
    with patch(
        "apps.api.src.services.code_atom.chunk_mapper.generate_atom_code_embedding"
    ) as mock_gen_emb:
        chunks_run2 = resolve_and_map_atomic_changes(
            changes=[change],
            snapshot_id=snap_id,
            files_map=files_map,
            compute_embedding=True,
            existing_chunks_by_fingerprint=existing_map,
        )
        # Should reuse existing chunk and not call generate_atom_code_embedding again
        assert len(chunks_run2) == 1
        assert chunks_run2[0].id == first_chunk.id
        assert chunks_run2[0].embedding == first_chunk.embedding
        mock_gen_emb.assert_not_called()


def test_8_non_atom_code_chunks_remain_valid():
    """8. Non-ATOM traditional CodeChunks (e.g. AST symbol chunks with/without embedding) remain valid."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    # Traditional chunk without embedding (NULL)
    traditional_null_chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snap_id,
        file_id=file_id,
        chunk_type="FUNCTION",
        name="legacy_function",
        path="src/legacy.py",
        content="def legacy_function(): pass",
        start_line=1,
        end_line=5,
        embedding=None,
    )
    assert traditional_null_chunk.embedding is None
    assert traditional_null_chunk.commit_sha is None
    assert traditional_null_chunk.fingerprint is None

    # Traditional chunk with AST symbol embedding
    sym_emb = generate_text_embedding("def legacy_function(): pass")
    traditional_emb_chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snap_id,
        file_id=file_id,
        chunk_type="CLASS",
        name="LegacyClass",
        path="src/legacy.py",
        content="class LegacyClass: pass",
        start_line=10,
        end_line=20,
        embedding=sym_emb,
    )
    assert len(traditional_emb_chunk.embedding) == 1536
    assert traditional_emb_chunk.commit_sha is None


def test_9_query_and_stored_vector_dimensions_match():
    """9. Query and stored ATOM vector dimensions match (both 1536) and compute_cosine_similarity works."""
    query = "session verification override token"
    query_vector = generate_text_embedding(query)
    assert len(query_vector) == 1536

    atom_vector = generate_atom_code_embedding(
        commit_message="feat: allow session verification override token",
        content="+ if token.startswith('override'): return True",
        file_path="src/auth/service.py",
        symbol_name="verify_session",
    )
    assert atom_vector is not None
    assert len(atom_vector) == 1536

    sim = compute_cosine_similarity(query_vector, atom_vector)
    assert isinstance(sim, float)
    assert sim > 0.3  # High semantic relevance due to overlapping concepts


@pytest.mark.asyncio
async def test_10_existing_vector_retrieval_still_works_with_atom_chunks():
    """10. Existing vector retrieval still works with ATOM chunks and candidates retain ATOM metadata."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    change = _create_sample_atomic_change(
        commit_msg="security: fix session validation override loophole",
        symbol_name="verify_session",
    )
    atom_chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=True,
    )

    mock_session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "embedding" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [atom_chunk]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    mock_session.execute.side_effect = execute_side_effect

    # Query matching the commit intent
    analyzed = analyze_query("session verification override")
    candidates = await MultiSignalRetriever.retrieve_candidates(
        session=mock_session,
        snapshot_id=snap_id,
        analyzed_query=analyzed,
    )

    # Candidate should be retrieved via vector search
    vec_cands = [c for c in candidates if "vector_similarity" in c.signals]
    assert len(vec_cands) >= 1
    cand = vec_cands[0]
    assert cand.signals["vector_similarity"] > 0.2

    # Retrieved candidate must retain ATOM metadata and provenance
    assert cand.metadata["commit_sha"] == change.commit_sha
    assert cand.metadata["commit_message"] == change.commit_message
    assert cand.metadata["fingerprint"] == change.fingerprint
    assert cand.metadata["chunk_type"] == "ATOM_MODIFY"
    assert cand.metadata["provenance"]["symbol_name"] == "verify_session"


def test_11_embedding_failure_does_not_corrupt_metadata():
    """11. Embedding generation failure does not corrupt CodeChunk metadata or fail mapping."""
    change = _create_sample_atomic_change()
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    # Simulate unexpected embedding failure
    with patch(
        "apps.api.src.services.code_atom.chunk_mapper.generate_atom_code_embedding",
        side_effect=RuntimeError("Vector computation service failure"),
    ):
        chunk = map_atomic_code_change_to_code_chunk(
            change=change,
            snapshot_id=snap_id,
            file_id=file_id,
            compute_embedding=True,
        )

        # Embedding safely falls back to None without throwing exception
        assert chunk.embedding is None
        # All metadata remains completely uncorrupted
        assert chunk.id is not None
        assert chunk.snapshot_id == snap_id
        assert chunk.file_id == file_id
        assert chunk.commit_sha == change.commit_sha
        assert chunk.commit_message == change.commit_message
        assert chunk.fingerprint == change.fingerprint
        assert chunk.provenance["atom_id"] == change.id
        assert chunk.chunk_type == "ATOM_MODIFY"
        assert chunk.content == change.raw_content


def test_12_code_embedding_interface_independence():
    """12. Clean, provider-independent Code-Lane embedding interface generates 1536-dim vector."""
    from apps.api.src.services.code_atom.embedding import (
        DevelopmentCodeEmbeddingBackend,
        generate_code_embedding,
    )

    dev_backend = DevelopmentCodeEmbeddingBackend()
    assert dev_backend.provider_name == "development"
    assert dev_backend.model_name == "deterministic-synthesizer-1536"
    assert dev_backend.dimension == 1536

    vec = generate_code_embedding("def calculate_total(): pass", backend=dev_backend)
    assert vec is not None
    assert len(vec) == 1536


def test_13_production_voyage_backend_configuration_and_mocked_call():
    """13. VoyageCodeEmbeddingBackend integrates properly, validates dimension (1536), and handles errors."""
    from apps.api.src.services.code_atom.embedding import (
        VoyageCodeEmbeddingBackend,
        generate_code_embedding,
    )

    voyage_backend = VoyageCodeEmbeddingBackend(api_key="va-test-key-12345", model="voyage-code-2")
    assert voyage_backend.provider_name == "voyage"
    assert voyage_backend.model_name == "voyage-code-2"
    assert voyage_backend.dimension == 1536

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "object": "list",
        "data": [{"embedding": [0.05] * 1536, "index": 0}],
        "model": "voyage-code-2",
    }

    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        vec = generate_code_embedding(
            "class AuthenticationService: pass",
            backend=voyage_backend,
            input_type="document",
        )
        assert vec is not None
        assert len(vec) == 1536
        assert vec[0] == 0.05
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["model"] == "voyage-code-2"
        assert call_kwargs["json"]["input_type"] == "document"
        assert "Bearer va-test-key-12345" in call_kwargs["headers"]["Authorization"]

    # Verify dimension mismatch rejection
    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {
        "object": "list",
        "data": [{"embedding": [0.05] * 512, "index": 0}],
    }
    with patch("httpx.Client.post", return_value=bad_resp):
        vec_bad = generate_code_embedding("test", backend=voyage_backend)
        assert vec_bad is None


def test_14_development_fallback_when_credentials_unavailable():
    """14. get_code_embedding_backend falls back cleanly to development when credentials missing."""
    from apps.api.src.services.code_atom.embedding import (
        DevelopmentCodeEmbeddingBackend,
        get_code_embedding_backend,
    )

    with patch.dict("os.environ", {}, clear=True), patch("apps.api.src.config.settings.settings.VOYAGE_API_KEY", None):
        backend = get_code_embedding_backend()
        assert isinstance(backend, DevelopmentCodeEmbeddingBackend)
        assert backend.provider_name == "development"


@pytest.mark.asyncio
async def test_15_reembed_atom_code_chunks_preserves_metadata():
    """15. reembed_atom_code_chunks updates only embedding and strictly preserves all metadata."""
    from apps.api.src.services.code_atom.embedding import reembed_atom_code_chunks

    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    change = _create_sample_atomic_change(
        commit_msg="refactor(auth): token cleanup",
        symbol_name="verify_session",
    )

    # Initial chunk with old / dummy embedding
    atom_chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=False,
    )
    atom_chunk.embedding = [0.01] * 1536

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [atom_chunk]
    mock_session.execute.return_value = mock_res

    reembedded_count = await reembed_atom_code_chunks(
        session=mock_session,
        snapshot_id=snap_id,
    )

    assert reembedded_count == 1
    # Embedding was updated with fresh 1536-dim vector
    assert len(atom_chunk.embedding) == 1536
    assert atom_chunk.embedding[0] != 0.01
    # All metadata strictly preserved
    assert atom_chunk.commit_sha == change.commit_sha
    assert atom_chunk.commit_message == change.commit_message
    assert atom_chunk.fingerprint == change.fingerprint
    assert atom_chunk.provenance["symbol_name"] == "verify_session"
    assert atom_chunk.provenance["atom_id"] == change.id
    assert atom_chunk.chunk_type == "ATOM_MODIFY"
    assert atom_chunk.content == change.raw_content


def test_16_query_stored_vector_compatibility_with_code_embedding():
    """16. Query and document vectors generated via generate_code_embedding share space and dimension."""
    from apps.api.src.services.code_atom.embedding import generate_code_embedding

    query_vec = generate_code_embedding("session verification override", input_type="query")
    doc_vec = generate_code_embedding(
        "def verify_session(session_id: str): override",
        input_type="document",
    )

    assert query_vec is not None
    assert doc_vec is not None
    assert len(query_vec) == 1536
    assert len(doc_vec) == 1536

    similarity = compute_cosine_similarity(query_vec, doc_vec)
    assert isinstance(similarity, float)
    assert similarity > 0.2
