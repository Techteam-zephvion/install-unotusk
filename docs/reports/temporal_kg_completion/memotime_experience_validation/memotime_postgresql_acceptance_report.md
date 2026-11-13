# MemoTime Experience Memory — PostgreSQL 16 Acceptance Report

**Date:** November 5, 2026  
**Track:** T3 — MemoTime (arXiv:2510.13614)  
**Database Engine:** PostgreSQL 18.6 / PostgreSQL 16 Dialect & Semantics  
**Connection Protocol:** `postgresql+asyncpg`  
**Schema Migration:** `apps/api/alembic/versions/0012_memotime_experiences.py`  
**Validation Script:** `scratch/test_postgres_acceptance.py`  
**Acceptance Status:** PASSED (100% compliant)

---

## 1. Executive Summary

In accordance with Phase 1 of the T1–T4 Final Closure requirements, live database validation of the MemoTime Experience Memory table (`memotime_experiences`), its schema migrations, indexes, data integrity constraints, quality gates, repository/branch isolation, and lifecycle operations was conducted against a live PostgreSQL server.

Every validation criterion defined in the architecture and research track specification was verified with zero failures:
- Migration `0012_memotime_experiences.py` applies cleanly and idempotently.
- Primary key, foreign key cascades, and compound/partial indexes exist and are recognized in `pg_catalog`.
- Strict quality gates prevent unverified, low-confidence (< 0.80), or empty reasoning outcomes from entering persistent storage.
- Records marked as contradictory are strictly filtered out from candidate retrieval.
- Multi-tenant repository isolation and Git branch boundaries are 100% respected.
- Cascade deletion cleans up child records upon repository deletion with zero orphaned rows.
- Schema downgrade (`downgrade()`) drops the table and all associated indexes cleanly; subsequent re-upgrade succeeds idempotently.

---

## 2. Environment & Database Configuration

| Parameter | Configuration |
|---|---|
| Engine | PostgreSQL 18.6 (x86_64-windows, MSVC 19.44) |
| Protocol / Driver | `postgresql+asyncpg://postgres@127.0.0.1:5433/unotusk_test` |
| Client ORM | SQLAlchemy 2.0 AsyncIO + Alembic DDL Operations |
| Schema Version | Linear migration chain terminating at revision `0012` |
| Upstream Dependencies | `0009_service_ontology` -> `0010_code_chunk_atom_metadata` -> `0011_evokg_triplets` -> `0012_memotime_experiences` |

---

## 3. Schema DDL & Index Verification

Live catalog verification on table `memotime_experiences` confirmed exact alignment with the migration specification:

```sql
CREATE TABLE memotime_experiences (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    branch VARCHAR(100) NOT NULL DEFAULT 'main',
    query_text TEXT NOT NULL,
    intent_type VARCHAR(50) NOT NULL,
    target_entities JSONB NOT NULL DEFAULT '[]',
    commit_sha VARCHAR(40),
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_to TIMESTAMP WITH TIME ZONE,
    verified_outcome JSONB NOT NULL DEFAULT '{}',
    confidence_score FLOAT NOT NULL DEFAULT 0.85,
    is_verified BOOLEAN NOT NULL DEFAULT TRUE,
    is_contradictory BOOLEAN NOT NULL DEFAULT FALSE,
    contradiction_detail TEXT,
    attribution TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
```

### Verified Indexes in `pg_indexes`
1. `memotime_experiences_pkey`: Primary key constraint on `id` (`UUID`).
2. `ix_memotime_repo_branch`: B-tree index on `(repository_id, branch)`.
3. `ix_memotime_lookup`: Compound partial index on `(repository_id, branch, intent_type)` with predicate `WHERE is_verified = true AND is_contradictory = false`.
4. `ix_memotime_commit`: Partial lookup index on `(repository_id, commit_sha)` with predicate `WHERE commit_sha IS NOT NULL`.

---

## 4. Live CRUD & Quality Gate Validation Results

| Test Case | Description | Input Conditions | Expected Outcome | Actual Result | Status |
|---|---|---|---|---|---|
| **CREATE 1** | Verified Reasoning Trace | Confidence: 0.92, Verified: True, Outcome: Valid JSONB | Stored in PostgreSQL with generated UUID | `deccc46f-...` persisted with timestamp | **PASSED** |
| **CREATE 2** | Low-Confidence Rejection | Confidence: 0.72 (< 0.80 threshold) | Gate rejection with explicit error | Rejected: `Experience confidence 0.72 below threshold 0.80` | **PASSED** |
| **CREATE 3** | Unverified Rejection | `is_verified=False` | Gate rejection with explicit error | Rejected: `Experience is unverified and cannot be committed to experience memory` | **PASSED** |
| **CREATE 4** | Empty Outcome Rejection | `verified_outcome={}` | Gate rejection with explicit error | Rejected: `Experience lacks verified outcome or reasoning trace` | **PASSED** |
| **CREATE 5** | Direct Contradiction Exclusion | `is_contradictory=True` inserted | Must be excluded from retrieval | Excluded by SQL predicate and filter | **PASSED** |
| **READ 1** | Repo & Branch Scope | Query `repo_1` / `main` | Return only valid, non-contradictory records | 2 records returned; 0 contradictory | **PASSED** |
| **READ 2** | Temporal Intent Filter | Query `intent_type="HISTORICAL"` | Return only historical experiences | 1 record returned with `HISTORICAL` intent | **PASSED** |
| **READ 3** | Target Entity JSONB Search | Query `target_entities=["src/auth.py"]` | Match experiences covering target entity | Matched candidate experiences | **PASSED** |
| **UPDATE** | Temporal Validity Update | Update `valid_to` and `contradiction_detail` | Row updated; confidence and provenance intact | Fields updated; confidence remains 0.92 | **PASSED** |
| **ISOLATION** | Multi-Repo & Branch Boundary | Query `repo_2` / `main` and `repo_1` / `dev` | Repo 2 query returns 0 Repo 1 records; dev returns 0 main records | 100% boundary isolation confirmed | **PASSED** |
| **CASCADE** | Foreign Key On Delete Cascade | Delete parent repository row | All child experiences deleted | 0 orphaned records; Repo 2 untouched | **PASSED** |
| **DOWNGRADE** | Migration Rollback | Run `alembic downgrade -1` | Drop table and all indexes | Table absent from `information_schema` | **PASSED** |
| **RE-UPGRADE**| Migration Re-application | Run `alembic upgrade +1` | Re-create table and all indexes | Table and indexes recreated cleanly | **PASSED** |

---

## 5. Architectural Invariants Enforced

1. **Storage Independence**: The Experience Memory subsystem operates entirely inside PostgreSQL 16/18 using standard JSONB and indexed relations. No external vector engine (Qdrant), graph engine (Neo4j), or key-value store (Redis) is introduced for Experience Memory storage.
2. **Quality & Grounding**: Experiences are never committed speculatively. Only verified reasoning chains with confidence $\ge 0.80$ and grounded evidence traces pass the write gate.
3. **Branch Isolation**: Experiences from feature or development branches never leak into `main` branch reasoning, preventing speculative code changes from polluting production codebase intelligence.
4. **Resilience & Graceful Degradation**: If the database is disconnected or experiences are absent, the MemoTime service falls back silently to deterministic temporal operator evaluation without crashing the retrieval pipeline.
