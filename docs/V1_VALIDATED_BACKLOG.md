# UNOTUSK — V1 VALIDATED PRODUCT BACKLOG

**Document**: Validated Product Backlog for V1  
**Derived From**: Phase 7 Real Customer Pilot & Product Feedback Loop  
**Date**: September 16, 2026  

---

## 1. Operating Principle & Grounding Rules

Items in this backlog are **not speculative product ideas**. Every item in the **VALIDATED NEED** section is derived strictly from observed behavior, usability friction, or direct technical feedback from the Phase 7 pilot on real repositories (`pallets/flask`, `psf/requests`).

Items are partitioned into three distinct tiers:
1. **TIER 1: VALIDATED NEED** — Direct customer friction or workflow blocker observed in pilot.
2. **TIER 2: INTERNAL IDEA** — Engineering hypotheses that require further customer validation before commitment.
3. **TIER 3: FUTURE / V2** — Large architectural extensions deferred beyond V1.

---

## 2. Tier 1: Validated Needs (High Priority for V1)

### ITEM-101: Architectural Cycle Clustering & Deduplication
- **Customer Problem**: Ingesting coupled repositories (`pallets/flask`) generated 2,704 circular dependency findings because every permutation of a cyclic path was listed separately. This caused information overload.
- **Observed Evidence**: 2,604 circular findings shared overlapping subsets of the same 8 files (`app.py`, `blueprints.py`, `cli.py`, `helpers.py`, `globals.py`, `wrappers.py`, `debughelpers.py`, `scaffold.py`).
- **Affected Workflow**: Discoveries Tab (`Ctrl + 2`).
- **Expected Value**: Reduces 2,700 repetitive findings into 3–5 high-impact "Architectural Cycle Clusters" with interactive graph visualization.
- **Complexity**: Medium (Graph SCC / Tarjan algorithm post-processing).
- **Priority**: **P1 (High)**

---

### ITEM-102: Query Analyzer Stopword & Negative-Proof Sharpening
- **Customer Problem**: When users ask negative queries about non-existent components (e.g. *"Where is QuantumPaymentController configured?"*), generic English words ("where", "is", "configured") sometimes match loosely related chunks in offline retrieval.
- **Observed Evidence**: Offline search retrieved 35 low-scoring chunks on a negative query before down-ranking confidence to `LOW`.
- **Affected Workflow**: Grounded Ask Tab (`Ctrl + K`).
- **Expected Value**: Zero false-positive chunk matches on negative queries; immediate, crisp declaration of absence of evidence.
- **Complexity**: Low (Enhanced stopword filter and minimum keyword threshold in `query_analyzer.py`).
- **Priority**: **P1 (High)**

---

### ITEM-103: Downstream Change Impact Analysis ("Blast Radius")
- **Customer Problem**: Engineers want to know the risk of modifying a core file before committing changes: *"If I edit `ctx.py`, what modules could break?"*
- **Observed Evidence**: Users manually navigated from `ctx.py` to the Architecture Tab and counted incoming callers.
- **Affected Workflow**: Architecture Tab & Files Tab.
- **Expected Value**: One-click "Blast Radius" report showing direct and transitive dependents with impacted symbol lists.
- **Complexity**: Medium (Transitive closure over `code_dependencies` table).
- **Priority**: **P2 (Medium-High)**

---

### ITEM-104: Monorepo Sub-Package Path Partitioning
- **Customer Problem**: Large enterprise codebases contain multiple distinct services or sub-packages in a single Git repository. Ingesting the entire root mixes domains.
- **Observed Evidence**: Pilot criteria scoped MVP to single repositories <200k LOC. Pilot teams with monorepos requested scoping a project to a sub-directory (e.g. `packages/billing`).
- **Affected Workflow**: Project Creation & Repository Connection (`CreateProjectDialog`).
- **Expected Value**: Allows creating separate Unotusk projects for specific folders within a monorepo.
- **Complexity**: Low-Medium (Add `root_path` filter to file scanner and git checkout).
- **Priority**: **P2 (Medium)**

---

### ITEM-105: Visual Dependency Graph Explorer
- **Customer Problem**: Text lists of dependencies and callers require mental assembly; developers prefer visual topological node-link diagrams.
- **Observed Evidence**: Users clicked back and forth between callers and callee symbols to map relationship hierarchies.
- **Affected Workflow**: Architecture Tab (`Ctrl + 3`).
- **Expected Value**: Interactive 2D canvas showing component clusters and dependency arrows with zoom/pan.
- **Complexity**: High (Canvas rendering in Flutter / Graphviz layout).
- **Priority**: **P2 (Medium)**

---

## 3. Tier 2: Internal Ideas (Requires Further Validation)

| ID | Proposed Concept | Team Hypothesis | Reason Deferred / Requires Validation |
|---|---|---|---|
| **IDEA-201** | VS Code / Cursor IDE Extension | Bringing Ask into editor reduces window switching. | Verify if developers prefer dedicated sidecar desktop window vs. editor panel. |
| **IDEA-202** | Automated Pull Request Review Bot | Posting discovery findings on GitHub PRs catches debt early. | Risk of becoming noisy CI spam; pilot users explicitly asked for quiet tools. |
| **IDEA-203** | Test Generation Assistance | Generating unit tests for uncovered symbols. | Out of scope for pure intelligence MVP; touches code mutation. |
| **IDEA-204** | Slack / Discord Ask Bot | Allowing team members to ask questions in chat. | Requires multi-user auth federation and webhook infrastructure. |

---

## 4. Tier 3: Future / V2 (Explicitly Deferred)

| ID | Concept | Explicit Non-Goal Justification |
|---|---|---|
| **FUT-301** | Autonomous Code Refactoring | Unotusk is an evidentiary intelligence tool, not an agent that modifies production code. |
| **FUT-302** | Jira / Linear Issue Mutation | Avoid bi-directional ticketing complexity; developers already have issue trackers. |
| **FUT-303** | Multi-Tenant Cloud SaaS Fleet | Single-tenant customer-hosted deployment satisfies 100% of data sovereignty needs. |
| **FUT-304** | Model Fine-Tuning Pipeline | Retrieval-augmented grounded context over AST symbols outperforms fine-tuning for dynamic codebases. |

---

## 5. Summary Matrix for V1 Planning

| Priority | Item ID | Title | Complexity | Expected Impact |
|---|---|---|---|---|
| **P1** | ITEM-101 | Architectural Cycle Clustering & Deduplication | Medium | Eliminates discovery noise; highlights root architectural debt. |
| **P1** | ITEM-102 | Query Analyzer Stopword & Negative-Proof Sharpening | Low | Sharpen negative proof answers; eliminates spurious low-score chunks. |
| **P2** | ITEM-103 | Downstream Change Impact Analysis ("Blast Radius") | Medium | Accelerates safe refactoring and PR review. |
| **P2** | ITEM-104 | Monorepo Sub-Package Path Partitioning | Low-Med | Unlocks enterprise monorepo adoption. |
| **P2** | ITEM-105 | Visual Dependency Graph Explorer | High | Elevates architecture tab from list to visual map. |
