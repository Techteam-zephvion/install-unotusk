# E1 — Integration Readiness Proposal & Production Graduation Roadmap

**Repository:** `Techteam-zephvion/install-unotusk`  
**Track:** E1 — Generative Information Extraction  
**Authoritative Architectural Specification:** `AI_PIE_Architecture_V1_Elite.pdf` — Section 24 (E1 Post-V1 Backlog) & Sections 6, 7, 10, 23, 25  
**Current Status Classification:** **`BLOCKED — LIVE MODEL VALIDATION PENDING`**  
**Date:** November 6, 2026  

---

## 1. Executive Summary & Readiness Verdict

This proposal defines the architectural blueprint and operational criteria for graduating Track E1 from the isolated experimental namespace (`experiments/e1_generative_ie/`) into the core Unotusk AI-PIE Code Lane ingestion service (`apps/api/src/services/`).

### Current Production Readiness Verdict:
$$\mathbf{NOT\ READY\ FOR\ PRODUCTION\ DEPLOYMENT\ TODAY}$$

### Justification:
1. **Live Model Validation Blocked:** API credentials (`GROQ_API_KEY`, `ANTHROPIC_API_KEY`) are unprovisioned in the deployment environment. Live model telemetry and latency budgets on production hardware remain unbenchmarked.
2. **Ground-Truth Sign-Off Pending:** The 40-scenario benchmark dataset contains provisional AI draft labels that must undergo independent human developer review before serving as formal production gates.
3. **Safety Scope Lock:** In accordance with `AGENTS.md` and the MVP charter, production database schemas, Alembic migrations, and feature flags are strictly locked during this research phase.

However, the **algorithmic architecture, schemas, grounding gates, and T1–T4 integration contracts are 100% designed, verified by 14 unit tests, and ready for Stage 3 execution upon credential provisioning.**

---

## 2. Proposed Production Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Proposed Production Ingestion Pipeline                    │
└─────────────────────────────────────────────────────────────────────────────┘

                  ┌──────────────────────────────────────────┐
                  │       Git Commit & Unified Diff          │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │       Track T1 ATOM (Synchronous)        │
                  │   - Unified hunk decomposition           │
                  │   - Innermost AST symbol correlation     │
                  │   - Syntactic facts & relations          │
                  │   - Fast-path storage in PostgreSQL 16   │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │ Feature Flag: E1_GENERATIVE_IE_ENABLED?  │
                  └────────────┬─────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               │ Disabled (Default: False)     │ Enabled (Optional)
               ▼                               ▼
     ┌───────────────────┐          ┌──────────────────────────────────────────┐
     │ Pipeline Complete │          │ Asynchronous E1 Worker Task              │
     │ Zero LLM Overhead │          │ - Context Assembly (Diff + Commit Msg)   │
     │ Fast Ingestion    │          │ - Multi-Provider LLM Call (Groq/Claude)  │
     └───────────────────┘          │ - Three-Layer Grounding Gate             │
                                    │ - JSONB metadata write-back              │
                                    └──────────────────┬───────────────────────┘
                                                       │
                               ┌───────────────────────┴───────────────────────┐
                               ▼                                               ▼
                    ┌─────────────────────┐                         ┌─────────────────────┐
                    │ T2 EvoKG Completion │                         │ T4 STAR-RAG Vector  │
                    │ Ingests REPLACES &  │                         │ Ingests semantic    │
                    │ DEPENDS_ON edges    │                         │ event descriptions  │
                    └─────────────────────┘                         └─────────────────────┘
```

### Key Architectural Tenets:
1. **Non-Blocking Asynchronous Execution:** E1 generative extraction must run as an asynchronous Redis background worker job (`services/workers/worker.py`), decoupled from the synchronous Git commit ingestion path. ATOM completes instantly ($< 2\text{ ms}$), ensuring repository indexing is never blocked by external LLM API latency.
2. **Deterministic Fallback Gate:** If the LLM provider times out ($> 10\text{s}$) or encounters rate limits (HTTP 429), the worker gracefully records a warning in ingestion metadata and preserves the deterministic ATOM facts without rolling back the commit.
3. **Additive Relational Storage:** E1 output will be stored in a dedicated JSONB column on `code_chunks`:
   ```sql
   ALTER TABLE code_chunks ADD COLUMN generative_metadata JSONB DEFAULT '{}'::jsonb;
   ```
   No existing primary keys, foreign keys, or vector index columns are modified.

---

## 3. T1–T4 Cross-Track Compatibility Guarantees

| Subsystem | Integration Interface | Operational Impact | Backward Compatibility |
| :--- | :--- | :--- | :---: |
| **Track T1 (ATOM)** | Ingests `AtomicCodeChange` records | Enriches chunks with causal rationale | **100% Preserved** (Zero modification to ATOM) |
| **Track T2 (EvoKG)** | Routes `REPLACES` & `DEPENDS_ON` edges | Enriches temporal reasoning graph | **100% Preserved** (Falls back to canonical types) |
| **Track T3 (MemoTime)** | Provides architectural intent context | Enhances Tree-of-Thought query parsing | **100% Preserved** (Read-only contextual enrichment)|
| **Track T4 (STAR-RAG)** | Embeds high-level software events | Boosts semantic query recall | **100% Preserved** (Separate vector space partition) |

---

## 4. Feature Flag Specification

To maintain complete production safety, E1 must be governed by an explicit, off-by-default feature flag:

```python
# In apps/api/src/config/settings.py
E1_GENERATIVE_IE_ENABLED: bool = False
E1_GENERATIVE_IE_PROVIDER: str = "groq"  # "groq" | "claude" | "offline"
E1_GENERATIVE_IE_TIMEOUT_SECONDS: int = 15
E1_GROUNDING_STRICT_MODE: bool = True
```

- When `E1_GENERATIVE_IE_ENABLED = False`, the system behaves identically to current production V1 Code Lane. Zero LLM API calls are made during ingestion.
- When enabled, only validated, grounded facts are written back to `code_chunks.generative_metadata`.

---

## 5. Stage 3 Production Graduation Acceptance Criteria Checklist

Before E1 can be merged into `main` and enabled in production, the following 6 gates must be satisfied:

- [ ] **Gate 1 — Credential Provisioning:** `GROQ_API_KEY` or `ANTHROPIC_API_KEY` configured in production environment.
- [ ] **Gate 2 — Live Benchmark Execution:** Real-model evaluation executed on the 40-scenario corpus confirming:
  - Named Entity F1 $\ge 0.70$
  - Relation Extraction F1 $\ge 0.60$
  - Event Extraction F1 $\ge 0.70$
  - P95 latency $< 4.0\text{ seconds}$ per commit.
- [ ] **Gate 3 — Independent Human Sign-Off:** All 40 scenarios in [`e1_human_review_annotations.json`](file:///c:/Users/savan/install-unotusk/experiments/e1_generative_ie/data/e1_human_review_annotations.json) certified by software engineers.
- [ ] **Gate 4 — Non-Destructive Alembic Migration:** Add `generative_metadata JSONB` column to `code_chunks` with tested bidirectional downgrade.
- [ ] **Gate 5 — Unified Pytest Suite:** All 356+ existing backend unit, integration, and security tests continue passing without regression.
- [ ] **Gate 6 — Architectural Governance Sign-Off:** Formal compliance sign-off under Section 25 of `AI_PIE_Architecture_V1_Elite.pdf`.
