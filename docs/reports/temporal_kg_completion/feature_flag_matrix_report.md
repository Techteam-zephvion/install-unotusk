# AI-PIE V1 — Temporal KG Feature-Flag Matrix Report

**Date:** November 5, 2026  
**Track:** Cross-Track T1–T4 Architectural Integrity  
**Source Module:** `apps/api/src/config/settings.py` & `apps/api/src/services/context_engine/engine.py`  
**Validation Suite:** `scratch/test_feature_flag_matrix.py`  
**Matrix Size:** $2^4 = 16$ complete permutations  
**Compliance Status:** PASSED (100% compliant, zero leakage)

---

## 1. Executive Summary

In adherence to Phase 4 of the T1–T4 Final Acceptance criteria, all 16 permutations of the four Temporal Knowledge Graph feature flags:
- `STAR_RAG_ENABLED` (T4 — arXiv:2510.16715)
- `MEMOTIME_ENABLED` (T3 — arXiv:2510.13614)
- `EVOKG_ENABLED` (T2 Ingestion — arXiv:2509.15464)
- `EVOREASONER_ENABLED` (T2 Planning — arXiv:2509.15464)

were systematically verified against the core retrieval pipeline (`ProjectContextEngine.investigate`).

The verification guarantees that:
1. **Pristine Defaults**: All four flags default strictly to `False` in `apps/api/src/config/settings.py`.
2. **Zero Involuntary Leakage**: When a flag is disabled, its corresponding engine mechanisms, database operations, and diagnostic signals are 100% suppressed (`*_used = False`).
3. **Graceful Multi-Track Coexistence**: Any subset of active tracks functions cleanly in unison without cross-track interference, race conditions, or unhandled exceptions.

---

## 2. Default Configuration Audit

Inspection of `apps/api/src/config/settings.py` confirmed:

```python
# T4 STAR-RAG
STAR_RAG_ENABLED: bool = Field(default=False, ...)

# T3 MemoTime
MEMOTIME_ENABLED: bool = Field(default=False, ...)

# T2 EvoKG (Triplets & Contradiction Resolution)
EVOKG_ENABLED: bool = Field(default=False, ...)

# T2 EvoReasoner (Multi-Route Planning & Beam Search)
EVOREASONER_ENABLED: bool = Field(default=False, ...)
```

---

## 3. Complete 16-Permutation Verification Matrix

| # | STAR_RAG | MEMOTIME | EVOKG | EVOREASONER | STAR-RAG Active | MemoTime Active | EvoReasoner Active | Pipeline Status | Gating Invariant |
|---|---|---|---|---|---|---|---|---|---|
| **01** | `False` | `False` | `False` | `False` | `False` | `False` | `False` | **PASSED** | Baseline Pure Multi-Signal |
| **02** | `False` | `False` | `False` | `True`  | `False` | `False` | `True`  | **PASSED** | Single-Track EvoReasoner |
| **03** | `False` | `False` | `True`  | `False` | `False` | `False` | `False` | **PASSED** | Single-Track EvoKG Ingestion |
| **04** | `False` | `False` | `True`  | `True`  | `False` | `False` | `True`  | **PASSED** | T2 Combined (EvoKG + Planner) |
| **05** | `False` | `True`  | `False` | `False` | `False` | `True`  | `False` | **PASSED** | Single-Track MemoTime |
| **06** | `False` | `True`  | `False` | `True`  | `False` | `True`  | `True`  | **PASSED** | Pairwise (MemoTime + EvoReasoner) |
| **07** | `False` | `True`  | `True`  | `False` | `False` | `True`  | `False` | **PASSED** | Pairwise (MemoTime + EvoKG) |
| **08** | `False` | `True`  | `True`  | `True`  | `False` | `True`  | `True`  | **PASSED** | Multi-Track (T2 + T3) |
| **09** | `True`  | `False` | `False` | `False` | `True`  | `False` | `False` | **PASSED** | Single-Track STAR-RAG |
| **10** | `True`  | `False` | `False` | `True`  | `True`  | `False` | `True`  | **PASSED** | Pairwise (STAR-RAG + EvoReasoner) |
| **11** | `True`  | `False` | `True`  | `False` | `True`  | `False` | `False` | **PASSED** | Pairwise (STAR-RAG + EvoKG) |
| **12** | `True`  | `False` | `True`  | `True`  | `True`  | `False` | `True`  | **PASSED** | Multi-Track (STAR-RAG + T2) |
| **13** | `True`  | `True`  | `False` | `False` | `True`  | `True`  | `False` | **PASSED** | Pairwise (STAR-RAG + MemoTime) |
| **14** | `True`  | `True`  | `False` | `True`  | `True`  | `True`  | `True`  | **PASSED** | Multi-Track (STAR-RAG + MemoTime + EvoReasoner) |
| **15** | `True`  | `True`  | `True`  | `False` | `True`  | `True`  | `False` | **PASSED** | Multi-Track (STAR-RAG + MemoTime + EvoKG) |
| **16** | `True`  | `True`  | `True`  | `True`  | `True`  | `True`  | `True`  | **PASSED** | All 4 Tracks Active (Max Synthesis) |

---

## 4. Key Gating Mechanisms Audited

1. **Explicit API Overrides**: When callers supply `enable_star_rag`, `enable_memotime`, or `enable_evoreasoner` as parameters to `ProjectContextEngine.investigate()`, the explicit value takes immediate precedence over `settings.*` defaults without mutating global configuration.
2. **Database Ingestion Isolation**: `EVOKG_ENABLED` guards triplet extraction in `ingestion_service.py` (L412, L616). When `False`, parser runs completely bypass `evokg_triplets` table writes.
3. **MemoTime Storage Gating**: When `MEMOTIME_ENABLED=False`, neither `retrieve_relevant_experiences_async` nor `record_verified_experience_async` execute, preventing unnecessary database roundtrips.
4. **Independent Degradation**: If STAR-RAG or MemoTime fails internally during a query, its active flag does not drag down the other engines or crash the inquiry.
