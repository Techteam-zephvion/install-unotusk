# EvoReasoner Ablation Comparison Report

## Component-by-Component Contribution Analysis

| Component Added | Baseline -> Delta | MRR Impact | nDCG@5 Impact | Latency Impact (P50) |
| :--- | :---: | :---: | :---: | :---: |
| **STAR-RAG (M1 vs M0)** | Recall@5: +0.0058 | +0.0036 | +0.0021 | +59.61 ms |
| **MemoTime (M2 vs M0)** | Recall@5: +0.0000 | +0.0000 | +0.0000 | -0.36 ms |
| **Combined STAR-RAG + MemoTime (M3 vs M0)** | Recall@5: +0.0058 | +0.0036 | +0.0021 | +59.85 ms |
| **Full Evo Stack (M4 vs M3)** | Recall@5: +0.0087 | +0.0000 | +0.0115 | +6.78 ms |
| **Proof Chains Isolated (M4 vs M4a)** | Recall@5: +0.0000 | +0.0000 | +0.0000 | -1.00 ms |
