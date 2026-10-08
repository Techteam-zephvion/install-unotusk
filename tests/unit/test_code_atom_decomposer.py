import uuid
from datetime import UTC, datetime

from apps.api.src.schemas.code_atom import (
    CodeChangeType,
    GitCommitArtifact,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.code_atom.fingerprint import (
    generate_code_atom_fingerprint,
    generate_code_atom_id,
)
from apps.api.src.services.code_atom.normalization import normalize_code_change

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
diff --git a/config/settings.yaml b/config/settings.yaml
--- a/config/settings.yaml
+++ b/config/settings.yaml
@@ -5,2 +5,3 @@ app:
   timeout: 30
+  debug: false
"""

SAMPLE_ADDED_FILE_DIFF = """diff --git a/apps/api/src/new_handler.py b/apps/api/src/new_handler.py
new file mode 100644
--- /dev/null
+++ b/apps/api/src/new_handler.py
@@ -0,0 +1,5 @@
+def handle_ping():
+    return {"ping": "pong"}
"""

SAMPLE_DELETED_FILE_DIFF = """diff --git a/apps/api/src/legacy_handler.py b/apps/api/src/legacy_handler.py
deleted file mode 100644
--- a/apps/api/src/legacy_handler.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def handle_legacy():
-    return {"deprecated": True}
"""

SAMPLE_RENAMED_FILE_DIFF = """diff --git a/apps/api/src/old_name.py b/apps/api/src/new_name.py
similarity index 100%
rename from apps/api/src/old_name.py
rename to apps/api/src/new_name.py
"""


def test_1_simple_one_change_diff():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
        commit_message="feat(auth): add test token prefix bypass",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.file_path == "apps/api/src/auth.py"
    assert change.change_type == CodeChangeType.MODIFY
    assert len(change.added_lines) == 2
    assert "if token.startswith(\"test_\"):" in change.added_lines[0]
    assert change.new_start_line == 10
    assert change.new_line_count == 6


def test_2_multi_hunk_diff():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="b2c3d4e5f6a1789012345678901234567890bcde",
        commit_message="fix(user): check deleted state and use setter method",
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 2
    hunk1 = result.changes[0]
    hunk2 = result.changes[1]

    assert hunk1.file_path == "apps/api/src/service.py"
    assert hunk2.file_path == "apps/api/src/service.py"
    assert hunk1.new_start_line == 15
    assert hunk2.new_start_line == 50
    assert "user.is_deleted" in "\n".join(hunk1.added_lines)
    assert "user.set_email(new_email)" in "\n".join(hunk2.added_lines)
    assert hunk1.id != hunk2.id


def test_3_multi_file_commit():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="c3d4e5f6a1b2789012345678901234567890cdef",
        commit_message="feat(core): update auth, models, and config",
        raw_diff=SAMPLE_MULTI_FILE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 3
    assert "apps/api/src/auth.py" in result.files_affected
    assert "apps/api/src/models.py" in result.files_affected
    assert "config/settings.yaml" in result.files_affected


def test_4_symbol_associated_change():
    decomposer = CodeAtomDecomposer()
    sym_uuid = uuid.uuid4()
    catalog = [
        {
            "id": sym_uuid,
            "name": "get_user_profile",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/service.py",
            "start_line": 10,
            "end_line": 30,
        },
        {
            "id": uuid.uuid4(),
            "name": "update_user_email",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/service.py",
            "start_line": 40,
            "end_line": 65,
        },
    ]

    commit = GitCommitArtifact(
        commit_sha="d4e5f6a1b2c3789012345678901234567890def0",
        commit_message="refactor(user): update profiles and email setters",
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )
    result = decomposer.decompose(commit, symbol_catalog=catalog)

    assert result.change_count == 2
    assert result.changes[0].symbol_name == "get_user_profile"
    assert result.changes[0].symbol_id == sym_uuid
    assert result.changes[0].symbol_type == "FUNCTION"
    assert result.changes[1].symbol_name == "update_user_email"


def test_5_added_file():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="e5f6a1b2c3d4789012345678901234567890ef01",
        commit_message="feat(ping): add ping handler",
        raw_diff=SAMPLE_ADDED_FILE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.change_type == CodeChangeType.ADD
    assert change.file_path == "apps/api/src/new_handler.py"
    assert "handle_ping" in "\n".join(change.added_lines)


def test_6_modified_file():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="f6a1b2c3d4e5789012345678901234567890f012",
        commit_message="fix(auth): update token verification",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 1
    assert result.changes[0].change_type == CodeChangeType.MODIFY


def test_7_deleted_file():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="11223344556677889900aabbccddeeff00112233",
        commit_message="chore(clean): remove legacy handler",
        raw_diff=SAMPLE_DELETED_FILE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.change_type == CodeChangeType.DELETE
    assert change.file_path == "apps/api/src/legacy_handler.py"


def test_8_renamed_file():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="22334455667788990011aabbccddeeff11223344",
        commit_message="refactor(rename): rename old module to new",
        raw_diff=SAMPLE_RENAMED_FILE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.change_type == CodeChangeType.RENAME
    assert change.file_path == "apps/api/src/new_name.py"
    assert change.old_file_path == "apps/api/src/old_name.py"


def test_9_commit_message_preserved():
    decomposer = CodeAtomDecomposer()
    msg = "feat(payment): integrate stripe webhook validation [PROJ-104]"
    commit = GitCommitArtifact(
        commit_sha="33445566778899001122aabbccddeeff22334455",
        commit_message=msg,
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )
    result = decomposer.decompose(commit)

    for change in result.changes:
        assert change.commit_message == msg
        assert change.provenance["commit_message"] == msg


def test_10_file_provenance_preserved():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="44556677889900112233aabbccddeeff33445566",
        commit_message="refactor(files): path audit",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit)
    change = result.changes[0]

    prov = change.provenance
    assert prov["file_path"] == "apps/api/src/auth.py"
    assert prov["old_line_range"] == (10, 4)
    assert prov["new_line_range"] == (10, 6)
    assert prov["change_type"] == "MODIFY"


def test_11_symbol_provenance_preserved():
    decomposer = CodeAtomDecomposer()
    sym_id = uuid.uuid4()
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
        commit_sha="55667788990011223344aabbccddeeff44556677",
        commit_message="feat(auth): link symbol",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit, symbol_catalog=catalog)
    change = result.changes[0]

    assert change.provenance["symbol_name"] == "authenticate_token"
    assert change.provenance["symbol_id"] == str(sym_id)
    assert change.provenance["symbol_type"] == "FUNCTION"


def test_12_normalization_determinism():
    added1 = ["    if token.startswith('test_'):  \r\n", "        return True\t"]
    added2 = ["    if token.startswith('test_'):", "        return True"]

    norm1 = normalize_code_change("apps/api/src/auth.py", "MODIFY", "auth_tok", added1, [], 10, 2, 10, 4)
    norm2 = normalize_code_change("apps\\api\\src\\auth.py", "modify", "auth_tok", added2, [], 10, 2, 10, 4)

    assert norm1 == norm2


def test_13_fingerprint_determinism():
    norm = "PATH:auth.py\nTYPE:MODIFY\nSYMBOL:test\nADDED:\nx = 1"
    fp1 = generate_code_atom_fingerprint("abcd1234abcd1234abcd1234abcd1234abcd1234", "auth.py", "MODIFY", norm, "test", 1)
    fp2 = generate_code_atom_fingerprint("abcd1234abcd1234abcd1234abcd1234abcd1234", "auth.py", "modify", norm, "test", 1)

    assert fp1 == fp2
    assert len(fp1) == 64
    id1 = generate_code_atom_id(fp1)
    assert id1.startswith("atom-code-")


def test_14_repeated_processing_produces_stable_ids():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="66778899001122334455aabbccddeeff55667788",
        commit_message="test(stability): idempotency check",
        raw_diff=SAMPLE_MULTI_HUNK_DIFF,
    )

    run1 = decomposer.decompose(commit)
    run2 = decomposer.decompose(commit)
    run3 = decomposer.decompose(commit)

    assert [c.id for c in run1.changes] == [c.id for c in run2.changes] == [c.id for c in run3.changes]
    assert [c.fingerprint for c in run1.changes] == [c.fingerprint for c in run2.changes] == [c.fingerprint for c in run3.changes]
    assert [c.normalized_content for c in run1.changes] == [c.normalized_content for c in run2.changes] == [c.normalized_content for c in run3.changes]


def test_15_no_loss_of_original_source_change_content():
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="77889900112233445566aabbccddeeff66778899",
        commit_message="test(content): preserve raw patch",
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit)
    change = result.changes[0]

    assert "@@ -10,4 +10,6 @@" in change.raw_content
    assert "+    if token.startswith(\"test_\"):" in change.raw_content
    assert "+        return True" in change.raw_content


def test_16_atomic_units_retain_parent_commit_context():
    decomposer = CodeAtomDecomposer()
    commit_time = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)
    commit = GitCommitArtifact(
        commit_sha="88990011223344556677aabbccddeeff77889900",
        commit_message="feat(context): complete parent metadata test",
        author_name="Alice Engineer",
        author_email="alice@company.com",
        committed_at=commit_time,
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit)
    change = result.changes[0]

    assert change.commit_sha == "88990011223344556677aabbccddeeff77889900"
    assert change.provenance["author_name"] == "Alice Engineer"
    assert change.provenance["author_email"] == "alice@company.com"
    assert change.provenance["committed_at"] == "2026-10-07T12:00:00+00:00"


def test_17_snapshot_project_association_preserved():
    decomposer = CodeAtomDecomposer()
    snap_id = uuid.uuid4()
    proj_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    commit = GitCommitArtifact(
        commit_sha="99001122334455667788aabbccddeeff88990011",
        commit_message="feat(scope): test snapshot and project binding",
        snapshot_id=snap_id,
        project_id=proj_id,
        repository_id=repo_id,
        raw_diff=SAMPLE_ONE_CHANGE_DIFF,
    )
    result = decomposer.decompose(commit)
    change = result.changes[0]

    assert change.snapshot_id == snap_id
    assert change.project_id == proj_id
    assert change.provenance["snapshot_id"] == str(snap_id)
    assert change.provenance["project_id"] == str(proj_id)
    assert change.provenance["repository_id"] == str(repo_id)
