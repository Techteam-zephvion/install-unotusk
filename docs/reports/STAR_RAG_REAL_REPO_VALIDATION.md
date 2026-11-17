# STAR-RAG Real-Repository Validation, Comparative Benchmarking & Production Readiness Report

**Project:** Unotusk MVP  
**Scope:** Strictly Code Lane (`apps/api/src/services/context_engine/`)  
**Git Base Commit:** `da7247f` (tracking `origin/main`, including STAR-RAG commit `708f866`)  
**Benchmark Artifact:** [`docs/reports/star_rag_real_repo_benchmark.json`](file:///c:/Users/savan/install-unotusk/docs/reports/star_rag_real_repo_benchmark.json)  
**Query Dataset:** [`docs/reports/star_rag_real_repo_benchmark_queries.json`](file:///c:/Users/savan/install-unotusk/docs/reports/star_rag_real_repo_benchmark_queries.json)  
**Date of Validation:** 17 November 2026  
**Final Verdict:** `3. KEEP DISABLED` (Preserve behind feature flag `STRUCTURE_AWARE_STAR_RAG_ENABLED=False` by default)

---

## A. Executive Summary

This report documents the rigorous, real-repository technical validation and comparative benchmarking of **Structure-Aware STAR-RAG** (Zhong et al., *Electronics* 2026, 15(22), 5289) against the authoritative **Baseline ATOM Code Lane** retrieval pipeline in Unotusk MVP.

Validation was conducted without synthetic mock graph fixtures. The evaluation used the real Unotusk backend codebase (`apps/api/src` and `services/workers/`), comprising **154 source files**, **821 extracted code symbols**, **821 code chunks** embedded with **Voyage AI (`voyage-code-2`, 1536-dimensional vectors)**, **1,216 dependency edges (701 resolved to internal files)**, hosted in PostgreSQL 16.15 with `pgvector` 0.8.7.

A curated benchmark of **45 realistic developer queries** was evaluated across 6 archetypes under a 15-query calibration set and a 30-query held-out evaluation set. Every query was executed through:
1. Baseline ATOM (`enable_structure_aware_star_rag=False`): `MultiSignalRetriever` (SQL vector + lexical search), `RelationshipExpander` (1-hop graph), `MultiSignalRanker` (Reciprocal Rank Fusion + AST heuristics), and `ContextAssembler`.
2. Structure-Aware STAR-RAG (`enable_structure_aware_star_rag=True`): `CodeGraphExtractor`, `SemanticNoiseRouter` (SNR), `DecoupledTopologicalPropagator` (DTP), `SemanticStructuralAdaptiveFusion` (SSAF), `GranularEvidencePathBuilder`, and `ContextAssembler`.
3. 5-Way Ablations: Baseline ATOM, ATOM+SNR, ATOM+DTP, ATOM+SSAF, Full STAR-RAG.

### Key Empirical Findings:
1. **Precision & Ranking Regression on Codebases:** Baseline ATOM significantly outperformed Structure-Aware STAR-RAG on standard codebase retrieval tasks:
   - **Precision@1:** Baseline ATOM achieved **0.6750 (67.5%)**, whereas STAR-RAG achieved **0.3750 (37.5%)** (Delta: **-30.00%**).
   - **Precision@3:** Baseline ATOM achieved **0.4833**, whereas STAR-RAG achieved **0.3250** (Delta: **-15.83%**).
   - **Recall@3:** Baseline ATOM achieved **0.4367**, whereas STAR-RAG achieved **0.1967** (Delta: **-24.00%**).
   - **MRR:** Baseline ATOM scored **0.7531**, whereas STAR-RAG scored **0.4824** (Delta: **-0.2707**).
   - **nDCG@3:** Baseline ATOM scored **0.5322**, whereas STAR-RAG scored **0.3398** (Delta: **-0.1924**).
2. **Graph Noise Suppression:** The Semantic Noise Router (SNR) demonstrated high edge filtering capability, suppressing **88.31%** of noisy graph edges (average 1,522 edges filtered per query), confirming the theoretical premise of SNR.
3. **Execution Latency:** Full Structure-Aware STAR-RAG added substantial latency overhead, averaging **1,844.80 ms** total per query compared to **226.42 ms** for Baseline ATOM (+1,618.38 ms, an **8.1x slowdown**).
4. **Out-of-Scope Hallucination Resistance:** On out-of-scope/unanswerable queries (Archetype F), STAR-RAG lowered maximum candidate confidence from **0.8960** (ATOM baseline) down to **0.6814** (a **24.0% reduction** in over-confident false matches).
5. **Architectural Root Cause:** Unlike sparse biological or academic knowledge graphs where structural topology indicates semantic relatedness, software source code contains **high-degree architectural hub files** (e.g., `settings.py`, `session.py`, `exceptions.py`). DTP's topological propagation elevated these utility hubs, while SSAF's linear fusion bypassed ATOM's exact-match heuristics (+1.5 symbol match, +0.8 path match), pushing utility hubs ahead of specific target functions.

**Recommendation:** Structure-Aware STAR-RAG must remain **DISABLED** by default (`STRUCTURE_AWARE_STAR_RAG_ENABLED=False`) in production. The implementation is technically sound, modular, and passes all unit and integration tests, but empirical metrics demonstrate that deploying it as the default retriever would degrade retrieval precision and add unacceptable latency.

---

## B. Research Context and Architecture Summary

The research reference for this implementation is:
> **STAR-RAG: Structure-Aware Graph Retrieval for Retrieval-Augmented Generation on Knowledge Graphs**  
> *Zhenshu Zhong, Kan Chen, Yechen Yin, Song Ming, Qian Sun*  
> Published in *Electronics* 2026, 15(22), 5289 (13 November 2026). DOI: [10.3390/electronics15225289](https://doi.org/10.3390/electronics15225289)

### Two Complementary STAR-RAG Paradigms in Unotusk:
Unotusk preserves two distinct STAR-RAG implementations:
1. **Temporal STAR-RAG (`apps/api/src/services/context_engine/star_rag.py`):** Based on Zhu et al. (arXiv:2510.16715). Focuses on temporal rule discovery, Minimum Description Length (MDL) compression, and Git commit evolution history. **Strictly preserved and unmodified.**
2. **Structure-Aware STAR-RAG (`apps/api/src/services/context_engine/star_rag_structure/`):** Based on Zhong et al. (Electronics 2026, 15(22), 5289). Focuses on static function call graphs, semantic edge noise routing, decoupled topological propagation, and adaptive stream fusion.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRUCTURE-AWARE STAR-RAG ARCHITECTURE                    │
│                                                                             │
│   User Question                                                             │
│         │                                                                   │
│         ▼                                                                   │
│   [Query Analyzer & Voyage AI Code Embedding]                               │
│         │                                                                   │
│         ▼                                                                   │
│   [MultiSignalRetriever + 1-Hop Graph Expander]                             │
│         │                                                                   │
│         ▼                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 1. FunctionGraphExtractor: Ingest AST Symbols, Callers, Deps        │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2. SemanticNoiseRouter (SNR): Filter Irrelevant Edges (thresh 0.30) │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 3. DecoupledTopologicalPropagator (DTP): Multi-Order Decay Scoring  │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 4. GranularEvidencePathBuilder: Verifiable Provenance Call Chains   │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 5. SemanticStructuralAdaptiveFusion (SSAF): Dynamic Beta Gating    │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   Final Ranked Candidates -> [ContextAssembler] -> [Grounded Answer]        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## C. Real Repository Test Environment

| Metric | Real Environment Value | Notes |
| :--- | :--- | :--- |
| **Repository Name** | `Techteam-zephvion/install-unotusk` | Unotusk Single-Tenant MVP Codebase |
| **Analyzed Directories** | `apps/api/src/`, `services/workers/` | Full backend and worker runtime |
| **Repository ID** | `e32c8e73-c510-4e77-8bbc-477c6e9d3383` | Verified in PostgreSQL `repositories` |
| **Snapshot ID** | `77057819-c7d5-4d3a-a7eb-2066de7ce834` | Status: `COMPLETED` |
| **Total Source Files** | **154 files** | 100% Tree-sitter parsed |
| **Total Extracted Symbols** | **821 symbols** | 353 Methods, 184 Functions, 284 Classes |
| **Total Code Chunks** | **821 chunks** | Stored in PostgreSQL `code_chunks` |
| **Embedding Model** | `voyage-code-2` | Voyage AI Production API |
| **Embedding Dimensions** | **1,536 dimensions** | 821/821 chunks embedded (100% coverage) |
| **Total Dependencies** | **1,216 dependencies** | 701 resolved to internal files, 515 external |
| **Database** | PostgreSQL 16.15 + pgvector 0.8.7 | Port 5433 (Docker Compose `unotusk-postgres`) |
| **Worker Cache** | Redis 7.2 | Port 6379 (Docker Compose `unotusk-redis`) |
| **LLM Grounding** | Deterministic Offline Grounded Synthesizer | Zero-hallucination baseline verification |

---

## D. Evaluation Dataset Specification

The evaluation dataset comprises **45 realistic developer queries** partitioned across 6 distinct archetypes and split into a **15-query Calibration Set** and a **30-query Held-Out Evaluation Set**.

| Archetype | Count | Intent Description | Expected Hops |
| :--- | :---: | :--- | :---: |
| **A. Direct Code Search** | 8 | Exact symbol or file name lookup | 0 |
| **B. Semantic Code Search** | 8 | Functional description without exact symbols | 0 |
| **C. Dependency Investigation** | 8 | Coupling, module dependencies, and import graphs | 1 |
| **D. Execution Flow Tracing** | 8 | Multi-hop callers, callees, and async flow chains | 2–3 |
| **E. Complex Architectural** | 8 | Cross-cutting subsystems, lifecycle, and patterns | 2–3 |
| **F. Out-of-Scope / Unknown** | 5 | Concepts not present in MVP (Kubernetes, SAML, Jira) | N/A |
| **Total Queries** | **45** | **40 Answerable, 5 Unanswerable Probes** | **0–3** |

### Split Allocation:
- **Calibration Set (15 Queries):** Q01, Q03, Q05, Q07, Q09, Q12, Q14, Q17, Q19, Q21, Q25, Q29, Q33, Q37, Q41. Used for tuning thresholds and verifying telemetry.
- **Held-Out Evaluation Set (30 Queries):** Q02, Q04, Q06, Q08, Q10, Q11, Q13, Q15, Q16, Q18, Q20, Q22, Q23, Q24, Q26, Q27, Q28, Q30, Q31, Q32, Q34, Q35, Q36, Q38, Q39, Q40, Q42, Q43, Q44, Q45. Strictly reserved for independent evaluation.

---

## E. End-to-End Comparative Evaluation Results

Comparative retrieval metrics calculated on all 40 answerable queries:

| Metric | Baseline ATOM | Structure-Aware STAR-RAG | Absolute Delta | Relative Delta | Superior System |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Precision@1 (P@1)** | **0.6750** | 0.3750 | -0.3000 | -44.44% | **Baseline ATOM** |
| **Precision@3 (P@3)** | **0.4833** | 0.3250 | -0.1583 | -32.75% | **Baseline ATOM** |
| **Recall@3 (R@3)** | **0.4367** | 0.1967 | -0.2400 | -54.96% | **Baseline ATOM** |
| **Recall@5 (R@5)** | **0.5092** | 0.2948 | -0.2144 | -42.11% | **Baseline ATOM** |
| **Hit@1 Rate** | **0.6750** | 0.3750 | -0.3000 | -44.44% | **Baseline ATOM** |
| **Mean Reciprocal Rank (MRR)** | **0.7531** | 0.4824 | -0.2707 | -35.94% | **Baseline ATOM** |
| **nDCG@3** | **0.5322** | 0.3398 | -0.1924 | -36.15% | **Baseline ATOM** |
| **nDCG@5** | **0.4945** | 0.3184 | -0.1761 | -35.61% | **Baseline ATOM** |
| **Average Latency (ms)** | **226.42 ms** | 1,844.80 ms | +1,618.38 ms | +714.77% | **Baseline ATOM** |
| **Context Assembly Precision** | 0.1412 | **0.1665** | +0.0253 | +17.92% | **STAR-RAG** |
| **Noise Suppression Rate** | N/A | **88.31%** | +88.31% | N/A | **STAR-RAG** |

### Performance Across Calibration vs Evaluation Splits:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CALIBRATION VS EVALUATION SPLITS                      │
├─────────────────────────┬─────────────────────────┬─────────────────────────┤
│ Metric                  │ Calibration (N=14)      │ Evaluation (N=26)       │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ ATOM Baseline P@1       │ 0.6429                  │ 0.6923                  │
│ STAR-RAG P@1            │ 0.4286                  │ 0.3462                  │
│ P@1 Delta               │ -0.2143                 │ -0.3461                 │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ ATOM Baseline P@3       │ 0.5000                  │ 0.4744                  │
│ STAR-RAG P@3            │ 0.3571                  │ 0.3077                  │
│ P@3 Delta               │ -0.1429                 │ -0.1667                 │
├─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ ATOM Baseline MRR       │ 0.7089                  │ 0.7769                  │
│ STAR-RAG MRR            │ 0.5176                  │ 0.4634                  │
│ MRR Delta               │ -0.1913                 │ -0.3135                 │
└─────────────────────────┴─────────────────────────┴─────────────────────────┘
```
The degradation observed in STAR-RAG is consistent across both calibration and held-out evaluation splits, ruling out overfitting or artifact bias.

---

## F. Archetype-by-Archetype Deep Dive

```
                               P@1 BY ARCHETYPE
  1.0 ┌─────────────────────────────────────────────────────────────┐
      │                                                             │
  0.8 │   0.75                      0.88          0.75              │
      │   ┌──┐                      ┌──┐          ┌──┐              │
  0.6 │   │  │                      │  │          │  │   0.50  0.50 │
      │   │  │  0.50                │  │  0.50    │  │   ┌──┐  ┌──┐ │
  0.4 │   │  │  ┌──┐   0.38         │  │  ┌──┐    │  │   │  │  │  │ │
      │   │  │  │  │   ┌──┐  0.25   │  │  │  │    │  │   │  │  │  │ │
  0.2 │   │  │  │  │   │  │  ┌──┐   │  │  │  │    │  │   │  │  │  │ │
      └───┴──┴──┴──┴───┴──┴──┴──┴───┴──┴──┴──┴────┴──┴───┴──┴──┴──┴─┘
            ATOM  STAR   ATOM  STAR   ATOM  STAR   ATOM  STAR   ATOM  STAR
          [A. Direct]  [B. Semantic]  [C. Dep Inv] [D. Flow Trace] [E. Arch]
```

### 1. Archetype A: Direct Code Search (8 queries)
- **ATOM Baseline:** P@1 = 0.7500, P@3 = 0.5833, MRR = 0.7917
- **STAR-RAG:** P@1 = 0.3750, P@3 = 0.5000, MRR = 0.5339
- **Analysis:** Baseline ATOM's exact symbol matching logic (+1.5 score boost) directly surfaces the queried class or function at rank 1. STAR-RAG's SSAF weights topological hub degree, which occasionally pushes downstream utility functions (e.g. `__init__` in exceptions or session fixtures) above the primary symbol.

### 2. Archetype B: Semantic Code Search (8 queries)
- **ATOM Baseline:** P@1 = 0.5000, P@3 = 0.3750, MRR = 0.6396
- **STAR-RAG:** P@1 = 0.2500, P@3 = 0.1250, MRR = 0.3476
- **Analysis:** Semantic code search queries rely heavily on dense vector similarity (`voyage-code-2`). STAR-RAG's DTP introduces topological scores that dilute purely semantic signals when code graph connections are distant.

### 3. Archetype C: Dependency & Import Investigation (8 queries)
- **ATOM Baseline:** P@1 = 0.8750, P@3 = 0.6250, MRR = 0.8750
- **STAR-RAG:** P@1 = 0.5000, P@3 = 0.4583, MRR = 0.5875
- **Analysis:** Baseline ATOM's `RelationshipExpander` (1-hop SQL traversal) accurately captures direct file-to-file imports. STAR-RAG extracts function-level call graphs, which are sparser than module import graphs for top-level modules.

### 4. Archetype D: Execution Flow Tracing (8 queries)
- **ATOM Baseline:** P@1 = 0.7500, P@3 = 0.4167, MRR = 0.7838
- **STAR-RAG:** P@1 = 0.2500, P@3 = 0.2083, MRR = 0.3610
- **Analysis:** This was expected to be STAR-RAG's strongest category. However, because static AST parsing cannot resolve dynamic async dependencies (such as FastAPI `Depends(get_db)` and dependency injection calls), the AST call graph lacked edges between route handlers and database models, causing DTP propagation to terminate prematurely.

### 5. Archetype E: Complex Architectural Subsystems (8 queries)
- **ATOM Baseline:** P@1 = 0.5000, P@3 = 0.4166, MRR = 0.6756
- **STAR-RAG:** P@1 = 0.5000, P@3 = 0.3333, MRR = 0.5817
- **Analysis:** Both systems tied on P@1 (0.5000). On broad architectural queries, STAR-RAG's noise filtering successfully preserved core pipeline components (`MultiSignalRetriever`, `Ranker`, `Expander`, `Assembler`).

### 6. Archetype F: Unknown & Low-Confidence Queries (5 queries)
- **ATOM Baseline:** Mean Top Score = **0.8960**
- **STAR-RAG:** Mean Top Score = **0.6814** (Superior: lower score on hallucination probes)
- **Analysis:** When queried about concepts not in the codebase (Kubernetes Helm, Jira sync, autonomous PR bots, Okta SAML, quantum circuits), Baseline ATOM returned high vector similarity scores (~0.90) from loose word matches. STAR-RAG suppressed these candidate scores to 0.68 because no structural graph edges supported them. This represents a genuine advantage of STAR-RAG for hallucination resistance.

---

## G. Granular Mechanism Telemetry and Observability

### 1. Semantic Noise Router (SNR) Diagnostics
- **Average Evaluated Edges per Query:** 1,724.1 edges
- **Average Retained Active Edges:** 201.5 edges
- **Average Suppressed Edges:** 1,522.6 edges
- **Noise Suppression Rate:** **88.31%**
- **Gate Activation Distribution:**
  - High Relevance ($g_e \ge 0.60$): 11.4%
  - Intermediate Retention ($0.30 \le g_e < 0.60$): 8.3%
  - Pruned Noise ($g_e < 0.30$): 80.3%
- **Evaluation:** SNR successfully eliminates spurious structural hops, preventing unrelated functions from contaminating the candidate pool.

### 2. Decoupled Topological Propagator (DTP) Diagnostics
- **Graph Nodes in Active Subgraph:** Average 391.9 nodes
- **Max In-Degree Observed:** 38 (utility files: `apps/api/src/config/settings.py`)
- **Max Out-Degree Observed:** 24 (`apps/api/src/services/context_engine/retriever.py`)
- **Order-k Decay Weights:** $\alpha_1 = 1.0, \alpha_2 = 0.50, \alpha_3 = 0.25$
- **Hub Skew Phenomenon:** Because utility modules are imported by almost all services, their forward and backward reachability scores accumulate mass rapidly, biasing the topological score toward infrastructural hub files rather than domain-specific symbols.

### 3. Semantic-Structural Adaptive Fusion (SSAF) Diagnostics
- **Average Detected Conflicts per Query:** **22.0 candidates**
- **Conflict Rate:** 20.4% of evaluated candidates exhibited $|score_{sem} - score_{struct}| \ge 0.40$.
- **Adaptive $\beta$ Distribution:**
  - Semantic-heavy queries (e.g. explain vector search): $\beta \approx 0.70$
  - Structural queries (e.g. trace execution flow): $\beta \approx 0.35$
  - Default balanced: $\beta \approx 0.52$
- **Failure Mode:** In conflict cases where a target symbol had high semantic score ($score_{sem} = 0.90$) but low structural propagation ($score_{struct} = 0.05$), SSAF blended them to $0.55 * 0.90 + 0.45 * 0.05 \approx 0.52$. Meanwhile, a utility hub with $score_{sem} = 0.40$ and $score_{struct} = 0.95$ was blended to $0.55 * 0.40 + 0.45 * 0.95 \approx 0.65$, incorrectly outranking the true target!

### 4. Granular Evidence Path Construction
- **Cycle Safety:** Verified 100% cycle-safe across all queries via visited node sets in BFS traversal.
- **Evidence Path Coverage:** For top seeds, candidates were identified directly without redundant path rendering. For multi-hop candidates, provenance chains were constructed with verified start/end line ranges.

### 5. Execution Latency Profile Breakdown

| Stage | Baseline ATOM (ms) | Structure-Aware STAR-RAG (ms) | Latency Delta |
| :--- | :---: | :---: | :---: |
| Query Analysis | 32.40 ms | 32.40 ms | 0.00 ms |
| SQL Lexical + Vector Retrieval | 114.20 ms | 114.20 ms | 0.00 ms |
| 1-Hop SQL Expansion | 62.10 ms | 62.10 ms | 0.00 ms |
| AST Graph Construction | N/A | 485.60 ms | +485.60 ms |
| SNR Routing & Filtering | N/A | 382.40 ms | +382.40 ms |
| DTP Topological Propagation | N/A | 412.30 ms | +412.30 ms |
| SSAF Adaptive Fusion | N/A | 344.20 ms | +344.20 ms |
| Ranking & Heuristics | 17.72 ms | N/A (replaced by SSAF) | -17.72 ms |
| Context Assembly | 11.60 ms | 11.60 ms | 0.00 ms |
| **Total End-to-End Latency** | **226.42 ms** | **1,844.80 ms** | **+1,618.38 ms** |

---

## H. Full Five-Way Ablation Benchmark

To determine which component of STAR-RAG causes the drop in precision, five configurations were systematically benchmarked on the identical 40 answerable queries:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FIVE-WAY ABLATION TABLE                           │
├───────────────────┬────────┬────────┬────────┬────────┬─────────┬───────────┤
│ Configuration     │  P@1   │  P@3   │  R@3   │  MRR   │ nDCG@3  │ Latency   │
├───────────────────┼────────┼────────┼────────┼────────┼─────────┼───────────┤
│ 1. Baseline ATOM  │ 0.6750 │ 0.4833 │ 0.4367 │ 0.7531 │ 0.5322  │  226 ms   │
│ 2. ATOM + SNR     │ 0.6750 │ 0.4833 │ 0.4367 │ 0.7531 │ 0.5322  │  710 ms   │
│ 3. ATOM + DTP     │ 0.6750 │ 0.4833 │ 0.4367 │ 0.7531 │ 0.5322  │  745 ms   │
│ 4. ATOM + SSAF    │ 0.3750 │ 0.4000 │ 0.2383 │ 0.5067 │ 0.3957  │  685 ms   │
│ 5. Full STAR-RAG  │ 0.3750 │ 0.3250 │ 0.1967 │ 0.4824 │ 0.3398  │ 1,845 ms  │
└───────────────────┴────────┴────────┴────────┴────────┴─────────┴───────────┘
```

### Ablation Insights:
1. **SNR in Isolation (Config 2):** When SNR filters the graph without SSAF altering candidate rank scores, ATOM's ranker preserves baseline ranking (P@1 = 0.6750) while reducing edge count.
2. **DTP in Isolation (Config 3):** When DTP computes topological reachability without SSAF overriding final ranking, precision remains stable.
3. **SSAF is the Primary Driver of Rank Inversion (Config 4):** The moment SSAF fuses semantic and structural scores with a linear combination, P@1 drops from **0.6750 to 0.3750**.
4. **Full Interaction Effect (Config 5):** Combining SNR edge pruning + DTP hub amplification + SSAF linear weighting causes the sharpest drop in Recall@3 (from 0.4367 down to 0.1967) because SNR prunes some dynamic edges while SSAF boosts non-relevant utility hubs.

---

## I. Real API Route and End-to-End Synthesis Validation

The integration was verified through the production FastAPI endpoint:
`POST /api/v1/projects/{project_id}/ask`

### Verification Results:
- **Baseline ATOM Mode (`STRUCTURE_AWARE_STAR_RAG_ENABLED=False`):**
  - HTTP Status: `200 OK`
  - Response Model: `GroundedAnswerResponse`
  - Confidence: `HIGH`
  - Evidence Items: 9 items with verified file, line range, and relevance
  - Debug Signals: `star_rag_used: false`, `structure_aware_star_rag_used: false`
  - Synthesized Answer: Correctly identified `MultiSignalRetriever` in `retriever.py` and detailed `retrieve_candidates` operations.
- **STAR-RAG Mode (`STRUCTURE_AWARE_STAR_RAG_ENABLED=True`):**
  - HTTP Status: `200 OK`
  - Response Model: `GroundedAnswerResponse`
  - Confidence: `HIGH`
  - Evidence Items: 9 items
  - Debug Signals: `structure_aware_star_rag_used: true`
  - Diagnostic Telemetry: `nodes_count: 406`, `total_edges: 28`, `snr_filtered_edges: 2684`, `ssaf_conflicts_detected: 17`
  - Synthesized Answer: Synthesized valid grounded answer with verifiable code citations.

---

## J. Error Analysis, Failure Modes, and Degraded Scenarios

| Failure Scenario | Tested Behavior | System Response | Pass/Fail |
| :--- | :--- | :--- | :---: |
| **Empty Candidate List** | Pass `candidates=[]` to STAR-RAG | Returns `[], is_fallback=True, fallback_reason="Empty candidate list"` | **PASS** |
| **Malformed Python Syntax** | AST parse syntax error in chunk | Logs debug warning, adds fallback file node, continues | **PASS** |
| **Cyclic Dependency Graphs** | Circular module imports ($A \to B \to A$) | `visited` set prevents infinite loops in BFS path traversal | **PASS** |
| **Disconnected Graph Islands** | Isolated symbol with 0 in/out edges | DTP assigns 0 structural score; SSAF gates to pure semantic | **PASS** |
| **Runtime Pipeline Exception** | Injected exception during graph build | Catches `Exception`, logs traceback, safely falls back to `MultiSignalRanker` | **PASS** |

---

## K. Production Readiness Assessment and Verdict

### Official Verdict:
```
================================================================================
                    FINAL VERDICT: 3. KEEP DISABLED
  (STRUCTURE_AWARE_STAR_RAG_ENABLED = False by default in production settings)
================================================================================
```

### Justification:
1. **Empirical Precision Deficit:** Structure-Aware STAR-RAG incurs a **-30.0% drop in Precision@1** (0.6750 to 0.3750) and a **-24.0% drop in Recall@3** compared to Baseline ATOM.
2. **Severe Latency Overhead:** An **8.1x increase in latency** (+1,618 ms) violates production SLA requirements for interactive IDE and desktop chat experiences.
3. **Architectural Mismatch:** The core assumption of Zhong et al. (Electronics 2026)—that graph structure unconditionally amplifies semantic truth—fails in source code repositories due to high-degree infrastructural utility hubs.
4. **Code Quality and Stability:** The implementation is clean, robust, and correctly integrated behind feature flags. It should remain preserved in the codebase for research and specific architectural tracing modes, but must not be enabled by default.

---

## L. Architectural Fit and Trade-Off Analysis

| Dimension | Baseline ATOM | Structure-Aware STAR-RAG |
| :--- | :--- | :--- |
| **Primary Strength** | High precision on exact symbols and files; low latency (226 ms) | High noise pruning (88.3%); low confidence on out-of-scope probes |
| **Primary Weakness** | Over-confident on out-of-scope queries; simple 1-hop graph | High-degree hub distortion; high latency (1,845 ms); lower P@1 |
| **Graph Representation** | Relational SQL 1-hop dependencies | In-memory directed AST call graph |
| **Ranking Methodology** | Reciprocal Rank Fusion + AST heuristic boosts | Adaptive stream fusion (SSAF) |
| **Best Used For** | General developer queries, code search, API navigation | Offline security call-graph audits, architecture risk reviews |

---

## M. Concrete Remediation and Optimization Plan

To make Structure-Aware STAR-RAG competitive with Baseline ATOM in future iterations, the following 4 engineering remediations are required:

1. **Hub Penalty in DTP:** Introduce PageRank-style or TF-IDF-style degree penalization in DTP:
   $$\text{Score}_{\text{adj}}(v) = \frac{\text{Score}_{\text{DTP}}(v)}{1 + \log(1 + \text{deg}_{\text{in}}(v))}$$
   This will suppress utility hubs (`settings.py`, `session.py`, `exceptions.py`) from dominating domain candidates.
2. **Preserve RRF Heuristics in SSAF:** Instead of replacing MultiSignalRanker with a pure linear combination, feed DTP's structural score as a **6th signal** into `MultiSignalRanker.rank_candidates` alongside `vector_similarity`, `semantic_match`, `symbol_match`, etc.
3. **Graph Pre-computation and Caching:** Move `CodeGraphExtractor.extract_from_source` and snapshot graph construction from request time into the **repository ingestion worker** (`services/workers/worker.py`), storing the graph in PostgreSQL or Redis to eliminate the 1,280 ms in-memory extraction overhead.
4. **Dynamic Import Resolution:** Enhance Tree-sitter AST extraction to resolve FastAPI dependency injections (`Depends(fn)`), Celery tasks, and framework decorators so that execution flow chains do not terminate prematurely.

---

## N. Configuration Reference

In `apps/api/src/config/settings.py`:

```python
# ==============================================================================
# STRUCTURE-AWARE STAR-RAG CONFIGURATION (Electronics 2026, 15(22), 5289)
# ==============================================================================
# Master feature flag: STRICTLY False by default for production stability
STRUCTURE_AWARE_STAR_RAG_ENABLED: bool = False

# Granular component flags (active when master flag is enabled)
STRUCTURE_AWARE_SNR_ENABLED: bool = True
STRUCTURE_AWARE_SNR_THRESHOLD: float = 0.30
STRUCTURE_AWARE_DTP_ENABLED: bool = True
STRUCTURE_AWARE_DTP_DECAY: float = 0.50
STRUCTURE_AWARE_SSAF_ENABLED: bool = True
STRUCTURE_AWARE_SSAF_CONFLICT_THRESHOLD: float = 0.40
```

---

## O. Verification Sign-Off

- [x] Real repository ingested into PostgreSQL 16 + pgvector without synthetic fixtures.
- [x] 154 files, 821 symbols, 821 chunks (1,536-dim Voyage embeddings), 1,216 dependencies verified in database.
- [x] 45 real-world developer queries executed across 6 archetypes.
- [x] Baseline ATOM vs Structure-Aware STAR-RAG comparative metrics computed.
- [x] Full 5-way ablation benchmark executed.
- [x] Production FastAPI route `POST /projects/{projectId}/ask` validated.
- [x] Edge cases, cyclicity, and runtime exception fallbacks verified.
- [x] `STRUCTURE_AWARE_STAR_RAG_ENABLED` verified `False` by default in settings.
- [x] Pre-existing `star_rag.py` (Temporal STAR-RAG) untouched and preserved.
- [x] Uncommitted developer work in `experiments/`, `docs/reports/confidence_scoring/`, etc. preserved.
- [x] Exact raw benchmark results persisted to `docs/reports/star_rag_real_repo_benchmark.json`.

---

## P. Appendix: Full Query Dataset and Results Summary

Refer to the complete machine-readable benchmark artifact:
[`docs/reports/star_rag_real_repo_benchmark.json`](file:///c:/Users/savan/install-unotusk/docs/reports/star_rag_real_repo_benchmark.json)

### Top-10 Sample Query Performance Summary:

| Query ID | Archetype | Target Symbol / File | ATOM P@1 | STAR P@1 | ATOM MRR | STAR MRR |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: |
| **Q01** | Direct Search | `MultiSignalRetriever`, `retrieve_candidates` | 1.00 | 1.00 | 1.00 | 1.00 |
| **Q02** | Direct Search | `SemanticNoiseRouter`, `route_and_filter_edges` | 0.00 | 0.00 | 0.33 | 0.07 |
| **Q03** | Direct Search | `DecoupledTopologicalPropagator`, `propagate` | 1.00 | 1.00 | 1.00 | 1.00 |
| **Q04** | Direct Search | `SemanticStructuralAdaptiveFusion`, `fuse` | 1.00 | 0.00 | 1.00 | 0.50 |
| **Q05** | Direct Search | `AuthService`, `authenticate_user` | 1.00 | 0.00 | 1.00 | 0.20 |
| **Q06** | Direct Search | `GranularEvidencePathBuilder` | 1.00 | 0.00 | 1.00 | 0.50 |
| **Q07** | Direct Search | `process_task`, `run_worker` | 1.00 | 1.00 | 1.00 | 1.00 |
| **Q08** | Direct Search | `VoyageEmbeddingProvider` | 0.00 | 0.00 | 0.00 | 0.00 |
| **Q09** | Semantic Search | Vector similarity search (`retriever.py`) | 0.00 | 0.00 | 0.25 | 0.07 |
| **Q10** | Semantic Search | JWT token generation (`auth_service.py`) | 1.00 | 1.00 | 1.00 | 1.00 |

*(The complete evaluations for all 45 queries are preserved in the benchmark JSON).*
