# T3 — MemoTime Technical Component Inventory

## 1. Overview and Architecture

Track 3 implements **MemoTime** (Memory-Augmented Temporal Knowledge Graph Enhanced Reasoning), adapted from arXiv:2510.13614 (*"MemoTime: Memory-Augmented Temporal Knowledge Graph Enhanced Large Language Model Reasoning"*).

The implementation is structured into two distinct, decoupled functional layers:
1. **Core Temporal Reasoning & Tree-of-Time (ToT)**: Deterministic temporal intent parsing, hierarchical subquestion decomposition in a Tree of Time, Allen Interval Algebra evaluation (all 13 relations), monotonic timestamp progression, multi-entity interval consistency checking, and operator-aware retrieval candidate reranking.
2. **Experience Memory Subsystem**: Persistent cross-query experience memory (`memotime_experiences` table), verified reasoning outcome storage, contradiction detection against prior experience, and automated write-back of high-confidence reasoning traces during query execution.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Core Temporal Reasoning & Tree of Time (In-Memory Reasoning)       │
│                                                                             │
│   Query Text ──► parse_temporal_intent()                                    │
│                        │                                                    │
│                        ▼                                                    │
│              StructuredTemporalIntent                                       │
│              (CURRENT, HISTORICAL, BEFORE, AFTER, INTERVAL, DIFF, EVOLUTION)│
│                        │                                                    │
│                        ▼                                                    │
│               build_tree_of_time() ──► TimeTreeNode hierarchy              │
│                        │                                                    │
│                        ▼                                                    │
│            Allen Interval Algebra & Bound Checking                          │
│            (compute_allen_relation, matches_allen_relation)                 │
│                        │                                                    │
│                        ▼                                                    │
│            Candidate Filtering & Signal Injection                           │
│            (memotime_temporal_match, memotime_diff_match, etc.)             │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: Experience Memory Subsystem (PostgreSQL Persistent Memory)         │
│                                                                             │
│   MemoTimeExperienceStore.retrieve_relevant_experiences_async()             │
│                        │                                                    │
│                        ▼                                                    │
│               ExperienceRecord Injection into Candidates                    │
│               (memotime_experience_relevance / contradiction)               │
│                        │                                                    │
│                        ▼                                                    │
│               Context Engine Answer Synthesis                               │
│                        │                                                    │
│                        ▼                                                    │
│   MemoTimeExperienceStore.record_verified_experience_async() (Write-Back)  │
│                        │                                                    │
│                        ▼                                                    │
│               memotime_experiences table (PostgreSQL 16)                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Inventory

### 2.1 Structured Temporal Intent Classifier
- **Component Name**: Temporal Intent Classifier
- **File Path**: `apps/api/src/services/context_engine/memotime.py`
- **Class and Function Names**:
  - `class TemporalIntentType(str, Enum)` (`CURRENT`, `HISTORICAL`, `BEFORE`, `AFTER`, `INTERVAL`, `DIFF`, `EVOLUTION`, `AMBIGUOUS`)
  - `class StructuredTemporalIntent`
  - `class TemporalConstraint`
  - `class TemporalBound`
  - `MemoTimeService.parse_temporal_intent(query_text: str, target_symbols: list[str] | None = None) -> StructuredTemporalIntent`
  - `MemoTimeService._detect_date_bound(text: str) -> datetime | None`
  - `MemoTimeService._detect_commit_shas(text: str) -> list[str]`
- **Responsibility**: Parses free-form user questions into typed temporal specifications. Detects explicit ISO dates (`YYYY-MM-DD`), Git commit SHAs, interval keywords (`between X and Y`, `from X to Y`), directional bounds (`before`, `after`, `since`, `prior to`), evolution cues (`how did X evolve across commits`), and diff requests (`what changed in commit X`). Flags contradictory constraints (e.g. `start > end`) and ambiguous requests (`intent_type = AMBIGUOUS`).
- **Input and Output**:
  - *Input*: `query_text: str`, optional `target_symbols: list[str]`.
  - *Output*: `StructuredTemporalIntent` containing `intent_type`, `is_temporal`, `confidence`, `constraints`, `reference_commits`, and detected entities.
- **Internal Dependencies**: `apps.api.src.services.code_atom.temporal.TEMPORAL_KEYWORDS`.
- **External Dependencies**: `re`, `datetime` (`UTC`).
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_memotime.py` (35 tests covering all intent types, commit parsing, and ambiguity)
  - `tests/unit/test_query_analyzer.py` (5 tests)
- **Current Implementation Limitations**: Resolves relative time words (e.g. "last week") relative to system current time (`datetime.now(UTC)`).

---

### 2.2 Tree-of-Time (ToT) Hierarchy Builder
- **Component Name**: Tree-of-Time Foundation
- **File Path**: `apps/api/src/services/context_engine/memotime.py`
- **Class and Function Names**:
  - `class ResolutionStatus(str, Enum)` (`UNRESOLVED`, `RESOLVED`, `NO_EVIDENCE`, `CONTRADICTORY`, `AMBIGUOUS`, `UNBOUNDED_TEMPORAL`)
  - `class TimeTreeNode`
  - `class TreeOfTime`
  - `TreeOfTime.add_node(self, node: TimeTreeNode) -> None`
  - `TreeOfTime.get_ordered_nodes(self) -> list[TimeTreeNode]`
  - `MemoTimeService.build_tree_of_time(intent: StructuredTemporalIntent, candidate_pool: list[RetrievedCandidate] | None = None) -> TreeOfTime`
  - `MemoTimeService.decompose_temporal_query(query_text: str, candidate_pool: list[RetrievedCandidate] | None = None) -> TreeOfTime`
- **Responsibility**: Builds a hierarchical Tree of Time (ToT) decomposing complex temporal queries into ordered subquestions and milestones. For `EVOLUTION` queries, discovers historical commits and generates sequential child nodes for each evolution phase. For `INTERVAL` queries, produces boundary check nodes. For `DIFF` queries, isolates pre-commit and post-commit state nodes. Enforces monotonic progression across child nodes.
- **Input and Output**:
  - *Input*: `StructuredTemporalIntent`, optional `candidate_pool: list[RetrievedCandidate]`.
  - *Output*: `TreeOfTime` structure containing root node, ordered child `TimeTreeNode` items, and validation status.
- **Internal Dependencies**: `StructuredTemporalIntent`, `TimeTreeNode`, `RetrievedCandidate`.
- **External Dependencies**: `dataclasses`, `uuid`.
- **Database Interaction**: None directly.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_memotime.py` (`test_tree_of_time_decomposition_evolution`, `test_tree_of_time_interval_bounds`)
- **Current Implementation Limitations**: Max decomposition depth is bounded to 5 hops (`MEMOTIME_MAX_PROPAGATION_HOPS = 5`) to prevent explosive tree growth.

---

### 2.3 Allen Interval Algebra Engine
- **Component Name**: Allen Interval Algebra Engine
- **File Path**: `apps/api/src/services/context_engine/memotime.py`
- **Class and Function Names**:
  - `class AllenIntervalRelation(str, Enum)` (13 relations: `BEFORE`, `AFTER`, `MEETS`, `MET_BY`, `OVERLAPS`, `OVERLAPPED_BY`, `DURING`, `CONTAINS`, `STARTS`, `STARTED_BY`, `FINISHES`, `FINISHED_BY`, `EQUALS`)
  - `AllenIntervalRelation.inverse -> AllenIntervalRelation`
  - `MemoTimeService.compute_allen_relation(a: TemporalBound, b: TemporalBound) -> AllenIntervalRelation | None`
  - `MemoTimeService.matches_allen_relation(a: TemporalBound, b: TemporalBound, relation: AllenIntervalRelation) -> bool`
- **Responsibility**: Implements the complete 13-relation Allen Interval Algebra for temporal code reasoning. Evaluates relationships between validity intervals `[s_a, e_a]` and `[s_b, e_b]`, correctly handling open-ended ongoing intervals (`end = None` representing currently active code). Enforces algebraic inverse symmetry:
  $$\text{matches\_allen\_relation}(a, b, r) \iff \text{matches\_allen\_relation}(b, a, r.\text{inverse})$$
- **Input and Output**:
  - *Input*: `a: TemporalBound`, `b: TemporalBound`, optional relation enum.
  - *Output*: `AllenIntervalRelation` enum or boolean match.
- **Internal Dependencies**: `TemporalBound`, `AllenIntervalRelation`.
- **External Dependencies**: Standard library (`datetime`).
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_memotime.py` (`test_allen_interval_algebra_all_13_relations`, `test_allen_interval_inverse_symmetry`)
- **Current Implementation Limitations**: Requires valid intervals (`start <= end`); malformed bounds where `start > end` return `None`.

---

### 2.4 Multi-Entity Temporal Consistency Checker
- **Component Name**: Multi-Entity Temporal Consistency Checker
- **File Path**: `apps/api/src/services/context_engine/memotime.py`
- **Class and Function Names**:
  - `MemoTimeService.check_multi_entity_consistency(entity_bounds: dict[str, TemporalBound]) -> tuple[bool, list[str]]`
  - `MemoTimeService.evaluate_monotonic_progression(nodes: list[TimeTreeNode]) -> tuple[bool, list[str]]`
  - `MemoTimeService.propagate_temporal_evidence(tree: TreeOfTime, candidates: list[RetrievedCandidate]) -> TreeOfTime`
- **Responsibility**: Validates that temporal constraints across distinct code entities (e.g. caller in `service.py` and callee in `client.py`) are mutually satisfiable. Identifies disjoint intervals when concurrent operation was requested. Verifies that milestone nodes progress monotonically forward in time without backwards time jumps. Binds candidate code evidence to the specific ToT nodes whose temporal bounds contain the candidate's commit or observation timestamp.
- **Input and Output**:
  - *Input*: `dict[str, TemporalBound]`, `list[TimeTreeNode]`, or `(TreeOfTime, list[RetrievedCandidate])`.
  - *Output*: Boolean validity with error strings, or updated `TreeOfTime` with resolution statuses.
- **Internal Dependencies**: `TreeOfTime`, `TimeTreeNode`, `TemporalBound`, `RetrievedCandidate`.
- **External Dependencies**: Standard library (`datetime`).
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_memotime.py` (`test_multi_entity_temporal_consistency`, `test_monotonic_progression_validation`)
- **Current Implementation Limitations**: Consistency checking operates on known timestamp bounds; entities with missing timestamps cannot be definitively validated and are marked `UNBOUNDED_TEMPORAL`.

---

### 2.5 Operator-Aware Temporal Retrieval Pipeline
- **Component Name**: MemoTime Retrieval Pipeline
- **File Path**: `apps/api/src/services/context_engine/memotime.py`
- **Class and Function Names**:
  - `class MemoTimeRetrievalResult`
  - `MemoTimeService.is_retrieval_enabled() -> bool`
  - `MemoTimeService.run_memotime_pipeline(candidates: list[RetrievedCandidate], analyzed_query: Any | None = None, query_text: str = "", tree_of_time: TreeOfTime | None = None, experiences: list[ExperienceRecord] | None = None) -> MemoTimeRetrievalResult`
  - `MemoTimeService.apply_memotime_retrieval(...) -> list[RetrievedCandidate]`
- **Responsibility**: Filters, scores, and reorders retrieval candidates based on the parsed temporal intent and ToT evidence bindings:
  - `CURRENT`: Prioritizes active implementations, demoting superseded and deleted chunks.
  - `HISTORICAL`: Boosts superseded code and precursor commits.
  - `DIFF`: Filters strictly to chunks matching the target commit SHA (`memotime_diff_match = 1.0`).
  - `INTERVAL`: Evaluates whether chunk timestamps fall inside the window, injecting `memotime_temporal_match = 1.0` or `memotime_temporal_mismatch = 1.0`.
  - `EVOLUTION`: Sorts candidates chronologically across commit milestones.
  - Generates a candidate `ExperienceRecord` for high-confidence verified runs.
- **Input and Output**:
  - *Input*: `candidates: list[RetrievedCandidate]`, query text, optional ToT, optional experiences.
  - *Output*: `MemoTimeRetrievalResult` with reranked candidates, strategy used, diagnostics, and potential experience candidate.
- **Internal Dependencies**: `apps.api.src.config.settings`, `RetrievedCandidate`, `TreeOfTime`, `ExperienceRecord`.
- **External Dependencies**: `logging`, `datetime`.
- **Database Interaction**: None directly; called by `ProjectContextEngine`.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_memotime.py` (coverage across all intent pipelines)
  - `tests/unit/test_historical_retrieval_hardening.py`
- **Current Implementation Limitations**: Falls back gracefully to baseline candidate ordering when temporal intent is `AMBIGUOUS` or candidates lack all timestamps.

---

### 2.6 Experience Memory Model
- **Component Name**: MemoTime Experience Model
- **File Path**: `apps/api/src/models/memotime.py`
- **Class and Function Names**:
  - `class MemoTimeExperience(Base, UUIDMixin, TimestampMixin)`
  - Table Indexes: `ix_memotime_repo_branch`, `ix_memotime_lookup`, `ix_memotime_commit`
- **Responsibility**: SQLAlchemy database model persisting verified reasoning experiences in PostgreSQL 16. Captures repository ID, branch, original query text, intent type, target entities (`JSONB`), commit SHA, validity interval (`valid_from`, `valid_to`), verified outcome (`JSONB` containing line spans, diffs, verified facts), confidence score, verification flags, contradiction detail, and attribution string.
- **Input and Output**: ORM mapping to PostgreSQL table `memotime_experiences`.
- **Internal Dependencies**: `apps.api.src.db.base` (`Base`, `UUIDMixin`, `TimestampMixin`).
- **External Dependencies**: `sqlalchemy`, `uuid`, `datetime`.
- **Database Interaction**: Maps to table `memotime_experiences` in migration `0012_memotime_experiences.py`.
- **Tests Covering It**:
  - `tests/unit/test_memotime_experience_memory.py` (7 tests)
  - `docs/reports/temporal_kg_completion/memotime_experience_validation/memotime_postgresql_acceptance_report.md`
- **Current Implementation Limitations**: Requires `confidence_score >= 0.80` and `is_contradictory = False` to qualify for persistent experience storage.

---

### 2.7 MemoTime Experience Migration
- **Component Name**: MemoTime Experience Database Migration
- **File Path**: `apps/api/alembic/versions/0012_memotime_experiences.py`
- **Class and Function Names**:
  - `revision = "0012_memotime_experiences"`
  - `down_revision = "0011_evokg_triplets"`
  - `upgrade() -> None`
  - `downgrade() -> None`
- **Responsibility**: Creates the `memotime_experiences` table with cascading foreign key to `repositories.id`, JSONB fields for target entities and verified outcomes, and three performance indexes (`ix_memotime_repo_branch`, `ix_memotime_lookup`, `ix_memotime_commit`).
- **Input and Output**: DDL execution in PostgreSQL.
- **Internal Dependencies**: Migration `0011_evokg_triplets`.
- **External Dependencies**: `alembic`, `sqlalchemy`.
- **Database Interaction**: DDL table creation.
- **Tests Covering It**:
  - `tests/unit/test_memotime_experience_memory.py`
- **Current Implementation Limitations**: None.

---

### 2.8 MemoTime Experience Store
- **Component Name**: MemoTime Experience Store
- **File Path**: `apps/api/src/services/context_engine/memotime.py`
- **Class and Function Names**:
  - `class ExperienceRecord`
  - `class MemoTimeExperienceStore`
  - `MemoTimeExperienceStore.record_verified_experience_async(...) -> ExperienceRecord | None`
  - `MemoTimeExperienceStore.retrieve_relevant_experiences_async(...) -> list[ExperienceRecord]`
  - `MemoTimeExperienceStore._to_record(model: MemoTimeExperience) -> ExperienceRecord`
  - `MemoTimeService.apply_experience_memory(...) -> tuple[list[RetrievedCandidate], int]`
- **Responsibility**: Manages persistence and retrieval of reasoning experiences:
  - `record_verified_experience_async`: Gated by `MIN_CONFIDENCE_THRESHOLD = 0.80`. Rejects contradictory or low-confidence experiences. Writes verified records to `memotime_experiences` table.
  - `retrieve_relevant_experiences_async`: Queries prior experiences by repository, branch, target entities, and intent type.
  - `apply_experience_memory`: Injects `memotime_experience_relevance` boost into candidates matching verified experiences, or penalizes candidates directly contradicting verified experiences (`memotime_experience_contradiction = 1.0`).
- **Input and Output**:
  - *Input*: `AsyncSession`, repository ID, branch, query text, verified outcome payload, candidates.
  - *Output*: `ExperienceRecord` objects; augmented `RetrievedCandidate` list with experience signals.
- **Internal Dependencies**: `apps.api.src.models.memotime.MemoTimeExperience`, `ExperienceRecord`, `RetrievedCandidate`.
- **External Dependencies**: `sqlalchemy`, `uuid`, `datetime`, `logging`.
- **Database Interaction**: SELECT and INSERT queries on `memotime_experiences`.
- **Tests Covering It**:
  - `tests/unit/test_memotime_experience_memory.py` (7 tests)
  - `tests/unit/test_code_lane_hardening.py`
- **Current Implementation Limitations**: Experience reuse is strictly scoped to the same repository and branch. Cross-repository experience transfer is explicitly prohibited to prevent tenant leakage.

---

### 2.9 Project Context Engine Write-Back Integration
- **Component Name**: Context Engine MemoTime Integration
- **File Path**: `apps/api/src/services/context_engine/engine.py`
- **Class and Function Names**:
  - `ProjectContextEngine.investigate(...)` (lines 116-195)
- **Responsibility**: Connects Layer 1 (temporal retrieval) and Layer 2 (experience memory) into the runtime context investigation loop:
  1. Retrieves matching experiences from `MemoTimeExperienceStore` before ranking.
  2. Runs `MemoTimeService.run_memotime_pipeline`.
  3. Propagates temporal and experience signals to `MultiSignalRanker`.
  4. Automatically executes write-back of newly verified reasoning traces to `MemoTimeExperienceStore` if quality gates are satisfied.
  5. Attaches detailed MemoTime diagnostics to `GroundedAnswer.debug_signals`.
- **Input and Output**: Integrated within `investigate` call returning `GroundedAnswer`.
- **Internal Dependencies**: `memotime.py`, `ranker.py`, `assembler.py`, `settings.py`.
- **External Dependencies**: `sqlalchemy.ext.asyncio.AsyncSession`.
- **Database Interaction**: Reads and writes `memotime_experiences`.
- **Tests Covering It**:
  - `tests/unit/test_context_engine.py` (19 tests)
  - `tests/unit/test_code_lane_e2e_scenarios.py` (8 tests)
- **Current Implementation Limitations**: Gated by feature flag `settings.MEMOTIME_ENABLED` (defaults to `False`).
