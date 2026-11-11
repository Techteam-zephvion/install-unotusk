# E2 — Stage 1: Ontology Induction Research and Isolated Prototype Report

**Repository:** `Techteam-zephvion/install-unotusk`  
**Track:** E2 — Ontology-Guided Information Extraction  
**Status:** STAGE 1 COMPLETE — PROTOTYPE ISOLATED & EVALUATED  
**Research Paper:** OntoRAG: Hybrid Chunking and Concept Hierarchy Construction for Retrieval-Augmented Generation (arXiv:2506.00664)  
**Architecture Reference:** `AI_PIE_Architecture_V1_Elite.pdf` — Section 25 (E2), Section 23 (EvoKG), Section 24 (E1)  
**Execution Environment:** Isolated Code Lane experimental sandbox (`experiments/e2_ontology_guided_extraction/`)  

---

## 1. Executive Summary

E2 Stage 1 investigates whether ontology-guided extraction and taxonomy induction, adapted from the OntoRAG framework (arXiv:2506.00664), can systematically organize, deduplicate, and enrich Code Lane implementation facts into verifiable architectural knowledge structures.

Building upon the completed E1 Generative IE baseline, E2 developed an isolated, zero-dependency, deterministic prototype that ingests flat extracted code entities, relationships, and commit diffs. It clusters semantically and syntactically related code items, derives canonical candidate ontology concepts, induces cross-concept relationships, and synthesizes multi-level hierarchical taxonomies (`Domain` → `Subsystem` → `Service Component` → `Member Operation`).

### Key Findings
1. **High Concept Coverage:** Evaluated across the 40 E1 benchmark scenarios (218 ingested code entities, 52 relations), the induced ontology achieved **100% Concept Extraction Coverage** against all 79 ground-truth benchmark entities.
2. **Substantial Redundancy Reduction:** At the balanced primary similarity threshold ($\tau = 0.70$), the prototype consolidated 218 raw entity occurrences into 60 canonical candidate concepts, achieving a **72.48% redundancy reduction** while preserving 100% of underlying evidence spans.
3. **Traceable Grounding:** **100% of proposed concepts and 100% of proposed relationships** retain traceable, immutable provenance links (`file_path`, line numbers, `diff_snippet`, and `commit_sha`).
4. **Strict Governance Integrity:** All candidate concepts, candidate relationships, and taxonomy nodes are strictly tagged with `ProposalStatus.PROPOSED_PENDING_REVIEW`. The production V1 ontology (`apps/api/src/services/code_atom/taxonomy.py` and `apps/api/src/schemas/code_atom.py`) remains **100% immutable and unmutated**, verified by regression and negative tests.

---

## 2. OntoRAG Research Mapping to Code Lane

OntoRAG (arXiv:2506.00664) was originally designed for knowledge-intensive question answering over unstructured domain documents (PDFs, scientific literature). To apply its principles to software engineering without introducing hallucinations, we performed a formal mapping to Code Lane:

| OntoRAG Concept (arXiv:2506.00664) | Unstructured Document Domain | Code Lane Adaptation (E2 Prototype) | Status / Decision |
|---|---|---|---|
| **Hybrid Chunking** | Splits PDF pages using formatting headings and fixed token limits | Grounded in AST node boundaries (classes, functions, interfaces) and unified Git diff hunks | **Adapted cleanly**: Syntactic integrity is preserved; arbitrary token slicing discarded. |
| **Key-Term & Definition Extraction** | Identifies salient domain terms, noun phrases, and glossary definitions | Extracts code symbols, type signatures, interfaces, docstrings, and architectural components | **Mapped directly**: Reuses E1 entities (`SERVICE`, `MODULE`, `CLASS`, `FUNCTION`, `CONFIG_PARAM`, `DATASTORE`). |
| **Similarity-Based Concept Clustering** | Dense vector embeddings with cosine similarity thresholds | Multi-signal similarity: (1) Subword token Jaccard (40%), (2) Namespace/file path proximity (30%), (3) Normalized vector embedding cosine (30%) | **Enhanced**: Code has explicit lexical conventions (camelCase/snake_case) and directory topologies that provide stronger signals than text embeddings alone. |
| **Community Detection for Hierarchy** | Leiden / Louvain community detection on term co-occurrence graphs | Deterministic label propagation and connected-component graph partitioning (`LIGHTWEIGHT_DETERMINISTIC_GRAPH_PARTITIONER`) | **Implemented deterministically**: Pure Python graph partitioning with zero C-dependencies. |
| **Hierarchical Concept Tree Construction** | Abstraction levels from broad topics to specific entities | 4-tier architectural hierarchy: Level 0 (`Domain`), Level 1 (`Subsystem`), Level 2 (`Service Component`), Level 3 (`Member Operation`) | **Mapped cleanly**: Directly reflects software engineering architectural patterns. |
| **Cross-Domain Generalization** | Adapts to biomedical, legal, and financial prose | Polyglot code structures (Python, TypeScript, Go) normalized via unified `CandidateConcept` taxonomy | **Preserved**: Agnostic to programming language syntax. |
| **Open-Domain LLM Ontology Expansion** | Unrestricted generative taxonomy generation | Constrained candidate proposals strictly gated behind `PROPOSED_PENDING_REVIEW` | **Discarded for Safety**: Autonomous mutation of core production ontology is strictly forbidden. |

---

## 3. Architecture Alignment with AI-PIE Specification

The E2 prototype aligns directly with the multi-tier intelligence architecture described in `AI_PIE_Architecture_V1_Elite.pdf`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AI-PIE ARCHITECTURE ALIGNMENT                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  [Section 6: Tree-sitter AST & Diff Ingestion]                         │
│           │                                                            │
│           ▼                                                            │
│  [Section 24: E1 Generative Information Extraction]                    │
│     ├── E1Entity (Class, Function, Service, Config)                    │
│     ├── E1Relation (Calls, Imports, Depends_on, Inherits)              │
│     └── E1SourceEvidence (file_path, diff_snippet, commit_sha)         │
│           │                                                            │
│           ▼                                                            │
│  [Section 25: E2 Ontology Induction & Guided Synthesis] (THIS WORK)    │
│     ├── Multi-Signal Similarity & Graph Partitioner                    │
│     ├── Candidate Concept & Relationship Induction                     │
│     ├── Hierarchical Taxonomy Synthesis (Domain -> Component)         │
│     └── Governance Gating (PROPOSED_PENDING_REVIEW)                    │
│           │                                                            │
│           ▼                                                            │
│  [Section 23: EvoKG Temporal Knowledge Graph (Read-Only Target)]       │
│     └── Immutable V1 RelationTaxonomy (Preserved & Verified)           │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

- **Section 6 & 24:** E2 consumes extraction outputs from E1 and T1 ATOM as immutable input streams, treating them as verified evidence atoms.
- **Section 25 (E2):** Provides the inductive bridge between fine-grained code changes (diffs, functions) and higher-level architectural abstractions.
- **Section 23 (EvoKG):** Enforces predicate exclusivity (`EXCLUSIVE` vs `NON_EXCLUSIVE`) and structural supersession rules. E2 proposals map their relationships to valid V1 predicate families without modifying V1 schemas.

---

## 4. Prototype Design and Implementation Details

The E2 prototype is isolated within `experiments/e2_ontology_guided_extraction/`:

### A. Data Models (`schema.py`)
- `CandidateConcept`: Represents an induced architectural concept. Contains unique ID, canonical name, `OntologyCategory`, list of source entity names/types, confidence score, list of `EvidenceProvenance` records, and status `PROPOSED_PENDING_REVIEW`.
- `CandidateRelation`: Represents a directed semantic relationship between two candidate concepts. Includes `subject_concept_id`, `relation_type` (`SPECIALIZES`, `COMPOSED_OF`, `DEPENDS_ON`, `CALLS`, `MANAGES`, `CONFIGURES`, `VALIDATES`, `MODIFIES`, `TESTS`), `object_concept_id`, confidence, and evidence.
- `TaxonomyNode`: Acyclic tree node with hierarchical levels (`level=0` Domain, `level=1` Subsystem, `level=2` Component, `level=3` Operation).
- `OntologyProposal`: Complete container bundle with generated concepts, relations, taxonomy roots, clustering threshold, and governance disclaimers.

### B. Concept Clustering & Graph Partitioning (`concept_clusterer.py`)
- **Identifier Subword Splitting:** Splits compound names (`UserAuthenticationService` → `{"user", "authentication", "service"}`) and computes token Jaccard similarity.
- **Path Proximity:** Analyzes shared directory hierarchies between source files.
- **Vector Cosine Similarity:** Computes cosine similarity over normalized deterministic 1536-dimensional embeddings.
- **Graph Community Detection:** Pure Python connected-component partitioner (`LIGHTWEIGHT_DETERMINISTIC_GRAPH_PARTITIONER`) clustering nodes exceeding threshold $\tau$.
- **Evidence-Preserving Concept Merging:** Near-duplicate concepts are merged into a canonical concept, combining all entity names, types, and evidence spans while averaging confidence scores.

### C. Ontology Induction Engine (`ontology_inducer.py`)
- Ingests raw entities and relations from E1 or synthetic benchmarks.
- Classifies entities into architectural categories (`DOMAIN_SUBSYSTEM`, `SERVICE_COMPONENT`, `DATA_ACCESS`, `SECURITY_VALIDATION`, `INFRASTRUCTURE_CONFIG`, `OPERATION_MEMBER`).
- Aggregates entity-level relations into concept-level relationships.
- Synthesizes an acyclic multi-level taxonomy rooted at code domains.
- Enforces strict governance: every concept and relation is tagged `PROPOSED_PENDING_REVIEW`.

---

## 5. Experimental Evaluation Results

The evaluation harness (`evaluator.py`) was executed across the full 40-scenario E1 benchmark corpus (218 ingested entities, 52 relations).

### Core Performance Metrics (Primary Threshold $\tau = 0.70$)

| Evaluation Metric | Measured Value | Target / Benchmark Expectation | Result |
|---|---|---|---|
| **Concept Extraction Coverage** | **1.0000 (100.0%)** | $\ge 90.0\%$ of ground-truth benchmark entities | **PASSED (Optimal)** |
| **Induced Concept Count** | **60 concepts** | Meaningful clustering from 218 raw inputs | **PASSED** |
| **Candidate Relationship Count** | **23 relationships** | Cross-concept architectural relations | **PASSED** |
| **Relationship Proposal Precision** | **1.0000 (100.0%)** | $100\%$ grounded in observed diff evidence | **PASSED (Optimal)** |
| **Evidence Grounding Coverage** | **1.0000 (100.0%)** | $100\%$ proposals carry traceable provenance | **PASSED (Optimal)** |
| **Redundancy Reduction Ratio** | **0.7248 (72.48%)** | $\ge 50.0\%$ reduction of raw duplications | **PASSED (High Efficiency)** |
| **Taxonomy Max Depth** | **3.0** | 3–4 abstraction levels | **PASSED** |
| **Taxonomy Mean Depth** | **2.16** | Well-balanced tree structure | **PASSED** |
| **Mean Branching Factor** | **4.50** | Non-trivial hierarchical grouping | **PASSED** |
| **Total Taxonomy Nodes** | **122 nodes** | Full domain-to-leaf coverage | **PASSED** |

---

## 6. Sensitivity Analysis Findings

We evaluated the behavior of the ontology induction engine across five distinct similarity thresholds $\tau \in [0.30, 0.50, 0.70, 0.85, 0.95]$:

| Threshold ($\tau$) | Induced Concepts | Candidate Relations | Redundancy Reduction | Concept Coverage | Evidence Coverage | Max Depth | Mean Branching Factor | Structural Characterization |
|---|---|---|---|---|---|---|---|---|
| **0.30** | 3 | 0 | 98.62% | 100.0% | 100.0% | 3.0 | 11.78 | **Severely Over-Clustered:** Dissimilar entities collapsed into monolithic clusters. |
| **0.50** | 5 | 1 | 97.71% | 100.0% | 100.0% | 3.0 | 9.73 | **Coarse Subsystems:** High-level grouping, but insufficient component granularity. |
| **0.70** | **60** | **23** | **72.48%** | **100.0%** | **100.0%** | **3.0** | **4.50** | **Balanced Optimum:** Clean concept deduplication, high precision, clear taxonomy. |
| **0.85** | 100 | 42 | 54.13% | 100.0% | 100.0% | 3.0 | 5.32 | **Fine-Grained:** Slight over-fragmentation; minor spelling variants preserved as separate. |
| **0.95** | 102 | 43 | 53.21% | 100.0% | 100.0% | 3.0 | 5.85 | **Near-Raw Granularity:** Almost no clustering; functions and classes remain unmerged. |

### Analysis
The sensitivity analysis demonstrates that $\tau = 0.70$ is the optimal operating threshold for Code Lane ontology induction. Below $0.50$, concept clusters lose architectural specificity; above $0.85$, near-identical concepts (e.g. slight naming variations across files) fail to merge.

---

## 7. Comparison: Flat E1 Extraction vs. Ontology-Guided Organization

| Evaluation Dimension | Flat E1 Extraction Baseline | E2 Ontology-Guided Organization | Impact on Downstream Retrieval |
|---|---|---|---|
| **Information Structure** | Flat list of disjoint entity and relation triples | Multi-level hierarchical taxonomy with domain grouping | Enables 1-hop and multi-hop hierarchical navigation |
| **Duplicate Handling** | Same symbol modified across 5 commits produces 5 separate entity instances | Clustered into a single canonical `CandidateConcept` with combined evidence | Eliminates context-window bloat in LLM queries (72.5% redundancy reduction) |
| **Cross-Cutting Concerns** | Isolated functions (e.g. `verify_token`, `check_auth`) have no semantic group | Grouped into `SECURITY_VALIDATION` category and `UserAuthentication` concept | Enables queries like "Show all security validation mechanisms in Billing" |
| **Provenance Tracking** | Entity-level file/line tags | Consolidated multi-span evidence preserving every commit SHA and diff snippet | Zero evidence loss despite deduplication |
| **Architectural Relations** | Raw AST calls and regex matches | Inferred architectural bindings (`SPECIALIZES`, `COMPOSED_OF`, `DEPENDS_ON`) | Grounded knowledge graph construction |

---

## 8. Safety, Provenance and Governance Assessment

1. **V1 Ontology Immutability:**
   - The production taxonomy (`apps/api/src/services/code_atom/taxonomy.py`) and schema (`apps/api/src/schemas/code_atom.py`) were verified as completely unchanged.
   - Negative unit test `test_v1_ontology_not_mutated` explicitly verifies that canonical V1 predicates (`CALLS`, `DEFINES`, `IMPORTS`, `REFERENCES`) and exclusivity rules are untouched.
2. **Strict Proposal Gating:**
   - Every candidate concept, relationship, and taxonomy tree is stamped with `ProposalStatus.PROPOSED_PENDING_REVIEW`.
   - Unit test `test_status_strictly_proposed_pending_review` confirms that no proposal can default to `ACCEPTED` or `REJECTED`.
3. **Traceable Provenance:**
   - Every proposal contains `EvidenceProvenance` objects recording `file_path`, `start_line`, `end_line`, `commit_sha`, and `diff_snippet`.
4. **Frozen Scopes Integrity:**
   - Production T1–T4 directories and E1 directories remain untouched. Negative test `test_frozen_scopes_read_only` passed.

---

## 9. Limitations and Open Research Questions

1. **Lightweight Graph Partitioner:** The current implementation uses connected-component partitioning on thresholded affinity graphs. While deterministic and dependency-free, more complex multi-scale community detection (e.g., modularity-optimizing Leiden) could uncover subtler cross-package dependencies if C-libraries are permitted in future stages.
2. **Polyglot Parsing Variance:** Scenarios in the benchmark currently cover Python and basic TypeScript diffs. Go interface implementations (`implements` implicit duck typing) require AST interface matching to induce `SPECIALIZES` relations accurately.
3. **Temporal Evolution of Concepts:** Current E2 induction aggregates static snapshots of extracted facts. Modeling how a candidate concept's definition drifts across multiple repository releases (concept versioning) remains an open research topic for E2 Stage 2.

---

## 10. Concrete Recommendation for E2 Stage 2

1. **Do not proceed to E2 Stage 2 immediately.** Complete human review of E1 annotations first when reviewers become available.
2. **Stage 2 Objectives (When Authorized):**
   - Implement an interactive review CLI / API endpoint allowing human architects to inspect `OntologyProposal` artifacts, accept/reject candidate concepts, and promote vetted concepts into a staging taxonomy.
   - Investigate concept temporal drift tracking across git commit series.
   - Benchmark retrieval quality (Recall@K and Answer Groundedness) using ontology-guided hierarchy traversal vs. flat chunk retrieval.
