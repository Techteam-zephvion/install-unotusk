# EvoKG + EvoReasoner Aggregate Metric Report

## 1. Overall Performance Across System Configurations

| Configuration | Recall@3 | Recall@5 | Recall@10 | Precision@3 | Precision@5 | MRR | nDCG@5 | Latency P50 | Latency P95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M0_BASELINE** | 0.3803 | 0.4488 | 0.5858 | 0.4444 | 0.3889 | 0.6714 | 0.5670 | 45.22 ms | 48.92 ms |
| **M1_STAR_RAG** | 0.3853 | 0.4546 | 0.5858 | 0.4444 | 0.3889 | 0.6750 | 0.5691 | 104.83 ms | 111.01 ms |
| **M2_MEMOTIME** | 0.3803 | 0.4488 | 0.5858 | 0.4444 | 0.3889 | 0.6714 | 0.5670 | 44.86 ms | 50.68 ms |
| **M3_COMBINED** | 0.3853 | 0.4546 | 0.5858 | 0.4444 | 0.3889 | 0.6750 | 0.5691 | 105.07 ms | 116.51 ms |
| **M4_EVOREASONER** | 0.3884 | 0.4633 | 0.6030 | 0.4537 | 0.4028 | 0.6750 | 0.5806 | 111.85 ms | 120.75 ms |
| **M4a_DIAGNOSTIC** | 0.3884 | 0.4633 | 0.6030 | 0.4537 | 0.4028 | 0.6750 | 0.5806 | 112.85 ms | 132.01 ms |
