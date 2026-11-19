# UNOTUSK V1 — Operational Deployment Evidence Audit

**Audit Date:** 2026-11-03  
**Auditor:** Senior Software Architect & Technical Audit Lead  
**Evaluation Scope:** ELEVATE NxT TRL 7 Compliance — Task 2: Prove Operational Deployment  

---

## 1. Executive Summary & Core Determination

The purpose of this audit is to determine whether **UNOTUSK V1** has demonstrated operational deployment within an external customer's production environment as required by **TRL 7** (*"System prototype demonstrated in an operational environment"*).

### Definitive Finding
**Operational Deployment at TRL 7 is NOT PROVEN.**

While the engineering team has achieved robust **TRL 6** maturity—delivering an integrated containerized backend, native cross-platform desktop clients, automated packaging tarballs, and high-fidelity parsing of realistic production open-source codebases (`pallets/flask` and `psf/requests`)—**there is zero evidentiary proof of an active, running, or completed deployment within an external customer-controlled infrastructure.**

```
+---------------------------------------------------------------------------------------------------+
|                                 DEPLOYMENT TAXONOMY & STATUS MATRIX                               |
+------------------------------------+--------------------------+-----------------------------------+
| Operational Category               | Status                   | Primary Evidence Source           |
+------------------------------------+--------------------------+-----------------------------------+
| 1. Internal Development & Testing  | VERIFIED & ROBUST        | 488 passing automated test suites |
| 2. Simulated Environment           | VERIFIED & VALIDATED     | Flask (226 files), Requests (121) |
| 3. External Evaluation Agreement   | UNEXECUTED DRAFT (BLANK) | Cloute Draft (18 Sep 2026)        |
| 4. Customer Infra Installation     | NOT FOUND / NO EVIDENCE  | No remote IPs, SSH, or server logs|
| 5. External Personnel Usage        | NOT FOUND / NO EVIDENCE  | 0 customer telemetry/user records |
+------------------------------------+--------------------------+-----------------------------------+
```

---

## 2. Taxonomy of Deployment Evidence

To avoid ambiguity or misleading claims in funding and audit submissions, all activities are categorized according to rigorous defense and aerospace TRL evaluation standards:

### 2.1 Internal Development & Unit Testing
- **Definition:** Code executed on developer workstations or CI environments using synthetic mock data and SQLite/PostgreSQL test fixtures.
- **Evidence:** 356 backend pytest cases (`apps/api/tests/`), 85 Flutter employee app widget tests (`app/test/`), and 47 Flutter server setup wizard tests (`setup_app/test/`).
- **Classification:** TRL 4–5 baseline.

### 2.2 Simulated Operational Deployment (Realistic Scale)
- **Definition:** Execution of the full containerized stack against real-world, complex, third-party production codebases under realistic operating loads, executed internally.
- **Evidence:**
  - Automated analysis of `pallets/flask` (226 files, 919 symbols, 675 dependencies, 2,704 discoveries generated in 62.86s). Recorded in [`pilot_repository_results.json`](file:///home/devils/PRO/Unotusk-MVP/pilot_repository_results.json).
  - Multi-signal indexing and grounded question answering across `psf/requests` (121 files, 707 symbols, 324 dependencies, 647 findings, 49 grounded questions). Recorded in [`scripts/validation_results.json`](file:///home/devils/PRO/Unotusk-MVP/scripts/validation_results.json).
- **Classification:** **TRL 6 (Fully Substantiated).** Integrated prototype demonstrated in a representative, relevant operational environment.

### 2.3 External Evaluation Agreement
- **Definition:** Contractual instrument negotiated with an external commercial enterprise for operational field testing.
- **Evidence:** Document titled [`UNOTUSK_Design_Partner_Agreement_Cloute_Executed_Draft.docx`](file:///home/devils/CTO/arch/company/CEO/UNOTUSK_Design_Partner_Agreement_Cloute_Executed_Draft.docx) (4.5 MB), dated 18 September 2026, naming **Cloute Technologies Private Limited** (Bengaluru).
- **Audit Finding:** **The signature blocks for both UNOTUSK (CTO Bhavani Krishna) and Cloute Technologies (Director Govindraj Krishnamurthy) are completely blank.** Under Indian contract law and technical audit guidelines, an unsigned contract draft does not constitute proof of engagement, authorization, or operational deployment.

### 2.4 Actual Customer Infrastructure Installation
- **Definition:** The software package installed, configured, and bound to ports on bare-metal or cloud infrastructure owned, leased, or administered directly by customer personnel.
- **Audit Finding:** **No evidence found.** No remote hostnames, IP allocations, VPN tunnels, customer cloud accounts (AWS/GCP/Azure/DigitalOcean), or server access logs exist.

### 2.5 Demonstrated Operational Use by External Personnel
- **Definition:** Hands-on product utilization by non-Unotusk engineers to investigate their own proprietary source repositories, review generated risk findings, and trigger project intelligence queries.
- **Audit Finding:** **No evidence found.** The database contains only local internal demo accounts (`admin@unotusk.com`, `lead@unotusk.com`, `dev@unotusk.com`). There are no user accounts, access tokens, or query logs associated with Cloute Technologies or any external design partner.

---

## 3. Investigation of Specific Audit Requirements

### 3.1 Installation on Customer-Controlled Infrastructure
Schedule 2 (Row 221-222) of the Cloute draft agreement specifies:
> *"Environment: On-premise / the Design Partner's own infrastructure (bare metal or a cloud VM controlled by the Design Partner). The Company does not host the Product."*

An exhaustive forensic search was conducted across repository shell scripts, configuration files, Docker Compose definitions, and local log directories:
1. **Network & DNS:** No configuration entries exist targeting domain names or private IPs belonging to `cloute.co.in` or external subnets.
2. **Setup Script Output:** Running [`scripts/verify_pilot_env.py`](file:///home/devils/PRO/Unotusk-MVP/scripts/verify_pilot_env.py) audits local developer environment prerequisites only.
3. **Database Records:** Inspecting the PostgreSQL database `unotusk` revealed a single organization: `Unotusk Demo Org` (slug: `unotusk-demo`), created via [`scripts/seed_demo.py`](file:///home/devils/PRO/Unotusk-MVP/scripts/seed_demo.py). There is no organization entity for Cloute Technologies.

### 3.2 Connection to Real, Authorized Production Repositories
Schedule 2 (Row 227-228) and Schedule 4 (Row 260) specify:
> *"Integrations to be configured: GitHub and Jira only... Kickoff and connection of GitHub + Jira within 5 (five) Business Days of the Effective Date."*

Audit inspection reveals:
1. **GitHub Ingestion:** The engine supports local and cloned Git repositories. Ingestion was proven on public repositories (`pallets/flask`, `psf/requests`) and the internal repository `Techteam-zephvion/School-management-app`. No private repositories belonging to Cloute Technologies were ingested.
2. **Jira Ingestion:** **Jira integration is completely unimplemented in the backend.** A search for `"jira"` across the entire API backend (`apps/api/src/`) yields 0 results. Moreover, the project's authoritative architecture specification, [`AGENTS.md`](file:///home/devils/PRO/Unotusk-MVP/AGENTS.md) Section 2, explicitly states:
   > *"Explicitly Out of Scope for MVP: No external tool connectors (Jira, Linear, Slack, Confluence) — Git active only."*
   Therefore, the product could not have ingested customer Jira tickets as contemplated in the draft agreement.

### 3.3 Context Indexing & Temporal Relationship Analysis in Customer Context
- **Code Capability:** The temporal engine ([`apps/api/src/services/code_atom/temporal.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/code_atom/temporal.py)) and graph engine ([`apps/api/src/services/graph_service.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/graph_service.py)) are functionally complete and verified under unit tests.
- **Operational Reality:** This capability has operated exclusively on test fixtures and public open-source benchmark repositories. It has never indexed a customer repository under external operational conditions.

### 3.4 Actual Application Use by External Personnel
- Audit query: `SELECT * FROM users WHERE email NOT LIKE '%@unotusk.com';`
- Result: 0 records.
- Audit query: `SELECT * FROM query_logs;` / `SELECT * FROM audit_logs;`
- Result: No external IP addresses, external user agents, or external user IDs exist in any persistent store.

### 3.5 Generated Project Intelligence Reports
Schedule 2 (Row 225-226) states:
> *"Deliverables to be provided by the Company: Structured Intelligence Report (PDF), delivered by email to the Design Partner's authorised CTO / Tech Lead contact named in Schedule 1."*

- **Audit Finding:** No customer-specific PDF or markdown intelligence reports addressed to Cloute Technologies exist on disk or in repository history.
- The report generation engine ([`apps/api/src/services/report_engine/engine.py`](file:///home/devils/PRO/Unotusk-MVP/apps/api/src/services/report_engine/engine.py)) has successfully generated synthetic 10-section intelligence reports for `pallets/flask` and local test projects, but none for customer codebases.

---

## 4. Evidentiary Distinction Table

| Criterion | Internal Development | Simulated Deployment | Agreement Draft | Customer Deployment |
|---|---|---|---|---|
| **Location** | Localhost / Docker | Localhost / Docker | Legal Template | Customer Server / VM |
| **Data Source** | Pytest mock fixtures | Public Repos (`flask`, `requests`) | N/A (Text docx) | Proprietary Customer Repo |
| **Users** | Core Dev Team | Core Dev Team | Named: G. Krishnamurthy | External Customer Engineers |
| **Jira Ingestion** | N/A | N/A | Promised in draft | None (Connector absent) |
| **Signature** | N/A | N/A | **Blank (`______`)** | None |
| **Dated Logs** | Present (Test logs) | Present (`validation.log` Sep 2026) | Document date 18 Sep 2026 | **None** |
| **TRL Value** | TRL 4–5 | **TRL 6** | TRL 6 Pipeline | **TRL 7 (Unsubstantiated)** |

---

## 5. Auditor Conclusion & Recommendation

1. **Defensible Claim:** UNOTUSK V1 can legitimately and defensibly claim **TRL 6** (*"System/subsystem model or prototype demonstrated in a relevant environment"*). The execution of the complete pipeline (parsing, AST symbol graph extraction, 10 discovery risk analyzers, and grounded query synthesis) against full-scale production codebases like `pallets/flask` constitutes rigorous TRL 6 validation.
2. **Prohibited Claim:** UNOTUSK V1 **cannot claim TRL 7** at this time. Claiming TRL 7 on grant applications, pitch decks, or technical evaluations without signed agreements, verified deployment logs, or authenticated customer usage would fail an independent technical audit.
3. **Actionable Remediation Path to TRL 7:**
   - Execute the Founding Design Partner Agreement with Cloute Technologies with genuine digital/wet signatures.
   - Deploy the container stack (`docker compose up -d`) to a Cloute-provisioned cloud VM or on-premise server.
   - Ingest an authorized Cloute proprietary Git repository.
   - Archive deployment console logs, container uptime metrics, and at least one structured Project Intelligence Report delivered to Cloute's engineering director.
