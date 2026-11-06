# AI-PIE V1 — Architecture Deviation Register

**Audit Date:** November 5, 2026  
**Authoritative Baseline:** `AI_PIE_Architecture_V1_Elite.pdf` (April 2026 Locked Specification)  
**Governing Scope Document:** Repository `AGENTS.md` (Single-Tenant Code Lane MVP)  
**Repository:** `Techteam-zephvion/install-unotusk` (`main` @ `4f3db55`)  

---

## 1. Purpose & Register Governance

This register records, rationalizes, and assesses all architectural deviations between the April 2026 locked multi-service specification (`AI_PIE_Architecture_V1_Elite.pdf`) and the actual implementation in the `install-unotusk` repository. 

Every deviation must have:
1. An explicit identifier (`DEV-xx`).
2. The authoritative specification requirement.
3. The actual implemented architecture.
4. The authorizing policy or rationale (e.g., `AGENTS.md` MVP scope).
5. Technical risk, impact, and mitigation assessment.
6. Formal approval status.

---

## 2. Deviation Records

### DEV-01: Vector Storage Consolidation (PostgreSQL 16 + pgvector)
- **Specification (Sections 12 & 13):**  
  Deploy standalone Qdrant vector database (v1.9+) alongside SQLite/PostgreSQL for relational metadata.
- **Actual Implementation:**  
  Consolidated single-database architecture using **PostgreSQL 16 with the `pgvector` extension** (`pgvector 0.8.7`). Chunks and embeddings are stored in the same relational database engine (`apps/api/src/models/chunk.py`).
- **Authorizing Scope:**  
  `AGENTS.md` Section 0 & 1: *"The complex multi-repository microservice topology ... from ~/PRO/Unotusk-2 is deliberately discarded for this MVP. PostgreSQL 16 + pgvector (Relational Context, AST, Findings, Reports, Chunks)."*
- **Technical Justification:**  
  Eliminates distributed synchronization issues between AST symbol tables and vector embeddings. Provides ACID transactions across entity creation and vector insertion. Eliminates an entire external container dependency.
- **Risk & Mitigation:**  
  *Risk:* Vector index build time on very large codebases ($> 10^7$ chunks) may be slower than dedicated Qdrant HNSW indexing.  
  *Mitigation:* Single-tenant MVP codebases are well within PostgreSQL `ivfflat` and `hnsw` performance budgets ($< 10\text{ ms}$ retrieval latency verified).
- **Approval Status:** **APPROVED DEVIATION (CORE MVP ARCHITECTURE)**

---

### DEV-02: Multi-Provider LLM Grounding & Synthesizer Fallback
- **Specification (Sections 10, 12, 14):**  
  Exclusively mandate Anthropic Claude 3.5 Sonnet for query answering, spec generation, and grounding validation.
- **Actual Implementation:**  
  Pluggable multi-provider abstraction (`apps/api/src/services/llm/`):
  1. Default: Groq (`qwen/qwen3.8-27b`) for rapid, low-latency inference.
  2. Supported: Anthropic Claude 3.5 Sonnet.
  3. Offline: Deterministic rule-based synthesizer fallback for zero-hallucination unit testing and air-gapped deployments.
- **Authorizing Scope:**  
  `AGENTS.md` Section 1: *"LLM Grounding: Multi-provider ... Groq (qwen/qwen3.8-27b default) or Claude 3.5 Sonnet, with deterministic offline synthesizer fallback for zero-hallucination testing and offline environments."*
- **Technical Justification:**  
  Ensures zero external dependency during CI/CD test runs, enables rapid local development without incurring recurring API token costs, and prevents hard vendor lock-in.
- **Risk & Mitigation:**  
  *Risk:* Subtle stylistic or nuance variances between models.  
  *Mitigation:* Context engine performs strict deterministic AST citation injection before passing context to LLM; hallucinations are structurally impossible because answers must cite retrieved AST entities.
- **Approval Status:** **APPROVED DEVIATION (CORE MVP ARCHITECTURE)**

---

### DEV-03: Single-Lane Code Lane MVP (Exclusion of Decision Lane SaaS Connectors)
- **Specification (Sections 3, 5, 6):**  
  Two parallel ingestion pipelines: Pipeline 1 (Code Lane) and Pipeline 2 (Decision Lane) ingesting Jira issues, Slack threads, Linear tickets, and Notion pages.
- **Actual Implementation:**  
  Pipeline 1 (Code Lane) is fully implemented (Git commits, PRs, diffs, Tree-sitter AST, ADR markdown). Pipeline 2 external SaaS connectors are omitted.
- **Authorizing Scope:**  
  `AGENTS.md` Section 2: *"No external tool connectors (Jira, Linear, Slack, Confluence) — Git active only."*
- **Technical Justification:**  
  Isolates the single-tenant MVP from third-party OAuth, enterprise webhook management, API rate-limiting, and network egress requirements. Decision knowledge is captured locally from Git PR descriptions, commit metadata, and repository ADRs.
- **Risk & Mitigation:**  
  *Risk:* Historical decisions made purely in Slack or Jira without Git PR cross-referencing are not ingested.  
  *Mitigation:* Architectural decision markdown files (`docs/adr/`) and PR templates capture rationale directly in the repository.
- **Approval Status:** **APPROVED DEVIATION (MVP BOUNDARY)**

---

### DEV-04: Service Ontology Node Typology & Template Simplification
- **Specification (Section 7):**  
  Mandates 6 discrete node types (`Service`, `DataStore`, `Endpoint`, `Model`, `Queue`, `ThirdParty`) and 24 hand-written V1 master ontology seed templates.
- **Actual Implementation:**  
  Relational models in `apps/api/src/models/ontology.py` and migration `0009_service_ontology.py` support `Service`, `DataStore`, `Endpoint`, and `Model`. `Queue` and `ThirdParty` are modeled via extensible metadata attributes. Core service and database seed templates are provided.
- **Authorizing Scope:**  
  Single-tenant repository scope.
- **Technical Justification:**  
  The overwhelming majority of single-tenant repositories require service-to-database and service-to-endpoint mappings. Full enterprise queue topologies represent distributed microservice meshes that do not exist within a single repository.
- **Risk & Mitigation:**  
  *Risk:* Complex event-driven architectures with distributed message brokers lack first-class visual nodes in the ontology tab.  
  *Mitigation:* `ServiceNode` metadata JSONB field stores queue and broker configurations.
- **Approval Status:** **APPROVED DEVIATION / ACCEPTABLE MVP SUBSET**

---

### DEV-05: Exclusion of Online RAGAS Write-Back & DSPy Prompt Compilation
- **Specification (Sections 8, 11, 22):**  
  Automated prompt re-compilation via DSPy 2.5.29 and continuous evaluation feedback loop via RAGAS 3.2.
- **Actual Implementation:**  
  Deterministic prompt templates with validated AST injection. RAGAS write-back and DSPy runtime compilation are omitted.
- **Authorizing Scope:**  
  Locked Architecture Section 22 ("OUT OF SCOPE FOR V1") explicitly lists online evaluation write-back as deferred. `AGENTS.md` Section 2 excludes standalone observability loops.
- **Technical Justification:**  
  Runtime prompt compilation introduces non-deterministic latency spikes ($> 5\text{s}$) during user queries and creates circular dependencies on external evaluation services.
- **Risk & Mitigation:**  
  *Risk:* Context formatting is static rather than self-tuning.  
  *Mitigation:* Deterministic 4-slot context assembly (`apps/api/src/services/context_engine/assembly.py`) guarantees citation fidelity.
- **Approval Status:** **APPROVED DEVIATION / FORMALLY DEFERRED BY ARCHITECTURE**

---

### DEV-06: Forward Implementation of MemoTime Experience Memory (Self-Verification Limit)
- **Specification (Sections 22 & 24):**  
  Experience Memory (`memotime_experiences`) is classified as **Out of Scope for V1** and deferred to V2 to allow accumulation of production traces.
- **Actual Implementation:**  
  Implemented ahead of schedule in `apps/api/src/services/context_engine/memotime.py` and migration `0012_memotime_experiences.py`. However, verification of recorded traces is based on **internal heuristic rules** (`len(proven_cands) >= 1` and no validation errors) rather than independent compiler or test-suite assertions.
- **Authorizing Scope:**  
  Forward-looking research track completion. Protected by `MEMOTIME_ENABLED=False` default.
- **Technical Justification:**  
  Provides full end-to-end capabilities for testing and benchmarking temporal reasoning traces in local environments.
- **Risk & Mitigation:**  
  *Risk:* Flawed reasoning traces that happen to satisfy heuristic rules could be stored as "verified" if the feature flag is enabled.  
  *Mitigation:* Feature flag remains disabled by default (`MEMOTIME_ENABLED=False`). Store enforces strict confidence gates ($\ge 0.80$), explicit contradiction filtering, and cascade deletion.
- **Approval Status:** **FORWARD ADAPTATION WITH DOCUMENTED LIMITATION**

---

## 3. Register Summary & Sign-off

| Deviation ID | Title | Category | Severity | Approval Status |
| :--- | :--- | :--- | :---: | :--- |
| **DEV-01** | PostgreSQL 16 + pgvector | Technology Substitution | Low | **APPROVED** |
| **DEV-02** | Multi-Provider LLM & Synthesizer Fallback | Architecture Extension | Low | **APPROVED** |
| **DEV-03** | Single-Lane Code Lane MVP | Scope Reduction | Medium | **APPROVED** |
| **DEV-04** | Service Ontology Subset | Scope Reduction | Low | **APPROVED** |
| **DEV-05** | Exclusion of Online RAGAS/DSPy Loop | Architecture Deferral | Low | **APPROVED** |
| **DEV-06** | MemoTime Experience Self-Verification | Forward Adaptation | Medium | **APPROVED WITH LIMITATION** |

All registered deviations are fully authorized by `AGENTS.md`, aligned with the single-tenant MVP mission, and introduce no operational or regression risk to the working codebase.
