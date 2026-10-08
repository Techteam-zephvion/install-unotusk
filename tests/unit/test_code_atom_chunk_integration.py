import os
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.enums import SymbolType
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.schemas.code_atom import (
    GitCommitArtifact,
)
from apps.api.src.services.code_atom import (
    CodeAtomDecomposer,
    extract_git_commit_artifact,
    generate_deterministic_chunk_id,
    map_atomic_code_change_to_code_chunk,
    resolve_and_map_atomic_changes,
)
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
"""

SAMPLE_DELETE_DIFF = """diff --git a/src/legacy_handler.py b/src/legacy_handler.py
deleted file mode 100644
--- a/src/legacy_handler.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def old_handler():
-    pass
"""

SAMPLE_RENAME_DIFF = """diff --git a/src/old_name.py b/src/new_name.py
similarity index 100%
rename from src/old_name.py
rename to src/new_name.py
"""


def test_commit_to_atomic_changes_and_code_chunks():
    """Verify end-to-end transformation: Git commit -> AtomicCodeChange -> CodeChunk."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit_sha = "abcdef1234567890abcdef1234567890abcdef12"
    commit_msg = "feat(auth): add test token verification support"

    commit = GitCommitArtifact(
        commit_sha=commit_sha,
        commit_message=commit_msg,
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )

    decomposer = CodeAtomDecomposer()
    decomp_result = decomposer.decompose(commit)
    assert decomp_result.change_count == 1

    atomic_change = decomp_result.changes[0]
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/auth.py",
        filename="auth.py",
        extension=".py",
        content_hash="abc",
    )
    files_map = {"apps/api/src/auth.py": repo_file}

    chunks = resolve_and_map_atomic_changes(
        changes=decomp_result.changes,
        snapshot_id=snap_id,
        files_map=files_map,
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, CodeChunk)
    assert chunk.snapshot_id == snap_id
    assert chunk.file_id == file_id
    assert chunk.commit_sha == commit_sha
    assert chunk.commit_message == commit_msg
    assert chunk.fingerprint == atomic_change.fingerprint
    assert chunk.chunk_type == "ATOM_MODIFY"
    assert "test_" in chunk.content
    assert chunk.embedding is not None
    assert len(chunk.embedding) == 1536


def test_atomic_change_to_code_chunk_mapping():
    """Verify precise field mapping from AtomicCodeChange to CodeChunk."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()
    decomposer = CodeAtomDecomposer()
    catalog = [
        {
            "id": sym_id,
            "name": "authenticate_token",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/auth.py",
            "start_line": 5,
            "end_line": 25,
        }
    ]
    commit = GitCommitArtifact(
        commit_sha="1122334455667788990011223344556677889900",
        commit_message="fix: authenticate token validation",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit, symbol_catalog=catalog)
    change = result.changes[0]

    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snap_id,
        file_id=file_id,
        symbol_id=sym_id,
    )

    assert chunk.snapshot_id == snap_id
    assert chunk.file_id == file_id
    assert chunk.symbol_id == sym_id
    assert chunk.name == "authenticate_token (MODIFY)"
    assert chunk.path == "apps/api/src/auth.py"
    assert chunk.chunk_type == "ATOM_MODIFY"
    assert chunk.start_line == 10
    assert chunk.end_line == 15
    assert chunk.commit_sha == "1122334455667788990011223344556677889900"
    assert chunk.commit_message == "fix: authenticate token validation"
    assert chunk.fingerprint == change.fingerprint
    assert chunk.provenance["symbol_name"] == "authenticate_token"
    assert chunk.provenance["atom_id"] == change.id
    assert chunk.embedding is not None
    assert len(chunk.embedding) == 1536


def test_commit_message_preservation():
    """Verify commit message is preserved across all mapped CodeChunks."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    msg = "refactor(core): split services and clean boundaries [UNOTUSK-42]"
    commit = GitCommitArtifact(
        commit_sha="2233445566778899001122334455667788990011",
        commit_message=msg,
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/service.py",
        filename="service.py",
        extension=".py",
        content_hash="xyz",
    )
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map={"apps/api/src/service.py": repo_file},
    )

    assert len(chunks) == 2
    for c in chunks:
        assert c.commit_message == msg
        assert c.provenance["commit_message"] == msg


def test_snapshot_mapping():
    """Verify that chunks accurately reference the parent RepositorySnapshot."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit = GitCommitArtifact(
        commit_sha="3344556677889900112233445566778899001122",
        commit_message="chore: bump snapshot",
        snapshot_id=snap_id,
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/auth.py",
        filename="auth.py",
        extension=".py",
        content_hash="abc",
    )
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map={"apps/api/src/auth.py": repo_file},
    )

    assert chunks[0].snapshot_id == snap_id


def test_file_mapping_and_no_duplicate_files():
    """Verify that existing files are reused and no duplicates are created."""
    snap_id = uuid.uuid4()
    existing_file_id = uuid.uuid4()
    repo_file = RepositoryFile(
        id=existing_file_id,
        snapshot_id=snap_id,
        path="apps/api/src/service.py",
        filename="service.py",
        extension=".py",
        content_hash="xyz",
    )
    files_map = {"apps/api/src/service.py": repo_file}

    commit = GitCommitArtifact(
        commit_sha="4455667788990011223344556677889900112233",
        commit_message="test: file resolution",
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map=files_map,
    )

    assert len(chunks) == 2
    # Both hunks should point to the SAME existing RepositoryFile entity
    assert chunks[0].file_id == existing_file_id
    assert chunks[1].file_id == existing_file_id
    assert len(files_map) == 1  # No duplicate files created


def test_symbol_mapping_resolved_and_unresolved():
    """Verify symbol mapping resolves symbols when present and leaves None when absent."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()

    code_sym = CodeSymbol(
        id=sym_id,
        file_id=file_id,
        name="get_user_profile",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="get_user_profile",
        start_line=15,
        end_line=30,
    )
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/service.py",
        filename="service.py",
        extension=".py",
        content_hash="abc",
    )

    commit = GitCommitArtifact(
        commit_sha="5566778899001122334455667788990011223344",
        commit_message="feat: profile update",
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )
    # Provide catalog with only get_user_profile
    catalog = [
        {
            "id": sym_id,
            "name": "get_user_profile",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/service.py",
            "start_line": 15,
            "end_line": 30,
        }
    ]
    result = CodeAtomDecomposer().decompose(commit, symbol_catalog=catalog)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map={"apps/api/src/service.py": repo_file},
        symbols_map={f"{file_id}:get_user_profile": code_sym},
    )

    # First hunk is in get_user_profile -> resolved
    assert chunks[0].symbol_id == sym_id
    # Second hunk is in update_user_email (not in catalog) -> None
    assert chunks[1].symbol_id is None


def test_change_type_add():
    """Verify ADD change mapping."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="src/new_handler.py",
        filename="new_handler.py",
        extension=".py",
        content_hash="abc",
    )
    commit = GitCommitArtifact(
        commit_sha="6677889900112233445566778899001122334455",
        commit_message="feat(handler): add new handler",
        raw_diff=SAMPLE_ADD_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map={"src/new_handler.py": repo_file},
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "ATOM_ADD"
    assert "handle_ping" in chunks[0].content


def test_change_type_modify():
    """Verify MODIFY change mapping."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/auth.py",
        filename="auth.py",
        extension=".py",
        content_hash="abc",
    )
    commit = GitCommitArtifact(
        commit_sha="7788990011223344556677889900112233445566",
        commit_message="fix: auth patch",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map={"apps/api/src/auth.py": repo_file},
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "ATOM_MODIFY"


def test_change_type_delete():
    """Verify DELETE change creates a CodeChunk referencing the file."""
    snap_id = uuid.uuid4()
    files_map: dict[str, RepositoryFile] = {}
    commit = GitCommitArtifact(
        commit_sha="8899001122334455667788990011223344556677",
        commit_message="chore: remove legacy handler",
        raw_diff=SAMPLE_DELETE_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map=files_map,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "ATOM_DELETE"
    assert chunks[0].path == "src/legacy_handler.py"
    # Ensure deleted file entity was created in files_map to satisfy FK
    assert "src/legacy_handler.py" in files_map


def test_change_type_rename():
    """Verify RENAME change preserves old and new paths."""
    snap_id = uuid.uuid4()
    old_file_id = uuid.uuid4()
    old_file = RepositoryFile(
        id=old_file_id,
        snapshot_id=snap_id,
        path="src/old_name.py",
        filename="old_name.py",
        extension=".py",
        content_hash="abc",
    )
    files_map = {"src/old_name.py": old_file}
    commit = GitCommitArtifact(
        commit_sha="9900112233445566778899001122334455667788",
        commit_message="refactor: rename file",
        raw_diff=SAMPLE_RENAME_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map=files_map,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "ATOM_RENAME"
    assert chunks[0].file_id == old_file_id
    assert chunks[0].provenance["old_file_path"] == "src/old_name.py"


def test_multi_file_commit_mapping():
    """Verify multi-file commits map to separate CodeChunks with distinct file IDs."""
    snap_id = uuid.uuid4()
    auth_file_id = uuid.uuid4()
    models_file_id = uuid.uuid4()

    auth_file = RepositoryFile(
        id=auth_file_id,
        snapshot_id=snap_id,
        path="apps/api/src/auth.py",
        filename="auth.py",
        extension=".py",
        content_hash="111",
    )
    models_file = RepositoryFile(
        id=models_file_id,
        snapshot_id=snap_id,
        path="apps/api/src/models.py",
        filename="models.py",
        extension=".py",
        content_hash="222",
    )
    files_map = {
        "apps/api/src/auth.py": auth_file,
        "apps/api/src/models.py": models_file,
    }

    commit = GitCommitArtifact(
        commit_sha="0011223344556677889900112233445566778899",
        commit_message="feat(account): add token hash and status flag",
        raw_diff=SAMPLE_MULTI_FILE_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map=files_map,
    )

    assert len(chunks) == 2
    paths = {c.path for c in chunks}
    assert "apps/api/src/auth.py" in paths
    assert "apps/api/src/models.py" in paths
    file_ids = {c.file_id for c in chunks}
    assert auth_file_id in file_ids
    assert models_file_id in file_ids


def test_multi_hunk_commit_mapping():
    """Verify multi-hunk commits in one file map to distinct CodeChunks with hunk indices."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/service.py",
        filename="service.py",
        extension=".py",
        content_hash="abc",
    )
    commit = GitCommitArtifact(
        commit_sha="aabbccddeeff00112233445566778899aabbccdd",
        commit_message="refactor(service): dual updates",
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )
    result = CodeAtomDecomposer().decompose(commit)
    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snap_id,
        files_map={"apps/api/src/service.py": repo_file},
    )

    assert len(chunks) == 2
    assert chunks[0].provenance["hunk_index"] == 1
    assert chunks[1].provenance["hunk_index"] == 2
    # Different line ranges
    assert chunks[0].start_line != chunks[1].start_line


def test_deterministic_fingerprint_preservation_and_chunk_id():
    """Verify deterministic fingerprint is preserved and produces identical UUIDs."""
    fp = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    uuid1 = generate_deterministic_chunk_id(fp)
    uuid2 = generate_deterministic_chunk_id(fp)
    assert uuid1 == uuid2
    assert isinstance(uuid1, uuid.UUID)

    commit = GitCommitArtifact(
        commit_sha="bbccddeeff00112233445566778899aabbccddee",
        commit_message="test: fingerprint test",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    change = CodeAtomDecomposer().decompose(commit).changes[0]
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    chunk = map_atomic_code_change_to_code_chunk(change, snap_id, file_id)

    assert chunk.fingerprint == change.fingerprint
    assert chunk.id == generate_deterministic_chunk_id(change.fingerprint)


def test_provenance_preservation():
    """Verify all provenance fields are preserved in CodeChunk."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit_time = datetime(2026, 10, 8, 9, 30, 0, tzinfo=UTC)
    commit = GitCommitArtifact(
        commit_sha="ccddeeff00112233445566778899aabbccddeeff",
        commit_message="feat(provenance): full provenance test",
        author_name="Dev Tester",
        author_email="dev@unotusk.com",
        committed_at=commit_time,
        snapshot_id=snap_id,
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    change = CodeAtomDecomposer().decompose(commit).changes[0]
    chunk = map_atomic_code_change_to_code_chunk(change, snap_id, file_id)

    prov = chunk.provenance
    assert prov["commit_sha"] == "ccddeeff00112233445566778899aabbccddeeff"
    assert prov["author_name"] == "Dev Tester"
    assert prov["author_email"] == "dev@unotusk.com"
    assert prov["file_path"] == "apps/api/src/auth.py"
    assert prov["atom_id"] == change.id
    assert prov["fingerprint"] == change.fingerprint


def test_git_extractor_from_local_repo():
    """Verify extract_git_commit_artifact on a real Git directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize a real git repo
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test Committer"],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "committer@test.com"],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )

        test_file = os.path.join(tmpdir, "main.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    return 'world'\n")

        subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: initial commit for git extractor"],
            cwd=tmpdir,
            check=True,
            capture_output=True,
        )

        artifact = extract_git_commit_artifact(tmpdir)
        assert artifact is not None
        assert artifact.commit_message == "feat: initial commit for git extractor"
        assert artifact.author_name == "Test Committer"
        assert artifact.author_email == "committer@test.com"
        assert len(artifact.commit_sha) == 40
        assert "def hello" in artifact.raw_diff


@pytest.mark.asyncio
async def test_ingestion_service_ingest_commit_atom_changes():
    """Verify IngestionService.ingest_commit_atom_changes with mocked session."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    sym_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/auth.py",
        filename="auth.py",
        extension=".py",
        content_hash="123",
    )
    code_sym = CodeSymbol(
        id=sym_id,
        file_id=file_id,
        name="authenticate_token",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="authenticate_token",
        start_line=10,
        end_line=20,
    )

    # Mock file query response
    mock_file_res = MagicMock()
    mock_file_res.scalars.return_value.all.return_value = [repo_file]

    # Mock symbol query response
    mock_sym_res = MagicMock()
    mock_sym_res.all.return_value = [(code_sym, "apps/api/src/auth.py")]

    # Mock existing chunks query response
    mock_chunks_res = MagicMock()
    mock_chunks_res.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [mock_file_res, mock_sym_res, mock_chunks_res]

    commit = GitCommitArtifact(
        commit_sha="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
        commit_message="feat(ingest): atom chunk integration",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )

    chunks = await IngestionService.ingest_commit_atom_changes(
        session=mock_session,
        snapshot_id=snap_id,
        commit_artifact=commit,
    )

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "ATOM_MODIFY"
    assert chunks[0].commit_sha == "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    assert chunks[0].symbol_id == sym_id
    assert chunks[0].embedding is not None
    assert len(chunks[0].embedding) == 1536
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
