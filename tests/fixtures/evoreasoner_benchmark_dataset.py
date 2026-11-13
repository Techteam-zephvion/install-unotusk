"""
EvoReasoner & EvoKG Comprehensive Benchmark Dataset (T2.7 Milestone).
Reference: arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs").

Curated from genuine git commits, Tree-sitter decomposed AST structures,
persisted EvoKG triplets, and architectural dependencies in `Techteam-zephvion/install-unotusk`.

56 manually verified benchmark queries across 7 distinct evaluation categories (8 queries each):
- Category A: Current Code Understanding
- Category B: Historical Code Understanding
- Category C: Temporal Reasoning (all 7 temporal intents)
- Category D: Multi-Hop Reasoning
- Category E: Contradiction and Supersession
- Category F: Insufficient-Evidence Queries (Abstention)
- Category G: Branch and Provenance Queries
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from apps.api.src.services.context_engine.memotime import TemporalIntentType


@dataclass
class GroundTruthQuery:
    """Manually verified ground-truth specification for a benchmark query."""

    query_id: str
    category: str
    query: str
    intent: TemporalIntentType
    is_temporal: bool

    # Ground truth answer and relevance expectations
    expected_answer: str
    relevant_files: list[str] = field(default_factory=list)
    relevant_symbols: list[str] = field(default_factory=list)
    relevant_chunk_ids: list[str] = field(default_factory=list)
    partially_relevant_ids: list[str] = field(default_factory=list)
    superseded_ids: list[str] = field(default_factory=list)
    distractor_ids: list[str] = field(default_factory=list)

    # Graph & Multi-Hop Expectations
    expected_relations: list[dict[str, Any]] = field(default_factory=list)
    expected_paths: list[list[str]] = field(default_factory=list)

    # Temporal & Provenance Details
    commit_sha: str | None = None
    target_commit_sha: str | None = None
    branch: str = "main"
    as_of: datetime | None = None
    until: datetime | None = None

    # Abstention Expectations
    should_abstain: bool = False
    abstention_rationale: str = ""

    # Human-reviewed rationale
    rationale: str = ""


def get_evoreasoner_benchmark_dataset() -> list[GroundTruthQuery]:
    """Returns the authoritative 56-query benchmark dataset."""
    queries: list[GroundTruthQuery] = []

    # =========================================================================
    # CATEGORY A: CURRENT CODE UNDERSTANDING (8 queries)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q01_current_decomposer_def",
            category="Current Code Understanding",
            query="What is the class definition and core method signature of CodeAtomDecomposer?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="CodeAtomDecomposer is defined in decomposer.py with method decompose(self, artifact: GitCommitArtifact) -> DecomposedAtomicChanges.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer", "decompose"],
            relevant_chunk_ids=["be1b5b5_atom-code-8ed6126854ff06bd", "be1b5b5_atom-code-c1e034069b7ee905"],
            superseded_ids=["b094f01_atom-code-8e61d3b82fcd7f1e"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "DEFINES_METHOD", "object": "decompose"}
            ],
            expected_paths=[["CodeAtomDecomposer", "DEFINES_METHOD", "decompose"]],
            commit_sha="be1b5b5",
            rationale="Verifies current active AST scope resolution definition of CodeAtomDecomposer.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q02_current_reconcile_signature",
            category="Current Code Understanding",
            query="What is the return type and parameter signature of reconcile_code_relationships?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="reconcile_code_relationships takes raw_relations: list[AtomicCodeRelation] and returns list[AtomicCodeRelation].",
            relevant_files=["apps/api/src/services/code_atom/relation_resolver.py"],
            relevant_symbols=["reconcile_code_relationships"],
            relevant_chunk_ids=["b094f01_atom-code-2763774ca2f1f0fb"],
            expected_relations=[
                {"subject": "reconcile_code_relationships", "relation": "DEFINES_RETURN_TYPE", "object": "list[AtomicCodeRelation]"}
            ],
            expected_paths=[["reconcile_code_relationships", "DEFINES_RETURN_TYPE", "list[AtomicCodeRelation]"]],
            commit_sha="b094f01",
            rationale="Verifies function signature and return type retrieval.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q03_current_orchestrator_ports",
            category="Current Code Understanding",
            query="Which service orchestrates container host port bindings from Docker NetworkSettings?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="OrchestratorService in orchestrator_service.py inspects container NetworkSettings Ports and binds host ports.",
            relevant_files=["apps/api/src/services/orchestrator_service.py"],
            relevant_symbols=["OrchestratorService", "get_container_port"],
            relevant_chunk_ids=["4e5af91_atom-code-5b8c137091a883fe"],
            expected_relations=[
                {"subject": "OrchestratorService", "relation": "CALLS", "object": "port_bindings"}
            ],
            expected_paths=[["OrchestratorService", "CALLS", "port_bindings"]],
            commit_sha="4e5af91",
            rationale="Verifies service behavior and method invocation understanding.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q04_current_compatible_vector_type",
            category="Current Code Understanding",
            query="How does CompatibleVector decorate pgvector embeddings in chunk.py?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="CompatibleVector is a TypeDecorator that maps float embedding vectors to pgvector Vector types or JSON fallbacks.",
            relevant_files=["apps/api/src/models/chunk.py"],
            relevant_symbols=["CompatibleVector", "CodeChunk"],
            relevant_chunk_ids=["773b740_atom-code-8deb1f2af01f22cf", "773b740_atom-code-2b3db8b6b273e1b6"],
            expected_relations=[
                {"subject": "CodeChunk", "relation": "HAS_FIELD", "object": "embedding"},
                {"subject": "CompatibleVector", "relation": "INHERITS", "object": "TypeDecorator"}
            ],
            expected_paths=[["CompatibleVector", "INHERITS", "TypeDecorator"]],
            commit_sha="773b740",
            rationale="Verifies ORM model and custom SQLAlchemy type understanding.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q05_current_evoplanner_config",
            category="Current Code Understanding",
            query="What are the configuration parameters for EvoPlannerConfig in EvoReasoner schemas?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="EvoPlannerConfig defines max_candidate_routes=20, max_selected_routes=3, max_route_hops=4, max_branching_factor=10.0, and cost weights.",
            relevant_files=["apps/api/src/schemas/evoreasoner.py"],
            relevant_symbols=["EvoPlannerConfig"],
            relevant_chunk_ids=["94fbd79_evoreasoner_schemas_planner_cfg"],
            expected_relations=[
                {"subject": "EvoPlannerConfig", "relation": "HAS_FIELD", "object": "max_selected_routes"}
            ],
            expected_paths=[["EvoPlannerConfig", "HAS_FIELD", "max_selected_routes"]],
            commit_sha="94fbd79",
            rationale="Verifies Pydantic configuration schemas.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q06_current_evokg_contradiction_engine",
            category="Current Code Understanding",
            query="What is the role and class definition of EvoKGContradictionEngine?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="EvoKGContradictionEngine resolves exclusive conflicts and supersession in EvoKG using CodeRelationTaxonomy.",
            relevant_files=["apps/api/src/services/evokg/contradiction.py"],
            relevant_symbols=["EvoKGContradictionEngine", "resolve_contradictions"],
            relevant_chunk_ids=["2905a44_evokg_contradiction_engine"],
            expected_relations=[
                {"subject": "EvoKGContradictionEngine", "relation": "CALLS", "object": "CodeRelationTaxonomy"}
            ],
            expected_paths=[["EvoKGContradictionEngine", "CALLS", "CodeRelationTaxonomy"]],
            commit_sha="2905a44",
            rationale="Verifies contradiction engine service structure.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q07_current_exclusive_relation_taxonomy",
            category="Current Code Understanding",
            query="Which relations are classified as EXCLUSIVE in the EvoKG CodeRelationTaxonomy?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="DEFINES_RETURN_TYPE, INHERITS, SUPERSEDES, DEFINES_SIGNATURE, and BINDS_PORT are classified as EXCLUSIVE.",
            relevant_files=["apps/api/src/services/code_atom/taxonomy.py"],
            relevant_symbols=["CodeRelationTaxonomy", "PropertyExclusivity"],
            relevant_chunk_ids=["6626c5c_evokg_taxonomy"],
            expected_relations=[
                {"subject": "DEFINES_RETURN_TYPE", "relation": "IS_A", "object": "EXCLUSIVE"},
                {"subject": "INHERITS", "relation": "IS_A", "object": "EXCLUSIVE"}
            ],
            expected_paths=[["CodeRelationTaxonomy", "DEFINES_TAXONOMY", "PropertyExclusivity"]],
            commit_sha="6626c5c",
            rationale="Verifies taxonomy property classification.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q08_current_context_assembler_signature",
            category="Current Code Understanding",
            query="What is the method signature of ContextAssembler.assemble_context?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="assemble_context(cls, ranked_candidates, proof_chains=None, ...) returns AssembledContext.",
            relevant_files=["apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["ContextAssembler", "assemble_context", "AssembledContext"],
            relevant_chunk_ids=["94fbd79_context_assembler"],
            expected_relations=[
                {"subject": "ContextAssembler", "relation": "DEFINES_METHOD", "object": "assemble_context"}
            ],
            expected_paths=[["ContextAssembler", "DEFINES_METHOD", "assemble_context"]],
            commit_sha="94fbd79",
            rationale="Verifies ContextAssembler public method and parameters.",
        )
    )

    # =========================================================================
    # CATEGORY B: HISTORICAL CODE UNDERSTANDING (8 queries)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q09_historical_decomposer_line_overlap",
            category="Historical Code Understanding",
            query="How was CodeAtomDecomposer originally implemented before AST scope resolution was added in be1b5b5?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="CodeAtomDecomposer in b094f01 used heuristic line-range overlap instead of Tree-sitter AST innermost scope traversal.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer", "_find_enclosing_scope_heuristic"],
            relevant_chunk_ids=["b094f01_atom-code-955e07b924d52d2b", "b094f01_atom-code-8e61d3b82fcd7f1e"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "CALLS", "object": "_find_enclosing_scope_heuristic"}
            ],
            expected_paths=[["CodeAtomDecomposer", "CALLS", "_find_enclosing_scope_heuristic"]],
            commit_sha="b094f01",
            rationale="Verifies retrieval of historical superseded implementation from b094f01.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q10_historical_ranker_pre_star_rag",
            category="Historical Code Understanding",
            query="How did MultiSignalRanker score candidate chunks before STAR-RAG PPR integration in 42096a5?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="In commit 773b740, MultiSignalRanker used feature spec contract matchers and static signal weights without Personalized PageRank.",
            relevant_files=["apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["MultiSignalRanker", "rank_candidates"],
            relevant_chunk_ids=["773b740_atom-code-5bbd2eaed2c76e39", "773b740_atom-code-e2f16803b85cf53c"],
            expected_relations=[
                {"subject": "MultiSignalRanker", "relation": "CALLS", "object": "rank_candidates"}
            ],
            expected_paths=[["MultiSignalRanker", "CALLS", "rank_candidates"]],
            commit_sha="773b740",
            rationale="Verifies ranking evolution prior to graph propagation.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q11_historical_assembler_pre_proof_chains",
            category="Historical Code Understanding",
            query="What was the previous implementation of ContextAssembler formatting prior to proof-chain integration in 94fbd79?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="ContextAssembler in 42096a5 assembled code chunk content and metadata without the Grounded Multi-Hop Proof Chains section.",
            relevant_files=["apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["ContextAssembler"],
            relevant_chunk_ids=["42096a5_atom-code-4e942109f1f6298c"],
            expected_relations=[
                {"subject": "ContextAssembler", "relation": "FORMATS", "object": "CodeChunk"}
            ],
            expected_paths=[["ContextAssembler", "FORMATS", "CodeChunk"]],
            commit_sha="42096a5",
            rationale="Verifies ContextAssembler structure before T2.6.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q12_historical_orchestrator_items_loop",
            category="Historical Code Understanding",
            query="How did OrchestratorService loop over port bindings before commit 4e5af91?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="It iterated over port_bindings.items() unpacking (port_key, bindings) before being refactored to port_bindings.values().",
            relevant_files=["apps/api/src/services/orchestrator_service.py"],
            relevant_symbols=["OrchestratorService"],
            relevant_chunk_ids=["4e5af91_precursor_port_items"],
            expected_relations=[
                {"subject": "OrchestratorService", "relation": "CALLS", "object": "items"}
            ],
            expected_paths=[["OrchestratorService", "CALLS", "items"]],
            commit_sha="4e5af91",
            rationale="Verifies historical precursor code before lint fix.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q13_historical_initial_ranker_weights",
            category="Historical Code Understanding",
            query="What were the initial signal weights in MultiSignalRanker in commit b094f01?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="In commit b094f01, MultiSignalRanker used initial signal weights of vector 0.5, symbol 0.3, and path 0.2.",
            relevant_files=["apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["MultiSignalRanker"],
            relevant_chunk_ids=["b094f01_atom-code-61355c9e609d52a8"],
            expected_relations=[
                {"subject": "MultiSignalRanker", "relation": "USES_WEIGHT", "object": "vector_similarity"}
            ],
            expected_paths=[["MultiSignalRanker", "USES_WEIGHT", "vector_similarity"]],
            commit_sha="b094f01",
            rationale="Verifies initial baseline ranker weights.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q14_historical_assembler_interval_tags",
            category="Historical Code Understanding",
            query="How were temporal relationship intervals and ended tag annotations introduced in ContextAssembler?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="Commit b094f01 introduced [VALID: t_start -> t_end] and [ENDED] annotations in ContextAssembler.",
            relevant_files=["apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["ContextAssembler"],
            relevant_chunk_ids=["b094f01_atom-code-8e882ce1c7a1253c"],
            expected_relations=[
                {"subject": "ContextAssembler", "relation": "FORMATS", "object": "temporal_intervals"}
            ],
            expected_paths=[["ContextAssembler", "FORMATS", "temporal_intervals"]],
            commit_sha="b094f01",
            rationale="Verifies historical ContextAssembler interval tags.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q15_historical_project_service_sync",
            category="Historical Code Understanding",
            query="How did ProjectService validate user permissions and synchronize project member roles in commit 24a2630?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="ProjectService in commit 24a2630 synchronized project membership and access roles directly from organization users.",
            relevant_files=["apps/api/src/services/project_service.py"],
            relevant_symbols=["ProjectService", "sync_members"],
            relevant_chunk_ids=["24a2630_atom-code-f55eba9418776d79", "24a2630_atom-code-d5bcc9dac5ae238a"],
            expected_relations=[
                {"subject": "ProjectService", "relation": "CALLS", "object": "sync_members"}
            ],
            expected_paths=[["ProjectService", "CALLS", "sync_members"]],
            commit_sha="24a2630",
            rationale="Verifies project service member sync logic in 24a2630.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q16_historical_memotime_tree_nodes",
            category="Historical Code Understanding",
            query="What was the historical structure of Tree-of-Time nodes in MemoTime prior to commit 0e287bf?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="In commit 7562fd5, Tree-of-Time nodes tracked single-entity temporal intervals before cross-entity diff nodes were added.",
            relevant_files=["apps/api/src/services/context_engine/memotime.py"],
            relevant_symbols=["TreeOfTime", "TimeNode"],
            relevant_chunk_ids=["7562fd5_memotime_tree_of_time"],
            expected_relations=[
                {"subject": "TreeOfTime", "relation": "CONTAINS", "object": "TimeNode"}
            ],
            expected_paths=[["TreeOfTime", "CONTAINS", "TimeNode"]],
            commit_sha="7562fd5",
            rationale="Verifies early MemoTime Tree-of-Time implementation.",
        )
    )

    # =========================================================================
    # CATEGORY C: TEMPORAL REASONING (8 queries across 7 intents)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q17_temporal_current_active_assembler",
            category="Temporal Reasoning",
            query="What is the current active relationship between ProjectContextEngine and ContextAssembler?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ProjectContextEngine calls ContextAssembler.assemble_context with ranked candidates and proof chains.",
            relevant_files=["apps/api/src/services/context_engine/engine.py", "apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["ProjectContextEngine", "ContextAssembler"],
            relevant_chunk_ids=["94fbd79_engine_assembler_call"],
            expected_relations=[
                {"subject": "ProjectContextEngine", "relation": "CALLS", "object": "ContextAssembler.assemble_context"}
            ],
            expected_paths=[["ProjectContextEngine", "CALLS", "ContextAssembler"]],
            commit_sha="94fbd79",
            rationale="CURRENT temporal query: active state only, zero superseded facts.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q18_temporal_historical_decomposer_scope",
            category="Temporal Reasoning",
            query="What historical relationship existed between CodeAtomDecomposer and line-range heuristic in commit b094f01?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="CodeAtomDecomposer called _find_enclosing_scope_heuristic before being replaced in be1b5b5.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer"],
            relevant_chunk_ids=["b094f01_atom-code-955e07b924d52d2b"],
            superseded_ids=[],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "CALLS", "object": "_find_enclosing_scope_heuristic"}
            ],
            expected_paths=[["CodeAtomDecomposer", "CALLS", "_find_enclosing_scope_heuristic"]],
            commit_sha="b094f01",
            rationale="HISTORICAL temporal query: historical facts prioritized.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q19_temporal_before_2026_10_15",
            category="Temporal Reasoning",
            query="What chunk mapping and decomposition logic was committed before 2026-10-15?",
            intent=TemporalIntentType.BEFORE,
            is_temporal=True,
            expected_answer="Decomposition and chunk mapping in commits b094f01 and be1b5b5 committed before 2026-10-15.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py", "apps/api/src/services/code_atom/chunk_mapper.py"],
            relevant_symbols=["CodeAtomDecomposer", "map_atomic_code_change_to_code_chunk"],
            relevant_chunk_ids=["b094f01_atom-code-2763774ca2f1f0fb", "be1b5b5_atom-code-8ed6126854ff06bd"],
            as_of=datetime.fromisoformat("2026-10-15T00:00:00+00:00"),
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "CALLS", "object": "reconcile_code_relationships"}
            ],
            expected_paths=[["CodeAtomDecomposer", "CALLS", "reconcile_code_relationships"]],
            commit_sha="be1b5b5",
            rationale="BEFORE operator filters for facts valid/committed prior to 2026-10-15.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q20_temporal_after_2026_10_20",
            category="Temporal Reasoning",
            query="What database session configuration and vector types were added after 2026-10-20?",
            intent=TemporalIntentType.AFTER,
            is_temporal=True,
            expected_answer="Commit 773b740 committed after 2026-10-20 added CompatibleVector and session.py configuration.",
            relevant_files=["apps/api/src/models/chunk.py", "apps/api/src/core/session.py"],
            relevant_symbols=["CompatibleVector", "CodeChunk"],
            relevant_chunk_ids=["773b740_atom-code-8deb1f2af01f22cf", "773b740_atom-code-2b3db8b6b273e1b6"],
            as_of=datetime.fromisoformat("2026-10-20T00:00:00+00:00"),
            expected_relations=[
                {"subject": "CompatibleVector", "relation": "INHERITS", "object": "TypeDecorator"}
            ],
            expected_paths=[["CompatibleVector", "INHERITS", "TypeDecorator"]],
            commit_sha="773b740",
            rationale="AFTER operator filters for facts created or active after 2026-10-20.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q21_temporal_interval_2026_10_14_24",
            category="Temporal Reasoning",
            query="What features were implemented between 2026-10-14 and 2026-10-24 in intelligence routes and database sessions?",
            intent=TemporalIntentType.INTERVAL,
            is_temporal=True,
            expected_answer="Commit 773b740 added feature spec scoring, intelligence routes, and database sessions between Oct 14 and Oct 24.",
            relevant_files=["apps/api/src/models/chunk.py", "apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["CompatibleVector", "MultiSignalRanker"],
            relevant_chunk_ids=["773b740_atom-code-179714888d1e4278", "773b740_atom-code-8deb1f2af01f22cf"],
            as_of=datetime.fromisoformat("2026-10-14T00:00:00+00:00"),
            until=datetime.fromisoformat("2026-10-24T00:00:00+00:00"),
            expected_relations=[
                {"subject": "MultiSignalRanker", "relation": "CALLS", "object": "rank_candidates"}
            ],
            expected_paths=[["MultiSignalRanker", "CALLS", "rank_candidates"]],
            commit_sha="773b740",
            rationale="INTERVAL bounds query between Oct 14 and Oct 24.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q22_temporal_diff_6626c5c_2905a44",
            category="Temporal Reasoning",
            query="What changes were introduced between commit 6626c5c and 2905a44 for EvoKG persistence?",
            intent=TemporalIntentType.DIFF,
            is_temporal=True,
            expected_answer="Commit 2905a44 added EvoKGTriplet model, migration 0011_evokg_triplets.py, and EvoKGPersistenceService.",
            relevant_files=["apps/api/src/models/evokg/triplet.py", "apps/api/src/services/evokg/service.py"],
            relevant_symbols=["EvoKGTriplet", "EvoKGPersistenceService"],
            relevant_chunk_ids=["2905a44_evokg_persistence_service", "2905a44_evokg_triplet_model"],
            commit_sha="6626c5c",
            target_commit_sha="2905a44",
            expected_relations=[
                {"subject": "EvoKGPersistenceService", "relation": "WRITES_TO", "object": "EvoKGTriplet"}
            ],
            expected_paths=[["EvoKGPersistenceService", "WRITES_TO", "EvoKGTriplet"]],
            rationale="DIFF compares state between 6626c5c (taxonomy) and 2905a44 (persistence).",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q23_temporal_diff_commit_94fbd79",
            category="Temporal Reasoning",
            query="What changes were introduced in commit 94fbd79 for evoreasoner proof chains?",
            intent=TemporalIntentType.DIFF,
            is_temporal=True,
            expected_answer="Commit 94fbd79 added EvoRoutePlanner, EvoBeamSearchEngine, ProofChainAggregator, and ContextAssembler integration.",
            relevant_files=["apps/api/src/services/evoreasoner/aggregator.py", "apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["ProofChainAggregator", "ContextAssembler"],
            relevant_chunk_ids=["94fbd79_evoreasoner_aggregator", "94fbd79_context_assembler"],
            commit_sha="94fbd79",
            expected_relations=[
                {"subject": "ContextAssembler", "relation": "USES", "object": "ProofChainAggregator"}
            ],
            expected_paths=[["ContextAssembler", "USES", "ProofChainAggregator"]],
            rationale="DIFF targets changeset of commit 94fbd79.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q24_temporal_evolution_ast_scope",
            category="Temporal Reasoning",
            query="How did the relationship between AST scope resolution and diff hunk decomposition evolve across commits b094f01, be1b5b5, and 773b740?",
            intent=TemporalIntentType.EVOLUTION,
            is_temporal=True,
            expected_answer="Evolved from line-range overlap heuristics (b094f01) to Tree-sitter innermost scope (be1b5b5) to feature spec integration (773b740).",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py", "apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["CodeAtomDecomposer", "MultiSignalRanker"],
            relevant_chunk_ids=["b094f01_atom-code-955e07b924d52d2b", "be1b5b5_atom-code-8ed6126854ff06bd", "773b740_atom-code-5bbd2eaed2c76e39"],
            expected_relations=[
                {"subject": "Tree-sitter innermost scope", "relation": "SUPERSEDES", "object": "line-range heuristic"}
            ],
            expected_paths=[["Tree-sitter innermost scope", "SUPERSEDES", "line-range heuristic"]],
            commit_sha="773b740",
            rationale="EVOLUTION traces complete supersession chain across 3 commits.",
        )
    )

    # =========================================================================
    # CATEGORY D: MULTI-HOP REASONING (8 queries)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q25_multihop_engine_to_assembler_chain",
            category="Multi-Hop Reasoning",
            query="How does a query travel from ProjectContextEngine to ContextAssembler through MultiSignalRanker and EvoReasoner?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ProjectContextEngine ranks candidates via MultiSignalRanker, plans routes via EvoRoutePlanner, searches paths via EvoBeamSearchEngine, aggregates proofs via ProofChainAggregator, and passes them to ContextAssembler.",
            relevant_files=["apps/api/src/services/context_engine/engine.py", "apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["ProjectContextEngine", "MultiSignalRanker", "EvoRoutePlanner", "ContextAssembler"],
            relevant_chunk_ids=["94fbd79_engine_evoreasoner_pipeline"],
            expected_relations=[
                {"subject": "ProjectContextEngine", "relation": "CALLS", "object": "MultiSignalRanker"},
                {"subject": "ProjectContextEngine", "relation": "CALLS", "object": "EvoRoutePlanner"},
                {"subject": "ProjectContextEngine", "relation": "CALLS", "object": "ContextAssembler"}
            ],
            expected_paths=[
                ["ProjectContextEngine", "CALLS", "MultiSignalRanker"],
                ["ProjectContextEngine", "CALLS", "EvoRoutePlanner"],
                ["EvoRoutePlanner", "PLANS_FOR", "EvoBeamSearchEngine"],
                ["EvoBeamSearchEngine", "FEEDS_INTO", "ContextAssembler"]
            ],
            commit_sha="94fbd79",
            rationale="4-hop architectural pipeline traversal.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q26_multihop_api_to_db_persistence",
            category="Multi-Hop Reasoning",
            query="Which components connect ApiService routes to database persistence in PostgreSQL?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ApiService routes call ProjectContextEngine, which uses MultiSignalRetriever with AsyncSession connected to PostgreSQL.",
            relevant_files=["apps/api/src/services/context_engine/engine.py", "apps/api/src/services/context_engine/retriever.py", "apps/api/src/core/session.py"],
            relevant_symbols=["ProjectContextEngine", "MultiSignalRetriever", "AsyncSession"],
            relevant_chunk_ids=["773b740_atom-code-179714888d1e4278", "773b740_atom-code-2a2772c95d198b5f"],
            expected_relations=[
                {"subject": "ProjectContextEngine", "relation": "CALLS", "object": "MultiSignalRetriever"},
                {"subject": "MultiSignalRetriever", "relation": "USES", "object": "AsyncSession"}
            ],
            expected_paths=[
                ["ProjectContextEngine", "CALLS", "MultiSignalRetriever"],
                ["MultiSignalRetriever", "USES", "AsyncSession"]
            ],
            commit_sha="773b740",
            rationale="Multi-hop request-to-database path.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q27_multihop_decomposer_to_evokg_triplets",
            category="Multi-Hop Reasoning",
            query="How does CodeAtomDecomposer connect to EvoKGTriplet persistence?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="CodeAtomDecomposer produces relations reconciled by reconcile_code_relationships, checked by EvoKGContradictionEngine, and persisted as EvoKGTriplets by EvoKGPersistenceService.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py", "apps/api/src/services/evokg/contradiction.py", "apps/api/src/services/evokg/service.py"],
            relevant_symbols=["CodeAtomDecomposer", "reconcile_code_relationships", "EvoKGContradictionEngine", "EvoKGPersistenceService", "EvoKGTriplet"],
            relevant_chunk_ids=["2905a44_evokg_persistence_service"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "PRODUCES", "object": "AtomicCodeRelation"},
                {"subject": "AtomicCodeRelation", "relation": "RESOLVED_BY", "object": "EvoKGContradictionEngine"},
                {"subject": "EvoKGContradictionEngine", "relation": "PERSISTED_BY", "object": "EvoKGPersistenceService"}
            ],
            expected_paths=[
                ["CodeAtomDecomposer", "PRODUCES", "AtomicCodeRelation"],
                ["AtomicCodeRelation", "RESOLVED_BY", "EvoKGContradictionEngine"],
                ["EvoKGContradictionEngine", "PERSISTED_BY", "EvoKGPersistenceService"]
            ],
            commit_sha="2905a44",
            rationale="3-hop decomposition to persistent graph chain.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q28_multihop_llm_provider_hierarchy",
            category="Multi-Hop Reasoning",
            query="Which classes inherit or implement the LLMProvider interface and connect to GroundedAnswer generation?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ClaudeLLMProvider and GroqLLMProvider implement LLMProvider, which produces GroundedAnswer for ProjectContextEngine.",
            relevant_files=["apps/api/src/services/llm/base.py", "apps/api/src/services/llm/claude.py", "apps/api/src/services/llm/groq.py"],
            relevant_symbols=["LLMProvider", "ClaudeLLMProvider", "GroqLLMProvider", "GroundedAnswer"],
            relevant_chunk_ids=["773b740_llm_provider_base"],
            expected_relations=[
                {"subject": "ClaudeLLMProvider", "relation": "INHERITS", "object": "LLMProvider"},
                {"subject": "GroqLLMProvider", "relation": "INHERITS", "object": "LLMProvider"},
                {"subject": "LLMProvider", "relation": "PRODUCES", "object": "GroundedAnswer"}
            ],
            expected_paths=[
                ["ClaudeLLMProvider", "INHERITS", "LLMProvider"],
                ["LLMProvider", "PRODUCES", "GroundedAnswer"]
            ],
            commit_sha="773b740",
            rationale="Multi-hop polymorphic provider inheritance path.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q29_multihop_star_rag_to_ranker_ppr",
            category="Multi-Hop Reasoning",
            query="How does StarRagContextService propagate relevance scores to MultiSignalRanker?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="StarRagContextService builds a temporal rule graph, computes Personalized PageRank, and injects graph scores into MultiSignalRanker.",
            relevant_files=["apps/api/src/services/context_engine/star_rag.py", "apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["StarRagContextService", "PersonalizedPageRank", "MultiSignalRanker"],
            relevant_chunk_ids=["42096a5_atom-code-f01cbbaf67af069e", "42096a5_atom-code-df18c56775cdfd95"],
            expected_relations=[
                {"subject": "StarRagContextService", "relation": "COMPUTES", "object": "PersonalizedPageRank"},
                {"subject": "PersonalizedPageRank", "relation": "BOOSTS", "object": "MultiSignalRanker"}
            ],
            expected_paths=[
                ["StarRagContextService", "COMPUTES", "PersonalizedPageRank"],
                ["PersonalizedPageRank", "BOOSTS", "MultiSignalRanker"]
            ],
            commit_sha="42096a5",
            rationale="2-hop algorithm to scoring pipeline.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q30_multihop_proof_aggregator_combination",
            category="Multi-Hop Reasoning",
            query="How does ProofChainAggregator combine two complementary hops into a composite chain?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ProofChainAggregator matches chain_a.target_entity with chain_b.source_entity, checks temporal intersection, and forms a synthesized multi-hop chain.",
            relevant_files=["apps/api/src/services/evoreasoner/aggregator.py"],
            relevant_symbols=["ProofChainAggregator", "_combine_complementary_chains"],
            relevant_chunk_ids=["94fbd79_evoreasoner_aggregator"],
            expected_relations=[
                {"subject": "ProofChainAggregator", "relation": "COMBINES", "object": "GroundedProofChain"}
            ],
            expected_paths=[["ProofChainAggregator", "COMBINES", "GroundedProofChain"]],
            commit_sha="94fbd79",
            rationale="Multi-hop path synthesis within aggregator.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q31_multihop_memotime_to_assembler",
            category="Multi-Hop Reasoning",
            query="How does MemoTimeContextService inform ContextAssembler of historical intervals?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="MemoTime classifies temporal intents, evaluates interval algebra in Tree-of-Time, and formats valid/ended annotations in ContextAssembler.",
            relevant_files=["apps/api/src/services/context_engine/memotime.py", "apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["MemoTimeContextService", "TreeOfTime", "ContextAssembler"],
            relevant_chunk_ids=["c49db6e_memotime_service"],
            expected_relations=[
                {"subject": "MemoTimeContextService", "relation": "CALLS", "object": "TreeOfTime"},
                {"subject": "TreeOfTime", "relation": "ANNOTATES", "object": "ContextAssembler"}
            ],
            expected_paths=[
                ["MemoTimeContextService", "CALLS", "TreeOfTime"],
                ["TreeOfTime", "ANNOTATES", "ContextAssembler"]
            ],
            commit_sha="c49db6e",
            rationale="2-hop temporal intent to markdown annotation flow.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q32_multihop_evoplanner_route_selection",
            category="Multi-Hop Reasoning",
            query="How does EvoRoutePlanner select canonical relations based on query analysis?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="EvoRoutePlanner maps analyzed query keywords and symbol candidates to canonical predicates and estimates route costs.",
            relevant_files=["apps/api/src/services/evoreasoner/planner.py", "apps/api/src/services/context_engine/query_analyzer.py"],
            relevant_symbols=["EvoRoutePlanner", "analyze_query_async"],
            relevant_chunk_ids=["94fbd79_evoreasoner_planner"],
            expected_relations=[
                {"subject": "analyze_query_async", "relation": "FEEDS_INTO", "object": "EvoRoutePlanner"},
                {"subject": "EvoRoutePlanner", "relation": "GENERATES", "object": "ReasoningRoute"}
            ],
            expected_paths=[
                ["analyze_query_async", "FEEDS_INTO", "EvoRoutePlanner"],
                ["EvoRoutePlanner", "GENERATES", "ReasoningRoute"]
            ],
            commit_sha="94fbd79",
            rationale="Multi-hop query analysis to route plan generation.",
        )
    )

    # =========================================================================
    # CATEGORY E: CONTRADICTION AND SUPERSESSION (8 queries)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q33_contradiction_supersede_exclusive_return",
            category="Contradiction and Supersession",
            query="How is an exclusive relationship superseded when a new return type is asserted for a function in the same scope?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Old triplet valid_to is closed, superseded_by_id is set to new triplet ID, and new triplet supersedes_id points to old triplet.",
            relevant_files=["apps/api/src/services/evokg/contradiction.py"],
            relevant_symbols=["EvoKGContradictionEngine", "resolve_contradictions"],
            relevant_chunk_ids=["2905a44_evokg_contradiction_engine"],
            expected_relations=[
                {"subject": "new_return_type", "relation": "SUPERSEDES", "object": "old_return_type"}
            ],
            expected_paths=[["new_return_type", "SUPERSEDES", "old_return_type"]],
            commit_sha="2905a44",
            rationale="Verifies exclusive relationship supersession mechanics.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q34_contradiction_coexist_non_exclusive",
            category="Contradiction and Supersession",
            query="What happens when two non-exclusive relationships (CALLS) are asserted for the same caller?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Non-exclusive relationships like CALLS and IMPORTS coexist concurrently without closing or superseding one another.",
            relevant_files=["apps/api/src/services/code_atom/taxonomy.py", "apps/api/src/services/evokg/contradiction.py"],
            relevant_symbols=["CodeRelationTaxonomy", "PropertyExclusivity"],
            relevant_chunk_ids=["6626c5c_evokg_taxonomy"],
            expected_relations=[
                {"subject": "Caller", "relation": "CALLS", "object": "CalleeA"},
                {"subject": "Caller", "relation": "CALLS", "object": "CalleeB"}
            ],
            expected_paths=[["Caller", "CALLS", "CalleeA"], ["Caller", "CALLS", "CalleeB"]],
            commit_sha="6626c5c",
            rationale="Verifies non-exclusive coexistence without false supersession.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q35_contradiction_exclusive_conflict_annotation",
            category="Contradiction and Supersession",
            query="How are conflicting exclusive assertions on different branches resolved and annotated upon merge?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Conflicting assertions are preserved with has_temporal_conflict=True and annotated with exclusive_relation_conflict.",
            relevant_files=["apps/api/src/services/evoreasoner/aggregator.py"],
            relevant_symbols=["ProofChainAggregator", "_evaluate_conflicts_and_uncertainty"],
            relevant_chunk_ids=["94fbd79_evoreasoner_aggregator"],
            expected_relations=[
                {"subject": "exclusive_conflict", "relation": "ANNOTATED_WITH", "object": "has_conflict"}
            ],
            expected_paths=[["exclusive_conflict", "ANNOTATED_WITH", "has_conflict"]],
            commit_sha="94fbd79",
            rationale="Verifies explicit conflict annotation without data loss.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q36_contradiction_superseded_demotion_current",
            category="Contradiction and Supersession",
            query="What is the score penalty applied to superseded facts when queried under CURRENT temporal intent?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Superseded facts receive a severe penalty to 0.05 score in PathScorer and are excluded by the database query.",
            relevant_files=["apps/api/src/services/evoreasoner/path_scorer.py", "apps/api/src/services/evoreasoner/beam_search.py"],
            relevant_symbols=["PathScorer", "evaluate_path"],
            relevant_chunk_ids=["94fbd79_evoreasoner_path_scorer"],
            expected_relations=[
                {"subject": "superseded_fact", "relation": "SCORED_AT", "object": "0.05"}
            ],
            expected_paths=[["superseded_fact", "SCORED_AT", "0.05"]],
            commit_sha="94fbd79",
            rationale="Verifies zero-tolerance for superseded facts in current queries.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q37_contradiction_expired_before_observation",
            category="Contradiction and Supersession",
            query="How does EvoKG handle an assertion whose validity interval expires before the observation time?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Flagged with has_temporal_conflict=True and excluded from active current state retrieval.",
            relevant_files=["apps/api/src/services/evoreasoner/beam_search.py", "apps/api/src/models/evokg/triplet.py"],
            relevant_symbols=["EvoBeamSearchEngine", "EvoKGTriplet"],
            relevant_chunk_ids=["94fbd79_evoreasoner_beam_search"],
            expected_relations=[
                {"subject": "expired_assertion", "relation": "EXCLUDED_FROM", "object": "CURRENT"}
            ],
            expected_paths=[["expired_assertion", "EXCLUDED_FROM", "CURRENT"]],
            commit_sha="94fbd79",
            rationale="Verifies interval expiration boundary handling.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q38_contradiction_proof_aggregator_penalties",
            category="Contradiction and Supersession",
            query="How does ProofChainAggregator penalize conflicting proof chains in final ranking?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Applies config.conflict_penalty (0.20 deduction) to the proof_score.",
            relevant_files=["apps/api/src/services/evoreasoner/aggregator.py"],
            relevant_symbols=["ProofChainAggregator", "ProofAggregationConfig"],
            relevant_chunk_ids=["94fbd79_evoreasoner_aggregator"],
            expected_relations=[
                {"subject": "ProofChainAggregator", "relation": "PENALIZES", "object": "conflict_penalty"}
            ],
            expected_paths=[["ProofChainAggregator", "PENALIZES", "conflict_penalty"]],
            commit_sha="94fbd79",
            rationale="Verifies explicit numeric penalty application for conflicts.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q39_contradiction_scope_isolated_exclusivity",
            category="Contradiction and Supersession",
            query="What distinguishes scope-isolated exclusive properties from global exclusive properties?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Scope key isolates exclusive properties (e.g. return types within distinct function scopes) without cross-function collisions.",
            relevant_files=["apps/api/src/services/code_atom/taxonomy.py", "apps/api/src/models/evokg/triplet.py"],
            relevant_symbols=["CodeRelationTaxonomy", "scope_key"],
            relevant_chunk_ids=["6626c5c_evokg_taxonomy"],
            expected_relations=[
                {"subject": "scope_key", "relation": "ISOLATES", "object": "PropertyExclusivity"}
            ],
            expected_paths=[["scope_key", "ISOLATES", "PropertyExclusivity"]],
            commit_sha="6626c5c",
            rationale="Verifies scope key isolation in partial unique constraints.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q40_contradiction_historical_row_preservation",
            category="Contradiction and Supersession",
            query="How does supersession preserve historical lineage without deleting superseded database rows?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Rows are never deleted; valid_to timestamp is closed and superseded_by_id foreign key links to the replacement.",
            relevant_files=["apps/api/src/services/evokg/service.py", "apps/api/src/models/evokg/triplet.py"],
            relevant_symbols=["EvoKGPersistenceService", "superseded_by_id"],
            relevant_chunk_ids=["2905a44_evokg_persistence_service"],
            expected_relations=[
                {"subject": "EvoKGPersistenceService", "relation": "PRESERVES", "object": "historical_rows"}
            ],
            expected_paths=[["EvoKGPersistenceService", "PRESERVES", "historical_rows"]],
            commit_sha="2905a44",
            rationale="Verifies non-destructive temporal persistence.",
        )
    )

    # =========================================================================
    # CATEGORY F: INSUFFICIENT-EVIDENCE QUERIES (ABSTENTION) (8 queries)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q41_abstain_audio_streaming",
            category="Insufficient Evidence (Abstention)",
            query="How is real-time bidirectional WebSocket audio streaming and Opus packet transcoding handled?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="I do not have sufficient evidence in the repository to answer this question. No real-time WebSocket audio streaming or Opus transcoding is implemented.",
            relevant_files=[],
            relevant_symbols=[],
            should_abstain=True,
            abstention_rationale="Out-of-corpus query; audio streaming is absent from repository.",
            rationale="Verifies abstention on unindexed domain.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q42_abstain_kubernetes_crd_controller",
            category="Insufficient Evidence (Abstention)",
            query="What is the implementation of KubernetesCRDController in install-unotusk?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="I do not have sufficient evidence in the repository. No KubernetesCRDController exists.",
            relevant_files=[],
            relevant_symbols=[],
            should_abstain=True,
            abstention_rationale="Non-existent symbol; no Kubernetes CRD controller in codebase.",
            rationale="Verifies hallucination prevention on non-existent symbols.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q43_abstain_migrations_before_2024",
            category="Insufficient Evidence (Abstention)",
            query="What were the database migrations committed before 2024-01-01?",
            intent=TemporalIntentType.BEFORE,
            is_temporal=True,
            expected_answer="No evidence exists for database migrations prior to 2024-01-01. The repository history begins in 2026.",
            relevant_files=[],
            relevant_symbols=[],
            as_of=datetime.fromisoformat("2024-01-01T00:00:00+00:00"),
            should_abstain=True,
            abstention_rationale="Temporal anchor predates repository inception.",
            rationale="Verifies temporal boundary abstention when facts do not exist.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q44_abstain_kafka_producer_cluster",
            category="Insufficient Evidence (Abstention)",
            query="How does KafkaProducerCluster publish events to partition 3?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="I do not have sufficient evidence. Kafka is not used in Unotusk MVP (Redis worker is used).",
            relevant_files=[],
            relevant_symbols=[],
            should_abstain=True,
            abstention_rationale="Kafka is explicitly out of scope for MVP.",
            rationale="Verifies rejection of out-of-scope technology stack.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q45_abstain_graphql_federation",
            category="Insufficient Evidence (Abstention)",
            query="What is the implementation of GraphQLFederationGateway in apps/api?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="I do not have sufficient evidence in the repository. The API uses FastAPI REST, not GraphQL federation.",
            relevant_files=[],
            relevant_symbols=[],
            should_abstain=True,
            abstention_rationale="Non-existent framework; API is REST only.",
            rationale="Verifies rejection of non-existent architecture.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q46_abstain_autonomous_code_bot",
            category="Insufficient Evidence (Abstention)",
            query="What were the changes to AutonomousCodeMutationBot in commit abcdef0?",
            intent=TemporalIntentType.DIFF,
            is_temporal=True,
            expected_answer="I do not have sufficient evidence. Autonomous code mutation bots are explicitly out of scope.",
            relevant_files=[],
            relevant_symbols=[],
            commit_sha="abcdef0",
            should_abstain=True,
            abstention_rationale="Out-of-scope feature and fictitious commit SHA.",
            rationale="Verifies rejection of fictitious commits and out-of-scope features.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q47_abstain_neo4j_cluster_relation",
            category="Insufficient Evidence (Abstention)",
            query="What is the relation between RedisWorker and Neo4jCluster?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="I do not have sufficient evidence. Neo4j is not used in Unotusk MVP (PostgreSQL 16 + pgvector is used).",
            relevant_files=[],
            relevant_symbols=[],
            should_abstain=True,
            abstention_rationale="Neo4j is explicitly discarded in MVP architecture.",
            rationale="Verifies compliance with out-of-scope constraints.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q48_abstain_unknown_function_signature",
            category="Insufficient Evidence (Abstention)",
            query="What was the return type of unknown_magic_function() in 2025?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="I do not have sufficient evidence in the repository to locate unknown_magic_function.",
            relevant_files=[],
            relevant_symbols=[],
            should_abstain=True,
            abstention_rationale="Fictitious symbol with no evidence in repository.",
            rationale="Verifies clean abstention on unknown symbols.",
        )
    )

    # =========================================================================
    # CATEGORY G: BRANCH AND PROVENANCE QUERIES (8 queries)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q49_provenance_integration_provider",
            category="Branch and Provenance",
            query="Which repository integration manages GitHub webhooks in RepositoryService?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Integration model with provider=GITHUB in repository_service.py manages GitHub webhooks.",
            relevant_files=["apps/api/src/services/repository_service.py", "apps/api/src/models/integration.py"],
            relevant_symbols=["RepositoryService", "Integration", "IntegrationProvider"],
            relevant_chunk_ids=["773b740_repository_service_integration"],
            expected_relations=[
                {"subject": "RepositoryService", "relation": "USES", "object": "Integration"}
            ],
            expected_paths=[["RepositoryService", "USES", "Integration"]],
            commit_sha="773b740",
            rationale="Verifies integration model provenance.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q50_provenance_evokg_migration_sha",
            category="Branch and Provenance",
            query="What commit SHA introduced the EvoKG partial unique index uq_evokg_active_exclusive?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Commit 2905a44 introduced Alembic migration 0011_evokg_triplets.py with partial unique index uq_evokg_active_exclusive.",
            relevant_files=["alembic/versions/0011_evokg_triplets.py"],
            relevant_symbols=["uq_evokg_active_exclusive"],
            relevant_chunk_ids=["2905a44_migration_0011"],
            expected_relations=[
                {"subject": "0011_evokg_triplets.py", "relation": "CREATES_INDEX", "object": "uq_evokg_active_exclusive"}
            ],
            expected_paths=[["0011_evokg_triplets.py", "CREATES_INDEX", "uq_evokg_active_exclusive"]],
            commit_sha="2905a44",
            rationale="Verifies migration provenance and commit SHA attribution.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q51_provenance_evoreasoner_commit_sha",
            category="Branch and Provenance",
            query="What commit SHA introduced the EvoReasoner multi-route planner and proof chains?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Commit 94fbd79 introduced the EvoReasoner multi-route planner, beam search, and ContextAssembler proof chains.",
            relevant_files=["apps/api/src/services/evoreasoner/planner.py", "apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["EvoRoutePlanner", "ContextAssembler"],
            relevant_chunk_ids=["94fbd79_evoreasoner_planner"],
            expected_relations=[
                {"subject": "94fbd79", "relation": "INTRODUCES", "object": "EvoRoutePlanner"}
            ],
            expected_paths=[["94fbd79", "INTRODUCES", "EvoRoutePlanner"]],
            commit_sha="94fbd79",
            rationale="Verifies milestone commit SHA tracking.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q52_provenance_branch_isolation_sql",
            category="Branch and Provenance",
            query="How does branch isolation prevent feature branch triplets from leaking into main branch queries?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="SQL filters enforce EvoKGTriplet.branch == branch, and ProofChainValidator validates expected_branch.",
            relevant_files=["apps/api/src/services/evoreasoner/beam_search.py", "apps/api/src/services/evoreasoner/validator.py"],
            relevant_symbols=["EvoBeamSearchEngine", "ProofChainValidator"],
            relevant_chunk_ids=["94fbd79_evoreasoner_beam_search"],
            expected_relations=[
                {"subject": "EvoBeamSearchEngine", "relation": "FILTERS_BY", "object": "branch"}
            ],
            expected_paths=[["EvoBeamSearchEngine", "FILTERS_BY", "branch"]],
            commit_sha="94fbd79",
            rationale="Verifies multi-branch query isolation.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q53_provenance_chunk_mapper_metadata",
            category="Branch and Provenance",
            query="What is the provenance metadata attached to decomposed atomic code changes in chunk_mapper?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Metadata includes commit_sha, committed_at, snapshot_id, repository_id, and file_id.",
            relevant_files=["apps/api/src/services/code_atom/chunk_mapper.py"],
            relevant_symbols=["map_atomic_code_change_to_code_chunk"],
            relevant_chunk_ids=["b094f01_atom-code-d1f3111f4cf5104d"],
            expected_relations=[
                {"subject": "map_atomic_code_change_to_code_chunk", "relation": "ATTACH_METADATA", "object": "commit_sha"}
            ],
            expected_paths=[["map_atomic_code_change_to_code_chunk", "ATTACH_METADATA", "commit_sha"]],
            commit_sha="b094f01",
            rationale="Verifies atomic chunk provenance tracking.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q54_provenance_proof_chain_hop_provenance",
            category="Branch and Provenance",
            query="How does ProofChainHop record Git provenance for an individual verified hop?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ProofChainHop stores commit_sha, branch, triplet_id, and arbitrary provenance key-values.",
            relevant_files=["apps/api/src/schemas/evoreasoner.py"],
            relevant_symbols=["ProofChainHop"],
            relevant_chunk_ids=["94fbd79_evoreasoner_schemas_proof_hop"],
            expected_relations=[
                {"subject": "ProofChainHop", "relation": "HAS_FIELD", "object": "commit_sha"}
            ],
            expected_paths=[["ProofChainHop", "HAS_FIELD", "commit_sha"]],
            commit_sha="94fbd79",
            rationale="Verifies individual proof hop provenance schema.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q55_provenance_decomposer_ast_commit",
            category="Branch and Provenance",
            query="What is the commit SHA that added Tree-sitter innermost scope resolution in CodeAtomDecomposer?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Commit be1b5b5 introduced innermost scope resolution in CodeAtomDecomposer.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer"],
            relevant_chunk_ids=["be1b5b5_atom-code-8ed6126854ff06bd"],
            expected_relations=[
                {"subject": "be1b5b5", "relation": "INTRODUCES", "object": "innermost_scope_resolution"}
            ],
            expected_paths=[["be1b5b5", "INTRODUCES", "innermost_scope_resolution"]],
            commit_sha="be1b5b5",
            rationale="Verifies commit SHA traceability for scope resolution.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q56_provenance_repo_branch_indexing",
            category="Branch and Provenance",
            query="How are multi-branch repository triplets differentiated in PostgreSQL persistence?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Differentiated by the branch column, indexed in ix_evokg_repo_branch_subject and partial unique index uq_evokg_active_exclusive.",
            relevant_files=["apps/api/src/models/evokg/triplet.py", "alembic/versions/0011_evokg_triplets.py"],
            relevant_symbols=["EvoKGTriplet", "ix_evokg_repo_branch_subject"],
            relevant_chunk_ids=["2905a44_evokg_triplet_model"],
            expected_relations=[
                {"subject": "EvoKGTriplet", "relation": "HAS_INDEX", "object": "ix_evokg_repo_branch_subject"}
            ],
            expected_paths=[["EvoKGTriplet", "HAS_INDEX", "ix_evokg_repo_branch_subject"]],
            commit_sha="2905a44",
            rationale="Verifies branch column and database index layout.",
        )
    )

    return queries


def get_expanded_evoreasoner_benchmark_dataset() -> list[GroundTruthQuery]:
    """
    Returns the expanded 84-query benchmark dataset.
    Preserves all 56 original reference queries (q01-q56) and appends 28 independently
    authored ground-truth queries (q57-q84, 4 additional queries per category).
    """
    queries = list(get_evoreasoner_benchmark_dataset())

    # =========================================================================
    # CATEGORY A: CURRENT CODE UNDERSTANDING (Expanded: q57 - q60)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q57_current_beam_search_def",
            category="Current Code Understanding",
            query="What is the function signature and primary return type of EvoBeamSearchEngine.search_paths?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="EvoBeamSearchEngine.search_paths takes session, repository_id, route_plan, branch, config, and temporal filters, returning a PathSearchResult.",
            relevant_files=["apps/api/src/services/evoreasoner/beam_search.py"],
            relevant_symbols=["EvoBeamSearchEngine", "search_paths"],
            expected_relations=[
                {"subject": "EvoBeamSearchEngine", "relation": "DEFINES_METHOD", "object": "search_paths"}
            ],
            expected_paths=[["EvoBeamSearchEngine", "DEFINES_METHOD", "search_paths"]],
            commit_sha="94fbd79",
            rationale="Verifies current beam search execution entry point and return contract.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q58_current_route_planner_plan",
            category="Current Code Understanding",
            query="How does EvoRoutePlanner.generate_multi_route_plan select and score reasoning routes for a query?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="EvoRoutePlanner extracts seed entities, matches candidate graph patterns, estimates costs via HeuristicRuleEstimator, deduplicates routes, and returns a MultiRoutePlan.",
            relevant_files=["apps/api/src/services/evoreasoner/planner.py"],
            relevant_symbols=["EvoRoutePlanner", "generate_multi_route_plan"],
            expected_relations=[
                {"subject": "EvoRoutePlanner", "relation": "DEFINES_METHOD", "object": "generate_multi_route_plan"}
            ],
            expected_paths=[["EvoRoutePlanner", "DEFINES_METHOD", "generate_multi_route_plan"]],
            commit_sha="94fbd79",
            rationale="Verifies current route planning heuristics and MultiRoutePlan assembly.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q59_current_path_scorer_breakdown",
            category="Current Code Understanding",
            query="What metrics compose the evidence path score in PathScorer.evaluate_path?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="PathScorer evaluates confidence_score, temporal_consistency, hop_relevance, depth_penalty, and route_cost, returning an aggregated score and PathScoreBreakdown.",
            relevant_files=["apps/api/src/services/evoreasoner/path_scorer.py"],
            relevant_symbols=["PathScorer", "evaluate_path"],
            expected_relations=[
                {"subject": "PathScorer", "relation": "DEFINES_METHOD", "object": "evaluate_path"}
            ],
            expected_paths=[["PathScorer", "DEFINES_METHOD", "evaluate_path"]],
            commit_sha="94fbd79",
            rationale="Verifies multi-factor path scoring and breakdown components.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q60_current_aggregator_schema",
            category="Current Code Understanding",
            query="What is the schema and structure of GroundedProofChain produced by ProofChainAggregator?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="GroundedProofChain contains chain_id, route_id, route_perspective, hops, confidence_score, temporal_validity, and formatting helpers.",
            relevant_files=["apps/api/src/schemas/evoreasoner.py", "apps/api/src/services/evoreasoner/aggregator.py"],
            relevant_symbols=["GroundedProofChain", "ProofChainAggregator"],
            expected_relations=[
                {"subject": "ProofChainAggregator", "relation": "PRODUCES", "object": "GroundedProofChain"}
            ],
            expected_paths=[["ProofChainAggregator", "PRODUCES", "GroundedProofChain"]],
            commit_sha="94fbd79",
            rationale="Verifies proof-chain schema and hop representations.",
        )
    )

    # =========================================================================
    # CATEGORY B: HISTORICAL CODE UNDERSTANDING (Expanded: q61 - q64)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q61_historical_decomposer_heuristic",
            category="Historical Code Understanding",
            query="How was _find_enclosing_scope_heuristic implemented in CodeAtomDecomposer before innermost scope resolution?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="Before commit be1b5b5, CodeAtomDecomposer used _find_enclosing_scope_heuristic which performed shallow lexical regex indentation parsing.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer", "_find_enclosing_scope_heuristic"],
            superseded_ids=["b094f01_atom-code-8e61d3b82fcd7f1e"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "CALLS", "object": "_find_enclosing_scope_heuristic"}
            ],
            expected_paths=[["CodeAtomDecomposer", "CALLS", "_find_enclosing_scope_heuristic"]],
            commit_sha="b094f01",
            rationale="Verifies historical AST decomposer heuristic retrieval.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q62_historical_reconcile_unconstrained",
            category="Historical Code Understanding",
            query="What was the initial return type of reconcile_code_relationships before exclusive property enforcement?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="Initially, reconcile_code_relationships returned list[AtomicCodeRelation] without filtering or resolving contradictory exclusive relations.",
            relevant_files=["apps/api/src/services/code_atom/reconciler.py"],
            relevant_symbols=["reconcile_code_relationships"],
            expected_relations=[
                {"subject": "reconcile_code_relationships", "relation": "DEFINES_RETURN_TYPE", "object": "list[AtomicCodeRelation]"}
            ],
            expected_paths=[["reconcile_code_relationships", "DEFINES_RETURN_TYPE", "list[AtomicCodeRelation]"]],
            commit_sha="6626c5c",
            rationale="Verifies historical unconstrained code relationship reconciliation.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q63_historical_atomic_relation_origin",
            category="Historical Code Understanding",
            query="How were atomic code relations originally introduced in b094f01 before the EvoKG taxonomy?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="In commit b094f01, AtomicCodeRelation was defined as a simple dataclass with source_atom_id, target_atom_id, and relation_type.",
            relevant_files=["apps/api/src/services/code_atom/models.py"],
            relevant_symbols=["AtomicCodeRelation"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "PRODUCES", "object": "AtomicCodeRelation"}
            ],
            expected_paths=[["CodeAtomDecomposer", "PRODUCES", "AtomicCodeRelation"]],
            commit_sha="b094f01",
            rationale="Verifies initial atom relation model prior to contradiction engine.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q64_historical_multisignal_ranker_weights",
            category="Historical Code Understanding",
            query="What was the original weight configuration of MultiSignalRanker when first introduced in commit 773b740?",
            intent=TemporalIntentType.HISTORICAL,
            is_temporal=True,
            expected_answer="In commit 773b740, MultiSignalRanker weighted semantic similarity at 0.50, exact match at 0.30, and recency at 0.20.",
            relevant_files=["apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["MultiSignalRanker"],
            expected_relations=[
                {"subject": "MultiSignalRanker", "relation": "CALLS", "object": "rank_candidates"}
            ],
            expected_paths=[["MultiSignalRanker", "CALLS", "rank_candidates"]],
            commit_sha="773b740",
            rationale="Verifies historical multi-signal ranking weights.",
        )
    )

    # =========================================================================
    # CATEGORY C: TEMPORAL REASONING (Expanded: q65 - q68)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q65_temporal_before_scope_change",
            category="Temporal Reasoning",
            query="What was the active implementation of CodeAtomDecomposer before commit be1b5b5?",
            intent=TemporalIntentType.BEFORE,
            is_temporal=True,
            expected_answer="Before commit be1b5b5, CodeAtomDecomposer used lexical heuristic scoping rather than Tree-sitter AST hierarchy.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "CALLS", "object": "_find_enclosing_scope_heuristic"}
            ],
            expected_paths=[["CodeAtomDecomposer", "CALLS", "_find_enclosing_scope_heuristic"]],
            commit_sha="b094f01",
            rationale="Verifies BEFORE temporal anchor boundary handling.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q66_temporal_after_multisignal",
            category="Temporal Reasoning",
            query="What retrieval components were added after commit 773b740?",
            intent=TemporalIntentType.AFTER,
            is_temporal=True,
            expected_answer="After commit 773b740, EvoKG persistence (2905a44) and EvoReasoner multi-route planning and beam search (94fbd79) were added.",
            relevant_files=["apps/api/src/services/context_engine/ranker.py", "apps/api/src/services/evoreasoner/planner.py"],
            relevant_symbols=["EvoRoutePlanner", "EvoBeamSearchEngine"],
            expected_relations=[
                {"subject": "ProjectContextEngine", "relation": "CALLS", "object": "EvoRoutePlanner"}
            ],
            expected_paths=[["ProjectContextEngine", "CALLS", "EvoRoutePlanner"]],
            commit_sha="773b740",
            rationale="Verifies AFTER temporal anchor boundary progression.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q67_temporal_interval_october",
            category="Temporal Reasoning",
            query="What changes were introduced between 2026-10-14 and 2026-10-22?",
            intent=TemporalIntentType.INTERVAL,
            is_temporal=True,
            as_of=datetime(2026, 10, 14, 12, 0, 0, tzinfo=UTC),
            until=datetime(2026, 10, 22, 12, 0, 0, tzinfo=UTC),
            expected_answer="Between 2026-10-14 and 2026-10-22, Tree-sitter scope resolution (be1b5b5) and MultiSignalRanker with CompatibleVector (773b740) were introduced.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py", "apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["CodeAtomDecomposer", "MultiSignalRanker"],
            commit_sha="be1b5b5",
            rationale="Verifies closed INTERVAL temporal boundary filtering.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q68_temporal_diff_graph_evolution",
            category="Temporal Reasoning",
            query="What is the difference between commit b094f01 and commit 94fbd79 regarding graph reasoning?",
            intent=TemporalIntentType.DIFF,
            is_temporal=True,
            commit_sha="b094f01",
            target_commit_sha="94fbd79",
            expected_answer="Commit b094f01 had flat atomic code chunks; commit 94fbd79 added EvoRoutePlanner, beam search, and proof-chain aggregation over EvoKG triplets.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py", "apps/api/src/services/evoreasoner/planner.py"],
            relevant_symbols=["EvoRoutePlanner", "EvoBeamSearchEngine"],
            expected_relations=[
                {"subject": "EvoRoutePlanner", "relation": "PLANS_FOR", "object": "EvoBeamSearchEngine"}
            ],
            expected_paths=[["EvoRoutePlanner", "PLANS_FOR", "EvoBeamSearchEngine"]],
            rationale="Verifies DIFF temporal comparison across repository milestones.",
        )
    )

    # =========================================================================
    # CATEGORY D: MULTI-HOP REASONING (Expanded: q69 - q72)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q69_multihop_pce_to_beam_search",
            category="Multi-Hop Reasoning",
            query="How does ProjectContextEngine connect to EvoBeamSearchEngine through EvoRoutePlanner?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ProjectContextEngine calls EvoRoutePlanner, which plans routes for EvoBeamSearchEngine, which executes beam search.",
            relevant_files=["apps/api/src/services/context_engine/engine.py", "apps/api/src/services/evoreasoner/planner.py", "apps/api/src/services/evoreasoner/beam_search.py"],
            relevant_symbols=["ProjectContextEngine", "EvoRoutePlanner", "EvoBeamSearchEngine"],
            expected_paths=[["ProjectContextEngine", "CALLS", "EvoRoutePlanner"], ["EvoRoutePlanner", "PLANS_FOR", "EvoBeamSearchEngine"]],
            commit_sha="94fbd79",
            rationale="Verifies 2-hop architectural delegation from context engine to beam search.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q70_multihop_persistence_to_triplet",
            category="Multi-Hop Reasoning",
            query="How does EvoKGPersistenceService persist code relations to the EvoKGTriplet table?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="EvoKGPersistenceService writes resolved AtomicCodeRelations as EvoKGTriplet records in PostgreSQL.",
            relevant_files=["apps/api/src/services/evokg/persistence.py", "apps/api/src/models/evokg/triplet.py"],
            relevant_symbols=["EvoKGPersistenceService", "EvoKGTriplet"],
            expected_paths=[["EvoKGPersistenceService", "WRITES_TO", "EvoKGTriplet"]],
            commit_sha="2905a44",
            rationale="Verifies multi-hop persistence pipeline traversal.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q71_multihop_starrag_to_ranker",
            category="Multi-Hop Reasoning",
            query="How does StarRagContextService influence MultiSignalRanker via PersonalizedPageRank?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="StarRagContextService computes PersonalizedPageRank across the code graph to boost scores in MultiSignalRanker.",
            relevant_files=["apps/api/src/services/context_engine/ranker.py"],
            relevant_symbols=["StarRagContextService", "PersonalizedPageRank", "MultiSignalRanker"],
            expected_paths=[["StarRagContextService", "COMPUTES", "PersonalizedPageRank"], ["PersonalizedPageRank", "BOOSTS", "MultiSignalRanker"]],
            commit_sha="773b740",
            rationale="Verifies 2-hop STAR-RAG PPR graph boosting traversal.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q72_multihop_memotime_to_assembler",
            category="Multi-Hop Reasoning",
            query="How does MemoTimeService annotate ContextAssembler through TreeOfTime?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="MemoTimeService constructs TreeOfTime intervals which annotate context chunks in ContextAssembler.",
            relevant_files=["apps/api/src/services/context_engine/memotime.py", "apps/api/src/services/context_engine/assembler.py"],
            relevant_symbols=["MemoTimeService", "TreeOfTime", "ContextAssembler"],
            expected_paths=[["MemoTimeService", "CALLS", "TreeOfTime"], ["TreeOfTime", "ANNOTATES", "ContextAssembler"]],
            commit_sha="94fbd79",
            rationale="Verifies 2-hop MemoTime temporal tree traversal to ContextAssembler.",
        )
    )

    # =========================================================================
    # CATEGORY E: CONTRADICTION AND SUPERSESSION (Expanded: q73 - q76)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q73_contradiction_exclusive_branch_conflict",
            category="Contradiction and Supersession",
            query="How does the system resolve conflicting exclusive return types on a feature branch versus main?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Branch isolation restricts queries to the requested branch, and exclusive property rules flag conflicting relations as temporal conflicts.",
            relevant_files=["apps/api/src/services/evokg/contradiction.py"],
            relevant_symbols=["EvoKGContradictionEngine", "reconcile_code_relationships"],
            commit_sha="2905a44",
            rationale="Verifies exclusive relation contradiction detection across branches.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q74_supersession_decomposer_scope",
            category="Contradiction and Supersession",
            query="Which EvoKG triplet superseded the old lexical heuristic in CodeAtomDecomposer?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="The DEFINES_METHOD 'decompose' triplet at be1b5b5 superseded the old _find_enclosing_scope_heuristic triplet from b094f01.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer"],
            superseded_ids=["b094f01_atom-code-8e61d3b82fcd7f1e"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "DEFINES_METHOD", "object": "decompose"}
            ],
            expected_paths=[["CodeAtomDecomposer", "DEFINES_METHOD", "decompose"]],
            commit_sha="be1b5b5",
            rationale="Verifies explicit supersedes_id link retrieval and demotion.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q75_demotion_superseded_heuristic",
            category="Contradiction and Supersession",
            query="Why is _find_enclosing_scope_heuristic demoted when answering queries about the current decomposer?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Because its triplet has valid_to set and has been superseded, causing MemoTime and beam search to heavily penalize it under CURRENT intent.",
            relevant_files=["apps/api/src/services/code_atom/decomposer.py"],
            relevant_symbols=["CodeAtomDecomposer", "_find_enclosing_scope_heuristic"],
            superseded_ids=["b094f01_atom-code-8e61d3b82fcd7f1e"],
            expected_relations=[
                {"subject": "CodeAtomDecomposer", "relation": "DEFINES_METHOD", "object": "decompose"}
            ],
            expected_paths=[["CodeAtomDecomposer", "DEFINES_METHOD", "decompose"]],
            commit_sha="be1b5b5",
            rationale="Verifies zero superseded violations in top-ranked candidates.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q76_unique_index_active_exclusive",
            category="Contradiction and Supersession",
            query="How does PostgreSQL enforce that only one active relation exists per exclusive scope?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Using partial unique index uq_evokg_active_exclusive on (repository_id, branch, subject_id, relation, scope_key) WHERE is_exclusive = TRUE AND valid_to IS NULL.",
            relevant_files=["alembic/versions/0011_evokg_triplets.py", "apps/api/src/models/evokg/triplet.py"],
            relevant_symbols=["uq_evokg_active_exclusive", "EvoKGTriplet"],
            expected_relations=[
                {"subject": "0011_evokg_triplets.py", "relation": "CREATES_INDEX", "object": "uq_evokg_active_exclusive"}
            ],
            expected_paths=[["0011_evokg_triplets.py", "CREATES_INDEX", "uq_evokg_active_exclusive"]],
            commit_sha="2905a44",
            rationale="Verifies database integrity constraint for exclusive relations.",
        )
    )

    # =========================================================================
    # CATEGORY F: INSUFFICIENT EVIDENCE (ABSTENTION) (Expanded: q77 - q80)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q77_abstain_kubernetes_operator",
            category="Insufficient Evidence (Abstention)",
            query="What is the Kubernetes operator deployment configuration for Unotusk worker nodes?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="INSUFFICIENT EVIDENCE: Unotusk MVP uses local docker-compose and does not implement a Kubernetes operator.",
            should_abstain=True,
            abstention_rationale="Unotusk MVP explicitly uses local docker-compose; no Kubernetes operator exists.",
            rationale="Tests model abstention on ungrounded infrastructure requests.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q78_abstain_qdrant_partitioning",
            category="Insufficient Evidence (Abstention)",
            query="How does the Qdrant vector database handle collection partitioning in Unotusk?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="INSUFFICIENT EVIDENCE: Qdrant was discarded from Unotusk MVP in favor of PostgreSQL 16 + pgvector.",
            should_abstain=True,
            abstention_rationale="Qdrant was explicitly removed from the MVP architecture.",
            rationale="Tests model abstention on removed external vector database.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q79_abstain_okta_sso",
            category="Insufficient Evidence (Abstention)",
            query="What is the OAuth2 SSO provider configuration for Okta enterprise login in Unotusk?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="INSUFFICIENT EVIDENCE: Enterprise OIDC/SAML is out of scope for Unotusk MVP; authentication uses local email and JWT.",
            should_abstain=True,
            abstention_rationale="Enterprise SAML/OIDC is out of scope for the single-tenant MVP.",
            rationale="Tests model abstention on enterprise auth integrations.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q80_abstain_neo4j_graph",
            category="Insufficient Evidence (Abstention)",
            query="How does Neo4j store graph relationships in the Decision Lane?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="INSUFFICIENT EVIDENCE: Neo4j is not used in Unotusk; knowledge graphs are stored in PostgreSQL 16 (EvoKG).",
            should_abstain=True,
            abstention_rationale="Neo4j is not part of Unotusk; EvoKG is relational in PostgreSQL.",
            rationale="Tests model abstention on non-existent graph databases.",
        )
    )

    # =========================================================================
    # CATEGORY G: BRANCH AND PROVENANCE (Expanded: q81 - q84)
    # =========================================================================
    queries.append(
        GroundTruthQuery(
            query_id="q81_provenance_feature_branch_isolation",
            category="Branch and Provenance",
            query="How are triplets filtered when querying feature-alt-return versus main?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Queries filter by branch column, ensuring feature-alt-return triplets are never returned when querying main.",
            relevant_files=["apps/api/src/services/evoreasoner/beam_search.py"],
            relevant_symbols=["EvoBeamSearchEngine"],
            expected_relations=[
                {"subject": "EvoKGTriplet", "relation": "HAS_INDEX", "object": "ix_evokg_repo_branch_subject"}
            ],
            expected_paths=[["EvoKGTriplet", "HAS_INDEX", "ix_evokg_repo_branch_subject"]],
            commit_sha="94fbd79",
            rationale="Verifies branch isolation during graph traversal.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q82_provenance_migration_commit",
            category="Branch and Provenance",
            query="Which Alembic migration added the EvoKG triplets table and indexes?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="Migration 0011_evokg_triplets.py created table evokg_triplets, index ix_evokg_repo_branch_subject, and partial unique index uq_evokg_active_exclusive.",
            relevant_files=["alembic/versions/0011_evokg_triplets.py"],
            relevant_symbols=["0011_evokg_triplets.py"],
            expected_relations=[
                {"subject": "0011_evokg_triplets.py", "relation": "CREATES_INDEX", "object": "uq_evokg_active_exclusive"}
            ],
            expected_paths=[["0011_evokg_triplets.py", "CREATES_INDEX", "uq_evokg_active_exclusive"]],
            commit_sha="2905a44",
            rationale="Verifies migration provenance tracking.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q83_provenance_aggregator_repo_id",
            category="Branch and Provenance",
            query="How does ProofChainAggregator preserve repository_id and branch in GroundedProofChain?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="ProofChainAggregator explicitly propagates repository_id and branch parameters into each generated GroundedProofChain.",
            relevant_files=["apps/api/src/services/evoreasoner/aggregator.py"],
            relevant_symbols=["ProofChainAggregator"],
            expected_relations=[
                {"subject": "ProofChainAggregator", "relation": "PRODUCES", "object": "GroundedProofChain"}
            ],
            expected_paths=[["ProofChainAggregator", "PRODUCES", "GroundedProofChain"]],
            commit_sha="94fbd79",
            rationale="Verifies repository and branch metadata preservation in proof chains.",
        )
    )

    queries.append(
        GroundTruthQuery(
            query_id="q84_provenance_evidence_edge_commit",
            category="Branch and Provenance",
            query="How does EvidenceEdge store commit SHA provenance during graph beam search?",
            intent=TemporalIntentType.CURRENT,
            is_temporal=False,
            expected_answer="EvidenceEdge extracts commit_sha and provenance dictionary directly from the source EvoKGTriplet.",
            relevant_files=["apps/api/src/services/evoreasoner/beam_search.py", "apps/api/src/schemas/evoreasoner.py"],
            relevant_symbols=["EvidenceEdge", "EvoBeamSearchEngine"],
            expected_relations=[
                {"subject": "EvoBeamSearchEngine", "relation": "PRODUCES", "object": "EvidenceEdge"}
            ],
            expected_paths=[["EvoBeamSearchEngine", "PRODUCES", "EvidenceEdge"]],
            commit_sha="94fbd79",
            rationale="Verifies commit SHA and provenance extraction during beam search.",
        )
    )

    return queries
