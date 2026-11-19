# UNOTUSK V1 — Technical Functionality & Test Results Audit

**Audit Date:** 2026-11-03  
**Auditor:** Senior Software Architect & Technical Audit Lead  
**Evaluation Scope:** ELEVATE NxT TRL 7 Compliance — Task 4: Verify Technical Functionality  

---

## 1. Executive Summary & Audit Scorecard

This audit provides an unsparing technical evaluation of the 8 core intelligence components comprising **UNOTUSK V1**. Each component has been audited at the source code level, tested against automated test suites, and evaluated for production readiness.

### Component Implementation Scorecard

```
+------------------------------------------------------+-------------------------+------------------------+
| Component / Capability                               | Implementation Status   | Test Verification      |
+------------------------------------------------------+-------------------------+------------------------+
| 1. MultiSignalRanker / composite_score               | IMPLEMENTED             | 100% Passed (Pytest)   |
| 2. Decision and Fact Extraction                      | IMPLEMENTED             | 100% Passed (Pytest)   |
| 3. TemporalEngine / GraphService                     | IMPLEMENTED             | 100% Passed (Pytest)   |
| 4. Incremental Knowledge Updates                     | IMPLEMENTED             | 100% Passed (Pytest)   |
| 5. Dependency and Risk Analysis                      | IMPLEMENTED (10 Engine) | 100% Passed (Pytest)   |
| 6. Evidence-Grounded Answers                         | IMPLEMENTED             | 100% Passed (Pytest)   |
| 7. Citation Verification                             | PARTIALLY IMPLEMENTED   | Verified at Retrieval  |
| 8. Feedback Propagation Rate (FPR) Instrumentation   | NOT IMPLEMENTED (Mock)  | No Backend Engine      |
+------------------------------------------------------+-------------------------+------------------------+
```

---

## 2. Automated Test Suite Execution Results

All automated test suites across the backend and frontend desktop clients were executed directly in the local operational environment.

### 2.1 Backend Pytest Suite (`apps/api/`)
- **Execution Command:** `apps/api/.venv/bin/pytest -v`
- **Result:** **356 passed, 1 skipped, 0 failed** in 615.28s (10m 15s)
- **Database Backend:** PostgreSQL 16 (`pgvector`) on `localhost:5432/unotusk_test`
- **Coverage Highlights:**
  - `tests/unit/test_context_engine.py`: Multi-signal candidate ranking, keyword weighting, and noise pruning.
  - `tests/unit/test_code_atom_fact_decomposition.py`: Rule-based code fact decomposition and SHA-256 fingerprinting.
  - `tests/unit/test_code_atom_temporal_relations.py`: Temporal query intent classification and commit supersession.
  - `tests/unit/test_discovery_engine.py`: Proactive discovery analyzers (circular dependencies, coupling, test gaps).
  - `tests/unit/test_auth_domain_validation.py`: Single-tenant authentication, JWT validation, and RBAC scoping.
  - `tests/api/`: REST endpoint contracts for auth, projects, repositories, snapshots, discoveries, grounded ask, and customer knowledge.
  - *Note on Skipped Test:* 1 test (`test_worker_pipeline_execution`) skipped due to standalone Redis worker daemon isolation.

### 2.2 Flutter Desktop Employee Client (`app/`)
- **Execution Command:** `cd app && PATH=/home/devils/flutter/bin:$PATH flutter test`
- **Result:** **85 passed, 0 failed** in 4.8s
- **Coverage:** Navigation shell, Warm Dark theme tokens, all 9 workspace tabs (`AskTab`, `DiscoveriesTab`, `OntologyTab`, `SpecHistoryTab`, `OverviewTab`, `FilesTab`, `KnowledgeTab`, `IngestionFeedTab`, `ArchitectureTab`), and state controllers.

### 2.3 Flutter Server Setup Wizard (`setup_app/`)
- **Execution Command:** `cd setup_app && PATH=/home/devils/flutter/bin:$PATH flutter test`
- **Result:** **47 passed, 0 failed** in 2.9s
- **Coverage:** Hardware diagnostics, Docker engine connectivity, port availability probes, container health polling, and deployment workflow navigation.

### 2.4 Code Quality & Static Analysis
- **Python Backend Linter:** `apps/api/.venv/bin/ruff check apps/api/ tests/` → **`All checks passed!`** (0 lint violations, 0 formatting errors).
- **Client Desktop Analyzer:** `cd app && flutter analyze` → **`No issues found!`** (0 issues).
- **Server Setup App Analyzer:** `cd setup_app && flutter analyze` → **`No issues found!`** (0 issues).

**Total Verified Automated Tests:** **488 tests passing with zero failures.**

---

## 3. Deep-Dive Audit of Specific Components

### 3.1 MultiSignalRanker / composite_score
- **Status:** **IMPLEMENTED**
- **Code Reference:** [`apps/api/src/services/context_engine/ranker.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/context_engine/ranker.py#L15-L244)
- **Implementation Architecture:**
  - Implements candidate deduplication with provenance and shortest-hop preservation.
  - Resolves temporal supersession across candidates before score computation.
  - Multi-signal composite weighting formula:
    $$\text{Score} = w_{\text{sym}}(1.5) + w_{\text{file}}(1.3) + w_{\text{content}}(1.1) + w_{\text{vec}}(1.4) + w_{\text{sem}}(1.2) + w_{\text{dep}}(0.9) + w_{\text{graph}}(0.7 \times 0.75^{\text{hop}-2})$$
  - Keyword density boosts in symbol name (+0.8), commit message (+0.5), and body text (+0.3).
  - Temporal query intent adjustments: demotes superseded (*0.4) and deleted (*0.15) code for current-state queries; promotes commit evidence (+0.6) and precursor diffs (+0.4) for historical evolution queries.
  - Normalized score capped at 1.0, with noise threshold filtering ($\ge 0.20$) and a minimum candidate floor guarantee (at least 3 candidates retained).
- **Known Limitations:** Vector similarity weight defaults to lexical/BM25 rank if external embeddings or Ollama are not active.

### 3.2 Decision and Fact Extraction
- **Status:** **IMPLEMENTED**
- **Code Reference:** [`apps/api/src/services/code_atom/fact_decomposer.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/code_atom/fact_decomposer.py#L1-L150), [`apps/api/src/services/knowledge_service.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/knowledge_service.py)
- **Implementation Architecture:**
  - Regex and AST decomposition into `SemanticCodeFact` with typed categories: `GUARD_CONDITION`, `METHOD_CALL`, `IMPORT_DEPENDENCY`, `ERROR_HANDLING`, `STATE_MUTATION`, `CONFIG_SETTING`.
  - Deterministic SHA-256 fingerprinting: `hashlib.sha256(f"{commit}:{path}:{symbol}:{statement}:{type}")`.
  - Anti-hallucination token ground-truth validator ([`validate_grounded_tokens`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/code_atom/fact_decomposer.py#L67-L80)) verifying that extracted identifier tokens exist in the underlying diff or symbol table.
  - Customer knowledge management: CRUD service for ADRs, architectural decisions, and operational constraints with project and organization isolation.
- **Known Limitations:** AST rules cover Python, TypeScript/JavaScript, and Go. Non-standard domain-specific languages (DSLs) rely on LLM fallback extraction.

### 3.3 TemporalEngine / GraphService
- **Status:** **IMPLEMENTED**
- **Code Reference:** [`apps/api/src/services/code_atom/temporal.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/code_atom/temporal.py), [`apps/api/src/services/graph_service.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/graph_service.py)
- **Implementation Architecture:**
  - `classify_temporal_intent()`: Regex patterns and temporal token matching (`evolution`, `history`, `timeline`, `deprecated`, `superseded`) to identify time-travel query intent.
  - `resolve_temporal_supersession()`: Compares code changes across chronological commit order to tag precursor modifications as superseded or deleted.
  - `GraphService`: Traverses relational entities (Services → Repositories → Files → Symbols → Dependencies) to emit typed graph nodes and edges (`CONTAINS`, `CALLS`, `IMPORTS`, `DEFINES`, `DEPENDS_ON`).
- **Known Limitations:** Interactive graph expansion is capped at 2 hops to guarantee sub-second REST response times.

### 3.4 Incremental Knowledge Updates
- **Status:** **IMPLEMENTED**
- **Code Reference:** [`apps/api/src/services/code_atom/git_extractor.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/code_atom/git_extractor.py#L118-L220), [`apps/api/src/services/ingestion_service.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/ingestion_service.py)
- **Implementation Architecture:**
  - `extract_incremental_commit_artifacts()`: Accepts `base_commit_sha` and `target_commit_sha`. Queries `git rev-list --reverse base..target` to extract only newly introduced commits and patches.
  - Generates new snapshots and code chunks while marking prior versions as superseded, eliminating the need to re-parse unchanged repository files.
- **Known Limitations:** Requires access to a local Git object repository; shallow clones without commit history must be un-shallowed before incremental diffs can be calculated.

### 3.5 Dependency and Risk Analysis
- **Status:** **IMPLEMENTED (10 Specialized Analyzers)**
- **Code Reference:** [`apps/api/src/services/discovery_engine/engine.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/discovery_engine/engine.py)
- **Analyzer Inventory:**
  1. `circular_dependency_analyzer.py`: Detects circular import cycles across packages using Tarjan's strongly connected components algorithm.
  2. `coupling_analyzer.py`: Identifies high afferent/efferent coupling and structural bottlenecks.
  3. `architecture_analyzer.py`: Enforces layer boundary rules and detects architectural violations.
  4. `security_analyzer.py`: Flags hardcoded secrets, unsafe deserialization, and dangerous standard library calls.
  5. `test_gap_analyzer.py`: Identifies mission-critical symbols lacking corresponding unit or integration tests.
  6. `change_risk_analyzer.py`: Evaluates commit churn rate and high-risk modification frequency.
  7. `documentation_gap_analyzer.py`: Detects undocumented public APIs and missing docstrings.
  8. `duplication_analyzer.py`: Flags near-identical code blocks across files.
  9. `legacy_analyzer.py`: Highlights deprecated runtime APIs and obsolete dependencies.
  10. `unused_code_analyzer.py`: Identifies orphaned functions and dead code paths.
- **Validation Scale:** Successfully triaged 2,704 discoveries in `pallets/flask` and 647 in `psf/requests`.

### 3.6 Evidence-Grounded Answers
- **Status:** **IMPLEMENTED**
- **Code Reference:** [`apps/api/src/services/context_engine/engine.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/context_engine/engine.py#L18-L130), [`apps/api/src/services/llm/groq.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/llm/groq.py), [`apps/api/src/services/llm/claude.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/llm/claude.py)
- **Implementation Architecture:**
  - Executes full multi-signal query pipeline: Query Analysis → Retrieval → Graph Expansion → Multi-Signal Ranking → Context Budgeting → LLM Synthesis.
  - System prompt ([`system_prompt.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/llm/system_prompt.py)) enforces four epistemic classes: `OBSERVED` (direct code facts), `CUSTOMER` (user-stated intent), `DERIVED` (inferences), and `RECOMMENDED` (actionable advice).
  - Deterministic offline synthesizer fallback (`_generate_offline_grounded_answer` in `groq.py` and `claude.py`) guarantees reproducible, hallucination-free answers even when cloud LLM APIs are unreachable or unconfigured.

### 3.7 Citation Verification
- **Status:** **PARTIALLY IMPLEMENTED**
- **Code Reference:** [`apps/api/src/services/context_engine/assembler.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/context_engine/assembler.py), [`apps/api/src/services/code_atom/fact_decomposer.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/code_atom/fact_decomposer.py#L67-L80)
- **Current Capability:**
  - Retrieved evidence items are tagged with exact file paths, line ranges, and relevance scores.
  - Extraction-time token validation prevents LLM hallucinations of non-existent methods during atomic fact creation.
  - Prompt instructions require the LLM to cite exact file paths and line numbers.
- **Audit Deficiencies & Gaps:**
  - **Absence of Post-Synthesis Mechanical Citation Verification:** The engine does not run a post-generation AST/regex parser on the generated markdown text to confirm that every file path and line number cited by the LLM exists in the database.
  - Citation accuracy depends on LLM adherence to prompt directives.

### 3.8 Feedback Propagation Rate (FPR) Instrumentation
- **Status:** **NOT IMPLEMENTED (UI Presentation Mock Only)**
- **Code Reference:** [`app/lib/features/workspace/presentation/tabs/spec_history_tab.dart`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/spec_history_tab.dart#L17), [`app/lib/features/workspace/presentation/tabs/ask_tab.dart`](file:///home/devils/PRO/Unotusk-MVP/app/lib/features/workspace/presentation/tabs/ask_tab.dart#L360-L361)
- **Audit Findings:**
  - All FPR figures displayed in the desktop client (`fprDelta: 0.08`, `fpr: 0.88`, `FPR +0.08 over past 30 days`) are **hardcoded mock literals** inside the Flutter UI code.
  - The UI even conflates the terms *"False Positive Rate"* and *"Feedback Propagation Rate"* interchangeably.
  - **There is zero backend instrumentation, database schema, or telemetry pipeline to calculate or measure Feedback Propagation Rate over time.**
- **Mandatory Audit Ruling:**
  > [!CAUTION]
  > **Any claim that UNOTUSK has achieved an FPR > 0.60 is completely unsubstantiated and factually incorrect.**
  > No longitudinal production measurements exist. The team must not cite FPR metrics in grant applications or investor decks until longitudinal measurement infrastructure is built and calibrated against production customer repositories.
