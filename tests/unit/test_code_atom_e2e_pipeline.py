import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.file import RepositoryFile
from apps.api.src.schemas.code_atom import (
    CodeChangeType,
    FactConfidence,
    GitCommitArtifact,
    GitDiffHunk,
    GitFileDiff,
    RelationType,
    TemporalCodeRelation,
)
from apps.api.src.services.code_atom import (
    CodeAtomDecomposer,
    embed_atomic_code_chunk,
    resolve_and_map_atomic_changes,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.graph_expander import RelationshipExpander
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker, RankedCandidate
from apps.api.src.services.context_engine.retriever import RetrievedCandidate
from apps.api.src.services.ingestion_service import IngestionService

SAMPLE_AUTH_DIFF = """diff --git a/apps/api/src/auth.py b/apps/api/src/auth.py
index 1111111..2222222 100644
--- a/apps/api/src/auth.py
+++ b/apps/api/src/auth.py
@@ -10,4 +10,6 @@ def authenticate_token(token: str) -> bool:
     if not token:
         return False
+    if token.startswith("test_"):
+        return True
     return token_validator.verify(token)
"""

SAMPLE_ORDER_DIFF = """diff --git a/apps/api/src/order.py b/apps/api/src/order.py
index 3333333..4444444 100644
--- a/apps/api/src/order.py
+++ b/apps/api/src/order.py
@@ -1,5 +1,10 @@
 class OrderProcessor:
     def process_order(self, order_id: str):
+        InventoryManager.reserve(order_id)
+        PaymentGateway.charge(order_id)
         return True
"""


def test_1_code_change_produces_grounded_semantic_facts():
    """1. A code change produces grounded semantic facts."""
    t_commit = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    commit = GitCommitArtifact(
        commit_sha="c111222333",
        commit_message="Add test token bypass to auth",
        committed_at=t_commit,
        raw_diff=SAMPLE_AUTH_DIFF,
    )
    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit)

    assert result.change_count >= 1
    assert result.fact_count >= 1

    facts = result.facts
    assert any("test_" in f.statement or "token" in f.statement for f in facts)
    for f in facts:
        assert f.file_path == "apps/api/src/auth.py"
        assert f.commit_sha == "c111222333"
        assert len(f.evidenced_lines) > 0


def test_2_supported_facts_yield_structured_temporal_relations():
    """2. Supported facts yield structured temporal relationships."""
    t_commit = datetime(2026, 4, 2, 14, 0, 0, tzinfo=UTC)
    commit = GitCommitArtifact(
        commit_sha="c444555666",
        commit_message="Process orders through inventory and payments",
        committed_at=t_commit,
        raw_diff=SAMPLE_ORDER_DIFF,
    )
    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit)

    assert result.relation_count >= 2
    relations = result.relations

    call_relations = [r for r in relations if r.relation == RelationType.CALLS]
    assert len(call_relations) >= 2

    targets = {r.canonical_object or r.object for r in call_relations}
    assert any("InventoryManager" in t for t in targets)
    assert any("PaymentGateway" in t for t in targets)

    for r in call_relations:
        assert r.t_start == t_commit
        assert r.t_obs == t_commit
        assert r.canonical_subject is not None
        assert r.canonical_object is not None


def test_3_resolver_recognizes_duplicates_and_preserves_verified_history():
    """3. The resolver recognizes duplicates and preserves verified history."""
    t1 = datetime(2026, 1, 10, tzinfo=UTC)
    t2 = datetime(2026, 2, 15, tzinfo=UTC)

    # Change in commit 1
    hunk1 = GitDiffHunk(
        header="@@ -1,4 +1,6 @@",
        section_header="def login():",
        old_start_line=1,
        old_line_count=4,
        new_start_line=1,
        new_line_count=6,
        added_lines=["    AuthService.verify_token(token)"],
    )
    diff1 = GitFileDiff(
        new_path="apps/api/src/service.py",
        change_type=CodeChangeType.MODIFY,
        hunks=[hunk1],
    )
    commit1 = GitCommitArtifact(
        commit_sha="sha-commit-1",
        commit_message="Add token verification",
        committed_at=t1,
        file_diffs=[diff1],
    )

    # Duplicate call in commit 2
    hunk2 = GitDiffHunk(
        header="@@ -10,4 +10,6 @@",
        section_header="def login():",
        old_start_line=10,
        old_line_count=4,
        new_start_line=10,
        new_line_count=6,
        added_lines=["    AuthService.verify_token(token)"],
    )
    diff2 = GitFileDiff(
        new_path="apps/api/src/service.py",
        change_type=CodeChangeType.MODIFY,
        hunks=[hunk2],
    )
    commit2 = GitCommitArtifact(
        commit_sha="sha-commit-2",
        commit_message="Re-authenticate session",
        committed_at=t2,
        file_diffs=[diff2],
    )

    decomposer = CodeAtomDecomposer()
    res1 = decomposer.decompose(commit1)
    res2 = decomposer.decompose(commit2)

    # Reconciling across commits
    all_rels = list(res1.relations) + list(res2.relations)
    from apps.api.src.services.code_atom.relation_resolver import reconcile_code_relationships
    reconciled = reconcile_code_relationships(all_rels)

    # Deduplicated to a single canonical relation with both commit SHAs in history
    matching = [
        r for r in reconciled
        if "AuthService" in (r.canonical_object or r.object)
    ]
    assert len(matching) == 1
    rel = matching[0]
    assert "sha-commit-1" in rel.history_commit_shas
    assert "sha-commit-2" in rel.history_commit_shas
    assert rel.t_start == t1  # Earliest verified start preserved


def test_4_resolved_relations_reach_stored_chunk_provenance():
    """4. Resolved relations reach stored chunk provenance."""
    t_commit = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
    commit = GitCommitArtifact(
        commit_sha="sha-prov-test",
        commit_message="Add payment processing",
        committed_at=t_commit,
        raw_diff=SAMPLE_ORDER_DIFF,
    )
    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit)

    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snapshot_id,
        path="apps/api/src/order.py",
        filename="order.py",
    )

    chunks = resolve_and_map_atomic_changes(
        changes=result.changes,
        snapshot_id=snapshot_id,
        files_map={"apps/api/src/order.py": repo_file},
    )

    assert len(chunks) >= 1
    chunk = chunks[0]

    # Verify provenance dictionary contains resolved temporal relations
    assert "temporal_relations" in chunk.provenance
    rels = chunk.provenance["temporal_relations"]
    assert len(rels) >= 2

    # Verify JSON-safe serialization for PostgreSQL JSONB
    json_str = json.dumps(chunk.provenance)
    loaded = json.loads(json_str)
    assert len(loaded["temporal_relations"]) >= 2
    for r in loaded["temporal_relations"]:
        assert "canonical_subject" in r
        assert "canonical_object" in r
        assert "fingerprint" in r


def test_5_retrieval_and_context_assembly_expose_correct_evidence():
    """5. Retrieval and context assembly expose the correct evidence."""
    t_start = "2026-01-01T00:00:00+00:00"
    cand = RankedCandidate(
        candidate=RetrievedCandidate(
            candidate_id="cand-1",
            entity_type="CHUNK",
            name="process_order (MODIFY)",
            path="apps/api/src/order.py",
            start_line=1,
            end_line=10,
            content="def process_order(): PaymentGateway.charge()",
            file_id=uuid.uuid4(),
            metadata={
                "commit_sha": "sha-order-1",
                "commit_message": "Add payment gateway integration",
                "temporal_relations": [
                    {
                        "subject": "order.py::process_order",
                        "canonical_subject": "apps/api/src/order.py::process_order",
                        "relation": "CALLS",
                        "object": "payments.py::PaymentGateway.charge",
                        "canonical_object": "apps/api/src/payments.py::PaymentGateway.charge",
                        "t_start": t_start,
                        "t_end": None,
                        "has_temporal_conflict": False,
                    },
                    {
                        "subject": "order.py::process_order",
                        "canonical_subject": "apps/api/src/order.py::process_order",
                        "relation": "CALLS",
                        "object": "legacy.py::OldBilling",
                        "canonical_object": "apps/api/src/legacy.py::OldBilling",
                        "t_start": t_start,
                        "t_end": "2026-03-01T00:00:00+00:00",
                        "has_temporal_conflict": False,
                    },
                ],
            },
        ),
        score=0.92,
        matched_reasons=["Semantic match"],
    )

    assembler = ContextAssembler()
    assembled = assembler.assemble_context([cand])

    prompt = assembled.prompt_context
    assert "apps/api/src/order.py::process_order" in prompt
    assert "apps/api/src/payments.py::PaymentGateway.charge" in prompt
    assert "apps/api/src/legacy.py::OldBilling" in prompt
    # Active relation does not have (ended), while ended relation explicitly displays (ended)
    assert "(ended)" in prompt


@pytest.mark.asyncio
async def test_6_repeated_and_incremental_ingestion_no_duplicates():
    """6. Repeated and incremental ingestion do not create duplicates."""
    snapshot_id = uuid.uuid4()
    t1 = datetime(2026, 2, 1, tzinfo=UTC)

    diff = GitFileDiff(
        new_path="apps/api/src/service.py",
        change_type=CodeChangeType.MODIFY,
        hunks=[
            GitDiffHunk(
                header="@@ -1,3 +1,5 @@",
                section_header="def run():",
                old_start_line=1,
                old_line_count=3,
                new_start_line=1,
                new_line_count=5,
                added_lines=["    init_service()"],
            )
        ],
    )
    artifact = GitCommitArtifact(
        commit_sha="sha-dup-test",
        commit_message="Initial service run",
        committed_at=t1,
        file_diffs=[diff],
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        path="apps/api/src/service.py",
        filename="service.py",
    )

    session = AsyncMock()
    session.add = MagicMock()
    # Mock file and symbol lookups
    mock_file_res = MagicMock()
    mock_file_res.scalars.return_value.all.return_value = [repo_file]
    mock_sym_res = MagicMock()
    mock_sym_res.all.return_value = []

    # Mock chunk lookup returning empty on first call, then existing chunk on second call
    existing_chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        file_id=repo_file.id,
        path="apps/api/src/service.py",
        name="run (MODIFY)",
        content="def run(): init_service()",
        start_line=1,
        end_line=5,
        fingerprint="fp-existing",
    )
    mock_chunk_empty = MagicMock()
    mock_chunk_empty.scalars.return_value.all.return_value = []
    mock_chunk_exists = MagicMock()
    mock_chunk_exists.scalars.return_value.all.return_value = [existing_chunk]

    call_count = 0
    def side_effect(stmt):
        nonlocal call_count
        stmt_str = str(stmt)
        if "repository_files" in stmt_str:
            return mock_file_res
        if "code_symbols" in stmt_str:
            return mock_sym_res
        if "code_chunks" in stmt_str:
            call_count += 1
            if call_count == 1:
                return mock_chunk_empty
            return mock_chunk_exists
        res = MagicMock()
        res.scalars.return_value.all.return_value = []
        res.all.return_value = []
        return res

    session.execute.side_effect = side_effect

    # Pass 1: first ingestion creates new chunk
    pass1_chunks = await IngestionService.ingest_commit_atom_changes(
        session=session,
        snapshot_id=snapshot_id,
        commit_artifact=artifact,
    )
    assert len(pass1_chunks) == 1

    # Pass 2: re-ingestion reuses existing chunk and does not add duplicate
    pass2_chunks = await IngestionService.ingest_commit_atom_changes(
        session=session,
        snapshot_id=snapshot_id,
        commit_artifact=artifact,
    )
    assert len(pass2_chunks) == 1


def test_7_missing_timestamps_conflicting_history_deletions_and_renames():
    """7. Missing timestamps, conflicting history, deletions, and renames are handled safely."""
    t_start = datetime(2026, 6, 1, tzinfo=UTC)
    t_conflict_end = datetime(2026, 1, 1, tzinfo=UTC)  # End earlier than start!

    # Conflicting relations
    r_start = TemporalCodeRelation(
        id="rel-start",
        subject="Worker",
        relation=RelationType.CALLS,
        object="Queue",
        t_start=t_start,
        fingerprint="fp-s",
    )
    r_end = TemporalCodeRelation(
        id="rel-end",
        subject="Worker",
        relation=RelationType.CALLS,
        object="Queue",
        t_end=t_conflict_end,
        fingerprint="fp-e",
    )

    from apps.api.src.services.code_atom.relation_resolver import reconcile_code_relationships
    reconciled = reconcile_code_relationships([r_start, r_end])
    assert len(reconciled) == 1
    rec = reconciled[0]
    assert rec.has_temporal_conflict is True
    assert rec.confidence == FactConfidence.UNCERTAIN
    assert rec.t_start == t_start
    assert rec.t_end == t_conflict_end

    # Missing timestamps: no fabrication
    r_none = TemporalCodeRelation(
        id="rel-none",
        subject="Worker",
        relation=RelationType.IMPORTS,
        object="os",
        t_start=None,
        t_end=None,
        fingerprint="fp-none",
    )
    rec_none = reconcile_code_relationships([r_none])
    assert rec_none[0].t_start is None
    assert rec_none[0].t_end is None

    # Renames under rename_history
    rename_history = {"apps/api/old_worker.py": "apps/api/worker.py"}
    r_rename = TemporalCodeRelation(
        id="rel-ren",
        subject="do_work",
        file_path="apps/api/old_worker.py",
        relation=RelationType.DEFINES,
        object="Task",
        fingerprint="fp-ren",
    )
    rec_rename = reconcile_code_relationships([r_rename], rename_history=rename_history)
    assert rec_rename[0].canonical_subject == "apps/api/worker.py::do_work"
    assert "apps/api/old_worker.py::do_work" in rec_rename[0].aliases


@pytest.mark.asyncio
async def test_8_relationship_expansion_uses_resolved_evidence():
    """8. Relationship expansion uses resolved temporal relations appropriately."""
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id="seed-1",
        entity_type="CHUNK",
        name="OrderProcessor.process",
        path="apps/api/src/order.py",
        start_line=1,
        end_line=20,
        content="def process(): PaymentGateway.charge()",
        file_id=file_id,
        signals={"symbol_match": 1.0},
        metadata={
            "temporal_relations": [
                {
                    "subject": "OrderProcessor.process",
                    "canonical_subject": "apps/api/src/order.py::OrderProcessor.process",
                    "relation": "CALLS",
                    "object": "apps/api/src/payments.py::PaymentGateway.charge",
                    "canonical_object": "apps/api/src/payments.py::PaymentGateway.charge",
                    "t_start": "2026-01-01T00:00:00Z",
                    "t_end": None,
                },
                {
                    "subject": "OrderProcessor.process",
                    "canonical_subject": "apps/api/src/order.py::OrderProcessor.process",
                    "relation": "CALLS",
                    "object": "apps/api/src/legacy.py::OldClient",
                    "canonical_object": "apps/api/src/legacy.py::OldClient",
                    "t_start": "2026-01-01T00:00:00Z",
                    "t_end": "2026-03-01T00:00:00Z",
                },
            ]
        },
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.all.return_value = []
    session.execute.return_value = mock_res

    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_expansions=5,
    )

    # Discovered candidates through verified temporal relations
    cand_ids = [c.candidate_id for c in expanded]
    assert any("apps/api/src/payments.py::PaymentGateway.charge" in cid for cid in cand_ids)
    assert any("apps/api/src/legacy.py::OldClient" in cid for cid in cand_ids)

    # Ranker handling: active relation vs ended relation
    # Current-state query
    current_query = analyze_query("How does OrderProcessor process payments?")
    ranked_current = MultiSignalRanker.rank_candidates(expanded, current_query)

    # Historical / evolution query
    history_query = analyze_query("How has the payment implementation changed over time?")
    ranked_history = MultiSignalRanker.rank_candidates(expanded, history_query)

    active_in_current = next(c for c in ranked_current if "PaymentGateway" in c.candidate.name)
    ended_in_current = next(c for c in ranked_current if "OldClient" in c.candidate.name)
    assert active_in_current.score > ended_in_current.score  # Active ranks higher than ended

    ended_in_history = next(c for c in ranked_history if "OldClient" in c.candidate.name)
    assert any("Historical ended relation" in r for r in ended_in_history.matched_reasons)


def test_9_phases_5_to_7_compatibility():
    """9. Phases 5-7 (embedding, temporal supersession, and relationships) remain compatible."""
    chunk = CodeChunk(
        id=uuid.uuid4(),
        path="apps/api/src/auth.py",
        name="verify_token (MODIFY)",
        content="def verify_token(t): return True",
        start_line=1,
        end_line=5,
        commit_sha="c1",
        fingerprint="fp-test-9",
    )
    # Phase 5 embedding compatibility
    embed_atomic_code_chunk(chunk)
    assert chunk.embedding is not None
    assert len(chunk.embedding) == 1536

    # Phase 6 temporal supersession compatibility
    c1 = RetrievedCandidate(
        candidate_id="c1",
        entity_type="CHUNK",
        name="verify_token (MODIFY)",
        path="apps/api/src/auth.py",
        start_line=1,
        end_line=5,
        content="code v1",
        file_id=uuid.uuid4(),
        metadata={"commit_sha": "sha1", "committed_at": "2026-01-01T00:00:00Z"},
    )
    c2 = RetrievedCandidate(
        candidate_id="c2",
        entity_type="CHUNK",
        name="verify_token (MODIFY)",
        path="apps/api/src/auth.py",
        start_line=1,
        end_line=5,
        content="code v2",
        file_id=c1.file_id,
        metadata={"commit_sha": "sha2", "committed_at": "2026-02-01T00:00:00Z"},
    )

    from apps.api.src.services.code_atom.temporal import resolve_temporal_supersession
    resolve_temporal_supersession([c1, c2])
    assert c1.metadata["is_superseded"] is True
    assert c2.metadata["is_current"] is True
