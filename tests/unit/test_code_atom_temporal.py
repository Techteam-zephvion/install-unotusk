import json
import uuid
from datetime import UTC, datetime

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.services.code_atom.chunk_mapper import (
    generate_deterministic_chunk_id,
)
from apps.api.src.services.code_atom.embedding import (
    DevelopmentCodeEmbeddingBackend,
    format_atom_code_embedding_input,
    generate_code_embedding,
)
from apps.api.src.services.code_atom.temporal import (
    parse_candidate_timestamp,
    resolve_temporal_supersession,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import (
    RetrievedCandidate,
)


def _create_mock_chunk(
    file_path: str,
    symbol_name: str | None,
    change_type: str,
    commit_sha: str,
    commit_msg: str,
    committed_at: str | None,
    content: str,
    start_line: int = 1,
    end_line: int = 20,
    snapshot_id: uuid.UUID | None = None,
    file_id: uuid.UUID | None = None,
) -> CodeChunk:
    snap_id = snapshot_id or uuid.uuid4()
    f_id = file_id or uuid.uuid4()
    sym_id = uuid.uuid4() if symbol_name else None
    c_name = f"{symbol_name} ({change_type})" if symbol_name else f"{file_path} ({change_type})"
    chunk_type = f"ATOM_{change_type}"
    fingerprint = f"fp_{commit_sha[:8]}_{file_path}_{symbol_name}_{change_type}"
    chunk_id = generate_deterministic_chunk_id(fingerprint)

    prov = {
        "commit_sha": commit_sha,
        "commit_message": commit_msg,
        "author_name": "Developer",
        "committed_at": committed_at,
        "file_path": file_path,
        "symbol_name": symbol_name,
        "change_type": change_type,
        "fingerprint": fingerprint,
    }

    emb = generate_code_embedding(
        format_atom_code_embedding_input(
            commit_message=commit_msg,
            content=content,
            file_path=file_path,
            symbol_name=symbol_name,
        ),
        backend=DevelopmentCodeEmbeddingBackend(),
    )

    created_dt = (
        datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
        if committed_at
        else datetime.now(UTC)
    )

    return CodeChunk(
        id=chunk_id,
        snapshot_id=snap_id,
        file_id=f_id,
        symbol_id=sym_id,
        chunk_type=chunk_type,
        name=c_name,
        path=file_path,
        content=content,
        start_line=start_line,
        end_line=end_line,
        commit_sha=commit_sha,
        commit_message=commit_msg,
        fingerprint=fingerprint,
        provenance=prov,
        embedding=emb,
        created_at=created_dt,
    )


def _to_candidate(chunk: CodeChunk, initial_signals: dict[str, float] | None = None) -> RetrievedCandidate:
    sig = initial_signals or {"content_match": 1.0, "vector_similarity": 0.8}
    prov = chunk.provenance or {}
    meta = {
        "commit_sha": chunk.commit_sha,
        "commit_message": chunk.commit_message,
        "fingerprint": chunk.fingerprint,
        "provenance": prov,
        "chunk_type": chunk.chunk_type,
        "committed_at": prov.get("committed_at"),
        "author": prov.get("author_name"),
        "symbol_name": prov.get("symbol_name"),
        "change_type": prov.get("change_type"),
    }
    return RetrievedCandidate(
        candidate_id=f"chunk:{chunk.id}",
        entity_type="CHUNK",
        name=chunk.name,
        path=chunk.path,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        content=chunk.content,
        file_id=chunk.file_id,
        symbol_id=chunk.symbol_id,
        signals=sig,
        metadata=meta,
    )


# =========================================================================
# TEST 1: Two or more commits modifying same file: latest applicable evidence
#         preferred for current-code queries
# =========================================================================
def test_1_two_or_more_commits_modifying_same_file_latest_preferred_for_current_query():
    shared_file_id = uuid.uuid4()
    shared_snap_id = uuid.uuid4()

    # Commit 1: earlier commit (2026-10-01)
    chunk_v1 = _create_mock_chunk(
        file_path="apps/api/src/services/user_service.py",
        symbol_name="UserService",
        change_type="ADD",
        commit_sha="1111111111111111111111111111111111111111",
        commit_msg="feat: initial UserService implementation",
        committed_at="2026-10-01T10:00:00Z",
        content="class UserService:\n    def validate(self, u):\n        return False\n",
        file_id=shared_file_id,
        snapshot_id=shared_snap_id,
    )

    # Commit 2: later commit (2026-10-05)
    chunk_v2 = _create_mock_chunk(
        file_path="apps/api/src/services/user_service.py",
        symbol_name="UserService",
        change_type="MODIFY",
        commit_sha="2222222222222222222222222222222222222222",
        commit_msg="fix: update UserService validation logic to support active users",
        committed_at="2026-10-05T15:30:00Z",
        content="class UserService:\n    def validate(self, u):\n        return u.is_active and True\n",
        file_id=shared_file_id,
        snapshot_id=shared_snap_id,
    )

    cand_v1 = _to_candidate(chunk_v1)
    cand_v2 = _to_candidate(chunk_v2)

    # Standard current-state query
    analyzed = analyze_query("how does UserService validate users")
    assert not analyzed.is_temporal

    ranked = MultiSignalRanker.rank_candidates([cand_v1, cand_v2], analyzed)

    # Verify latest applicable evidence is preferred
    assert len(ranked) >= 1
    top_cand = ranked[0].candidate
    assert top_cand.metadata["commit_sha"] == "2222222222222222222222222222222222222222"
    assert top_cand.metadata.get("is_current") is True
    assert top_cand.metadata.get("is_superseded") is False

    # Verify earlier commit is marked as superseded
    assert cand_v1.metadata.get("is_superseded") is True
    assert cand_v1.metadata.get("superseded_by_sha") == "2222222222222222222222222222222222222222"
    assert ranked[0].score > (ranked[1].score if len(ranked) > 1 else 0.0)


# =========================================================================
# TEST 2: Historical queries retrieve earlier versions with commit context
# =========================================================================
def test_2_historical_queries_retrieve_earlier_versions_with_commit_context():
    shared_file_id = uuid.uuid4()
    shared_snap_id = uuid.uuid4()

    chunk_v1 = _create_mock_chunk(
        file_path="apps/api/src/services/auth_service.py",
        symbol_name="AuthService",
        change_type="ADD",
        commit_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        commit_msg="feat: add basic AuthService with session auth",
        committed_at="2026-09-15T09:00:00Z",
        content="class AuthService:\n    def login(self): pass\n",
        file_id=shared_file_id,
        snapshot_id=shared_snap_id,
    )

    chunk_v2 = _create_mock_chunk(
        file_path="apps/api/src/services/auth_service.py",
        symbol_name="AuthService",
        change_type="MODIFY",
        commit_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        commit_msg="refactor: migrate AuthService from sessions to JWT tokens",
        committed_at="2026-10-02T14:00:00Z",
        content="class AuthService:\n    def login(self): return create_jwt_token()\n",
        file_id=shared_file_id,
        snapshot_id=shared_snap_id,
    )

    cand_v1 = _to_candidate(chunk_v1)
    cand_v2 = _to_candidate(chunk_v2)

    # Historical / evolution query
    query = "how did AuthService evolve over time in commit history"
    analyzed = analyze_query(query)
    assert analyzed.is_temporal is True
    assert analyzed.temporal_intent == "EVOLUTION"
    assert "evolve" in analyzed.temporal_keywords or "commit" in analyzed.temporal_keywords or "history" in analyzed.temporal_keywords

    ranked = MultiSignalRanker.rank_candidates([cand_v1, cand_v2], analyzed)

    # Both earlier and later versions should be preserved and scored highly
    assert len(ranked) == 2
    cands_returned = [r.candidate for r in ranked]
    shas = {c.metadata["commit_sha"] for c in cands_returned}
    assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" in shas
    assert "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" in shas

    # Earlier version is NOT demoted; has historical evidence reasons
    reasons_v1 = next(r.matched_reasons for r in ranked if r.candidate.metadata["commit_sha"] == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    assert any("Historical" in reason for reason in reasons_v1)

    # Context assembly preserves commit SHA and timestamp
    assembled = ContextAssembler.assemble_context(ranked)
    assert "Commit: aaaaaaaa" in assembled.prompt_context
    assert "Commit: bbbbbbbb" in assembled.prompt_context
    assert "Date: 2026-09-15T09:00:00Z" in assembled.prompt_context
    assert "Date: 2026-10-02T14:00:00Z" in assembled.prompt_context


# =========================================================================
# TEST 3: Deletions (ATOM_DELETE) do not make deleted code appear current
# =========================================================================
def test_3_deletions_do_not_make_deleted_code_appear_current():
    shared_file_id = uuid.uuid4()
    shared_snap_id = uuid.uuid4()

    chunk_add = _create_mock_chunk(
        file_path="apps/api/src/services/legacy_payment.py",
        symbol_name="LegacyPaymentService",
        change_type="ADD",
        commit_sha="c111111111111111111111111111111111111111",
        commit_msg="feat: implement legacy payment provider",
        committed_at="2026-08-01T12:00:00Z",
        content="class LegacyPaymentService:\n    def charge(self): pass\n",
        file_id=shared_file_id,
        snapshot_id=shared_snap_id,
    )

    chunk_del = _create_mock_chunk(
        file_path="apps/api/src/services/legacy_payment.py",
        symbol_name="LegacyPaymentService",
        change_type="DELETE",
        commit_sha="c222222222222222222222222222222222222222",
        commit_msg="chore: delete deprecated LegacyPaymentService",
        committed_at="2026-09-20T17:00:00Z",
        content="--- legacy_payment.py\n+++ /dev/null\n-class LegacyPaymentService:\n",
        file_id=shared_file_id,
        snapshot_id=shared_snap_id,
    )

    active_service = _create_mock_chunk(
        file_path="apps/api/src/services/modern_payment.py",
        symbol_name="ModernPaymentService",
        change_type="ADD",
        commit_sha="c333333333333333333333333333333333333333",
        commit_msg="feat: modern stripe payment provider",
        committed_at="2026-09-25T11:00:00Z",
        content="class ModernPaymentService:\n    def charge(self): return True\n",
        file_id=uuid.uuid4(),
        snapshot_id=shared_snap_id,
    )

    cands = [
        _to_candidate(chunk_add),
        _to_candidate(chunk_del),
        _to_candidate(active_service),
    ]

    # Current code query
    analyzed_current = analyze_query("how does payment charge work in services")
    ranked_current = MultiSignalRanker.rank_candidates(cands, analyzed_current)

    # Active payment service must decisively beat the deleted service
    assert ranked_current[0].candidate.metadata["symbol_name"] == "ModernPaymentService"

    # Both deleted chunk and pre-deletion chunk are marked deleted / superseded
    cand_add_ranked = next(r.candidate for r in ranked_current if r.candidate.metadata["commit_sha"] == "c111111111111111111111111111111111111111")
    assert cand_add_ranked.metadata.get("is_deleted") is True
    assert cand_add_ranked.metadata.get("is_superseded") is True

    # Temporal query: asking when legacy service was removed
    analyzed_hist = analyze_query("when was LegacyPaymentService deleted from codebase")
    assert analyzed_hist.is_temporal is True
    ranked_hist = MultiSignalRanker.rank_candidates(cands, analyzed_hist)

    # Deletion event is retrieved and ranked as valid historical evidence
    del_cand = next(r.candidate for r in ranked_hist if r.candidate.metadata["commit_sha"] == "c222222222222222222222222222222222222222")
    assert del_cand.metadata.get("is_deleted") is True
    assembled = ContextAssembler.assemble_context(ranked_hist)
    assert "DELETED" in assembled.prompt_context


# =========================================================================
# TEST 4: Renames (ATOM_RENAME) preserve historical relationships without
#         duplicate current evidence
# =========================================================================
def test_4_renames_preserve_historical_relationships_without_duplicate_current_evidence():
    shared_snap_id = uuid.uuid4()
    f_old_id = uuid.uuid4()
    f_new_id = uuid.uuid4()

    # Pre-rename chunk
    chunk_pre = _create_mock_chunk(
        file_path="apps/api/src/services/old_helper.py",
        symbol_name="Helper",
        change_type="ADD",
        commit_sha="r111111111111111111111111111111111111111",
        commit_msg="feat: add helper utilities",
        committed_at="2026-09-01T10:00:00Z",
        content="class Helper:\n    def run(self): return 1\n",
        file_id=f_old_id,
        snapshot_id=shared_snap_id,
    )

    # Rename chunk
    chunk_rename = _create_mock_chunk(
        file_path="apps/api/src/services/core_helper.py",
        symbol_name="Helper",
        change_type="RENAME",
        commit_sha="r222222222222222222222222222222222222222",
        commit_msg="refactor: rename old_helper.py to core_helper.py",
        committed_at="2026-09-10T15:00:00Z",
        content="class Helper:\n    def run(self): return 1\n",
        file_id=f_new_id,
        snapshot_id=shared_snap_id,
    )
    chunk_rename.provenance["old_file_path"] = "apps/api/src/services/old_helper.py"

    cand_pre = _to_candidate(chunk_pre)
    cand_rename = _to_candidate(chunk_rename)
    cand_rename.metadata["old_file_path"] = "apps/api/src/services/old_helper.py"

    # Current query: new path should be preferred without duplicate current representation
    analyzed_cur = analyze_query("how does Helper run work")
    ranked = MultiSignalRanker.rank_candidates([cand_pre, cand_rename], analyzed_cur)

    assert len(ranked) >= 1
    top = ranked[0].candidate
    assert top.path == "apps/api/src/services/core_helper.py"
    assert top.metadata.get("is_current") is True
    assert cand_pre.metadata.get("is_superseded") is True
    assert cand_pre.metadata.get("renamed_to") == "apps/api/src/services/core_helper.py"
    assert cand_rename.metadata.get("renamed_from") == "apps/api/src/services/old_helper.py"


# =========================================================================
# TEST 5: Changes to unrelated files do not supersede each other
# =========================================================================
def test_5_changes_to_unrelated_files_do_not_supersede_each_other():
    shared_snap_id = uuid.uuid4()

    chunk_auth = _create_mock_chunk(
        file_path="apps/api/src/services/auth.py",
        symbol_name="AuthService",
        change_type="MODIFY",
        commit_sha="auth11111111111111111111111111111111111",
        commit_msg="feat: update auth logic",
        committed_at="2026-09-01T10:00:00Z",
        content="def authenticate(): pass",
        file_id=uuid.uuid4(),
        snapshot_id=shared_snap_id,
    )

    chunk_billing = _create_mock_chunk(
        file_path="apps/api/src/services/billing.py",
        symbol_name="BillingService",
        change_type="MODIFY",
        commit_sha="bill22222222222222222222222222222222222",
        commit_msg="feat: update billing logic",
        committed_at="2026-10-01T10:00:00Z",
        content="def charge_customer(): pass",
        file_id=uuid.uuid4(),
        snapshot_id=shared_snap_id,
    )

    cand_auth = _to_candidate(chunk_auth)
    cand_billing = _to_candidate(chunk_billing)

    analyzed = analyze_query("how does authenticate and charge_customer work")
    ranked = MultiSignalRanker.rank_candidates([cand_auth, cand_billing], analyzed)
    assert len(ranked) == 2

    # Neither file should be marked superseded by the other
    assert cand_auth.metadata.get("is_superseded") is False
    assert cand_billing.metadata.get("is_superseded") is False


# =========================================================================
# TEST 6: Missing temporal metadata handled safely without crash or fabricated dates
# =========================================================================
def test_6_missing_temporal_metadata_handled_safely_without_crash_or_fabricated_dates():
    chunk_no_meta = _create_mock_chunk(
        file_path="apps/api/src/services/unknown.py",
        symbol_name=None,
        change_type="MODIFY",
        commit_sha="none11111111111111111111111111111111111",
        commit_msg="update without timestamp",
        committed_at=None,
        content="def mystery(): pass",
    )
    chunk_no_meta.created_at = None
    chunk_no_meta.provenance = {}

    cand = _to_candidate(chunk_no_meta)
    cand.metadata = {"commit_sha": "none111"}  # Minimal metadata, no timestamps

    # Verify parse_candidate_timestamp does not crash or fabricate dates
    parsed_ts = parse_candidate_timestamp(cand)
    assert parsed_ts is None

    # Ranking and supersession resolution must execute safely
    analyzed = analyze_query("what does mystery do")
    ranked = MultiSignalRanker.rank_candidates([cand], analyzed)
    assert len(ranked) == 1
    assert ranked[0].candidate.metadata.get("is_superseded") is False

    # Assembled context formats cleanly without fake dates
    assembled = ContextAssembler.assemble_context(ranked)
    assert "Date:" not in assembled.prompt_context
    assert assembled.candidate_count == 1


# =========================================================================
# TEST 7: Incremental re-ingestion remains idempotent and checkpoint-safe
# =========================================================================
def test_7_incremental_reingestion_remains_idempotent_and_checkpoint_safe():
    shared_snap = uuid.uuid4()
    f_id = uuid.uuid4()

    chunk_a = _create_mock_chunk(
        file_path="apps/api/src/services/cache.py",
        symbol_name="CacheManager",
        change_type="ADD",
        commit_sha="c001111111111111111111111111111111111111",
        commit_msg="feat: cache manager initial",
        committed_at="2026-10-01T12:00:00Z",
        content="class CacheManager: pass",
        file_id=f_id,
        snapshot_id=shared_snap,
    )

    chunk_b = _create_mock_chunk(
        file_path="apps/api/src/services/cache.py",
        symbol_name="CacheManager",
        change_type="MODIFY",
        commit_sha="c002222222222222222222222222222222222222",
        commit_msg="feat: cache manager redis backend",
        committed_at="2026-10-02T12:00:00Z",
        content="class CacheManager: redis = True",
        file_id=f_id,
        snapshot_id=shared_snap,
    )

    # First resolution run
    cands_run1 = [_to_candidate(chunk_a), _to_candidate(chunk_b)]
    resolved_1 = resolve_temporal_supersession(cands_run1)
    cand_a_1 = next(c for c in resolved_1 if c.metadata["commit_sha"] == chunk_a.commit_sha)
    cand_b_1 = next(c for c in resolved_1 if c.metadata["commit_sha"] == chunk_b.commit_sha)

    # Second idempotent run with fresh candidate instances
    cands_run2 = [_to_candidate(chunk_a), _to_candidate(chunk_b)]
    resolved_2 = resolve_temporal_supersession(cands_run2)
    cand_a_2 = next(c for c in resolved_2 if c.metadata["commit_sha"] == chunk_a.commit_sha)
    cand_b_2 = next(c for c in resolved_2 if c.metadata["commit_sha"] == chunk_b.commit_sha)

    # Both runs must produce identical supersession attributes
    assert cand_a_1.metadata["is_superseded"] == cand_a_2.metadata["is_superseded"] is True
    assert cand_b_1.metadata["is_current"] == cand_b_2.metadata["is_current"] is True
    assert cand_a_1.metadata["superseded_by_sha"] == cand_a_2.metadata["superseded_by_sha"] == chunk_b.commit_sha


# =========================================================================
# TEST 8: Existing ATOM retrieval, ranking, assembly, and serialization
#         remain compatible
# =========================================================================
def test_8_existing_retrieval_ranking_assembly_and_serialization_remain_compatible():
    snap_id = uuid.uuid4()
    f_id = uuid.uuid4()

    atom_chunk = _create_mock_chunk(
        file_path="apps/api/src/services/dispatcher.py",
        symbol_name="dispatch_event",
        change_type="ADD",
        commit_sha="d1234567890abcdef1234567890abcdef1234567",
        commit_msg="feat: dispatch event handler",
        committed_at="2026-10-08T08:00:00Z",
        content="def dispatch_event(event): return True",
        file_id=f_id,
        snapshot_id=snap_id,
    )

    atom_cand = _to_candidate(atom_chunk)

    # Standard non-ATOM file candidate
    file_cand = RetrievedCandidate(
        candidate_id=f"file:{f_id}",
        entity_type="FILE",
        name="dispatcher.py",
        path="apps/api/src/services/dispatcher.py",
        start_line=1,
        end_line=50,
        content="File content",
        file_id=f_id,
        signals={"file_match": 1.2},
    )

    # Standard non-ATOM dependency candidate
    dep_cand = RetrievedCandidate(
        candidate_id=f"dep:{uuid.uuid4()}",
        entity_type="DEPENDENCY",
        name="redis",
        path="apps/api/src/services/dispatcher.py",
        start_line=1,
        end_line=1,
        content="import redis",
        file_id=f_id,
        signals={"dependency_match": 0.8},
    )

    analyzed = analyze_query("how does dispatcher dispatch_event work with redis")
    ranked = MultiSignalRanker.rank_candidates([atom_cand, file_cand, dep_cand], analyzed)

    # All candidate types survive ranking
    types_present = {r.candidate.entity_type for r in ranked}
    assert "CHUNK" in types_present
    assert "FILE" in types_present
    assert "DEPENDENCY" in types_present

    # Assembled context generates cleanly
    assembled = ContextAssembler.assemble_context(ranked)
    assert assembled.candidate_count == 3
    assert len(assembled.evidence_items) == 3

    # Evidence items must be 100% JSON serializable
    json_str = json.dumps(assembled.evidence_items)
    assert json_str is not None
    loaded = json.loads(json_str)
    assert len(loaded) == 3
    atom_item = next(item for item in loaded if item["type"] == "chunk")
    assert atom_item["commit_sha"] == atom_chunk.commit_sha
    assert atom_item["is_current"] is True
