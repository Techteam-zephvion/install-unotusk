# EvoKG + EvoReasoner Latency & Resource Report

## Execution Latency Breakdown

| Configuration | P50 (ms) | P95 (ms) | Mean (ms) | Context Chars | Chunks Preserved |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **M0_BASELINE** | 45.22 | 48.92 | 45.27 | ~3,200 | 5 |
| **M1_STAR_RAG** | 104.83 | 111.01 | 104.9 | ~3,200 | 5 |
| **M2_MEMOTIME** | 44.86 | 50.68 | 45.6 | ~3,200 | 5 |
| **M3_COMBINED** | 105.07 | 116.51 | 105.7 | ~3,200 | 5 |
| **M4_EVOREASONER** | 111.85 | 120.75 | 112.05 | ~3,200 | 5 |
| **M4a_DIAGNOSTIC** | 112.85 | 132.01 | 114.28 | ~3,200 | 5 |

## EvoReasoner Internal Pipeline Overhead (Mean)

- **Multi-Route Planning**: 0.42 ms
- **PostgreSQL Beam Search (Indexed)**: 4.85 ms
- **Proof-Chain Aggregation**: 0.61 ms
- **Context Assembly**: 0.28 ms
- **Total EvoReasoner Overhead**: ~6.16 ms (well within 25ms interactive budget)
