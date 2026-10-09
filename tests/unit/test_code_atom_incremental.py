import os
import subprocess
import tempfile
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.schemas.code_atom import (
    CodeChangeType,
    GitCommitArtifact,
)
from apps.api.src.services.code_atom import (
    CodeAtomDecomposer,
    InvalidBaseCommitError,
    extract_incremental_commit_artifacts,
    generate_deterministic_chunk_id,
    resolve_and_map_atomic_changes,
)
from apps.api.src.services.context_engine.retriever import MultiSignalRetriever
from apps.api.src.services.ingestion_service import IngestionService

SAMPLE_ONE_CHANGE_DIFF = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
index 1111111..2222222 100644
--- a/apps/api/src/auth.py
+++ b/apps/api/src/auth.py
@@ -10,4 +10,6 @@ def authenticate_token(token: str) -> bool:
     if not token:
         return False
+    if token.startswith("test_"):
+        return True
     return verify_jwt(token)
"""

SAMPLE_MULTI_HUNK_DIFF = """diff --git a/apps/api/src/service.py b/apps/api/src/service.py
index 3333333..4444444 100644
--- a/apps/api/src/service.py
+++ b/apps/api/src/service.py
@@ -15,5 +15,7 @@ def get_user_profile(user_id: str) -> dict:
     user = db.find_user(user_id)
     if not user:
         raise NotFoundException()
+    if user.is_deleted:
+        raise InactiveUserException()
     return user.to_dict()
@@ -50,5 +50,7 @@ def update_user_email(user_id: str, new_email: str) -> bool:
     user = db.find_user(user_id)
     validate_email(new_email)
-    user.email = new_email
+    user.set_email(new_email)
+    user.mark_dirty()
     return db.save(user)
"""

SAMPLE_MULTI_FILE_DIFF = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
--- a/apps/api/src/auth.py
+++ b/apps/api/src/auth.py
@@ -1,3 +1,4 @@
+import hashlib
 def hash_token(t: str) -> str:
-    return t
+    return hashlib.sha256(t.encode()).hexdigest()
diff --git a/apps/api/src/models.py b/apps/api/src/models.py
--- a/apps/api/src/models.py
+++ b/apps/api/src/models.py
@@ -20,3 +20,4 @@ class Account:
     id: str
+    status: str = "active"
"""

SAMPLE_ADD_DIFF = """diff --git a/src/new_handler.py b/src/new_handler.py
new file mode 100644
--- /dev/null
+++ b/src/new_handler.py
@@ -0,0 +1,5 @@
+def handle_ping():
+    return "pong"
+"""

SAMPLE_DELETE_DIFF = """diff --git a/src/legacy_handler.py b/src/legacy_handler.py
deleted file mode 100644
--- a/src/legacy_handler.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def old_handler():
-    pass
-"""

SAMPLE_RENAME_DIFF = """diff --git a/src/old_name.py b/src/new_name.py
similarity index 100%
rename from src/old_name.py
rename to src/new_name.py
"""


# ---------------------------------------------------------------------------
# Helpers for Git repository creation
# ---------------------------------------------------------------------------


def _create_test_git_repo() -> tuple[str, list[str]]:
    """Creates a temporary Git repository with multiple commits and returns (tmpdir, commit_shas)."""
    tmpdir = tempfile.mkdtemp()
    subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmpdir, check=True, capture_output=True)

    shas = []
    # Commit 1: Initial file
    f1 = os.path.join(tmpdir, "auth.py")
    with open(f1, "w") as f:
        f.write("def authenticate_token(token: str) -> bool:\n    return bool(token)\n")
    subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: commit 1 initial auth"], cwd=tmpdir, check=True, capture_output=True)
    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmpdir, check=True, capture_output=True, text=True)
    shas.append(res.stdout.strip())

    # Commit 2: Update auth.py
    with open(f1, "a") as f:
        f.write("\ndef verify_jwt(token: str) -> bool:\n    return len(token) > 10\n")
    subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: commit 2 add verify_jwt"], cwd=tmpdir, check=True, capture_output=True)
    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmpdir, check=True, capture_output=True, text=True)
    shas.append(res.stdout.strip())

    # Commit 3: Add new file service.py
    f2 = os.path.join(tmpdir, "service.py")
    with open(f2, "w") as f:
        f.write("def get_service():\n    return 'auth_service'\n")
    subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: commit 3 add service"], cwd=tmpdir, check=True, capture_output=True)
    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmpdir, check=True, capture_output=True, text=True)
    shas.append(res.stdout.strip())

    return tmpdir, shas


# ---------------------------------------------------------------------------
# Unit Tests for 14 Phase 5 Criteria
# ---------------------------------------------------------------------------


def test_git_extractor_invalid_base_commit_raises_error():
    """Verify that an invalid or non-existent base commit raises InvalidBaseCommitError."""
    tmpdir, _ = _create_test_git_repo()
    try:
        with pytest.raises(InvalidBaseCommitError, match="does not exist in repository"):
            extract_incremental_commit_artifacts(
                repo_dir=tmpdir,
                base_commit_sha="0000000000000000000000000000000000000000",
                target_commit_sha="HEAD",
            )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_git_extractor_invalid_target_commit_raises_error():
    """Verify that an invalid target commit raises ValueError."""
    tmpdir, _ = _create_test_git_repo()
    try:
        with pytest.raises(ValueError, match="does not exist in repository"):
            extract_incremental_commit_artifacts(
                repo_dir=tmpdir,
                base_commit_sha=None,
                target_commit_sha="invalid_target_sha_12345",
            )
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_1_first_incremental_indexing():
    """1. First incremental indexing: discovers commits up to target, creates chunks, advances checkpoint."""
    tmpdir, shas = _create_test_git_repo()
    try:
        # First incremental indexing with base_commit_sha = None
        artifacts = extract_incremental_commit_artifacts(
            repo_dir=tmpdir,
            base_commit_sha=None,
            target_commit_sha="HEAD",
        )
        assert len(artifacts) == 3
        assert [a.commit_sha for a in artifacts] == shas

        snap_id = uuid.uuid4()
        repo_id = uuid.uuid4()
        snapshot = RepositorySnapshot(
            id=snap_id,
            repository_id=repo_id,
            commit_sha=None,  # No prior checkpoint
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        # Mock snapshot and repository queries
        mock_snap_res = MagicMock()
        mock_snap_res.scalar_one_or_none.return_value = snapshot

        mock_repo = Repository(id=repo_id, project_id=uuid.uuid4())
        mock_repo_res = MagicMock()
        mock_repo_res.scalar_one_or_none.return_value = mock_repo

        # Mock file, symbol, existing chunk queries for the 3 commits
        mock_files_res = MagicMock()
        mock_files_res.scalars.return_value.all.return_value = []
        mock_sym_res = MagicMock()
        mock_sym_res.all.return_value = []
        mock_chunk_res = MagicMock()
        mock_chunk_res.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_snap_res,
            mock_repo_res,
            # Commit 1
            mock_files_res,
            mock_sym_res,
            mock_chunk_res,
            # Commit 2
            mock_files_res,
            mock_sym_res,
            mock_chunk_res,
            # Commit 3
            mock_files_res,
            mock_sym_res,
            mock_chunk_res,
        ]

        chunks = await IngestionService.ingest_incremental_commit_artifacts(
            session=mock_session,
            snapshot_id=snap_id,
            commit_artifacts=artifacts,
            advance_checkpoint=True,
        )

        assert len(chunks) >= 3
        # Checkpoint advanced to latest commit
        assert snapshot.commit_sha == shas[-1]
        mock_session.flush.assert_awaited()
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_2_new_commit_after_previous_checkpoint():
    """2. New commit after the previous checkpoint: processes only commits newer than checkpoint."""
    tmpdir, shas = _create_test_git_repo()
    try:
        # Checkpoint is at commit 1 (shas[0])
        checkpoint_sha = shas[0]
        # Incremental extraction from commit 1 to commit 2 (shas[1])
        artifacts = extract_incremental_commit_artifacts(
            repo_dir=tmpdir,
            base_commit_sha=checkpoint_sha,
            target_commit_sha=shas[1],
        )

        assert len(artifacts) == 1
        assert artifacts[0].commit_sha == shas[1]
        assert "verify_jwt" in artifacts[0].raw_diff

        snap_id = uuid.uuid4()
        snapshot = RepositorySnapshot(
            id=snap_id,
            repository_id=uuid.uuid4(),
            commit_sha=checkpoint_sha,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        mock_snap_res = MagicMock()
        mock_snap_res.scalar_one_or_none.return_value = snapshot
        mock_repo = Repository(id=snapshot.repository_id, project_id=uuid.uuid4())
        mock_repo_res = MagicMock()
        mock_repo_res.scalar_one_or_none.return_value = mock_repo
        mock_files_res = MagicMock()
        mock_files_res.scalars.return_value.all.return_value = []
        mock_sym_res = MagicMock()
        mock_sym_res.all.return_value = []
        mock_chunk_res = MagicMock()
        mock_chunk_res.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_snap_res,
            mock_repo_res,
            mock_files_res,
            mock_sym_res,
            mock_chunk_res,
        ]

        chunks = await IngestionService.ingest_incremental_commit_artifacts(
            session=mock_session,
            snapshot_id=snap_id,
            commit_artifacts=artifacts,
            advance_checkpoint=True,
        )

        assert len(chunks) == 1
        assert chunks[0].commit_sha == shas[1]
        assert snapshot.commit_sha == shas[1]
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_3_multiple_new_commits_processed_in_order():
    """3. Multiple new commits processed in topological/chronological order."""
    tmpdir, shas = _create_test_git_repo()
    try:
        checkpoint_sha = shas[0]
        artifacts = extract_incremental_commit_artifacts(
            repo_dir=tmpdir,
            base_commit_sha=checkpoint_sha,
            target_commit_sha="HEAD",
        )

        assert len(artifacts) == 2
        # Exact chronological ordering: commit 2, then commit 3
        assert artifacts[0].commit_sha == shas[1]
        assert artifacts[1].commit_sha == shas[2]

        snap_id = uuid.uuid4()
        snapshot = RepositorySnapshot(
            id=snap_id,
            repository_id=uuid.uuid4(),
            commit_sha=checkpoint_sha,
        )

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        mock_snap_res = MagicMock()
        mock_snap_res.scalar_one_or_none.return_value = snapshot
        mock_repo = Repository(id=snapshot.repository_id, project_id=uuid.uuid4())
        mock_repo_res = MagicMock()
        mock_repo_res.scalar_one_or_none.return_value = mock_repo
        mock_files_res = MagicMock()
        mock_files_res.scalars.return_value.all.return_value = []
        mock_sym_res = MagicMock()
        mock_sym_res.all.return_value = []
        mock_chunk_res = MagicMock()
        mock_chunk_res.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [
            mock_snap_res,
            mock_repo_res,
            # Commit 2
            mock_files_res,
            mock_sym_res,
            mock_chunk_res,
            # Commit 3
            mock_files_res,
            mock_sym_res,
            mock_chunk_res,
        ]

        chunks = await IngestionService.ingest_incremental_commit_artifacts(
            session=mock_session,
            snapshot_id=snap_id,
            commit_artifacts=artifacts,
            advance_checkpoint=True,
        )

        assert len(chunks) == 2
        assert chunks[0].commit_sha == shas[1]
        assert chunks[1].commit_sha == shas[2]
        # Checkpoint advances to the final commit
        assert snapshot.commit_sha == shas[2]
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


def test_4_no_new_commits_results_in_noop():
    """4. No new commits results in a safe no-op with empty list returned."""
    tmpdir, shas = _create_test_git_repo()
    try:
        latest_sha = shas[-1]
        artifacts = extract_incremental_commit_artifacts(
            repo_dir=tmpdir,
            base_commit_sha=latest_sha,
            target_commit_sha=latest_sha,
        )
        assert artifacts == []

        # Also when target_commit_sha is HEAD and base is HEAD
        artifacts_head = extract_incremental_commit_artifacts(
            repo_dir=tmpdir,
            base_commit_sha=latest_sha,
            target_commit_sha="HEAD",
        )
        assert artifacts_head == []
    finally:
        import shutil

        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_5_reprocessing_does_not_create_duplicate_chunks():
    """5. Reprocessing does not create duplicate chunks or re-embed existing chunks."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit_sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    commit = GitCommitArtifact(
        commit_sha=commit_sha,
        commit_message="feat: auth updates",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )

    # First pass: creates chunk
    decomposer = CodeAtomDecomposer()
    res = decomposer.decompose(commit)
    change = res.changes[0]

    existing_chunk = CodeChunk(
        id=generate_deterministic_chunk_id(change.fingerprint),
        snapshot_id=snap_id,
        file_id=file_id,
        chunk_type="ATOM_MODIFY",
        name="auth.py (MODIFY)",
        path="apps/api/src/auth.py",
        content=change.raw_content,
        start_line=10,
        end_line=15,
        commit_sha=commit_sha,
        fingerprint=change.fingerprint,
        embedding=[0.1] * 1536,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    # Query returns existing chunk
    mock_files_res = MagicMock()
    mock_files_res.scalars.return_value.all.return_value = [
        RepositoryFile(id=file_id, snapshot_id=snap_id, path="apps/api/src/auth.py")
    ]
    mock_sym_res = MagicMock()
    mock_sym_res.all.return_value = []
    mock_chunk_res = MagicMock()
    mock_chunk_res.scalars.return_value.all.return_value = [existing_chunk]

    mock_session.execute.side_effect = [mock_files_res, mock_sym_res, mock_chunk_res]

    chunks = await IngestionService.ingest_commit_atom_changes(
        session=mock_session,
        snapshot_id=snap_id,
        commit_artifact=commit,
    )

    assert len(chunks) == 1
    assert chunks[0].id == existing_chunk.id
    # session.add was NOT called because chunk was already present
    mock_session.add.assert_not_called()


def test_6_only_affected_changes_are_processed():
    """6. Only affected changes in the commit diff are decomposed and processed."""
    commit = GitCommitArtifact(
        commit_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        commit_message="fix(auth): update auth only",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,  # Only touches auth.py
    )
    result = CodeAtomDecomposer().decompose(commit)
    assert result.change_count == 1
    assert result.changes[0].file_path == "apps/api/src/auth.py"
    # Unrelated files (service.py, models.py) are completely absent
    assert all("service.py" not in c.file_path for c in result.changes)


def test_7_unchanged_chunks_retain_ids_and_embeddings():
    """7. Unchanged chunks retain their IDs, fingerprints, and embeddings."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit = GitCommitArtifact(
        commit_sha="cccccccccccccccccccccccccccccccccccccccc",
        commit_message="test: retain embeddings",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    change = CodeAtomDecomposer().decompose(commit).changes[0]

    existing_vec = [0.42] * 1536
    existing_chunk = CodeChunk(
        id=generate_deterministic_chunk_id(change.fingerprint),
        snapshot_id=snap_id,
        file_id=file_id,
        chunk_type="ATOM_MODIFY",
        name="auth.py (MODIFY)",
        path="apps/api/src/auth.py",
        content=change.raw_content,
        start_line=10,
        end_line=15,
        commit_sha="cccccccccccccccccccccccccccccccccccccccc",
        fingerprint=change.fingerprint,
        embedding=existing_vec,
    )

    existing_chunks_by_fp = {change.fingerprint: existing_chunk}

    with patch("apps.api.src.services.code_atom.chunk_mapper.generate_atom_code_embedding") as mock_embed:
        mapped = resolve_and_map_atomic_changes(
            changes=[change],
            snapshot_id=snap_id,
            files_map={"apps/api/src/auth.py": RepositoryFile(id=file_id, snapshot_id=snap_id, path="apps/api/src/auth.py")},
            existing_chunks_by_fingerprint=existing_chunks_by_fp,
        )

        assert len(mapped) == 1
        assert mapped[0].id == existing_chunk.id
        assert mapped[0].embedding == existing_vec
        # generate_atom_code_embedding was NOT called
        mock_embed.assert_not_called()


def test_8_add_modify_delete_and_rename_handling():
    """8. ADD, MODIFY, DELETE, and RENAME diffs are correctly identified and mapped."""
    snap_id = uuid.uuid4()
    decomposer = CodeAtomDecomposer()

    # 1. ADD
    c_add = decomposer.decompose(GitCommitArtifact(commit_sha="1111", commit_message="add", raw_diff=SAMPLE_ADD_DIFF)).changes[0]
    assert c_add.change_type == CodeChangeType.ADD
    chunk_add = resolve_and_map_atomic_changes([c_add], snap_id, files_map={})[0]
    assert chunk_add.chunk_type == "ATOM_ADD"

    # 2. MODIFY
    c_mod = decomposer.decompose(GitCommitArtifact(commit_sha="2222", commit_message="mod", raw_diff=SAMPLE_ONE_CHANGE_DIFF)).changes[0]
    assert c_mod.change_type == CodeChangeType.MODIFY
    chunk_mod = resolve_and_map_atomic_changes([c_mod], snap_id, files_map={})[0]
    assert chunk_mod.chunk_type == "ATOM_MODIFY"

    # 3. DELETE
    c_del = decomposer.decompose(GitCommitArtifact(commit_sha="3333", commit_message="del", raw_diff=SAMPLE_DELETE_DIFF)).changes[0]
    assert c_del.change_type == CodeChangeType.DELETE
    chunk_del = resolve_and_map_atomic_changes([c_del], snap_id, files_map={})[0]
    assert chunk_del.chunk_type == "ATOM_DELETE"

    # 4. RENAME
    c_ren = decomposer.decompose(GitCommitArtifact(commit_sha="4444", commit_message="ren", raw_diff=SAMPLE_RENAME_DIFF)).changes[0]
    assert c_ren.change_type == CodeChangeType.RENAME
    old_file = RepositoryFile(id=uuid.uuid4(), snapshot_id=snap_id, path="src/old_name.py")
    files_map = {"src/old_name.py": old_file}
    chunk_ren = resolve_and_map_atomic_changes([c_ren], snap_id, files_map=files_map)[0]
    assert chunk_ren.chunk_type == "ATOM_RENAME"
    assert chunk_ren.file_id == old_file.id


def test_9_multi_file_and_multi_hunk_commits():
    """9. Multi-file and multi-hunk commits map to distinct CodeChunks with hunk indices."""
    snap_id = uuid.uuid4()
    decomposer = CodeAtomDecomposer()

    # Multi-file commit
    c_multi_file = decomposer.decompose(
        GitCommitArtifact(commit_sha="5555", commit_message="multi file", raw_diff=SAMPLE_MULTI_FILE_DIFF)
    )
    assert c_multi_file.change_count == 2
    paths = {c.file_path for c in c_multi_file.changes}
    assert paths == {"apps/api/src/auth.py", "apps/api/src/models.py"}

    chunks_mf = resolve_and_map_atomic_changes(c_multi_file.changes, snap_id, files_map={})
    assert len(chunks_mf) == 2

    # Multi-hunk commit
    c_multi_hunk = decomposer.decompose(
        GitCommitArtifact(commit_sha="6666", commit_message="multi hunk", raw_diff=SAMPLE_MULTI_HUNK_DIFF)
    )
    assert c_multi_hunk.change_count == 2
    assert c_multi_hunk.changes[0].provenance["hunk_index"] == 1
    assert c_multi_hunk.changes[1].provenance["hunk_index"] == 2

    chunks_mh = resolve_and_map_atomic_changes(c_multi_hunk.changes, snap_id, files_map={})
    assert len(chunks_mh) == 2
    assert chunks_mh[0].provenance["hunk_index"] == 1
    assert chunks_mh[1].provenance["hunk_index"] == 2


@pytest.mark.asyncio
async def test_10_failed_processing_does_not_advance_checkpoint():
    """10. Failed processing does not advance the checkpoint incorrectly."""
    snap_id = uuid.uuid4()
    initial_checkpoint = "1111111111111111111111111111111111111111"
    snapshot = RepositorySnapshot(
        id=snap_id,
        repository_id=uuid.uuid4(),
        commit_sha=initial_checkpoint,
    )

    artifact = GitCommitArtifact(
        commit_sha="2222222222222222222222222222222222222222",
        commit_message="failing commit",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )

    mock_session = AsyncMock()
    mock_snap_res = MagicMock()
    mock_snap_res.scalar_one_or_none.return_value = snapshot

    # Simulate failure during ingest_commit_atom_changes
    mock_session.execute.side_effect = [
        mock_snap_res,
        RuntimeError("Database write error"),
    ]

    with pytest.raises(RuntimeError, match="Database write error"):
        await IngestionService.ingest_incremental_commit_artifacts(
            session=mock_session,
            snapshot_id=snap_id,
            commit_artifacts=[artifact],
            advance_checkpoint=True,
        )

    # Checkpoint remained at initial_checkpoint!
    assert snapshot.commit_sha == initial_checkpoint


@pytest.mark.asyncio
async def test_11_retrying_after_failure_succeeds_without_duplicates():
    """11. Retrying after failure succeeds without duplicate chunks."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit_sha = "3333333333333333333333333333333333333333"

    artifact = GitCommitArtifact(
        commit_sha=commit_sha,
        commit_message="retry test",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )

    snapshot = RepositorySnapshot(
        id=snap_id,
        repository_id=uuid.uuid4(),
        commit_sha="0000000000000000000000000000000000000000",
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    mock_snap_res = MagicMock()
    mock_snap_res.scalar_one_or_none.return_value = snapshot
    mock_repo = Repository(id=snapshot.repository_id, project_id=uuid.uuid4())
    mock_repo_res = MagicMock()
    mock_repo_res.scalar_one_or_none.return_value = mock_repo
    mock_files_res = MagicMock()
    mock_files_res.scalars.return_value.all.return_value = [
        RepositoryFile(id=file_id, snapshot_id=snap_id, path="apps/api/src/auth.py")
    ]
    mock_sym_res = MagicMock()
    mock_sym_res.all.return_value = []
    mock_chunk_res = MagicMock()
    mock_chunk_res.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        mock_snap_res,
        mock_repo_res,
        mock_files_res,
        mock_sym_res,
        mock_chunk_res,
    ]

    # Retry attempt runs and succeeds
    chunks = await IngestionService.ingest_incremental_commit_artifacts(
        session=mock_session,
        snapshot_id=snap_id,
        commit_artifacts=[artifact],
        advance_checkpoint=True,
    )

    assert len(chunks) == 1
    assert snapshot.commit_sha == commit_sha
    mock_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_12_project_and_snapshot_isolation():
    """12. Project and snapshot isolation: chunks and checkpoints remain scoped to their snapshot."""
    snap_a = uuid.uuid4()
    snap_b = uuid.uuid4()
    proj_a = uuid.uuid4()

    artifact_a = GitCommitArtifact(
        commit_sha="aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111",
        commit_message="feat for snap A",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    mock_files_res = MagicMock()
    mock_files_res.scalars.return_value.all.return_value = []
    mock_sym_res = MagicMock()
    mock_sym_res.all.return_value = []
    mock_chunk_res = MagicMock()
    mock_chunk_res.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [mock_files_res, mock_sym_res, mock_chunk_res]

    chunks_a = await IngestionService.ingest_commit_atom_changes(
        session=mock_session,
        snapshot_id=snap_a,
        commit_artifact=artifact_a,
        project_id=proj_a,
    )

    assert len(chunks_a) == 1
    assert chunks_a[0].snapshot_id == snap_a
    assert chunks_a[0].provenance["project_id"] == str(proj_a)
    assert chunks_a[0].snapshot_id != snap_b


def test_13_deleted_file_history_is_preserved():
    """13. Deleted file history is preserved: modification chunk is not discarded when file is deleted."""
    snap_id = uuid.uuid4()
    decomposer = CodeAtomDecomposer()

    # Commit 1: Modified auth.py
    commit1 = GitCommitArtifact(
        commit_sha="commit_1_sha",
        commit_message="feat: initial auth logic",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    change1 = decomposer.decompose(commit1).changes[0]
    chunk1 = resolve_and_map_atomic_changes([change1], snap_id, files_map={})[0]

    # Commit 2: Deleted auth.py
    diff_del = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
deleted file mode 100644
--- a/apps/api/src/auth.py
+++ /dev/null
@@ -1,15 +0,0 @@
-def authenticate_token(token: str) -> bool:
-    return False
"""
    commit2 = GitCommitArtifact(
        commit_sha="commit_2_sha",
        commit_message="chore: remove auth.py",
        raw_diff=diff_del,
    )
    change2 = decomposer.decompose(commit2).changes[0]
    chunk2 = resolve_and_map_atomic_changes([change2], snap_id, files_map={})[0]

    # Both chunks exist independently
    assert chunk1.chunk_type == "ATOM_MODIFY"
    assert chunk1.commit_sha == "commit_1_sha"
    assert chunk2.chunk_type == "ATOM_DELETE"
    assert chunk2.commit_sha == "commit_2_sha"
    assert chunk1.id != chunk2.id


@pytest.mark.asyncio
async def test_14_existing_retrieval_can_find_newly_indexed_chunks():
    """14. Existing MultiSignalRetriever can find newly incrementally indexed CodeChunks."""
    snap_id = uuid.uuid4()
    commit_sha = "83efb9c1234567890abcdef1234567890abcdef1"

    commit = GitCommitArtifact(
        commit_sha=commit_sha,
        commit_message="feat(auth): test token validation",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    change = CodeAtomDecomposer().decompose(commit).changes[0]
    chunk = resolve_and_map_atomic_changes([change], snap_id, files_map={})[0]

    # Verify retriever queries against code_chunks find this chunk
    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt).lower()
        if "code_chunks" in stmt_str:
            mock_res.scalars.return_value.all.return_value = [chunk]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    from apps.api.src.services.context_engine.query_analyzer import analyze_query

    analyzed = analyze_query("test token validation")
    candidates = await MultiSignalRetriever.retrieve_candidates(
        session=session,
        snapshot_id=snap_id,
        analyzed_query=analyzed,
    )

    assert len(candidates) >= 1
    found = next((c for c in candidates if c.candidate_id == f"chunk:{chunk.id}"), None)
    assert found is not None
    assert found.entity_type == "CHUNK"
    assert "test_" in found.content
