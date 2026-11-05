# T3 — MemoTime Implementation Status Report: Memory-Augmented Temporal Reasoning & Experience Memory

**Product:** Unotusk AI-PIE V1 (Code Lane MVP)  
**Architecture Spec:** `AI_PIE_Architecture_V1_Elite.pdf` (April 2026 Locked Specification)  
**Research Reference:** arXiv:2510.13614 ("MemoTime: Memory-Augmented Temporal Knowledge Graph Enhanced Large Language Model Reasoning")  
**Module Locations:** `apps/api/src/services/context_engine/memotime.py`, `apps/api/src/models/memotime.py`  
**Targeted Test Execution:** 
- `tests/unit/test_code_lane_memotime.py` (35 passed in 5.54s)
- `tests/unit/test_memotime_experience_memory.py` (7 passed in 1.36s)
- Total: 42 passed across targeted suites
**Migration Status:** Created `apps/api/alembic/versions/0012_memotime_experiences.py` (Alembic down_revision: `0011_evokg_triplets`). Live DB application pending Stage B.  
**Implementation Status:** **IMPLEMENTED & TARGETED TESTS PASSED** (Final cross-track acceptance pending Stage B)

---

## 1. Executive Summary

Track T3 (MemoTime) provides operator-aware temporal query decomposition and persistent reasoning memory. Standard retrieval architectures struggle with complex temporal questions that involve interval bounds ("between v1 and v2"), relative ordering ("before migration"), or evolutionary histories ("trace auth from origin to current"). MemoTime addresses this through two primary capabilities:
1. **Tree-of-Time (ToT) Hierarchical Decomposition:** Decomposes complex queries into subquestions governed by Allen interval algebra, monotonic constraint checking, and multi-entity bound compatibility.
2. **Persistent Experience Memory:** Stores verified, provenance-backed reasoning traces in PostgreSQL 16 to enable cross-question-type experience reuse across subsequent queries on the same repository and branch.

All 42 targeted unit tests passed across the two dedicated test suites. Setting `MEMOTIME_ENABLED=False` by default guarantees zero database queries and zero overhead for baseline queries.

---

## 2. Research Mechanisms vs. Code Lane Adaptation

| MemoTime Mechanism (arXiv:2510.13614) | Authorized Code Lane Adaptation | Repository Location | Status |
| :--- | :--- | :--- | :--- |
| **Temporal Query Intent Classification** | 8 structured temporal intents (`CURRENT`, `HISTORICAL`, `BEFORE`, `AFTER`, `INTERVAL`, `DIFF`, `EVOLUTION`, `AMBIGUOUS`) | `apps/api/src/services/context_engine/memotime.py` | **IMPLEMENTED** |
| **Tree of Time (ToT) Decomposition** | Hierarchical decomposition with subquestions and candidate binding | `TreeOfTime`, `TimeTreeNode` | **IMPLEMENTED** |
| **Allen Interval Algebra** | Complete 13 Allen interval relations with inverse mappings and point containment | `AllenIntervalRelation` | **IMPLEMENTED** |
| **Multi-Entity Bound Compatibility** | Cross-entity temporal constraint validation (e.g. dependency introduced after consumer) | `propagate_cross_entity_temporal_constraints` | **IMPLEMENTED** |
| **Diff Changeset Evidence Extraction** | Attributed diff evidence extraction at commit, file, symbol, and line spans | `extract_diff_evidence` | **IMPLEMENTED** |
| **Persistent Experience Memory** | PostgreSQL model `MemoTimeExperience` and `MemoTimeExperienceStore` | `apps/api/src/models/memotime.py`, migration `0012_memotime_experiences.py` | **IMPLEMENTED (Created)** |
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
4. **Live Migration Application Pending Stage B:** The schema migration `0012_memotime_experiences.py` has been created and verified for syntax and Alembic graph integrity; live execution against a PostgreSQL 16 test database is part of Stage B validation.

---

## 5. Empirical Verification & Test Evidence

### 5.1. Targeted Test Invocations
```bash
# 1. Tree-of-Time and Allen interval suite
apps/api/.venv/Scripts/pytest tests/unit/test_code_lane_memotime.py -q
# Result: 35 passed in 5.54s

# 2. Experience Memory dedicated suite
apps/api/.venv/Scripts/pytest tests/unit/test_memotime_experience_memory.py -v
# Result: 7 passed in 1.36s

# Combined pre-commit execution:
apps/api/.venv/Scripts/pytest tests/unit/test_code_lane_memotime.py tests/unit/test_memotime_experience_memory.py -q
# Result: 42 passed in 6.53s
```

---

## 6. Architectural Status

| Verification Criterion | Targeted Status | Stage B Acceptance Status |
| :--- | :---: | :---: |
| Structured temporal query intent classification (8 types) | **PASS (35 tests)** | Pending Stage B unified run |
| 13 Allen interval algebra relations | **PASS** | Pending Stage B unified run |
| Monotonic progression & contradiction safety gate | **PASS** | Pending Stage B unified run |
| Persistent Experience Memory model & migration created | **PASS (Created)** | Pending Stage B live DB test |
| Quality threshold gate (confidence $\ge 0.80$) | **PASS (7 tests)** | Pending Stage B unified run |
| Cross-question-type experience reuse | **PASS** | Pending Stage B unified run |
| Explainable attribution metadata | **PASS** | Pending Stage B unified run |
| Default disabled with baseline parity | **PASS** | `MEMOTIME_ENABLED=False` verified |

**Conclusion:** T3 (MemoTime) with Experience Memory is implemented and targeted unit tests pass. Final formal cross-track acceptance and live database migration validation will be established upon completion of Stage B.
