"""
tests/unit/test_code_atom_scope_resolution.py

Phase 13 — Code Lane Fidelity & Targeted Gap Fixes
Verifies AST scope resolution, innermost scope selection, line-range correlation
for diffs lacking hunk header signatures, deletion handling, rename lineage,
embedding backend routing, and provenance synchronization.
"""

import uuid

from apps.api.src.schemas.code_atom import GitCommitArtifact
from apps.api.src.services.code_atom.chunk_mapper import (
    map_atomic_code_change_to_code_chunk,
)
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.code_atom.embedding import (
    DevelopmentCodeEmbeddingBackend,
    VoyageCodeEmbeddingBackend,
    format_atom_code_embedding_input,
    get_code_embedding_backend,
)


def test_partial_diff_without_signature_resolves_via_symbol_catalog():
    """Diff hunk header lacks function signature; line range correlates with AST catalog."""
    diff_without_signature = """diff --git a/apps/api/src/payment.py b/apps/api/src/payment.py
index 1234567..89abcdef 100644
--- a/apps/api/src/payment.py
+++ b/apps/api/src/payment.py
@@ -15,4 +15,6 @@
     if amount <= 0:
         raise InvalidAmountError()
+    if currency != "USD":
+        amount = convert_currency(amount, currency, "USD")
     return gateway.charge(amount)
"""
    sym_id = uuid.uuid4()
    catalog = [
        {
            "id": sym_id,
            "name": "process_payment",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/payment.py",
            "start_line": 10,
            "end_line": 30,
            "qualified_name": "apps.api.src.payment.process_payment",
        }
    ]

    commit = GitCommitArtifact(
        commit_sha="a1b2c3d4e5f67890123456789012345678901234",
        commit_message="fix(payment): normalize non-USD amounts before charging",
        raw_diff=diff_without_signature,
    )

    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit, symbol_catalog=catalog)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.symbol_name == "process_payment"
    assert change.symbol_id == sym_id
    assert change.symbol_type == "FUNCTION"
    assert change.provenance["symbol_id"] == str(sym_id)


def test_nested_symbols_prefer_innermost_scope():
    """Nested symbols (class containing method): changes resolve to innermost method scope."""
    diff_method_change = """diff --git a/apps/api/src/tax_service.py b/apps/api/src/tax_service.py
index 1111111..2222222 100644
--- a/apps/api/src/tax_service.py
+++ b/apps/api/src/tax_service.py
@@ -22,4 +22,5 @@
     rate = self.get_rate(region)
+    rate += self.get_surcharge(region)
     return subtotal * rate
"""
    class_id = uuid.uuid4()
    method_id = uuid.uuid4()
    catalog = [
        {
            "id": class_id,
            "name": "TaxCalculator",
            "symbol_type": "CLASS",
            "file_path": "apps/api/src/tax_service.py",
            "start_line": 5,
            "end_line": 120,
            "qualified_name": "TaxCalculator",
        },
        {
            "id": method_id,
            "name": "calculate_tax",
            "symbol_type": "METHOD",
            "file_path": "apps/api/src/tax_service.py",
            "start_line": 20,
            "end_line": 35,
            "qualified_name": "TaxCalculator.calculate_tax",
        },
    ]

    commit = GitCommitArtifact(
        commit_sha="b2c3d4e5f6a17890123456789012345678902345",
        commit_message="feat(tax): apply regional surcharge in calculation",
        raw_diff=diff_method_change,
    )

    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit, symbol_catalog=catalog)

    assert result.change_count == 1
    change = result.changes[0]
    # Innermost scope is calculate_tax (span 16), not TaxCalculator (span 116)
    assert change.symbol_name == "calculate_tax"
    assert change.symbol_id == method_id
    assert change.symbol_type == "METHOD"


def test_pure_deletion_resolves_via_old_line_range():
    """Pure deletion (new_line_count == 0) correctly correlates with old line range in catalog."""
    diff_deletion = """diff --git a/apps/api/src/endpoints.py b/apps/api/src/endpoints.py
index 3333333..4444444 100644
--- a/apps/api/src/endpoints.py
+++ b/apps/api/src/endpoints.py
@@ -45,5 +45,0 @@
-def legacy_endpoint():
-    deprecated_telemetry()
-    return {"status": "deprecated"}
-
"""
    sym_id = uuid.uuid4()
    catalog = [
        {
            "id": sym_id,
            "name": "legacy_endpoint",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/endpoints.py",
            "start_line": 40,
            "end_line": 55,
            "qualified_name": "legacy_endpoint",
        }
    ]

    commit = GitCommitArtifact(
        commit_sha="c3d4e5f6a1b27890123456789012345678903456",
        commit_message="refactor: remove legacy endpoint",
        raw_diff=diff_deletion,
    )

    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit, symbol_catalog=catalog)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.symbol_name == "legacy_endpoint"
    assert change.symbol_id == sym_id


def test_renamed_file_correlates_symbols_across_paths():
    """When a file is renamed, symbols cataloged under the old path correlate properly."""
    diff_rename = """diff --git a/apps/api/src/old_auth.py b/apps/api/src/auth.py
similarity index 90%
rename from apps/api/src/old_auth.py
rename to apps/api/src/auth.py
index 5555555..6666666 100644
--- a/apps/api/src/old_auth.py
+++ b/apps/api/src/auth.py
@@ -12,4 +12,5 @@
 def verify_signature(token: str) -> bool:
+    audit_log(token)
     return validate(token)
"""
    sym_id = uuid.uuid4()
    catalog = [
        {
            "id": sym_id,
            "name": "verify_signature",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/old_auth.py",  # Catalog has pre-commit path
            "start_line": 10,
            "end_line": 25,
        }
    ]

    commit = GitCommitArtifact(
        commit_sha="d4e5f6a1b2c37890123456789012345678904567",
        commit_message="refactor: rename old_auth to auth and add audit log",
        raw_diff=diff_rename,
    )

    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit, symbol_catalog=catalog)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.file_path == "apps/api/src/auth.py"
    assert change.old_file_path == "apps/api/src/old_auth.py"
    assert change.symbol_name == "verify_signature"
    assert change.symbol_id == sym_id


def test_shifted_line_numbers_recover_symbol_via_header_name():
    """If line numbers shifted past AST bounds, header symbol name recovers catalog UUID."""
    diff_shifted = """diff --git a/apps/api/src/handler.py b/apps/api/src/handler.py
index 7777777..8888888 100644
--- a/apps/api/src/handler.py
+++ b/apps/api/src/handler.py
@@ -150,5 +150,6 @@ def handle_request(req):
     parse_body(req)
+    rate_limit(req)
     return execute(req)
"""
    sym_id = uuid.uuid4()
    # Catalog has old line numbers (e.g. 80-95) from previous commit
    catalog = [
        {
            "id": sym_id,
            "name": "handle_request",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/handler.py",
            "start_line": 80,
            "end_line": 95,
        }
    ]

    commit = GitCommitArtifact(
        commit_sha="e5f6a1b2c3d47890123456789012345678905678",
        commit_message="feat: add rate limiting to handle_request",
        raw_diff=diff_shifted,
    )

    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit, symbol_catalog=catalog)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.symbol_name == "handle_request"
    assert change.symbol_id == sym_id
    assert change.symbol_type == "FUNCTION"


def test_top_level_code_falls_back_cleanly_to_file_level():
    """Top-level module changes with no enclosing AST symbol fall back safely without hallucination."""
    diff_toplevel = """diff --git a/apps/api/src/config.py b/apps/api/src/config.py
index 9999999..aaaaaaa 100644
--- a/apps/api/src/config.py
+++ b/apps/api/src/config.py
@@ -1,4 +1,5 @@
 import os
+import sys
 from typing import Any
"""
    # Catalog only has a symbol further down at line 50
    catalog = [
        {
            "id": uuid.uuid4(),
            "name": "get_settings",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/config.py",
            "start_line": 50,
            "end_line": 70,
        }
    ]

    commit = GitCommitArtifact(
        commit_sha="f6a1b2c3d4e57890123456789012345678906789",
        commit_message="chore: add sys import to config",
        raw_diff=diff_toplevel,
    )

    decomposer = CodeAtomDecomposer()
    result = decomposer.decompose(commit, symbol_catalog=catalog)

    assert result.change_count == 1
    change = result.changes[0]
    assert change.symbol_name is None
    assert change.symbol_id is None
    assert change.symbol_type is None
    assert change.file_path == "apps/api/src/config.py"


def test_provenance_fidelity_preserved_in_chunk_mapping():
    """Effective symbol ID is synchronized across chunk.symbol_id and chunk.provenance."""
    diff = """diff --git a/apps/api/src/service.py b/apps/api/src/service.py
index 1111111..2222222 100644
--- a/apps/api/src/service.py
+++ b/apps/api/src/service.py
@@ -10,3 +10,4 @@ def run_task():
+    step()
     return True
"""
    sym_id = uuid.uuid4()
    catalog = [
        {
            "id": sym_id,
            "name": "run_task",
            "symbol_type": "FUNCTION",
            "file_path": "apps/api/src/service.py",
            "start_line": 8,
            "end_line": 20,
        }
    ]
    commit = GitCommitArtifact(
        commit_sha="1111222233334444555566667777888899990000",
        commit_message="feat: add step to run_task",
        raw_diff=diff,
    )
    decomposer = CodeAtomDecomposer()
    res = decomposer.decompose(commit, symbol_catalog=catalog)
    change = res.changes[0]

    snapshot_id = uuid.uuid4()
    file_id = uuid.uuid4()
    chunk = map_atomic_code_change_to_code_chunk(
        change=change,
        snapshot_id=snapshot_id,
        file_id=file_id,
        symbol_id=sym_id,
        compute_embedding=False,
    )

    assert chunk.symbol_id == sym_id
    assert chunk.provenance["symbol_id"] == str(sym_id)
    assert chunk.provenance["symbol_name"] == "run_task"
    assert chunk.commit_message == "feat: add step to run_task"
    assert chunk.start_line == 10


def test_embedding_backend_routing_and_format():
    """Fidelity check on Voyage vs Development backend routing and embedding text formatting."""
    dev_backend = DevelopmentCodeEmbeddingBackend()
    assert dev_backend.provider_name == "development"
    assert dev_backend.dimension == 1536
    vec = dev_backend.generate_embedding("def calculate_tax(): return 0.1")
    assert vec is not None
    assert len(vec) == 1536

    voyage_backend = VoyageCodeEmbeddingBackend(api_key="mock_key", model="voyage-code-2")
    assert voyage_backend.provider_name == "voyage"
    assert voyage_backend.model_name == "voyage-code-2"
    assert voyage_backend.dimension == 1536

    # Verify formatted embedding text combines commit message + file + symbol + content
    formatted = format_atom_code_embedding_input(
        commit_message="feat(core): update tax rate",
        content="rate = 0.15",
        file_path="apps/api/src/tax.py",
        symbol_name="calculate_tax",
    )
    assert "feat(core): update tax rate" in formatted
    assert "File: apps/api/src/tax.py" in formatted
    assert "Symbol: calculate_tax" in formatted
    assert "rate = 0.15" in formatted

    # Default backend resolution without VOYAGE_API_KEY defaults cleanly to Development
    default_backend = get_code_embedding_backend()
    assert isinstance(default_backend, DevelopmentCodeEmbeddingBackend)
