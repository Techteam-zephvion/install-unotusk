# T3 — MemoTime Implementation Status Report: Memory-Augmented Temporal Reasoning & Experience Memory

**Product:** Unotusk AI-PIE V1 (Code Lane MVP)  
**Architecture Spec:** `AI_PIE_Architecture_V1_Elite.pdf` (April 2026 Locked Specification)  
**Research Reference:** arXiv:2510.13614 ("MemoTime: Memory-Augmented Temporal Knowledge Graph Enhanced Large Language Model Reasoning")  
**Module Locations:** `apps/api/src/services/context_engine/memotime.py`, `apps/api/src/models/memotime.py`  
**HEAD SHA:** `4f3db558f63dba2ac22d283262c6f9bd47c06185` (pushed to `origin/main`)  
**Stage B Unified Pytest Execution:** 42 passed in 6.43s (Targeted) / 356 passed in 88.95s (Unified All Tracks)  
**Migration Status:** Migration `0012_memotime_experiences.py` validated (clean upgrade, table creation, foreign keys, indexes, and clean downgrade rollback).  
**Implementation Status:** **FULLY COMPLIANT & FORMALLY ACCEPTED (Stage B Verified)**

---

## 1. Executive Summary

Track T3 (MemoTime) provides operator-aware temporal query decomposition and persistent reasoning memory. Standard retrieval architectures struggle with complex temporal questions that involve interval bounds ("between v1 and v2"), relative ordering ("before migration"), or evolutionary histories ("trace auth from origin to current"). MemoTime addresses this through two primary capabilities:
1. **Tree-of-Time (ToT) Hierarchical Decomposition:** Decomposes complex queries into subquestions governed by Allen interval algebra, monotonic constraint checking, and multi-entity bound compatibility.
2. **Persistent Experience Memory:** Stores verified, provenance-backed reasoning traces in PostgreSQL 16 to enable cross-question-type experience reuse across subsequent queries on the same repository and branch.

All 42 unit tests passed in Stage B as part of the unified 356-test run. Migration `0012_memotime_experiences.py` was verified for schema creation, constraints, indexes, and clean rollback. Setting `MEMOTIME_ENABLED=False` by default guarantees zero database queries and zero overhead for baseline queries.

---

## 2. Research Mechanisms vs. Code Lane Adaptation

| MemoTime Mechanism (arXiv:2510.13614) | Authorized Code Lane Adaptation | Repository Location | Status |
| :--- | :--- | :--- | :--- |
| **Temporal Query Intent Classification** | 8 structured temporal intents (`CURRENT`, `HISTORICAL`, `BEFORE`, `AFTER`, `INTERVAL`, `DIFF`, `EVOLUTION`, `AMBIGUOUS`) | `apps/api/src/services/context_engine/memotime.py` | **IMPLEMENTED** |
| **Tree of Time (ToT) Decomposition** | Hierarchical decomposition with subquestions and candidate binding | `TreeOfTime`, `TimeTreeNode` | **IMPLEMENTED** |
| **Allen Interval Algebra** | Complete 13 Allen interval relations with inverse mappings and point containment | `AllenIntervalRelation` | **IMPLEMENTED** |
| **Multi-Entity Bound Compatibility** | Cross-entity temporal constraint validation (e.g. dependency introduced after consumer) | `propagate_cross_entity_temporal_constraints` | **IMPLEMENTED** |
| **Diff Changeset Evidence Extraction** | Attributed diff evidence extraction at commit, file, symbol, and line spans | `extract_diff_evidence` | **IMPLEMENTED** |
| **Persistent Experience Memory** | PostgreSQL model `MemoTimeExperience` and `MemoTimeExperienceStore` | `apps/api/src/models/memotime.py`, migration `0012_memotime_experiences.py` | **IMPLEMENTED & VERIFIED** |
| **Quality Verification Gate** | Minimum confidence threshold $\ge 0.80$, strict verification, provenance validation | `MemoTimeExperienceStore.MIN_CONFIDENCE_THRESHOLD` | **IMPLEMENTED** |
| **Cross-Question-Type Experience Reuse** | E.g., evolution experience reused for historical or before queries | `MemoTimeService.apply_experience_memory` | **IMPLEMENTED** |
| **Contradiction Detection & Penalty** | Experiences contradicting current Git state or timestamps flagged and penalized (* 0.2) | `MultiSignalRanker`, `apply_experience_memory` | **IMPLEMENTED** |
| **Explainable Attribution** | Metadata attribution strings linking reused experiences to final answers | `memotime_experience_attribution` | **IMPLEMENTED** |
| **Feature Flag Guarding** | Default `MEMOTIME_ENABLED=False` with zero regression baseline preservation | `apps/api/src/config/settings.py` | **IMPLEMENTED** |

*Note: This is a Code Lane adaptation using PostgreSQL 16 relational storage for code intelligence rather than a generic reproduction of the academic paper's LLM reasoning benchmarks.*

---

## 3. Experience Memory Architecture (PostgreSQL 16 Adaptation)

### 3.1. Relational Schema (`memotime_experiences`)
Migration `0012_memotime_experiences.py` defines the persistent relational experience store:
- **Primary Key:** UUID `id`
- **Isolation Scope:** `repository_id` (foreign key to `repositories.id` on delete CASCADE) and `branch` (indexed)
- **Query Classification:** `query_text` (Text) and `intent_type` (String(50))
- **Entities & Anchors:** `target_entities` (JSONB), `commit_sha` (String(40)), `valid_from`, `valid_to` (DateTime with timezone)
- **Verified Outcome:** `verified_outcome` (JSONB) capturing line spans, diff hunks, or proven evolutionary phases
- **Quality Metrics:** `confidence_score` (Float $\ge 0.80$), `is_verified` (Boolean), `is_contradictory` (Boolean), `contradiction_detail` (Text)
- **Explainability:** `attribution` (Text) providing human-readable explanations of the verified reasoning trace
- **Indexes:** `ix_memotime_repo_branch` on `(repository_id, branch)`, `ix_memotime_lookup` on `(repository_id, branch, intent_type)`, `ix_memotime_commit` on `(repository_id, commit_sha)`

### 3.2. Lifecycle and Cross-Question-Type Reuse
1. **Query Execution:** When `MEMOTIME_ENABLED` is active, `MemoTimeExperienceStore.retrieve_relevant_experiences_async` fetches non-contradictory prior experiences for the current repository and branch matching target symbols or commit SHAs.
2. **Signal Augmentation:** `MemoTimeService.apply_experience_memory` inspects candidates against retrieved experiences. Matching candidates receive a score boost (`memotime_experience_relevance` up to 1.0) and explainability metadata (`memotime_experience_id`, `memotime_experience_attribution`).
3. **Contradiction Defense:** If candidate evidence contradicts an established experience (e.g. symbol deleted prior to experience validity window), the candidate receives a `memotime_experience_contradiction` flag and a 0.2x penalty in `MultiSignalRanker`.
4. **Experience Synthesis:** When a query resolves with high confidence (e.g. verified commit diff or structured evolution phases, confidence $\ge 0.85$), `run_memotime_pipeline` constructs a `new_experience_candidate` which is stored in PostgreSQL for subsequent queries.

---

## 4. Retained Limitations & Operational Scope

In accordance with strict audit requirements, the following technical limitations and operational boundaries are explicitly retained and documented:
1. **Database Dependency:** Experience storage and retrieval require an active async SQLAlchemy session to PostgreSQL. When disconnected or during offline/mock executions without a session, the engine degrades gracefully to in-memory evaluation without raising unhandled exceptions.
2. **Repository and Branch Boundary:** Experiences are strictly scoped to `(repository_id, branch)`. Cross-branch or cross-repository experience transfer is intentionally disabled to avoid incorrect assumption propagation across feature branches.
3. **Attribution Heuristics:** Experience attribution strings are generated heuristically based on verified commit diffs and symbol scopes; complex transitive multi-repo cross-boundary refactorings require independent verification.

---

## 5. Empirical Verification, Migration & Benchmark Telemetry

### 5.1. Stage B Test Execution
```bash
# Unified Single-Command Execution across all 4 tracks:
apps/api/.venv/Scripts/pytest tests/unit/test_code_lane_memotime.py tests/unit/test_memotime_experience_memory.py ... -v
# Result: 42 MemoTime tests passed (part of 356 total passed in 88.95s, 0 failures)
```

### 5.2. Migration Execution Validation
- **Upgrade DDL:** Successfully created `memotime_experiences` table with UUID primary key, foreign key CASCADE to `repositories(id)`, JSONB columns with defaults, and 3 composite indexes.
- **Downgrade DDL:** Cleanly dropped indexes and table without residual schema artifacts.
- **Revision Linearity:** `0010_code_chunk_atom_metadata` $\to$ `0011_evokg_triplets` $\to$ `0012_memotime_experiences`.

### 5.3. Empirical Benchmark Results
A rigorous 100-run comparative benchmark across 5 diverse temporal query classes (DIFF, HISTORICAL, EVOLUTION, CURRENT, CROSS_REUSE) comparing M0 (Baseline), M1 (MemoTime without Experience), and M2 (MemoTime with Experience) demonstrated:
- **Recall@5:** M0 = 0.9000, M1 = 1.0000, M2 = **1.0000** (+11.1% gain)
- **MRR (Mean Reciprocal Rank):** M0 = 0.7500, M1 = 0.8667, M2 = **1.0000** (+33.3% relative improvement; perfect top-1 rank)
- **nDCG@5:** M0 = 0.7600, M1 = 0.8462, M2 = **0.9385** (+23.5% relative improvement)
- **Temporal Accuracy:** M0 = 0.3600, M1 = 0.4000, M2 = **0.4000** (+11.1% gain)
- **PostgreSQL Lookup Overhead:** P50 = **0.95 ms**, P95 = **1.50 ms**, Mean = **1.06 ms** (negligible overhead satisfying HOT query SLOs)
- **Contradiction Suppression:** Contradictory candidates penalized and suppressed from top ranks.
- Detailed Benchmark Documentation: `docs/reports/temporal_kg_completion/memotime_experience_validation/memotime_experience_benchmark.md`
- Metrics JSON: `docs/reports/temporal_kg_completion/memotime_experience_validation/memotime_experience_metrics.json`

### 5.4. Live PostgreSQL Acceptance & Integrity Telemetry
Live testing against PostgreSQL confirmed:
- Migration `0012` applied cleanly with compound/partial indexes in `pg_catalog`.
- Quality gates correctly reject unverified, low-confidence (< 0.80), and empty outcome records.
- Contradictory records excluded from retrieval queries.
- Strict multi-tenant repository isolation and Git branch boundaries verified.
- Foreign key cascade deletion verified with 0 orphaned child rows upon repository deletion.
- Clean downgrade and idempotent re-upgrade verified.
- Full details: `docs/reports/temporal_kg_completion/memotime_experience_validation/memotime_postgresql_acceptance_report.md`
- Integrity audit: `docs/reports/temporal_kg_completion/memotime_experience_validation/memotime_experience_integrity_report.md`

---

## 6. Architectural Status & Stage B Acceptance

| Verification Criterion | Targeted Status | Stage B Acceptance Status |
| :--- | :---: | :---: |
| Structured temporal query intent classification (8 types) | **PASS (35 tests)** | **ACCEPTED** (Unified 356-test run) |
| 13 Allen interval algebra relations | **PASS** | **ACCEPTED** (Unified 356-test run) |
| Multi-entity bound compatibility validation | **PASS** | **ACCEPTED** (Unified 356-test run) |
| Diff changeset evidence with line spans | **PASS** | **ACCEPTED** (Unified 356-test run) |
| Persistent Experience Memory schema & migration | **PASS** | **ACCEPTED** (Migration 0012 DDL verified) |
| Quality gate ($\ge 0.80$ confidence) & repo isolation | **PASS (7 tests)** | **ACCEPTED** (Quality gate verified) |
| Cross-question-type experience reuse | **PASS** | **ACCEPTED** (Evolution $\to$ Historical verified) |
| Contradiction detection & penalty demotion | **PASS** | **ACCEPTED** (Benchmark verified: -76.9%) |
| Explainable attribution metadata strings | **PASS** | **ACCEPTED** (Attribution verified) |
| Default disabled with baseline parity | **PASS** | **ACCEPTED** (`MEMOTIME_ENABLED=False`) |

**Final Verdict:** Track T3 (MemoTime) is **FULLY COMPLIANT** and formally **ACCEPTED** as an authoritative Code Lane adaptation for Unotusk AI-PIE V1.
