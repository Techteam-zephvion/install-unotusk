# Shared and Cross-Track Component Inventory

## Executive Overview

This document presents a comprehensive technical inventory of all components shared across or integrating the four Code Lane intelligence tracks:
- **T1: ATOM** (Atomic Code Fact Extraction & Commit Chunk Mapping)
- **T2: EvoKG / EvoReasoner** (Evolutionary Knowledge Graph & Beam-Search Multi-Route Reasoner)
- **T3: MemoTime** (Operator-Aware Temporal Intent Classification & Experience Memory)
- **T4: STAR-RAG** (Spatio-Temporal Association Rule Mining & Seeded Personalized PageRank)

Rather than operating as disconnected silos, the four tracks are integrated into a unified multi-signal retrieval, reasoning, and synthesis pipeline orchestrated by `ProjectContextEngine`. This document details the 13 shared components, cross-track pipelines, isolation mechanisms, and common infrastructure that bind T1–T4 into the Unotusk MVP context engine.

---

## 1. MultiSignalRetriever

### 1.1 Metadata
- **Component Name**: MultiSignalRetriever
- **File Path**: `apps/api/src/services/context_engine/retriever.py`
- **Class / Functions**:
  - `class MultiSignalRetriever`
  - `MultiSignalRetriever.retrieve_candidates`
  - `_extract_chunk_metadata`
  - `_check_definition_match`
  - `generate_text_embedding`
  - `compute_cosine_similarity`
  - `RetrievedCandidate` (dataclass)

### 1.2 Tracks Using It
- **T1 (ATOM)**: Primary consumer and data source. Extracts ATOM commit metadata (`commit_sha`, `commit_message`, `fingerprint`, `provenance`, `chunk_type`, `atomic_code_facts`, `temporal_relations`) from `CodeChunk` records and attaches them to `RetrievedCandidate.metadata`. Resolves `generate_code_embedding` from `apps.api.src.services.code_atom.embedding`.
- **T2 (EvoKG)**: Reads `RetrievedCandidate` seeds to identify entry nodes for graph reasoning; utilizes file/symbol IDs retrieved by candidate search.
- **T3 (MemoTime)**: Consumes `RetrievedCandidate` candidate list and `AnalyzedQuery` to apply Allen interval temporal filtering and compute phase matching.
- **T4 (STAR-RAG)**: Uses candidate chunks as the event universe for Spatio-Temporal Association Rule mining and initial seed set.

### 1.3 Functionality Provided
Executes 6 parallel SQL retrieval channels bounded by `snapshot_id` and optional `repository_id`:
1. **File Search**: Exact, prefix, and substring ILIKE matching on `RepositoryFile.path` and `RepositoryFile.filename` (scoring 0.8–1.5).
2. **Symbol Search**: Exact, prefix, and qualified substring matching on `CodeSymbol.name` and `CodeSymbol.qualified_name` (scoring 0.8–1.6).
3. **Content / Code Chunk Search**: Lexical matching on chunk name, path, content, and commit message with definition weighting (`def_match` at 1.2, exact at 1.4). Unpacks ATOM metadata via `_extract_chunk_metadata`.
4. **Dependency Search**: External package name matching on `CodeDependency` (score 0.75).
5. **Vector Search**: Computes 1536-dim embedding (calling Voyage code-3 with deterministic 1536-dim hash fallback). Executes native PostgreSQL `pgvector` cosine distance query (`CodeChunk.embedding.cosine_distance(vec)`), falling back to in-memory cosine similarity if SQLite/mocked.
6. **Semantic / Concept Search**: Domain synonym matching against `analyzed_query.concept_keywords`.

### 1.4 Calling Modules & Integration Type
- **Calling Modules**: `ProjectContextEngine.investigate` (`apps/api/src/services/context_engine/engine.py`), `IntelligenceService.search_context` (`apps/api/src/services/intelligence_service.py`), direct pytest suites.
- **Integration Type**: Direct class invocation (`await MultiSignalRetriever.retrieve_candidates(...)`).

### 1.5 Database Interactions
- Queries `repository_snapshots`, `repository_files`, `code_symbols`, `code_dependencies`, and `code_chunks`.
- Uses SQLAlchemy `select`, `join`, `where`, `or_`, `limit`, and `pgvector` distance operators. Read-only.

### 1.6 Test Coverage
- `tests/test_context_engine.py`: Unit tests for lexical, vector, and symbol candidate generation.
- `tests/test_code_lane_postgres_pgvector.py`: Verifies native PostgreSQL `pgvector` cosine distance execution.
- `tests/test_code_atom_retrieval.py`: Verifies ATOM metadata extraction and candidate scoring.

### 1.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Default candidate limit per signal is fixed to 15. In-memory vector fallback evaluates all snapshot chunks sequentially if PostgreSQL connection fails.

---

## 2. MultiSignalRanker

### 2.1 Metadata
- **Component Name**: MultiSignalRanker
- **File Path**: `apps/api/src/services/context_engine/ranker.py`
- **Class / Functions**:
  - `class MultiSignalRanker`
  - `MultiSignalRanker.rank_candidates`
  - `MultiSignalRanker._deduplicate_candidates`
  - `RankedCandidate` (dataclass)

### 2.2 Tracks Using It
- **T1 (ATOM)**: Calls `resolve_temporal_supersession` (`apps.api.src.services.code_atom.temporal`) to mark superseded historical changes and compute latest active versions. Deduplicates chunks using ATOM `chunk:atom:{fingerprint}`.
- **T2 (EvoKG / EvoReasoner)**: Ranks graph expansion signals (`graph_expansion` 0.7, `graph_expansion_hop2` 0.5, transitive decay $0.5 \times 0.75^{h-2}$). Considers proof chain connectivity.
- **T3 (MemoTime)**: Ingests `memotime_temporal_match` (weight 1.5), `memotime_evolution_phase` (1.2), `memotime_diff_match` (1.4), `memotime_historical` (1.0), and `memotime_experience_relevance` (1.5). Applies severe penalties: `memotime_temporal_mismatch` ($0.3\times$) and `memotime_experience_contradiction` ($0.2\times$).
- **T4 (STAR-RAG)**: Ingests `star_rag_ppr` signal with highest primary weight: $1.6\times$.

### 2.3 Functionality Provided
- **Deduplication**: Merges overlapping candidates across 5 entity types (`FILE`, `CHUNK`, `SYMBOL`, `DEPENDENCY`, `RELATION_TARGET`), aggregating maximum signal values and preserving multi-hop provenance and alternative traversal paths.
- **Lifecycle & Intent Weighting**:
  - Current-state queries: Demotes deleted code ($0.15\times$), superseded changes ($0.4\times$), ended relations ($0.2\times$), and boosts latest active versions ($+0.4$).
  - Temporal queries: Amplifies historical changes ($+0.5$), commit evidence, and modification history.
- **Non-Test Demotion**: Automatically penalizes test, mock, and fixture files ($0.7\times$) unless the user query explicitly requests test code.
- **Threshold Pruning**: Prunes candidates with composite scores below `noise_threshold` (default 0.2).

### 2.4 Calling Modules & Integration Type
- **Calling Modules**: `ProjectContextEngine.investigate` (`apps/api/src/services/context_engine/engine.py`), `IntelligenceService`.
- **Integration Type**: Direct class invocation (`MultiSignalRanker.rank_candidates(...)`).

### 2.5 Database Interactions
- In-memory computation over `list[RetrievedCandidate]`. No direct SQL queries.

### 2.6 Test Coverage
- `tests/test_context_engine.py`: Tests signal weights, deduplication, and ranking order.
- `tests/test_code_lane_hardening.py`: Tests test-file demotion, keyword density, and noise filtering.
- `tests/test_code_atom_temporal.py`: Verifies temporal supersession and lifecycle adjustments.
- `tests/test_code_lane_star_rag.py`: Verifies `star_rag_ppr` rank amplification.

### 2.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Linear additive weighting scheme. Does not dynamically tune signal coefficients per repository characteristics.

---

## 3. RelationshipExpander

### 3.1 Metadata
- **Component Name**: RelationshipExpander
- **File Path**: `apps/api/src/services/context_engine/graph_expander.py`
- **Class / Functions**:
  - `class RelationshipExpander`
  - `RelationshipExpander.expand_candidates`
  - `RelationshipExpander._record_relationship_provenance`

### 3.2 Tracks Using It
- **T1 (ATOM)**: Reads `temporal_relations` stored in candidate metadata (generated by ATOM AST parsing) and constructs synthetic `RELATION_TARGET` candidates with full traversal paths (e.g. `file.py -> calls -> target_fn`) and validity markers (`is_ended_relation`).
- **T2 (EvoKG)**: Mirrors the graph topology used by EvoKG; provides candidate seed neighbors before EvoReasoner runs beam search.
- **T3 (MemoTime)**: Expands temporal relation candidates that MemoTime subsequent filters evaluate for Allen interval consistency.
- **T4 (STAR-RAG)**: Expanded candidates form the enriched graph node candidate set evaluated by STAR-RAG's temporal rule builder.

### 3.3 Functionality Provided
- Performs breadth-first search (BFS) graph expansion up to `max_depth` (default 2) starting from seed candidates.
- Expands across three core relational dimensions:
  1. **Direct Temporal Relations**: Expands grounded subject-relation-object triplets from ATOM metadata.
  2. **Code Dependencies**: Expands imported packages and modules to destination files within the snapshot.
  3. **Symbol Callers and Definitions**: Discovers callers and definition sites across files.
- Records multi-hop provenance: `relationship_hop` (0 for seeds, 1 for direct neighbors, 2 for transitive), `relationship_path` (e.g., `A.py -> imports -> B.py`), `connected_from`, and `alternative_paths`.

### 3.4 Calling Modules & Integration Type
- **Calling Modules**: `ProjectContextEngine.investigate`, `IntelligenceService.search_context`.
- **Integration Type**: Direct async invocation (`await RelationshipExpander.expand_candidates(...)`).

### 3.5 Database Interactions
- Executes queries on `repository_files`, `code_dependencies`, `code_symbols`, and `code_chunks` bounded by `snapshot_id`.

### 3.6 Test Coverage
- `tests/test_context_engine.py`: Verifies 1-hop and 2-hop BFS candidate expansion.
- `tests/test_code_atom_temporal_relations.py`: Verifies expansion of ATOM temporal relations and metadata preservation.

### 3.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Default expansion budget is capped at `max_expansions = 10` per seed to prevent combinatorial explosion.

---

## 4. ContextAssembler

### 4.1 Metadata
- **Component Name**: ContextAssembler
- **File Path**: `apps/api/src/services/context_engine/assembler.py`
- **Class / Functions**:
  - `class ContextAssembler`
  - `ContextAssembler.assemble_context`
  - `_json_safe`
  - `AssembledContext` (dataclass)

### 4.2 Tracks Using It
- **T1 (ATOM)**: Formats chunk provenance: commit SHA (shortened to 8 characters), author, commit timestamp, change type, lifecycle tag (`CURRENT`, `SUPERSEDED by sha`, `DELETED`), and grounded semantic facts (`BEHAVIOR`, `ARCHITECTURAL_DECISION`, `BREAKING_CHANGE`).
- **T2 (EvoKG / EvoReasoner)**: Allocates a dedicated context partition (bounded to $\le 25\%$ of total token budget, max 2500 characters) specifically for `GroundedProofChain`s. Formats traversed hops, directional indicators, validity intervals, conflict warnings, and uncertainty notes.
- **T3 (MemoTime)**: Formats Allen interval temporal relation tags (`[t_start -> t_end]`), temporal conflict markers, and experience memory attribution items.
- **T4 (STAR-RAG)**: Formats rule propagation scores and association evidence into candidate metadata headers.

### 4.3 Functionality Provided
- Enforces strict token budget management (`settings.CONTEXT_BUDGET_TOKENS`, default 4096 tokens $\approx 16,384$ characters).
- Builds a unified markdown prompt context structure:
  1. `### [PROOF CHAIN]` sections with step-by-step verified reasoning hops.
  2. `## Code Candidates` with commit headers, lifecycle status, relationship paths, and grounded atomic facts.
- Assembles structured `evidence_items` JSON dictionaries for API responses and client inspection.
- Collects `related_entities` set for graph visualization and navigation.

### 4.4 Calling Modules & Integration Type
- **Calling Modules**: `ProjectContextEngine.investigate`.
- **Integration Type**: Direct class invocation (`ContextAssembler.assemble_context(...)`).

### 4.5 Database Interactions
- None. Operates purely in-memory over ranked candidates and proof chains.

### 4.6 Test Coverage
- `tests/test_context_engine.py`: Verifies token budgeting and truncation.
- `tests/test_evoreasoner_proof_chains.py`: Verifies 25% proof-chain budget bounding and markdown formatting.
- `tests/test_code_lane_hardening.py`: Verifies evidence item JSON serialization.

### 4.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Token approximation uses a constant ratio of 4 characters per token rather than a BPE tokenizer.

---

## 5. ProjectContextEngine

### 5.1 Metadata
- **Component Name**: ProjectContextEngine
- **File Path**: `apps/api/src/services/context_engine/engine.py`
- **Class / Functions**:
  - `class ProjectContextEngine`
  - `ProjectContextEngine.investigate`
  - `GroundedAnswer` (dataclass)

### 5.2 Tracks Using It
- **Master Orchestrator**: Directly integrates and coordinates all four tracks:
  - Calls T1 embedding & candidate metadata extraction.
  - Calls T4 `StarRagContextService.run_star_rag_pipeline` (gated by `STAR_RAG_ENABLED`).
  - Calls T3 `MemoTimeExperienceStore` & `MemoTimeService.run_memotime_pipeline` (gated by `MEMOTIME_ENABLED`).
  - Calls T2 `EvoRoutePlanner`, `EvoBeamSearchEngine`, and `ProofChainAggregator` (gated by `EVOREASONER_ENABLED`).
  - Assembles unified context and triggers LLM generation with fallback synthesizer.
  - Performs T3 write-back on high-confidence verified outcomes.

### 5.3 Functionality Provided
- Implements the complete end-to-end 10-stage Code Lane Q&A pipeline:
  1. Query analysis and temporal intent extraction.
  2. Snapshot-to-repository scope resolution.
  3. Query embedding generation.
  4. Multi-signal retrieval across 6 channels.
  5. Multi-hop structural graph expansion.
  6. STAR-RAG temporal rule mining and PPR propagation.
  7. MemoTime temporal reasoning and experience memory injection.
  8. Multi-signal candidate ranking and supersession resolution.
  9. EvoReasoner multi-route planning, beam search, and proof-chain aggregation.
  10. Context assembly, customer knowledge integration, LLM answer synthesis, and experience write-back.
- Compiles comprehensive telemetry and diagnostics (`star_rag_diagnostics`, `memotime_diagnostics`, `evoreasoner_diagnostics`, `proof_chains`).

### 5.4 Calling Modules & Integration Type
- **Calling Modules**: `IntelligenceService.ask_question` (`apps/api/src/services/intelligence_service.py`), API route `POST /api/v1/intelligence/ask`, test suites.
- **Integration Type**: Core service dependency (`engine = ProjectContextEngine()`).

### 5.5 Database Interactions
- Manages SQLAlchemy `AsyncSession` across all sub-services. Executes queries on snapshots, chunks, triplets, and experiences. Writes back new verified `MemoTimeExperience` records.

### 5.6 Test Coverage
- `tests/test_context_engine.py`: Comprehensive test suite for full investigation pipeline.
- `tests/test_code_lane_e2e_scenarios.py`: End-to-end scenario verification.
- `tests/test_grounded_intelligence.py`: Grounding contract tests.

### 5.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Pipeline execution is currently sequential (retrieval $\to$ expand $\to$ STAR-RAG $\to$ MemoTime $\to$ rank $\to$ EvoReasoner) rather than parallelized across independent steps.

---

## 6. QueryAnalyzer & AnalyzedQuery

### 6.1 Metadata
- **Component Name**: QueryAnalyzer & AnalyzedQuery
- **File Path**: `apps/api/src/services/context_engine/query_analyzer.py`
- **Class / Functions**:
  - `class QueryAnalyzer`
  - `analyze_query`
  - `analyze_query_async`
  - `AnalyzedQuery` (dataclass)
  - `CONCEPT_SYNONYMS` (dictionary)
  - `TEMPORAL_MARKERS` (tuple)

### 6.2 Tracks Using It
- **T1 (ATOM)**: Provides keywords, symbols, and paths to drive chunk retrieval and commit matching.
- **T2 (EvoKG / EvoReasoner)**: Supplies seed symbols and entities to `EvoRoutePlanner`.
- **T3 (MemoTime)**: Calls `classify_temporal_intent` to populate `structured_temporal_intent` (`TemporalIntentType`, temporal anchors, directionality).
- **T4 (STAR-RAG)**: Supplies query terms for seed node identification in Personalized PageRank.

### 6.3 Functionality Provided
- Extracts file path candidates using regex matching common extensions (`.py`, `.ts`, `.js`, `.go`, `.rs`, `.java`, etc.).
- Extracts code symbol candidates using casing heuristics (`CamelCase`, `snake_case`, `SCREAMING_SNAKE`).
- Extracts general keywords, filtering out stop words.
- Maps domain keywords to concept synonyms (e.g. "auth" $\to$ "jwt", "token", "login", "password").
- Detects temporal markers ("history", "evolution", "changed", "commit", "previous", "was", "earlier", "deprecated", "removed", "before", "since", "why").
- Integrates T3 temporal classification (`classify_temporal_intent`).

### 6.4 Calling Modules & Integration Type
- **Calling Modules**: `ProjectContextEngine.investigate`, `RelationshipExpander`, `MultiSignalRetriever`, `MultiSignalRanker`.
- **Integration Type**: Direct function call (`await analyze_query_async(question)`).

### 6.5 Database Interactions
- None. Purely text parsing and heuristic classification.

### 6.6 Test Coverage
- `tests/test_context_engine.py`: Tests symbol, path, and keyword extraction.
- `tests/test_code_lane_memotime.py`: Verifies temporal intent classification.

### 6.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Keyword and symbol extraction relies on regex heuristics without full natural language dependency parsing.

---

## 7. FeatureSpecificationGenerator

### 7.1 Metadata
- **Component Name**: FeatureSpecificationGenerator
- **File Path**: `apps/api/src/services/context_engine/feature_spec_generator.py`
- **Class / Functions**:
  - `class FeatureSpecificationGenerator`
  - `FeatureSpecificationGenerator.generate_spec`
  - `FeatureSpecificationResult` (dataclass)

### 7.2 Tracks Using It
- Consumes grounded context assembled from **T1** (facts, diffs), **T2** (proof chains, architecture constraints), **T3** (historical evolutions), and **T4** (rule-propagated dependencies) to generate engineering feature specifications.

### 7.3 Functionality Provided
- Generates 6-section engineering specifications:
  1. Overview & Business Context.
  2. Architectural Grounding & Affected Components.
  3. Historical Precedents & Evolution Notes.
  4. Implementation Steps & Acceptance Criteria.
  5. Security & Risk Assessment.
  6. Verified Evidence Citations.
- Bounds specification generation with strict zero-hallucination guarantees using `GroundedAnswer` evidence.

### 7.4 Calling Modules & Integration Type
- **Calling Modules**: `IntelligenceService.generate_feature_spec`, API route `POST /api/v1/intelligence/feature-spec`.
- **Integration Type**: Service class invocation.

### 7.5 Database Interactions
- None directly; invokes `ProjectContextEngine.investigate`.

### 7.6 Test Coverage
- `tests/test_code_lane_feature_spec_contract.py`: 14 unit and integration tests.

### 7.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Dependent on LLM provider quality or deterministic template synthesizer.

---

## 8. Common Data Models & Schemas

### 8.1 Metadata
- **Component Names**: `CodeChunk`, `RepositoryFile`, `CodeSymbol`, `CodeDependency`, `RepositorySnapshot`, `Repository`
- **File Paths**:
  - `apps/api/src/models/chunk.py`
  - `apps/api/src/models/file.py`
  - `apps/api/src/models/symbol.py`
  - `apps/api/src/models/dependency.py`
  - `apps/api/src/models/snapshot.py`
  - `apps/api/src/models/repository.py`

### 8.2 Tracks Using Them
- **T1 (ATOM)**: Persists atomic code change chunks in `code_chunks` with columns `commit_sha`, `commit_message`, `fingerprint`, and JSONB `provenance`.
- **T2 (EvoKG)**: Triplet foreign keys link directly to `repository_snapshots.id`, `repository_files.id`, `code_symbols.id`, and `repositories.id`.
- **T3 (MemoTime)**: Experiences link to `repositories.id` and index `target_entities` corresponding to `code_symbols.name`.
- **T4 (STAR-RAG)**: Builds event graph across `code_chunks` and `code_symbols`.

### 8.3 Functionality Provided
- Foundational relational data model for all repository entities, code structure, AST symbols, dependencies, and vector embeddings in PostgreSQL 16.
- Provides `CompatibleVector` type in `apps/api/src/models/chunk.py` to allow seamless operation across native `pgvector` on PostgreSQL and JSON/Text on SQLite test environments.

### 8.4 Calling Modules & Integration Type
- **Calling Modules**: All models are imported across `ingestion_service.py`, `retriever.py`, `graph_expander.py`, `service.py`, `memotime.py`, and test fixtures.
- **Integration Type**: SQLAlchemy declarative ORM models.

### 8.5 Database Interactions
- Maps to PostgreSQL tables: `repositories`, `repository_snapshots`, `repository_files`, `code_symbols`, `code_dependencies`, `code_chunks`.

### 8.6 Test Coverage
- `tests/test_code_lane_postgres_pgvector.py`: Tests ORM mapping, vector similarity, and relational integrity.

### 8.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: None. Core ORM layer.

---

## 9. Common Ingestion Pipeline (`IngestionService`)

### 9.1 Metadata
- **Component Name**: IngestionService
- **File Path**: `apps/api/src/services/ingestion_service.py`
- **Class / Functions**:
  - `class IngestionService`
  - `IngestionService.run_ingestion`
  - `_clean_null`, `_clean_dict_null`

### 9.2 Tracks Using It
- **T1 (ATOM)**: Executes git diff extraction (`extract_git_commit_artifact`), AST-aware chunk decomposition (`CodeAtomDecomposer.decompose`), and maps atomic changes to `CodeChunk` records (`resolve_and_map_atomic_changes`).
- **T2 (EvoKG)**: Bridges T1 to T2. Extracts `decomp_result.relations` produced by ATOM AST parsing and invokes `EvoKGPersistenceService.persist_relations` to store triplets in PostgreSQL when `settings.EVOKG_ENABLED` is True.

### 9.3 Functionality Provided
- End-to-end repository ingestion pipeline:
  1. Fetches repository and snapshot metadata.
  2. Clones or accesses local git repository.
  3. Parses files using Tree-sitter (Python, TypeScript, JavaScript, Go).
  4. Extracts symbols and dependencies.
  5. Runs ATOM commit decomposition and chunk mapping.
  6. Ingests relations into EvoKG knowledge graph.
  7. Computes code vector embeddings and updates snapshot status.

### 9.4 Calling Modules & Integration Type
- **Calling Modules**: Background worker (`services/workers/worker.py`), API route `POST /api/v1/projects/{id}/ingest`, pytest suites.
- **Integration Type**: Background async task invocation.

### 9.5 Database Interactions
- Inserts/updates `repository_snapshots`, `repository_files`, `code_symbols`, `code_dependencies`, `code_chunks`, and `evokg_triplets`.

### 9.6 Test Coverage
- `tests/test_code_atom_chunk_integration.py`: Tests ATOM chunk generation during ingestion.
- `tests/test_evokg_ingestion.py`: Tests automatic EvoKG triplet persistence during ingestion.

### 9.7 Limitations & Status
- **Status**: Implemented and active.
- **Limitations**: Ingestion is long-running and requires background worker for large repositories.

---

## 10. Common Intelligence API & Service (`IntelligenceService`)

### 10.1 Metadata
- **Component Names**: `IntelligenceService`, Intelligence API Routes
- **File Paths**:
  - `apps/api/src/services/intelligence_service.py`
  - `apps/api/src/api/routes/intelligence.py`
  - `apps/api/src/schemas/intelligence.py`
- **Class / Functions**:
  - `class IntelligenceService`
  - `IntelligenceService.ask_question`
  - `IntelligenceService.search_context`
  - `IntelligenceService.generate_feature_spec`
  - `_build_evidence_item`
  - API endpoints: `POST /api/v1/intelligence/ask`, `POST /api/v1/intelligence/search`, `POST /api/v1/intelligence/feature-spec`

### 10.2 Tracks Using Them
- Exposes all four tracks to external consumers (desktop Flutter client and setup app):
  - Ingests user questions and maps them to `ProjectContextEngine`.
  - Serializes `GroundedAnswerResponse` with evidence items from T1, T2, T3, T4.
  - Returns `proof_chains` and track diagnostics in response payload.

### 10.3 Functionality Provided
- Enforces organization authorization and project access control (`_verify_project_access`).
- Manages conversation state and persistent chat history (`Conversation`, `Message`).
- Resolves latest active snapshot (`_get_active_snapshot`).
- Provides unified serialization for evidence items, lifecycle tags, proof chains, and retrieval scores.

### 10.4 Calling Modules & Integration Type
- **Calling Modules**: Flutter Desktop Client (`app/`), Server Setup Wizard (`setup_app/`), external REST callers.
- **Integration Type**: FastAPI HTTP router dependency.

### 10.5 Database Interactions
- Reads `projects`, `organization_memberships`, `repository_snapshots`. Writes `conversations` and `messages`.

### 10.6 Test Coverage
- `tests/api/test_intelligence.py`: API route integration tests.
- `tests/test_grounded_intelligence.py`: End-to-end service response validation.

### 10.7 Limitations & Status
- **Status**: Implemented and fully active.
- **Limitations**: Multi-tenant authorization is scoped to local organization memberships.

---

## 11. Repository and Branch Isolation Infrastructure

### 11.1 Metadata
- **Scope**: Multi-track data isolation.
- **Applied Locations**:
  - `apps/api/src/services/context_engine/retriever.py` (`snapshot_id`, `repository_id` filtering)
  - `apps/api/src/services/evokg/service.py` (`repository_id`, `branch` scoping on triplets)
  - `apps/api/src/services/evoreasoner/beam_search.py` (`repository_id`, `branch` in path traversal)
  - `apps/api/src/services/context_engine/memotime.py` (`repository_id`, `branch` on experience memory)
  - `apps/api/src/services/context_engine/star_rag.py` (candidate snapshot isolation)
  - `apps/api/src/models/evokg.py` (partial unique index `uq_evokg_active_exclusive` per repo/branch)

### 11.2 Tracks Using It
- All four tracks (T1, T2, T3, T4) strictly enforce repository and branch boundaries.

### 11.3 Functionality Provided
- Guarantees zero cross-repository or cross-branch data bleeding:
  1. `MultiSignalRetriever`: Validates that `snapshot_id` belongs to `repository_id`. Returns empty list if mismatch detected.
  2. `EvoKG`: All triplets require `repository_id` and `branch`. Contradiction detection and active status checks are strictly isolated to `(repository_id, branch)`.
  3. `EvoReasoner`: Beam search transitions only traverse triplets sharing the identical `(repository_id, branch)`.
  4. `MemoTime`: Experience memory retrieval and write-back filter strictly by `(repository_id, branch)`.

### 11.4 Database Interactions
- Compound database indexes on `(repository_id, branch)` in `evokg_triplets` and `memotime_experiences`.

### 11.5 Test Coverage
- `tests/test_evokg_persistence.py`: Verifies multi-repository and multi-branch triplet isolation.
- `tests/test_evoreasoner_beam_search.py`: Verifies beam search rejects cross-repo triplets.
- `tests/test_memotime_experience_memory.py`: Verifies branch-scoped experience retrieval.

### 11.6 Limitations & Status
- **Status**: Implemented and verified.
- **Limitations**: Cross-repository reasoning (e.g. multi-repo microservice tracing) is intentionally blocked by this isolation barrier.

---

## 12. Shared Database Infrastructure & Vector Storage

### 12.1 Metadata
- **Component Names**: Database Session, Async Engine, CompatibleVector, PostgreSQL 16 + pgvector
- **File Paths**:
  - `apps/api/src/db/session.py`
  - `apps/api/src/models/chunk.py`
  - `apps/api/src/config/settings.py`
- **Class / Functions**:
  - `get_db_session`
  - `AsyncSessionLocal`
  - `engine`
  - `CompatibleVector` (SQLAlchemy custom type)

### 12.2 Tracks Using It
- Shared foundation for all database operations across T1 (`code_chunks`), T2 (`evokg_triplets`), and T3 (`memotime_experiences`).

### 12.3 Functionality Provided
- Async connection pooling with `create_async_engine` and `async_sessionmaker`.
- NullPool support for isolated test executions (`APP_ENV=test`).
- `CompatibleVector`: Implements pgvector `Vector(1536)` on PostgreSQL with fallback to `JSON` or `Text` when running in SQLite unit test environments.

### 12.4 Database Interactions
- Manages PostgreSQL connection lifecycle, transactions, commits, and rollbacks.

### 12.5 Test Coverage
- `tests/test_code_lane_postgres_pgvector.py`: Verifies real PostgreSQL connection, pgvector extension, table creation, and vector index operations.

### 12.6 Limitations & Status
- **Status**: Implemented and active.
- **Limitations**: Requires PostgreSQL 16 with `pgvector` extension installed for production workloads.

---

## 13. Feature Flag & Settings Management

### 13.1 Metadata
- **Component Name**: Settings
- **File Path**: `apps/api/src/config/settings.py`
- **Class / Functions**:
  - `class Settings(BaseSettings)`
  - `settings = Settings()`

### 13.2 Tracks Using It
- Controls runtime enablement and behavior across all tracks:
  - `settings.STAR_RAG_ENABLED` (Controls T4 execution in `ProjectContextEngine`).
  - `settings.MEMOTIME_ENABLED` (Controls T3 execution in `ProjectContextEngine`).
  - `settings.EVOKG_ENABLED` (Controls T2 persistence in `IngestionService`).
  - `settings.EVOREASONER_ENABLED` (Controls T2 beam search in `ProjectContextEngine`).
  - `settings.EMBEDDING_PROVIDER` (Controls T1 vector provider: `"development"` vs `"voyage"`).
  - `settings.LLM_PROVIDER` (Controls synthesis provider: `"groq"`, `"anthropic"`, `"development"`).

### 13.3 Functionality Provided
- Centralized environment variable parsing and configuration management using Pydantic Settings.
- Allows independent toggling of tracks without code modification.
- Provides per-call parameter overrides in `ProjectContextEngine.investigate` (`enable_star_rag`, `enable_memotime`, `enable_evoreasoner`).

### 13.4 Calling Modules & Integration Type
- Imported across entire API codebase.

### 13.5 Test Coverage
- `tests/test_code_lane_feature_spec_contract.py`: Verifies settings defaults and flag handling.

### 13.6 Limitations & Status
- **Status**: Implemented and active.
- **Limitations**: Defaults for T2, T3, and T4 are `False` in baseline configuration, requiring explicit flag activation for full pipeline execution.

---

## Summary Matrix of Shared Components

| Shared Component | Primary File Path | Tracks Using It | Primary Functionality | Integration Type |
|---|---|---|---|---|
| **MultiSignalRetriever** | `apps/api/src/services/context_engine/retriever.py` | T1, T2, T3, T4 | 6-channel parallel candidate retrieval & ATOM metadata unpack | Direct class invocation |
| **MultiSignalRanker** | `apps/api/src/services/context_engine/ranker.py` | T1, T2, T3, T4 | Deduplication, supersession resolution, signal fusion, intent weighting | Direct class invocation |
| **RelationshipExpander** | `apps/api/src/services/context_engine/graph_expander.py` | T1, T2, T3, T4 | Multi-hop BFS graph expansion & ATOM temporal relation extraction | Direct async invocation |
| **ContextAssembler** | `apps/api/src/services/context_engine/assembler.py` | T1, T2, T3, T4 | Token budgeting (25% proof chains), markdown prompt formatting | Direct class invocation |
| **ProjectContextEngine** | `apps/api/src/services/context_engine/engine.py` | T1, T2, T3, T4 | Master pipeline orchestrator coordinating retrieval, reasoning & synthesis | Core service dependency |
| **QueryAnalyzer** | `apps/api/src/services/context_engine/query_analyzer.py` | T1, T2, T3, T4 | Symbol, path, keyword, concept extraction & MemoTime temporal intent | Direct async invocation |
| **FeatureSpecGenerator** | `apps/api/src/services/context_engine/feature_spec_generator.py` | T1, T2, T3, T4 | 6-section engineering specification generation grounded in evidence | Service class invocation |
| **Common Data Models** | `apps/api/src/models/*.py` | T1, T2, T3, T4 | PostgreSQL ORM models (`CodeChunk`, `RepositoryFile`, `CodeSymbol`, etc.) | Declarative ORM models |
| **IngestionService** | `apps/api/src/services/ingestion_service.py` | T1, T2 | End-to-end repository parsing, ATOM chunking, and EvoKG triplet bridging | Background async task |
| **IntelligenceService** | `apps/api/src/services/intelligence_service.py` | T1, T2, T3, T4 | Multi-tenant auth, session handling, REST API endpoints | FastAPI service class |
| **Isolation Infrastructure** | Cross-cutting across all services & models | T1, T2, T3, T4 | Strict `(repository_id, branch)` scoping across retrieval, reasoning & storage | Relational FKs & query filters |
| **Shared Database & Vector** | `apps/api/src/db/session.py`, `chunk.py` | T1, T2, T3 | PostgreSQL 16 connection pooling, async sessions & pgvector extension | SQLAlchemy engine & sessionmaker |
| **Settings / Feature Flags** | `apps/api/src/config/settings.py` | T1, T2, T3, T4 | Runtime configuration and track-level enablement toggles | Pydantic BaseSettings |
