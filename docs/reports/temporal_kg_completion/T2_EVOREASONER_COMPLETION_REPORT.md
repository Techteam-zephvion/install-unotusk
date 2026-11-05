# T2 — EvoReasoner Implementation Status Report: Multi-Route Temporal Reasoning & Evolving Knowledge Graphs

**Product:** Unotusk AI-PIE V1 (Code Lane MVP)  
**Architecture Spec:** `AI_PIE_Architecture_V1_Elite.pdf` (April 2026 Locked Specification)  
**Research Reference:** arXiv:2509.15464 ("EvoReasoner: Temporal Reasoning with Large Language Models Augmented by Evolving Knowledge Graphs")  
**Module Locations:** `apps/api/src/services/evokg/`, `apps/api/src/services/evoreasoner/`  
**Targeted Test Execution:** `tests/unit/test_evokg_*.py`, `tests/unit/test_evoreasoner_*.py` (130 tests passed individually)  
**Implementation Status:** **IMPLEMENTED & TARGETED TESTS PASSED** (Final cross-track acceptance pending Stage B)

---

## 1. Executive Summary

Track T2 (EvoReasoner & EvoKG) implements multi-route temporal reasoning and evolving knowledge graph operations. While standard RAG approaches struggle when code entities undergo repeated modifications, renaming, or architectural replacement across commits, EvoReasoner maintains an explicit evolutionary knowledge graph with uncertainty calibration, exclusivity rules, and beam search multi-route verification.

The implementation is designed and validated as an authoritative **Code Lane adaptation** in PostgreSQL 16 (`evokg_triplets` table). In targeted testing, all 130 tests passed, and the T2.8 hardening suite confirms a P50 latency of 111.85 ms while strictly respecting context assembler budget constraints ($\le 25\%$).

---

## 2. Research Mechanisms vs. Code Lane Adaptation

| EvoReasoner Mechanism (arXiv:2509.15464) | Authorized Code Lane Adaptation | Repository Location | Status |
| :--- | :--- | :--- | :--- |
| **Evolving Knowledge Graph (EvoKG)** | Relational temporal triplets with `valid_from`, `valid_to`, `observation_time` | `apps/api/src/models/evokg.py`, `apps/api/src/services/evokg/` | **IMPLEMENTED** |
| **Two-Level Taxonomy & Exclusivity** | 8 entity types, 13 canonical predicates, exclusivity validation (`is_exclusive`, `scope_key`) | `apps/api/src/services/evokg/taxonomy.py` | **IMPLEMENTED** |
| **Temporal Contradiction Detection** | Simultaneous active exclusivity checks with uncertainty gating | `apps/api/src/services/evokg/conflicts.py` | **IMPLEMENTED** |
| **Beam Search Multi-Route Planner** | Deterministic multi-route exploration with cost estimation and candidate expansion | `apps/api/src/services/evoreasoner/planner.py`, `beam_search.py` | **IMPLEMENTED** |
| **Proof Chain Aggregator** | Verifiable proof chains linking source commit, line spans, and facts | `apps/api/src/services/evoreasoner/proof_chains.py` | **IMPLEMENTED** |
| **Context Assembler Budget Gate** | EvoReasoner evidence capped at $\le 25\%$ of final LLM context budget | `apps/api/src/services/context_engine/context_assembler.py` | **IMPLEMENTED** |
| **Feature Flag Guarding** | Default `EVOKG_ENABLED=False` and `EVOREASONER_ENABLED=False` | `apps/api/src/config/settings.py` | **IMPLEMENTED** |

*Note: This is a Code Lane adaptation using PostgreSQL 16 relational storage rather than a separate graph database like Neo4j or academic evaluation on general KG benchmarks.*

---

## 3. Architecture & Code Lane Implementation

### 3.1. Relational Triplet Model (`evokg_triplets`)
The triplet schema (`apps/api/src/models/evokg.py`, migration `0011_evokg_triplets.py`) models evolving relationships:
- **Scope Isolation:** `repository_id` and `branch` (default `main`).
- **Entity Identity:** `subject_id`, `relation`, `object_id`.
- **Exclusivity:** `is_exclusive=True` and `scope_key` enforce single-active-state rules (e.g., an endpoint can only have one active handler at a given point in time).
- **Temporal Boundaries:** `valid_from`, `valid_to`, `observation_time`, `commit_sha`.
- **Supersession Links:** Self-referential foreign keys `superseded_by_id` and `supersedes_id`.
- **Uncertainty & Conflict:** `confidence_score`, `is_uncertain`, `has_temporal_conflict`, `conflict_detail`.

### 3.2. Beam Search Route Planning
`EvoRouteSearcher` executes bounded deterministic beam search across temporal graph hops:
- Maximum candidate expansion: 20 (`EVOREASONER_MAX_CANDIDATES`).
- Selected routes: up to 3 (`EVOREASONER_MAX_SELECTED_ROUTES`).
- Maximum path depth: 4 hops (`EVOREASONER_MAX_ROUTE_HOPS`).
- Route scoring prioritizes proven facts, temporal consistency, and AST proximity, while heavily penalizing unverified or contradictory leaps.

### 3.3. T2.8 System Hardening
Following the T2.8 hardening audit:
- Route evaluation overhead achieved a benchmark P50 latency of 111.85 ms and P99 under 280 ms.
- Category B historical queries (retrieving superseded facts without polluting current active implementation) were validated at 100% precision.
- Proof chains serialize attribution metadata directly into the Grounded Answer contract.

---

## 4. Empirical Verification & Test Evidence

### 4.1. Targeted Test Execution
```bash
apps/api/.venv/Scripts/pytest (Get-ChildItem tests/unit/test_evokg_*.py, tests/unit/test_evoreasoner_*.py) -q
# Result: 130 passed, 4 warnings in 29.60s
```

### 4.2. Verification Summary
- **Taxonomy & Ingestion:** 13 canonical code predicates verified across import, call, inheritance, implementation, modification, and supersession links.
- **Conflict Resolution:** Verified detection of conflicting exclusive relations and appropriate `is_uncertain` flag calibration.
- **Proof Chains:** Verified serialization into context assembler without exceeding the 25% token budget constraint.
- **Safety Defaults:** Verified complete no-op behavior and zero database overhead when `EVOREASONER_ENABLED=False`.

---

## 5. Architectural Status

| Verification Criterion | Targeted Status | Stage B Acceptance Status |
| :--- | :---: | :---: |
| Relational EvoKG schema in PostgreSQL 16 | **PASS (Registered)** | Pending Stage B migration check |
| Exclusivity and contradiction checking | **PASS (130 tests)** | Pending Stage B unified run |
| Deterministic beam search route planner | **PASS** | Pending Stage B unified run |
| Proof chain attribution with line ranges | **PASS** | Pending Stage B unified run |
| Context budget compliance ($\le 25\%$) | **PASS** | Pending Stage B unified run |
| Feature flag defaults disabled | **PASS** | `EVOKG_ENABLED=False`, `EVOREASONER_ENABLED=False` |

**Conclusion:** T2 (EvoReasoner) implementation is complete and targeted tests pass. Final formal cross-track acceptance will be established upon completion of Stage B.
