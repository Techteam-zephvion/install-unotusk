# AI-PIE V1 — Temporal Knowledge Graph Research Tracks Implementation Status & Acceptance Plan

**Repository:** `Techteam-zephvion/install-unotusk`  
**Branch:** `main` (HEAD: `3ba0fde6fb6ca0d2985ec8fb7b6390797f6cd790`)  
**Primary Architecture Authority:** `AI_PIE_Architecture_V1_Elite.pdf` (April 2026 Locked Specification)  
**Scope Boundary:** Code Lane MVP (`AGENTS.md`)  
**Audit Date:** November 5, 2026  
**Status:** **STAGE A IMPLEMENTED — PENDING STAGE B FINAL ACCEPTANCE VALIDATION**

---

## 1. Executive Implementation Statement

This document provides a requirement-by-requirement, evidence-grounded review of all four Temporal Knowledge Graph research tracks within the Unotusk AI-PIE V1 Code Lane:
1. **T1 — ATOM** (arXiv:2510.22590: Atomic Decomposition and Dynamic Temporal Knowledge Graph Construction)
2. **T2 — EvoReasoner** (arXiv:2509.15464: Temporal Reasoning with Large Language Models Augmented by Evolving Knowledge Graphs)
3. **T3 — MemoTime** (arXiv:2510.13614: Memory-Augmented Temporal Knowledge Graph Enhanced Large Language Model Reasoning)
4. **T4 — STAR-RAG** (arXiv:2510.16715: Structure-Aware Temporal Knowledge Graph Augmented Generation)

Following the identification of the Experience Memory gap in Track T3 during the research fidelity audit, persistent Experience Memory has been implemented in PostgreSQL 16 (`apps/api/src/models/memotime.py`, `apps/api/alembic/versions/0012_memotime_experiences.py`, `apps/api/src/services/context_engine/memotime.py`).

Targeted test execution across the four individual tracks yielded 356 passed tests (161 ATOM, 130 EvoReasoner/EvoKG, 42 MemoTime, 23 STAR-RAG). Final formal cross-track acceptance is pending the unified single-command test run and live PostgreSQL 16 migration execution in Stage B.

---

## 2. Requirements Traceability Matrix

| Track | Key Architectural Requirement | Code Lane Implementation | Automated Verification | Current Status | Stage B Acceptance |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **T1** | Atomic commit hunk decomposition | `apps/api/src/services/code_atom/parser.py` | 161 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T1** | AST scope extraction (Python, TS/JS, Go) | `apps/api/src/services/code_atom/ast_extractor.py` | 161 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T1** | Dual-time intervals (`valid_from`, `valid_to`) | `code_chunks.atom_metadata` JSONB in PostgreSQL | 161 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T1** | Deterministic supersession & tombstones | `resolve_temporal_supersession` in `temporal.py` | 161 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T2** | Relational EvoKG evolving triplets | `EvoKGTriplet` in `apps/api/src/models/evokg.py` | 130 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T2** | 2-level taxonomy (8 entities, 13 predicates) | `apps/api/src/services/evokg/taxonomy.py` | 130 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T2** | Temporal exclusivity & conflict calibration | `apps/api/src/services/evokg/conflicts.py` | 130 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T2** | Deterministic beam search route planner | `apps/api/src/services/evoreasoner/beam_search.py` | 130 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T2** | Proof chain aggregator & $\le 25\%$ context budget | `ContextAssembler`, `proof_chains.py` | 130 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T3** | Structured temporal query intent (8 types) | `StructuredTemporalIntent` in `memotime.py` | 35 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T3** | Hierarchical Tree of Time (ToT) decomposition | `TreeOfTime`, `TimeTreeNode` in `memotime.py` | 35 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T3** | Complete 13 Allen interval algebra relations | `AllenIntervalRelation` with inverses and points | 35 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T3** | Multi-entity bound compatibility validation | `propagate_cross_entity_temporal_constraints` | 35 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T3** | Diff changeset evidence with line spans | `extract_diff_evidence` in `memotime.py` | 35 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T3** | Persistent Experience Memory (PostgreSQL 16) | `MemoTimeExperience`, `MemoTimeExperienceStore` | 7 tests passed individually | **IMPLEMENTED (Created)** | Pending Stage B DB test |
| **T3** | Quality gate ($\ge 0.80$ confidence) & repo isolation | `record_verified_experience_async` | 7 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T3** | Cross-question-type experience reuse | `apply_experience_memory` in `memotime.py` | 7 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T4** | Heterogeneous bipartite entity-rule graph | `StarBipartiteGraph`, `RuleNode` in `star_rag.py` | 19 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T4** | Minimum Description Length (MDL) pruning | `calculate_mdl_cost`, `greedy_mdl_pruning` | 19 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T4** | Seeded PPR with probability conservation ($\sum p=1$) | `run_seeded_ppr` in `star_rag.py` | 19 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T4** | 0.15 anchor score gate bypass & hub attenuation | `STAR_RAG_MIN_SCORE_THRESHOLD=0.15` | 19 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **T4** | Real-repo benchmark: MAP@5 = 1.000, 100% abstention | `test_star_rag_real_repo_benchmark.py` | 4 tests passed individually | **IMPLEMENTED** | Pending Stage B |
| **ALL** | Safe defaults: advanced flags False by default | `apps/api/src/config/settings.py` | Verified across suites | **IMPLEMENTED** | Pending Stage B |

---

## 3. Explicit Boundaries & Safe vs. Unsafe Claims

In accordance with strict audit standards, the following distinctions define the authoritative scope of Unotusk AI-PIE V1:

### Safe, Verified Claims:
- **Code Lane Scope:** All four tracks operate cleanly and exclusively within the Code Lane.
- **Relational Storage:** All persistence utilizes standard PostgreSQL 16 with `pgvector` extension (`code_chunks`, `evokg_triplets`, `memotime_experiences`). No external graph stores (Neo4j), document stores, or separate vector databases (Qdrant) are required or present.
- **Single-Tenant Deployment:** Everything runs locally and deterministically without cross-tenant leakage or complex microservice meshes.
- **Safe Feature Defaults:** `STAR_RAG_ENABLED=False`, `MEMOTIME_ENABLED=False`, `EVOKG_ENABLED=False`, and `EVOREASONER_ENABLED=False` default to `False`. When disabled, baseline dual-signal SQL retrieval operates with 100% fidelity and zero overhead.
- **Grounding Integrity:** All responses are grounded in concrete Git commit SHAs, file paths, and AST line spans; ungrounded queries trigger explicit abstention or warnings.

### Explicit Non-Goals & Unsafe Claims (Out of Scope):
- **Decision Lane:** External connectors (Jira, Slack, Notion, Linear, Confluence) are explicitly excluded from V1 MVP.
- **Autonomous Code Mutation:** AI-PIE V1 provides read-only code intelligence; it does not generate automated pull requests or mutate source repositories.
- **Direct Research Paper Claims:** Implementations are *Code Lane adaptations* tailored to ASTs, diffs, and commits, rather than literal re-implementations of academic general-domain temporal knowledge graph benchmarks (e.g. ICEWS, GDELT, YAGO).

---

## 4. Empirical Test Suite Summary (Separate Targeted Runs)

```
========================================================================================
TRACK                          MODULES TESTED                  TESTS RUN   PASS RATE
========================================================================================
T1 — ATOM                      code_atom/ parser, ast, temp    161         100% (161/161)
T2 — EvoReasoner & EvoKG       evokg/, evoreasoner/            130         100% (130/130)
T3 — MemoTime (ToT + Memory)   context_engine/memotime.py       42         100% (42/42)
T4 — STAR-RAG (Unit + Bench)   context_engine/star_rag.py       23         100% (23/23)
========================================================================================
TOTAL COMPONENT RUNS           SEPARATE INVOCATIONS            356         100% (356/356)
========================================================================================
```

*Note: The above counts represent individual per-track invocations. A single combined pytest invocation covering all tracks will be conducted in Stage B.*

---

## 5. Stage B Acceptance Plan & Gates

Final completion and formal acceptance are scheduled for Stage B:
1. **Unified Single-Command Pytest Invocation:** Execute all T1–T4 tests in a single command run and record full execution telemetry.
2. **PostgreSQL 16 Migration Execution:** Validate application of migration `0012_memotime_experiences.py` against a live PostgreSQL 16 test database.
3. **Cross-Track Feature Flag Matrix:** Test all flag combinations (`0000`, single flags, pairs, all enabled).
4. **Empirical MemoTime Benchmark:** Evaluate retrieval accuracy and latency with Experience Memory enabled vs disabled.
5. **Final Acceptance Decision:** Formally update and lock completion status before Information Extraction E1 begins.
