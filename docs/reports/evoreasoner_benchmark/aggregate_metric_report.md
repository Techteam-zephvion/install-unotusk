# EvoKG + EvoReasoner Aggregate Metric Report

## 1. Overall Performance Across System Configurations

| Configuration | Recall@3 | Recall@5 | Recall@10 | Precision@3 | Precision@5 | MRR | nDCG@5 | Latency P50 | Latency P95 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **M0_BASELINE** | 0.2818 | 0.3546 | 0.4436 | 0.4167 | 0.3583 | 0.6818 | 0.4989 | 48.11 ms | 52.51 ms |
| **M1_STAR_RAG** | 0.2892 | 0.3530 | 0.4436 | 0.4167 | 0.3542 | 0.6855 | 0.4968 | 111.02 ms | 121.95 ms |
| **M2_MEMOTIME** | 0.2748 | 0.3450 | 0.4436 | 0.4028 | 0.3458 | 0.6818 | 0.4882 | 48.2 ms | 55.66 ms |
| **M3_COMBINED** | 0.2823 | 0.3434 | 0.4395 | 0.4028 | 0.3417 | 0.6855 | 0.4861 | 107.64 ms | 119.96 ms |
| **M4_EVOREASONER** | 0.2839 | 0.3560 | 0.4623 | 0.4097 | 0.3625 | 0.6855 | 0.5017 | 156.93 ms | 175.94 ms |
| **M4a_DIAGNOSTIC** | 0.2839 | 0.3560 | 0.4623 | 0.4097 | 0.3625 | 0.6855 | 0.5017 | 154.75 ms | 168.8 ms |
