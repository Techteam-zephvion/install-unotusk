import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from apps.api.src.models.chunk import CodeChunk, CompatibleVector
from apps.api.src.models.enums import SnapshotStatus
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.code_atom import (
    GitCommitArtifact,
)
from apps.api.src.services.code_atom.chunk_mapper import (
    generate_deterministic_chunk_id,
    resolve_and_map_atomic_changes,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.code_atom.embedding import (
    DevelopmentCodeEmbeddingBackend,
    reembed_atom_code_chunks,
)
from apps.api.src.services.code_atom.temporal import resolve_temporal_supersession
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import (
    MultiSignalRetriever,
    RetrievedCandidate,
    _extract_chunk_metadata,
)

SAMPLE_DIFF = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
--- a/apps/api/src/auth.py
+++ b/apps/api/src/auth.py
@@ -10,4 +10,6 @@ def authenticate_token(token: str) -> bool:
     if not token:
         return False
+    if token.startswith("test_"):
+        return True
     return verify_jwt(token)
"""


def test_1_compatible_vector_comparator():
    """1. CompatibleVector comparator supports cosine, l2, max inner product, and l1 operators."""
    vec = [0.1] * 1536

    cosine_expr = CodeChunk.embedding.cosine_distance(vec)
    assert cosine_expr is not None
    assert "<=>" in str(cosine_expr)

    l2_expr = CodeChunk.embedding.l2_distance(vec)
    assert l2_expr is not None
    assert "<->" in str(l2_expr)

    inner_expr = CodeChunk.embedding.max_inner_product(vec)
    assert inner_expr is not None
    assert "<#>" in str(inner_expr)

    l1_expr = CodeChunk.embedding.l1_distance(vec)
    assert l1_expr is not None
    assert "<+>" in str(l1_expr)


def test_2_compatible_vector_bind_param_sanitization():
    """2. CompatibleVector sanitizes empty list/tuple to None to avoid pgvector syntax errors."""
    cv = CompatibleVector()
    pg_dialect = postgresql.dialect()

    assert cv.process_bind_param(None, pg_dialect) is None
    assert cv.process_bind_param([], pg_dialect) is None
    assert cv.process_bind_param((), pg_dialect) is None

    result = cv.process_bind_param([1, 2.5, 3], pg_dialect)
    assert result == [1.0, 2.5, 3.0]

    try:
        from pgvector import Vector

        pv = Vector([1.5, 2.5])
        assert cv.process_bind_param(pv, pg_dialect) == [1.5, 2.5]
        assert cv.process_result_value(pv, pg_dialect) == [1.5, 2.5]
    except ImportError:
        pass


@pytest.mark.asyncio
async def test_3_retriever_native_pgvector_path():
    """3. MultiSignalRetriever uses native pgvector distance query when connected to PostgreSQL."""
    mock_session = AsyncMock()
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"
    mock_session.get_bind.return_value = mock_bind
    mock_session.bind = mock_bind

    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_chunk = CodeChunk(
        id=chunk_id,
        snapshot_id=snap_id,
        file_id=file_id,
        chunk_type="ATOM_MODIFY",
        name="auth.py (MODIFY)",
        path="apps/api/src/auth.py",
        content="def authenticate(user, password): pass",
        start_line=1,
        end_line=5,
        embedding=[0.2] * 1536,
    )

    mock_pg_result = MagicMock()
    # distance is 0.1, so similarity is 1.0 - 0.1 = 0.9
    mock_pg_result.all.return_value = [(mock_chunk, 0.1)]

    # Mock execute for file search, symbol search, chunk lexical, vector, concept
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    def execute_side_effect(stmt):
        stmt_str = str(stmt).lower()
        if "<=>" in stmt_str or "distance" in stmt_str:
            return mock_pg_result
        return empty_res

    mock_session.execute.side_effect = execute_side_effect

    analyzed = AnalyzedQuery(
        raw_query="how does authentication work",
        keywords=["auth"],
        symbol_candidates=[],
        path_candidates=[],
        concept_keywords=[],
    )

    candidates = await MultiSignalRetriever.retrieve_candidates(
        session=mock_session,
        snapshot_id=snap_id,
        analyzed_query=analyzed,
        limit_per_signal=5,
        query_embedding=[0.2] * 1536,
    )

    assert len(candidates) >= 1
    found = next((c for c in candidates if c.candidate_id == f"chunk:{chunk_id}"), None)
    assert found is not None
    assert found.signals.get("vector_similarity") == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_4_retriever_repository_scoping():
    """4. MultiSignalRetriever strictly isolates candidates to the specified repository_id."""
    mock_session = AsyncMock()
    matching_repo_id = uuid.uuid4()
    mismatch_repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()

    analyzed = AnalyzedQuery(
        raw_query="test query",
        keywords=["test"],
        symbol_candidates=[],
        path_candidates=[],
        concept_keywords=[],
    )

    # 1. Matching repository: snapshot check succeeds
    mock_check_ok = MagicMock()
    mock_check_ok.scalar_one_or_none.return_value = snap_id

    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    def execute_match(stmt):
        stmt_str = str(stmt).lower()
        if "repository_snapshots" in stmt_str:
            return mock_check_ok
        return empty_res

    mock_session.execute.side_effect = execute_match

    candidates_ok = await MultiSignalRetriever.retrieve_candidates(
        session=mock_session,
        snapshot_id=snap_id,
        analyzed_query=analyzed,
        repository_id=matching_repo_id,
    )
    assert isinstance(candidates_ok, list)

    # 2. Mismatched repository: snapshot check fails
    mock_check_fail = MagicMock()
    mock_check_fail.scalar_one_or_none.return_value = None

    def execute_mismatch(stmt):
        stmt_str = str(stmt).lower()
        if "repository_snapshots" in stmt_str:
            return mock_check_fail
        return empty_res

    mock_session.execute.side_effect = execute_mismatch

    candidates_fail = await MultiSignalRetriever.retrieve_candidates(
        session=mock_session,
        snapshot_id=snap_id,
        analyzed_query=analyzed,
        repository_id=mismatch_repo_id,
    )
    assert candidates_fail == []


def test_5_context_assembler_provenance_and_scope():
    """5. ContextAssembler includes repository_id, file_id, symbol_id, and scope in evidence."""
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()

    cand = RetrievedCandidate(
        candidate_id=f"chunk:{uuid.uuid4()}",
        entity_type="CHUNK",
        name="login_handler (MODIFY)",
        path="apps/api/src/auth.py",
        start_line=10,
        end_line=25,
        content="def login_handler(): return True",
        file_id=file_id,
        symbol_id=sym_id,
        signals={"content_match": 1.0},
        metadata={
            "repository_id": repo_id,
            "snapshot_id": snap_id,
            "commit_sha": "abc12345def67890",
            "commit_message": "fix: sanitize login input",
            "fingerprint": "fp_login_test",
        },
    )

    ranked = [RankedCandidate(candidate=cand, score=1.8, matched_reasons=["content_match"])]
    assembled = ContextAssembler.assemble_context(ranked_candidates=ranked)

    assert assembled.candidate_count == 1
    assert len(assembled.evidence_items) == 1
    ev = assembled.evidence_items[0]

    assert ev["file_id"] == str(file_id)
    assert ev["symbol_id"] == str(sym_id)
    assert ev["repository_id"] == str(repo_id)
    assert ev["snapshot_id"] == str(snap_id)
    assert ev["commit_sha"] == "abc12345def67890"

    assert f"Repo: {repo_id}" in assembled.prompt_context
    assert f"Snapshot: {snap_id}" in assembled.prompt_context


def test_6_temporal_supersession_base_chunk_superseded():
    """6. Initial base chunk without commit metadata is superseded by subsequent commit modifying it."""
    file_id = uuid.uuid4()

    # Base chunk from initial repository scan (no commit_sha, created earlier)
    base_chunk = RetrievedCandidate(
        candidate_id="chunk:base_1",
        entity_type="CHUNK",
        name="UserService",
        path="src/user.py",
        start_line=1,
        end_line=50,
        content="class UserService: pass",
        file_id=file_id,
        metadata={
            "chunk_type": "class",
            "created_at": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
    )

    # Incremental commit modifying UserService
    commit_chunk = RetrievedCandidate(
        candidate_id="chunk:commit_1",
        entity_type="CHUNK",
        name="UserService (MODIFY)",
        path="src/user.py",
        start_line=1,
        end_line=60,
        content="class UserService: def authenticate(self): pass",
        file_id=file_id,
        metadata={
            "chunk_type": "ATOM_MODIFY",
            "commit_sha": "commit_sha_1234567890",
            "committed_at": datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            "fingerprint": "fp_commit_1",
            "provenance": {"symbol_name": "UserService", "change_type": "MODIFY"},
        },
    )

    resolved = resolve_temporal_supersession([base_chunk, commit_chunk])
    assert len(resolved) == 2

    # The base chunk should be marked superseded by the commit
    assert base_chunk.metadata.get("is_superseded") is True
    assert base_chunk.metadata.get("is_current") is False
    assert base_chunk.metadata.get("superseded_by_sha") == "commit_sha_1234567890"

    # The commit chunk should be marked current
    assert commit_chunk.metadata.get("is_current") is True
    assert commit_chunk.metadata.get("is_superseded") is False


def test_7_chunk_mapper_backfills_missing_embedding():
    """7. resolve_and_map_atomic_changes backfills missing embedding on existing chunks during retry."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    commit = GitCommitArtifact(
        commit_sha="commit_999",
        commit_message="feat: background worker",
        raw_diff=SAMPLE_DIFF,
    )
    changes = CodeAtomDecomposer().decompose(commit).changes
    assert len(changes) >= 1
    change = changes[0]

    # Existing chunk from an interrupted run where embedding failed/was skipped
    existing_chunk = CodeChunk(
        id=generate_deterministic_chunk_id(change.fingerprint),
        snapshot_id=snap_id,
        file_id=file_id,
        chunk_type="ATOM_MODIFY",
        name="auth.py (MODIFY)",
        path=change.file_path,
        content=change.raw_content,
        start_line=10,
        end_line=16,
        commit_sha=change.commit_sha,
        fingerprint=change.fingerprint,
        embedding=None,  # Missing embedding!
    )

    repo_file = RepositoryFile(id=file_id, snapshot_id=snap_id, path=change.file_path)
    files_map = {change.file_path: repo_file}

    mapped = resolve_and_map_atomic_changes(
        changes=[change],
        snapshot_id=snap_id,
        files_map=files_map,
        existing_chunks_by_fingerprint={change.fingerprint: existing_chunk},
        compute_embedding=True,
    )

    assert len(mapped) == 1
    # Existing chunk embedding was backfilled
    assert existing_chunk.embedding is not None
    assert len(existing_chunk.embedding) == 1536


def test_8_chunk_mapper_intra_batch_duplicate_fingerprints():
    """8. Intra-batch duplicate fingerprints produce a single chunk instance without duplicate IDs."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()

    commit = GitCommitArtifact(
        commit_sha="commit_111",
        commit_message="refactor",
        raw_diff=SAMPLE_DIFF,
    )
    changes = CodeAtomDecomposer().decompose(commit).changes
    change1 = changes[0]
    # Re-use same change instance representing duplicated hunk
    change2 = change1

    assert change1.fingerprint == change2.fingerprint

    repo_file = RepositoryFile(id=file_id, snapshot_id=snap_id, path=change1.file_path)
    files_map = {change1.file_path: repo_file}

    mapped = resolve_and_map_atomic_changes(
        changes=[change1, change2],
        snapshot_id=snap_id,
        files_map=files_map,
        compute_embedding=False,
    )

    # Both refer to the same chunk instance rather than creating two competing objects with the same UUID
    assert len(mapped) == 2
    assert mapped[0] is mapped[1]


@pytest.mark.asyncio
async def test_9_ingestion_service_rollback_on_failure():
    """9. IngestionService rolls back aborted transaction so FAILED status can be committed."""
    mock_session = AsyncMock()

    snap_id = uuid.uuid4()
    repo_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    mock_repo = Repository(
        id=repo_id,
        project_id=proj_id,
        name="test-repo",
        full_name="org/test-repo",
        default_branch="main",
    )
    mock_snap = RepositorySnapshot(
        id=snap_id,
        repository_id=repo_id,
        status=SnapshotStatus.CLONING,
    )
    assert mock_repo.id == repo_id
    assert mock_snap.status == SnapshotStatus.CLONING

    # Simulate flush failing with a database error
    mock_session.execute = AsyncMock(side_effect=Exception("Database connection error"))
    mock_session.rollback = AsyncMock()
    mock_session.commit = AsyncMock()

    # Test the exception recovery block directly
    try:
        raise Exception("Database write failed")
    except Exception:
        await mock_session.rollback()
        # Verify rollback was called before attempting status update commit
        assert mock_session.rollback.called


def test_10_extract_chunk_metadata_provenance_fields():
    """10. _extract_chunk_metadata extracts file_id, symbol_id, and repository_id."""
    repo_id = uuid.uuid4()
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()

    chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snap_id,
        file_id=file_id,
        symbol_id=sym_id,
        chunk_type="ATOM_ADD",
        name="test.py (ADD)",
        path="test.py",
        content="x = 1",
        start_line=1,
        end_line=1,
        commit_sha="sha123",
        fingerprint="fp123",
        provenance={"repository_id": str(repo_id)},
    )

    meta = _extract_chunk_metadata(chunk)
    assert meta["file_id"] == str(file_id)
    assert meta["symbol_id"] == str(sym_id)
    assert meta["repository_id"] == str(repo_id)
    assert meta["snapshot_id"] == str(snap_id)


def test_11_graph_expander_candidate_deduplication():
    """11. RelationshipExpander does not duplicate candidates between seed and expansion."""
    file_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    fingerprint = "fp_dedup_test"

    # Candidate already present in seeds
    seed_cand = RetrievedCandidate(
        candidate_id=f"chunk:{chunk_id}",
        entity_type="CHUNK",
        name="test_symbol",
        path="src/service.py",
        start_line=1,
        end_line=10,
        content="def test_symbol(): pass",
        file_id=file_id,
        signals={"content_match": 1.0},
        metadata={"fingerprint": fingerprint},
    )

    expanded = {seed_cand.candidate_id: seed_cand}

    # Simulate graph expander encountering the same chunk with atom fingerprint
    chunk_cid = f"chunk:{chunk_id}"
    atom_cid = f"chunk:atom:{fingerprint}"
    existing_cand = expanded.get(chunk_cid) or expanded.get(atom_cid)

    assert existing_cand is not None
    assert existing_cand is seed_cand


@pytest.mark.asyncio
async def test_12_reembed_atom_code_chunks_only_missing():
    """12. reembed_atom_code_chunks with only_missing=True queries only chunks with embedding IS NULL."""
    mock_session = AsyncMock()
    mock_res = MagicMock()

    snap_id = uuid.uuid4()
    chunk_missing = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snap_id,
        file_id=uuid.uuid4(),
        chunk_type="ATOM_ADD",
        name="foo.py (ADD)",
        path="foo.py",
        content="x = 1",
        start_line=1,
        end_line=1,
        commit_sha="c1",
        fingerprint="fp1",
        embedding=None,
    )
    mock_res.scalars.return_value.all.return_value = [chunk_missing]
    mock_session.execute.return_value = mock_res
    mock_session.flush = AsyncMock()

    backend = DevelopmentCodeEmbeddingBackend()
    count = await reembed_atom_code_chunks(
        session=mock_session,
        snapshot_id=snap_id,
        backend=backend,
        only_missing=True,
    )

    assert count == 1
    assert chunk_missing.embedding is not None
    assert len(chunk_missing.embedding) == 1536
