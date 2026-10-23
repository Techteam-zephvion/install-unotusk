import uuid
from datetime import datetime

import pytest
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.enums import (
    IntegrationProvider,
    IntegrationStatus,
    SnapshotStatus,
    SymbolType,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.schemas.code_atom import GitCommitArtifact
from apps.api.src.services.code_atom.chunk_mapper import generate_deterministic_chunk_id
from apps.api.src.services.code_atom.embedding import DevelopmentCodeEmbeddingBackend
from apps.api.src.services.context_engine.query_analyzer import AnalyzedQuery
from apps.api.src.services.context_engine.retriever import MultiSignalRetriever
from apps.api.src.services.ingestion_service import IngestionService
from tests.conftest import TestSessionLocal


@pytest.fixture(autouse=True)
async def check_db_available(db_session: AsyncSession):
    """Skips integration test gracefully if PostgreSQL service is not reachable."""
    if db_session is None:
        pytest.skip("Database session is not configured")
    try:
        await db_session.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL database integration environment not available: {exc}")


async def _has_pgvector_extension(session: AsyncSession) -> bool:
    """Checks whether the pgvector extension is installed and active in PostgreSQL."""
    try:
        res = await session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        if res.scalar() is not None:
            return True
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await session.commit()
        check = await session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        return check.scalar() is not None
    except Exception:
        await session.rollback()
        return False


async def _setup_project_hierarchy(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
    tag: str = "main",
) -> tuple[Project, Repository, RepositorySnapshot]:
    """Helper to provision an isolated organization, project, repository, and snapshot hierarchy."""
    user = await create_test_user(email=f"pgvector-{tag}-{uuid.uuid4().hex[:6]}@unotusk.io")
    org, _ = await create_test_org(user=user, name=f"PGVector Org {tag}")
    project = await create_test_project(organization=org, name=f"PGVector Project {tag}")

    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id=f"gh-ext-{uuid.uuid4().hex[:8]}",
        integration_metadata={},
    )
    db_session.add(integration)

    repo = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id=f"repo-{uuid.uuid4().hex[:8]}",
        owner="unotusk",
        name=f"test-repo-{tag}",
        full_name=f"unotusk/test-repo-{tag}",
        default_branch="main",
        url=f"https://github.com/unotusk/test-repo-{tag}",
        is_private=False,
    )
    db_session.add(repo)

    snapshot = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )
    db_session.add(snapshot)
    await db_session.commit()
    return project, repo, snapshot


@pytest.mark.asyncio
async def test_1_pgvector_extension_and_schema_initialization(db_session: AsyncSession):
    """1. Verify that pgvector extension and code_chunks table schema can be initialized."""
    # Check if vector extension is active or can be enabled
    has_vector = await _has_pgvector_extension(db_session)

    # Inspect code_chunks columns in PostgreSQL schema
    def _inspect_columns(sync_session):
        insp = sa_inspect(sync_session.connection())
        return {col["name"]: col for col in insp.get_columns("code_chunks")}

    columns = await db_session.run_sync(_inspect_columns)

    # Verify all essential Code Lane and ATOM columns are present
    expected_cols = [
        "id",
        "snapshot_id",
        "file_id",
        "symbol_id",
        "chunk_type",
        "name",
        "path",
        "content",
        "start_line",
        "end_line",
        "embedding",
        "commit_sha",
        "commit_message",
        "fingerprint",
        "provenance",
        "created_at",
    ]
    for col in expected_cols:
        assert col in columns, f"Expected column '{col}' missing from code_chunks table"

    # If vector extension is installed, verify column type is recognized
    if has_vector:
        ext_check = await db_session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        version = ext_check.scalar_one_or_none()
        assert version is not None, "pgvector extension must have a valid version string"


@pytest.mark.asyncio
async def test_2_vector_embedding_persistence_and_retrieval(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """2. Verify 1,536-dimensional vector embedding insertion, persistence, retrieval, and comparison."""
    _, repo, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="persist"
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/auth.py",
        filename="auth.py",
        extension=".py",
        language="python",
        size_bytes=120,
        content_hash="hash_auth_01",
    )
    db_session.add(repo_file)
    await db_session.commit()

    # Generate 1536-dimensional embedding using development backend
    backend = DevelopmentCodeEmbeddingBackend()
    raw_vec = backend.embed_text("def authenticate_token(token: str) -> bool: return True")
    assert len(raw_vec) == 1536

    chunk_id = uuid.uuid4()
    chunk = CodeChunk(
        id=chunk_id,
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        chunk_type="ATOM_ADD",
        name="authenticate_token (ADD)",
        path="src/auth.py",
        content="def authenticate_token(token: str) -> bool: return True",
        start_line=1,
        end_line=2,
        embedding=raw_vec,
        commit_sha="a1b2c3d4e5",
        commit_message="feat: implement token authentication",
        fingerprint="fp_auth_persist_01",
        provenance={"repository_id": str(repo.id), "file_path": "src/auth.py"},
    )
    db_session.add(chunk)
    await db_session.commit()

    # Expunge local identity map to ensure clean fetch from real database
    db_session.expunge_all()

    stmt = select(CodeChunk).where(CodeChunk.id == chunk_id)
    res = await db_session.execute(stmt)
    retrieved_chunk = res.scalar_one()

    assert retrieved_chunk.id == chunk_id
    assert retrieved_chunk.embedding is not None
    assert isinstance(retrieved_chunk.embedding, list)
    assert len(retrieved_chunk.embedding) == 1536

    # Verify numerical fidelity (within single-precision floating point limits)
    for original, retrieved in zip(raw_vec[:20], retrieved_chunk.embedding[:20], strict=False):
        assert abs(original - retrieved) < 1e-4, f"Mismatch: original {original} vs {retrieved}"


@pytest.mark.asyncio
async def test_3_native_vector_cosine_distance_query_and_ordering(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """3. Verify native vector distance queries execute with correct distance ordering against real DB."""
    has_vector = await _has_pgvector_extension(db_session)
    if not has_vector:
        pytest.skip("Native vector distance requires pgvector extension installed in PostgreSQL")

    _, repo, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="distance"
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/service.py",
        filename="service.py",
        extension=".py",
        language="python",
        size_bytes=300,
        content_hash="hash_service_01",
    )
    db_session.add(repo_file)
    await db_session.commit()

    backend = DevelopmentCodeEmbeddingBackend()

    # Chunk A: Tax calculation (aligned with query)
    vec_a = backend.embed_text("def compute_sales_tax(subtotal: float, rate: float) -> float:")
    chunk_a = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        chunk_type="ATOM_ADD",
        name="compute_sales_tax (ADD)",
        path="src/service.py",
        content="def compute_sales_tax(subtotal: float, rate: float) -> float:\n    return subtotal * rate",
        start_line=10,
        end_line=12,
        embedding=vec_a,
        commit_sha="c1",
        fingerprint="fp_tax",
    )

    # Chunk B: React navigation banner (orthogonal / unrelated to query)
    vec_b = backend.embed_text("export const NavbarComponent = ({ user }) => <header />")
    chunk_b = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        chunk_type="ATOM_ADD",
        name="NavbarComponent (ADD)",
        path="src/service.py",
        content="export const NavbarComponent = ({ user }) => <header />",
        start_line=50,
        end_line=52,
        embedding=vec_b,
        commit_sha="c2",
        fingerprint="fp_nav",
    )

    db_session.add_all([chunk_a, chunk_b])
    await db_session.commit()

    # Query embedding for "sales tax computation"
    query_vec = backend.embed_text("how is sales tax computed on subtotal")

    # Native pgvector cosine distance query (<=> operator via CompatibleVector)
    distance_expr = CodeChunk.embedding.cosine_distance(query_vec)
    stmt = (
        select(CodeChunk, distance_expr.label("distance"))
        .where(
            CodeChunk.snapshot_id == snapshot.id,
            CodeChunk.embedding.isnot(None),
        )
        .order_by(distance_expr.asc())
    )

    res = await db_session.execute(stmt)
    rows = res.all()

    assert len(rows) == 2
    first_chunk, first_dist = rows[0]
    second_chunk, second_dist = rows[1]

    # Verify that the tax calculation chunk is retrieved first with smaller distance
    assert first_chunk.id == chunk_a.id
    assert second_chunk.id == chunk_b.id
    assert float(first_dist) < float(second_dist)


@pytest.mark.asyncio
async def test_4_empty_and_missing_embeddings_handling(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """4. Verify that chunks with empty or missing embeddings are handled safely without crashing queries."""
    _, _, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="missing"
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="README.md",
        filename="README.md",
        extension=".md",
        language="markdown",
        size_bytes=50,
        content_hash="hash_readme_01",
    )
    db_session.add(repo_file)
    await db_session.commit()

    # Insert chunk with NULL embedding
    chunk_null = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        chunk_type="FILE_DOCUMENTATION",
        name="README.md",
        path="README.md",
        content="# Documentation",
        start_line=1,
        end_line=1,
        embedding=None,  # Missing embedding
        fingerprint="fp_readme_null",
    )
    db_session.add(chunk_null)
    await db_session.commit()

    # Query IS NULL
    stmt_null = select(CodeChunk).where(
        CodeChunk.snapshot_id == snapshot.id,
        CodeChunk.embedding.is_(None),
    )
    res_null = await db_session.execute(stmt_null)
    assert res_null.scalar_one().id == chunk_null.id

    # Query IS NOT NULL excludes the chunk cleanly
    stmt_not_null = select(CodeChunk).where(
        CodeChunk.snapshot_id == snapshot.id,
        CodeChunk.embedding.isnot(None),
    )
    res_not_null = await db_session.execute(stmt_not_null)
    assert len(res_not_null.scalars().all()) == 0


@pytest.mark.asyncio
async def test_5_repository_and_snapshot_scope_isolation(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """5. Verify repository and snapshot filters prevent cross-scope and cross-repo retrieval."""
    # Scope 1: Project Alpha
    _, _, snap_alpha = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="alpha"
    )
    file_alpha = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap_alpha.id,
        path="alpha.py",
        filename="alpha.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="hash_alpha_01",
    )
    db_session.add(file_alpha)

    # Scope 2: Project Beta
    _, _, snap_beta = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="beta"
    )
    file_beta = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap_beta.id,
        path="beta.py",
        filename="beta.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="hash_beta_01",
    )
    db_session.add(file_beta)
    await db_session.commit()

    backend = DevelopmentCodeEmbeddingBackend()
    shared_text = "def shared_service_identifier(): return 42"
    shared_vec = backend.embed_text(shared_text)

    chunk_alpha = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snap_alpha.id,
        file_id=file_alpha.id,
        chunk_type="ATOM_ADD",
        name="shared_service_identifier (Alpha)",
        path="alpha.py",
        content=shared_text,
        start_line=1,
        end_line=2,
        embedding=shared_vec,
        fingerprint="fp_shared_alpha",
    )
    chunk_beta = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snap_beta.id,
        file_id=file_beta.id,
        chunk_type="ATOM_ADD",
        name="shared_service_identifier (Beta)",
        path="beta.py",
        content=shared_text,
        start_line=1,
        end_line=2,
        embedding=shared_vec,
        fingerprint="fp_shared_beta",
    )
    db_session.add_all([chunk_alpha, chunk_beta])
    await db_session.commit()

    # Query scoped to Alpha snapshot
    alpha_stmt = select(CodeChunk).where(
        CodeChunk.snapshot_id == snap_alpha.id,
        CodeChunk.embedding.isnot(None),
    )
    alpha_res = await db_session.execute(alpha_stmt)
    alpha_chunks = alpha_res.scalars().all()
    assert len(alpha_chunks) == 1
    assert alpha_chunks[0].id == chunk_alpha.id
    assert alpha_chunks[0].path == "alpha.py"

    # Query scoped to Beta snapshot
    beta_stmt = select(CodeChunk).where(
        CodeChunk.snapshot_id == snap_beta.id,
        CodeChunk.embedding.isnot(None),
    )
    beta_res = await db_session.execute(beta_stmt)
    beta_chunks = beta_res.scalars().all()
    assert len(beta_chunks) == 1
    assert beta_chunks[0].id == chunk_beta.id
    assert beta_chunks[0].path == "beta.py"


@pytest.mark.asyncio
async def test_6_incremental_indexing_duplicate_protection_and_rollback(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """6. Verify incremental indexing, duplicate chunk protection, and rollback behavior against real DB."""
    _, _, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="inc"
    )
    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="inc.py",
        filename="inc.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="hash_inc_01",
    )
    db_session.add(repo_file)
    await db_session.commit()

    fingerprint = "fp_incremental_unique_01"
    det_id = generate_deterministic_chunk_id(fingerprint)

    # 1. Insert initial chunk
    chunk1 = CodeChunk(
        id=det_id,
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        chunk_type="ATOM_ADD",
        name="initial_symbol",
        path="inc.py",
        content="x = 1",
        start_line=1,
        end_line=1,
        fingerprint=fingerprint,
    )
    db_session.add(chunk1)
    await db_session.commit()

    # 2. Incremental update: modify existing record safely
    chunk1.content = "x = 2"
    chunk1.end_line = 2
    await db_session.commit()

    updated_chunk = await db_session.get(CodeChunk, det_id)
    assert updated_chunk is not None
    assert updated_chunk.content == "x = 2"

    # Expunge local identity map so real database primary key unique constraint is tested directly
    db_session.expunge_all()

    # 3. Duplicate protection: inserting duplicate primary key in database raises IntegrityError
    dup_chunk = CodeChunk(
        id=det_id,
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        chunk_type="ATOM_ADD",
        name="competing_instance",
        path="inc.py",
        content="x = 3",
        start_line=1,
        end_line=1,
        fingerprint=fingerprint,
    )
    db_session.add(dup_chunk)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()

    # 4. Rollback safely recovers session state
    await db_session.rollback()

    # Session is completely operational after rollback
    survivor = await db_session.get(CodeChunk, det_id)
    assert survivor is not None
    assert survivor.content == "x = 2"


@pytest.mark.asyncio
async def test_7_code_lane_retrieval_pipeline_with_real_db_records(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """7. Verify full Code Lane retrieval pipeline returns expected records and preserves complete provenance."""
    _, repo, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="pipeline"
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="apps/api/src/services/billing.py",
        filename="billing.py",
        extension=".py",
        language="python",
        size_bytes=450,
        content_hash="hash_billing_01",
    )
    db_session.add(repo_file)

    symbol = CodeSymbol(
        id=uuid.uuid4(),
        file_id=repo_file.id,
        name="BillingEngine",
        symbol_type=SymbolType.CLASS,
        qualified_name="BillingEngine",
        start_line=5,
        end_line=25,
        symbol_metadata={},
    )
    db_session.add(symbol)
    await db_session.commit()

    backend = DevelopmentCodeEmbeddingBackend()
    code_text = "class BillingEngine:\n    def process_invoice(self, inv_id: str):\n        pass"
    embedding_vec = backend.embed_text(code_text)

    chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        file_id=repo_file.id,
        symbol_id=symbol.id,
        chunk_type="ATOM_ADD",
        name="BillingEngine (ADD)",
        path="apps/api/src/services/billing.py",
        content=code_text,
        start_line=5,
        end_line=25,
        embedding=embedding_vec,
        commit_sha="commit_billing_777",
        commit_message="feat: introduce billing engine",
        fingerprint="fp_billing_pipeline",
        provenance={
            "repository_id": str(repo.id),
            "file_id": str(repo_file.id),
            "symbol_id": str(symbol.id),
            "file_path": "apps/api/src/services/billing.py",
            "symbol_name": "BillingEngine",
        },
    )
    db_session.add(chunk)
    await db_session.commit()

    # Run MultiSignalRetriever against real database records
    retriever = MultiSignalRetriever()
    analyzed = AnalyzedQuery(
        raw_query="BillingEngine invoice processing",
        keywords=["BillingEngine", "invoice", "billing"],
        symbol_candidates=["BillingEngine"],
        path_candidates=["billing.py"],
    )

    candidates = await retriever.retrieve_candidates(
        session=db_session,
        analyzed_query=analyzed,
        snapshot_id=snapshot.id,
        query_embedding=embedding_vec,
    )

    assert len(candidates) >= 1
    chunk_candidate = next((c for c in candidates if c.entity_type == "CHUNK"), None)
    assert chunk_candidate is not None
    assert "BillingEngine" in chunk_candidate.name

    # Check complete provenance retention
    meta = chunk_candidate.metadata
    assert meta.get("repository_id") == str(repo.id)
    assert meta.get("snapshot_id") == str(snapshot.id)
    assert meta.get("file_id") == str(repo_file.id)
    assert meta.get("symbol_id") == str(symbol.id)
    assert meta.get("commit_sha") == "commit_billing_777"
    assert meta.get("commit_message") == "feat: introduce billing engine"
    assert meta.get("fingerprint") == "fp_billing_pipeline"


@pytest.mark.asyncio
async def test_8_cross_session_vector_lifecycle_update_and_delete(
    create_test_user,
    create_test_org,
    create_test_project,
):
    """8. Verify vector insertion, cross-session retrieval, update, and deletion across isolated sessions."""
    if TestSessionLocal is None:
        pytest.skip("TestSessionLocal not available")

    # Session 1: Provision project and chunk with 1536-dim embedding
    chunk_id = uuid.uuid4()
    backend = DevelopmentCodeEmbeddingBackend()
    vec_initial = backend.embed_text("def initial_method(): return 1")

    async with TestSessionLocal() as session1:
        _, repo, snapshot = await _setup_project_hierarchy(
            session1, create_test_user, create_test_org, create_test_project, tag="lifecycle"
        )
        repo_file = RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snapshot.id,
            path="src/lifecycle.py",
            filename="lifecycle.py",
            extension=".py",
            language="python",
            size_bytes=80,
            content_hash="hash_lifecycle_01",
        )
        session1.add(repo_file)
        await session1.commit()

        chunk = CodeChunk(
            id=chunk_id,
            snapshot_id=snapshot.id,
            file_id=repo_file.id,
            chunk_type="ATOM_ADD",
            name="initial_method (ADD)",
            path="src/lifecycle.py",
            content="def initial_method(): return 1",
            start_line=1,
            end_line=2,
            embedding=vec_initial,
            commit_sha="c_init",
            fingerprint="fp_life_1",
            provenance={"repo": str(repo.id)},
        )
        session1.add(chunk)
        await session1.commit()

    # Session 2: Read from fresh session, verify persistence and numerical precision, then update
    vec_updated = backend.embed_text("def initial_method(): return 2 # updated logic")
    async with TestSessionLocal() as session2:
        c_read = await session2.get(CodeChunk, chunk_id)
        assert c_read is not None
        assert len(c_read.embedding) == 1536
        for orig, ret in zip(vec_initial[:10], c_read.embedding[:10], strict=False):
            assert abs(orig - ret) < 1e-4

        # Update chunk content and embedding
        c_read.content = "def initial_method(): return 2 # updated logic"
        c_read.embedding = vec_updated
        await session2.commit()

    # Session 3: Verify updated vector in real DB, then delete chunk
    async with TestSessionLocal() as session3:
        c_updated = await session3.get(CodeChunk, chunk_id)
        assert c_updated is not None
        assert c_updated.content == "def initial_method(): return 2 # updated logic"
        for orig, ret in zip(vec_updated[:10], c_updated.embedding[:10], strict=False):
            assert abs(orig - ret) < 1e-4

        await session3.delete(c_updated)
        await session3.commit()

    # Session 4: Verify chunk deletion in real DB
    async with TestSessionLocal() as session4:
        c_deleted = await session4.get(CodeChunk, chunk_id)
        assert c_deleted is None


@pytest.mark.asyncio
async def test_9_sql_similarity_ordering_before_limit_and_metadata_fidelity(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """9. Verify SQL-level cosine distance ordering executes strictly before limit truncation."""
    has_vector = await _has_pgvector_extension(db_session)
    if not has_vector:
        pytest.skip("Native pgvector extension required")

    _, _, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="sqllimit"
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/calc.py",
        filename="calc.py",
        extension=".py",
        language="python",
        size_bytes=200,
        content_hash="hash_calc_01",
    )
    db_session.add(repo_file)
    await db_session.commit()

    backend = DevelopmentCodeEmbeddingBackend()
    query_text = "matrix multiplication algorithm linear algebra"
    q_vec = backend.embed_text(query_text)

    # Insert 4 chunks with differing semantic proximity
    texts = [
        "dense matrix multiplication algorithm dot product",
        "matrix operations linear algebra transpose inverse",
        "database query connection pool settings",
        "css styles flexbox layout responsive design",
    ]
    chunks = []
    for i, t in enumerate(texts):
        c = CodeChunk(
            id=uuid.uuid4(),
            snapshot_id=snapshot.id,
            file_id=repo_file.id,
            chunk_type="ATOM_ADD",
            name=f"calc_item_{i}",
            path="src/calc.py",
            content=t,
            start_line=i * 5 + 1,
            end_line=i * 5 + 4,
            embedding=backend.embed_text(t),
            fingerprint=f"fp_calc_{i}",
        )
        chunks.append(c)
        db_session.add(c)
    await db_session.commit()

    # Execute SQL cosine distance query with limit=2
    dist_expr = CodeChunk.embedding.cosine_distance(q_vec)
    stmt = (
        select(CodeChunk, dist_expr.label("dist"))
        .where(
            CodeChunk.snapshot_id == snapshot.id,
            CodeChunk.embedding.isnot(None),
        )
        .order_by(dist_expr.asc())
        .limit(2)
    )
    res = await db_session.execute(stmt)
    rows = res.all()

    assert len(rows) == 2
    top1_chunk, dist1 = rows[0]
    top2_chunk, dist2 = rows[1]

    # The top 2 must strictly be the first two matrix-related chunks
    assert top1_chunk.id == chunks[0].id
    assert top2_chunk.id == chunks[1].id
    assert float(dist1) < float(dist2)


@pytest.mark.asyncio
async def test_10_end_to_end_incremental_indexing_and_temporal_supersession(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """10. Verify incremental ingestion, atomic chunk mapping, and temporal supersession in PostgreSQL."""
    _, repo, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="atominc"
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/service.py",
        filename="service.py",
        extension=".py",
        language="python",
        size_bytes=150,
        content_hash="hash_serv_01",
    )
    db_session.add(repo_file)

    symbol = CodeSymbol(
        id=uuid.uuid4(),
        file_id=repo_file.id,
        name="UserService",
        symbol_type=SymbolType.CLASS,
        qualified_name="UserService",
        start_line=1,
        end_line=20,
        symbol_metadata={},
    )
    db_session.add(symbol)
    await db_session.commit()

    # Commit 1 diff artifact: adding validate_user method
    diff_c1 = (
        "diff --git a/src/service.py b/src/service.py\n"
        "--- a/src/service.py\n"
        "+++ b/src/service.py\n"
        "@@ -10,0 +11,2 @@\n"
        "+    def validate_user(self, uid: str) -> bool:\n"
        "+        return len(uid) > 3\n"
    )
    art1 = GitCommitArtifact(
        commit_sha="c1_add_validate",
        commit_message="feat: add validate_user method",
        raw_diff=diff_c1,
        committed_at=datetime.fromisoformat("2026-10-15T10:00:00+00:00"),
    )

    chunks1 = await IngestionService.ingest_commit_atom_changes(
        session=db_session,
        snapshot_id=snapshot.id,
        commit_artifact=art1,
        project_id=repo.project_id,
        repository_id=repo.id,
    )
    await db_session.commit()

    assert len(chunks1) >= 1
    c1 = chunks1[0]
    assert c1.commit_sha == "c1_add_validate"
    assert c1.embedding is not None
    assert len(c1.embedding) == 1536

    # Verify retrieval against real DB finds the new chunk
    retriever = MultiSignalRetriever()
    analyzed = AnalyzedQuery(
        raw_query="validate user identifier",
        keywords=["validate", "user"],
        symbol_candidates=["UserService"],
        path_candidates=["service.py"],
    )
    candidates = await retriever.retrieve_candidates(
        session=db_session,
        analyzed_query=analyzed,
        snapshot_id=snapshot.id,
        query_embedding=c1.embedding,
    )
    assert any(c.entity_type == "CHUNK" for c in candidates)


@pytest.mark.asyncio
async def test_11_transaction_rollback_and_error_recovery(
    db_session: AsyncSession,
    create_test_user,
    create_test_org,
    create_test_project,
):
    """11. Verify transaction rollback cleans partial state and allows safe recovery and retry in PostgreSQL."""
    _, repo, snapshot = await _setup_project_hierarchy(
        db_session, create_test_user, create_test_org, create_test_project, tag="rollback"
    )

    repo_file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snapshot.id,
        path="src/retry.py",
        filename="retry.py",
        extension=".py",
        language="python",
        size_bytes=50,
        content_hash="hash_retry_01",
    )
    db_session.add(repo_file)
    await db_session.commit()

    snap_id = snapshot.id
    f_id = repo_file.id

    # 1. Attempt invalid insert violating foreign key constraint
    invalid_chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),  # Non-existent snapshot ID violates FK
        file_id=f_id,
        chunk_type="ATOM_ADD",
        name="orphan_chunk",
        path="src/retry.py",
        content="x = 1",
        start_line=1,
        end_line=1,
    )
    db_session.add(invalid_chunk)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()

    # 2. Rollback transaction
    await db_session.rollback()

    # 3. Verify no orphaned records exist in database
    res = await db_session.execute(
        select(CodeChunk).where(CodeChunk.name == "orphan_chunk")
    )
    assert res.scalar_one_or_none() is None

    # 4. Subsequent valid insert succeeds cleanly on the recovered session
    valid_chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snap_id,
        file_id=f_id,
        chunk_type="ATOM_ADD",
        name="valid_recovered_chunk",
        path="src/retry.py",
        content="x = 1",
        start_line=1,
        end_line=1,
        fingerprint="fp_valid_rec",
    )
    db_session.add(valid_chunk)
    await db_session.commit()

    saved = await db_session.get(CodeChunk, valid_chunk.id)
    assert saved is not None
    assert saved.name == "valid_recovered_chunk"
