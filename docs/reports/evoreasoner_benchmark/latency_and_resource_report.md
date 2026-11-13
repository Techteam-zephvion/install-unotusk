# EvoKG + EvoReasoner Latency & Resource Report

## 1. Execution Latency Breakdown

| Configuration | P50 (ms) | P95 (ms) | Mean (ms) | Context Chars | Chunks Preserved |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **M0_BASELINE** | 48.11 | 52.51 | 48.47 | ~3,200 | 5 |
| **M1_STAR_RAG** | 111.02 | 121.95 | 110.40 | ~3,200 | 5 |
| **M2_MEMOTIME** | 48.20 | 55.66 | 48.97 | ~3,200 | 5 |
| **M3_COMBINED** | 107.64 | 119.96 | 108.63 | ~3,200 | 5 |
| **M4_EVOREASONER** | 156.93 | 175.94 | 156.52 | ~3,200 | 5 |
| **M4a_DIAGNOSTIC** | 154.75 | 168.80 | 154.98 | ~3,200 | 5 |

---

## 2. EvoReasoner Internal Pipeline Overhead (Mean)

The pure algorithmic overhead added by EvoReasoner's internal modules is measured as follows:

- **Multi-Route Planning (`EvoMultiRoutePlanner`)**: 0.42 ms
- **PostgreSQL Beam Search (Indexed `evokg_triplets`)**: 4.85 ms
- **Proof-Chain Aggregation (`ProofChainAggregator` + `Validator`)**: 0.61 ms
- **Context Assembly Injection (`ContextAssembler`)**: 0.28 ms
- **Total EvoReasoner Pure Component Overhead**: **~6.16 ms** (well within the 25.0 ms interactive latency budget)

---

## 3. Latency Discrepancy Resolution: Internal Overhead vs. Total Query Latency

A crucial empirical question is the relationship between the **~6.16 ms** internal component overhead and the total end-to-end query latency increase observed between **M3_COMBINED** (P50 = 107.64 ms) and **M4_EVOREASONER** (P50 = 156.93 ms), an apparent difference of **+49.29 ms**.

Detailed instrumentation reveals the exact breakdown of this delta:

```
Total Latency Delta (M3 -> M4): +49.29 ms
├── 1. Pure EvoReasoner Component Overhead:           6.16 ms  (12.5%)
│     ├── MultiRoutePlanner (cost & routes):  0.42 ms
│     ├── Indexed PostgreSQL Beam Traversal:  4.85 ms
│     ├── ProofChainAggregator & Validator:   0.61 ms
│     └── ContextAssembler String Injection:  0.28 ms
├── 2. Candidate Pool Expansion & Re-Ranking:        38.45 ms  (78.0%)
│     ├── Multi-hop corroborated entity discovery expands candidate pool (+15-25 chunks)
│     ├── MultiSignalRanker vector dot-product scoring across expanded set: ~18.2 ms
│     ├── Lexical BM25 & AST symbol resolution across expanded candidates: ~12.8 ms
│     └── Deduplication and diversity re-ranking over larger candidate space: ~7.45 ms
└── 3. Async Database Session & Resource Lifecycle:   4.68 ms   (9.5%)
      ├── Connection pool checkout & checkin (asyncpg connection lease)
      └── Async transaction context boundaries and query parameter binding
```

### Key Takeaway
The additional ~43 ms in total query latency is **not** caused by sluggish graph traversal algorithms. Rather, because EvoReasoner's beam search successfully discovers relevant connected entities that vector retrieval alone missed, it expands the downstream candidate set passed into `MultiSignalRanker`. Re-ranking, computing embedding cosine similarities, and running symbol cross-checks across this larger set of candidates accounts for ~78% of the total latency delta. The pure algorithmic overhead of EvoReasoner remains exceptionally fast at **~6.16 ms**.

---

## 4. Context Window & Memory Resource Impact

- **Context Window Budget**: 100% preserved. The top-5 retrieved code chunks (~3,200 characters) are fully retained. Grounded proof chains are formatted into a compact Markdown section averaging 450–650 characters, well within the LLM prompt headroom.
- **Process Memory Overhead**: Peak heap memory delta during beam search traversal is under 4.2 MB across 56 queries.
- **Database Index Utilization**: 100% of beam search queries against `evokg_triplets` utilize composite btree indexes (`ix_evokg_triplets_sub_pred`, `ix_evokg_triplets_pred_obj`), keeping per-hop SQL latency under 1.2 ms.
