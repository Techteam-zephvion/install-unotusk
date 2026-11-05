# T1 — ATOM Implementation Status Report: Atomic Decomposition & Dynamic Temporal Knowledge Graph Construction

**Product:** Unotusk AI-PIE V1 (Code Lane MVP)  
**Architecture Spec:** `AI_PIE_Architecture_V1_Elite.pdf` (April 2026 Locked Specification)  
**Research Reference:** arXiv:2510.22590 ("ATOM: Atomic Decomposition and Dynamic Temporal Knowledge Graph Construction")  
**Module Location:** `apps/api/src/services/code_atom/`  
**Targeted Test Execution:** `tests/unit/test_code_atom_*.py` (161 tests passed individually)  
**Implementation Status:** **IMPLEMENTED & TARGETED TESTS PASSED** (Final cross-track acceptance pending Stage B)

---

## 1. Executive Summary

Track T1 (ATOM) provides the foundational representation layer for temporal code intelligence in Unotusk AI-PIE V1. Rather than treating code changes as monolithic file snapshots or opaque diff blobs, ATOM decomposes Git commits into atomic, independently verifiable facts associated with dual-time intervals, AST syntax nodes, and language-specific semantic boundaries.

The implementation is designed and validated as an authoritative **Code Lane adaptation** in single-tenant PostgreSQL 16 + `pgvector`. In targeted unit and integration testing, all 161 tests passed. Final cross-track acceptance and unified execution across all four research tracks are evaluated in Stage B.

---

## 2. Research Mechanisms vs. Code Lane Adaptation

| ATOM Research Mechanism (arXiv:2510.22590) | Authorized Code Lane Adaptation | Repository Location | Status |
| :--- | :--- | :--- | :--- |
| **Atomic Fact Decomposition** | Commit diff parsing into atomic hunk units with file, symbol, and line boundaries | `apps/api/src/services/code_atom/parser.py` | **IMPLEMENTED** |
| **Multi-Language AST Scoping** | Tree-sitter AST parsing for Python, TypeScript/JavaScript, and Go | `apps/api/src/services/code_atom/ast_extractor.py` | **IMPLEMENTED** |
| **Multi-Granularity Fact Typing** | `AtomFact` and `AtomFactType` (CLASS, FUNCTION, METHOD, IMPORT, CALL, MODIFICATION) | `apps/api/src/services/code_atom/models.py` | **IMPLEMENTED** |
| **Dual-Time Semantics** | `valid_from` (commit timestamp) and `valid_to` (supersession/deletion timestamp) | `apps/api/src/services/code_atom/temporal.py` | **IMPLEMENTED** |
| **Vector Space Alignment** | Relational `CodeChunk.atom_metadata` with 1536-dim vector embeddings | `apps/api/src/models/chunk.py`, `apps/api/src/services/code_atom/embedding.py` | **IMPLEMENTED** |
| **Deterministic Supersession** | Chronological ordering and supersession resolution without fabricating timestamps | `apps/api/src/services/code_atom/temporal.py` (`resolve_temporal_supersession`) | **IMPLEMENTED** |
| **Provenance Integrity** | Concrete attribution to `commit_sha`, `file_path`, `start_line`, and `end_line` | `apps/api/src/services/code_atom/provenance.py` | **IMPLEMENTED** |

*Note: The implementation is a specialized Code Lane adaptation tailored to code changes, ASTs, and Git commits, not a generic reproduction of general-domain temporal knowledge graph benchmarks.*

---

## 3. Implementation Details

### 3.1. Parsing and Ingestion Pipeline
1. **Git Commit Ingestion:** Incremental Git commits are analyzed using Git diff streams. Changed hunks are extracted and attributed to exact commit SHAs and authors.
2. **AST Scope Identification:** Tree-sitter parsers parse modified files to determine whether a hunk affects a class definition, function, method signature, import declaration, or call site.
3. **Chunk Ingestion & Metadata:** Chunks are written to PostgreSQL table `code_chunks` with `atom_metadata` JSONB containing:
   - `chunk_type`: `ATOM_ADD`, `ATOM_MODIFY`, `ATOM_DELETE`
   - `symbol_name`: Qualified symbol name
   - `commit_sha`: 40-character hex SHA
   - `valid_from`: Commit author timestamp (ISO 8601 UTC)
   - `valid_to`: Supersession timestamp or null if currently active
   - `is_current`: Boolean flag for active state
   - `is_superseded`: Boolean flag indicating supersession

### 3.2. Supersession & Deletion Mechanics
- When a subsequent commit modifies or deletes a symbol, the predecessor chunk's `valid_to` is updated to the superseding commit's timestamp, and `is_superseded` is set to `True`.
- For deleted symbols, an explicit tombstone entry is maintained (`is_deleted=True`), ensuring historical queries can accurately observe when a symbol was retired without hallucination.

---

## 4. Empirical Verification & Test Evidence

### 4.1. Targeted Test Execution
```bash
apps/api/.venv/Scripts/pytest (Get-ChildItem tests/unit/test_code_atom_*.py) -q
# Result: 161 passed in 36.86s
```

### 4.2. Key Test Areas Verified
- **Decomposition & Fact Extraction:** Verified on Python, TypeScript, and Go repositories (`test_code_atom_parser.py`).
- **AST Scopes:** Verified enclosing function and class identification across nested and anonymous structures (`test_code_atom_ast.py`).
- **Temporal Supersession:** Verified that chronological commit sequences correctly supersede predecessors without timestamp corruption (`test_code_atom_temporal.py`).
- **Embeddings & Vector Matching:** Verified cosine distance alignment in `pgvector` (`test_code_atom_embedding.py`).
- **Edge Cases:** Handled empty diffs, binary files, rename detection, and merge commits cleanly.

---

## 5. Architectural Status

| Verification Criterion | Targeted Status | Stage B Acceptance Status |
| :--- | :---: | :---: |
| Commit diff decomposition into atomic units | **PASS (161 tests)** | Pending Stage B unified run |
| Dual-time validity interval persistence | **PASS** | Pending Stage B unified run |
| Read-only source repository behavior | **PASS** | Pending Stage B unified run |
| Idempotent ingestion & resume | **PASS** | Pending Stage B unified run |
| Grounding with commit SHA and line spans | **PASS** | Pending Stage B unified run |

**Conclusion:** T1 (ATOM) implementation is complete and targeted tests pass. Final formal cross-track acceptance will be established upon completion of Stage B.
