# Historical Retrieval Analysis & Regression Resolution (T2.8)

## 1. Executive Summary

In milestone T2.7, an empirical regression in Historical Code Understanding (Category B) was observed:
- Baseline M0 Recall@5: **0.5997**
- MemoTime / Combined M2/M3 Recall@5: **0.5424**
- EvoReasoner M4 Recall@5: **0.5580** (delta: **-0.0417**)

Through Phase 0 micro-audits of `per_query_results.json` and component-level tracing, the regression was isolated to a single query:
- Query ID: `q14_historical_assembler_interval_tags`
- Query text: *"How were temporal relationship intervals and ended tag annotations introduced in ContextAssembler?"*
- Baseline M0 Recall@5: **0.8333**
- Regressed M2/M3/M4 Recall@5: **0.5000** (delta: **-0.3333** on 1 query, which divided by 8 queries = exactly **-0.0417** across Category B).

All other 7 queries in Category B achieved identical Recall@5 scores across M0, M2, M3, and M4.

Following the minimal, principled corrections implemented in Phase 1, **Category B Recall@5 has been fully restored to 0.5997 (and 0.6602 on the expanded 84-query dataset), with zero regression in Current Code, Temporal Reasoning, or Multi-Hop Reasoning.**

---

## 2. Root Cause Investigation

### 2.1 Missing Introduction Keywords in Temporal Lexicon
Query `q14` utilized the phrasing:
> *"How were temporal relationship intervals and ended tag annotations **introduced** in ContextAssembler?"*

In the pre-T2.8 implementation:
- `TEMPORAL_KEYWORDS` in `apps/api/src/services/code_atom/temporal.py` and `memotime.py` lacked past-tense genesis words such as `"introduced"`, `"introduction"`, `"initially"`, `"initial"`, `"originally"`, and `"origin"`.
- Consequently, `analyze_query()` classified the question as non-temporal or generic, failing to recognize the explicit request for the historical introduction commit.

### 2.2 Unconditioned Historical Boosting in MultiSignalRanker
In `MultiSignalRanker.rank_candidates` and benchmark Step C, historical temporal intent was handled with an unconditioned boost:
```python
elif query_spec.intent == TemporalIntentType.HISTORICAL:
    if not is_active:
        r.score *= 1.40  # Applied to ALL superseded/inactive candidates indiscriminately
```

Because this boost applied to *every* inactive chunk regardless of symbol or file match:
1. Historical chunks from unrelated modules (such as `TemporalCodeRelation` from commit `6626c5c` or `RelationshipExpander` from commit `b094f01`) received the full 1.40x multiplier.
2. Moderate lexical similarity caused these unrelated historical chunks to leapfrog genuine target chunks (`ContextAssembler` from commit `773b740`).
3. For query `q14`, this displacement pushed the third relevant `ContextAssembler` chunk down to rank 6, cutting Recall@5 from `0.8333` (5/6 chunks) down to `0.5000` (3/6 chunks).

---

## 3. Implemented Corrections

Two minimal, non-invasive code changes were applied:

### 3.1 Temporal Lexicon Expansion
Added genesis and origin keywords (`"introduced"`, `"introduction"`, `"initially"`, `"initial"`, `"originally"`, `"origin"`) to:
- `apps/api/src/services/code_atom/temporal.py`: added to `TEMPORAL_KEYWORDS`
- `apps/api/src/services/context_engine/memotime.py`: added to `_HISTORICAL_CUES` regex patterns
- `apps/api/src/services/evoreasoner/planner.py`: added to route planning intent matching

### 3.2 Symbol/File Conditioned Historical Boosting
Conditioned the 1.40x historical boost on entity relevance (matching queried symbol name or file path) in `MultiSignalRanker`:
```python
matches_entity = any(s in c_name or s in c_sym or (len(c_name) > 3 and c_name in s) for s in target_syms if len(s) > 2)
matches_file = any(f in c_path or c_path in f for f in target_files)

elif query_spec.intent == TemporalIntentType.HISTORICAL:
    if not is_active:
        if matches_entity or matches_file or not target_syms:
            r.score *= 1.40
        else:
            r.score *= 0.85  # Demote unrelated inactive chunks
    else:
        if not matches_entity and not matches_file:
            r.score *= 0.70  # Demote unrelated active chunks
```

---

## 4. Verification & Results

### 4.1 Authoritative 56-Query Benchmark Verification
| Category | Metric | Baseline M0 | Regressed M4 (T2.7) | Hardened M4 (T2.8) | Delta vs Baseline |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Historical Code Understanding** | Recall@5 | 0.5997 | 0.5580 | **0.5997** | **±0.0000 (Fully Restored)** |
| Current Code Understanding | Recall@5 | 0.3027 | 0.3235 | **0.3339** | **+0.0312** |
| Temporal Reasoning | Recall@5 | 0.2833 | 0.3333 | **0.3333** | **+0.0500** |
| Multi-Hop Reasoning | Recall@5 | 0.3317 | 0.3413 | **0.3413** | **+0.0096** |
| Superseded Violations | Violations | 0 | 0 | **0** | **0** |

### 4.2 Expanded 84-Query Generalization Verification
On the expanded 84-query benchmark (12 queries per category):
- **Category B (Historical Code) Recall@5**: **0.6602** across M0, M1, M2, M3, M4, and M4a.
- Zero superseded violations under CURRENT intent.
- 100% abstention precision on ungrounded historical requests.

### 4.3 Regression Test Suite
Created `tests/unit/test_historical_retrieval_hardening.py` with 4 dedicated regression tests:
1. `test_1_historical_intent_detection_on_introduced_phrasing`: PASSED
2. `test_2_historical_intent_detection_on_initially_and_originally`: PASSED
3. `test_3_conditioned_historical_ranking_prevents_unrelated_displacement`: PASSED
4. `test_4_current_intent_demotes_superseded_chunks`: PASSED
