# E3 Stage 1 Technical Report: Unsupervised Confidence Scoring for Sparse Software Projects

**Track:** AI-PIE Code Lane Research Proof of Concept (E3 Stage 1)  
**Research Paper:** *Comparison of Unsupervised Metrics for Evaluating Judicial Decision Extraction* — [arXiv:2510.01792](https://arxiv.org/abs/2510.01792)  
**Repository:** `Techteam-zephvion/install-unotusk`  
**Execution Context:** Real Code Lane Pipeline (`E1` Generative Extraction $\rightarrow$ `E2` Ontology Induction $\rightarrow$ `E3` Confidence Scoring)  
**Status:** `E3 FUNCTIONAL — PROJECT-LEVEL VALIDATION PENDING`

---

## 1. Executive Summary & Objective

The objective of **E3 Stage 1** is to establish an unsupervised, evidence-grounded confidence scoring and evidence sufficiency assessment engine for software engineering facts and ontology proposals in sparse software repositories. In early-stage or enterprise codebase intelligence, projects frequently suffer from **history sparsity**—limited code changes, few commits, single-file diffs, or incomplete source code coverage.

Rather than relying on hallucinated model probabilities or penalizing a project simply because it has fewer commits, E3 adapts the unsupervised metric evaluation framework of **arXiv:2510.01792** to software artifacts. It evaluates:
1. **Direct Evidence Quality** (provenance completeness, lexical coherence, syntax harmony).
2. **Structural & Temporal Consistency** (cycle detection, hierarchy adherence, contradiction absence).
3. **Corroboration & Independence** (multi-file and cross-commit support vs. redundant duplicate penalty).
4. **Project Evidence Sufficiency** (decoupled sparsity index: `ABUNDANT`, `MODERATE`, `SPARSE`, `CRITICALLY_INSUFFICIENT`).

---

## 2. Methodology Mapping: Legal Extraction (arXiv:2510.01792) $\rightarrow$ Code Lane

The reference paper examines unsupervised metric families for evaluating information extraction when human reference annotations are scarce. In E3, these metric families are adapted to software source code changes and architectural proposals:

| Reference Research Metric (arXiv:2510.01792) | Legal Domain Formulation | Code Lane Domain Adaptation |
| :--- | :--- | :--- |
| **Citation Coverage / Completeness** | Proportion and syntactic validity of statutory/case citations | Completeness and validity of `file_path`, line numbers (`start_line`, `end_line`), `diff_snippet`, and `grounded_tokens`. |
| **Term Frequency Coherence** | TF-IDF / lexical alignment between extracted elements and ruling | Alignment between extracted symbol identifiers (e.g. `BearerTokenAuth`) and tokens in source diffs and commit messages. |
| **Intra-Block Semantic Coherence** | Consistency of evidence within a single legal holding | Semantic harmony between entity types and naming conventions (e.g. `CLASS` vs `FUNCTION`), and relation type argument compatibility. |
| **Structural Consistency** | Adherence to legal decision hierarchical structure | Absence of circular relationships (`SPECIALIZES`, `COMPOSED_OF`), absence of self-parenting in candidate taxonomies. |
| **Redundancy Penalty** | Penalty for duplicate rulings across text blocks | Detection and penalization of duplicate facts extracted from the identical diff hunk without independent corroboration. |
| **Corroboration / Inter-Block Support** | Multi-paragraph affirmation of legal principles | Verification across independent files or independent commits; single observations receive valid baseline scores without artificial sparsity penalties. |
| **Contradiction Detection** | Incompatible legal dispositions | Identification of conflicting relationships (e.g. mutual `REPLACES` or incompatible temporal validity). |
| **Keyword Pseudo-Ground-Truth Proxy** | Unsupervised F1 proxy measuring key legal term overlap | Extraction of declared code identifiers from diff headers (`def`, `class`, `import`) to compute heuristic pseudo-precision, pseudo-recall, and pseudo-F1. |

> [!IMPORTANT]
> Domain Exclusions: Legal-specific metrics from the paper (such as *Legal Term Density*, *Statutory Citation Ratio*, and court hierarchy weights) have been omitted as they possess no meaningful equivalent in source code intelligence.

---

## 3. Mathematical Formulation & Scoring Engine

The normalized heuristic confidence score $C(f) \in [0.0, 1.0]$ for a fact or proposal $f$ is computed through a linear combination of grounded quality signals modulated by redundancy and contradiction penalties:

$$C(f) = \max\left(0.0, \min\left(1.0, \left( \sum_{m \in M_{\text{active}}} w_m \cdot S_m(f) \right) \cdot (1 - P_{\text{red}}(f)) - P_{\text{contra}}(f) \right)\right)$$

### Base Metric Weights ($w_m$, Normalized to $\sum w_m = 1.0$):
- **Provenance Completeness ($w_{\text{prov}} = 0.30$):**
  $$S_{\text{prov}} = 0.35 \cdot \mathbb{I}_{\text{valid\_path}} + 0.25 \cdot \mathbb{I}_{\text{valid\_lines}} + 0.25 \cdot \mathbb{I}_{\text{diff\_present}} + 0.15 \cdot \mathbb{I}_{\text{tokens\_grounded}}$$
- **Term Frequency Coherence ($w_{\text{tf}} = 0.25$):**
  Jaccard sub-token overlap between identifier tokens and the diff vocabulary. Exact substring match yields $1.0$.
- **Intra-Block Coherence ($w_{\text{intra}} = 0.20$):**
  Evaluates naming syntax conformance (e.g., PascalCase for `CLASS`, snake_case for `FUNCTION`, route format for `API`).
- **Structural Consistency ($w_{\text{struct}} = 0.15$):**
  $1.0$ minus cycle/hierarchy penalties ($0.40$ for circular directed edges, $0.25$ for self-referencing links).
- **Corroboration Score ($w_{\text{corrob}} = 0.10$):**
  $0.50$ for single verified observation; $0.80$ for $\ge 2$ independent files/commits; $1.00$ for $\ge 3$ independent sources.

### Categorical Thresholds & Abstention:
- **`HIGH`**: $C(f) \ge 0.75$
- **`MEDIUM`**: $0.50 \le C(f) < 0.75$
- **`LOW`**: $0.25 \le C(f) < 0.50$
- **`INSUFFICIENT_EVIDENCE`**: $C(f) < 0.25$ or abstention triggered.
- **Abstention Policy:** If provenance completeness $S_{\text{prov}} < 0.20$ (missing source files or ungrounded claims) or if unresolvable structural contradictions exist, the engine abstains ($C(f) \rightarrow \text{INSUFFICIENT\_EVIDENCE}$).

---

## 4. Sparse-Project Behavior & Evidence Budgets

In sparse projects, a common defect of naive confidence models is penalizing a fact simply because the repository has few commits. E3 decouples **Direct Evidence Confidence** from **Global Evidence Sufficiency**:

1. **Direct Evidence in 1 Commit:** A function modified in 1 commit with complete file path, valid line boundaries, and grounded diff tokens receives $C(f) \ge 0.77$ (`HIGH`).
2. **Project Evidence Sufficiency ($S_{\text{suff}}$):** Categorized based on commit count, modified file count, fact count, and diff volume into:
   - **`ABUNDANT`**: $\ge 5$ commits, $\ge 5$ files, $\ge 15$ facts (Sparsity index $\approx 0.15$).
   - **`MODERATE`**: $\ge 3$ commits or ($\ge 3$ files and $\ge 8$ facts) (Sparsity index $\approx 0.40$).
   - **`SPARSE`**: $\ge 1$ commit with verified diff $> 50$ chars (Sparsity index $\approx 0.70$).
   - **`CRITICALLY_INSUFFICIENT`**: 0 commits, 0 facts, or trivial scalar diff (Sparsity index $\ge 0.95$).

### Controlled Downsampling Experiments:
Evaluated across controlled commit budgets ($k \in \{1, 2, 3, 5, 10\}$) using the real E1 benchmark scenarios:

| Evidence Budget | Commits ($k$) | Extracted Facts | Induced Concepts | Evidence Sufficiency | Sparsity Index | Overall Confidence | Confidence Level | Abstention Rate | Contradictions |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1 Commit** | 1 | 3 | 2 | **SPARSE** | 0.70 | **0.7720** | `HIGH` | 0.0% | 0 |
| **2 Commits** | 2 | 10 | 6 | **SPARSE** | 0.70 | **0.7694** | `HIGH` | 0.0% | 0 |
| **3 Commits** | 3 | 14 | 8 | **MODERATE** | 0.40 | **0.7666** | `HIGH` | 0.0% | 0 |
| **5 Commits** | 5 | 23 | 13 | **ABUNDANT** | 0.15 | **0.7298** | `MEDIUM` | 22.2% | 5 |
| **10 Commits** | 10 | 38 | 18 | **ABUNDANT** | 0.15 | **0.7247** | `MEDIUM` | 20.7% | 7 |

*Findings:*
- At $k=1$ and $k=2$, facts are sparse but directly grounded with zero contradictions, maintaining high individual fact reliability.
- At $k \ge 5$, multi-commit evolution introduces deprecations and replacements (e.g. `dev_05_auth_deprecation` superseding `LegacySessionAuth` with `BearerTokenAuth`), correctly surfacing structural contradictions and causing the engine to selectively abstain on contested facts.

---

## 5. Controlled Metric Ablation Analysis

Ablation experiments were performed over a 5-commit multi-file evolution sequence to evaluate whether each unsupervised metric contributes distinct, non-redundant signal:

| Configuration | Overall Score | Score $\Delta$ | Confidence Level | Abstention Rate | Key Finding |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Baseline (All Metrics Active)** | **0.7298** | — | `MEDIUM` | 22.2% | Reference multi-signal baseline |
| **Without Provenance Completeness** | **0.8021** | **+0.0723** | `HIGH` | 22.2% | Omitting provenance artificially inflates confidence on ungrounded claims. |
| **Without TF Coherence** | **0.6674** | **-0.0624** | `MEDIUM` | 22.2% | Lexical diff-alignment provides strong baseline grounding signal. |
| **Without Intra-Block Coherence** | **0.6960** | **-0.0338** | `MEDIUM` | 22.2% | Syntax & naming convention check prevents malformed type associations. |
| **Without Structural Consistency** | **0.7184** | **-0.0114** | `MEDIUM` | **5.56%** | Disabling structural check fails to catch circular and contradictory relations. |
| **Without Corroboration Score** | **0.7665** | **+0.0367** | `HIGH` | 22.2% | Omitting corroboration ignores multi-source affirmation bonuses. |

---

## 6. End-to-End Pipeline Integration: Real Data Flow

E3 connects directly to the existing E1 and E2 interfaces without mocks:

```
┌─────────────────────────┐
│ GitCommitArtifact (Git) │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ E1 Extractor & Validator│ ──> Produces 94 entities, 11 relations, 39 events (40 cases)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ E2 Ontology Inducer     │ ──> Induces Candidate Concepts & Relations (Status: PROPOSED)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ E3 Sparse Conf. Engine  │ ──> Computes Unsupervised Confidence & Evidence Sufficiency
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ E3AssessmentResult JSON │ ──> Serializable & Reloadable (Zero Data Loss)
└─────────────────────────┘
```

### Critical Data Distinction:
- **E1 M1 Offline Extraction Output:** Evaluates to **94 entities, 11 relations, and 39 events** across the 40 benchmark scenarios.
- **E2 Independent Evaluator:** Evaluates to **218 entities and 52 relations** from simulated reference annotations.
- E3 consumes genuine extraction outputs (`E1ExtractionResult` and `OntologyProposal`) and does not confuse them with provisional benchmark annotations.

---

## 7. Verification & Test Suite Summary

- **New E3 Test Suite (`tests/unit/test_e3_sparse_confidence.py`):** **11 passed in 2.05s**
  1. `test_high_quality_direct_evidence`: Validates high score for complete provenance.
  2. `test_sparse_single_commit_not_penalized_for_sparsity`: Validates sparse project decoupled confidence.
  3. `test_missing_provenance_penalties_and_abstention`: Validates ungrounded fact abstention.
  4. `test_duplicate_evidence_redundancy_penalty`: Validates duplicate occurrence penalty.
  5. `test_cross_file_independent_corroboration`: Validates multi-file corroboration boost.
  6. `test_contradictory_relationship_detection`: Validates reciprocal conflict detection.
  7. `test_structural_consistency_and_hierarchy`: Validates circular dependency violations.
  8. `test_keyword_pseudo_f1_calculation`: Validates pseudo-ground-truth proxy metrics.
  9. `test_deterministic_repeated_execution`: Validates bit-for-bit repeatability.
  10. `test_serialization_and_round_trip`: Validates JSON serialization and schema reloading.
  11. `test_real_e1_e2_e3_pipeline_integration`: Validates real end-to-end data flow.
- **Full Project Unit Suite:** **631 passed, 2 skipped** (Zero regressions).
- **Ruff Linter:** `0 errors` (`All checks passed!`).

---

## 8. Limitations & Human-Validation Requirements

1. **Unsupervised Heuristics vs. Statistical Calibration:**
   The confidence scores are normalized heuristic signals grounded in code evidence. They do **not** represent calibrated frequentist probabilities or human agreement rates.
2. **Pending Human Ground Truth:**
   The 40 E1 benchmark annotations remain classified as provisional AI drafts. Formal statistical calibration requires double-annotated human ratings from software engineering practitioners.
3. **Project-Level History Grouping:**
   The 40 benchmark scenarios represent discrete change patterns rather than a single continuous linear commit history of one repository. Project-level multi-year history validation remains pending until multi-commit repositories are ingested.

---

## 9. Conclusion & Stage Gate Verdict

E3 Stage 1 successfully delivers an isolated, working, and evidence-grounded confidence scoring engine. It resolves the sparse-project dilemma by distinguishing direct evidence quality from overall coverage sufficiency, and integrates seamlessly with E1 and E2 without altering T1–T4 or the immutable V1 ontology.

**Stage Gate Classification:**
### `E3 FUNCTIONAL — PROJECT-LEVEL VALIDATION PENDING`
*(Stopping execution as mandated. T1–T4, E1, E2, and V1 ontology remain strictly unchanged and frozen.)*
