# Database and Configuration Inventory

## Executive Overview

This document provides a technical inventory of all database structures, Alembic migrations, PostgreSQL 16 / pgvector configurations, feature flags, and runtime dependencies implemented for Tracks T1–T4:
- **T1: ATOM** (CodeChunk metadata, fingerprinting, and commit provenance)
- **T2: EvoKG / EvoReasoner** (`evokg_triplets` evolutionary knowledge graph)
- **T3: MemoTime** (`memotime_experiences` verified reasoning storage)
- **T4: STAR-RAG** (In-memory temporal graph with database candidate grounding)

The database architecture is strictly single-tenant local PostgreSQL 16 with the `pgvector` extension enabled for 1536-dimensional semantic code search.

---

## 1. Database Migrations Inventory

The repository maintains an Alembic migration chain located at `apps/api/alembic/versions/`. Three specific migrations introduce and govern the T1–T4 relational and vector schema:

| Migration Revision ID | Down Revision | Creation Date | Impacted Table | Track | Description |
|---|---|---|---|---|---|
| `0010_code_chunk_atom_metadata` | `0009_service_ontology` | 2026-10-08 | `code_chunks` | T1 (ATOM) | Adds `commit_sha`, `commit_message`, `fingerprint`, and JSONB `provenance` columns with B-tree indexes. |
| `0011_evokg_triplets` | `0010_code_chunk_atom_metadata` | 2026-11-02 | `evokg_triplets` | T2 (EvoKG) | Creates `evokg_triplets` table, foreign keys, 8 temporal/relational indexes, and PostgreSQL partial unique index. |
| `0012_memotime_experiences` | `0011_evokg_triplets` | 2026-11-05 | `memotime_experiences` | T3 (MemoTime) | Creates `memotime_experiences` table, JSONB outcome storage, and compound repository/branch indexes. |

---

## 2. Table Specifications & Model Definitions

### 2.1 Table: `code_chunks` (T1 ATOM & Shared Vector Retrieval)
- **Model Definition**: `apps/api/src/models/chunk.py` (`class CodeChunk(Base, UUIDMixin)`)
- **Primary Migration**: `0001_initial_schema.py` & `0010_code_chunk_atom_metadata.py`
- **Purpose**: Stores semantic code chunks, AST definition boundaries, deterministic fingerprints, commit diff provenance, and 1536-dimensional vector embeddings.

#### Column Schema
| Column Name | Data Type | Nullable | Default | Foreign Key & Cascade | Description |
|---|---|---|---|---|---|
| `id` | `UUID` (CHAR(36) in SQLite) | No | `uuid.uuid4()` | Primary Key | Unique chunk identifier. |
| `snapshot_id` | `UUID` | No | — | `repository_snapshots.id` ON DELETE CASCADE | Associated snapshot. |
| `file_id` | `UUID` | No | — | `repository_files.id` ON DELETE CASCADE | Source repository file. |
| `symbol_id` | `UUID` | Yes | `None` | `code_symbols.id` ON DELETE CASCADE | Optional AST symbol mapping. |
| `chunk_type` | `VARCHAR(50)` | No | — | — | Type of chunk (e.g. `definition`, `block`, `diff`). |
| `name` | `VARCHAR(255)` | No | — | — | Chunk name or symbol identifier. |
| `path` | `VARCHAR(1000)` | No | — | — | Repository relative file path. |
| `content` | `TEXT` | No | — | — | Raw code chunk content or diff hunk. |
| `start_line` | `INTEGER` | No | — | — | 1-based start line number. |
| `end_line` | `INTEGER` | No | — | — | 1-based end line number. |
| `embedding` | `CompatibleVector` (`Vector(1536)`) | Yes | `None` | — | 1536-dim semantic code embedding. |
| `commit_sha` | `VARCHAR(40)` | Yes | `None` | — | Git commit SHA (T1 ATOM). |
| `commit_message` | `TEXT` | Yes | `None` | — | Commit message summary (T1 ATOM). |
| `fingerprint` | `VARCHAR(64)` | Yes | `None` | — | SHA-256 deterministic fingerprint (T1 ATOM). |
| `provenance` | `JSONB` (`JSON` in SQLite) | Yes | `None` | — | Structured JSON: author, facts, relations, diffs. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `utc_now` | — | Record creation timestamp. |

#### Database Indexes
1. `ix_code_chunks_snapshot_id`: B-tree on `[snapshot_id]`
2. `ix_code_chunks_file_id`: B-tree on `[file_id]`
3. `ix_code_chunks_symbol_id`: B-tree on `[symbol_id]`
4. `ix_code_chunks_name`: B-tree on `[name]`
5. `ix_code_chunks_path`: B-tree on `[path]`
6. `ix_code_chunks_commit_sha`: B-tree on `[commit_sha]` (introduced in `0010`)
7. `ix_code_chunks_fingerprint`: B-tree on `[fingerprint]` (introduced in `0010`)

---

### 2.2 Table: `evokg_triplets` (T2 EvoKG Temporal Knowledge Graph)
- **Model Definition**: `apps/api/src/models/evokg.py` (`class EvoKGTriplet(Base, UUIDMixin)`)
- **Primary Migration**: `0011_evokg_triplets.py`
- **Purpose**: Persists temporal knowledge graph relations (`subject`, `relation`, `object`), validity intervals (`[valid_from, valid_to]`), contradiction status, confidence metrics, and self-referential lineage links.

#### Column Schema
| Column Name | Data Type | Nullable | Default | Foreign Key & Cascade | Description |
|---|---|---|---|---|---|
| `id` | `UUID` (CHAR(36)) | No | `uuid.uuid4()` | Primary Key | Unique triplet identifier. |
| `repository_id` | `UUID` | No | — | `repositories.id` ON DELETE CASCADE | Scoped repository isolation key. |
| `snapshot_id` | `UUID` | Yes | `None` | `repository_snapshots.id` ON DELETE SET NULL | Snapshot where triplet was extracted. |
| `branch` | `VARCHAR(100)` | No | `'main'` | — | Git branch isolation key. |
| `subject_id` | `VARCHAR(500)` | No | — | — | Canonical subject entity identifier. |
| `relation` | `VARCHAR(100)` | No | — | — | Relation verb (e.g. `CALLS`, `INHERITS_FROM`). |
| `object_id` | `VARCHAR(500)` | No | — | — | Canonical object entity identifier. |
| `file_id` | `UUID` | Yes | `None` | `repository_files.id` ON DELETE SET NULL | Associated file entity. |
| `symbol_id` | `UUID` | Yes | `None` | `code_symbols.id` ON DELETE SET NULL | Associated symbol entity. |
| `is_exclusive` | `BOOLEAN` | No | `False` | — | True if relationship permits only 1 active target. |
| `scope_key` | `VARCHAR(255)` | No | `'default'` | — | Contextual partition for exclusivity. |
| `valid_from` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | Interval start ($t_{\text{start}}$ / commit date). |
| `valid_to` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | Interval end ($t_{\text{end}}$, NULL if active). |
| `observation_time` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | Timestamp when relationship was observed. |
| `commit_sha` | `VARCHAR(40)` | Yes | `None` | — | Originating Git commit SHA. |
| `superseded_by_id` | `UUID` | Yes | `None` | `evokg_triplets.id` ON DELETE SET NULL | Pointer to replacing triplet. |
| `supersedes_id` | `UUID` | Yes | `None` | `evokg_triplets.id` ON DELETE SET NULL | Pointer to prior triplet superseded. |
| `confidence_score` | `FLOAT` | No | `0.5` | — | Float in $[0.0, 1.0]$. |
| `confidence_level` | `VARCHAR(20)` | No | `'UNCERTAIN'` | — | `DEFINITIVE` or `UNCERTAIN`. |
| `is_uncertain` | `BOOLEAN` | No | `True` | — | Flag for probabilistic/unresolved evidence. |
| `has_temporal_conflict` | `BOOLEAN` | No | `False` | — | Flag indicating temporal or exclusivity conflict. |
| `conflict_detail` | `TEXT` | Yes | `None` | — | Human-readable conflict description. |
| `file_path` | `VARCHAR(1000)` | Yes | `None` | — | File path where relation occurs. |
| `symbol_name` | `VARCHAR(255)` | Yes | `None` | — | Associated AST symbol name. |
| `line_start` | `INTEGER` | Yes | `None` | — | Code start line. |
| `line_end` | `INTEGER` | Yes | `None` | — | Code end line. |
| `fingerprint` | `VARCHAR(64)` | No | — | — | Deterministic deduplication hash. |
| `provenance` | `JSONB` | No | `'{}'` | — | Ingestion and diff attribution metadata. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | — | Insertion timestamp. |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | — | Last update timestamp. |

#### Database Indexes
1. `ix_evokg_active_outgoing`: Compound B-tree on `[repository_id, branch, subject_id, relation]`
2. `ix_evokg_active_incoming`: Compound B-tree on `[repository_id, branch, object_id, relation]`
3. `ix_evokg_temporal_lookup`: Compound B-tree on `[repository_id, branch, subject_id, valid_from, valid_to]`
4. `ix_evokg_exclusive_conflict`: Compound B-tree on `[repository_id, branch, subject_id, relation, scope_key]`
5. `ix_evokg_snapshot`: Compound B-tree on `[repository_id, snapshot_id]`
6. `ix_evokg_commit`: Compound B-tree on `[repository_id, commit_sha]`
7. `ix_evokg_repo_fingerprint`: Compound B-tree on `[repository_id, fingerprint]`
8. `uq_evokg_active_exclusive`: **PostgreSQL Partial Unique Index** on `[repository_id, branch, subject_id, relation, scope_key]` WHERE `is_exclusive = true AND valid_to IS NULL AND is_uncertain = false AND has_temporal_conflict = false`. Enforces physical database-level consistency preventing duplicate active exclusive relationships.

---

### 2.3 Table: `memotime_experiences` (T3 MemoTime Experience Memory)
- **Model Definition**: `apps/api/src/models/memotime.py` (`class MemoTimeExperience(Base, UUIDMixin)`)
- **Primary Migration**: `0012_memotime_experiences.py`
- **Purpose**: Stores verified high-confidence reasoning traces, temporal intent query patterns, target entities, and verified outcomes for subsequent retrieval reuse.

#### Column Schema
| Column Name | Data Type | Nullable | Default | Foreign Key & Cascade | Description |
|---|---|---|---|---|---|
| `id` | `UUID` (CHAR(36)) | No | `uuid.uuid4()` | Primary Key | Unique experience record identifier. |
| `repository_id` | `UUID` | No | — | `repositories.id` ON DELETE CASCADE | Scoped repository isolation key. |
| `branch` | `VARCHAR(100)` | No | `'main'` | — | Branch isolation key. |
| `query_text` | `TEXT` | No | — | — | Original query or intent description. |
| `intent_type` | `VARCHAR(50)` | No | — | — | Temporal intent classification. |
| `target_entities` | `JSONB` | No | `'[]'` | — | List of target symbols/files involved. |
| `commit_sha` | `VARCHAR(40)` | Yes | `None` | — | Git commit SHA associated with outcome. |
| `valid_from` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | Valid time range start. |
| `valid_to` | `TIMESTAMP WITH TIME ZONE` | Yes | `None` | — | Valid time range end. |
| `verified_outcome` | `JSONB` | No | `'{}'` | — | Structured reasoning outcome and facts. |
| `confidence_score` | `FLOAT` | No | `0.85` | — | Confidence score ($[0.0, 1.0]$). |
| `is_verified` | `BOOLEAN` | No | `True` | — | Verified ground truth status. |
| `is_contradictory` | `BOOLEAN` | No | `False` | — | Contradiction flag against newer changes. |
| `contradiction_detail` | `TEXT` | Yes | `None` | — | Explanation if experience was invalidated. |
| `attribution` | `TEXT` | No | — | — | Model or algorithm that produced outcome. |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | — | Insertion timestamp. |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | No | `now()` | — | Update timestamp. |

#### Database Indexes
1. `ix_memotime_repo_branch`: Compound B-tree on `[repository_id, branch]`
2. `ix_memotime_lookup`: Compound B-tree on `[repository_id, branch, intent_type]`
3. `ix_memotime_commit`: Compound B-tree on `[repository_id, commit_sha]`

---

## 3. Configuration & Feature Flags Inventory

All runtime configuration and feature flags are managed via Pydantic BaseSettings in `apps/api/src/config/settings.py`.

### 3.1 Feature Flags & Toggles
| Environment Variable | Setting Attribute | Type | Default Value | Track | Functional Impact |
|---|---|---|---|---|---|
| `STAR_RAG_ENABLED` | `settings.STAR_RAG_ENABLED` | `bool` | `False` | T4 | Toggles STAR-RAG temporal rule mining and Seeded PPR candidate scoring in `ProjectContextEngine`. |
| `MEMOTIME_ENABLED` | `settings.MEMOTIME_ENABLED` | `bool` | `False` | T3 | Toggles MemoTime temporal operator evaluation and experience memory retrieval/write-back. |
| `EVOKG_ENABLED` | `settings.EVOKG_ENABLED` | `bool` | `False` | T2 | Toggles incremental triplet extraction and persistence into `evokg_triplets` during ingestion. |
| `EVOREASONER_ENABLED` | `settings.EVOREASONER_ENABLED` | `bool` | `False` | T2 | Toggles EvoReasoner multi-route planning, beam search, and proof-chain aggregation. |
| `STAR_RAG_HUB_ATTENUATION` | `settings.STAR_RAG_HUB_ATTENUATION` | `bool` | `True` | T4 | Enables degree penalization ($1/\sqrt{d_v}$) in Seeded PageRank to prevent utility hub dominance. |

### 3.2 Algorithmic & Retrieval Hyperparameters
| Environment Variable | Setting Attribute | Type | Default Value | Track | Description |
|---|---|---|---|---|---|
| `CONTEXT_BUDGET_TOKENS` | `settings.CONTEXT_BUDGET_TOKENS` | `int` | `3500` | Shared | Total token budget for context assembly ($\approx 14,000$ chars). |
| `STAR_RAG_TOP_K1` | `settings.STAR_RAG_TOP_K1` | `int` | `10` | T4 | Top candidates selected during primary retrieval stage. |
| `STAR_RAG_TOP_K2` | `settings.STAR_RAG_TOP_K2` | `int` | `5` | T4 | Top candidates retained after PPR reranking. |
| `STAR_RAG_PPR_ALPHA` | `settings.STAR_RAG_PPR_ALPHA` | `float` | `0.2` | T4 | Teleport probability ($\alpha$) in Personalized PageRank. |
| `STAR_RAG_PPR_EPSILON` | `settings.STAR_RAG_PPR_EPSILON` | `float` | `1e-6` | T4 | Convergence tolerance for power-iteration PPR. |
| `STAR_RAG_MIN_SUPPORT` | `settings.STAR_RAG_MIN_SUPPORT` | `int` | `2` | T4 | Minimum co-occurrence support for Apriori association rule mining. |
| `STAR_RAG_MIN_ANCHOR_SCORE` | `settings.STAR_RAG_MIN_ANCHOR_SCORE` | `float` | `1.0` | T4 | Anchor gate threshold (scaled to min(score, 0.40) on normalized candidates). |
| `MEMOTIME_MAX_PROPAGATION_HOPS` | `settings.MEMOTIME_MAX_PROPAGATION_HOPS` | `int` | `5` | T3 | Maximum hops permitted during Tree-of-Time interval propagation. |
| `EVOREASONER_MAX_CANDIDATES` | `settings.EVOREASONER_MAX_CANDIDATES` | `int` | `20` | T2 | Candidate pool size considered during route planning. |
| `EVOREASONER_MAX_SELECTED_ROUTES` | `settings.EVOREASONER_MAX_SELECTED_ROUTES` | `int` | `3` | T2 | Maximum non-overlapping reasoning routes selected per plan. |
| `EVOREASONER_MAX_ROUTE_HOPS` | `settings.EVOREASONER_MAX_ROUTE_HOPS` | `int` | `4` | T2 | Maximum search depth per beam-search route traversal. |

### 3.3 Provider Dependencies & Runtime Configurations
| Environment Variable | Setting Attribute | Type | Default Value | Supported Values | Functional Impact |
|---|---|---|---|---|---|
| `DATABASE_URL` | `settings.DATABASE_URL` | `str` | `postgresql+asyncpg://postgres:postgres@localhost:5432/unotusk` | PostgreSQL connection string | Async SQLAlchemy engine connection. |
| `REDIS_URL` | `settings.REDIS_URL` | `str` | `redis://localhost:6379/0` | Redis URI | Task queue broker for background ingestion and workers. |
| `LLM_PROVIDER` | `settings.LLM_PROVIDER` | `str` | `"groq"` | `"groq"`, `"claude"`, `"offline"` | Selects LLM synthesis provider for final answer generation. |
| `GROQ_API_KEY` | `settings.GROQ_API_KEY` | `str | None` | `None` | Valid Groq API Key | Required when `LLM_PROVIDER="groq"`. |
| `GROQ_MODEL` | `settings.GROQ_MODEL` | `str` | `"qwen/qwen3.8-27b"` | Any valid Groq model | Target model for Groq grounded generation. |
| `ANTHROPIC_API_KEY` | `settings.ANTHROPIC_API_KEY` | `str | None` | `None` | Valid Anthropic Key | Required when `LLM_PROVIDER="claude"`. |
| `ANTHROPIC_MODEL` | `settings.ANTHROPIC_MODEL` | `str` | `"claude-3-5-sonnet-20241022"` | Any valid Anthropic model | Target model for Anthropic Claude generation. |
| `EMBEDDING_PROVIDER` | `settings.EMBEDDING_PROVIDER` | `str` | `"development"` | `"development"`, `"voyage"` | Vector embedding engine for code chunks and query vectors. |
| `VOYAGE_API_KEY` | `settings.VOYAGE_API_KEY` | `str | None` | `None` | Valid Voyage AI Key | Required when `EMBEDDING_PROVIDER="voyage"`. |
| `VOYAGE_MODEL` | `settings.VOYAGE_MODEL` | `str` | `"voyage-code-2"` | `"voyage-code-2"`, `"voyage-code-3"` | Model used for Voyage AI code embeddings. |
| `EMBEDDING_DIMENSION` | `settings.EMBEDDING_DIMENSION` | `int` | `1536` | `1536` | Vector embedding dimensionality across all models. |

---

## 4. Architectural Invariants

1. **PostgreSQL 16 & pgvector Exclusivity**: The relational model relies on PostgreSQL 16 and native pgvector operators (`<=>` cosine distance). No external vector databases (such as Qdrant or Milvus) are permitted or utilized.
2. **Deterministic Fallbacks**: When external LLM or embedding providers are unconfigured (`EMBEDDING_PROVIDER="development"` or `LLM_PROVIDER="offline"`), deterministic 1536-dimensional token-hashing algorithms and offline synthesizers maintain full end-to-end pipeline functionality without external network calls.
3. **Immutability of Inactive Flags**: In accordance with project instructions, all default feature flags (`STAR_RAG_ENABLED=False`, `MEMOTIME_ENABLED=False`, `EVOKG_ENABLED=False`, `EVOREASONER_ENABLED=False`) remain unchanged in the codebase.
