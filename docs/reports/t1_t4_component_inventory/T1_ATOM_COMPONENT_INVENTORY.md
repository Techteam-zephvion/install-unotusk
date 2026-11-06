# T1 — ATOM Technical Component Inventory

## 1. Overview and Architecture

Track 1 (**ATOM** — Atomic Code Fact Decomposition & Incremental Ingestion) provides repository-grounded, fine-grained change intelligence for Unotusk. It decomposes raw Git commits and unified diffs into atomic code change units (`AtomicCodeChange`), extracts deterministic semantic facts (`SemanticCodeFact`), isolates temporal relationships (`TemporalCodeRelation`), and maps them directly into the persistent relational and vector database (`CodeChunk` in PostgreSQL 16 with pgvector).

```
                        ┌───────────────────────────────┐
                        │   Git Repository (.git / ref) │
                        └───────────────┬───────────────┘
                                        │ git log / show / diff
                                        ▼
                        ┌───────────────────────────────┐
                        │ GitCommitArtifact & DiffParser│
                        └───────────────┬───────────────┘
                                        │ Unified diff hunks
                                        ▼
                        ┌───────────────────────────────┐
                        │      CodeAtomDecomposer       │
                        └───────┬───────────────┬───────┘
                                │               │
          ┌─────────────────────┴───┐       ┌───┴─────────────────────┐
          ▼                         ▼       ▼                         ▼
┌──────────────────┐ ┌────────────────────┐ ┌─────────────────┐ ┌───────────────────┐
│ AST & Symbol     │ │ SemanticFact       │ │ TemporalRelation│ │ Exclusivity &     │
│ Line Correlator  │ │ Extractor (Mod 1)  │ │ Extractor (Mod 2│ │ Taxonomy Engine   │
└─────────┬────────┘ └──────────┬─────────┘ └────────┬────────┘ └─────────┬─────────┘
          │                     │                    │                    │
          └─────────────────────┼────────────────────┼────────────────────┘
                                │                    │
                                ▼                    ▼
                        ┌─────────────────────────────────────┐
                        │ CodeEntityResolver & RelationResolver│
                        └──────────────────┬──────────────────┘
                                           │ Reconciled relations
                                           ▼
                        ┌─────────────────────────────────────┐
                        │  ChunkMapper & Vector Embedding     │
                        └──────────────────┬──────────────────┘
                                           │ CodeChunk (1536-dim vector, JSONB)
                                           ▼
                        ┌─────────────────────────────────────┐
                        │   PostgreSQL 16 code_chunks table   │
                        └─────────────────────────────────────┘
```

---

## 2. Component Inventory

### 2.1 Git Diff Parser & Hunk Segmenter
- **Component Name**: Unified Diff Parser
- **File Path**: `apps/api/src/services/code_atom/diff_parser.py`
- **Class and Function Names**:
  - `parse_unified_diff(raw_diff: str) -> list[GitFileDiff]`
  - `_clean_diff_path(path: str) -> str`
  - `_parse_single_file_block(lines: list[str]) -> GitFileDiff | None`
  - `HUNK_HEADER_REGEX = re.compile(r"^@@\s+-(?P<old_start>\d+)(?:,(?P<old_count>\d+))?\s+\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))?\s+@@(?:\s+(?P<heading>.*))?$")`
- **Responsibility**: Parses raw unified Git diff text into structured `GitFileDiff` and `GitDiffHunk` domain objects. Correctly detects file lifecycle states (`ADD`, `MODIFY`, `DELETE`, `RENAME`), strips standard Git `a/` and `b/` prefixes, parses standard unified hunk headers, and categorizes added (`+`), deleted (`-`), and context (` `) lines.
- **Input and Output**:
  - *Input*: `raw_diff: str` (raw multi-file unified git patch string).
  - *Output*: `list[GitFileDiff]` containing parsed `GitDiffHunk` items with line ranges and line arrays.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom` (`CodeChangeType`, `GitDiffHunk`, `GitFileDiff`).
- **External Dependencies**: Python standard library (`re`).
- **Database Interaction**: None (pure in-memory parsing).
- **Tests Covering It**:
  - `tests/unit/test_code_atom_decomposer.py` (`test_parse_unified_diff_multiple_files`, `test_diff_parser_renamed_file`, `test_diff_parser_deleted_file`)
  - `tests/unit/test_code_atom_e2e_pipeline.py`
- **Current Implementation Limitations**: Assumes standard Git unified diff formatting; custom diff formats without standard `diff --git` or `@@ ... @@` headers will fallback to single-block parsing.

---

### 2.2 Git Commit Extractor
- **Component Name**: Git Commit Artifact & History Extractor
- **File Path**: `apps/api/src/services/code_atom/git_extractor.py`
- **Class and Function Names**:
  - `class InvalidBaseCommitError(ValueError)`
  - `extract_git_commit_artifact(repo_dir: str, fallback_sha: str | None = None, commit_ref: str = "HEAD") -> GitCommitArtifact | None`
  - `extract_incremental_commit_artifacts(repo_dir: str, base_commit_sha: str | None = None, target_commit_sha: str = "HEAD", max_commits: int | None = None) -> list[GitCommitArtifact]`
  - `extract_diff_between_commits(repo_dir: str, base_commit_sha: str, target_commit_sha: str, file_path: str | None = None) -> str`
  - `extract_git_patch_lines(repo_dir: str, commit_sha: str, file_path: str) -> tuple[list[str], list[str], tuple[int, int] | None]`
- **Responsibility**: Interacts with the local Git worktree via `subprocess` execution. Extracts commit metadata (SHA, message, author, email, committed timestamp in ISO 8601) and generates complete patch diffs using `git show` or `git diff-tree --root`. For incremental ingestion, resolves commit ranges (`base..target`) in topological/chronological order (`git rev-list --reverse`), raising `InvalidBaseCommitError` if base commits are invalid.
- **Input and Output**:
  - *Input*: `repo_dir: str`, `base_commit_sha: str | None`, `target_commit_sha: str`, `max_commits: int | None`.
  - *Output*: `GitCommitArtifact` or `list[GitCommitArtifact]` with populated commit metadata, timestamp, and `raw_diff`.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom.GitCommitArtifact`.
- **External Dependencies**: `subprocess`, `os`, `re`, `logging`, Git CLI binary on PATH.
- **Database Interaction**: None directly; called by `IngestionService`.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_incremental.py` (`test_extract_incremental_commit_artifacts_range`, `test_invalid_base_commit_raises_error`)
  - `tests/unit/test_code_atom_e2e_pipeline.py`
- **Current Implementation Limitations**: Requires local disk access to a checked-out Git repository with `.git` directory or worktree. Does not support bare remote repository URLs directly without cloning.

---

### 2.3 Code Atom Decomposer
- **Component Name**: Code Atom Decomposer
- **File Path**: `apps/api/src/services/code_atom/decomposer.py`
- **Class and Function Names**:
  - `class CodeAtomDecomposer`
  - `CodeAtomDecomposer.__init__(self, fact_extractor: SemanticFactExtractor | None = None, relation_extractor: TemporalRelationExtractor | None = None)`
  - `CodeAtomDecomposer.decompose(self, commit: GitCommitArtifact, symbol_catalog: list[dict[str, Any]] | None = None, extract_facts: bool = True, extract_relations: bool = True, rename_history: dict[str, str] | None = None) -> CodeDecompositionResult`
  - `CodeAtomDecomposer.decompose_async(self, commit: GitCommitArtifact, symbol_catalog: list[dict[str, Any]] | None = None, extract_facts: bool = True, extract_relations: bool = True, use_llm: bool = True, rename_history: dict[str, str] | None = None) -> CodeDecompositionResult`
  - `CodeAtomDecomposer._resolve_symbol(...) -> tuple[uuid.UUID | None, str | None, str | None]`
  - `CodeAtomDecomposer._create_file_level_atomic_change(...) -> AtomicCodeChange`
- **Responsibility**: Core orchestrator of Track 1 decomposition. Breaks a `GitCommitArtifact` into granular `AtomicCodeChange` units per diff hunk or file change. Correlates each hunk with AST symbols from `symbol_catalog` by calculating line overlaps (preferring the innermost enclosing symbol scope), formats normalized change representations, generates deterministic SHA-256 fingerprints and IDs, invokes fact and relation extractors, and reconciles relationships under rename history.
- **Input and Output**:
  - *Input*: `GitCommitArtifact`, optional `symbol_catalog`, flags, `rename_history`.
  - *Output*: `CodeDecompositionResult` containing `changes: list[AtomicCodeChange]`, `facts: list[SemanticCodeFact]`, `relations: list[TemporalCodeRelation]`, and affected files/symbols.
- **Internal Dependencies**: `diff_parser.py`, `fact_decomposer.py`, `relation_extractor.py`, `relation_resolver.py`, `fingerprint.py`, `normalization.py`, `schemas/code_atom.py`.
- **External Dependencies**: `uuid`, `re`, `logging`.
- **Database Interaction**: None directly.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_decomposer.py` (17 tests)
  - `tests/unit/test_code_atom_scope_resolution.py` (8 tests)
  - `tests/unit/test_code_atom_e2e_pipeline.py` (9 tests)
- **Current Implementation Limitations**: When diff hunks span multiple adjacent top-level functions in a single hunk, AST resolution matches the innermost or highest-overlapping symbol rather than splitting the single unified hunk into multiple sub-hunks.

---

### 2.4 Semantic Fact Extractor (Module 1)
- **Component Name**: Semantic Fact Extractor
- **File Path**: `apps/api/src/services/code_atom/fact_decomposer.py`
- **Class and Function Names**:
  - `class SemanticFactExtractor`
  - `SemanticFactExtractor.__init__(self, llm_provider: LLMProvider | None = None)`
  - `SemanticFactExtractor.extract_facts_deterministic(self, change: AtomicCodeChange) -> list[SemanticCodeFact]`
  - `SemanticFactExtractor.extract_facts_async(self, change: AtomicCodeChange, use_llm: bool = True) -> list[SemanticCodeFact]`
  - `SemanticFactExtractor._extract_facts_llm(...) -> list[SemanticCodeFact]`
  - `generate_fact_fingerprint(...) -> str`
  - `generate_fact_id(fingerprint: str) -> str`
  - `deduplicate_facts(facts: list[SemanticCodeFact]) -> list[SemanticCodeFact]`
  - `validate_grounded_tokens(statement: str, raw_content: str, file_path: str, symbol_name: str | None) -> bool`
- **Responsibility**: Implements Module 1 (Atomic Fact Decomposition). Derives self-contained, grounded semantic facts from code changes across 8 fact types (`BEHAVIOR`, `VALIDATION`, `ERROR_HANDLING`, `STATE_CHANGE`, `RELATIONSHIP`, `REMOVAL`, `CONFIGURATION`, `STRUCTURAL`). Handles file deletions, renames, removed logic, guard clauses (`if ... return/raise`), cryptographic hashing, state mutations (`set_...`, `mark_dirty`), configuration entries (`.yaml`, `.json`), and unknown lines (marked `UNCERTAIN`). When LLM mode is active, enforces strict anti-hallucination token validation (`validate_grounded_tokens`) ensuring identifier tokens exist in the source diff.
- **Input and Output**:
  - *Input*: `AtomicCodeChange`, optional LLM provider.
  - *Output*: `list[SemanticCodeFact]` with confidence category (`HIGH`, `MEDIUM`, `UNCERTAIN`), evidenced lines, and deterministic fingerprint.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom`, `apps.api.src.services.llm.base`.
- **External Dependencies**: `hashlib`, `re`, `logging`, `os`.
- **Database Interaction**: None directly; facts are embedded in chunk provenance and stored in `code_chunks.provenance`.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_facts.py` (12 tests)
  - `tests/unit/test_code_atom_quality_eval.py` (7 tests)
  - `tests/unit/test_anti_hallucination.py` (11 tests)
- **Current Implementation Limitations**: Deterministic extraction relies on regex and lexical AST patterns for Python, JS/TS, and Go; complex macros in C/C++ or deeply nested closures in Lisp/Rust are captured under generic behavior statements marked `UNCERTAIN`.

---

### 2.5 Temporal Relation Extractor (Module 2)
- **Component Name**: Temporal Relation Extractor
- **File Path**: `apps/api/src/services/code_atom/relation_extractor.py`
- **Class and Function Names**:
  - `class TemporalRelationExtractor`
  - `TemporalRelationExtractor.__init__(self, llm_provider: LLMProvider | None = None)`
  - `TemporalRelationExtractor.extract_relations_from_facts(self, facts: list[SemanticCodeFact], change: AtomicCodeChange, commit_time: datetime | None = None) -> list[TemporalCodeRelation]`
  - `TemporalRelationExtractor.extract_relations_deterministic(self, change: AtomicCodeChange, commit_time: datetime | None = None) -> list[TemporalCodeRelation]`
  - `TemporalRelationExtractor.extract_relations_async(self, change: AtomicCodeChange, commit_time: datetime | None = None, use_llm: bool = True) -> list[TemporalCodeRelation]`
  - `TemporalRelationExtractor._extract_relations_llm(...) -> list[TemporalCodeRelation]`
  - `generate_relation_fingerprint(...) -> str`
  - `generate_relation_id(fingerprint: str) -> str`
  - `deduplicate_relations(relations: list[TemporalCodeRelation]) -> list[TemporalCodeRelation]`
  - `validate_grounded_relation_tokens(...) -> bool`
  - `normalize_relation_name(raw: str) -> RelationType`
  - `parse_iso_timestamp(ts_val: Any) -> datetime | None`
- **Responsibility**: Implements Module 2 (Temporal 5-Tuple Extraction). Extracts `(subject, relation, object, t_start, t_end)` tuples with observation timestamp `t_obs`. Enforces strict affirmative normalization (e.g. deleted code maps to affirmative `CALLS` or `DEFINES` with `t_end = commit_time`, never negative predicates like `stops_calling`). Preserves missing timestamps as `None` rather than inventing dates. Validates subject and object tokens against diff ground-truth.
- **Input and Output**:
  - *Input*: `SemanticCodeFact` list, `AtomicCodeChange`, observation timestamp `commit_time`.
  - *Output*: `list[TemporalCodeRelation]` with calibrated confidence score, exclusivity flag, scope key, and fingerprint.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom`, `apps.api.src.services.code_atom.taxonomy.CodeRelationTaxonomy`.
- **External Dependencies**: `hashlib`, `re`, `datetime`, `logging`.
- **Database Interaction**: None directly; results feed into `reconcile_code_relationships` and `EvoKGPersistenceService`.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_relationships.py` (11 tests)
  - `tests/unit/test_code_atom_temporal_relations.py` (12 tests)
  - `tests/unit/test_code_atom_quality_eval.py` (7 tests)
- **Current Implementation Limitations**: Unresolved symbols in third-party dynamic libraries or reflection calls default to `REFERENCES` or target `referenced_entity` with `UNCERTAIN` confidence.

---

### 2.6 Entity & Temporal Relation Resolver
- **Component Name**: Code Entity & Temporal Relation Resolver
- **File Path**: `apps/api/src/services/code_atom/relation_resolver.py`
- **Class and Function Names**:
  - `class CodeEntityResolver`
  - `CodeEntityResolver.build_qualified_identifier(name: str, file_path: str | None = None, rename_history: dict[str, str] | None = None) -> str`
  - `CodeEntityResolver.resolve_entity(name: str, file_path: str | None = None, rename_history: dict[str, str] | None = None) -> tuple[str, list[str]]`
  - `CodeEntityResolver.are_entities_equivalent(entity_a: str, entity_b: str, rename_history: dict[str, str] | None = None) -> bool`
  - `canonicalize_file_path(file_path: str | None, rename_history: dict[str, str] | None = None) -> str`
  - `class TemporalRelationResolver`
  - `TemporalRelationResolver.__init__(self, rename_history: dict[str, str] | None = None)`
  - `TemporalRelationResolver.reconcile_relations(self, relations: list[TemporalCodeRelation]) -> list[TemporalCodeRelation]`
  - `reconcile_code_relationships(relations: list[TemporalCodeRelation], rename_history: dict[str, str] | None = None) -> list[TemporalCodeRelation]`
  - `generate_reconciled_fingerprint(...) -> str`
- **Responsibility**: Guarantees stable entity identity across Git commits and verified file renames (`<canonical_path>::<symbol_name>`). Reconciles multiple relationship instances into coherent temporal representations: retains verified earliest `t_start` and latest `t_end`, preserves observation times `t_obs`, flags conflicting intervals (`t_end < t_start`) safely without data loss, aggregates provenance history, and prevents fuzzy entity conflation.
- **Input and Output**:
  - *Input*: `list[TemporalCodeRelation]`, optional `rename_history: dict[str, str]`.
  - *Output*: Reconciled, deduplicated, sorted `list[TemporalCodeRelation]` with canonical IDs and history lists.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom`, `apps.api.src.services.code_atom.relation_extractor`.
- **External Dependencies**: `hashlib`, `logging`, `datetime`.
- **Database Interaction**: None directly.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_relation_resolution.py` (11 tests)
  - `tests/unit/test_code_atom_relationships.py`
- **Current Implementation Limitations**: Resolves renames based on explicit Git rename tracking (`old_file_path -> new_file_path`); cross-file symbol moves without commit diff tracking remain distinct entities.

---

### 2.7 Temporal Supersession Engine
- **Component Name**: ATOM Temporal History & Supersession Engine
- **File Path**: `apps/api/src/services/code_atom/temporal.py`
- **Class and Function Names**:
  - `classify_temporal_intent(query_text: str) -> tuple[bool, str | None, list[str]]`
  - `parse_candidate_timestamp(cand: RetrievedCandidate) -> datetime | None`
  - `resolve_temporal_supersession(candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]`
  - `_get_candidate_target(cand: RetrievedCandidate) -> tuple[str, str | None, str | None]`
  - `_is_atom_candidate(cand: RetrievedCandidate) -> bool`
  - `TEMPORAL_KEYWORDS: set[str]`
  - `TEMPORAL_REGEX_PATTERNS: list[re.Pattern]`
- **Responsibility**: Manages candidate-level temporal lifecycle. Detects temporal query intent via `classify_temporal_intent` (leveraging MemoTime intent classification and fallback regex patterns). In `resolve_temporal_supersession`, groups candidates targeting the same file or symbol across rename chains, sorts chronologically, marks previous versions as superseded (`is_superseded=True`, `is_current=False`, `superseded_by_sha`), tags deletions (`is_deleted=True`), and ensures unrelated files do not supersede each other. Never invents timestamps.
- **Input and Output**:
  - *Input*: `candidates: list[RetrievedCandidate]`.
  - *Output*: In-place mutated and returned `list[RetrievedCandidate]` with annotated lifecycle metadata (`is_current`, `is_superseded`, `superseded_by_sha`, `superseded_by_date`, `is_deleted`, `renamed_from`, `renamed_to`).
- **Internal Dependencies**: `apps.api.src.services.context_engine.retriever.RetrievedCandidate`, `apps.api.src.services.context_engine.memotime.MemoTimeService`.
- **External Dependencies**: `re`, `datetime` (`UTC`).
- **Database Interaction**: Operates on `RetrievedCandidate` metadata loaded from `code_chunks`.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_temporal.py` (8 tests)
  - `tests/unit/test_code_atom_retrieval.py` (10 tests)
  - `tests/unit/test_historical_retrieval_hardening.py` (4 tests)
- **Current Implementation Limitations**: Candidates with completely missing timestamps (no commit date, no chunk creation date) are preserved as active without assumption rather than arbitrarily ordered.

---

### 2.8 CodeChunk Mapper
- **Component Name**: CodeChunk Entity Mapper
- **File Path**: `apps/api/src/services/code_atom/chunk_mapper.py`
- **Class and Function Names**:
  - `generate_deterministic_chunk_id(fingerprint: str) -> uuid.UUID`
  - `map_atomic_code_change_to_code_chunk(change: AtomicCodeChange, snapshot_id: uuid.UUID, file_id: uuid.UUID, symbol_id: uuid.UUID | None = None, compute_embedding: bool = True) -> CodeChunk`
  - `resolve_and_map_atomic_changes(...) -> list[CodeChunk]`
- **Responsibility**: Maps canonical `AtomicCodeChange` domain objects into the persistent `CodeChunk` SQLAlchemy model instances. Computes RFC 4122 v5 deterministic UUIDs (`uuid.uuid5(uuid.NAMESPACE_DNS, f"code-atom:{fingerprint}")`), links parent `snapshot_id`, `file_id`, and optional `symbol_id`, stores full provenance, atomic facts, and temporal relations in `JSONB`, and generates 1536-dimensional embeddings. Resolves renamed and deleted `RepositoryFile` entities without violating foreign key constraints.
- **Input and Output**:
  - *Input*: `changes: list[AtomicCodeChange]`, `snapshot_id: UUID`, `files_map: dict[str, RepositoryFile]`, `symbols_map`, optional session.
  - *Output*: `list[CodeChunk]` ready for database persistence or session addition.
- **Internal Dependencies**: `apps.api.src.models.chunk.CodeChunk`, `apps.api.src.models.file.RepositoryFile`, `apps.api.src.models.symbol.CodeSymbol`, `apps.api.src.schemas.code_atom.AtomicCodeChange`, `embedding.py`, `relation_resolver.py`.
- **External Dependencies**: `uuid`, `os`.
- **Database Interaction**: Creates and maps `CodeChunk` entities; adds missing `RepositoryFile` objects to `session`.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_chunk_integration.py` (16 tests)
  - `tests/unit/test_code_atom_incremental.py`
- **Current Implementation Limitations**: Batches assume unique fingerprints within a commit; duplicate identical hunks within the same commit are deduplicated to the first chunk instance.

---

### 2.9 Code Lane Embedding Engine
- **Component Name**: Code Lane Embedding Provider & Re-embedder
- **File Path**: `apps/api/src/services/code_atom/embedding.py`
- **Class and Function Names**:
  - `class CodeEmbeddingBackend(ABC)`
  - `class DevelopmentCodeEmbeddingBackend(CodeEmbeddingBackend)`
  - `class VoyageCodeEmbeddingBackend(CodeEmbeddingBackend)`
  - `get_code_embedding_backend() -> CodeEmbeddingBackend`
  - `generate_code_embedding(text: str, dim: int = 1536, input_type: str | None = None, backend: CodeEmbeddingBackend | None = None) -> list[float] | None`
  - `format_atom_code_embedding_input(commit_message: str | None, content: str, file_path: str, symbol_name: str | None = None) -> str`
  - `generate_atom_code_embedding(...) -> list[float] | None`
  - `embed_atomic_code_chunk(chunk: CodeChunk, ...) -> CodeChunk`
  - `reembed_atom_code_chunks(session: AsyncSession, snapshot_id: UUID | None = None, ...) -> int`
- **Responsibility**: Provides pluggable embedding generation for Code-Lane chunks. Supports two backends:
  1. `DevelopmentCodeEmbeddingBackend`: Deterministic, zero-hallucination offline synthesizer generating 1536-dimensional normalized vectors via token hashing.
  2. `VoyageCodeEmbeddingBackend`: Production Voyage AI client targeting `voyage-code-2`, validating 1536-dim vector return, retrying on transient errors, sanitizing API keys in logs, and rejecting non-finite/NaN outputs.
  Also provides `reembed_atom_code_chunks` for transactional background vector backfills.
- **Input and Output**:
  - *Input*: Text, commit message, content, file path, symbol name.
  - *Output*: `list[float]` of length 1536, or `None` on unrecoverable failure.
- **Internal Dependencies**: `apps.api.src.config.settings`, `apps.api.src.services.context_engine.retriever.generate_text_embedding`.
- **External Dependencies**: `httpx`, `math`, `logging`, `hashlib`, `uuid`.
- **Database Interaction**: `reembed_atom_code_chunks` queries and flushes `CodeChunk` embeddings via `AsyncSession`.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_embedding.py` (16 tests)
  - `tests/unit/test_voyage_provider_mocked.py` (24 tests)
  - `tests/integration/test_voyage_live.py` (4 tests)
- **Current Implementation Limitations**: In offline/development mode, vector distance reflects deterministic token overlap rather than deep semantic contextual embedding.

---

### 2.10 Normalization & Fingerprint Utilities
- **Component Name**: Deterministic Normalization and Fingerprinting
- **File Paths**:
  - `apps/api/src/services/code_atom/normalization.py`
  - `apps/api/src/services/code_atom/fingerprint.py`
- **Class and Function Names**:
  - `normalize_diff_line(line: str) -> str`
  - `normalize_code_change(...) -> str`
  - `generate_code_atom_fingerprint(...) -> str`
  - `generate_code_atom_id(fingerprint: str) -> str`
- **Responsibility**: Formats code diffs into stable, cross-platform canonical strings by stripping carriage returns and trailing whitespace while strictly preserving indentation, casing, and identifiers. Computes SHA-256 fingerprints across `(commit_sha, canonical_path, change_type, symbol_name, hunk_index, normalized_content)`.
- **Input and Output**:
  - *Input*: File path, change type, symbol, line arrays, ranges.
  - *Output*: Normalized string payload and 64-character SHA-256 hex digest string.
- **Internal Dependencies**: None.
- **External Dependencies**: `hashlib`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_decomposer.py`
  - `tests/unit/test_code_atom_chunk_integration.py`
- **Current Implementation Limitations**: Fingerprints include `commit_sha`; identical code changes committed under different commit SHAs receive distinct fingerprints by design to maintain commit provenance.

---

### 2.11 Relation Taxonomy & Exclusivity Engine
- **Component Name**: Code Relation Taxonomy
- **File Path**: `apps/api/src/services/code_atom/taxonomy.py`
- **Class and Function Names**:
  - `class RelationTaxonomyEntry`
  - `class CodeRelationTaxonomy`
  - `CodeRelationTaxonomy.normalize_predicate(relation: RelationType | str) -> RelationType | None`
  - `CodeRelationTaxonomy.classify(relation: RelationType | str) -> RelationTaxonomyEntry`
  - `CodeRelationTaxonomy.is_exclusive(relation: RelationType | str) -> bool`
  - `CodeRelationTaxonomy.get_canonical_predicate(relation: RelationType | str) -> RelationType`
  - `CodeRelationTaxonomy.generate_scope_key(...) -> tuple[str, bool]`
  - `CodeRelationTaxonomy.build_scope_key(...) -> str`
  - `CodeRelationTaxonomy.can_supersede(...) -> bool`
- **Responsibility**: Central authority defining relationship exclusivity, canonical predicate normalization, and scope key strategies:
  - Exclusive relations: `DEFINES` (`SYMBOL_NAME`), `DEFINES_RETURN_TYPE` (`OVERLOAD_INDEX`), `HAS_SIGNATURE` (`OVERLOAD_INDEX`), `ASSIGNED_TYPE` (`LEXICAL_SCOPE`), `MODULE_LOCATION` (`CANONICAL_PATH`), `INHERITS` (`INHERITANCE_SLOT`).
  - Non-exclusive relations: `CALLS`, `IMPORTS`, `REFERENCES`, `RAISES`, `MUTATES`, `CONFIGURES`, `VALIDATES`.
  - Normalizes over 40 relation string aliases (e.g., `EXTENDS_CLASS` -> `INHERITS`, `INVOKES` -> `CALLS`).
- **Input and Output**:
  - *Input*: `RelationType | str`, symbol names, scope parameters.
  - *Output*: Canonical `RelationTaxonomyEntry`, boolean exclusivity, or scope key string.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom` (`PropertyExclusivity`, `RelationType`, `ScopeKeyStrategy`, `TemporalSupersessionPolicy`).
- **External Dependencies**: Standard library (`dataclasses`).
- **Database Interaction**: None directly; used by EvoKG and ATOM modules.
- **Tests Covering It**:
  - `tests/unit/test_evokg_relation_taxonomy.py` (10 tests)
  - `tests/unit/test_code_atom_scope_resolution.py`
- **Current Implementation Limitations**: Unrecognized predicates default conservatively to non-exclusive `REFERENCES` with `UNCERTAIN` scope key to prevent destructive supersession.

---

### 2.12 Ingestion Service Integration
- **Component Name**: ATOM Ingestion Pipeline
- **File Path**: `apps/api/src/services/ingestion_service.py`
- **Class and Function Names**:
  - `IngestionService.ingest_commit_atom_changes(session: AsyncSession, snapshot_id: UUID, commit_artifact: GitCommitArtifact, ...) -> list[CodeChunk]`
  - `IngestionService.ingest_incremental_commits_atom(session: AsyncSession, snapshot_id: UUID, commit_artifacts: list[GitCommitArtifact], ...) -> list[CodeChunk]`
  - `IngestionService.run_incremental_atom_ingestion(snapshot_id: UUID, target_commit_sha: str = "HEAD", ...) -> list[CodeChunk]`
- **Responsibility**: Connects the ATOM decomposition pipeline to the repository ingestion workflow. During snapshot ingestion (Section 4.5 of `ingestion_service.py`), extracts commit artifacts, builds AST symbol catalogs, runs `CodeAtomDecomposer`, resolves chunks via `resolve_and_map_atomic_changes`, checks for existing fingerprints in `code_chunks` to avoid redundant re-embedding, and persists new chunks. For incremental updates, advances repository snapshot commit checkpoints.
- **Input and Output**:
  - *Input*: `AsyncSession`, `snapshot_id`, `GitCommitArtifact` or commit range.
  - *Output*: `list[CodeChunk]` persisted in PostgreSQL.
- **Internal Dependencies**: `apps.api.src.services.code_atom.*`, `apps.api.src.models.*`.
- **External Dependencies**: `sqlalchemy`, `logging`, `uuid`.
- **Database Interaction**: Inserts and selects from `code_chunks`, `repository_files`, `code_symbols`, and `repository_snapshots`.
- **Tests Covering It**:
  - `tests/unit/test_code_atom_chunk_integration.py` (16 tests)
  - `tests/unit/test_code_atom_incremental.py` (16 tests)
  - `tests/integration/test_code_lane_postgres_pgvector.py` (11 tests)
- **Current Implementation Limitations**: High commit volumes (e.g. 500+ commits) are processed sequentially in batches of 50 to prevent database connection timeouts.
