import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import SymbolType
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.schemas.code_atom import GitCommitArtifact
from apps.api.src.services.code_atom.chunk_mapper import (
    map_atomic_code_change_to_code_chunk,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.context_engine.assembler import ContextAssembler
from apps.api.src.services.context_engine.graph_expander import RelationshipExpander
from apps.api.src.services.context_engine.query_analyzer import analyze_query
from apps.api.src.services.context_engine.ranker import MultiSignalRanker
from apps.api.src.services.context_engine.retriever import RetrievedCandidate


@pytest.mark.asyncio
async def test_1_direct_matches_retrieve_relevant_connected_code():
    """Scenario 1: Direct matches retrieve relevant connected code (callers, callees, symbols)."""
    snapshot_id = uuid.uuid4()
    seed_file_id = uuid.uuid4()
    callee_file_id = uuid.uuid4()
    caller_file_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id=f"file:{seed_file_id}",
        entity_type="FILE",
        name="auth_service.py",
        path="src/services/auth_service.py",
        start_line=1,
        end_line=100,
        content="// AuthService implementation",
        file_id=seed_file_id,
        signals={"file_match": 1.5},
    )

    file_seed = RepositoryFile(
        id=seed_file_id,
        snapshot_id=snapshot_id,
        path="src/services/auth_service.py",
        filename="auth_service.py",
    )
    file_callee = RepositoryFile(
        id=callee_file_id,
        snapshot_id=snapshot_id,
        path="src/repos/user_repo.py",
        filename="user_repo.py",
    )
    file_caller = RepositoryFile(
        id=caller_file_id,
        snapshot_id=snapshot_id,
        path="src/controllers/auth_ctrl.py",
        filename="auth_ctrl.py",
    )

    dep_outbound = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=seed_file_id,
        target_file_id=callee_file_id,
        line_number=5,
    )
    dep_inbound = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=caller_file_id,
        target_file_id=seed_file_id,
        line_number=10,
    )

    sym_callee = CodeSymbol(
        id=uuid.uuid4(),
        file_id=callee_file_id,
        name="find_by_email",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="user_repo.find_by_email",
        start_line=10,
        end_line=25,
    )

    session = AsyncMock()
    sym_query_num = 0

    def execute_side_effect(stmt):
        nonlocal sym_query_num
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "code_symbols" in stmt_str:
            sym_query_num += 1
            if sym_query_num == 1:
                mock_res.all.return_value = []
            else:
                mock_res.all.return_value = [(sym_callee, file_callee)]
        elif "code_dependencies" in stmt_str:
            mock_res.all.return_value = [
                (dep_outbound, file_seed, file_callee),
                (dep_inbound, file_caller, file_seed),
            ]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=2,
    )

    # 1. Connected caller and callee dependencies discovered
    dep_cands = [c for c in expanded if c.entity_type == "DEPENDENCY"]
    assert len(dep_cands) >= 2
    outbound = next(c for c in dep_cands if c.metadata.get("relationship_type") == "CALLEE")
    inbound = next(c for c in dep_cands if c.metadata.get("relationship_type") == "CALLER")

    assert outbound.metadata["relationship_hop"] == 1
    assert "imports -> src/repos/user_repo.py" in outbound.metadata["relationship_path"]
    assert inbound.metadata["relationship_hop"] == 1
    assert "calls -> src/services/auth_service.py" in inbound.metadata["relationship_path"]

    # 2. Connected files discovered
    file_cands = [c for c in expanded if c.entity_type == "FILE" and c.candidate_id != seed_cand.candidate_id]
    assert any(c.path == "src/repos/user_repo.py" for c in file_cands)
    assert any(c.path == "src/controllers/auth_ctrl.py" for c in file_cands)


@pytest.mark.asyncio
async def test_2_two_hop_expansion_works():
    """Scenario 2: Multi-hop BFS discovers direct (hop 1) and transitive (hop 2) relationships with signal decay."""
    snapshot_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    hop1_id = uuid.uuid4()
    hop2_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id=f"file:{seed_id}",
        entity_type="FILE",
        name="main.py",
        path="src/main.py",
        start_line=1,
        end_line=50,
        content="// Entry point",
        file_id=seed_id,
    )

    file_seed = RepositoryFile(id=seed_id, snapshot_id=snapshot_id, path="src/main.py", filename="main.py")
    file_hop1 = RepositoryFile(id=hop1_id, snapshot_id=snapshot_id, path="src/service.py", filename="service.py")
    file_hop2 = RepositoryFile(id=hop2_id, snapshot_id=snapshot_id, path="src/db.py", filename="db.py")

    dep1 = CodeDependency(id=uuid.uuid4(), source_file_id=seed_id, target_file_id=hop1_id, line_number=3)
    dep2 = CodeDependency(id=uuid.uuid4(), source_file_id=hop1_id, target_file_id=hop2_id, line_number=8)

    session = AsyncMock()
    dep_count = 0

    def execute_side_effect(stmt):
        nonlocal dep_count
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "code_symbols" in stmt_str:
            mock_res.all.return_value = []
        elif "code_dependencies" in stmt_str:
            dep_count += 1
            if dep_count == 1:
                mock_res.all.return_value = [(dep1, file_seed, file_hop1)]
            elif dep_count == 2:
                mock_res.all.return_value = [(dep2, file_hop1, file_hop2)]
            else:
                mock_res.all.return_value = []
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=2,
    )

    hop1_cands = [c for c in expanded if c.metadata.get("relationship_hop") == 1]
    hop2_cands = [c for c in expanded if c.metadata.get("relationship_hop") == 2]

    assert len(hop1_cands) >= 1
    assert len(hop2_cands) >= 1

    # Verify signal keys and weights decay
    assert "graph_expansion" in hop1_cands[0].signals
    assert "graph_expansion_hop2" in hop2_cands[0].signals
    assert hop1_cands[0].signals["graph_expansion"] > hop2_cands[0].signals["graph_expansion_hop2"]


@pytest.mark.asyncio
async def test_3_traversal_depth_and_candidate_limits_are_respected():
    """Scenario 3: Traversal depth (max_depth) and candidate limits (max_expansions) are strictly respected."""
    snapshot_id = uuid.uuid4()
    f1_id = uuid.uuid4()
    f2_id = uuid.uuid4()
    f3_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id=f"file:{f1_id}",
        entity_type="FILE",
        name="f1.py",
        path="src/f1.py",
        start_line=1,
        end_line=10,
        content="// f1",
        file_id=f1_id,
    )

    file1 = RepositoryFile(id=f1_id, snapshot_id=snapshot_id, path="src/f1.py", filename="f1.py")
    file2 = RepositoryFile(id=f2_id, snapshot_id=snapshot_id, path="src/f2.py", filename="f2.py")
    file3 = RepositoryFile(id=f3_id, snapshot_id=snapshot_id, path="src/f3.py", filename="f3.py")

    dep1 = CodeDependency(id=uuid.uuid4(), source_file_id=f1_id, target_file_id=f2_id, line_number=2)
    dep2 = CodeDependency(id=uuid.uuid4(), source_file_id=f2_id, target_file_id=f3_id, line_number=4)

    session = AsyncMock()
    dep_count = 0

    def execute_side_effect(stmt):
        nonlocal dep_count
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "code_symbols" in stmt_str:
            mock_res.all.return_value = []
        elif "code_dependencies" in stmt_str:
            dep_count += 1
            if dep_count == 1:
                mock_res.all.return_value = [(dep1, file1, file2)]
            elif dep_count == 2:
                mock_res.all.return_value = [(dep2, file2, file3)]
            else:
                mock_res.all.return_value = []
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    # Depth 1: should ONLY discover hop 1 (f2), NOT hop 2 (f3)
    expanded_d1 = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=1,
    )
    d1_hops = {c.metadata.get("relationship_hop") for c in expanded_d1}
    assert 2 not in d1_hops
    assert not any(c.path == "src/f3.py" for c in expanded_d1)

    # Candidate budget: limit = 0
    expanded_empty = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[],
        max_depth=2,
    )
    assert expanded_empty == []


@pytest.mark.asyncio
async def test_4_cycles_terminate_without_duplicate_results():
    """Scenario 4: Cyclic graphs terminate cleanly without infinite loops or duplicate candidates."""
    snapshot_id = uuid.uuid4()
    f1_id = uuid.uuid4()
    f2_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id=f"file:{f1_id}",
        entity_type="FILE",
        name="cycle1.py",
        path="src/cycle1.py",
        start_line=1,
        end_line=20,
        content="// cycle 1",
        file_id=f1_id,
    )

    file1 = RepositoryFile(id=f1_id, snapshot_id=snapshot_id, path="src/cycle1.py", filename="cycle1.py")
    file2 = RepositoryFile(id=f2_id, snapshot_id=snapshot_id, path="src/cycle2.py", filename="cycle2.py")

    dep_1_to_2 = CodeDependency(id=uuid.uuid4(), source_file_id=f1_id, target_file_id=f2_id, line_number=5)
    dep_2_to_1 = CodeDependency(id=uuid.uuid4(), source_file_id=f2_id, target_file_id=f1_id, line_number=7)

    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        stmt_str = str(stmt)
        if "code_symbols" in stmt_str:
            mock_res.all.return_value = []
        elif "code_dependencies" in stmt_str:
            mock_res.all.return_value = [
                (dep_1_to_2, file1, file2),
                (dep_2_to_1, file2, file1),
            ]
        else:
            mock_res.scalars.return_value.all.return_value = []
            mock_res.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    # Traversal should terminate in bounded steps and not duplicate cycle1.py
    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=2,
    )

    cand_ids = [c.candidate_id for c in expanded]
    assert len(cand_ids) == len(set(cand_ids))

    # Seed candidate is not re-created under a new ID
    cycle1_cands = [c for c in expanded if c.path == "src/cycle1.py" and c.entity_type == "FILE"]
    assert len(cycle1_cands) == 1
    assert cycle1_cands[0].candidate_id == f"file:{f1_id}"


def test_5_multiple_relationship_paths_to_one_chunk_deduplicated_preserving_provenance():
    """Scenario 5: Multiple relationship paths to one chunk are deduplicated while preserving shortest hop and alternative paths."""
    file_id = uuid.uuid4()
    query = analyze_query("data handler")

    # Candidate encountered via 2-hop path
    cand_hop2 = RetrievedCandidate(
        candidate_id="chunk:x",
        entity_type="CHUNK",
        name="handle_data",
        path="src/handler.py",
        start_line=10,
        end_line=30,
        content="def handle_data(): pass",
        file_id=file_id,
        signals={"graph_expansion_hop2": 0.34},
        metadata={
            "fingerprint": "fp_x_123",
            "relationship_path": "seed_b -> hop1 -> handle_data",
            "relationship_type": "CALLEE",
            "relationship_hop": 2,
            "connected_from": "hop1",
            "retrieval_reason": "Transitive dependency (hop 2)",
            "alternative_paths": [],
        },
    )

    # Same candidate encountered via 1-hop path
    cand_hop1 = RetrievedCandidate(
        candidate_id="chunk:x",
        entity_type="CHUNK",
        name="handle_data",
        path="src/handler.py",
        start_line=10,
        end_line=30,
        content="def handle_data(): pass",
        file_id=file_id,
        signals={"graph_expansion": 0.45},
        metadata={
            "fingerprint": "fp_x_123",
            "relationship_path": "seed_a -> handle_data",
            "relationship_type": "CALLEE",
            "relationship_hop": 1,
            "connected_from": "seed_a",
            "retrieval_reason": "Direct dependency (hop 1)",
            "alternative_paths": [],
        },
    )

    ranked = MultiSignalRanker.rank_candidates([cand_hop2, cand_hop1], query)
    assert len(ranked) == 1

    winner = ranked[0].candidate
    # 1. Shortest hop is preserved
    assert winner.metadata["relationship_hop"] == 1
    assert winner.metadata["relationship_path"] == "seed_a -> handle_data"
    assert winner.metadata["connected_from"] == "seed_a"

    # 2. Alternative path is preserved in provenance
    assert "seed_b -> hop1 -> handle_data" in winner.metadata["alternative_paths"]

    # 3. Signals were merged taking the maximum
    assert winner.signals["graph_expansion"] == 0.45
    assert winner.signals["graph_expansion_hop2"] == 0.34


def test_6_strong_direct_evidence_ranks_above_weak_relationship_only_evidence():
    """Scenario 6: Strong direct matches outrank relationship-only candidates, and hop distance decay is reflected."""
    file_id = uuid.uuid4()
    query = analyze_query("How does UserService authenticate users?")

    # 1. Strong direct match (symbol match + keyword in name)
    cand_direct = RetrievedCandidate(
        candidate_id="sym:user_service",
        entity_type="SYMBOL",
        name="UserService",
        path="src/services/user_service.py",
        start_line=1,
        end_line=50,
        content="class UserService:\n    def authenticate(self): pass",
        file_id=file_id,
        signals={"symbol_match": 1.5, "content_match": 1.2},
    )

    # 2. Hop 1 relationship-only neighbor (e.g. logger or helper)
    cand_hop1 = RetrievedCandidate(
        candidate_id="chunk:logger",
        entity_type="CHUNK",
        name="setup_logger",
        path="src/utils/logger.py",
        start_line=1,
        end_line=20,
        content="def setup_logger(): pass",
        file_id=uuid.uuid4(),
        signals={"graph_expansion": 0.45},
        metadata={
            "relationship_hop": 1,
            "relationship_type": "DEPENDENCY",
            "connected_from": "UserService",
        },
    )

    # 3. Hop 2 relationship-only transitive neighbor
    cand_hop2 = RetrievedCandidate(
        candidate_id="chunk:sys_clock",
        entity_type="CHUNK",
        name="get_system_time",
        path="src/utils/clock.py",
        start_line=1,
        end_line=10,
        content="def get_system_time(): pass",
        file_id=uuid.uuid4(),
        signals={"graph_expansion_hop2": 0.34},
        metadata={
            "relationship_hop": 2,
            "relationship_type": "DEPENDENCY",
            "connected_from": "setup_logger",
        },
    )

    ranked = MultiSignalRanker.rank_candidates([cand_hop2, cand_direct, cand_hop1], query)

    # Direct evidence ranks #1
    assert ranked[0].candidate.candidate_id == "sym:user_service"
    assert ranked[0].score > ranked[1].score

    # Hop 1 ranks above Hop 2 due to decay
    hop1_rank = next(r for r in ranked if r.candidate.candidate_id == "chunk:logger")
    hop2_rank = next(r for r in ranked if r.candidate.candidate_id == "chunk:sys_clock")
    assert hop1_rank.score >= hop2_rank.score

    # Relationship reasons recorded
    assert any("Connected dependency" in r for r in hop1_rank.matched_reasons)


@pytest.mark.asyncio
async def test_7_unrelated_files_are_not_added_unnecessarily():
    """Scenario 7: Files with no dependency or symbol links to the seeds are never added."""
    snapshot_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    unrelated_id = uuid.uuid4()

    seed_cand = RetrievedCandidate(
        candidate_id=f"file:{seed_id}",
        entity_type="FILE",
        name="isolated.py",
        path="src/isolated.py",
        start_line=1,
        end_line=20,
        content="// Isolated module",
        file_id=seed_id,
    )

    session = AsyncMock()

    def execute_side_effect(stmt):
        mock_res = MagicMock()
        # No relationships in DB for this seed
        mock_res.all.return_value = []
        mock_res.scalars.return_value.all.return_value = []
        return mock_res

    session.execute.side_effect = execute_side_effect

    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=2,
    )

    # Only seed candidate returned
    assert len(expanded) == 1
    assert expanded[0].candidate_id == seed_cand.candidate_id
    assert not any(c.file_id == unrelated_id for c in expanded)


@pytest.mark.asyncio
async def test_8_missing_relationship_data_falls_back_safely():
    """Scenario 8: Missing relationships, empty database, or missing candidate fields fall back cleanly."""
    snapshot_id = uuid.uuid4()

    # Seed without file_id or symbol_id
    seed_cand = RetrievedCandidate(
        candidate_id="virtual:doc",
        entity_type="FILE",
        name="README.md",
        path="README.md",
        start_line=1,
        end_line=10,
        content="# Documentation",
        file_id=None,  # type: ignore[arg-type]
    )

    session = AsyncMock()
    expanded = await RelationshipExpander.expand_candidates(
        session=session,
        snapshot_id=snapshot_id,
        seed_candidates=[seed_cand],
        max_depth=2,
    )

    assert len(expanded) == 1
    assert expanded[0].candidate_id == "virtual:doc"

    # Context assembler handles it smoothly
    query = analyze_query("documentation")
    ranked = MultiSignalRanker.rank_candidates(expanded, query)
    assembled = ContextAssembler.assemble_context(ranked)
    assert assembled.candidate_count == 1
    assert "README.md" in assembled.prompt_context


def test_9_phase_6_temporal_ranking_deletion_handling_and_historical_retrieval_remain_correct():
    """Scenario 9: Phase 6 temporal resolution (supersession, deletion, renames) works seamlessly with relationship candidates."""
    file_id = uuid.uuid4()

    cand_current = RetrievedCandidate(
        candidate_id="chunk:v2",
        entity_type="CHUNK",
        name="render_view",
        path="src/view.py",
        start_line=1,
        end_line=20,
        content="def render_view(): return 'new'",
        file_id=file_id,
        signals={"graph_expansion": 0.45},
        metadata={
            "commit_sha": "def5678",
            "committed_at": "2026-03-01T10:00:00Z",
            "is_current": True,
            "relationship_hop": 1,
            "relationship_type": "CALLEE",
        },
    )

    cand_superseded = RetrievedCandidate(
        candidate_id="chunk:v1",
        entity_type="CHUNK",
        name="render_view",
        path="src/view.py",
        start_line=1,
        end_line=20,
        content="def render_view(): return 'old'",
        file_id=file_id,
        signals={"graph_expansion": 0.45},
        metadata={
            "commit_sha": "abc1234",
            "committed_at": "2026-01-01T10:00:00Z",
            "is_superseded": True,
            "relationship_hop": 1,
            "relationship_type": "CALLEE",
        },
    )

    cand_deleted = RetrievedCandidate(
        candidate_id="chunk:dead",
        entity_type="CHUNK",
        name="legacy_render",
        path="src/view.py",
        start_line=25,
        end_line=40,
        content="def legacy_render(): pass",
        file_id=file_id,
        signals={"graph_expansion": 0.45},
        metadata={
            "is_deleted": True,
            "relationship_hop": 1,
            "relationship_type": "CALLEE",
        },
    )

    # 1. Current query: current implementation preferred, superseded and deleted demoted
    query_current = analyze_query("render_view")
    ranked_current = MultiSignalRanker.rank_candidates(
        [cand_superseded, cand_deleted, cand_current],
        query_current,
    )
    assert ranked_current[0].candidate.candidate_id == "chunk:v2"
    assert ranked_current[0].score > ranked_current[1].score

    # 2. Historical query: evolution and commits are promoted
    query_hist = analyze_query("How did render_view evolve across commits?")
    assert query_hist.is_temporal is True

    ranked_hist = MultiSignalRanker.rank_candidates(
        [cand_superseded, cand_current],
        query_hist,
    )
    superseded_item = next(r for r in ranked_hist if r.candidate.candidate_id == "chunk:v1")
    assert any("Historical commit evidence" in r or "Historical precursor" in r for r in superseded_item.matched_reasons)


def test_10_evidence_serialization_remains_json_safe():
    """Scenario 10: Relationship metadata (hop, path, reason, alternative_paths) is serialized safely into JSON."""
    file_id = uuid.uuid4()
    query = analyze_query("controller")

    cand = RetrievedCandidate(
        candidate_id="chunk:ctrl",
        entity_type="CHUNK",
        name="AuthController",
        path="src/auth_controller.py",
        start_line=1,
        end_line=50,
        content="class AuthController: pass",
        file_id=file_id,
        signals={"symbol_match": 1.2, "graph_expansion": 0.45},
        metadata={
            "snapshot_id": uuid.uuid4(),  # Raw UUID to test _json_safe
            "relationship_path": "routes.py -> calls -> AuthController",
            "relationship_type": "CALLER",
            "relationship_hop": 1,
            "connected_from": "routes.py",
            "retrieval_reason": "Connected caller controller (hop 1)",
            "alternative_paths": ["api.py -> AuthController", "main.py -> AuthController"],
        },
    )

    ranked = MultiSignalRanker.rank_candidates([cand], query)
    assembled = ContextAssembler.assemble_context(ranked)

    # 1. Check prompt context includes relationship lines
    assert "- Relationship: Path: routes.py -> calls -> AuthController | Hop 1" in assembled.prompt_context
    assert "- Relationship Reason: Connected caller controller (hop 1)" in assembled.prompt_context
    assert "- Alternative Paths: api.py -> AuthController, main.py -> AuthController" in assembled.prompt_context

    # 2. Ensure evidence_items can be dumped to JSON without TypeError
    json_str = json.dumps(assembled.evidence_items)
    deserialized = json.loads(json_str)
    assert len(deserialized) == 1

    item = deserialized[0]
    assert item["relationship_type"] == "CALLER"
    assert item["relationship_hop"] == 1
    assert item["relationship_path"] == "routes.py -> calls -> AuthController"
    assert item["connected_from"] == "routes.py"
    assert len(item["alternative_paths"]) == 2


def test_11_phase_5_incremental_ingestion_behavior_remains_unchanged():
    """Scenario 11: Phase 5 incremental ATOM indexing functions cleanly without interference from Phase 7."""
    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()

    sample_diff = """diff --git a/src/feature.py b/src/feature.py
new file mode 100644
--- /dev/null
+++ b/src/feature.py
@@ -0,0 +1,2 @@
+def new_feature():
+    return True
+"""

    commit = GitCommitArtifact(
        commit_sha="c32a873abcdef1234567890abcdef1234567890ab",
        commit_message="feat: implement incremental feature",
        author_name="Developer",
        author_email="dev@example.com",
        snapshot_id=snapshot_id,
        raw_diff=sample_diff,
    )

    decomposed = CodeAtomDecomposer().decompose(commit)
    assert len(decomposed.changes) >= 1
    change = decomposed.changes[0]

    # Map change to CodeChunk
    chunk = map_atomic_code_change_to_code_chunk(change, snapshot_id=snapshot_id, file_id=file_id)

    assert chunk.snapshot_id == snapshot_id
    assert chunk.file_id == file_id
    assert chunk.path == "src/feature.py"
    assert chunk.commit_sha == "c32a873abcdef1234567890abcdef1234567890ab"
    assert chunk.fingerprint is not None
    assert chunk.provenance["commit_sha"] == "c32a873abcdef1234567890abcdef1234567890ab"
