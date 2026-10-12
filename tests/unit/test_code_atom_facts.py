import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from apps.api.src.models.file import RepositoryFile
from apps.api.src.schemas.code_atom import (
    AtomicCodeChange,
    CodeChangeType,
    FactConfidence,
    FactType,
    GitCommitArtifact,
    SemanticCodeFact,
)
from apps.api.src.services.code_atom import (
    CodeAtomDecomposer,
    SemanticFactExtractor,
    generate_fact_fingerprint,
    map_atomic_code_change_to_code_chunk,
    resolve_and_map_atomic_changes,
)
from apps.api.src.services.code_atom.fact_decomposer import validate_grounded_tokens
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate

SAMPLE_AUTH_DIFF = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
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

SAMPLE_COMPOUND_DIFF = """diff --git a/apps/api/src/service.py b/apps/api/src/service.py
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

SAMPLE_DELETED_FILE_DIFF = """diff --git a/apps/api/src/legacy_handler.py b/apps/api/src/legacy_handler.py
deleted file mode 100644
--- a/apps/api/src/legacy_handler.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def handle_legacy():
-    return {"deprecated": True}
"""

SAMPLE_VAGUE_DIFF = """diff --git a/apps/api/src/utils.py b/apps/api/src/utils.py
--- a/apps/api/src/utils.py
+++ b/apps/api/src/utils.py
@@ -5,1 +5,2 @@ def update_metric():
+    x = 1
"""


def test_1_single_code_change_produces_atomic_facts():
    """1. A single code change produces one or more meaningful atomic facts when supported."""
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
        commit_message="feat(auth): add test token prefix bypass",
        raw_diff=SAMPLE_AUTH_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.change_count == 1
    assert result.fact_count >= 1
    change = result.changes[0]
    assert len(change.atomic_facts) >= 1

    fact = change.atomic_facts[0]
    assert isinstance(fact, SemanticCodeFact)
    assert fact.file_path == "apps/api/src/auth.py"
    assert fact.symbol_name == "authenticate_token"
    assert fact.fact_type in (FactType.VALIDATION, FactType.BEHAVIOR)
    assert fact.confidence == FactConfidence.HIGH
    assert fact.is_uncertain is False
    assert "authenticate_token" in fact.statement
    assert "test_" in fact.statement


def test_2_compound_changes_produce_separate_self_contained_facts():
    """2. Compound changes can produce separate self-contained facts."""
    decomposer = CodeAtomDecomposer()
    sym_catalog = [
        {
            "id": uuid.uuid4(),
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
            "end_line": 70,
        },
    ]
    commit = GitCommitArtifact(
        commit_sha="b2c3d4e5f6a1789012345678901234567890bcde",
        commit_message="fix(user): check deleted state and use setter method",
        raw_diff=SAMPLE_COMPOUND_DIFF,
    )
    result = decomposer.decompose(commit, symbol_catalog=sym_catalog)

    assert result.change_count == 2
    hunk1_change = result.changes[0]
    hunk2_change = result.changes[1]

    # Hunk 1: error handling for deleted user
    hunk1_stmts = [f.statement for f in hunk1_change.atomic_facts]
    assert any("InactiveUserException" in s for s in hunk1_stmts)
    assert any("is_deleted" in s for s in hunk1_stmts)

    # Hunk 2: email setter and mark dirty
    hunk2_stmts = [f.statement for f in hunk2_change.atomic_facts]
    assert any("set_email" in s for s in hunk2_stmts)
    assert any("mark_dirty" in s for s in hunk2_stmts)

    # Verify they are separate facts and not one merged blob
    set_email_fact = next(f for f in hunk2_change.atomic_facts if "set_email" in f.statement)
    mark_dirty_fact = next(f for f in hunk2_change.atomic_facts if "mark_dirty" in f.statement)
    assert set_email_fact.id != mark_dirty_fact.id
    assert set_email_fact.fact_type == FactType.STATE_CHANGE


def test_3_facts_preserve_source_provenance():
    """3. Facts preserve source file, symbol, and commit provenance."""
    decomposer = CodeAtomDecomposer()
    commit_time = datetime(2026, 10, 12, 10, 0, 0, tzinfo=UTC)
    snap_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    commit = GitCommitArtifact(
        commit_sha="c3d4e5f6a1b2789012345678901234567890cdef",
        commit_message="feat(auth): test token bypass with full provenance",
        author_name="Alice Engineer",
        author_email="alice@company.com",
        committed_at=commit_time,
        snapshot_id=snap_id,
        project_id=proj_id,
        raw_diff=SAMPLE_AUTH_DIFF,
    )
    result = decomposer.decompose(commit)
    fact = result.facts[0]

    assert fact.commit_sha == "c3d4e5f6a1b2789012345678901234567890cdef"
    assert fact.commit_message == "feat(auth): test token bypass with full provenance"
    assert fact.file_path == "apps/api/src/auth.py"
    assert fact.symbol_name == "authenticate_token"
    assert fact.provenance["commit_sha"] == "c3d4e5f6a1b2789012345678901234567890cdef"
    assert fact.provenance["author_name"] == "Alice Engineer"
    assert fact.provenance["snapshot_id"] == str(snap_id)
    assert fact.provenance["project_id"] == str(proj_id)
    assert len(fact.fingerprint) == 64
    assert fact.id.startswith("fact-code-")


def test_4_unsupported_behavior_not_fabricated_when_evidence_insufficient():
    """4. Unsupported behavior is not fabricated when evidence is insufficient."""
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="d4e5f6a1b2c3789012345678901234567890def0",
        commit_message="chore: update metric helper",
        raw_diff=SAMPLE_VAGUE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.fact_count >= 1
    fact = result.facts[0]
    # Evidence is ambiguous (x = 1), must be marked uncertain
    assert fact.is_uncertain is True
    assert fact.confidence == FactConfidence.UNCERTAIN
    # Must not invent unevidenced terms like payment, database, auth, or network
    for forbidden in ("payment", "authenticate", "database", "api", "network", "token"):
        assert forbidden not in fact.statement.lower()


def test_5_deleted_code_not_represented_as_active_behavior():
    """5. Deleted code is not represented as active behavior."""
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="e5f6a1b2c3d4789012345678901234567890ef01",
        commit_message="chore: remove deprecated legacy handler",
        raw_diff=SAMPLE_DELETED_FILE_DIFF,
    )
    result = decomposer.decompose(commit)

    assert result.fact_count >= 1
    fact = result.facts[0]
    assert fact.fact_type == FactType.REMOVAL
    assert "Removed" in fact.statement
    assert "executes" not in fact.statement.lower()
    assert "handles" not in fact.statement.lower()


def test_6_duplicate_facts_handled_consistently():
    """6. Duplicate facts are handled consistently and deduplicated."""
    extractor = SemanticFactExtractor()
    change = AtomicCodeChange(
        id="atom-1",
        commit_sha="1122334455667788990011223344556677889900",
        commit_message="fix: repeated validation",
        file_path="apps/api/src/auth.py",
        change_type=CodeChangeType.MODIFY,
        symbol_name="authenticate_token",
        raw_content="diff",
        normalized_content="norm",
        added_lines=[
            "if token.startswith('test_'): return True",
            "if token.startswith('test_'): return True",  # duplicate line
        ],
        fingerprint="fp1",
    )
    facts = extractor.extract_facts_deterministic(change)

    # Should only produce one unique fact
    assert len(facts) == 1
    # Reprocessing produces identical fingerprint
    fp1 = facts[0].fingerprint
    fp2 = generate_fact_fingerprint(
        change.commit_sha,
        change.file_path,
        change.symbol_name,
        facts[0].statement,
        facts[0].fact_type,
    )
    assert fp1 == fp2


@pytest.mark.asyncio
async def test_7_llm_provider_failures_degrade_safely():
    """7. LLM/provider failures degrade safely to deterministic extraction."""
    mock_failing_provider = AsyncMock()
    mock_failing_provider.generate_json.side_effect = RuntimeError("External LLM Service Timeout")

    extractor = SemanticFactExtractor(llm_provider=mock_failing_provider)
    change = AtomicCodeChange(
        id="atom-test",
        commit_sha="2233445566778899001122334455667788990011",
        commit_message="feat(auth): test bypass",
        file_path="apps/api/src/auth.py",
        change_type=CodeChangeType.MODIFY,
        symbol_name="authenticate_token",
        raw_content=SAMPLE_AUTH_DIFF,
        normalized_content="norm",
        added_lines=["if token.startswith('test_'):", "    return True"],
        fingerprint="fp-auth",
    )

    # Must degrade gracefully without raising an exception
    facts = await extractor.extract_facts_async(change, use_llm=True)
    assert len(facts) >= 1
    assert any("test_" in f.statement for f in facts)
    assert facts[0].confidence == FactConfidence.HIGH


def test_8_existing_deterministic_decomposition_behavior_remains_compatible():
    """8. Existing deterministic decomposition behavior remains 100% compatible."""
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="3344556677889900112233445566778899001122",
        commit_message="feat(auth): add test token prefix bypass",
        raw_diff=SAMPLE_AUTH_DIFF,
    )
    result = decomposer.decompose(commit)

    # Phase 5 assertions remain intact
    assert result.change_count == 1
    change = result.changes[0]
    assert change.file_path == "apps/api/src/auth.py"
    assert change.change_type == CodeChangeType.MODIFY
    assert len(change.added_lines) == 2
    assert change.new_start_line == 10
    assert change.new_line_count == 6
    assert change.id.startswith("atom-code-")
    assert len(change.fingerprint) == 64


def test_9_reprocessing_idempotency_and_mapping():
    """9. Reprocessing does not break Phase 5 idempotency or entity mapping."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit = GitCommitArtifact(
        commit_sha="4455667788990011223344556677889900112233",
        commit_message="feat(auth): test token",
        raw_diff=SAMPLE_AUTH_DIFF,
    )
    decomposer = CodeAtomDecomposer()
    result1 = decomposer.decompose(commit)
    result2 = decomposer.decompose(commit)

    assert [f.fingerprint for f in result1.facts] == [f.fingerprint for f in result2.facts]
    assert [f.id for f in result1.facts] == [f.id for f in result2.facts]

    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snap_id,
        path="apps/api/src/auth.py",
        filename="auth.py",
        extension=".py",
        content_hash="abc",
    )
    chunks1 = resolve_and_map_atomic_changes(
        changes=result1.changes,
        snapshot_id=snap_id,
        files_map={"apps/api/src/auth.py": repo_file},
        compute_embedding=False,
    )

    chunk = chunks1[0]
    assert "atomic_code_facts" in chunk.provenance
    assert len(chunk.provenance["atomic_code_facts"]) >= 1

    # Re-running with existing chunks by fingerprint reuses without duplicate creation
    existing_map = {chunk.fingerprint: chunk}
    chunks2 = resolve_and_map_atomic_changes(
        changes=result2.changes,
        snapshot_id=snap_id,
        files_map={"apps/api/src/auth.py": repo_file},
        compute_embedding=False,
        existing_chunks_by_fingerprint=existing_map,
    )
    assert chunks2[0].id == chunk.id


def test_10_phases_6_and_7_retain_temporal_and_retrieval_behavior():
    """10. Phases 6 and 7 retain temporal, relationship, and context assembly behavior."""
    snap_id = uuid.uuid4()
    file_id = uuid.uuid4()
    decomposer = CodeAtomDecomposer()
    commit = GitCommitArtifact(
        commit_sha="5566778899001122334455667788990011223344",
        commit_message="feat(auth): test token bypass",
        raw_diff=SAMPLE_AUTH_DIFF,
    )
    result = decomposer.decompose(commit)
    chunk = map_atomic_code_change_to_code_chunk(
        change=result.changes[0],
        snapshot_id=snap_id,
        file_id=file_id,
        compute_embedding=False,
    )

    # Form candidate simulating retriever output
    candidate = RetrievedCandidate(
        candidate_id=f"chunk:{chunk.id}",
        entity_type="CHUNK",
        name=chunk.name,
        path=chunk.path,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        content=chunk.content,
        file_id=file_id,
        signals={"content_match": 1.2},
        metadata={
            "commit_sha": chunk.commit_sha,
            "commit_message": chunk.commit_message,
            "is_current": True,
            "relationship_path": "auth.py -> verify_jwt",
            "relationship_hop": 1,
            "atomic_code_facts": chunk.provenance.get("atomic_code_facts", []),
        },
    )

    ranked = [RankedCandidate(candidate=candidate, score=0.95, matched_reasons=["test"])]
    assembled = ContextAssembler.assemble_context(ranked, max_tokens=1000)

    # Grounded facts must be rendered into prompt context
    assert "Grounded Semantic Facts" in assembled.prompt_context
    assert "authenticate_token" in assembled.prompt_context
    assert "test_" in assembled.prompt_context

    # Evidence item must be JSON-safe and preserve facts
    ev = assembled.evidence_items[0]
    assert ev["is_current"] is True
    assert ev["relationship_hop"] == 1
    assert "atomic_code_facts" in ev
    assert len(ev["atomic_code_facts"]) >= 1


def test_11_llm_grounding_validation_rejects_hallucinations():
    """11. Anti-hallucination validation: Rejects claimed symbols not present in diff."""
    # Diff only has test_ token check
    raw_content = "def authenticate_token(token: str):\n+    if token.startswith('test_'): return True"

    # Hallucinated fact claiming non-existent PaymentGateway call
    fake_statement = "Calls `PaymentGateway.process_charge()` before returning token."
    assert validate_grounded_tokens(fake_statement, raw_content, "auth.py", "authenticate_token") is False

    # Valid grounded fact
    real_statement = "Returns True when `token.startswith('test_')` is satisfied."
    assert validate_grounded_tokens(real_statement, raw_content, "auth.py", "authenticate_token") is True


def test_12_fact_serialization_json_safe():
    """12. Semantic facts serialize cleanly into JSON-compatible dictionaries."""
    fact = SemanticCodeFact(
        id="fact-1",
        statement="Checks user role before issuing token.",
        fact_type=FactType.VALIDATION,
        confidence=FactConfidence.HIGH,
        is_uncertain=False,
        file_path="src/auth.py",
        symbol_name="issue_token",
        commit_sha="abcd1234abcd1234abcd1234abcd1234abcd1234",
        commit_message="fix: role check",
        change_type=CodeChangeType.MODIFY,
        evidenced_lines=["if not role: raise Error()"],
        provenance={"hunk_index": 1},
        fingerprint="fp1",
    )
    dumped = fact.model_dump()
    assert dumped["id"] == "fact-1"
    assert dumped["fact_type"] == "VALIDATION"
    assert dumped["confidence"] == "HIGH"
    assert dumped["is_uncertain"] is False
    assert dumped["evidenced_lines"] == ["if not role: raise Error()"]
