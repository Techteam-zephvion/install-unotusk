# E1 — Baseline Fairness Analysis: Investigating and Remediating Track T1 (ATOM) Benchmark Disparities

**Repository:** `Techteam-zephvion/install-unotusk`  
**Track:** E1 — Generative Information Extraction  
**Authoritative Architectural Specification:** `AI_PIE_Architecture_V1_Elite.pdf` — Section 2 (Code KG), Section 6 (Decision Extraction), Section 24 (E1)  
**Related Test Suite:** [`tests/unit/test_e1_generative_ie.py`](file:///c:/Users/savan/install-unotusk/tests/unit/test_e1_generative_ie.py)  
**Date:** November 6, 2026  

---

## 1. Executive Summary & Problem Statement

In Stage 1 preliminary benchmarks, Configuration M0 (the deterministic Track T1 ATOM baseline) reported an **Entity F1 score of $0.0000$** across all 40 scenarios. This outcome contradicted the verified performance of the ATOM engine in production acceptance testing ([`T1_ATOM_COMPLETION_REPORT.md`](file:///c:/Users/savan/install-unotusk/docs/reports/temporal_kg_completion/T1_ATOM_COMPLETION_REPORT.md)), where ATOM achieved **$100.0\%$ precision and recall** on deterministic AST extraction across genuine repository commits.

A rigorous forensic investigation was conducted to determine why M0 appeared completely defective in the synthetic benchmark harness. The investigation revealed that **M0 was severely and artificially disadvantaged** by synthetic in-memory diff formatting and restrictive entity harvesting adapters.

This report documents the root-cause analysis, the remediation implemented in Stage 2, and the resulting fair comparative evaluation.

---

## 2. Root Cause Investigation: Why Did M0 Report Zero Entity F1 in Stage 1?

The failure was traced to three distinct architectural and harness-level discrepancies:

```
Stage 1 Artificial Baseline Defect
┌────────────────────────────────┐
│ Synthetic _make_commit Harness │
│  hunk.header = "@@ -1,5 ... @@"│
│  section_header = None         │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐      ┌──────────────────────────────┐
│ CodeAtomDecomposer             │      │ Fallback Triggered           │
│  - symbol_catalog = None       │─────▶│ _resolve_symbol returns:    │
│  - section_header = None       │      │  (None, None, None)          │
└────────────────────────────────┘      └──────────────┬───────────────┘
                                                       │
                                                       ▼
                                        ┌──────────────────────────────┐
                                        │ M0 Extractor                 │
                                        │  - Only emits FILE entity    │
                                        │  - Symbol entity omitted!    │
                                        │  - Entity TP = 0             │
                                        └──────────────────────────────┘
```

### Forensic Breakdown:

1. **Synthetic Hunk Header Truncation:**
   In Stage 1, the test fixture helper `_make_commit()` manually instantiated `GitDiffHunk` objects with a generic header:
   ```python
   # Stage 1 Flawed Harness
   hunk = GitDiffHunk(header="@@ -1,5 +1,10 @@", ...)  # section_header is None!
   ```
   When Git generates real diffs, the hunk header line includes the trailing section heading (e.g., `@@ -10,3 +10,3 @@ def calculate_score(...):`). By populating `file_diffs` with header-stripped hunks, the test harness stripped the primary lexical signal ATOM relies on in diff-only ingestion.

2. **In-Memory Symbol Catalog Absence:**
   `CodeAtomDecomposer._resolve_symbol()` is designed to match hunks against an existing AST symbol catalog populated from disk files. In synthetic test scenarios where file paths do not exist as physical files on disk at runtime, the symbol catalog is empty (`None`). Without a section header to fall back to, `_resolve_symbol()` safely returned `(None, None, None)` to prevent scope hallucination.

3. **Restrictive Entity Harvesting in M0 Adapter:**
   In `experiments/e1_generative_ie/extractor.py`, the M0 extraction adapter only converted `change.symbol_name` into an `E1Entity`. Because `change.symbol_name` was `None`, M0 only emitted a single `FILE` entity per change, completely discarding:
   - Symbols extracted by ATOM's `fact_decomposer.py` (e.g., `calculate_score returns weight * 1.5`).
   - Symbol participants extracted by ATOM's `relation_extractor.py` (e.g., `TaskQueue`, `Redis`, `ConflictException`).

Because expected benchmark targets were functions and classes (`calculate_score`, `TaskQueue`), M0 scored zero true positives despite ATOM's underlying parser correctly identifying the code tokens.

---

## 3. Remediation: Building a Fair Baseline

To eliminate artificial bias and establish an authentic, scientifically defensible comparison, three fixes were deployed:

1. **Standard Git Unified Diff Formatting:**
   All 40 scenarios in [`dataset.py`](file:///c:/Users/savan/install-unotusk/experiments/e1_generative_ie/data/dataset.py) were updated to include standard Git hunk section headings:
   ```diff
   diff --git a/apps/api/src/services/scorer.py b/apps/api/src/services/scorer.py
   --- a/apps/api/src/services/scorer.py
   +++ b/apps/api/src/services/scorer.py
   @@ -10,3 +10,3 @@ def calculate_score(weight: float) -> float:
   -    return weight * 1.0
   +    return weight * 1.5
   ```

2. **Authentic Diff Parsing via `parse_unified_diff`:**
   `_make_commit_fair()` now parses diffs using the actual production `parse_unified_diff()` engine, correctly capturing `GitDiffHunk.section_header` and regex-parsed headings.

3. **Comprehensive Entity Harvesting in M0 Adapter:**
   `E1Extractor.extract_m0_atom_baseline()` was updated to harvest entities across all three of ATOM's deterministic outputs:
   - Innermost symbol scope resolved by AST or hunk section headers.
   - Symbols identified by deterministic atomic facts (`SemanticCodeFact.symbol_name`).
   - Participant entities extracted in temporal relations (`TemporalCodeRelation.subject` and `TemporalCodeRelation.object`).

---

## 4. Empirical Results of the Fair Baseline

Following remediation, M0 was benchmarked across all 40 scenarios alongside M1 and M2:

| Metric Category | M0: Stage 1 (Flawed) | M0: Stage 2 (Fair) | M1: Generative IE | M2: Constrained Dec |
| :--- | :---: | :---: | :---: | :---: |
| **Named Entity Precision** | $0.0000$ | **$0.5766$** | $0.8298$ | $0.8298$ |
| **Named Entity Recall** | $0.0000$ | **$0.9753$** | $0.9630$ | $0.9630$ |
| **Named Entity F1** | $0.0000$ | **$0.7248$** | $0.8914$ | $0.8914$ |
| **Relation Recall** | $0.0000$ | **$0.5000$** | $0.3750$ | $0.3750$ |
| **Relation F1** | $0.0000$ | **$0.1538$** | $0.3158$ | $0.3158$ |
| **Event Extraction F1** | $0.0000$ | **$0.0000$** | **$0.5455$** | **$0.5455$** |
| **P50 Latency (ms)** | $0.61\text{ ms}$ | **$0.67\text{ ms}$** | $0.17\text{ ms}$ | $0.19\text{ ms}$ |

---

## 5. Architectural Insights: Capabilities vs. Limitations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Stratified Capability Matrix                          │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Syntactic Capabilities (ATOM Native) │ Semantic Capabilities (E1 Generative)│
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • AST Symbol Identification (97.5% R)│ • Software Evolution Events (54.5% F)│
│ • Direct Method Calls (CALLS)        │ • Commit Message Causal Rationale    │
│ • Module Package Imports (IMPORTS)   │ • Replacement Lifecycles (REPLACES)  │
│ • Class Inheritance (INHERITS)       │ • Behavioral Shifts (Static Sig)     │
│ • Exception Raising (RAISES)         │ • Test Contract Intent (TESTS)       │
│ • Sub-millisecond Execution (<1.5ms) │ • Cross-Component Semantic Coupling  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### Conclusions:
1. **M0 is a Formidable Syntactic Baseline:** When evaluated fairly, ATOM achieves **$97.53\%$ entity recall** and **$0.7248$ F1**. It is exceptionally reliable at capturing concrete code symbols and syntactic calls.
2. **The Zero Event Score is Not a Defect:** M0 scores $0.0000$ on Event Extraction because ATOM is a syntactic decomposition engine, not an event classifier.
3. **Generative IE Provides True Added Value:** M1 and M2 do not merely duplicate what ATOM extracts; they capture high-level evolution events ($F1 = 0.5455$) and semantic relationships (`REPLACES`, `TESTS`) that AST grammars cannot express.
4. **The Recommendation Holds:** E1 must be built as a complementary semantic layer that enriches ATOM's syntactic foundation, preserving ATOM's speed and deterministic precision while extending intelligence into architectural intent.
