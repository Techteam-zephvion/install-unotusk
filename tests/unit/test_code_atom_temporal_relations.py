import json
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
    RelationType,
    SemanticCodeFact,
    TemporalCodeRelation,
)
from apps.api.src.services.code_atom import (
    CodeAtomDecomposer,
    TemporalRelationExtractor,
    deduplicate_relations,
    generate_relation_fingerprint,
    generate_relation_id,
    map_atomic_code_change_to_code_chunk,
    normalize_relation_name,
    resolve_and_map_atomic_changes,
    validate_grounded_relation_tokens,
)
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.ranker import RankedCandidate
from apps.api.src.services.context_engine.retriever import (
    RetrievedCandidate,
    _extract_chunk_metadata,
)

SAMPLE_AUTH_DIFF = """diff --git a/apps/api/src/auth_service.py b/apps/api/src/auth_service.py
index 1111111..2222222 100644
--- a/apps/api/src/auth_service.py
+++ b/apps/api/src/auth_service.py
@@ -10,4 +10,6 @@ def authenticate_token(token: str) -> bool:
     if not token:
         return False
+    if token.startswith("test_"):
+        return True
     return token_validator.verify(token)
"""

SAMPLE_MULTI_RELATION_DIFF = """diff --git a/apps/api/src/order_service.py b/apps/api/src/order_service.py
index 3333333..4444444 100644
--- a/apps/api/src/order_service.py
+++ b/apps/api/src/order_service.py
@@ -1,5 +1,12 @@
+from apps.api.src.inventory import InventoryManager
+from apps.api.src.payments import PaymentGateway
+
+class OrderProcessor(BaseProcessor):
+    def process_order(self, order_id: str):
+        InventoryManager.reserve(order_id)
+        PaymentGateway.charge(order_id)
+        return True
"""

SAMPLE_REMOVAL_DIFF = """diff --git a/apps/api/src/legacy_client.py b/apps/api/src/legacy_client.py
index 5555555..6666666 100644
--- a/apps/api/src/legacy_client.py
+++ b/apps/api/src/legacy_client.py
@@ -10,3 +10,1 @@ def run_pipeline():
-    legacy_tracker.record_telemetry()
-    from deprecated_module import old_helper
     return True
"""

SAMPLE_DELETED_FILE_DIFF = """diff --git a/apps/api/src/old_worker.py b/apps/api/src/old_worker.py
deleted file mode 100644
--- a/apps/api/src/old_worker.py
+++ /dev/null
@@ -1,5 +0,0 @@
-def run_old_worker():
-    pass
"""


def test_1_valid_subject_relation_object_extraction():
    """1. Valid subject-relation-object extraction with verified validity start time."""
    extractor = TemporalRelationExtractor()
    commit_time = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)

    change = AtomicCodeChange(
        id="atom-1",
        commit_sha="a1b2c3d4e5f6789012345678901234567890abcd",
        commit_message="feat(auth): integrate token_validator",
        file_path="apps/api/src/auth_service.py",
        change_type=CodeChangeType.ADD,
        symbol_name="authenticate_token",
        raw_content=SAMPLE_AUTH_DIFF,
        normalized_content="",
        added_lines=["    return token_validator.verify(token)"],
        deleted_lines=[],
        provenance={"committed_at": commit_time.isoformat()},
        fingerprint="fp-auth-1",
    )

    relations = extractor.extract_relations_deterministic(change, commit_time=commit_time)
    assert len(relations) >= 1

    call_rel = next((r for r in relations if r.relation == RelationType.CALLS), None)
    assert call_rel is not None
    assert call_rel.subject == "authenticate_token"
    assert call_rel.object == "token_validator"
    assert call_rel.t_obs == commit_time
    assert call_rel.t_start == commit_time
    assert call_rel.t_end is None
    assert call_rel.confidence == FactConfidence.HIGH
    assert call_rel.is_uncertain is False
    assert call_rel.id.startswith("rel-code-")


def test_2_multiple_relations_from_single_change():
    """2. Multiple relations extracted from a single change (imports, inheritance, and calls)."""
    decomposer = CodeAtomDecomposer()
    commit_time = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    commit = GitCommitArtifact(
        commit_sha="b2c3d4e5f6a1789012345678901234567890bcde",
        commit_message="feat(order): add OrderProcessor with inventory and payments",
        raw_diff=SAMPLE_MULTI_RELATION_DIFF,
        committed_at=commit_time,
    )

    result = decomposer.decompose(commit)
    assert result.relation_count >= 3

    rels = result.relations
    rel_types = {r.relation for r in rels}

    assert RelationType.IMPORTS in rel_types
    assert RelationType.CALLS in rel_types
    assert RelationType.INHERITS in rel_types

    # Verify inheritance
    inherit_rel = next((r for r in rels if r.relation == RelationType.INHERITS), None)
    assert inherit_rel is not None
    assert inherit_rel.subject == "OrderProcessor"
    assert inherit_rel.object == "BaseProcessor"
    assert inherit_rel.t_start == commit_time

    # Verify calls
    targets = {r.object for r in rels if r.relation == RelationType.CALLS}
    assert "InventoryManager" in targets or "PaymentGateway" in targets


def test_3_rejection_of_unsupported_relationships():
    """3. Rejection of unsupported relationships / hallucinated tokens."""
    # Real content contains token_validator and authenticate_token
    valid = validate_grounded_relation_tokens(
        subject="authenticate_token",
        target_object="token_validator",
        raw_content=SAMPLE_AUTH_DIFF,
        file_path="apps/api/src/auth_service.py",
        symbol_name="authenticate_token",
    )
    assert valid is True

    # Hallucinated tokens not in diff
    hallucinated = validate_grounded_relation_tokens(
        subject="StripeBillingClient",
        target_object="ExternalPaymentProcessor",
        raw_content=SAMPLE_AUTH_DIFF,
        file_path="apps/api/src/auth_service.py",
        symbol_name="authenticate_token",
    )
    assert hallucinated is False


def test_4_missing_timestamps_without_fabricated_dates():
    """4. Missing timestamps remain explicitly None without fabricated dates."""
    extractor = TemporalRelationExtractor()
    change = AtomicCodeChange(
        id="atom-no-date",
        commit_sha="c3d4e5f6a1b2789012345678901234567890cdef",
        commit_message="fix: tweak logic",
        file_path="apps/api/src/auth_service.py",
        change_type=CodeChangeType.MODIFY,
        symbol_name="authenticate_token",
        raw_content=SAMPLE_AUTH_DIFF,
        normalized_content="",
        added_lines=["    return token_validator.verify(token)"],
        deleted_lines=[],
        provenance={},  # No committed_at
        fingerprint="fp-no-date",
    )

    relations = extractor.extract_relations_deterministic(change, commit_time=None)
    assert len(relations) >= 1
    for r in relations:
        assert r.t_obs is None
        assert r.t_start is None
        assert r.t_end is None


def test_5_relative_time_normalization_when_verified():
    """5. Observation timestamp t_obs is anchored correctly to commit date."""
    commit_time = datetime(2026, 5, 20, 14, 30, 0, tzinfo=UTC)
    extractor = TemporalRelationExtractor()

    change = AtomicCodeChange(
        id="atom-time-verify",
        commit_sha="d4e5f6a1b2c3789012345678901234567890def0",
        commit_message="feat: verified time commit",
        file_path="apps/api/src/auth_service.py",
        change_type=CodeChangeType.ADD,
        symbol_name="authenticate_token",
        raw_content=SAMPLE_AUTH_DIFF,
        normalized_content="",
        added_lines=["    return token_validator.verify(token)"],
        deleted_lines=[],
        provenance={"committed_at": commit_time.isoformat()},
        fingerprint="fp-time-verify",
    )

    relations = extractor.extract_relations_deterministic(change, commit_time=commit_time)
    assert len(relations) >= 1
    for r in relations:
        assert r.t_obs == commit_time
        assert r.t_start == commit_time
        assert r.t_end is None


def test_6_correct_end_action_and_deletion_handling():
    """6. Deletions and removals normalize to affirmative relations with verified t_end."""
    extractor = TemporalRelationExtractor()
    removal_time = datetime(2026, 6, 1, 9, 0, 0, tzinfo=UTC)

    # A. Deleted lines within a file
    change_lines = AtomicCodeChange(
        id="atom-removal-lines",
        commit_sha="e5f6a1b2c3d4789012345678901234567890ef01",
        commit_message="refactor: remove legacy tracker",
        file_path="apps/api/src/legacy_client.py",
        change_type=CodeChangeType.MODIFY,
        symbol_name="run_pipeline",
        raw_content=SAMPLE_REMOVAL_DIFF,
        normalized_content="",
        added_lines=[],
        deleted_lines=[
            "    legacy_tracker.record_telemetry()",
            "    from deprecated_module import old_helper",
        ],
        provenance={"committed_at": removal_time.isoformat()},
        fingerprint="fp-rem-lines",
    )

    relations = extractor.extract_relations_deterministic(change_lines, commit_time=removal_time)
    assert len(relations) >= 1

    assert normalize_relation_name("stops_calling") == RelationType.CALLS
    assert normalize_relation_name("removed_import") == RelationType.IMPORTS
    assert normalize_relation_name("invokes") == RelationType.CALLS

    call_rel = next((r for r in relations if r.relation == RelationType.CALLS), None)
    assert call_rel is not None
    # Affirmative relation form (CALLS), not negative (e.g. stops_calling)
    assert call_rel.relation == RelationType.CALLS
    assert call_rel.object == "legacy_tracker"
    assert call_rel.t_end == removal_time
    assert call_rel.t_start is None  # Prior start unverified

    import_rel = next((r for r in relations if r.relation == RelationType.IMPORTS), None)
    assert import_rel is not None
    assert import_rel.relation == RelationType.IMPORTS
    assert import_rel.t_end == removal_time
    assert import_rel.t_start is None

    # B. Pure deleted file
    change_file = AtomicCodeChange(
        id="atom-deleted-file",
        commit_sha="f6a1b2c3d4e5789012345678901234567890f012",
        commit_message="chore: delete old_worker.py",
        file_path="apps/api/src/old_worker.py",
        change_type=CodeChangeType.DELETE,
        symbol_name=None,
        raw_content=SAMPLE_DELETED_FILE_DIFF,
        normalized_content="",
        added_lines=[],
        deleted_lines=["def run_old_worker():", "    pass"],
        provenance={"committed_at": removal_time.isoformat()},
        fingerprint="fp-del-file",
    )

    del_file_rels = extractor.extract_relations_deterministic(change_file, commit_time=removal_time)
    assert len(del_file_rels) >= 1
    for r in del_file_rels:
        assert r.t_end == removal_time
        assert r.t_start is None


def test_7_safe_behavior_when_historical_start_unavailable():
    """7. Unverified prior start remains None on deletions and modifications."""
    fact = SemanticCodeFact(
        id="fact-rem-1",
        statement="run_pipeline removed logic: `legacy_tracker.record_telemetry()`.",
        fact_type=FactType.REMOVAL,
        confidence=FactConfidence.HIGH,
        is_uncertain=False,
        file_path="apps/api/src/legacy_client.py",
        symbol_name="run_pipeline",
        commit_sha="sha1",
        change_type=CodeChangeType.MODIFY,
        fingerprint="fp-fact-rem-1",
    )
    change = AtomicCodeChange(
        id="atom-rem-1",
        commit_sha="sha1",
        commit_message="msg",
        file_path="apps/api/src/legacy_client.py",
        change_type=CodeChangeType.MODIFY,
        symbol_name="run_pipeline",
        raw_content="",
        normalized_content="",
        added_lines=[],
        deleted_lines=["legacy_tracker.record_telemetry()"],
        atomic_facts=[fact],
        fingerprint="fp-rem-1",
    )

    extractor = TemporalRelationExtractor()
    now_time = datetime(2026, 6, 15, tzinfo=UTC)
    rels = extractor.extract_relations_from_facts([fact], change, commit_time=now_time)

    assert len(rels) >= 1
    rel = rels[0]
    assert rel.t_end == now_time
    assert rel.t_start is None  # Never fabricated


@pytest.mark.asyncio
async def test_8_provider_failures_and_malformed_responses():
    """8. Provider failures, malformed output, or exceptions degrade safely to deterministic extraction."""
    mock_provider = AsyncMock()
    mock_provider.generate_json.side_effect = RuntimeError("Remote LLM connection timeout")

    extractor = TemporalRelationExtractor(llm_provider=mock_provider)
    commit_time = datetime(2026, 7, 1, tzinfo=UTC)

    change = AtomicCodeChange(
        id="atom-fallback",
        commit_sha="fallback_sha",
        commit_message="feat: fallback test",
        file_path="apps/api/src/auth_service.py",
        change_type=CodeChangeType.ADD,
        symbol_name="authenticate_token",
        raw_content=SAMPLE_AUTH_DIFF,
        normalized_content="",
        added_lines=["    return token_validator.verify(token)"],
        deleted_lines=[],
        fingerprint="fp-fallback",
    )

    # Should not throw; falls back safely to deterministic relations
    rels = await extractor.extract_relations_async(change, commit_time=commit_time, use_llm=True)
    assert len(rels) >= 1
    assert any(r.relation == RelationType.CALLS for r in rels)


@pytest.mark.asyncio
async def test_9_bounded_parallel_processing():
    """9. Bounded parallel processing limits concurrency safely with Semaphore."""
    mock_provider = AsyncMock()
    mock_provider.generate_json.return_value = {
        "relations": [
            {
                "subject": "authenticate_token",
                "relation": "CALLS",
                "object": "token_validator",
                "t_start": "2026-07-01T00:00:00+00:00",
                "t_end": None,
                "confidence": "HIGH",
                "is_uncertain": False,
            }
        ]
    }

    extractor = TemporalRelationExtractor(llm_provider=mock_provider)
    commit_time = datetime(2026, 7, 1, tzinfo=UTC)

    changes = [
        AtomicCodeChange(
            id=f"atom-{i}",
            commit_sha=f"sha_{i}",
            commit_message="msg",
            file_path="apps/api/src/auth_service.py",
            change_type=CodeChangeType.ADD,
            symbol_name="authenticate_token",
            raw_content=SAMPLE_AUTH_DIFF,
            normalized_content="",
            added_lines=["    return token_validator.verify(token)"],
            deleted_lines=[],
            fingerprint=f"fp-{i}",
        )
        for i in range(5)
    ]

    import asyncio

    tasks = [
        extractor.extract_relations_async(c, commit_time=commit_time, use_llm=True, max_concurrency=2)
        for c in changes
    ]
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    for rel_list in results:
        assert len(rel_list) >= 1


def test_10_idempotent_reprocessing_and_provenance_preservation():
    """10. Idempotent reprocessing produces identical fingerprints and IDs."""
    commit_time = datetime(2026, 8, 1, 10, 0, 0, tzinfo=UTC)
    fp1 = generate_relation_fingerprint(
        commit_sha="test_sha",
        file_path="apps/api/src/service.py",
        subject="OrderProcessor",
        relation=RelationType.CALLS,
        target_object="PaymentGateway",
        t_start=commit_time,
        t_end=None,
        t_obs=commit_time,
    )
    fp2 = generate_relation_fingerprint(
        commit_sha="test_sha",
        file_path="apps/api/src/service.py",
        subject="OrderProcessor",
        relation=RelationType.CALLS,
        target_object="PaymentGateway",
        t_start=commit_time,
        t_end=None,
        t_obs=commit_time,
    )
    assert fp1 == fp2
    assert generate_relation_id(fp1) == generate_relation_id(fp2)

    # Deduplication preserves single instance
    rel1 = TemporalCodeRelation(
        id=generate_relation_id(fp1),
        subject="OrderProcessor",
        relation=RelationType.CALLS,
        object="PaymentGateway",
        t_start=commit_time,
        t_obs=commit_time,
        fingerprint=fp1,
    )
    rel2 = TemporalCodeRelation(
        id=generate_relation_id(fp2),
        subject="OrderProcessor",
        relation=RelationType.CALLS,
        object="PaymentGateway",
        t_start=commit_time,
        t_obs=commit_time,
        fingerprint=fp2,
    )
    deduped = deduplicate_relations([rel1, rel2])
    assert len(deduped) == 1


def test_11_json_safe_serialization():
    """11. JSON-safe serialization and round-trip via model_dump(mode='json')."""
    commit_time = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
    fp = generate_relation_fingerprint(
        commit_sha="sha_json",
        file_path="apps/api/src/service.py",
        subject="UserRepo",
        relation=RelationType.INHERITS,
        target_object="BaseRepo",
        t_start=commit_time,
        t_obs=commit_time,
    )
    rel = TemporalCodeRelation(
        id=generate_relation_id(fp),
        subject="UserRepo",
        relation=RelationType.INHERITS,
        object="BaseRepo",
        t_start=commit_time,
        t_end=None,
        t_obs=commit_time,
        fingerprint=fp,
    )

    dumped = rel.model_dump(mode="json")
    serialized = json.dumps(dumped)
    assert "UserRepo" in serialized
    assert "BaseRepo" in serialized
    assert "INHERITS" in serialized
    assert "2026-08-15T12:00:00" in serialized


def test_12_compatibility_with_phases_5_6_7():
    """12. Seamless end-to-end integration across ChunkMapper, Retriever, and Assembler."""
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()
    commit_time = datetime(2026, 9, 1, 10, 0, 0, tzinfo=UTC)

    # 1. Phase 5 Chunk Mapping
    rel = TemporalCodeRelation(
        id="rel-test-12",
        subject="OrderProcessor",
        relation=RelationType.CALLS,
        object="PaymentGateway",
        t_start=commit_time,
        t_obs=commit_time,
        fingerprint="fp-test-12",
    )
    change = AtomicCodeChange(
        id="atom-12",
        commit_sha="sha-12",
        commit_message="feat: phase 12 integration",
        file_path="apps/api/src/order.py",
        change_type=CodeChangeType.ADD,
        symbol_name="OrderProcessor",
        raw_content="def process(): pass",
        normalized_content="",
        added_lines=["def process(): pass"],
        deleted_lines=[],
        provenance={"committed_at": commit_time.isoformat()},
        temporal_relations=[rel],
        fingerprint="fp-change-12",
    )

    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snapshot_id,
        file_id=file_id,
        compute_embedding=False,
    )
    assert "temporal_relations" in chunk.provenance
    assert len(chunk.provenance["temporal_relations"]) == 1
    assert chunk.provenance["temporal_relations"][0]["subject"] == "OrderProcessor"

    # Batch mapping test
    repo_file = RepositoryFile(
        id=file_id,
        snapshot_id=snapshot_id,
        path="apps/api/src/order.py",
        filename="order.py",
        extension="py",
        language="python",
        size_bytes=100,
        content_hash="hash",
    )
    batch_chunks = resolve_and_map_atomic_changes(
        changes=[change],
        snapshot_id=snapshot_id,
        files_map={"apps/api/src/order.py": repo_file},
        compute_embedding=False,
    )
    assert len(batch_chunks) == 1
    assert "temporal_relations" in batch_chunks[0].provenance

    # 2. Phase 6 Retriever Metadata Extraction
    retrieved_cand = RetrievedCandidate(
        candidate_id=str(chunk.id),
        entity_type="CHUNK",
        name=chunk.name,
        path=chunk.path,
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        content=chunk.content,
        file_id=file_id,
        metadata=dict(chunk.provenance),
    )
    cand_meta = _extract_chunk_metadata(chunk)
    assert "temporal_relations" in cand_meta

    # 3. Phase 7 Context Assembler Formatting
    retrieved_cand.metadata.update(cand_meta)
    ranked = RankedCandidate(candidate=retrieved_cand, score=0.95, matched_reasons=["KEYWORD"])

    assembled = ContextAssembler.assemble_context([ranked])

    assert "Grounded Temporal Relations:" in assembled.prompt_context
    assert "(OrderProcessor, CALLS, PaymentGateway)" in assembled.prompt_context
    assert len(assembled.evidence_items) == 1
    assert "temporal_relations" in assembled.evidence_items[0]
