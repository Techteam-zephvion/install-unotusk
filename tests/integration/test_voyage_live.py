"""
Live integration test for Voyage AI code embeddings (voyage-code-3).

Opt-in execution:
This test is executed only when VOYAGE_API_KEY is explicitly configured in the environment.
When VOYAGE_API_KEY is absent, the test is cleanly skipped with an explicit BLOCKED explanation.
No fake credentials, mocked HTTP responses, or fabricated vectors are permitted here.
"""

import os
import time

import pytest

from apps.api.src.services.code_atom.embedding import (
    VoyageCodeEmbeddingBackend,
    generate_code_embedding,
)

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")


@pytest.mark.skipif(
    not VOYAGE_API_KEY,
    reason="BLOCKED -- API key not configured: Set VOYAGE_API_KEY in environment to run live Voyage embedding integration test",
)
def test_live_voyage_code_embedding_generation():
    """Verify live Voyage AI API embedding generation, dimension, and latency."""
    backend = VoyageCodeEmbeddingBackend(
        api_key=VOYAGE_API_KEY,
        model="voyage-code-3",
        timeout_seconds=20.0,
    )

    sample_code = """
def calculate_invoice_discount(subtotal: float, tier: str) -> float:
    \"\"\"Calculates customer discount percentage based on membership tier.\"\"\"
    if tier == "enterprise":
        return subtotal * 0.25
    elif tier == "pro":
        return subtotal * 0.15
    return 0.0
"""

    start_time = time.perf_counter()
    vec = generate_code_embedding(sample_code, backend=backend, input_type="document")
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert vec is not None, "Live Voyage API returned None for valid code input"
    assert len(vec) == 1536, f"Expected 1536-dimensional vector, got {len(vec)}"
    assert all(isinstance(x, float) for x in vec), "All embedding components must be floats"

    # Verify vector normalization: L2 norm should be approximately 1.0
    l2_norm = sum(x * x for x in vec) ** 0.5
    assert abs(l2_norm - 1.0) < 0.05, f"Expected unit L2 norm (~1.0), got {l2_norm}"

    print(f"\n[LIVE VOYAGE] Document embedding generated in {elapsed_ms:.2f} ms")


@pytest.mark.skipif(
    not VOYAGE_API_KEY,
    reason="BLOCKED -- API key not configured: Set VOYAGE_API_KEY in environment to run live Voyage embedding integration test",
)
def test_live_voyage_query_embedding_generation():
    """Verify live Voyage AI API embedding generation for search queries."""
    backend = VoyageCodeEmbeddingBackend(
        api_key=VOYAGE_API_KEY,
        model="voyage-code-3",
        timeout_seconds=20.0,
    )

    query = "where is invoice discount calculated for enterprise customers?"

    start_time = time.perf_counter()
    vec = generate_code_embedding(query, backend=backend, input_type="query")
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert vec is not None, "Live Voyage API returned None for valid query"
    assert len(vec) == 1536, f"Expected 1536-dimensional vector, got {len(vec)}"
    l2_norm = sum(x * x for x in vec) ** 0.5
    assert abs(l2_norm - 1.0) < 0.05, f"Expected unit L2 norm (~1.0), got {l2_norm}"

    print(f"\n[LIVE VOYAGE] Query embedding generated in {elapsed_ms:.2f} ms")
