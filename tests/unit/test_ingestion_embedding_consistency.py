"""
tests/unit/test_ingestion_embedding_consistency.py

Regression test suite verifying consistent embedding generation across both
initial AST code chunks (symbols, children, file modules) and atomic commit chunks.

Guarantees:
1. AST chunks and ATOM chunks use the exact same configured backend factory.
2. In Development mode, all chunks use DevelopmentCodeEmbeddingBackend with 1536 dimensions.
3. When Voyage is configured, all chunks use VoyageCodeEmbeddingBackend with 1536 dimensions.
4. When Voyage is configured but an error occurs, chunks receive None rather than
   polluting the vector space with incompatible hash vectors.
5. Vector dimensions are strictly validated (1536 dimensions).
"""

from unittest.mock import MagicMock, patch

from apps.api.src.config.settings import settings
from apps.api.src.schemas.code_atom import GitCommitArtifact
from apps.api.src.services.code_atom.chunk_mapper import map_atomic_code_change_to_code_chunk
from apps.api.src.services.code_atom.decomposer import CodeAtomDecomposer
from apps.api.src.services.code_atom.embedding import (
    DEFAULT_VECTOR_DIM,
    DevelopmentCodeEmbeddingBackend,
    VoyageCodeEmbeddingBackend,
    generate_atom_code_embedding,
    generate_code_embedding,
    get_code_embedding_backend,
)


def test_ast_and_atomic_chunks_use_same_development_backend(monkeypatch):
    """Verifies both AST chunks and atomic commit chunks use Development backend consistently."""
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "development")
    monkeypatch.setattr(settings, "VOYAGE_API_KEY", "")
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)

    backend = get_code_embedding_backend()
    assert isinstance(backend, DevelopmentCodeEmbeddingBackend)
    assert backend.dimension == DEFAULT_VECTOR_DIM

    # 1. AST symbol chunk embedding path
    ast_embedding = generate_atom_code_embedding(
        commit_message=None,
        content="def authenticate_user(email: str, password: str):\n    return True",
        file_path="apps/api/src/services/auth.py",
        symbol_name="authenticate_user",
    )
    assert ast_embedding is not None
    assert len(ast_embedding) == DEFAULT_VECTOR_DIM

    # 2. Atomic code change chunk embedding path via canonical decomposer
    sample_diff = """diff --git a/apps/api/src/services/auth.py b/apps/api/src/services/auth.py
--- a/apps/api/src/services/auth.py
+++ b/apps/api/src/services/auth.py
@@ -10,3 +10,4 @@
 def authenticate_user(email: str, password: str):
+    return True
"""
    commit = GitCommitArtifact(
        commit_sha="abcdef1234567890abcdef1234567890abcdef12",
        commit_message="feat(auth): implement user authentication",
        raw_diff=sample_diff,
    )
    decomposer = CodeAtomDecomposer()
    decomp_result = decomposer.decompose(commit)
    assert len(decomp_result.changes) > 0
    atomic_change = decomp_result.changes[0]

    import uuid
    atomic_chunk = map_atomic_code_change_to_code_chunk(
        change=atomic_change,
        snapshot_id=uuid.uuid4(),
        file_id=uuid.uuid4(),
        compute_embedding=True,
    )
    assert atomic_chunk.embedding is not None
    assert len(atomic_chunk.embedding) == DEFAULT_VECTOR_DIM

    # Both embeddings are 1536-dim vectors in the same development vector space
    assert len(ast_embedding) == len(atomic_chunk.embedding) == 1536


def test_ast_and_atomic_chunks_use_voyage_backend_when_configured(monkeypatch):
    """Verifies both AST and ATOM chunks route to Voyage AI backend when configured."""
    mock_voyage_key = "pa-test-voyage-key-123456789012345678"
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "voyage")
    monkeypatch.setattr(settings, "VOYAGE_API_KEY", mock_voyage_key)

    backend = get_code_embedding_backend()
    assert isinstance(backend, VoyageCodeEmbeddingBackend)
    assert backend.provider_name == "voyage"
    assert backend.dimension == DEFAULT_VECTOR_DIM

    # Mock Voyage HTTP API batch response
    mock_vector = [0.05] * DEFAULT_VECTOR_DIM
    with patch.object(VoyageCodeEmbeddingBackend, "generate_embeddings_batch", return_value=[mock_vector]):
        # AST chunk
        ast_vec = generate_atom_code_embedding(
            commit_message=None,
            content="class PaymentGateway:\n    def charge(self): pass",
            file_path="src/payments/gateway.py",
            symbol_name="PaymentGateway",
        )
        assert ast_vec is not None
        assert len(ast_vec) == DEFAULT_VECTOR_DIM
        assert ast_vec == mock_vector

        # Atomic commit chunk via canonical decomposer
        sample_diff = """diff --git a/src/payments/gateway.py b/src/payments/gateway.py
--- a/src/payments/gateway.py
+++ b/src/payments/gateway.py
@@ -1,3 +1,4 @@
+class PaymentGateway:
+    def charge(self): pass
"""
        commit = GitCommitArtifact(
            commit_sha="c0ffee1234567890c0ffee1234567890c0ffee12",
            commit_message="feat(payments): add payment gateway",
            raw_diff=sample_diff,
        )
        decomposer = CodeAtomDecomposer()
        decomp_result = decomposer.decompose(commit)
        assert len(decomp_result.changes) > 0
        atomic_change = decomp_result.changes[0]

        import uuid
        atomic_chunk = map_atomic_code_change_to_code_chunk(
            change=atomic_change,
            snapshot_id=uuid.uuid4(),
            file_id=uuid.uuid4(),
            compute_embedding=True,
        )
        assert atomic_chunk.embedding is not None
        assert len(atomic_chunk.embedding) == DEFAULT_VECTOR_DIM
        assert atomic_chunk.embedding == mock_vector


def test_prevent_incompatible_embeddings_when_voyage_fails(monkeypatch):
    """Verifies that when Voyage fails, chunk embeddings are set to None and do NOT fall back to hash vectors."""
    mock_voyage_key = "pa-test-voyage-key-123456789012345678"
    monkeypatch.setattr(settings, "EMBEDDING_PROVIDER", "voyage")
    monkeypatch.setattr(settings, "VOYAGE_API_KEY", mock_voyage_key)

    backend = get_code_embedding_backend()
    assert isinstance(backend, VoyageCodeEmbeddingBackend)

    # Simulate Voyage API failure (e.g. rate limit / network error returns [None])
    with patch.object(VoyageCodeEmbeddingBackend, "generate_embeddings_batch", return_value=[None]):
        ast_vec = generate_atom_code_embedding(
            commit_message=None,
            content="def fallback_func(): pass",
            file_path="src/service.py",
            symbol_name="fallback_func",
        )
        # MUST BE None — must NEVER fall back to hash vectors in Voyage vector space
        assert ast_vec is None


def test_dimension_validation_enforced(monkeypatch):
    """Verifies that vector dimension mismatch is strictly rejected."""
    wrong_dim_vector = [0.1] * 768  # 768 dims instead of 1536
    mock_backend = MagicMock()
    mock_backend.provider_name = "test_provider"
    mock_backend.dimension = DEFAULT_VECTOR_DIM
    mock_backend.generate_embedding.return_value = wrong_dim_vector

    result = generate_code_embedding("test code", dim=DEFAULT_VECTOR_DIM, backend=mock_backend)
    assert result is None
