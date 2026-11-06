# T2 — EvoKG / EvoReasoner Technical Component Inventory

## 1. Overview and Architecture

Track 2 implements **EvoKG** (Evolving Knowledge Graph) and **EvoReasoner** (Temporal Multi-Route Graph Reasoner), grounded in arXiv:2509.15464 (*"EvoReasoner: Temporal Reasoning with LLMs Augmented by Evolving Knowledge Graphs"*).

EvoKG models code entity relationships with explicit validity intervals `[valid_from, valid_to)`, observation timestamps `t_obs`, calibrated confidence scores, and Git branch isolation. The contradiction engine enforces strict property exclusivity and confidence-gated supersession (0.65 threshold). EvoReasoner generates multi-perspective reasoning routes, estimates route costs, performs bounded beam search traversal over persisted triplets, and aggregates verifiable, explainable proof chains (`GroundedProofChain`) directly into the context assembly pipeline.

```
                         ┌────────────────────────────────────┐
                         │   ATOM Temporal 5-Tuples (Mod 2)   │
                         └─────────────────┬──────────────────┘
                                           │
                                           ▼
                         ┌────────────────────────────────────┐
                         │      CodeRelationTaxonomy          │
                         │ (Exclusive vs Non-Exclusive Policy)│
                         └─────────────────┬──────────────────┘
                                           │
                                           ▼
                         ┌────────────────────────────────────┐
                         │     EvoKGContradictionEngine       │
                         │ (Confidence Gating & Supersession) │
                         └─────────────────┬──────────────────┘
                                           │
                                           ▼
                         ┌────────────────────────────────────┐
                         │     EvoKGPersistenceService        │
                         │  (PostgreSQL evokg_triplets table) │
                         └─────────────────┬──────────────────┘
                                           │
                   ┌───────────────────────┴───────────────────────┐
                   ▼                                               ▼
     ┌───────────────────────────┐                   ┌───────────────────────────┐
     │      Indexed Queries      │                   │      EvoRoutePlanner      │
     │(Outgoing, Incoming, Hist) │                   │(Multi-Route Query Planning)│
     └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                   │                                               │ Routes & Cost
                   │                                               ▼
                   │                                 ┌───────────────────────────┐
                   │                                 │    RouteCostEstimator     │
                   │                                 └─────────────┬─────────────┘
                   │                                               │
                   └───────────────────────┬───────────────────────┘
                                           │
                                           ▼
                         ┌────────────────────────────────────┐
                         │       EvoBeamSearchEngine          │
                         │ (Bounded Traversal & PathScorer)   │
                         └─────────────────┬──────────────────┘
                                           │ EvidencePaths
                                           ▼
                         ┌────────────────────────────────────┐
                         │  ProofChainAggregator & Validator  │
                         └─────────────────┬──────────────────┘
                                           │ GroundedProofChains
                                           ▼
                         ┌────────────────────────────────────┐
                         │  ContextAssembler (Prompt Section) │
                         └────────────────────────────────────┘
```

---

## 2. Component Inventory

### 2.1 Persistent Temporal Triplet Model
- **Component Name**: EvoKG Persistent Temporal Triplet Model
- **File Path**: `apps/api/src/models/evokg.py`
- **Class and Function Names**:
  - `class EvoKGTriplet(Base, UUIDMixin, TimestampMixin)`
  - `EvoKGTriplet.__init__(self, **kwargs)`
  - Partial Unique Index: `uq_evokg_active_exclusive`
  - Table Indexes: `ix_evokg_active_outgoing`, `ix_evokg_active_incoming`, `ix_evokg_temporal_lookup`, `ix_evokg_exclusive_conflict`, `ix_evokg_snapshot`, `ix_evokg_commit`, `ix_evokg_repo_fingerprint`
- **Responsibility**: Authoritative database model representing evolving code entity relationships in PostgreSQL 16. Stores subject and object identifiers, canonical relation, foreign keys to AST files and symbols, exclusivity flag, scope keys (for overload and inheritance slotting), validity intervals (`valid_from`, `valid_to`), observation timestamp, commit SHA, forward and backward supersession pointers (`superseded_by_id`, `supersedes_id`), calibrated confidence scores, and uncertainty/conflict flags.
- **Input and Output**:
  - *Input*: Triplet attribute kwargs.
  - *Output*: SQLAlchemy mapped ORM entity `evokg_triplets`.
- **Internal Dependencies**: `apps.api.src.db.base` (`Base`, `UUIDMixin`, `TimestampMixin`), `apps.api.src.models.*`.
- **External Dependencies**: `sqlalchemy`, `uuid`, `datetime`.
- **Database Interaction**: Maps directly to PostgreSQL 16 table `evokg_triplets` defined in migration `0011_evokg_triplets.py`.
- **Tests Covering It**:
  - `tests/unit/test_evokg_models_and_migration.py` (5 tests)
  - `tests/integration/test_evokg_real_postgresql_acceptance.py` (14 tests)
- **Current Implementation Limitations**: The partial unique index `uq_evokg_active_exclusive` enforces at most one active non-conflicting assertion per `(repository_id, branch, subject_id, relation, scope_key)` on PostgreSQL; on SQLite in-memory test databases it uses an equivalent conditional expression.

---

### 2.2 EvoKG Alembic Migration
- **Component Name**: EvoKG Database Migration
- **File Path**: `apps/api/alembic/versions/0011_evokg_triplets.py`
- **Class and Function Names**:
  - `revision = "0011_evokg_triplets"`
  - `down_revision = "0010_code_chunk_atom_metadata"`
  - `upgrade() -> None`
  - `downgrade() -> None`
- **Responsibility**: Creates the `evokg_triplets` database table with all required foreign key constraints (cascading on repository deletion, set null on snapshot/file/symbol deletion), column definitions, default timestamps, and 8 specialized B-tree and partial unique indexes.
- **Input and Output**: DDL execution against target PostgreSQL database.
- **Internal Dependencies**: Migration `0010_code_chunk_atom_metadata`.
- **External Dependencies**: `alembic`, `sqlalchemy`.
- **Database Interaction**: DDL table creation, index creation, table teardown.
- **Tests Covering It**:
  - `tests/unit/test_evokg_models_and_migration.py`
  - `tests/integration/test_evokg_real_postgresql_acceptance.py`
- **Current Implementation Limitations**: None; strictly verified against PostgreSQL 16 with pgvector.

---

### 2.3 Relation Taxonomy & Exclusivity Policy
- **Component Name**: Code Relation Taxonomy & Exclusivity Engine
- **File Path**: `apps/api/src/services/code_atom/taxonomy.py`
- **Class and Function Names**:
  - `class RelationTaxonomyEntry`
  - `class CodeRelationTaxonomy`
  - `CodeRelationTaxonomy.classify(relation: RelationType | str) -> RelationTaxonomyEntry`
  - `CodeRelationTaxonomy.is_exclusive(relation: RelationType | str) -> bool`
  - `CodeRelationTaxonomy.normalize_predicate(relation: RelationType | str) -> RelationType | None`
  - `CodeRelationTaxonomy.generate_scope_key(...) -> tuple[str, bool]`
  - `CodeRelationTaxonomy.can_supersede(...) -> bool`
- **Responsibility**: Governs whether a relation can supersede existing assertions. Strictly categorizes relations into:
  - `EXCLUSIVE`: `DEFINES`, `DEFINES_RETURN_TYPE`, `HAS_SIGNATURE`, `ASSIGNED_TYPE`, `MODULE_LOCATION`, `INHERITS`.
  - `NON_EXCLUSIVE`: `CALLS`, `IMPORTS`, `REFERENCES`, `RAISES`, `MUTATES`, `CONFIGURES`, `VALIDATES`.
  Generates deterministic scope keys (`overload:<idx>`, `scope:<id>`, `base:<idx>`, `symbol:<name>`, `canonical_path`, `concurrent`) so that different overload signatures or multiple inheritance bases do not falsely terminate each other.
- **Input and Output**:
  - *Input*: Predicate string or enum, symbol names, indices.
  - *Output*: `RelationTaxonomyEntry`, boolean exclusivity, or `(scope_key, is_uncertain)` tuple.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom` (`PropertyExclusivity`, `RelationType`, `ScopeKeyStrategy`, `TemporalSupersessionPolicy`).
- **External Dependencies**: `dataclasses`.
- **Database Interaction**: In-memory specification engine.
- **Tests Covering It**:
  - `tests/unit/test_evokg_relation_taxonomy.py` (10 tests)
  - `tests/unit/test_evokg_contradiction.py` (16 tests)
- **Current Implementation Limitations**: Unclassified predicates default to non-exclusive with `UNCERTAIN` strategy to prevent accidental deletion of valid facts.

---

### 2.4 EvoKG Contradiction & Lifecycle Engine
- **Component Name**: EvoKG Contradiction Engine
- **File Path**: `apps/api/src/services/evokg/contradiction.py`
- **Class and Function Names**:
  - `class ResolutionAction(str, Enum)`
  - `class ResolutionDiagnostic(BaseModel)`
  - `class ContradictionResolutionResult`
  - `class EvoKGContradictionEngine`
  - `EvoKGContradictionEngine.resolve_contradictions(self, relations: list[TemporalCodeRelation], existing_relations: list[TemporalCodeRelation] | None = None) -> ContradictionResolutionResult`
  - `EvoKGContradictionEngine.is_ancestor(self, ancestor_sha: str | None, descendant_sha: str | None) -> bool | None`
  - `EvoKGContradictionEngine.can_supersede_lineage(self, rel_old: TemporalCodeRelation, rel_new: TemporalCodeRelation) -> tuple[bool, str]`
  - `EvoKGContradictionEngine._resolve_exclusive_evolution(...)`
  - `EvoKGContradictionEngine._resolve_non_exclusive_evolution(...)`
- **Responsibility**: Implements the temporal lifecycle resolver and contradiction resolution algorithm (arXiv:2509.15464 §3.2).
  1. *Confidence Gating*: New assertions must meet or exceed `min_confidence_threshold = 0.65` to supersede active assertions. Assertions below 0.65 are flagged as `conflicting_relations` (`has_temporal_conflict=True`, `confidence_level="UNCERTAIN"`) without terminating active validity.
  2. *Supersession Linking*: When an exclusive assertion arrives with sufficient confidence and matching scope key, it sets `valid_to = new_assertion.valid_from`, points `superseded_by_id`, and links `supersedes_id`.
  3. *Out-of-Order History Insertion*: If an incoming historical assertion is older than an active assertion, it bounds the historical interval (`valid_to = active.valid_from`) without overwriting active validity.
  4. *Git DAG Ancestry Verification*: Verifies commit lineage via `is_ancestor`. Isolated branches without merge ancestry cannot supersede each other.
- **Input and Output**:
  - *Input*: `relations: list[TemporalCodeRelation]`, `existing_relations: list[TemporalCodeRelation]`.
  - *Output*: `ContradictionResolutionResult` categorizing relations into `active_relations`, `superseded_relations`, `historical_relations`, `conflicting_relations`, and detailed `diagnostics`.
- **Internal Dependencies**: `apps.api.src.schemas.code_atom`, `apps.api.src.services.code_atom.taxonomy.CodeRelationTaxonomy`, `apps.api.src.services.code_atom.relation_resolver.CodeEntityResolver`.
- **External Dependencies**: `dataclasses`, `enum`, `datetime`, `logging`, `pydantic`.
- **Database Interaction**: None directly; called by `EvoKGPersistenceService`.
- **Tests Covering It**:
  - `tests/unit/test_evokg_contradiction.py` (16 tests)
  - `tests/integration/test_evokg_real_postgresql_acceptance.py` (14 tests)
- **Current Implementation Limitations**: When commit parents are not provided (shallow repository clones), commit DAG ancestry verification gracefully falls back to timestamp comparison on the same branch.

---

### 2.5 EvoKG Persistence Service
- **Component Name**: EvoKG Persistence Service
- **File Path**: `apps/api/src/services/evokg/service.py`
- **Class and Function Names**:
  - `class EvoKGPersistenceService`
  - `EvoKGPersistenceService.__init__(self, contradiction_engine: EvoKGContradictionEngine | None = None, entity_resolver: CodeEntityResolver | None = None)`
  - `EvoKGPersistenceService.persist_relations(...) -> ContradictionResolutionResult`
  - `EvoKGPersistenceService.get_active_outgoing(...) -> list[EvoKGTriplet]`
  - `EvoKGPersistenceService.get_active_incoming(...) -> list[EvoKGTriplet]`
  - `EvoKGPersistenceService.get_temporal_history(...) -> list[EvoKGTriplet]`
  - `EvoKGPersistenceService.get_conflicts(...) -> list[EvoKGTriplet]`
  - `EvoKGPersistenceService._normalize_relation(...) -> TemporalCodeRelation`
  - `EvoKGPersistenceService._triplet_to_relation(t: EvoKGTriplet) -> TemporalCodeRelation`
- **Responsibility**: Database adapter connecting in-memory contradiction resolution to PostgreSQL.
  - Locks affected subject rows using `FOR UPDATE` concurrency control under PostgreSQL.
  - Enforces fingerprint-based idempotency (`ix_evokg_repo_fingerprint`), preventing duplicate inserts.
  - Executes updates on existing records (`valid_to`, `superseded_by_id`).
  - Persists new `EvoKGTriplet` records with AST foreign key links (`file_id`, `symbol_id`).
  - Provides high-performance indexed query APIs for active traversal and point-in-time (`as_of`) history.
- **Input and Output**:
  - *Input*: `AsyncSession`, `repository_id: UUID`, `relations: list[TemporalCodeRelation]`, `branch: str`.
  - *Output*: `ContradictionResolutionResult`, committed database entities.
- **Internal Dependencies**: `apps.api.src.models.evokg.EvoKGTriplet`, `contradiction.py`, `taxonomy.py`, `relation_resolver.py`.
- **External Dependencies**: `sqlalchemy.ext.asyncio.AsyncSession`, `uuid`, `logging`.
- **Database Interaction**: Transactional SELECT (with FOR UPDATE), INSERT, and UPDATE on `evokg_triplets`.
- **Tests Covering It**:
  - `tests/unit/test_evokg_persistence.py` (11 tests)
  - `tests/unit/test_evokg_ingestion.py` (6 tests)
  - `tests/integration/test_evokg_real_postgresql_acceptance.py` (14 tests)
- **Current Implementation Limitations**: Requires an open database transaction; caller must manage commit/rollback boundaries.

---

### 2.6 EvoReasoner Route Planner
- **Component Name**: EvoReasoner Multi-Route Query Planner
- **File Path**: `apps/api/src/services/evoreasoner/planner.py`
- **Class and Function Names**:
  - `class EvoRoutePlanner`
  - `EvoRoutePlanner.create_hop(...) -> ReasoningHop`
  - `EvoRoutePlanner.plan_routes(query_text: str, analyzed_query: AnalyzedQuery | None = None, temporal_intent: StructuredTemporalIntent | None = None, config: EvoPlannerConfig | None = None, seed_entities: list[str] | None = None) -> MultiRoutePlan`
  - `EvoRoutePlanner.generate_multi_route_plan(...) -> MultiRoutePlan`
  - `EvoRoutePlanner._generate_perspective_routes(...)`
  - `EvoRoutePlanner._generate_multi_entity_routes(...)`
  - `EvoRoutePlanner._detect_relation_biases(q_lower: str) -> list[RelationType]`
- **Responsibility**: Generates alternative graph-reasoning routes conditioned on temporal query intent (`CURRENT`, `HISTORICAL`, `EVOLUTION`, `DIFF`, `INTERVAL`, `BEFORE`, `AFTER`) and semantic relations (arXiv:2509.15464 §3.3). Produces routes across 5 perspectives:
  1. `STRUCTURAL` (definitions, containment, interfaces)
  2. `BEHAVIORAL_CALLGRAPH` (invocations, state mutations)
  3. `ARCHITECTURAL_DEPENDENCY` (imports, module locations)
  4. `TEMPORAL_LINEAGE` (supersession, commit evolution)
  5. `SIGNATURE_SPEC` (signatures, return types)
  Deduplicates routes via `RouteDeduplicator` and bounds output to top-N (`max_selected_routes = 3`, `max_route_hops = 4`).
- **Input and Output**:
  - *Input*: `query_text: str`, optional `analyzed_query`, `temporal_intent`, `config`.
  - *Output*: `MultiRoutePlan` with selected routes, estimated costs, and planning diagnostics.
- **Internal Dependencies**: `apps.api.src.schemas.evoreasoner`, `apps.api.src.services.code_atom.taxonomy`, `cost_estimator.py`, `deduplicator.py`, `query_analyzer.py`, `memotime.py`.
- **External Dependencies**: `logging`.
- **Database Interaction**: None (pure in-memory planner).
- **Tests Covering It**:
  - `tests/unit/test_evoreasoner_planner.py` (14 tests)
  - `tests/unit/test_evoreasoner_production_readiness.py` (5 tests)
- **Current Implementation Limitations**: Empty or whitespace queries return an empty plan with `empty_query` diagnostic; ambiguous/contradictory queries safely return an unexpanded plan.

---

### 2.7 Route Cost Estimator
- **Component Name**: Route Cost Estimator
- **File Path**: `apps/api/src/services/evoreasoner/cost_estimator.py`
- **Class and Function Names**:
  - `class RouteCostEstimator`
  - `RouteCostEstimator.calculate_route_cost(hops: list[ReasoningHop], intent_type: TemporalIntentType, config: EvoPlannerConfig | None = None) -> RouteCostBreakdown`
  - `RouteCostEstimator.get_relation_branching(relation: RelationType | str) -> float`
  - `RouteCostEstimator.get_relation_entropy(relation: RelationType | str) -> float`
  - `RouteCostEstimator.compute_temporal_distance(source_temporal: str, target_temporal: str) -> float`
  - `DEFAULT_BRANCHING_FACTORS: dict[RelationType, float]`
  - `DEFAULT_ENTROPY_VALUES: dict[RelationType, float]`
- **Responsibility**: Calculates an explainable, deterministic exploration cost for candidate routes:
  $$\text{Cost} = w_{\text{hops}} \cdot H + w_{\text{branch}} \cdot B + w_{\text{entropy}} \cdot E + w_{\text{temporal}} \cdot \Delta T + w_{\text{complexity}} \cdot C$$
  Grounds branching factors in `CodeRelationTaxonomy`: exclusive relations have branching factor 1.0 and entropy 0.0; non-exclusive relations scale up to 5.0. Route cost represents exploration efficiency, strictly decoupled from evidence confidence.
- **Input and Output**:
  - *Input*: `hops: list[ReasoningHop]`, `intent_type: TemporalIntentType`, `config`.
  - *Output*: `RouteCostBreakdown` with individual cost terms and `total_cost`.
- **Internal Dependencies**: `apps.api.src.schemas.evoreasoner`, `apps.api.src.services.code_atom.taxonomy.CodeRelationTaxonomy`.
- **External Dependencies**: `logging`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_evoreasoner_planner.py`
  - `tests/unit/test_evoreasoner_beam_search.py`
- **Current Implementation Limitations**: Cost parameters use calibrated heuristic weights (`w_hops=1.0`, `w_branch=0.5`, `w_entropy=0.3`, `w_temporal=0.4`, `w_complexity=0.2`).

---

### 2.8 Route Deduplicator
- **Component Name**: Route Canonical Deduplicator
- **File Path**: `apps/api/src/services/evoreasoner/deduplicator.py`
- **Class and Function Names**:
  - `class RouteDeduplicator`
  - `RouteDeduplicator.compute_canonical_key(hops: list[ReasoningHop]) -> str`
  - `RouteDeduplicator.are_routes_equivalent(route_a: ReasoningRoute, route_b: ReasoningRoute) -> bool`
  - `RouteDeduplicator.deduplicate_routes(routes: list[ReasoningRoute]) -> list[ReasoningRoute]`
- **Responsibility**: Computes deterministic structural signatures for reasoning routes:
  Format: `[source_entity]--CANONICAL_RELATION:INVERSE-->[target_entity]==>...`
  Identifies and merges structurally identical routes generated from multiple perspectives, retaining the route instance with the lowest exploration cost.
- **Input and Output**:
  - *Input*: `routes: list[ReasoningRoute]`.
  - *Output*: Deduplicated `list[ReasoningRoute]`.
- **Internal Dependencies**: `apps.api.src.schemas.evoreasoner.ReasoningRoute`.
- **External Dependencies**: Standard library.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_evoreasoner_planner.py`
- **Current Implementation Limitations**: Compares canonical relations; alias differences (e.g. `CALLS` vs `INVOKES`) are normalized prior to signature hashing.

---

### 2.9 Beam Search Engine
- **Component Name**: EvoReasoner Beam Search Engine
- **File Path**: `apps/api/src/services/evoreasoner/beam_search.py`
- **Class and Function Names**:
  - `class EvoBeamSearchEngine`
  - `EvoBeamSearchEngine.search_paths(session: AsyncSession, repository_id: UUID, route_plan: MultiRoutePlan | None = None, branch: str = "main", ...) -> PathSearchResult`
  - `EvoBeamSearchEngine._expand_route(...)`
  - `EvoBeamSearchEngine._query_traversal_triplets(...)`
  - `class _CandidateBeamPath`
- **Responsibility**: Executes bounded beam search over persisted `evokg_triplets` in PostgreSQL:
  - Traverses forward and inverse edges adhering to the sequence of planned `ReasoningHop` steps.
  - Enforces strict entity continuity between consecutive hops (`edge[i].object_id == edge[i+1].subject_id`).
  - Prevents cycles by tracking visited node sets.
  - Bounded by `beam_width = 3`, `max_path_depth = 4`, `max_expansions_per_node = 5`, and total expansion limit (50).
  - Evaluates explainable path ranking scores via `PathScorer`.
  - Produces typed `EvidencePath` items with commit SHAs, validity spans, and score breakdowns.
- **Input and Output**:
  - *Input*: `AsyncSession`, `repository_id: UUID`, `plan: MultiRoutePlan`, `branch: str`, optional temporal bounds (`as_of`, `until`).
  - *Output*: `PathSearchResult` with ranked `paths: list[EvidencePath]`, total paths explored, and search diagnostics.
- **Internal Dependencies**: `apps.api.src.models.evokg.EvoKGTriplet`, `apps.api.src.schemas.evoreasoner.*`, `path_scorer.py`.
- **External Dependencies**: `sqlalchemy`, `asyncio`, `logging`, `time`.
- **Database Interaction**: Reads from `evokg_triplets` with branch, repository, and temporal interval filters.
- **Tests Covering It**:
  - `tests/unit/test_evoreasoner_beam_search.py` (33 tests)
  - `tests/integration/test_evoreasoner_benchmark.py` (7 tests)
  - `tests/integration/test_evoreasoner_postgresql_acceptance.py` (8 tests)
- **Current Implementation Limitations**: Max depth is capped at 4 hops to ensure retrieval latency remains well within interactive context budgets (< 50ms).

---

### 2.10 Evidence Path Scorer
- **Component Name**: Evidence Path Scorer
- **File Path**: `apps/api/src/services/evoreasoner/path_scorer.py`
- **Class and Function Names**:
  - `class PathScorer`
  - `PathScorer.evaluate_path(edges: list[EvidenceEdge], planned_hops: list[ReasoningHop], intent_type: TemporalIntentType | str, config: BeamSearchConfig | None = None, ...) -> tuple[float, PathScoreBreakdown]`
- **Responsibility**: Computes transparent, explainable path ranking scores:
  $$\text{Score} = w_{\text{conf}} \cdot S_{\text{conf}} + w_{\text{rel}} \cdot S_{\text{rel}} + w_{\text{cont}} \cdot S_{\text{cont}} + w_{\text{temp}} \cdot S_{\text{temp}} - w_{\text{unc}} \cdot P_{\text{unc}} - w_{\text{conflict}} \cdot P_{\text{conflict}} - w_{\text{len}} \cdot P_{\text{len}}$$
  - $S_{\text{conf}}$: Mean evidence confidence of traversed triplets.
  - $S_{\text{rel}}$: Relation alignment against planned hops.
  - $S_{\text{cont}}$: Entity continuity across consecutive hops.
  - $S_{\text{temp}}$: Temporal compatibility with the query intent (e.g., active vs superseded).
  - Penalties for unverified assertions ($P_{\text{unc}}$) and unresolved temporal conflicts ($P_{\text{conflict}}$).
  - Clamped strictly to $[0.0, 1.0]$.
- **Input and Output**:
  - *Input*: `edges: list[EvidenceEdge]`, `planned_hops: list[ReasoningHop]`, `intent_type`, `config`.
  - *Output*: `tuple[float, PathScoreBreakdown]`.
- **Internal Dependencies**: `apps.api.src.schemas.evoreasoner`, `apps.api.src.services.context_engine.memotime.TemporalIntentType`.
- **External Dependencies**: Standard library (`datetime`).
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_evoreasoner_beam_search.py`
  - `tests/integration/test_evoreasoner_benchmark.py`
- **Current Implementation Limitations**: Scoring weights default to `w_conf=0.35`, `w_rel=0.25`, `w_cont=0.20`, `w_temp=0.20`, `w_unc=0.15`, `w_conflict=0.20`, `w_len=0.05`.

---

### 2.11 Proof-Chain Validator
- **Component Name**: Proof-Chain Validator
- **File Path**: `apps/api/src/services/evoreasoner/validator.py`
- **Class and Function Names**:
  - `class ProofChainValidator`
  - `ProofChainValidator.validate_and_convert_path(path: EvidencePath, expected_repo_id: UUID | None = None, expected_branch: str = "main", temporal_intent: TemporalIntentType = TemporalIntentType.CURRENT) -> tuple[bool, str | None, GroundedProofChain | None]`
- **Responsibility**: Enforces structural and security invariants on traversed evidence paths before aggregation:
  1. Rejects paths with broken entity continuity (`curr_edge.object_id != next_edge.subject_id`).
  2. Enforces repository and branch boundary isolation (`path.repository_id == expected_repo_id`, `path.branch == expected_branch`).
  3. Computes validity interval intersections ($\max(valid\_from) \le \min(valid\_to)$); flags contradictory intervals as conflicts.
  4. Converts verified paths into `GroundedProofChain` objects with step-by-step `ProofChainHop` items.
- **Input and Output**:
  - *Input*: `EvidencePath`, expected repository ID, branch, temporal intent.
  - *Output*: `tuple[bool, str | None, GroundedProofChain | None]`.
- **Internal Dependencies**: `apps.api.src.schemas.evoreasoner.*`.
- **External Dependencies**: `uuid`, `datetime`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_evoreasoner_proof_chains.py` (30 tests)
  - `tests/unit/test_code_lane_hardening.py` (12 tests)
- **Current Implementation Limitations**: Chains containing uncertainty or conflicts are preserved with explicit tags and penalties rather than silently dropped, ensuring transparent explainability.

---

### 2.12 Proof-Chain Aggregator
- **Component Name**: Proof-Chain Aggregator
- **File Path**: `apps/api/src/services/evoreasoner/aggregator.py`
- **Class and Function Names**:
  - `class ProofChainAggregator`
  - `ProofChainAggregator.aggregate_paths(paths: list[EvidencePath], query_text: str = "", temporal_intent: TemporalIntentType = TemporalIntentType.CURRENT, repository_id: UUID | None = None, branch: str = "main", config: ProofAggregationConfig | None = None) -> AggregatedProofResult`
  - `ProofChainAggregator._deduplicate_equivalent_chains(...)`
  - `ProofChainAggregator._combine_complementary_chains(...)`
  - `ProofChainAggregator._evaluate_conflicts_and_uncertainty(...)`
  - `ProofChainAggregator._generate_grounded_explanation(chain: GroundedProofChain) -> str`
- **Responsibility**: Aggregates validated proof chains:
  - Validates each path via `ProofChainValidator`.
  - Deduplicates equivalent paths sharing identical endpoints and intermediate hops, applying a corroboration bonus (`+0.05`) for multi-source confirmation.
  - Combines complementary paths with verifiable entity handover into multi-hop synthesis chains.
  - Preserves conflicting assertions with penalties and diagnostic warnings.
  - Generates natural-language grounded explanations (e.g. `"AuthenticationService calls TokenValidator (Active since ...) which validates JWT tokens"`).
  - Bounds output to top-N proof chains (`max_proof_chains = 3`).
- **Input and Output**:
  - *Input*: `paths: list[EvidencePath]`, `query_text: str`, `temporal_intent`, `repository_id`, `branch`, `config`.
  - *Output*: `AggregatedProofResult` containing `chains: list[GroundedProofChain]` and complete aggregation diagnostics.
- **Internal Dependencies**: `apps.api.src.schemas.evoreasoner.*`, `validator.py`, `apps.api.src.services.code_atom.taxonomy.CodeRelationTaxonomy`.
- **External Dependencies**: `uuid`, `logging`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_evoreasoner_proof_chains.py` (30 tests)
  - `tests/integration/test_evoreasoner_benchmark.py` (7 tests)
- **Current Implementation Limitations**: Limits combined synthesis chains to a maximum of 4 hops to avoid unbounded combinatorial growth.
