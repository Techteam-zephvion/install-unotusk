"""
Live integration test suite for Voyage AI code embeddings (Phase 2).

Opt-in execution:
These tests are executed only when VOYAGE_API_KEY is explicitly configured in the environment.
When VOYAGE_API_KEY is absent, tests cleanly skip with an explicit BLOCKED explanation.
No fake credentials, mocked HTTP responses, or fabricated vectors are permitted in this file.
"""

import math
import os
import time
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.config.settings import settings
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.enums import IntegrationProvider, IntegrationStatus
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.code_atom.chunk_mapper import generate_deterministic_chunk_id
from apps.api.src.services.code_atom.embedding import (
    DEFAULT_VECTOR_DIM,
    VoyageCodeEmbeddingBackend,
)
from apps.api.src.services.context_engine.retriever import compute_cosine_similarity
from tests.conftest import TestSessionLocal

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
VOYAGE_MODEL = getattr(settings, "VOYAGE_MODEL", "voyage-code-2")
EXPECTED_DIM = getattr(settings, "EMBEDDING_DIMENSION", DEFAULT_VECTOR_DIM)


def _check_key_configured():
    if not VOYAGE_API_KEY or not VOYAGE_API_KEY.strip():
        pytest.skip(
            "BLOCKED -- API key not configured: Set VOYAGE_API_KEY in environment to run live Voyage embedding integration test"
        )


async def _check_pgvector_ready(session: AsyncSession | None) -> bool:
    if session is None:
        return False
    try:
        await session.execute(text("SELECT 1"))
        res = await session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        return res.scalar() is not None
    except Exception:
        return False


# ==============================================================================
# Test A — Live provider request
# ==============================================================================


@pytest.mark.skipif(
    not VOYAGE_API_KEY,
    reason="BLOCKED -- API key not configured: Set VOYAGE_API_KEY in environment to run live Voyage embedding integration test",
)
def test_a_live_voyage_provider_request():
    """Test A: Verify live Voyage AI API embedding generation, dimension, finiteness, and model."""
    _check_key_configured()

    backend = VoyageCodeEmbeddingBackend(
        api_key=VOYAGE_API_KEY,
        model=VOYAGE_MODEL,
        dimension=EXPECTED_DIM,
        timeout=20.0,
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
    vec = backend.generate_embedding(sample_code, input_type="document")
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert vec is not None, "Live Voyage API returned None for valid code input"
    assert len(vec) == EXPECTED_DIM, f"Expected {EXPECTED_DIM}-dimensional vector, got {len(vec)}"
    assert all(isinstance(x, float) for x in vec), "All embedding components must be floats"
    assert all(not (math.isnan(x) or math.isinf(x)) for x in vec), "All vector components must be finite"

    # Verify vector normalization: L2 norm should be approximately 1.0
    l2_norm = sum(x * x for x in vec) ** 0.5
    assert abs(l2_norm - 1.0) < 0.05, f"Expected unit L2 norm (~1.0), got {l2_norm}"

    # Verify backend model configuration matches
    assert backend.model_name == VOYAGE_MODEL

    print(f"\n[LIVE VOYAGE] Test A: Document embedding generated in {elapsed_ms:.2f} ms ({len(vec)} dims)")


# ==============================================================================
# Test B — Query embedding compatibility
# ==============================================================================


@pytest.mark.skipif(
    not VOYAGE_API_KEY,
    reason="BLOCKED -- API key not configured: Set VOYAGE_API_KEY in environment to run live Voyage embedding integration test",
)
def test_b_live_voyage_query_embedding_compatibility():
    """Test B: Verify query embedding generation and cosine similarity alignment with document vector."""
    _check_key_configured()

    backend = VoyageCodeEmbeddingBackend(
        api_key=VOYAGE_API_KEY,
        model=VOYAGE_MODEL,
        dimension=EXPECTED_DIM,
        timeout=20.0,
    )

    doc_code = """
def authenticate_user_credentials(username: str, password_hash: str) -> bool:
    \"\"\"Validates user credentials against encrypted auth storage.\"\"\"
    return auth_vault.verify(username, password_hash)
"""
    matching_query = "how does user authentication verify passwords?"

    # 1. Document embedding
    doc_vec = backend.generate_embedding(doc_code, input_type="document")
    assert doc_vec is not None
    assert len(doc_vec) == EXPECTED_DIM

    # 2. Query embedding
    query_vec = backend.generate_embedding(matching_query, input_type="query")
    assert query_vec is not None
    assert len(query_vec) == EXPECTED_DIM

    # 3. Compatibility & semantic alignment
    sim = compute_cosine_similarity(query_vec, doc_vec)
    assert isinstance(sim, float)
    assert sim > 0.35, f"Expected strong semantic similarity between matching query and code, got {sim}"

    # 4. Explicit rejection of incompatible vector dimension
    bad_dim_backend = VoyageCodeEmbeddingBackend(
        api_key=VOYAGE_API_KEY,
        model=VOYAGE_MODEL,
        dimension=512,  # deliberately mismatching actual model output
    )
    assert bad_dim_backend.generate_embedding(doc_code) is None

    print(f"\n[LIVE VOYAGE] Test B: Query/doc cosine similarity: {sim:.4f}")


# ==============================================================================
# Test C — Actual PostgreSQL + pgvector storage
# ==============================================================================


@pytest.mark.skipif(
    not VOYAGE_API_KEY,
    reason="BLOCKED -- API key not configured: Set VOYAGE_API_KEY in environment to run live Voyage embedding integration test",
)
@pytest.mark.asyncio
async def test_c_live_voyage_postgres_pgvector_storage(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """Test C: Persist a live Voyage embedding to real PostgreSQL + pgvector and verify cross-session retrieval."""
    _check_key_configured()

    if not await _check_pgvector_ready(db_session):
        pytest.skip("PostgreSQL database with pgvector extension is not reachable")

    backend = VoyageCodeEmbeddingBackend(
        api_key=VOYAGE_API_KEY,
        model=VOYAGE_MODEL,
        dimension=EXPECTED_DIM,
    )

    sample_code = "def handle_webhook_event(payload: dict) -> None: logger.info('webhook')"
    live_vector = backend.generate_embedding(sample_code, input_type="document")
    assert live_vector is not None
    assert len(live_vector) == EXPECTED_DIM

    # Provision repository and snapshot
    user = await create_test_user(email=f"voyage-c-{uuid.uuid4().hex[:6]}@unotusk.io")
    org, _ = await create_test_org(user=user, name="Voyage Test Org")
    project = await create_test_project(organization=org, name="Voyage Test Project")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id=f"gh-voyage-{uuid.uuid4().hex[:6]}",
        integration_metadata={},
    )
    db_session.add(integration)

    repo = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id=f"repo-voyage-{uuid.uuid4().hex[:6]}",
        owner="unotusk",
        name="voyage-test-repo",
        full_name="unotusk/voyage-test-repo",
        default_branch="main",
        url="https://github.com/unotusk/voyage-test-repo",
        is_private=False,
    )
    db_session.add(repo)

    snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        commit_sha="c001voyage1234567890abcdef1234567890abc",
        commit_message="feat(webhook): live voyage test",
    )
    db_session.add(snapshot)

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/webhook.py",
        filename="webhook.py",
        extension=".py",
        content_hash="hash_webhook_1",
    )
    db_session.add(repo_file)

    fingerprint = f"fp-voyage-{uuid.uuid4().hex}"
    chunk_id = generate_deterministic_chunk_id(fingerprint)

    chunk = CodeChunk(
        id=chunk_id,
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        chunk_type="ATOM_ADD",
        name="handle_webhook_event (ADD)",
        path="src/webhook.py",
        content=sample_code,
        start_line=1,
        end_line=5,
        commit_sha=snapshot.commit_sha,
        commit_message=snapshot.commit_message,
        fingerprint=fingerprint,
        provenance={"test": "voyage_live_c"},
        embedding=live_vector,
    )
    db_session.add(chunk)
    await db_session.commit()

    # Verify cross-session persistence in a fresh independent session
    async with TestSessionLocal() as verify_session:
        fetched = await verify_session.get(CodeChunk, chunk_id)
        assert fetched is not None
        assert fetched.embedding is not None
        assert len(fetched.embedding) == EXPECTED_DIM
        assert fetched.embedding[0] == pytest.approx(live_vector[0], abs=1e-5)
        assert fetched.fingerprint == fingerprint
        assert fetched.commit_sha == snapshot.commit_sha

    print(f"\n[LIVE VOYAGE] Test C: Successfully persisted {EXPECTED_DIM}-dim live vector into PostgreSQL")


# ==============================================================================
# Test D — Real semantic retrieval with live Voyage embeddings
# ==============================================================================


@pytest.mark.skipif(
    not VOYAGE_API_KEY,
    reason="BLOCKED -- API key not configured: Set VOYAGE_API_KEY in environment to run live Voyage embedding integration test",
)
@pytest.mark.asyncio
async def test_d_live_voyage_real_semantic_retrieval(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """Test D: End-to-end SQL vector similarity retrieval with live Voyage document and query embeddings."""
    _check_key_configured()

    if not await _check_pgvector_ready(db_session):
        pytest.skip("PostgreSQL database with pgvector extension is not reachable")

    backend = VoyageCodeEmbeddingBackend(
        api_key=VOYAGE_API_KEY,
        model=VOYAGE_MODEL,
        dimension=EXPECTED_DIM,
    )

    # 1. Target code snippet (Payment processing)
    target_code = """
def process_stripe_charge(amount_cents: int, customer_token: str) -> dict:
    \"\"\"Processes an immediate credit card transaction via Stripe payment gateway.\"\"\"
    return stripe_client.charges.create(amount=amount_cents, currency="usd", source=customer_token)
"""
    # 2. Distractor code snippet (Geometry 3D rendering)
    distractor_code = """
def compute_mesh_normal_vectors(vertices: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    \"\"\"Computes per-vertex surface normals for 3D polygonal mesh rendering.\"\"\"
    return [normalize_cross_product(v1, v2) for v1, v2 in zip(vertices[:-1], vertices[1:])]
"""

    target_vec = backend.generate_embedding(target_code, input_type="document")
    distractor_vec = backend.generate_embedding(distractor_code, input_type="document")

    assert target_vec is not None and len(target_vec) == EXPECTED_DIM
    assert distractor_vec is not None and len(distractor_vec) == EXPECTED_DIM

    # Provision hierarchy
    user = await create_test_user(email=f"voyage-d-{uuid.uuid4().hex[:6]}@unotusk.io")
    org, _ = await create_test_org(user=user, name="Voyage Retrieval Org")
    project = await create_test_project(organization=org, name="Voyage Retrieval Project")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id=f"gh-voyage-ret-{uuid.uuid4().hex[:6]}",
        integration_metadata={},
    )
    db_session.add(integration)

    repo = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id=f"repo-voyage-ret-{uuid.uuid4().hex[:6]}",
        owner="unotusk",
        name="voyage-retrieval-repo",
        full_name="unotusk/voyage-retrieval-repo",
        default_branch="main",
        url="https://github.com/unotusk/voyage-retrieval-repo",
        is_private=False,
    )
    db_session.add(repo)

    snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        commit_sha="d001voyage1234567890abcdef1234567890abc",
        commit_message="feat(payment): add stripe charge processor",
    )
    db_session.add(snapshot)

    file_payment = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/payments/stripe.py",
        filename="stripe.py",
        extension=".py",
        content_hash="hash_stripe_1",
    )
    file_geometry = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/graphics/mesh.py",
        filename="mesh.py",
        extension=".py",
        content_hash="hash_mesh_1",
    )
    db_session.add_all([file_payment, file_geometry])

    target_chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        file_id=file_payment.id,
        chunk_type="ATOM_ADD",
        name="process_stripe_charge (ADD)",
        path="src/payments/stripe.py",
        content=target_code,
        start_line=1,
        end_line=10,
        commit_sha=snapshot.commit_sha,
        commit_message=snapshot.commit_message,
        fingerprint=f"fp-target-{uuid.uuid4().hex}",
        provenance={"symbol_name": "process_stripe_charge"},
        embedding=target_vec,
    )
    distractor_chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        file_id=file_geometry.id,
        chunk_type="ATOM_ADD",
        name="compute_mesh_normal_vectors (ADD)",
        path="src/graphics/mesh.py",
        content=distractor_code,
        start_line=1,
        end_line=10,
        commit_sha=snapshot.commit_sha,
        commit_message=snapshot.commit_message,
        fingerprint=f"fp-distractor-{uuid.uuid4().hex}",
        provenance={"symbol_name": "compute_mesh_normal_vectors"},
        embedding=distractor_vec,
    )
    db_session.add_all([target_chunk, distractor_chunk])
    await db_session.commit()

    # 3. Query with live query embedding
    search_query = "how are credit card charges submitted to stripe?"
    query_vector = backend.generate_embedding(search_query, input_type="query")
    assert query_vector is not None and len(query_vector) == EXPECTED_DIM

    # 4. Production SQL vector retrieval path
    distance_col = CodeChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(CodeChunk, distance_col.label("distance"))
        .where(
            CodeChunk.snapshot_id == snapshot.id,
            CodeChunk.embedding.isnot(None),
        )
        .order_by("distance")
        .limit(5)
    )

    async with TestSessionLocal() as search_session:
        res = await search_session.execute(stmt)
        results = res.all()

        assert len(results) == 2, f"Expected 2 ranked results, got {len(results)}"
        top_chunk, top_dist = results[0]
        second_chunk, second_dist = results[1]

        # Verify semantic ranking: target payment chunk MUST be ranked #1
        assert top_chunk.id == target_chunk.id, "Target stripe payment chunk should be ranked #1"
        assert top_dist < second_dist, f"Target distance ({top_dist}) should be smaller than distractor ({second_dist})"

        print(
            f"\n[LIVE VOYAGE] Test D: Top match '{top_chunk.name}' (distance: {top_dist:.4f}), "
            f"distractor '{second_chunk.name}' (distance: {second_dist:.4f})"
        )
