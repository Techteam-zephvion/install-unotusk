# T4 — STAR-RAG Technical Component Inventory

## 1. Overview and Architecture

Track 4 implements **STAR-RAG** (Spatio-Temporal Abstraction & Reasoning for Retrieval-Augmented Generation), grounded in Zhu et al. (arXiv:2510.16715, *"Right Answer at the Right Time — Temporal Retrieval-Augmented Generation via Graph Summarization"*).

STAR-RAG abstracts grounded code events $f = (s, r, o, t)$ into a generalized temporal rule graph where nodes represent abstract relation patterns $u = \langle c_s, r, c_o \rangle$. It uses Apriori frequent relation mining to induce entity categories, employs Minimum Description Length (MDL) model selection to prune redundant edges, and performs query-time Seeded Personalized PageRank (PPR) with Dirichlet smoothing and hub attenuation to propagate relevance back to grounded code evidence.

```
                      ┌─────────────────────────────────┐
                      │ Expanded Candidates (Retriever) │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │    Grounded Event Extraction    │
                      │    f = (s, r, o, t)             │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │      EntityRelationMiner        │
                      │ (Apriori Frequent Pattern Mining│
                      │  inducing Entity Types c_s, c_o)│
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │   TemporalRuleGraphBuilder      │
                      │  (Rule nodes u=<c_s, r, c_o>    │
                      │   Hamming distance <= 1 edges)  │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │       MdlGraphSelector          │
                      │ (L(M) + L_cov(G|M) + L_time(G|M)│
                      │  Greedy Edge Pruning Selection) │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │      SeededPprRetriever         │
                      │ (Anchor Gating, Personalization │
                      │  Dirichlet Smoothing, Power Iter│
                      │  Hub Attenuation)               │
                      └────────────────┬────────────────┘
                                       │
                                       ▼
                      ┌─────────────────────────────────┐
                      │   StarRagContextService         │
                      │ (Inject star_rag_ppr Signal     │
                      │  into Ranked Candidates)        │
                      └─────────────────────────────────┘
```

---

## 2. Component Inventory

### 2.1 Temporal Event & Rule Graph Structures
- **Component Name**: Temporal Event & Rule Node Graph Representation
- **File Path**: `apps/api/src/services/context_engine/star_rag.py`
- **Class and Function Names**:
  - `class TemporalCodeEvent`
  - `class RuleNode`
  - `class StarRagResult`
- **Responsibility**: Defines fundamental graph primitives:
  - `TemporalCodeEvent`: Represents an atomic grounded temporal event $f = (s, r, o, t)$ extracted from retrieved code chunks, AST symbols, commit deltas, or temporal relations.
  - `RuleNode`: Represents an abstract rule node $u = \langle c_s, r, c_o \rangle$ grouping events that share category bindings $c_s, c_o$ and relation $r$.
  - `StarRagResult`: Envelope encapsulating ranked candidates, rule graph nodes, selected edges, top rules, PPR distribution, and initial/final MDL costs.
- **Input and Output**: Data containers for the STAR-RAG summarization pipeline.
- **Internal Dependencies**: `apps.api.src.services.context_engine.retriever.RetrievedCandidate`.
- **External Dependencies**: `dataclasses`, `datetime`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_star_rag.py` (19 tests)
  - `tests/integration/test_star_rag_real_repo_benchmark.py` (4 tests)
- **Current Implementation Limitations**: In-memory representation operating over retrieved candidate sets.

---

### 2.2 Entity Relation Miner (Apriori Pattern Mining)
- **Component Name**: Entity Relation Miner
- **File Path**: `apps/api/src/services/context_engine/star_rag.py`
- **Class and Function Names**:
  - `class EntityRelationMiner`
  - `EntityRelationMiner.mine_relation_patterns(events: list[TemporalCodeEvent], min_support: int = 2) -> dict[str, str]`
  - `EntityRelationMiner._apriori_frequent_itemsets(baskets: list[set[str]], min_support: int) -> list[set[str]]`
  - `EntityRelationMiner._extract_lexical_category(entity_name: str) -> str`
- **Responsibility**: Induces abstract entity types without manual ontology annotations using the classic Apriori algorithm (Paper Section 3.2 & Appendix A).
  1. Gathers relation profiles for every entity (the set of relations it participates in as subject or object).
  2. Runs candidate itemset generation and pruning ($L_1 \to C_2 \to L_2 \to \dots$) based on `min_support`.
  3. Maps frequent relation itemsets to cluster keys (`TYPE_PROFILE_<hash>`).
  4. For single-occurrence or rare entities, falls back to lexical camelCase/snake_case suffix clustering (`_extract_lexical_category`).
- **Input and Output**:
  - *Input*: `events: list[TemporalCodeEvent]`, `min_support: int = 2`.
  - *Output*: `dict[str, str]` mapping each entity name to its abstract cluster category $c$.
- **Internal Dependencies**: `TemporalCodeEvent`.
- **External Dependencies**: `itertools.combinations`, `re`, `logging`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_star_rag.py` (`test_apriori_frequent_pattern_mining`, `test_lexical_category_clustering`)
- **Current Implementation Limitations**: Entities participating in completely unique single relations default to lexical token suffix categories (`TYPE_AUTH`, `TYPE_SERVICE`, etc.).

---

### 2.3 Temporal Rule Graph Builder
- **Component Name**: Temporal Rule Graph Builder
- **File Path**: `apps/api/src/services/context_engine/star_rag.py`
- **Class and Function Names**:
  - `class TemporalRuleGraphBuilder`
  - `TemporalRuleGraphBuilder.build_rule_graph(events: list[TemporalCodeEvent], entity_types: dict[str, str]) -> tuple[dict[str, RuleNode], set[tuple[str, str]]]`
  - `TemporalRuleGraphBuilder._hamming_distance(node_a: RuleNode, node_b: RuleNode) -> int`
  - `TemporalRuleGraphBuilder.collect_event_spans(node: RuleNode) -> list[float]`
- **Responsibility**: Constructs the unpruned candidate rule graph:
  1. Groups grounded events into `RuleNode` instances $u = \langle c_s, r, c_o \rangle$.
  2. Generates directed candidate edges between rule nodes whose Hamming distance is $\le 1$ (sharing at least two of the three components $c_s, r, c_o$).
  3. Collects chronological event timestamps and computes interval time deltas (in hours) between successive events mapped to each rule.
- **Input and Output**:
  - *Input*: `events: list[TemporalCodeEvent]`, `entity_types: dict[str, str]`.
  - *Output*: `tuple[dict[str, RuleNode], set[tuple[str, str]]]` (rule nodes dictionary and candidate directed edge set).
- **Internal Dependencies**: `TemporalCodeEvent`, `RuleNode`.
- **External Dependencies**: `datetime`, `logging`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_star_rag.py` (`test_rule_graph_construction_hamming_distance`, `test_event_span_collection`)
- **Current Implementation Limitations**: Directed edges are generated when consecutive events respect temporal chronological ordering or share structural type overlap.

---

### 2.4 Minimum Description Length (MDL) Model Selector
- **Component Name**: MDL Graph Selector
- **File Path**: `apps/api/src/services/context_engine/star_rag.py`
- **Class and Function Names**:
  - `class MdlGraphSelector`
  - `MdlGraphSelector.compute_mdl_cost(rule_nodes: dict[str, RuleNode], edges: set[tuple[str, str]], all_events: list[TemporalCodeEvent]) -> float`
  - `MdlGraphSelector.model_cost(rule_nodes: dict[str, RuleNode], edges: set[tuple[str, str]]) -> float`
  - `MdlGraphSelector.coverage_cost(rule_nodes: dict[str, RuleNode], all_events: list[TemporalCodeEvent]) -> float`
  - `MdlGraphSelector.temporal_cost(rule_nodes: dict[str, RuleNode]) -> float`
  - `MdlGraphSelector.prune_edges_mdl(rule_nodes: dict[str, RuleNode], candidate_edges: set[tuple[str, str]], all_events: list[TemporalCodeEvent]) -> tuple[set[tuple[str, str]], float, float]`
- **Responsibility**: Selects the optimal graph summary using the Minimum Description Length principle (Paper Section 3.3):
  $$\mathcal{L}(G, M) = \mathcal{L}(M) + \mathcal{L}_{\text{cov}}(G \mid M) + \mathcal{L}_{\text{time}}(G \mid M)$$
  - $\mathcal{L}(M)$: Model cost encoding rule nodes and directed chain edges.
  - $\mathcal{L}_{\text{cov}}(G \mid M)$: Coverage cost modeling unexplained residual events via log-binomial coefficients:
    $$\log_2 \binom{|E_{\text{corpus}}|}{\text{uncovered}}$$
  - $\mathcal{L}_{\text{time}}(G \mid M)$: Temporal cost modeling event interval spans via exponential distribution likelihood:
    $$\sum \lambda \Delta t - \log(\lambda)$$
  - `prune_edges_mdl`: Executes greedy edge pruning, evaluating each candidate edge and retaining only those that strictly decrease total MDL description length.
- **Input and Output**:
  - *Input*: `rule_nodes: dict[str, RuleNode]`, `candidate_edges: set[tuple[str, str]]`, `all_events: list[TemporalCodeEvent]`.
  - *Output*: `tuple[set[tuple[str, str]], float, float]` (pruned edge set, initial MDL cost, final compressed MDL cost).
- **Internal Dependencies**: `RuleNode`, `TemporalCodeEvent`, `TemporalRuleGraphBuilder`.
- **External Dependencies**: `math`, `logging`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_star_rag.py` (`test_mdl_cost_components`, `test_mdl_greedy_edge_pruning`)
  - `tests/integration/test_star_rag_real_repo_benchmark.py` (4 tests)
- **Current Implementation Limitations**: Greedy edge evaluation runs in descending support order; edges whose removal does not decrease MDL are permanently pruned.

---

### 2.5 Seeded Personalized PageRank (PPR) Engine
- **Component Name**: Seeded PPR Retriever
- **File Path**: `apps/api/src/services/context_engine/star_rag.py`
- **Class and Function Names**:
  - `class SeededPprRetriever`
  - `SeededPprRetriever.compute_ppr(rule_nodes: dict[str, RuleNode], edges: set[tuple[str, str]], query_anchors: dict[str, float], alpha: float = 0.2, epsilon: float = 1e-6, max_iter: int = 100, hub_attenuation: bool = True) -> dict[str, float]`
  - `SeededPprRetriever.build_transition_matrix(rule_nodes: dict[str, RuleNode], edges: set[tuple[str, str]], hub_attenuation: bool = True) -> dict[str, dict[str, float]]`
- **Responsibility**: Computes query-time relevance propagation across the summarized rule graph (Paper Section 3.4):
  1. *Personalization Vector* $\mathbf{p}$: Seeds distribution using query anchor relevance blended with Dirichlet-smoothed corpus coverage.
  2. *Transition Matrix* $\mathbf{M}$: Normalizes edge transitions out of each rule node. When `hub_attenuation = True`, penalizes high-degree nodes by damping transition probabilities proportional to inverse out-degree $1 / \sqrt{\text{degree}}$.
  3. *Power Iteration*: Iteratively solves:
     $$\mathbf{r}^{(t+1)} = (1 - \alpha) \mathbf{M}^T \mathbf{r}^{(t)} + \alpha \mathbf{p}$$
     terminating when $\|\mathbf{r}^{(t+1)} - \mathbf{r}^{(t)}\|_1 < \epsilon$ or iterations exceed `max_iter = 100`.
- **Input and Output**:
  - *Input*: `rule_nodes`, `edges`, `query_anchors: dict[str, float]`, $\alpha = 0.2$, $\epsilon = 10^{-6}$, `hub_attenuation: bool`.
  - *Output*: `dict[str, float]` mapping each rule node ID to its stationary PPR probability score.
- **Internal Dependencies**: `RuleNode`, `settings.py`.
- **External Dependencies**: `math`, `logging`.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_star_rag.py` (`test_seeded_ppr_power_iteration_convergence`, `test_hub_attenuation`)
- **Current Implementation Limitations**: Isolated rule nodes with zero edges receive the uniform restart probability proportional to their personalization anchor weight.

---

### 2.6 Anchor & Confidence Gating System
- **Component Name**: STAR-RAG Anchor & Confidence Gate
- **File Path**: `apps/api/src/services/context_engine/star_rag.py`
- **Class and Function Names**:
  - `StarRagContextService.extract_query_anchors(analyzed_query: Any, query_text: str, candidates: list[RetrievedCandidate]) -> dict[str, float]`
  - Threshold constant: `STAR_RAG_MIN_ANCHOR_SCORE` in `apps.api.src.config.settings` (default `1.0` unnormalized / `0.40` normalized).
- **Responsibility**: Enforces structural gating before executing graph summarization and PPR reasoning.
  - Inspects query keywords, symbols, paths, and candidate scores.
  - Matches rule nodes against query entities.
  - If maximum anchor relevance fails to meet `STAR_RAG_MIN_ANCHOR_SCORE` (e.g. queries lacking solid symbol or entity overlap), STAR-RAG cleanly abstains and returns candidates unchanged (`is_fallback = True`, `fallback_reason = "No query anchor matched rule graph nodes above threshold"`).
- **Input and Output**:
  - *Input*: `AnalyzedQuery`, query text, `RetrievedCandidate` list.
  - *Output*: `dict[str, float]` mapping matched entity names to anchor weights, or empty dict if gate fails.
- **Internal Dependencies**: `apps.api.src.config.settings`, `RetrievedCandidate`.
- **External Dependencies**: Standard library.
- **Database Interaction**: None.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_star_rag.py` (`test_anchor_gating_abstention_on_weak_query`)
- **Current Implementation Limitations**: Queries containing purely generic conversational language without code identifiers are gated off by design to avoid hallucinated graph expansions.

---

### 2.7 Context Service & Ranking Integration
- **Component Name**: STAR-RAG Context Service & Ranker Signal Injection
- **File Path**: `apps/api/src/services/context_engine/star_rag.py`
- **Class and Function Names**:
  - `class StarRagContextService`
  - `StarRagContextService.is_enabled() -> bool`
  - `StarRagContextService.run_star_rag_pipeline(candidates: list[RetrievedCandidate], analyzed_query: Any | None = None, query_text: str = "") -> StarRagResult`
  - `StarRagContextService.extract_grounded_events(candidates: list[RetrievedCandidate]) -> list[TemporalCodeEvent]`
  - `StarRagContextService.map_ppr_to_candidates(rule_nodes: dict[str, RuleNode], ppr_dist: dict[str, float], candidates: list[RetrievedCandidate]) -> list[RetrievedCandidate]`
- **Responsibility**: Top-level STAR-RAG orchestrator:
  1. Extracts grounded `TemporalCodeEvent` items from candidate code chunks, AST symbols, commit messages, and temporal relations.
  2. Runs Apriori pattern mining via `EntityRelationMiner`.
  3. Builds rule graph via `TemporalRuleGraphBuilder`.
  4. Prunes edges via `MdlGraphSelector`.
  5. Evaluates anchor relevance gate; falls back cleanly if below threshold.
  6. Executes `SeededPprRetriever.compute_ppr`.
  7. Injects normalized `star_rag_ppr` scores into candidate `signals` dictionary.
  8. Propagates `star_rag_ppr` into `MultiSignalRanker` (which applies a `1.6` signal multiplier in ranking).
- **Input and Output**:
  - *Input*: `candidates: list[RetrievedCandidate]`, optional `analyzed_query`, `query_text`.
  - *Output*: `StarRagResult` with updated candidates, diagnostic metrics, and compression statistics.
- **Internal Dependencies**: `apps.api.src.config.settings`, `MultiSignalRanker`, `RetrievedCandidate`.
- **External Dependencies**: `logging`.
- **Database Interaction**: None directly; called by `ProjectContextEngine.investigate`.
- **Tests Covering It**:
  - `tests/unit/test_code_lane_star_rag.py` (19 tests)
  - `tests/integration/test_star_rag_real_repo_benchmark.py` (4 benchmark tests on real repository graphs)
- **Current Implementation Limitations**: Gated by feature flag `settings.STAR_RAG_ENABLED` (defaults to `False`). Requires at least 2 distinct grounded events to build an initial graph; single-chunk queries safely trigger fallback.
