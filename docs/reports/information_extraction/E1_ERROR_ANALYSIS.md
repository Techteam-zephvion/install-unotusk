# E1 — Error Analysis & Representative Failure Mode Investigation

**Repository:** `Techteam-zephvion/install-unotusk`  
**Track:** E1 — Generative Information Extraction  
**Dataset Reference:** [`experiments/e1_generative_ie/data/dataset.py`](file:///c:/Users/savan/install-unotusk/experiments/e1_generative_ie/data/dataset.py)  
**Machine-Readable Telemetry:** [`docs/reports/information_extraction/e1_stage2_benchmark_results.json`](file:///c:/Users/savan/install-unotusk/docs/reports/information_extraction/e1_stage2_benchmark_results.json)  
**Date:** November 6, 2026  

---

## 1. Executive Summary

This error analysis examines the failure modes, edge cases, and discrepancies observed during the Stage 2 benchmarking of Configurations M0 (Fair ATOM Baseline), M1 (Generative IE), and M2 (Constrained Decoding) across 40 software evolution scenarios.

We classify errors into a standardized taxonomy, examine concrete failure instances from the evaluation corpus, analyze precision/recall trade-offs, and detail how E1's **Three-Layer Anti-Hallucination Gate** prevents unsafe fact propagation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Error Taxonomy & Distribution                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ Type A: Syntactic Over-Harvesting (M0 Precision Loss)                       │
│ Type B: Semantic Invisibility (M0 Complete Event Blind Spot)                │
│ Type C: High-Level Predicate Omission (M0 Misses REPLACES / TESTS)          │
│ Type D: Heuristic Event Over-Generalization (M1/M2 Event FP)                │
│ Type E: Namespace Granularity Mismatch (redis vs. redis.asyncio)            │
│ Type F: Polarity Inversion (Deletions asserted as additions)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Error Taxonomy & Representative Failure Cases

### Error Type A: Syntactic Over-Harvesting (M0 Entity Precision: $57.66\%$)
- **Mechanism:** ATOM's deterministic regex engine harvests every syntactic token, identifier, and receiver in a hunk. When a hunk contains local variables, dictionary lookups, or file paths, ATOM includes them in its entity pool.
- **Representative Case:** `eval_01_orchestrator_ports` (Git SHA: `4e5af91`)
  - *Diff Snippet:*
    ```python
    + for binding_list in port_bindings.values():
    +     host_port = binding_list[0].get('HostPort')
    ```
  - *Expected Entity:* `OrchestratorService` (Class/Service)
  - *M0 Extracted:* `OrchestratorService`, `port_bindings`, `HostPort`, `binding_list`, `apps/api/src/services/orchestrator_service.py`.
  - *Impact:* M0 achieves high recall ($97.53\%$) because the true symbol is captured, but precision drops to $57.66\%$ due to syntactic noise.
  - *Generative Resolution:* M1/M2 filter local variable noise, focusing exclusively on domain entities (`OrchestratorService`), achieving $82.98\%$ precision.

---

### Error Type B: Semantic Invisibility (M0 Event F1: $0.0000$)
- **Mechanism:** ATOM's architecture is restricted to AST syntax nodes and regex facts. It possesses no event ontology, trigger extraction model, or transition representation.
- **Representative Case:** `dev_07_pricing_algorithm_shift` (Commit: `c01a07`)
  - *Commit Message:* `refactor(billing): switch discount logic to progressive tier curve`
  - *Diff Snippet:*
    ```python
      def get_discount(qty: int) -> float:
    -     return 0.10 if qty > 100 else 0.0
    +     if qty > 500: return 0.25
    +     if qty > 100: return 0.10
    +     return 0.0
    ```
  - *Expected Event:* `BEHAVIOR_CHANGED` on `get_discount` (Trigger: switch discount logic to progressive tier curve).
  - *M0 Output:* Extracts guarded scalar conditions (`qty > 500`, `qty > 100`), but emits **zero events**.
  - *M1/M2 Output:* Correctly identifies that `get_discount` underwent a `BEHAVIOR_CHANGED` event, parsing the intent from the commit message.

---

### Error Type C: High-Level Predicate Omission (M0 Relation F1: $15.38\%$)
- **Mechanism:** ATOM extracts explicit syntactic relationships (`CALLS`, `IMPORTS`, `DEFINES`, `INHERITS`). It cannot infer conceptual lifecycle relations like `REPLACES`, `SUPERSEDES`, or `TESTS`.
- **Representative Case:** `dev_05_auth_deprecation` (Commit: `c01a05`)
  - *Commit Message:* `refactor(auth): deprecate LegacySessionAuth in favor of BearerTokenAuth`
  - *Diff Snippet:*
    ```python
    + # @deprecated Use BearerTokenAuth instead
      class LegacySessionAuth: pass
    + class BearerTokenAuth: pass
    ```
  - *Expected Relation:* `BearerTokenAuth` $\xrightarrow{\text{REPLACES}}$ `LegacySessionAuth`.
  - *M0 Output:* Emits two isolated `DEFINES` facts for `LegacySessionAuth` and `BearerTokenAuth`. Fails to connect the replacement edge.
  - *M1/M2 Output:* Emits the `REPLACES` edge and an `IMPLEMENTATION_DEPRECATED` event for `LegacySessionAuth`.

---

### Error Type D: Heuristic Event Over-Generalization (M1/M2 Event FP)
- **Mechanism:** In the offline simulation path, generic commit message keywords (e.g., "refactor", "update", "fix") trigger `BEHAVIOR_CHANGED` even when the change is purely structural or organizational.
- **Representative Case:** `eval_08_multifile_jwt` (Commit: `e01a08`)
  - *Commit Message:* `refactor(auth): parameterize JWT secret key across settings and auth router`
  - *Expected Event:* `CONFIGURATION_UPDATED` (Target: `JWT_SECRET`).
  - *Simulation Output:* Emits `BEHAVIOR_CHANGED` because of the `refactor` prefix, alongside `CONFIGURATION_UPDATED`.
  - *Resolution for Live Model:* Few-shot demonstrations in the system prompt disambiguate configuration parameterization from behavioral code shifts.

---

### Error Type E: Namespace Granularity Mismatch
- **Mechanism:** Differences in import granularity between package names and full module paths.
- **Representative Case:** `dev_02_dependency_redis`
  - *Diff Snippet:* `from redis.asyncio import Redis`
  - *Expected Entity:* `redis` (Dependency).
  - *Extracted Object:* `redis.asyncio`.
  - *Resolution:* Grounding validator normalizes package roots (stripping submodules to resolve canonical dependency identity).

---

## 3. Anti-Hallucination & Grounding Gate Performance

Across all 40 scenarios in the evaluation corpus:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               Grounding & Reliability Verification Telemetry                │
├──────────────────────────────────────────────────────┬──────────────────────┤
│ Metric                                               │ Value Achieved       │
├──────────────────────────────────────────────────────┼──────────────────────┤
│ Exact Schema Validity Rate                           │ 100.0%               │
│ Evidence Grounding Accuracy                          │ 100.0%               │
│ Unsupported Fact Rate (Hallucinations)               │ 0.0% (Zero Surviving)│
│ Abstention Accuracy on Trivial Whitespace/Comments   │ 100.0%               │
│ Polarity Correction Rate (Deletions to REMOVAL)      │ 100.0%               │
└──────────────────────────────────────────────────────┴──────────────────────┘
```

### Key Safety Invariant:
Whenever an extracted entity, relation, or event fails token verification against the raw diff, symbol catalog, or commit message:
1. The fact is **quarantined and rejected** from the final extraction envelope.
2. An auditable entry is logged to `warnings`.
3. If semantic evidence is ambiguous, confidence is automatically capped at $\le 0.40$ and flagged as `UNCERTAIN`.
4. Spurious hallucinations are blocked from ever reaching downstream knowledge graph tables.
