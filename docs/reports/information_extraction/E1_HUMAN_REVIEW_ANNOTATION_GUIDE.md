# E1 — Human-Review Annotation Guide & Ground-Truth Protocol

**Repository:** `Techteam-zephvion/install-unotusk`  
**Track:** E1 — Generative Information Extraction  
**Dataset Artifact:** [`experiments/e1_generative_ie/data/e1_human_review_annotations.json`](file:///c:/Users/savan/install-unotusk/experiments/e1_generative_ie/data/e1_human_review_annotations.json)  
**Corpus Size:** 40 Scenarios (20 Development / 20 Held-Out Evaluation)  
**Date:** November 6, 2026  
**Current Annotation Status:** **`PROVISIONAL_AI_DRAFT` (Awaiting Independent Human Sign-Off)**  

---

## 1. Executive Protocol & Ground-Truth Rule Compliance

> [!IMPORTANT]
> **MANDATORY GROUND-TRUTH COMPLIANCE RULE**  
> All 40 scenarios currently populated in the E1 evaluation corpus were drafted using automated heuristic extraction. In strict accordance with the project ground-truth rules, **these labels must NOT be represented or certified as human-verified ground truth** until independent software developers review, correct, and formally sign off on each record.

This document establishes the definitive human-annotation protocol, schema definitions, labeling criteria, and verification workflows required to transition the provisional corpus into certified ground truth.

---

## 2. Dataset Architecture & Split Integrity

```
E1 Evaluation Corpus (40 Scenarios)
├── Development Split (dev_01 to dev_20): 20 Cases (50%)
│   ├── Used for prompt engineering, schema tuning, few-shot examples
│   └── Multi-language: Python (15), Dart (2), TypeScript (2), YAML (1)
│
└── Held-Out Evaluation Split (eval_01 to eval_20): 20 Cases (50%)
    ├── Strictly quarantined from prompt examples (ZERO LEAKAGE)
    ├── Genuine repository commits (4e5af91, 24a2630, a9d81bb, etc.)
    └── Multi-language: Python (12), Dart (3), TypeScript (3), Go (2)
```

### Prompt-Leakage Prevention Guardrail:
To maintain rigorous statistical validity, **no example from the Held-Out Evaluation Split (`eval_01` through `eval_20`) may ever be included in system prompts, few-shot demonstrations, or context templates**. The benchmark runner strictly validates split boundaries.

---

## 3. Human Annotation Schema Specification

Each record in [`e1_human_review_annotations.json`](file:///c:/Users/savan/install-unotusk/experiments/e1_generative_ie/data/e1_human_review_annotations.json) adheres to the following JSON schema:

```json
{
  "case_id": "eval_01_orchestrator_ports",
  "split": "eval",
  "category": "RealRepo",
  "language": "Python",
  "commit_sha": "4e5af91",
  "commit_message": "fix(orchestrator): extract host port from container port bindings dictionary values",
  "author_timestamp": "2026-10-14T12:00:00+00:00",
  "raw_diff": "diff --git a/apps/api/src/services/orchestrator_service.py ...",
  "annotation_status": "PROVISIONAL_AI_DRAFT",
  "review_metadata": {
    "reviewed_by": "Senior Backend Engineer Name",
    "review_date": "2026-11-06",
    "review_status": "CERTIFIED_HUMAN_GROUND_TRUTH",
    "reviewer_notes": "Verified port extraction loop and service scope."
  },
  "expected_entities": [
    {
      "name": "OrchestratorService",
      "type": "CLASS",
      "evidence_span": "class OrchestratorService",
      "is_supported_by_atom": true
    }
  ],
  "expected_relations": [
    {
      "subject": "OrchestratorService",
      "rel": "CALLS",
      "obj": "port_bindings.values",
      "temporal_attribute": "t_start",
      "evidence_span": "port_bindings.values()",
      "is_supported_by_atom": true
    }
  ],
  "expected_events": [
    {
      "type": "BEHAVIOR_CHANGED",
      "target": "OrchestratorService",
      "trigger_statement": "extract host port from container port bindings",
      "temporal_attribute": "t_obs",
      "arguments": {
        "attribute": "HostPort",
        "container": "port_bindings"
      },
      "evidence_span": "host_port = binding_list[0].get('HostPort')",
      "is_supported_by_atom": false
    }
  ],
  "is_ambiguous": false,
  "is_trivial": false
}
```

---

## 4. Annotation Guidelines for Independent Reviewers

### 4.1 Entity Annotation Guidelines
- **`name`**: Exact identifier name as declared in the source code (case-sensitive).
- **`type`**: Must belong to the authorized Code Lane entity vocabulary:
  `SERVICE | MODULE | FILE | CLASS | FUNCTION | API | DEPENDENCY | CONFIG_PARAM | TEST | DATASTORE | OTHER`.
- **`evidence_span`**: Exact substring snippet from the diff or hunk header proving the entity's existence.
- **`is_supported_by_atom`**: Set to `true` if this entity is a syntactic code symbol (class, function, file, import, config key) that a Tree-sitter AST parser or regex can extract deterministically. Set to `false` for conceptual entities implied by the commit message.

### 4.2 Relation Annotation Guidelines
- **`subject` & `obj`**: Canonical names of the participant entities.
- **`rel`**: Must belong to the authorized relation vocabulary:
  `CALLS | IMPORTS | DEFINES | INHERITS | MUTATES | CONFIGURES | VALIDATES | RAISES | REFERENCES | DEPENDS_ON | REPLACES | SUPERSEDES | TESTS`.
- **`temporal_attribute`**:
  - `t_start`: Relationship was introduced or activated in this commit.
  - `t_end`: Relationship was removed, replaced, or ended in this commit.
  - `t_obs`: Static observation timestamp.
- **`is_supported_by_atom`**:
  - `true` for syntactic AST relations: `CALLS`, `IMPORTS`, `DEFINES`, `INHERITS`, `MUTATES`, `CONFIGURES`, `VALIDATES`, `RAISES`.
  - `false` for higher-order semantic relations: `REPLACES`, `SUPERSEDES`, `TESTS`, `DEPENDS_ON`.

### 4.3 Event Annotation Guidelines
- **`type`**: Must belong to the authorized event vocabulary:
  `COMPONENT_INTRODUCED | COMPONENT_MODIFIED | COMPONENT_DELETED | DEPENDENCY_ADDED | DEPENDENCY_REMOVED | API_CHANGED | BEHAVIOR_CHANGED | TEST_MODIFIED | CONFIGURATION_UPDATED | IMPLEMENTATION_DEPRECATED`.
- **`target`**: Primary component or symbol undergoing the state transition.
- **`trigger_statement`**: Natural language clause from the commit message or code annotation explaining the intent.
- **`is_supported_by_atom`**: Always `false` (Track T1 ATOM possesses no event extraction mechanism).

### 4.4 Ambiguity & Trivial Diff Rules
- **Trivial Diffs (`is_trivial = true`):** If a diff contains only whitespace, reformatting, or comment edits without modifying executable logic, reviewers must assert **zero expected entities, relations, and events**. The model is expected to trigger **abstention**.
- **Ambiguous Diffs (`is_ambiguous = true`):** If a diff makes a scalar modification (e.g., `counter = 2`) with an uninformative commit message (e.g., `wip: update stuff`), reviewers must flag the record as ambiguous. The model is expected to mark extractions as `is_uncertain = true` and reduce confidence to $\le 0.40$.

---

## 5. Reviewer Sign-Off Workflow

To certify a test scenario as ground truth:
1. Open [`e1_human_review_annotations.json`](file:///c:/Users/savan/install-unotusk/experiments/e1_generative_ie/data/e1_human_review_annotations.json).
2. Inspect `raw_diff` and `commit_message` against the proposed `expected_entities`, `expected_relations`, and `expected_events`.
3. Add missing items or remove hallucinated items.
4. Set `review_metadata.reviewed_by` to the engineer's name.
5. Set `review_metadata.review_date` to the completion date (ISO format).
6. Set `review_metadata.review_status` to `"CERTIFIED_HUMAN_GROUND_TRUTH"`.
7. Set `annotation_status` to `"CERTIFIED_HUMAN_GROUND_TRUTH"`.
8. Once all 40 scenarios are certified, the benchmark runner can be executed in certified mode.
