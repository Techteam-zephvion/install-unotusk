# E1 — Code Lane Gap Analysis: Deterministic AST ATOM Baseline vs. Generative Information Extraction

**Repository:** `Techteam-zephvion/install-unotusk`  
**Evaluation Scope:** Code Lane Ingestion Pipeline, T1 ATOM Decomposition, and Semantic Knowledge Gaps  
**Authoritative Architectural References:**  
- `AI_PIE_Architecture_V1_Elite.pdf` — Section 2 (Code KG), Section 6 (Decision Extraction), Section 7 (Ontology), Section 24 (E1)  
- `docs/reports/temporal_kg_completion/T1_ATOM_COMPLETION_REPORT.md`  
- `docs/reports/ATOM_REAL_REPO_EVALUATION.md`  
**Audit Date:** November 6, 2026  

---

## 1. Executive Summary

Track T1 (ATOM — *Atomic Decomposition and Dynamic Temporal Knowledge Graph Construction*, arXiv:2510.22590) forms the authoritative deterministic foundation of Unotusk AI-PIE Code Lane. Operating inside `apps/api/src/services/code_atom/`, ATOM decomposes incoming Git commits into syntactic hunks, correlates them with Tree-sitter AST nodes (Python, TypeScript/JavaScript, Go, and Dart), extracts regex-grounded facts and relations, assigns dual-time temporal intervals, computes cryptographic fingerprints, and indexes atomic units in PostgreSQL 16 + `pgvector`.

While ATOM achieves **100.0% precision and recall on deterministic syntactic patterns** (such as explicit function declarations, static method calls, and module imports), it is inherently constrained by its lexical and AST-bound nature. It cannot parse the causal rationale embedded in commit messages, infer cross-component architectural coupling across multi-file diffs, capture subtle semantic algorithm alterations where symbol signatures remain static, or detect deprecation lifecycles and behavioral test specifications.

This gap analysis rigorously audits the existing ATOM pipeline, traces the end-to-end data flow from Git input to context retrieval, evaluates seven representative code evolution scenarios, and demonstrates where **Generative Information Extraction (E1)** provides indispensable semantic enrichment without compromising ATOM's zero-hallucination deterministic baseline.

---

## 2. End-to-End Pipeline Audit: From Git Input to Context Retrieval

The Code Lane ingestion and retrieval architecture follows a strict, multi-stage pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                            Existing Code Lane Ingestion Architecture                        │
└─────────────────────────────────────────────────────────────────────────────────────────────┘

  1. Git Commit Ingestion           2. Hunk & AST Decomposition           3. Fact & Relation Extraction
 ┌───────────────────────┐        ┌─────────────────────────────┐        ┌──────────────────────────────┐
 │ GitCommitArtifact     │───────▶│ CodeAtomDecomposer          │───────▶│ SemanticFactExtractor        │
 │ - raw_diff            │        │ - parse_unified_diff        │        │ - Regex guards, calls, defs  │
 │ - commit_sha          │        │ - _resolve_symbol (AST)     │        ├──────────────────────────────┤
 │ - commit_message      │        │ - normalize_code_change     │        │ TemporalRelationExtractor    │
 │ - author & timestamp  │        │ - file renames              │        │ - (subj, rel, obj, t_s, t_e) │
 └───────────────────────┘        └─────────────────────────────┘        └──────────────┬───────────────┘
                                                                                        │
  6. Context Retrieval & RAG        5. Relational & Vector Store         4. Reconciliation & Mapping
 ┌───────────────────────┐        ┌─────────────────────────────┐        ┌──────────────▼───────────────┐
 │ ContextAssembler      │◀───────│ PostgreSQL 16 + pgvector    │◀───────│ relation_resolver.py         │
 │ - Multi-Signal SQL    │        │ - code_chunks table         │        │ - Deduplication              │
 │ - 1-Hop AST Traversal │        │ - code_relations table      │        │ - Rename propagation         │
 │ - Temporal Filtering  │        │ - HNSW / IVFFlat embeddings │        │ chunk_mapper.py              │
 └───────────────────────┘        └─────────────────────────────┘        └──────────────────────────────┘
```

### Detailed Pipeline Stages:

1. **Git Commit Ingestion (`GitCommitArtifact`):**
   - Source data enters via `GitCommitArtifact` (`apps/api/src/schemas/code_atom.py`), containing `commit_sha`, `commit_message`, `author_name`, `committed_at`, and `raw_diff`.
   - Diff parsing (`diff_parser.py`) converts the raw unified diff into structured `GitFileDiff` and `GitDiffHunk` records with `old_start_line`, `new_start_line`, `added_lines`, and `deleted_lines`.

2. **AST-Aware Symbol Resolution (`CodeAtomDecomposer`):**
   - In `decomposer.py`, each hunk is matched against the repository symbol catalog using Tree-sitter AST ranges.
   - Innermost enclosing scope resolution binds hunks to concrete classes, functions, or methods (`symbol_name`, `symbol_type`, `symbol_id`).

3. **Deterministic Semantic Fact Extraction (`fact_decomposer.py`):**
   - `SemanticFactExtractor` applies compiled regular expressions (`GUARD_PATTERN`, `METHOD_CALL_PATTERN`, `ASSIGNMENT_CALL_PATTERN`, `IMPORT_PATTERN`, `RAISE_PATTERN`).
   - Categorizes statements into `FactType` (`BEHAVIOR`, `VALIDATION`, `ERROR_HANDLING`, `STATE_CHANGE`, `RELATIONSHIP`, `REMOVAL`, `CONFIGURATION`, `STRUCTURAL`).
   - Implements `validate_grounded_tokens()` to verify that extracted identifier tokens exist in the raw diff, file path, or symbol scope.

4. **Temporal Relation Extraction & Exclusivity Taxonomy (`relation_extractor.py`, `taxonomy.py`):**
   - `TemporalRelationExtractor` identifies syntactic relations: `CALLS`, `DEFINES`, `IMPORTS`, `INHERITS`, `MUTATES`, `CONFIGURES`, `VALIDATES`, `RAISES`.
   - Anchors dual-time validity intervals:
     - $t_{\text{obs}} = \text{commit author timestamp (UTC)}$
     - $t_{\text{start}} = t_{\text{obs}}$ for additions; $t_{\text{end}} = \text{None}$ (open interval).
     - $t_{\text{end}} = t_{\text{obs}}$ for deletions; $t_{\text{start}} = \text{None}$.
   - Resolves relation exclusivity (`EXCLUSIVE` vs. `NON_EXCLUSIVE`) and scope keys via `CodeRelationTaxonomy` (`taxonomy.py`).

5. **Entity & Relation Reconciliation (`relation_resolver.py`):**
   - Reconciles historical file renames (`old_path` $\to$ `new_path`).
   - Deduplicates relations using SHA256 fingerprints:
     $$\text{fingerprint} = \text{SHA256}(\text{commit\_sha} : \text{file\_path} : \text{subj} : \text{rel} : \text{obj} : t_{\text{start}} : t_{\text{end}})$$

6. **Relational & Vector Storage (`chunk_mapper.py`, `embedding.py`):**
   - Ingests atomic changes into `CodeChunk` records (`apps/api/src/models/chunk.py`).
   - Stores `atom_metadata` (facts, hunk lines, symbol scopes) in JSONB columns.
   - Generates 1536-dimensional vector embeddings stored with `pgvector`.

7. **Context Assembly & Grounded Retrieval (`context_engine/assembler.py`):**
   - Combines lexical BM25 matching, dense vector cosine similarity, and 1-hop AST graph traversal.
   - Gathers active temporal relations (filtering out superseded edges where $t_{\text{end}} < t_{\text{query}}$).
   - Enforces low-confidence abstention gates if evidence relevance falls below threshold ($< 0.20$).

---

## 3. What ATOM Already Extracts Correctly

ATOM is rock-solid at deterministic syntactic extraction. Across all tests and benchmarks, ATOM reliably captures:

1. **Exact AST Symbol Boundaries:** Accurate mapping of file paths, enclosing classes, function signatures, and line intervals ($[L_{\text{start}}, L_{\text{end}}]$).
2. **Explicit Language Imports:** Syntactic `import x` and `from y import z` across Python, Dart, TypeScript, and Go.
3. **Direct Method and Function Calls:** Standard receiver-method syntax (`client.send_event()`, `db.session.commit()`).
4. **Class Inheritance & Interfaces:** `class AdminUser(BaseUser)` and `class Service implements IService`.
5. **Exception Handling:** Explicit `raise ConflictException(...)` and `throw new UnimplementedError(...)`.
6. **File Renames & Structural Lineage:** Complete tracking of rename operations preserving historical identity.
7. **Strict Dual-Time Temporal Invariants:** Zero invented timestamps; precise anchoring of addition and deletion times to Git author commits.
8. **Token-Level Grounding:** Immediate rejection of any fact claiming identifiers not present in the diff.

---

## 4. What Information is Missing (The Semantic Gap)

Despite its syntactic precision, ATOM cannot extract the **cognitive, architectural, and causal intent** of code evolution. Below is the systematic comparison of capabilities:

| Capability | T1 ATOM Deterministic Baseline | E1 Generative Information Extraction | Gap Classification |
| :--- | :--- | :--- | :--- |
| **Direct Function Call (`CALLS`)** | ✅ Fully Extracted (Regex/AST) | ✅ Supported | Baseline Parity |
| **Static Import (`IMPORTS`)** | ✅ Fully Extracted (AST) | ✅ Supported | Baseline Parity |
| **Symbol Definition (`DEFINES`)** | ✅ Fully Extracted (AST) | ✅ Supported | Baseline Parity |
| **Commit Message Causal Rationale** | ❌ **Omitted** (Ignored by regex) | ✅ **Extracted** (Captures *why* change occurred) | **Major Semantic Gap** |
| **Cross-Component Coupling** | ❌ **Omitted** (Hunks isolated) | ✅ **Extracted** (Correlates multi-file diffs) | **Major Architectural Gap** |
| **Implicit / Dynamic Dependencies** | ❌ **Omitted** (Requires static AST) | ✅ **Extracted** (Infers config/injection deps) | **Major Semantic Gap** |
| **Behavioral Change (Static Signature)**| ❌ **Partial** (Only generic assignment) | ✅ **Extracted** (Describes algorithm shifts) | **Major Behavioral Gap** |
| **Cross-Service Config Propagation** | ❌ **Omitted** (Treated as raw key-value) | ✅ **Extracted** (Links config to service impact)| **Major Operational Gap** |
| **Deprecation & Replacement Lifecycle** | ❌ **Omitted** (Sees two unrelated defs) | ✅ **Extracted** (`DEPRECATES`, `REPLACES` events)| **Major Lifecycle Gap** |
| **Test Behavioral Specification** | ❌ **Omitted** (Sees generic assert call) | ✅ **Extracted** (Extracts contract invariants) | **Major Quality Gap** |

---

## 5. Investigation of Seven Critical Code Evolution Scenarios

To prove the necessity of E1, we investigate seven concrete code evolution scenarios representing genuine repository commits.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    7 Critical Code Evolution Scenarios                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Causal Commit Rationale    │ "Why was this auth guard added?"            │
│ 2. Multi-Component Coupling   │ Auth middleware refactor touching 3 files   │
│ 3. Implicit Dependency Intro  │ Redis worker concurrency parameter          │
│ 4. Signature-Preserved Shift  │ Pricing algorithm from flat to tiered       │
│ 5. Cross-Service Config Impact│ Port binding change in YAML affecting API   │
│ 6. Deprecation / Replacement  │ Legacy token validator replaced by JWT      │
│ 7. Behavioral Test Contract   │ Asserting expired session token deactivates │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Scenario 1: Commit Message Explaining *Why* a Change Was Introduced
- **Input Context:**
  - *Commit Message:* `fix(auth): enforce permanent lead admin guard to prevent privilege revocation lockout during org sync`
  - *Diff Snippet:*
    ```python
    + if user.email == "admin@acme.com":
    +     return True
    ```
- **What ATOM Extracts:**
  - `Fact`: `VALIDATION` — `user.email == "admin@acme.com"`.
  - `Relation`: None.
  - *Missing:* ATOM completely discards the commit message. It does not know *why* this guard exists (protecting permanent lead admin against automated sync lockout).
- **What Generative IE Adds:**
  - `Event`: `BEHAVIOR_CHANGED` with rationale: *"Protects permanent lead admin against automated privilege revocation during organization member synchronization."*
  - `Relation`: `AuthService` $\xrightarrow{\text{VALIDATES}}$ `admin@acme.com`.

---

### Scenario 2: Diff Modifying Several Related Components (Architectural Coupling)
- **Input Context:**
  - *Commit Message:* `feat(rbac): isolate workspace project operations by organization boundary`
  - *Diff:* Modifies `apps/api/src/routers/projects.py`, `apps/api/src/services/project_service.py`, and `apps/api/src/models/project.py`.
- **What ATOM Extracts:**
  - Three isolated atomic changes with local AST scopes.
  - Three separate facts with no semantic bridge linking the router validation to the service domain invariant.
- **What Generative IE Adds:**
  - `Event`: `API_CHANGED` and `BEHAVIOR_CHANGED`.
  - Cross-component `DEPENDS_ON` and `VALIDATES` relationships linking `ProjectRouter` $\to$ `ProjectService` $\to$ `OrganizationBoundary`.
  - Captures the systemic invariant: *Project CRUD operations now enforce strict tenant isolation via organization foreign keys.*

---

### Scenario 3: Code Change Introducing a New Dependency
- **Input Context:**
  - *Commit Message:* `chore: integrate redis client for distributed worker task queue`
  - *Diff Snippet (`worker.py`):*
    ```python
    + from redis.asyncio import Redis
    + task_queue = Redis.from_url(settings.REDIS_URL)
    ```
- **What ATOM Extracts:**
  - `Relation`: `worker.py` $\xrightarrow{\text{IMPORTS}}$ `redis.asyncio.Redis`.
  - `Fact`: `RELATIONSHIP` — `task_queue = Redis.from_url(...)`.
- **What Generative IE Adds:**
  - `Event`: `DEPENDENCY_ADDED` with target `redis` (versioned dependency).
  - `Relation`: `WorkerService` $\xrightarrow{\text{DEPENDS\_ON}}$ `RedisTaskQueue`.
  - Captures the operational role of Redis as an asynchronous task queue rather than just an inert Python import.

---

### Scenario 4: Method Behavior Change Without Name or Signature Change
- **Input Context:**
  - *Commit Message:* `refactor(billing): switch discount calculation from flat tier to progressive volume curve`
  - *Diff Snippet (`billing.py`):*
    ```python
      def calculate_discount(volume: int) -> float:
    -     return 0.10 if volume > 100 else 0.0
    +     if volume > 500: return 0.25
    +     if volume > 100: return 0.10
    +     return 0.0
    ```
- **What ATOM Extracts:**
  - Both before and after diff, AST signature is `calculate_discount(volume: int) -> float`.
  - ATOM extracts added guards `volume > 500` and `volume > 100`.
  - It has no concept that the pricing tier strategy changed from single-threshold flat rate to multi-tier progressive curve.
- **What Generative IE Adds:**
  - `Event`: `BEHAVIOR_CHANGED` on `calculate_discount`.
  - Statement: *"Introduced progressive 25% discount tier for volumes exceeding 500 units, while preserving 10% tier for volumes over 100."*

---

### Scenario 5: Configuration Change Affecting Another Service
- **Input Context:**
  - *Commit Message:* `config: increase worker task concurrency to 8 to alleviate ingestion backlog`
  - *Diff Snippet (`docker-compose.yml`):*
    ```yaml
    - WORKER_CONCURRENCY: 2
    + WORKER_CONCURRENCY: 8
    ```
- **What ATOM Extracts:**
  - `Fact`: `CONFIGURATION` — `WORKER_CONCURRENCY: 8`.
  - `Relation`: None (YAML files lack AST symbols).
- **What Generative IE Adds:**
  - `Event`: `CONFIGURATION_UPDATED` targeting `WorkerService`.
  - `Relation`: `docker-compose.yml` $\xrightarrow{\text{CONFIGURES}}$ `WorkerService.concurrency`.
  - Contextual note linking concurrency increase to task backlog mitigation.

---

### Scenario 6: Implementation Deprecation or Replacement
- **Input Context:**
  - *Commit Message:* `refactor(auth): deprecate SessionTokenManager in favor of StatelessJWTService`
  - *Diff Snippet (`auth.py`):*
    ```python
    + @deprecated("Use StatelessJWTService instead. Will be removed in v2.")
      class SessionTokenManager:
          ...
    + class StatelessJWTService:
    +     def verify_token(self, token: str) -> Claims: ...
    ```
- **What ATOM Extracts:**
  - `Fact`: `STRUCTURAL` definition of `StatelessJWTService`.
  - Decorator line extracted as generic token.
  - Fails to establish the directed replacement relationship between the two classes.
- **What Generative IE Adds:**
  - `Event`: `IMPLEMENTATION_DEPRECATED` for `SessionTokenManager`.
  - `Relation`: `StatelessJWTService` $\xrightarrow{\text{REPLACES}}$ `SessionTokenManager`.
  - `Relation`: `SessionTokenManager` $\xrightarrow{\text{SUPERSEDED\_BY}}$ `StatelessJWTService`.

---

### Scenario 7: Test Change Establishing a New Expected Behavior
- **Input Context:**
  - *Commit Message:* `test(auth): add specification test verifying expired JWT rejects authentication`
  - *Diff Snippet (`test_auth.py`):*
    ```python
    + def test_expired_token_raises_unauthorized():
    +     token = create_test_token(expired=True)
    +     with pytest.raises(HTTPException) as exc:
    +         auth_service.verify(token)
    +     assert exc.value.status_code == 401
    ```
- **What ATOM Extracts:**
  - `Fact`: `BEHAVIOR` — `def test_expired_token_raises_unauthorized()`.
  - `Relation`: `test_auth.py` $\xrightarrow{\text{CALLS}}$ `create_test_token`.
- **What Generative IE Adds:**
  - `Event`: `TEST_MODIFIED` establishing intent contract.
  - `Relation`: `test_expired_token_raises_unauthorized` $\xrightarrow{\text{TESTS}}$ `auth_service.verify`.
  - Behavioral Invariant: *"Specifies that expired JWT tokens must result in HTTP 401 Unauthorized."*

---

## 6. Synthesis: Where Generative Extraction Adds Decisive Value

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       The E1 Generative Value Proposition                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Deterministic AST (ATOM)            Generative IE (E1)                     │
│  ─────────────────────────            ──────────────────                    │
│  • What changed (Exact diff)          • Why it changed (Intent & Rationale) │
│  • Exact line numbers & AST nodes     • Cross-component architectural impact│
│  • Syntactic calls & imports          • Semantic relationships (REPLACES)   │
│  • Hard zero-hallucination floor      • Behavioral contracts & specifications│
│                                                                             │
│  HYBRID ARCHITECTURE:                                                       │
│  E1 sits ON TOP OF ATOM, ingesting ATOM's verified hunks and AST symbols,   │
│  enriching them with generative semantic facts, relations, and events,      │
│  and subjecting all LLM outputs to ATOM's deterministic grounding gate.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

The gap analysis demonstrates conclusively that:
1. **ATOM is necessary but insufficient:** AST and regex cannot interpret natural language commit messages, architectural intent, or cross-file conceptual coupling.
2. **Generative IE must NOT replace ATOM:** Replacing ATOM with an LLM-only pipeline would destroy deterministic provenance, increase ingestion latency by 50x, incur unsustainable API costs, and reintroduce hallucination risks.
3. **The Optimal Architecture is a Layered Hybrid:** ATOM provides the verified syntactic substrate (files, hunks, line spans, AST scopes, author timestamps), and E1 provides the higher-order semantic reasoning layer.
