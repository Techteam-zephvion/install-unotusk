# UNOTUSK MVP — PILOT INSTRUMENTATION & PRIVACY SPECIFICATION

**Document**: Pilot Operational Telemetry & Privacy Bounds  
**Version**: Unotusk MVP v0.1.0  
**Compliance**: Zero Code Collection / Strict Data Sovereignty  

---

## 1. Operating Principle: Privacy-First Observability

Unotusk is designed for technical organizations with strict intellectual property and confidentiality requirements. The telemetry architecture enforces an unambiguous boundary between **operational metrics** (safe to monitor system reliability) and **customer content** (which must never leave the customer's perimeter).

> **Core Axiom**: *We measure how the system runs, never what the system analyzes.*

---

## 2. Permitted vs. Strictly Prohibited Data

| Dimension | Permitted Operational Signals (Safe) | Strictly Prohibited Data (Never Captured) |
|---|---|---|
| **System State** | Container status, memory/CPU utilization, disk space free | Host user files outside repository, hardware IDs |
| **Health** | `/health` and `/health/ready` probe status, DB/Redis connection state | Database passwords, connection URLs with credentials |
| **Repositories** | File count, LOC total, language breakdown (e.g. 70% Python), duration | Repository source code, comments, docstrings, commit messages |
| **Parsing** | Symbol count, chunk count, AST parser duration | Function bodies, variable names with customer business data |
| **Discoveries** | Heuristic rule IDs triggered, severity counts, execution time | Proprietary architectural details, internal customer ticket references |
| **Ask (Q&A)** | Request count, latency in milliseconds, token counts, error status | Raw user questions, generated text, prompt templates |
| **Authentication** | Request count, 401 count, token expiration events | User passwords, password hashes, JWT secrets, raw tokens |
| **Errors** | HTTP error codes (404, 500), sanitized exception class name, stack span | Stack traces containing database credentials or source code lines |

---

## 3. Minimal MVP Telemetry Implementation

Rather than introducing an external SaaS telemetry platform (e.g. Datadog, Mixpanel, or Segment) which would introduce third-party risk and require customer security review, Unotusk MVP instruments observability through:

1. **Standardized Health Probes**:
   - `GET /health`: Liveness probe (service, version, environment).
   - `GET /health/ready`: Dependency check (PostgreSQL pool, Redis cache ping).
2. **Structured Sanitized Logging**:
   - API request duration, status code, and sanitized exceptions logged to stdout.
   - Automatic regex sanitization masks all known secret patterns (`gsk_...`, `sk-ant-...`, `password=...`, `token=...`).
3. **Database Operational Counts**:
   - Quantitative aggregates (snapshots processed, discovery counts, error states) queryable directly through the diagnostics export script without external data egress.

---

## 4. Operational Sign-Off for Pilot Deployment

- [x] Zero code chunks or file text exported.
- [x] Zero secrets, tokens, or passwords logged.
- [x] Database and cache bound strictly to `127.0.0.1`.
- [x] No external telemetry SDKs bundled in client or server.
- [x] Customer retains 100% data sovereignty on local deployment.
