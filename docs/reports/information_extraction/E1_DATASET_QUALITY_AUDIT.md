# E1 Dataset Quality Audit & Ground-Truth Review

**Track:** E1 — Generative Information Extraction  
**Artifact:** `experiments/e1_generative_ie/data/e1_human_review_annotations.json`  
**Dataset Size:** 40 Scenarios (20 Development / 20 Evaluation)  
**Date:** November 11, 2026  
**Status:** **PROVISIONAL — HUMAN REVIEW PENDING**

---

## 1. Corpus Architecture & Composition

The E1 benchmark dataset consists of 40 rigorously specified Git commit scenarios designed to test the boundary between deterministic AST parsing (T1 ATOM) and generative information extraction (LLM).

### 1.1 Dataset Split Distribution

```
40 TOTAL SCENARIOS
├── DEV SPLIT (20 Scenarios: dev_01 to dev_20)
│   ├── Used for: Context prompt design, few-shot demonstration selection, guideline tuning
│   └── Never evaluated without reporting dev-split context
└── EVAL SPLIT (20 Scenarios: eval_21 to eval_40)
    ├── Used for: Blind held-out model evaluation
    └── Isolated from prompt construction to prevent data leakage
```

### 1.2 Categorical Stratification

The dataset spans 15 distinct architectural categories representing diverse real-world development workflows:

| Category | Split Breakdown | Primary Extraction Challenge |
|:---|:---:|:---|
| **Simple** | 1 Dev (`dev_01`) | Single function arithmetic modification and parameter behavior change |
| **Dependency** | 1 Dev (`dev_02`) | Third-party library import (`redis.asyncio`) and client initialization |
| **API** | 1 Dev (`dev_03`) | HTTP route signature update and query parameter addition (`FastAPI`) |
| **Configuration** | 1 Dev (`dev_04`) | Environment and infrastructure parameter changes (`worker_concurrency`) |
| **Deprecation** | 1 Dev (`dev_05`) | `@deprecated` decorator tagging and component replacement |
| **Test** | 1 Dev (`dev_06`) | Pytest test addition testing a core service function |
| **Behavior** | 1 Dev (`dev_07`) | Internal algorithmic refactor preserving external signature |
| **Deletion** | 1 Dev (`dev_08`) | Obsolete symbol removal (`new_memberships_added`) |
| **Trivial** | 1 Dev (`dev_09`) | Formatting and whitespace-only diff (abstention test) |
| **Ambiguous** | 1 Dev (`dev_10`) | Minimal commit message with opaque variable naming |
| **MultiFile** | 6 Dev (`dev_11`–`dev_16`) | Cross-file refactoring, caller-callee updates, shared type imports |
| **MultiLanguage** | 4 Dev + 3 Eval (`dev_17`–`dev_20`, `eval_21`–`eval_23`) | Polyglot codebase commits (Python, TypeScript, Go, Dart) |
| **RealRepo** | 7 Eval (`eval_24`–`eval_30`) | Authentic diffs extracted from Unotusk MVP and open-source repos |
| **Evolution** | 5 Eval (`eval_31`–`eval_35`) | Multi-commit architectural sequence tracking symbol lifecycles |
| **EdgeCase** | 5 Eval (`eval_36`–`eval_40`) | Merge commit hunks, Unicode symbols, massive diff truncations |

---

## 2. Annotation Status & Verification Audit

### 2.1 Current Audit State

Every scenario in `experiments/e1_generative_ie/data/e1_human_review_annotations.json` carries explicit provenance metadata:

```json
{
  "annotation_status": "PROVISIONAL_AI_DRAFT",
  "review_metadata": {
    "reviewed_by": null,
    "review_date": null,
    "review_status": "PENDING_INDEPENDENT_HUMAN_REVIEW",
    "reviewer_notes": ""
  }
}
```

### 2.2 Audit Findings
- **Total Scenarios Audited:** 40
- **Scenarios Marked `PROVISIONAL_AI_DRAFT`:** 40 ($100\%$)
- **Scenarios Marked `HUMAN_VERIFIED`:** 0 ($0\%$)
- **Fabricated Sign-Offs:** None (0 detected)
- **Schema Compliance:** $100\%$ valid against `E1TestCase` Pydantic models.
- **Fairness Metadata:** $100\%$ of entities and relations carry `is_supported_by_atom` boolean flags to enable stratified fairness reporting.

---

## 3. Data Leakage Prevention Protocol

To ensure academic and engineering validity:
1. **Zero Eval in Prompts:** None of the 20 evaluation cases (`eval_21` through `eval_40`) are permitted to be used as prompt examples, system prompt descriptions, or context builder few-shot demonstrations in `experiments/e1_generative_ie/context_builder.py`.
2. **Deterministic Token Isolation:** Ground-truth evidence spans are required to match exact string tokens present in the scenario's diff snippet or commit message, preventing model hallucination of external entity names.

---

## 4. Human Review & Certification Guide

To advance the dataset from `PROVISIONAL_AI_DRAFT` to `HUMAN_VERIFIED`, human software engineers must follow the review protocol detailed in `docs/reports/information_extraction/E1_HUMAN_REVIEW_ANNOTATION_GUIDE.md`:

### Review Steps:
1. **Entity Inspection:** Verify that each entity exists in the diff and that the entity type (`FUNCTION`, `CLASS`, `FILE`, `CONFIG_PARAM`, `DEPENDENCY`) is accurate.
2. **Relation Inspection:** Verify subject-relation-object triplets and check whether the relation represents an architectural dependency or syntactic call.
3. **Event Inspection:** Verify event type (`BEHAVIOR_CHANGED`, `IMPLEMENTATION_DEPRECATED`, `API_CHANGED`, etc.) and ensure the `trigger_statement` is grounded in the commit message or diff comments.
4. **ATOM Fairness Flag:** Verify whether `is_supported_by_atom` is correctly set (true for syntactic definitions and direct imports, false for semantic intent or architectural events).
5. **Worksheet Sign-Off:** Update `annotation_status` to `HUMAN_VERIFIED`, record reviewer name/ID in `reviewed_by`, and add ISO timestamp in `review_date`.

---

## 5. Gate B Conclusion

- **Gate B Result:** **PROVISIONAL — HUMAN REVIEW PENDING**
- **Rationale:** The dataset is fully authored, syntactically and semantically validated, and equipped with a complete review worksheet. However, independent human sign-off has not yet been executed by external engineers. Under Unotusk quality rules, AI draft annotations cannot be claimed as certified ground truth.
