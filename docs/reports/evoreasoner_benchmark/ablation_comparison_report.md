# EvoReasoner Ablation Comparison Report

## 1. Component-by-Component Contribution Analysis

| Component Added | Baseline -> Delta | MRR Impact | nDCG@5 Impact | Latency Impact (P50) |
| :--- | :---: | :---: | :---: | :---: |
| **STAR-RAG (M1 vs M0)** | Recall@5: -0.0016 | +0.0037 | -0.0021 | +62.91 ms |
| **MemoTime (M2 vs M0)** | Recall@5: -0.0096 | +0.0000 | -0.0107 | +0.09 ms |
| **Combined STAR-RAG + MemoTime (M3 vs M0)** | Recall@5: -0.0112 | +0.0037 | -0.0128 | +59.53 ms |
| **Full Evo Stack (M4 vs M3)** | Recall@5: +0.0126 | +0.0000 | +0.0156 | +49.29 ms |
| **Proof Chains Isolated (M4 vs M4a)** | Recall@5: +0.0000 | +0.0000 | +0.0000 | +2.18 ms |

---

## 2. Category-Specific Ablation Observations

- **Multi-Hop Reasoning (Category D)**:
  - Baseline (M0): 0.4500 Recall@5
  - Combined (M3): 0.4500 Recall@5
  - Full EvoReasoner (M4): **0.9167 Recall@5** (+103.7% relative improvement)
  - *Observation*: Multi-hop queries experience the largest benefit from EvoReasoner beam search across persisted `evokg_triplets`.

- **Historical Code Understanding (Category B) — Observed Regression**:
  - Baseline (M0): 0.5997 Recall@5
  - MemoTime / Combined (M2 / M3): 0.5424 Recall@5
  - Full EvoReasoner (M4): 0.5580 Recall@5 (-0.0417 net delta vs M0 baseline)
  - *Observation*: While EvoReasoner partially recovers the Recall@5 loss introduced in M2/M3 (0.5424 -> 0.5580), active entity graph corroboration slightly competes with older superseded code chunks in the top-5 ranking window.

---

## 3. Latency Attribution Summary

- **Algorithmic EvoReasoner Execution**: **~6.16 ms** (planning, PostgreSQL beam search, proof-chain validation, formatting).
- **Candidate Pool Expansion & Downstream Re-Ranking**: **~38.45 ms** (evaluating vector similarity, BM25, and AST symbols across newly discovered multi-hop entities).
- **Async Database Connection Lifecycle**: **~4.68 ms** (connection acquisition and asyncpg transaction handling).
- **Total Latency Delta (M3 -> M4)**: **+49.29 ms** (P50: 107.64 ms -> 156.93 ms).
