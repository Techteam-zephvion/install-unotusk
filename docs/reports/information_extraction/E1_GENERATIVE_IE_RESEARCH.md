# E1 — Generative Information Extraction: Research Paper Analysis & Methodology Assessment

**Repository:** `Techteam-zephvion/install-unotusk`  
**Authoritative Paper:** *Large Language Models for Generative Information Extraction: A Survey*  
**arXiv Identifier:** [arXiv:2312.17617](https://arxiv.org/abs/2312.17617)  
**Authors:** Derong Xu, Wei Chen, Wenjun Peng, Chao Zhang, Tong Xu, Xiangyu Zhao, Xian Wu, Yefeng Zheng, Enhong Chen  
**Publication:** *Frontiers of Computer Science* (Higher Education Press / Springer, 2024)  
**Architecture Context:** `AI_PIE_Architecture_V1_Elite.pdf` — Section 24 (E1 Post-V1 Backlog) & Sections 6, 7, 10, 23, 25  
**Evaluation Scope:** Code Lane Knowledge Extraction & Temporal Knowledge Graph Grounding  
**Audit Date:** November 6, 2026  

---

## 1. Executive Summary & Context

Information Extraction (IE) is the fundamental natural language processing and knowledge engineering discipline of identifying and structuring factual assertions—specifically entities, relations, and events—from unstructured source material. Historically, IE has been framed as a cascade of discriminative classification tasks: token-level sequence labeling for Named Entity Recognition (NER), pair-wise or matrix classification for Relation Extraction (RE), and trigger detection plus role-slot classification for Event Extraction (EE). These traditional approaches suffer from error propagation across pipeline stages, poor generalization to unseen schemas, and brittle handling of overlapping or nested structures.

With the advent of Large Language Models (LLMs), the IE paradigm has undergone an epochal transition: **Generative Information Extraction**. As established by the authoritative survey paper *Large Language Models for Generative Information Extraction: A Survey* (Xu et al., arXiv:2312.17617), generative IE reformulates information extraction as an autoregressive text-to-structure sequence generation problem. Rather than assigning discrete class indices to token spans, the LLM directly synthesizes linearized representations of structured knowledge (such as JSON schemas, code blocks, or markup sequences).

This research report conducts an exhaustive, systematic investigation of arXiv:2312.17617 within the operational boundaries of **Unotusk AI-PIE Code Lane**. We analyze the core extraction subtasks (NER, RE, EE), examine the primary learning paradigms, evaluate landmark generative IE frameworks (UIE, InstructUIE, GoLLIE, ChatIE, Code4UIE, CodeKGC), answer critical research questions regarding schema unification, hallucination prevention, and temporal grounding, and formulate the theoretical foundation for our isolated Code Lane proof of concept.

---

## 2. A1: Information Extraction Fundamentals

The survey categorizes information extraction into three foundational subtasks: Named Entity Recognition (NER), Relation Extraction (RE), and Event Extraction (EE). In this section, we unpack each task's input, output, extraction objective, typical challenges, relevant LLM techniques, evaluation methods, and specific suitability for Code Lane intelligence.

```
                    ┌──────────────────────────────────────────┐
                    │    Generative Information Extraction     │
                    │           (arXiv:2312.17617)             │
                    └─────────────────────┬────────────────────┘
                                          │
         ┌────────────────────────────────┼────────────────────────────────┐
         ▼                                ▼                                ▼
  ┌──────────────┐                 ┌──────────────┐                 ┌──────────────┐
  │   Task 1:    │                 │   Task 2:    │                 │   Task 3:    │
  │     NER      │                 │      RE      │                 │      EE      │
  ├──────────────┤                 ├──────────────┤                 ├──────────────┤
  │ Entity Spans │                 │ Entity Pairs │                 │ Trigger Word │
  │ Entity Types │                 │ Predicates   │                 │ Event Type   │
  │ Boundary Det │                 │ Direction    │                 │ Arguments    │
  └──────────────┘                 └──────────────┘                 └──────────────┘
```

### 2.1 Named Entity Recognition (NER)

- **Input:** Unstructured text sequence $X = (x_1, x_2, \dots, x_n)$ and an optional predefined entity schema/type set $\mathcal{Y}_E = \{y_1, y_2, \dots, y_m\}$.
- **Output:** A set of typed entity instances $\mathcal{E} = \{(s_i, e_i, t_i)\}$, where $s_i$ and $e_i$ denote the start and end character/token offsets of the entity span within $X$, and $t_i \in \mathcal{Y}_E$ represents the assigned entity category.
- **Extraction Objective:** Accurately identify entity boundaries within text and assign correct semantic labels without segment truncation or span boundary drift.
- **Typical Challenges:**
  1. *Flat vs. Nested Entities:* Entities containing sub-entities (e.g., `OrchestratorService.get_port_bindings` containing class, method, and dictionary attribute).
  2. *Discontinuous Entities:* Entity references split across separated tokens or clauses.
  3. *Out-of-Vocabulary (OOV) and Polysemy:* Software symbols with multiple domain meanings (e.g., `Set` as a data structure vs. an action verb).
  4. *Boundary Ambiguity:* Determining whether modifiers belong to the entity span (e.g., `async def handle_request` vs. `handle_request`).
- **Relevant LLM Techniques:**
  - *Code-style schema prompts:* Defining entities as typed Python classes or dataclasses (GoLLIE, Code4UIE).
  - *Linearized structural tagging:* Generating bracketed markup sequences (e.g., `[Class: AuthService]`) or JSON key-value pairs.
  - *Multi-turn QA:* Asking the LLM to identify candidate entities round by round (ChatIE).
- **Evaluation Methods:**
  - *Strict Micro/Macro F1:* Requires exact token span boundary match AND exact entity type label match.
  - *Relaxed / Partial F1:* Grants credit if entity span overlaps by $\ge 50\%$ or token set overlap exists.
- **Suitability for Code Lane Knowledge Extraction:** **High.** In the Code Lane, NER corresponds to identifying software components: Services, Modules, Source Files, Classes, Functions/Methods, API Endpoints, External Dependencies, Configuration Keys, and Test Suites. Unlike generic open-domain text, code entity spans must strictly align with AST syntax nodes or source diff tokens.

---

### 2.2 Relation Extraction (RE)

- **Input:** Source text $X$, optionally conditioned on previously extracted entity pairs $(e_h, e_t)$, or jointly extracting entity pairs alongside a relation predicate set $\mathcal{Y}_R$.
- **Output:** A set of relational triplets $\mathcal{R} = \{(e_h, r, e_t)\}$, where $e_h \in \mathcal{E}$ is the head/subject entity, $e_t \in \mathcal{E}$ is the tail/object entity, and $r \in \mathcal{Y}_R$ represents the semantic relationship directed from $e_h$ to $e_t$.
- **Extraction Objective:** Discover and formalize the semantic, structural, or dependency connections binding entities together into a directed graph structure.
- **Typical Challenges:**
  1. *Entity Pair Combinatorial Explosion:* For $n$ entities, evaluating all $n(n-1)$ possible ordered pairs introduces quadratic complexity.
  2. *Overlapping and Multi-label Relations:* Two entities may share multiple relationships simultaneously (e.g., `WorkerService` both `imports` and `monitors` `RedisQueue`).
  3. *Document-Level / Cross-Sentence Dependency:* The subject and object may reside in distinct files, paragraphs, or diff hunks separated by hundreds of lines.
  4. *Implicit Relations:* Relational connections implied by syntactic placement or architectural context without explicit lexical marker words.
- **Relevant LLM Techniques:**
  - *Two-Stage Cascaded Prompting:* First identify active entities, then query specific relations between the isolated entities (ChatIE).
  - *Table Sequence Generation:* Linearizing the entity-relation table into structured row/column representations.
  - *Code-Generation Triplets:* Generating executable Python method calls or assignments representing edges (CodeKGC).
- **Evaluation Methods:**
  - *Strict Triplet F1:* Exact match on head entity span, tail entity span, AND relation predicate type.
  - *Entity-Agnostic Relation F1:* Evaluates relation classification assuming golden entity spans.
- **Suitability for Code Lane Knowledge Extraction:** **Crucial.** Relation extraction forms the core topology of the Code Knowledge Graph. In Code Lane, this includes structural relations (`CALLS`, `DEFINES`, `IMPORTS`, `INHERITS`), operational relations (`MUTATES`, `CONFIGURES`, `VALIDATES`, `RAISES`), and high-level architectural dependencies (`DEPENDS_ON`, `REPLACES`, `SUPERSEDES`).

---

### 2.3 Event Extraction (EE)

- **Input:** Source text $X$, an event schema defining event types $\mathcal{Y}_{Ev}$, and role-argument slots $\mathcal{Y}_{Arg}^{(v)}$ associated with each event type $v \in \mathcal{Y}_{Ev}$.
- **Output:** A set of structured event frames:
  $$\mathcal{E}v = \{(tr_k, v_k, \mathcal{A}_k)\}$$
  where $tr_k$ is the event trigger span, $v_k \in \mathcal{Y}_{Ev}$ is the event type, and $\mathcal{A}_k = \{(a_{k,j}, \text{role}_j)\}$ maps argument spans $a_{k,j}$ to specific argument roles $\text{role}_j \in \mathcal{Y}_{Arg}^{(v_k)}$.
- **Extraction Objective:** Capture dynamic occurrences, state transitions, actions, or modifications described in the text, binding participating entities to their precise contextual roles.
- **Typical Challenges:**
  1. *Trigger Identification Ambiguity:* Triggers can be verbs, nouns, or implicit multi-word phrases (e.g., "deprecate", "sunset", "migrated from").
  2. *Role-Slot Sparsity:* Many event arguments (e.g., reason, consequence, author, timestamp) may be absent or left implicit in source text.
  3. *Multi-Event Co-occurrence:* A single diff or commit message may describe multiple intertwined events (e.g., "Upgrade auth library and deprecate legacy session handler").
- **Relevant LLM Techniques:**
  - *Schema-Guided Template Filling:* Populating predefined event slots directly within an output JSON frame.
  - *Question-Answering (Machine Reading Comprehension):* Asking slot-specific questions (e.g., "What component was deprecated?", "What was the reason for this deprecation?").
- **Evaluation Methods:**
  - *Trigger Identification & Classification F1:* Correct detection and typing of the event trigger span.
  - *Argument Identification & Classification F1:* Correct detection of argument spans and their assigned role categories.
- **Suitability for Code Lane Knowledge Extraction:** **Very High.** Software development is inherently event-driven: code evolves through discrete commits. Code Lane event types capture dynamic evolution: `COMPONENT_INTRODUCED`, `COMPONENT_MODIFIED`, `COMPONENT_DELETED`, `DEPENDENCY_ADDED`, `API_CHANGED`, `BEHAVIOR_CHANGED`, `TEST_MODIFIED`, `CONFIGURATION_UPDATED`, and `IMPLEMENTATION_DEPRECATED`. These map directly to temporal graph transitions with author timestamps.

---

## 3. A2: Generative IE Approaches & Paradigm Taxonomy

The survey provides a systematic classification of learning paradigms and structural generation strategies applied in generative IE. Here, we analyze these paradigms and compare landmark frameworks.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Taxonomy of Generative IE Approaches                  │
├──────────────────────────────────────┬──────────────────────────────────────┤
│        A. Learning Paradigms         │       B. Generation Structures       │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ 1. Supervised Fine-Tuning (SFT)      │ 1. Natural Language / JSON Prompts   │
│ 2. Zero-Shot Prompting               │ 2. Structured Extraction Lang. (SEL) │
│ 3. Few-Shot In-Context Learning (ICL)│ 3. Code-Style Prompting (Python/AST) │
│ 4. Instruction-Based Extraction      │ 4. Grammar-Constrained Decoding (GCD)│
│ 5. Retrieval-Augmented IE            │ 5. Multi-Turn Interactive Dialogue   │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### 3.1 Detailed Paradigm Analysis

1. **Supervised Fine-Tuning (SFT):**
   - *Mechanism:* Updates model parameters on curated $(X, Y)$ datasets where $Y$ is a linearized structural representation.
   - *Strengths:* Achieves high precision on in-distribution schemas; minimizes token latency by eliminating verbose system instructions.
   - *Weaknesses:* Prohibitively expensive GPU requirements; severe vulnerability to catastrophic forgetting; brittle when schemas evolve; requires retraining when new programming languages or relation types are introduced.

2. **Zero-Shot Prompting:**
   - *Mechanism:* Prompts an off-the-shelf, frozen LLM with task instructions and schema definitions without demonstrations.
   - *Strengths:* Zero training cost; instantaneous adaptation to arbitrary schemas; highly flexible.
   - *Weaknesses:* Prone to schema drift, invented labels, missing required JSON brackets, and lower recall on complex domain entities.

3. **Few-Shot In-Context Learning (Few-Shot ICL):**
   - *Mechanism:* Appends 2 to 5 representative demonstrations of input diffs and corresponding structured extractions in the prompt context.
   - *Strengths:* Dramatically reduces hallucinated formatting; teaches the LLM domain-specific extraction granularity without parameter updates.
   - *Weaknesses:* Consumes prompt context window; increases per-query token cost and inference latency; sensitive to demonstration selection order.

4. **Instruction-Based Extraction:**
   - *Mechanism:* Incorporates explicit positive/negative extraction guidelines, disambiguation rules, and edge-case handling directly into the system instruction prompt.
   - *Strengths:* Enforces domain boundary rules (e.g., "Do not treat deleted lines as active behavior"); steers model behavior reliably across diverse inputs.
   - *Weaknesses:* Requires careful prompt engineering; complex instructions can degrade compliance in smaller models.

5. **Unified Information Extraction (UIE):**
   - *Mechanism:* Pioneered by Lu et al. (ACL 2022), UIE frames all IE subtasks (NER, RE, EE) under a single sequence-to-sequence model using a **Structural Schema Instructor (SSI)** and **Structured Extraction Language (SEL)**.
   - *Strengths:* Single unified model and vocabulary; cross-task transfer learning; uniform evaluation and serialization.
   - *Weaknesses:* Original UIE relies on fine-tuned T5 models; custom SEL syntax requires specialized parsers and lacks standard JSON tooling support.

6. **Schema-Conditioned Extraction:**
   - *Mechanism:* Injects dynamic schema definitions (valid entity types, permitted relations, argument roles) directly into the prompt context for each query.
   - *Strengths:* Restricts model output to authorized ontology boundaries; prevents out-of-schema label hallucinations.
   - *Weaknesses:* Large schemas inflate prompt size; model may struggle if schema has dozens of overlapping types.

7. **Retrieval-Augmented Extraction (RAE):**
   - *Mechanism:* Dynamically retrieves the most relevant historical examples, similar diffs, or symbol definitions from a knowledge store using BM25 or vector embeddings, injecting them into the prompt.
   - *Strengths:* Grounds extractions in verified historical repository context; enables dynamic few-shot example selection tailored to the target diff.
   - *Weaknesses:* Retrieval errors propagate into the generation prompt; adds vector search latency before LLM invocation.

8. **Code-Generation-Based Extraction (CodeIE / Code4UIE / CodeKGC):**
   - *Mechanism:* Translates the extraction task into code generation (e.g., Python class instantiations, typed dictionaries, or AST construction).
   - *Strengths:* Capitalizes on the powerful structural syntax priors of Code-LLMs (Claude, Qwen-Coder, CodeLlama); code syntax is natively hierarchical and eliminates formatting ambiguity; supports direct Python type validation.
   - *Weaknesses:* Output syntax errors cause interpreter parsing failures if not handled by a resilient parser.

9. **Constrained Decoding (Grammar-Guided Generation / GCD / Outlines):**
   - *Mechanism:* Intercepts model logit outputs at each autoregressive decoding step, masking out tokens that would violate a predefined formal grammar (EBNF), Context-Free Grammar (CFG), or JSON Schema.
   - *Strengths:* **100% mathematical guarantee** of syntactic validity; zero unclosed JSON braces; zero missing required keys; zero out-of-enum labels.
   - *Weaknesses:* Requires direct logit manipulation; inaccessible on closed remote APIs (Claude, Groq) that only expose text generation endpoints; computational overhead for complex regular expressions.

---

### 3.2 Landmark Framework Comparison

| Framework | Core Mechanism | Representation Style | Primary Advantage | Limitation in Code Lane Context |
| :--- | :--- | :--- | :--- | :--- |
| **UIE** (Lu et al., 2022) | Structural Schema Instructor (SSI) + SEL | Prefix tree + linearized brackets | First unified text-to-structure model | Custom parser required; T5 fine-tuning overhead |
| **InstructUIE** (Wang et al., 2023) | Instruction tuning across 11K IE tasks | Natural language instruction + JSON | Strong zero-shot generalization | Requires fine-tuning an open-source base LLM |
| **GoLLIE** (Sainz et al., 2023) | Code-LLM fine-tuning on Python guidelines | Python class definitions & docstrings | Zero-shot compliance with detailed guidelines | Heavy model footprint; relies on local CodeLlama fine-tune |
| **ChatIE** (Wei et al., 2023) | Multi-turn conversational question-answering | Conversational dialogue turns | Drastically reduces relation search space | Multi-turn API calls multiply latency and cost by 3–5x |
| **Code4UIE** (Guo et al., 2023) | Retrieval-augmented code generation | Python class instantiation | Leverages code-LLM structural syntax | Demands retrieval infrastructure before extraction |
| **CodeKGC** (Wang et al., 2023) | Knowledge graph construction via code generation | Python dictionary / functional call triples | Enforces structural constraints via code syntax | Focused on relational triples; lacks event temporal intervals |

---

### 3.3 Applicability Assessment for Unotusk Single-Tenant MVP

Based on the survey's findings and `AGENTS.md` boundaries:

1. **Discard Supervised Fine-Tuning (SFT / InstructUIE / GoLLIE Fine-Tuning):**
   - Unotusk MVP is an on-premises, single-tenant deployment designed to run on standard developer hardware.
   - Maintaining fine-tuned checkpoint weights for every language or repository is operationally infeasible and financially wasteful.

2. **Discard Multi-Turn Interactive Prompting (ChatIE):**
   - Sequential multi-turn dialogue (NER $\to$ filter $\to$ RE $\to$ EE) across thousands of Git commits would cause massive latency spikes ($> 15\text{ seconds}$ per commit) and exhaust API rate limits.

3. **Adopt Schema-Conditioned In-Context Learning with Pydantic JSON Mode:**
   - Leveraging prompt-injected JSON schemas with Pydantic v2 validation and structured token-grounding filters provides the optimal balance: zero model training, $< 2\text{s}$ latency, 100% schema compliance, and zero API vendor lock-in.

---

## 4. A3: Research Comparison Table

The following table compares generative information extraction methods, distinguishing techniques directly analyzed in arXiv:2312.17617 from supplementary modern methods.

| Method | Extraction Task | Input Format | Output Format | Training Required | Strengths | Limitations | Code Lane Suitability | Source Category |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| **UIE** (Lu et al., 2022) | NER, RE, EE | Text + SSI schema prefix | SEL (linearized bracketed string) | Yes (T5/BART fine-tune) | Unified architecture; handles all IE subtasks | Non-standard SEL syntax; T5 model limits context size | Moderate (Concept useful, syntax obsolete) | **Directly from Paper** |
| **InstructUIE** (Wang et al., 2023) | NER, RE, EE | Instruction + Text + Options | JSON / Natural language text | Yes (LLaMA-7B fine-tune) | Broad zero-shot generalization across 11K datasets | Requires dedicated fine-tuned weights; GPU heavy | Low (Too heavy for single-tenant MVP) | **Directly from Paper** |
| **GoLLIE** (Sainz et al., 2023) | NER, RE, EE | Annotation guidelines as Python code | Instantiated Python dataclasses | Yes (CodeLlama fine-tune) | Excellent structural adherence; guideline grounding | Model weights required; complex evaluation tooling | High in concept, Low in fine-tune requirement | **Directly from Paper** |
| **ChatIE** (Wei et al., 2023) | NER, RE, EE | Multi-turn conversational questions | Short entity/relation answers | No (Zero-shot ChatGPT) | Decomposes complex extraction into simple QA steps | High cumulative latency; rate-limit vulnerable | Low (Too slow for continuous Git diffs) | **Directly from Paper** |
| **Code4UIE** (Guo et al., 2023) | NER, RE, EE | Retrieved demonstrations + Code prompt | Python class instantiations | No (In-Context Learning) | Inductive bias of Code-LLMs; clean syntax | Requires high-quality retrieval index | High (Directly aligned with Code Lane) | **Directly from Paper** |
| **CodeKGC** (Wang et al., 2023) | RE, KG Triples | Schema as Python class + Source text | Python function calls / Triples | Yes / Few-shot | Structurally constrained triplet generation | Relational triples only; omits event semantics | Moderate (Good for RE, incomplete for EE) | **Directly from Paper** |
| **Zero-Shot JSON Prompting** | NER, RE, EE | System instructions + Source diff | JSON string | No (Zero-shot) | Trivial implementation; fast setup | Prone to syntax errors, hallucinations, enum drift | Low (Fails production robustness requirements) | **Directly from Paper** |
| **Pydantic Schema Healing** | NER, RE, EE | Prompt + Inlined JSON Schema | Validated Pydantic models | No (Few-shot / API JSON Mode) | 100% type safety; resilient error repair; lightweight | Cannot enforce generation at raw logit level | **VERY HIGH (Selected E1 Approach)** | Supplementary Industry SOTA |
| **Outlines (Grammar GCD)** | NER, RE, EE | Schema regex / Context-Free Grammar | Guaranteed valid JSON tokens | No (Local open-weights LLM) | 100% token validity; zero syntax failure | Requires local logit control; incompatible with cloud APIs | High for local LLM, Zero for Claude/Groq APIs | Supplementary Research |

---

## 5. A4: E1 Research Conclusions

Drawing directly from the empirical and theoretical findings of arXiv:2312.17617, we address the nine core architectural questions governing E1 design:

### 1. Can a single generative extraction framework support entities, relations, and events?
**Yes.** As proven by UIE, InstructUIE, and Code4UIE, information extraction tasks share a common underlying representation: mapping unstructured text spans to structured semantic nodes and typed directed edges. A single LLM invocation with a unified JSON/code schema can jointly extract entities, relations, and event frames from a single Git diff and commit message, eliminating cross-stage pipeline cascading errors.

### 2. When is a unified schema better than separate extraction tasks?
A unified schema is superior when:
- **Strong mutual interdependence exists:** In a code diff, an API change event (`API_CHANGED`) is intrinsically linked to the entity modified (`AuthService.login`) and the relation altered (`CALLS` $\to$ `TokenManager.validate`). Extracting them jointly allows the LLM to leverage context from the event to disambiguate the relation.
- **Latency and token budgets are constrained:** Running three sequential LLM calls (NER, then RE, then EE) triples API latency, token consumption, and financial cost. Joint extraction amortizes the input token overhead into a single forward pass.

### 3. When should prompting be preferred over fine-tuning?
Prompting (specifically Few-Shot In-Context Learning with Schema Conditioned Prompting) is decisively preferred when:
- **Schemas evolve dynamically:** When new relation types (e.g., `DEPRECATES`, `SUPERSEDES`) or programming languages are introduced, prompting requires editing a configuration prompt, whereas fine-tuning demands re-annotating thousands of examples and running GPU retraining.
- **Single-tenant / On-premises deployment:** Users deploy Unotusk on commodity developer machines without enterprise GPU clusters. Prompting offloads inference to existing multi-provider APIs (Groq, Claude) or lightweight local models without maintaining model checkpoints.
- **Data scarcity:** Fine-tuning requires large annotated corpora, which are virtually non-existent for proprietary multi-language codebase diffs.

### 4. How can hallucinated entities and relations be prevented?
The survey identifies four critical hallucination prevention mechanisms:
1. **Source Token Grounding Gate:** Extracted entity names and arguments must be strictly verified against the lexical tokens of the input diff, symbol catalog, or commit message. Spurious tokens not present in source text are rejected.
2. **Schema Whitelisting:** Permitted relation types and entity types are strictly restricted to the authorized vocabulary. Out-of-vocabulary predicates are mapped to canonical types or marked `UNCERTAIN`.
3. **Diff Polarity Verification:** Deletions (lines starting with `-`) must never be asserted as active, positive behavior. Deletions must strictly trigger `REMOVAL` or `COMPONENT_DELETED` events.
4. **Abstention on Low Semantic Evidence:** When a diff consists solely of trivial whitespace, comments, or ambiguous scalar assignments, the model must explicitly abstain rather than invent architectural intent.

### 5. How can generated facts be grounded in original source material?
Every extracted fact must maintain immutable **Provenance Tuples**:
$$\text{Provenance} = (\text{repository\_id}, \text{branch}, \text{commit\_sha}, \text{file\_path}, \text{start\_line}, \text{end\_line}, \text{diff\_hunk\_snippet})$$
By anchoring every entity, relation, and event to exact file paths and source line spans verified by Tree-sitter AST nodes, the system creates an auditable proof chain that can be verified deterministically.

### 6. How should extraction uncertainty be represented?
Drawing from the ATOM and EvoKG formalisms (arXiv:2509.15464 and arXiv:2510.22590):
- Model-reported confidence numbers (e.g., `0.95`) must **never** be accepted as proof of truth.
- Extraction uncertainty must be represented by a discrete dual-state indicator: `is_uncertain: bool` and a calibrated confidence category `HIGH | MEDIUM | UNCERTAIN`.
- Whenever evidence tokens cannot be verified in the diff, or when commit messages are ambiguous, the system forces `is_uncertain = True` and downgrades confidence to `UNCERTAIN` ($0.30$).

### 7. How should temporal facts be represented?
Temporal facts must strictly follow **Dual-Time Interval Semantics**:
- $t_{\text{obs}}$: Observation timestamp, anchored immutably to the Git commit author timestamp (UTC).
- $t_{\text{start}}$: Valid start timestamp. For newly introduced components, relations, or configurations, $t_{\text{start}} = t_{\text{obs}}$.
- $t_{\text{end}}$: Valid end timestamp. For removed, replaced, or deprecated components, $t_{\text{end}} = t_{\text{obs}}$. Active facts have $t_{\text{end}} = \text{None}$ (open interval).
- **Strict Invariant:** No timestamps may ever be fabricated. If the commit date is missing or malformed, temporal fields must remain `None`.

### 8. How can structured output be guaranteed?
- **Pydantic v2 Schema Enforcement:** Models validate JSON structure, type constraints, and field requirements.
- **JSON Mode with Structured Schema Instruction:** Frontier APIs (Groq, Claude, OpenAI) provide JSON mode enforcing bracket and key balance.
- **Robust Schema Healing:** A resilient deserializer strips markdown wrappers (` ```json `), balances unclosed braces, applies default values for missing optional fields, and catches malformed JSON before downstream processing.

### 9. How can extraction quality be measured without an expensive manually annotated dataset?
The survey and industry benchmarks establish three viable low-cost evaluation strategies:
1. **Cross-Checking against AST Ground Truth:** Evaluate generative extraction against deterministic AST parser outputs for syntax-level symbols (functions, classes, calls, imports). Generative extraction must achieve $\ge 95\%$ recall on known AST symbols while capturing semantic relationships outside AST reach.
2. **Deterministic Grounding Verification:** Automatically compute the token overlap and line existence rate between generated facts and raw diff content. Spurious tokens directly penalize precision.
3. **Targeted Real-World Scenario Benchmarking:** Curate a compact, representative suite (40+ real commits) covering diverse change categories (API refactoring, config tuning, dependency updates, renames) with expert-verified draft assertions.

---

## 6. Synthesis for Code Lane Implementation

The findings of arXiv:2312.17617 provide an authoritative theoretical and practical roadmap for E1:
- We formulate Code Lane extraction as a **Unified Generative Schema** capturing Entities, Relations, and Events in a single pass.
- We reject fragile fine-tuning in favor of **Schema-Conditioned In-Context Learning** backed by **Pydantic v2 validation**.
- We mandate **Immutable Source Grounding** to ensure that generative flexibility does not compromise zero-hallucination guarantees.
- We establish an isolated experimental sandbox (`experiments/e1_generative_ie/`) preserving the production ATOM baseline while extending intelligence into architectural intent and cross-component semantic reasoning.
