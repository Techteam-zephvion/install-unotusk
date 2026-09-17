# UNOTUSK MVP — CUSTOMER PILOT FEEDBACK FRAMEWORK

**Document**: Customer & Design-Partner Feedback Protocol  
**Version**: Unotusk MVP v0.1.0  
**Focus**: Grounded Evidence, Real Usage, Usability, Retention Signals  

---

## 1. Feedback Framework Goals

The purpose of Phase 7 customer interviews and observational telemetry is to answer one question:  
> *"Does Unotusk provide enough real project understanding and discovery value that an engineering team would continue using it?"*

This framework defines structured observation protocols, interview prompts, qualitative rubrics, and quantitative scoring across five core dimensions:
1. **Value**: Real utility and hours saved vs. manual code inspection.
2. **Usability**: Friction points, cognitive load, and unclear mental models.
3. **Trust & Evidence**: Grounding believability, citation accuracy, and clarity of knowledge provenance.
4. **Workflow Integration**: Return visits, feature utilization, and screen attention.
5. **Retention & Willingness to Pay**: Recurring use cases and organic adoption signals.

---

## 2. The 5 Feedback Dimensions & Assessment Rubric

### 2.1 Dimension 1: Value Assessment
*What did Unotusk discover that developers did not already know, or that saved non-trivial investigation time?*

| Inquiry Area | Customer Interview Questions | Observational Signal |
|---|---|---|
| **Novel Discoveries** | "Did the Discoveries tab highlight any coupling, circular dependency, or dead code you were unaware of?" | User clicked into affected file lines from finding card. |
| **Investigation Savings** | "How long would this architectural tracing normally have taken you using grep or IDE searches?" | Self-reported time: >1 hour vs. <2 minutes. |
| **Grounded Answers** | "Did the Ask tab answer a concrete architecture question accurately?" | User copied citation or navigated to source view. |
| **Knowledge Capture** | "What team rule or design decision did you record in the Knowledge tab?" | Knowledge item created with specific file link. |

**Value Scoring**:
- `Level 4 (High)`: Found an unaddressed defect or critical hidden coupling that directly informed a refactor or architectural decision.
- `Level 3 (Moderate)`: Accelerated onboarding or answered an architectural question faster than manual search.
- `Level 2 (Marginal)`: Findings were technically true but obvious to experienced team members.
- `Level 1 (Zero)`: No useful findings generated; answers felt generic or unhelpful.

---

### 2.2 Dimension 2: Usability & Mental Models
*Where did technical users experience friction, hesitation, or confusion?*

| Inquiry Area | Customer Interview Questions | Observational Friction Signal |
|---|---|---|
| **First-Run Setup** | "Was connecting the server and signing in clear and obvious?" | Paused >30s on connection screen or needed help with host URL. |
| **Repo Connection** | "Did the Git URL input behave as expected? Was slug generation clear?" | Errored on repository URL format or branch selection. |
| **Ingestion Wait** | "Did you understand what the engine was doing during ingestion?" | Wondered if process was frozen during `SCANNING` or `PARSING`. |
| **Navigation & Terms** | "Were the 6 workspace tabs clearly differentiated in your mind?" | Confused Overview with Architecture or Ask with Files. |

**Usability Scoring**:
- `Pass`: User navigated all 6 tabs without asking a single operational question.
- `Minor Friction`: User asked 1-2 terminology clarification questions but self-corrected.
- `Fail`: User required guided intervention to complete basic operations.

---

### 2.3 Dimension 3: Trust & Evidence Grounding
*Do technical users trust the system's conclusions and distinguish machine facts from human intent?*

| Inquiry Area | Customer Interview Questions | Observational Trust Signal |
|---|---|---|
| **Citation Integrity** | "Did you click on the code citations? Did the lines match the answer?" | Inspected highlighted lines in Files tab. |
| **Provenance Clarity** | "Was it clear what was an OBSERVED FACT vs. a TEAM CURATED note?" | Recognized knowledge badge distinction. |
| **Negative Proof** | "When you asked about something absent, did it honestly admit no evidence?" | System stated absence of code evidence without hallucinating. |
| **False Positives** | "Were any architectural findings misleading or factually incorrect?" | User disputed discovery finding or marked rule as noisy. |

**Trust Scoring**:
- `High Trust`: User verified code citations and agreed findings were accurate.
- `Guarded Trust`: User verified citations, found 1-2 false alarms, but recognized code grounding.
- `Distrust`: User caught a hallucination, inaccurate line range, or misleading finding.

---

### 2.4 Dimension 4: Workflow Integration
*Where does Unotusk fit in the team's daily or weekly routine?*

| Screen / Feature | Expected Use Case | Actual Customer Usage (Observed) |
|---|---|---|
| **Overview** | Periodic codebase health check | Evaluated on first run; infrequently revisited. |
| **Discoveries** | Pre-refactoring audits & technical debt triage | Revisited when planning architectural changes. |
| **Architecture** | High-level component topology | Used during architecture reviews. |
| **Files / AST** | Fast code symbol exploration | Used during onboarding & code exploration. |
| **Knowledge** | Architectural Decision Records (ADR) & constraints | Curated by tech leads, read by team members. |
| **Ask** | Daily developer question answering | Most frequently invoked tab (`Ctrl + K`). |

---

### 2.5 Dimension 5: Retention & Pilot Exit Signals
*Will the engineering team continue using Unotusk next week?*

- **Core Retention Questions**:
  1. *"If this server was turned off tomorrow, what would you miss most?"*
  2. *"Who else on your engineering team would benefit from accessing this instance?"*
  3. *"What is the single biggest obstacle preventing your team from using Unotusk weekly?"*
- **Exit Classification**:
  - `STRONG ADOPT`: Customer requests continued server uptime, invites teammates, connects second repo.
  - `QUALIFIED ADOPT`: Customer sees strong value in Ask & Knowledge, requests specific analyzer fix.
  - `INDIFFERENT`: Customer acknowledged accuracy but has no recurring habit or pain point.
  - `CHURN / REJECT`: Customer found tool noisy or insufficient compared to existing IDE tools.

---

## 3. Pilot Debrief Template

```markdown
### Pilot Debrief: [Customer / Design Partner Name]
- **Date**: YYYY-MM-DD
- **Pilot Lead**: [Customer Tech Lead Name]
- **Repository Analyzed**: [Repo Name, LOC, Languages]
- **Deployment Mode**: [Local Workstation / Remote Host]

#### Key Findings
1. Value Delivered: [Describe specific finding or investigation solved]
2. Usability Friction: [Describe exact confusion point if any]
3. Evidence & Trust: [Did citations verify? False positive rate %]
4. Retention Verdict: [STRONG ADOPT / QUALIFIED ADOPT / INDIFFERENT / CHURN]
```
