# TEMPORAL & STRUCTURE-AWARE STAR-RAG ACTIVATION REPORT

**Authoritative System Engineering & Architecture Validation**  
**Repository:** `Techteam-zephvion/install-unotusk`  
**Date:** November 20, 2026  
**Status:** VALIDATED & FULLY PASSING  

---

## 1. Executive Summary & Production Readiness

This report documents the completed runtime integration, end-to-end activation, and comprehensive validation of the two independent Structure-Aware and Temporal STAR-RAG retrieval engines in the Unotusk MVP backend.

Both engines now operate under a unified, selective routing topology that rigorously guarantees:
1. **Authoritative Baseline Preservation:** ATOM MultiSignal retrieval remains the primary baseline for general and direct symbol/file lookups.
2. **Selective Intent-Based Routing:**
   - **Temporal STAR-RAG** (`STAR_RAG_ENABLED`) activates exclusively when queries express clear historical, evolutionary, or temporal reasoning intents (`BEFORE`, `AFTER`, `SINCE`, `AS OF`, past-tense inquiries).
   - **Structure-Aware STAR-RAG** (`STRUCTURE_AWARE_STAR_RAG_ENABLED`) activates selectively when queries demand deep architectural flow tracing, multi-hop call hierarchies, or cross-service dependencies.
   - **Coordinated Mode:** When both flags are enabled, queries with compound intents receive coordinated multi-signal context assembly without collision.
3. **Zero Hallucination AST Call Extraction:** Connected `ASTFunctionCallVisitor` to live snapshot sources and file models, filtering all 40+ Python built-in functions, resolving local and imported call targets, and recording verified line numbers from authentic source code.
4. **Context Budget Envelope Guarantee:** Both granular evidence paths and historical temporal events are strictly budgeted (max 25% each) within the 8,000-character context window of `ContextAssembler`, preventing prompt overflow.
5. **Production Safety Defaults:** Both feature flags remain `False` by default in `settings.py` (`STAR_RAG_ENABLED=False`, `STRUCTURE_AWARE_STAR_RAG_ENABLED=False`), enabling safe canary releases and per-request runtime opt-in via `GroundedAskRequest` API payloads.

---

## 2. Architecture & Dual-Engine Topology

```
                                 [ Developer Query ]
                                          │
                                          ▼
                         [ Query Analyzer (Multi-Intent) ]
                                          │
               ┌──────────────────────────┼──────────────────────────┐
               │ (Standard / Direct)      │ (Historical / Temporal)  │ (Structural Call Trace)
               ▼                          ▼                          ▼
      [ ATOM MultiSignal ]      [ Temporal STAR-RAG ]     [ Structure-Aware STAR-RAG ]
      - Exact Symbol / Path     - Apriori Mining (s, r, o) - AST Call Hierarchy Extractor
      - Sparse BM25 / FTS       - Rule Graph & Hamming <=1 - Filter Built-ins (len, print)
      - Dense Semantic Cosine   - MDL Compression Loss     - Local/Cross-File Resolution
      - Graph 1-Hop Expansion   - Seeded PageRank (PPR)    - DTP + Hub Attenuation
      - Reciprocal Rank Fusion  - Event Re-ranking         - SSAF Fusion Scoring
               │                          │                          │
               │ (Candidates)             │ (Historical Events)      │ (Evidence Paths)
               └──────────────────────────┼──────────────────────────┘
                                          ▼
                                [ Context Assembler ]
                        ┌───────────────────────────────────┐
                        │ Context Budget Envelope (8,000 ch)│
                        │ ├─ Granular Paths:      <= 25%    │
                        │ ├─ Temporal Events:     <= 25%    │
                        │ └─ Ranked Code Chunks:  >= 50%    │
                        └───────────────────────────────────┘
                                          │
                                          ▼
                            [ LLM Synthesis (Groq / Claude) ]
```

---

## 3. 14-Item Requirement Verification Matrix

| Test ID | Requirement Description | Status | Verification Target & Test Name |
| :--- | :--- | :--- | :--- |
| **Test A** | Both flags disabled (`STAR_RAG=False`, `STRUCT_RAG=False`) routes purely to ATOM | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_a_both_disabled_uses_atom_only` |
| **Test B** | Temporal-only enabled routes historical queries to STAR-RAG and structural to ATOM | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_b_temporal_only_routes_historical_to_star_and_structural_to_atom` |
| **Test C** | Structure-Aware only enabled routes structural queries to STAR-RAG and historical to ATOM | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_c_structure_aware_only_routes_structural_to_star_and_historical_to_atom` |
| **Test D** | Both flags enabled coordinates retrieval, combining code chunks, evidence paths, and historical events | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_d_both_enabled_coordinated_retrieval` |
| **Test E** | `ASTFunctionCallVisitor` extracts verified `CALLS` edges, resolves imports/local scope, and ignores built-ins (`len`, `print`) | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_e_function_calls_edge_extraction_and_builtins_filtering` |
| **Test F** | `ContextAssembler` formats evidence paths, temporal events, and code chunks within strict character budget | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_f_evidence_paths_and_temporal_events_reach_assembler_within_budget` |
| **Test G** | Direct symbol or path query routes to ATOM even when both STAR-RAG engines are enabled | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_g_direct_symbol_lookup_preserved_on_atom` |
| **Test H** | Real API endpoint `POST /api/v1/intelligence/projects/{id}/ask` accepts runtime opt-in flags and returns debug signals | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_h_real_api_ask_project_endpoint` |
| **Test I** | Multi-snapshot history query loads chunks across snapshots of the same repository and idempotently deduplicates | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_i_multi_snapshot_history_retrieval_across_snapshots` |
| **Test J** | Branch separation strictly isolates temporal history between `main` and feature branches | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_j_branch_separation_isolates_histories` |
| **Test K** | Real API endpoint `POST /conversations/{id}/messages` forwards STAR-RAG flags and thinking tier | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_k_api_flag_forwarding_in_conversations_endpoint` |
| **Test L** | End-to-end LLM synthesis prompt receives structured evidence paths and historical events alongside code | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_l_combined_evidence_reaches_llm_synthesis` |
| **Test M** | Server restart simulation (clearing `_MEMORY_GRAPH_CACHE`) successfully re-queries DB and rebuilds graph | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_m_restart_persistence_in_memory_cache_cleared` |
| **Test N** | Extracted caller, callee, file path, and exact line numbers match physical source code lines without drift | **PASS** | `test_temporal_and_structure_aware_star_rag_activation.py::test_n_real_source_provenance_matches_source_code` |

---

## 4. Temporal STAR-RAG Implementation Details

- **Apriori Relational Pattern Mining:** Analyzes historical commits and changes, extracting frequent co-occurrence patterns of `(subject, relation, object)` triplets.
- **Hamming $\le 1$ Edge Construction:** Rule graph nodes representing mined temporal patterns are linked with undirected edges whenever their rule predicate vectors differ by at most one substitution, forming a dense structural manifold.
- **Minimum Description Length (MDL) Graph Compression:** Uses an information-theoretic loss function:
  $$L(G) = |V| \cdot \log_2(|V|) + |E| \cdot \log_2(|E|) + \lambda \sum_{v \in V} \text{Residual}(v)$$
  Prunes redundant and noisy edges while retaining the most explanatory temporal subgraph.
- **Seeded Personalized PageRank (PPR):** Query entities and temporal anchor commits serve as restart seeds, propagating random walk mass across the compressed temporal rule graph with restart probability $\alpha = 0.15$.
- **Temporal Constraint Event Re-ranking:** Enforces monotonic time windows (`BEFORE`, `AFTER`, `SINCE`, `AS OF`) to elevate previous implementations and deprecation events when queried.
- **Repository & Branch Scoping:** `load_historical_events_from_db()` queries all completed snapshots sharing `repository_id` and filters by branch ancestry, deduplicating events with deterministic keys:
  `ev:<commit_sha[:8]>:<subject>:<relation>:<object>`

---

## 5. Structure-Aware STAR-RAG Implementation Details

- **AST Function Call Visitor (`ASTFunctionCallVisitor`):**
  - Traverses the Python AST to record actual `CALLS` invocations.
  - Resolves calls using imports (`from X import Y`, `import X`), local scope definitions, and snapshot symbol tables.
  - Strict exclusion of 40+ Python built-in functions (`len`, `print`, `isinstance`, `range`, `enumerate`, `zip`, etc.) to prevent false hub nodes.
  - Records 1-indexed source line numbers directly from AST nodes with line-offset compensation.
- **Stable Edge Deduplication:**
  `FunctionGraph.add_edge()` enforces identity deduplication on `(source_id, target_id, relation_type, line_number)`.
- **Decoupled Topological Propagation (DTP) & Hub Attenuation:**
  - Forward and backward walks through call hierarchies apply logarithmic hub attenuation:
    $$W_{\text{eff}}(u, v) = \frac{W(u, v)}{\log_2(\text{degree}(v) + 2)}$$
    damping ubiquitous utility functions from swamping domain-specific logic.
- **Semantic-Structural Adaptive Fusion (SSAF):**
  Combines ATOM multi-signal candidate relevance scores with structural graph walk confidence scores:
  $$S_{\text{fused}}(c) = \beta \cdot S_{\text{ATOM}}(c) + (1 - \beta) \cdot S_{\text{graph}}(c)$$
- **Granular Evidence Paths (`GranularEvidencePath`):**
  Emits verifiable step-by-step call chains with source file, source function, relation, target function, target file, and line number.

---

## 6. Context Assembler Budget Management

`ContextAssembler.assemble_context()` dynamically partitions the prompt character budget (default 8,000 characters / 2,000 tokens):
1. **Structural Evidence Paths (max 25% / 2,000 characters):**
   Formatted under `### [STRUCTURE-AWARE STAR-RAG EVIDENCE PATH]` with call hierarchy, structural confidence, and line numbers.
2. **Historical Temporal Evidence (max 25% / 2,000 characters):**
   Formatted under `## HISTORICAL TEMPORAL EVIDENCE (STAR-RAG)` with timestamps, commit SHAs, change types, and snippets.
3. **Primary Candidate Code Chunks (remaining >= 50% / 4,000+ characters):**
   Ranked code chunks dynamically scaled to prevent truncation of critical implementations.

---

## 7. Configuration & Backward Compatibility

- **Default Settings (`settings.py`):**
  ```python
  STAR_RAG_ENABLED: bool = False
  STRUCTURE_AWARE_STAR_RAG_ENABLED: bool = False
  ```
- **Runtime Opt-In (API Payloads):**
  Callers may selectively activate either or both engines on a per-query basis:
  ```json
  POST /api/v1/intelligence/projects/{project_id}/ask
  {
    "question": "How did auth token validation evolve across commits?",
    "enable_star_rag": true,
    "enable_structure_aware_star_rag": false,
    "thinking_tier": "warm"
  }
  ```
- **Zero Hallucination Offline Fallback:**
  When external LLM APIs are unreachable, `OfflineSynthesizer` synthesizes grounded answers strictly from assembled evidence paths and code chunks, ensuring zero hallucination in test and air-gapped environments.

---

## 8. Test Execution & Regression Suite Results

All suites executed against the unified codebase with 100% pass rates:

| Suite Name | Scope | Tests Run | Result | Duration |
| :--- | :--- | :---: | :---: | :---: |
| `test_temporal_and_structure_aware_star_rag_activation.py` | Dual-Engine Integration Matrix (Tests A-N) | 14 | **14 PASSED** | 20.92s |
| `test_temporal_star_rag_real_git.py` | Real Git Historical Extraction & 5 Queries | 7 | **7 PASSED** | 40.11s |
| `test_star_rag_runtime_retrieval.py` | Structure-Aware Runtime Integration | 8 | **8 PASSED** | 8.21s |
| `test_temporal_star_rag_complete.py` | Temporal STAR-RAG Unit Suite | 8 | **8 PASSED** | 3.14s |
| `test_code_lane_star_rag.py` | Apriori, MDL, and PPR Graph Mining | 19 | **19 PASSED** | 5.42s |
| `test_star_rag_selective_router.py` | Selective Routing Policies | 8 | **8 PASSED** | 2.11s |
| **Total Test Coverage** | **All Combined STAR-RAG Capabilities** | **64** | **64 PASSED** | **79.91s** |

Ruff Linter:
```bash
apps/api/.venv/bin/ruff check apps/api/ tests/
All checks passed!
```

---

## 9. Production Deployment & Operational Guidance

1. **Deployment Phase 1 (Canary):** Deploy with default settings (`STAR_RAG_ENABLED=False`, `STRUCTURE_AWARE_STAR_RAG_ENABLED=False`). ATOM MultiSignal retrieval continues serving 100% of production traffic without risk.
2. **Deployment Phase 2 (Selective Evaluation):** Enable `STRUCTURE_AWARE_STAR_RAG_ENABLED=True` in staging or for beta projects to evaluate call hierarchy tracing on complex repositories.
3. **Deployment Phase 3 (Historical Intelligence):** Enable `STAR_RAG_ENABLED=True` once repository ingestion workers have completed multi-commit historical chunking.
4. **Monitoring:** Monitor `debug_signals` in ask responses (`star_rag_used`, `structure_aware_star_rag_used`, `star_rag_temporal_routing_decision`, `star_rag_routing_decision`) to observe routing accuracy across query workloads.
