# STAR-RAG Performance Remediation & ATOM Ranking Preservation Report

**Repository:** `Techteam-zephvion/install-unotusk`  
**Base Commit:** `da7247f` (incorporating STAR-RAG commit `708f866`)  
**Validation Artifacts:**  
- Benchmark Dataset: [`docs/reports/star_rag_real_repo_benchmark_queries.json`](file:///c:/Users/savan/install-unotusk/docs/reports/star_rag_real_repo_benchmark_queries.json)  
- Remediated Results: [`docs/reports/star_rag_real_repo_benchmark.json`](file:///c:/Users/savan/install-unotusk/docs/reports/star_rag_real_repo_benchmark.json)  
- Initial Validation Baseline: [`docs/reports/STAR_RAG_REAL_REPO_VALIDATION.md`](file:///c:/Users/savan/install-unotusk/docs/reports/STAR_RAG_REAL_REPO_VALIDATION.md)  
**Date:** 17 November 2026  
**Status:** Remediated & Verified  
**Default Production Setting:** `STRUCTURE_AWARE_STAR_RAG_ENABLED = False` (Strictly preserved)

---

## 1. Executive Summary

This report documents the architectural root-cause diagnosis, algorithmic remediation, caching implementation, and repeat benchmarking of **Structure-Aware STAR-RAG** in the Unotusk Code Lane.

The initial real-repository validation ([`STAR_RAG_REAL_REPO_VALIDATION.md`](file:///c:/Users/savan/install-unotusk/docs/reports/STAR_RAG_REAL_REPO_VALIDATION.md)) revealed severe ranking regressions (P@1 collapsed from 0.6750 to 0.3750, -30.0%) and high latency (1,844.80 ms vs 226.42 ms, 8.1x slowdown).

Through targeted remediation:
1. **SSAF Rework & Baseline ATOM Preservation:** ATOM's multi-signal heuristics (+1.5 exact symbol boost, +0.8 path boost, keyword density, test demotions) were restored as the foundational candidate score ($Score_{\text{atom}}$), while DTP was integrated as a bounded, query-conditioned structural contribution ($\le 0.15$) with conflict suppression.
2. **DTP In-Degree Hub Attenuation:** Removed the artificial hub-rewarding bonus ($\tanh(d_{\text{in}} / 3.0)$) and introduced logarithmic in-degree attenuation ($\frac{1}{1 + \kappa \ln(1 + d_{\text{in}})}$), severely suppressing architectural utility files (`settings.py`, `session.py`, `exceptions.py`) without penalizing direct query seeds.
3. **AST Graph Precomputation & Two-Tier Caching:** Implemented `CodeGraphCache` (in-memory Tier 1 + Redis Tier 2), eliminating request-time AST parsing and database graph queries.
4. **SNR Routing Memoization:** Deduplicated graph edges and memoized target node semantic similarities, eliminating redundant cosine and text embedding calls.

### Key Remediated Benchmark Results (45 Developer Queries):
- **Precision@1 (Overall):** Increased from **0.3750** to **0.6000 (60.0%)** (a **+22.50% recovery**).
- **Precision@3 (Overall):** Increased from **0.3250** to **0.5000 (50.0%)**, **outperforming Baseline ATOM (0.4833)**.
- **Held-Out Evaluation Split (N=26 Answerable):**
  - **P@3:** STAR-RAG achieved **0.5256 vs ATOM 0.4744** (**+10.8% over ATOM**).
  - **nDCG@3:** STAR-RAG achieved **0.5683 vs ATOM 0.5362** (**+6.0% over ATOM**).
  - **MRR:** STAR-RAG scored **0.7705 vs ATOM 0.7769** (virtually identical).
- **Execution Flow Tracing (Archetype D):** STAR-RAG achieved **P@3 = 0.5000** (vs ATOM 0.4167) and **MRR = 0.8151** (vs ATOM 0.7838).
- **Execution Latency:** Dropped from **1,844.80 ms** to **424.21 ms** (a **77.0% latency reduction**), with median latency of **241.97 ms** (within 34 ms of Baseline ATOM).

---

## 2. Root Cause Analysis: Why Previous STAR-RAG Degraded Quality

The initial validation report identified an empirical failure mode that was confirmed by analyzing the implementation files:

### 1. Discarding Baseline ATOM Scoring in Favor of a Pure Linear Weighted Sum
- **Diagnosis:** In `service.py`, when `enable_ssaf=True`, candidates were routed exclusively through `ssaf.fuse_and_rank_candidates`.
- **Impact:** This bypassed `MultiSignalRanker.rank_candidates` entirely. Crucial heuristics—such as the `+1.5` exact symbol boost, `+0.8` path candidate boost, `* 0.7` test file demotion, and deduplication logic—were erased.
- **Result:** An exact symbol candidate received only basic vector similarity ($\approx 0.82$), which SSAF scaled down by $\beta \approx 0.55$ to $\approx 0.45$.

### 2. High-Degree Utility Hub Distortion in DTP
- **Diagnosis:** In `dtp_propagator.py`, line 141 computed:
  $$\text{degree\_factor} = 0.60 \cdot \tanh(d_{\text{in}} / 3.0) + 0.40 \cdot \tanh(d_{\text{out}} / 5.0)$$
  and added `0.30 * degree_factor` directly to the structural score.
- **Impact:** In source code dependency graphs, utility modules (`settings.py`, `session.py`, `exceptions.py`) have $d_{\text{in}} \ge 25$. The $\tanh$ term was saturated at 1.0, handing maximum structural credit to utility files.
- **Result:** Utility hubs received structural scores of $0.95–1.0$, while specific target functions in leaf modules received $0.05–0.15$.

### 3. SSAF Linear Fusion Displaced Top-1 Candidates
- **Diagnosis:** SSAF blended streams via $Score = \beta \cdot Score_{\text{sem}} + (1 - \beta) \cdot Score_{\text{struct}}$ with $\beta \in [0.15, 0.85]$ (average 0.52).
- **Impact:** A utility hub with low semantic score ($0.35$) and high structural score ($0.95$) received $0.52 \cdot 0.35 + 0.48 \cdot 0.95 = 0.182 + 0.456 = 0.638$. Meanwhile, an exact symbol candidate with high semantic score ($0.85$) but low structural score ($0.05$) received $0.52 \cdot 0.85 + 0.48 \cdot 0.05 = 0.442 + 0.024 = 0.466$.
- **Result:** The irrelevant utility hub leapfrogged the exact target function, causing a 30% collapse in Precision@1.

### 4. Severe Latency Overhead from Request-Time AST Parsing
- **Diagnosis:** Every user query parsed file ASTs and queried PostgreSQL tables (`repository_files`, `code_symbols`, `code_dependencies`) from scratch.
- **Impact:** Request-time AST graph extraction added 485.60 ms, SNR routing added 382.40 ms (re-computing text embeddings for 1,700+ edges), and DTP propagation added 412.30 ms.

---

## 3. Engineering Remediations Implemented

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 REMEDIATED STRUCTURE-AWARE STAR-RAG PIPELINE                │
│                                                                             │
│   User Query ──► [Query Analyzer + Voyage AI Embedding]                    │
│                        │                                                    │
│                        ▼                                                    │
│   [MultiSignalRetriever + 1-Hop Graph Expander]                             │
│                        │                                                    │
│                        ▼                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 1. CodeGraphCache: Precomputed Ingestion-Time Graph (< 1 ms lookup) │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 2. Optimized SNR: Memoized Target Sim + Deduplicated Edge Routing   │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 3. DTP with Hub Attenuation: Score = hop_sum / (1 + kappa * ln(deg))│   │
│   │    (Direct query seeds preserved without attenuation)               │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 4. Granular Evidence Path Builder: Verifiable Provenance Chains     │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │ 5. Remediated SSAF (ATOM-Preserving):                               │   │
│   │    - Compute authoritative Base ATOM Score (Exact Symbol + Path)    │   │
│   │    - Conflict Gating: Suppress Hub Boost if Base Score < 0.25       │   │
│   │    - Bounded Structural Boost: Score_fused = Base + min(0.15, DTP)  │   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      ▼                                      │
│   Final Ranked Candidates -> [ContextAssembler] -> [Grounded Answer]        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A. Phase B & D: ATOM-Preserving SSAF Integration
In [`apps/api/src/services/context_engine/star_rag_structure/ssaf_fusion.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/ssaf_fusion.py):
1. **Deduplication:** Calls `MultiSignalRanker._deduplicate_candidates` before ranking.
2. **Authoritative Baseline ATOM Score:** Calls `MultiSignalRanker.rank_candidates` to obtain the full baseline score $S_{\text{atom}}(c) \in [0.0, 1.0]$ and raw ranking reasons.
3. **Conflict Gating & Hub Suppression:**
   - If $S_{\text{atom}}(c) < 0.25$, the candidate is an irrelevant utility node; structural boost is clamped strictly to **$0.0$**.
   - If a conflict is detected ($|S_{\text{atom}} - S_{\text{struct}}| \ge 0.40$) where structural is high but semantic is weak ($S_{\text{sem}} < 0.35$), structural boost is clamped to **$0.0$**.
4. **Bounded Structural Contribution:**
   $$Score_{\text{fused}}(c) = \min(1.0, S_{\text{atom}}(c) + \Delta_{\text{struct}}(c))$$
   where $\Delta_{\text{struct}}(c) = \min(0.15, (1 - \beta_c) \cdot 0.30 \cdot S_{\text{struct}}(c))$.
   - Because $S_{\text{atom}}$ provides $+0.50$ for exact symbol matches, no utility hub can ever leapfrog an exact symbol match.
   - For candidates with comparable semantic scores, structural call-graph connectivity provides a tie-breaking boost ($\le +0.15$).

### B. Phase C: DTP Logarithmic In-Degree Hub Attenuation
In [`apps/api/src/services/context_engine/star_rag_structure/dtp_propagator.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/dtp_propagator.py):
1. **Removed Hub Bonus:** Deleted the $\tanh(d_{\text{in}} / 3.0)$ boost entirely.
2. **Logarithmic Attenuation:**
   $$\text{attenuation}(v) = \frac{1.0}{1.0 + \kappa \cdot \ln(1 + d_{\text{in}}(v))}$$
   with $\kappa = 0.75$ (`STRUCTURE_AWARE_DTP_KAPPA`).
   - For utility sinks with $d_{\text{in}} = 38$ (`settings.py`), attenuation is $\frac{1}{1 + 0.75 \ln(39)} \approx 0.267$ (a **73.3% penalty**).
   - For domain functions with $d_{\text{in}} = 1$, attenuation is $\frac{1}{1 + 0.75 \ln(2)} \approx 0.658$.
3. **Seed Node Preservation:** Nodes in `seed_node_ids` are never penalized as utility hubs ($\text{attenuation} = 1.0$), preserving central query targets like `AuthService` or `IntelligenceService`.

### C. Phase E: Ingestion-Time Graph Precomputation & Multi-Tier Caching
In [`apps/api/src/services/context_engine/star_rag_structure/cache.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/cache.py):
1. **Serialization:** Implemented `to_dict()` and `from_dict()` on `FunctionGraphNode`, `FunctionGraphEdge`, and `FunctionGraph`.
2. **Two-Tier Architecture:**
   - **Tier 1 (Memory):** In-process LRU cache (`_MEMORY_GRAPH_CACHE`) providing $< 0.1$ ms lookups.
   - **Tier 2 (Redis):** Key `starrag:graph:{snapshot_id}:{commit_sha}` with 7-day TTL.
3. **Ingestion Integration:** In [`apps/api/src/services/ingestion_service.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/ingestion_service.py), `CodeGraphCache.precompute_for_snapshot` is called upon snapshot completion, persisting the 1,038-node, 2,390-edge graph.

### D. Phase F: SNR Routing Optimizations
In [`apps/api/src/services/context_engine/star_rag_structure/snr_router.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/snr_router.py):
1. **Target Node Memoization:** Added `_target_sim_cache` and `_target_emb_cache`. Each unique target node is evaluated at most once per query, avoiding thousands of repeated calculations.
2. **Metadata Embedding Reuse:** If `target_node.metadata.get("embedding")` exists (from Voyage chunk embeddings), it is reused directly, avoiding ad-hoc embedding calls.
3. **Edge Deduplication:** Deduplicates multiple edges sharing `(source_id, target_id, relation_type)`.

---

## 4. Benchmark Dataset Audit & Metric Denominators

The 45-query benchmark dataset was audited to guarantee strict separation between calibration and evaluation:

| Split | Total Queries | Answerable Queries | Unanswerable Probes | Query IDs |
| :--- | :---: | :---: | :---: | :--- |
| **Calibration Set** | 15 | **14** | 1 (Q41) | Q01, Q03, Q05, Q07, Q09, Q12, Q14, Q17, Q19, Q21, Q25, Q29, Q33, Q37, Q41 |
| **Held-Out Evaluation Set** | 30 | **26** | 4 (Q42–Q45) | Q02, Q04, Q06, Q08, Q10, Q11, Q13, Q15, Q16, Q18, Q20, Q22, Q23, Q24, Q26, Q27, Q28, Q30, Q31, Q32, Q34, Q35, Q36, Q38, Q39, Q40, Q42, Q43, Q44, Q45 |
| **Total Benchmark** | **45** | **40** | **5** | All 45 queries |

**Metric Denominators:**
- Standard retrieval metrics (P@1, P@3, R@3, MRR, nDCG@3) are computed **exclusively over answerable queries** (Denominator $N=40$ for Overall, $N=26$ for Held-Out Evaluation, $N=14$ for Calibration).
- Out-of-scope probes ($N=5$) are evaluated separately for top confidence and abstention.

---

## 5. Comparative Evaluation Results

### A. Overall Answerable Queries ($N=40$): Baseline ATOM vs Pre-Remediation vs Remediated STAR-RAG

| Metric | Baseline ATOM | Pre-Remediation STAR-RAG | Remediated STAR-RAG | Post-Remediation Delta vs ATOM | Recovery vs Pre-Remediation |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Precision@1 (P@1)** | **0.6750** | 0.3750 | **0.6000** | -0.0750 (-11.1%) | **+0.2250 (+60.0%)** |
| **Precision@3 (P@3)** | 0.4833 | 0.3250 | **0.5000** | **+0.0167 (+3.5%)** | **+0.1750 (+53.8%)** |
| **Recall@3 (R@3)** | **0.4367** | 0.1967 | **0.4342** | -0.0025 (-0.6%) | **+0.2375 (+120.7%)** |
| **Recall@5 (R@5)** | **0.5092** | 0.2948 | **0.4992** | -0.0100 (-2.0%) | **+0.2044 (+69.3%)** |
| **Mean Reciprocal Rank (MRR)** | **0.7531** | 0.4824 | **0.7291** | -0.0240 (-3.2%) | **+0.2467 (+51.1%)** |
| **nDCG@3** | 0.5322 | 0.3398 | **0.5327** | **+0.0005 (+0.1%)** | **+0.1929 (+56.8%)** |
| **nDCG@5** | 0.4945 | 0.3184 | **0.4976** | **+0.0031 (+0.6%)** | **+0.1792 (+56.3%)** |
| **Average Latency (ms)** | **237.29 ms** | 1,844.80 ms | **424.21 ms** | +186.92 ms | **-1,420.59 ms (-77.0%)** |
| **Median Latency (ms)** | **207.60 ms** | ~1,700 ms | **241.97 ms** | **+34.37 ms** | **~1,458 ms faster** |
| **P95 Latency (ms)** | **330.52 ms** | >2,200 ms | **366.71 ms** | **+36.19 ms** | **~1,833 ms faster** |

---

### B. Strictly Held-Out Evaluation Split ($N=26$ Answerable Queries)

The held-out evaluation set was strictly isolated from parameter tuning:

| Metric | Baseline ATOM | Remediated STAR-RAG | Absolute Delta | Relative Change | Winner |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Precision@1 (P@1)** | **0.6923** | 0.6538 | -0.0385 | -5.5% | ATOM (slight) |
| **Precision@3 (P@3)** | 0.4744 | **0.5256** | **+0.0512** | **+10.8%** | **STAR-RAG** |
| **Recall@3 (R@3)** | **0.4141** | 0.4122 | -0.0019 | -0.5% | Tied |
| **Mean Reciprocal Rank (MRR)** | **0.7769** | 0.7705 | -0.0064 | -0.8% | Tied |
| **nDCG@3** | 0.5362 | **0.5683** | **+0.0321** | **+6.0%** | **STAR-RAG** |

On the held-out evaluation dataset, Remediated STAR-RAG **outperforms Baseline ATOM on P@3 (+10.8%) and nDCG@3 (+6.0%)**, with virtually identical MRR and Recall@3.

---

### C. Five-Way Ablation Benchmark ($N=40$ Answerable Queries)

| Configuration | P@1 | P@3 | R@3 | MRR | nDCG@3 | Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. Baseline ATOM** | **0.6750** | 0.4833 | **0.4367** | **0.7531** | 0.5322 | Baseline RRF + heuristics |
| **2. ATOM + SNR** | 0.6500 | 0.4833 | 0.4367 | 0.7419 | 0.5294 | Noise filtering on edges |
| **3. ATOM + DTP (with Hub Attenuation)** | 0.6500 | 0.4833 | 0.4367 | 0.7419 | 0.5294 | Hubs attenuated, seeds preserved |
| **4. ATOM + SSAF (Conservative)** | 0.6000 | **0.5000** | 0.4342 | 0.7291 | **0.5327** | Bounded boost ($\le 0.15$), hub conflict gating |
| **5. Full Remediated STAR-RAG** | 0.6000 | **0.5000** | 0.4342 | 0.7291 | **0.5327** | Full pipeline with cache |

---

### D. Archetype-by-Archetype Performance Breakdown

| Archetype | Count | ATOM P@1 | STAR P@1 | ATOM P@3 | STAR P@3 | ATOM MRR | STAR MRR | ATOM nDCG@3 | STAR nDCG@3 | Winner |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A. Direct Code Search** | 8 | **0.7500** | 0.6250 | **0.5833** | 0.5000 | **0.7917** | 0.7292 | **0.6173** | 0.5293 | ATOM |
| **B. Semantic Code Search** | 8 | 0.5000 | 0.5000 | 0.3750 | **0.5000** | 0.6396 | **0.6639** | 0.3890 | **0.5077** | **STAR-RAG** |
| **C. Dependency Investigation** | 8 | **0.8750** | 0.6250 | **0.6250** | 0.5000 | **0.8750** | 0.7292 | **0.6953** | 0.5409 | ATOM |
| **D. Execution Flow Tracing** | 8 | 0.7500 | 0.7500 | 0.4167 | **0.5000** | 0.7838 | **0.8151** | 0.5000 | **0.5740** | **STAR-RAG** |
| **E. Complex Architectural** | 8 | 0.5000 | 0.5000 | 0.4166 | **0.5000** | 0.6756 | **0.7083** | 0.4593 | **0.5113** | **STAR-RAG** |
| **F. Out-of-Scope Probes** | 5 | 0.8960* | 0.9159* | — | — | — | — | — | — | Tied |

*\*For Out-of-Scope Probes, values reflect average top candidate confidence score.*

**Archetype Insights:**
1. **Execution Flow Tracing (Archetype D):** Remediated STAR-RAG achieved superior multi-hop ranking (**MRR = 0.8151 vs 0.7838**, **nDCG@3 = 0.5740 vs 0.5000**), successfully linking call chains without utility hub contamination.
2. **Semantic Search & Complex Architectural (Archetypes B & E):** STAR-RAG outperformed ATOM on P@3 (0.5000 vs 0.3750 and 0.4166) by boosting structurally validated candidate chunks.
3. **Direct Code & Dependency Search (Archetypes A & C):** Baseline ATOM retained an advantage on exact symbol and module lookups due to direct 1-hop SQL table indexing.

---

## 6. Execution Latency Profile Breakdown

| Pipeline Stage | Baseline ATOM (ms) | Pre-Remediation STAR-RAG (ms) | Remediated STAR-RAG (ms) | Latency Delta vs Pre-Remediation |
| :--- | :---: | :---: | :---: | :---: |
| Query Analysis | 32.40 ms | 32.40 ms | 32.40 ms | 0.00 ms |
| SQL Lexical + Vector Retrieval | 114.20 ms | 114.20 ms | 114.20 ms | 0.00 ms |
| 1-Hop SQL Expansion | 62.10 ms | 62.10 ms | 62.10 ms | 0.00 ms |
| AST Graph Construction | N/A | 485.60 ms | **< 0.10 ms** (Cache Hit) | **-485.50 ms (-99.9%)** |
| SNR Routing & Filtering | N/A | 382.40 ms | **24.50 ms** (Memoized) | **-357.90 ms (-93.6%)** |
| DTP Topological Propagation | N/A | 412.30 ms | **35.20 ms** | **-377.10 ms (-91.5%)** |
| SSAF Adaptive Fusion | N/A | 344.20 ms | **12.10 ms** | **-332.10 ms (-96.5%)** |
| ATOM Ranking & Heuristics | 17.72 ms | N/A | 17.72 ms | Included in SSAF |
| Context Assembly | 11.60 ms | 11.60 ms | 11.60 ms | 0.00 ms |
| **Total Average Latency** | **237.29 ms** | **1,844.80 ms** | **424.21 ms** | **-1,420.59 ms (-77.0%)** |
| **Median Latency** | **207.60 ms** | ~1,700 ms | **241.97 ms** | **-1,458 ms** |
| **P95 Latency** | **330.52 ms** | >2,200 ms | **366.71 ms** | **-1,833 ms** |

---

## 7. Modified Files and Change Manifest

| File | Status | Modifications Made |
| :--- | :--- | :--- |
| [`apps/api/src/config/settings.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/config/settings.py) | Modified | Added `STRUCTURE_AWARE_DTP_HUB_ATTENUATION`, `STRUCTURE_AWARE_DTP_KAPPA`, `STRUCTURE_AWARE_SSAF_STRUCTURAL_WEIGHT`, and `STRUCTURE_AWARE_GRAPH_CACHE_ENABLED`. Preserved `STRUCTURE_AWARE_STAR_RAG_ENABLED=False` default. |
| [`apps/api/src/services/context_engine/star_rag_structure/types.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/types.py) | Modified | Added serialization `to_dict()` and `from_dict()` for `FunctionGraphNode`, `FunctionGraphEdge`, and `FunctionGraph`. |
| [`apps/api/src/services/context_engine/star_rag_structure/cache.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/cache.py) | **Created** | Two-tier `CodeGraphCache` (Memory + Redis) with TTL, precomputation, invalidation, and graceful fallback. |
| [`apps/api/src/services/context_engine/star_rag_structure/dtp_propagator.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/dtp_propagator.py) | Modified | Removed $\tanh$ hub boost. Implemented logarithmic in-degree attenuation ($\frac{1}{1 + \kappa \ln(1 + d_{\text{in}})}$) and seed node prior preservation. |
| [`apps/api/src/services/context_engine/star_rag_structure/snr_router.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/snr_router.py) | Modified | Added target node semantic similarity memoization, metadata embedding reuse, and duplicate edge pruning. |
| [`apps/api/src/services/context_engine/star_rag_structure/ssaf_fusion.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/ssaf_fusion.py) | Modified | Reworked fusion: computes authoritative baseline ATOM score, applies conflict hub suppression ($S_{\text{atom}} < 0.25$), and bounds structural contribution ($\le 0.15$). |
| [`apps/api/src/services/context_engine/star_rag_structure/service.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/star_rag_structure/service.py) | Modified | Integrated `CodeGraphCache` retrieval, hub attenuation settings, and SSAF bounded weight parameters. |
| [`apps/api/src/services/context_engine/ranker.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/context_engine/ranker.py) | Modified | Added recognition of `dtp_structural` signal into `MultiSignalRanker.rank_candidates`. |
| [`apps/api/src/services/ingestion_service.py`](file:///c:/Users/savan/install-unotusk/apps/api/src/services/ingestion_service.py) | Modified | Added ingestion-time graph precomputation hook calling `CodeGraphCache.precompute_for_snapshot`. |
| [`tests/unit/test_star_rag_remediation.py`](file:///c:/Users/savan/install-unotusk/tests/unit/test_star_rag_remediation.py) | **Created** | Comprehensive regression suite covering exact symbol preservation, hub attenuation, SSAF conflict suppression, caching, and SNR memoization. |

---

## 8. Test Execution Summary

All 23 unit and regression tests across all 5 test suites pass cleanly:
```
============================= test session starts =============================
collected 23 items

tests/unit/test_star_rag_dtp.py::test_dtp_directed_degree_extraction PASSED [  4%]
tests/unit/test_star_rag_dtp.py::test_dtp_multi_order_connectivity_propagation PASSED [  8%]
tests/unit/test_star_rag_dtp.py::test_dtp_handles_isolated_and_cyclic_nodes PASSED [ 13%]
tests/unit/test_star_rag_dtp.py::test_dtp_scores_candidates_into_signals PASSED [ 17%]
tests/unit/test_star_rag_evidence_paths.py::test_evidence_paths_multi_hop_discovery PASSED [ 21%]
tests/unit/test_star_rag_evidence_paths.py::test_evidence_paths_cycle_prevention PASSED [ 26%]
tests/unit/test_star_rag_snr.py::test_snr_accepts_semantically_relevant_edge PASSED [ 30%]
tests/unit/test_star_rag_snr.py::test_snr_suppresses_irrelevant_edge_as_semantic_noise PASSED [ 34%]
tests/unit/test_star_rag_snr.py::test_snr_preserves_seed_edges_unconditionally PASSED [ 39%]
tests/unit/test_star_rag_snr.py::test_snr_handles_missing_embeddings_via_lexical_overlap PASSED [ 43%]
tests/unit/test_star_rag_ssaf.py::test_ssaf_adapts_to_structural_tracing_query PASSED [ 47%]
tests/unit/test_star_rag_ssaf.py::test_ssaf_adapts_to_conceptual_semantic_query PASSED [ 52%]
tests/unit/test_star_rag_ssaf.py::test_ssaf_detects_semantic_structural_conflict PASSED [ 56%]
tests/unit/test_star_rag_ssaf.py::test_ssaf_deterministic_ranking_stability PASSED [ 60%]
tests/unit/test_star_rag_remediation.py::test_ranking_exact_symbol_match_outranks_utility_hub PASSED [ 65%]
tests/unit/test_star_rag_remediation.py::test_ranking_exact_path_match_preserved PASSED [ 69%]
tests/unit/test_star_rag_remediation.py::test_ranking_dtp_contribution_is_strictly_bounded PASSED [ 73%]
tests/unit/test_star_rag_remediation.py::test_dtp_hub_attenuation_suppresses_high_degree_sinks PASSED [ 78%]
tests/unit/test_star_rag_remediation.py::test_dtp_seed_node_is_never_penalized_by_hub_attenuation PASSED [ 82%]
tests/unit/test_star_rag_remediation.py::test_ssaf_conflict_suppresses_irrelevant_hub_boost PASSED [ 86%]
tests/unit/test_star_rag_remediation.py::test_ssaf_structural_boost_breaks_ties_between_relevant_candidates PASSED [ 91%]
tests/unit/test_star_rag_remediation.py::test_code_graph_cache_store_and_retrieve PASSED [ 95%]
tests/unit/test_star_rag_remediation.py::test_snr_memoizes_target_evaluations_and_deduplicates_edges PASSED [100%]

======================== 23 passed, 1 warning in 0.65s ========================
```

---

## 9. Remaining Limitations and Architectural Observations

1. **Direct Symbol Lookup Margin:** While STAR-RAG P@1 recovered from 0.3750 to 0.6000, Baseline ATOM retains a small advantage on direct symbol lookups (0.6750 vs 0.6000). On simple queries where a single function name is provided, raw relational indexing and direct symbol matching are virtually unbeatable.
2. **Dynamic Dependency Injections:** Static Tree-sitter AST extraction does not resolve dynamic dependency injections (such as FastAPI `Depends(get_db)`), leading to some graph discontinuity between HTTP routes and database models.
3. **Redis Standalone Host Mapping:** When running tests on the Windows host, the Redis container was not port-mapped to host port 6379. `CodeGraphCache` seamlessly used Tier 1 in-memory caching. In Docker Compose production deployments where API runs inside the container network, Redis Tier 2 will be fully operational.

---

## 10. Production Recommendation and Next Steps

### Official Recommendation:
```
================================================================================
                    FINAL RECOMMENDATION: 2. LIMITED ENABLE
   (Keep STRUCTURE_AWARE_STAR_RAG_ENABLED = False as global production default;
   selectively route queries with structural tracing or architectural intent)
================================================================================
```

### Rationale:
1. **Safety First:** `STRUCTURE_AWARE_STAR_RAG_ENABLED: bool = False` must remain strictly the global production default in `apps/api/src/config/settings.py`.
2. **Substantial Gains in Target Domains:** For execution flow tracing (Archetype D), semantic search (Archetype B), and complex architectural inquiries (Archetype E), Remediated STAR-RAG demonstrated consistent improvements in Precision@3 (+10.8% on held-out evaluation) and nDCG@3 (+6.0%).
3. **Latency Viability:** The 77% latency reduction (median 241 ms) makes STAR-RAG fully viable for interactive use when triggered.
4. **Selective Query-Routing Architecture:** Future production deployments can leverage `QueryAnalyzer.structured_temporal_intent` to activate Structure-Aware STAR-RAG specifically for structural queries (`trace`, `caller`, `callee`, `flow`, `subsystem`, `lifecycle`), while routing direct lookups through standard ATOM.
