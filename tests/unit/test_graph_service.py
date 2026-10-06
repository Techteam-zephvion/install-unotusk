import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.api.exceptions import ForbiddenException, NotFoundException
from apps.api.src.db.base import Base
from apps.api.src.main import app
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    DependencyType,
    IntegrationProvider,
    IntegrationStatus,
    MembershipRole,
    ProjectStatus,
    SnapshotStatus,
    SymbolType,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.organization import Organization
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.models.user import User
from apps.api.src.schemas.graph import (
    GraphEdgeType,
    GraphNodeType,
    GraphResponse,
)
from apps.api.src.services.graph_service import GraphService


@pytest_asyncio.fixture
async def sqlite_session():
    """Isolated in-memory SQLite async database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_maker() as session:
        yield session

    await engine.dispose()


async def _setup_project_hierarchy(
    session: AsyncSession,
) -> tuple[User, Organization, Project, Repository]:
    """Helper to create realistic Tenant/Project/Repo hierarchy."""
    user = User(
        id=uuid.uuid4(),
        email=f"user-{uuid.uuid4().hex[:6]}@example.com",
        name="Developer",
        password_hash="hash",
    )
    org = Organization(
        id=uuid.uuid4(),
        name="Engineering Org",
        slug=f"org-{uuid.uuid4().hex[:6]}",
    )
    membership = OrganizationMembership(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=user.id,
        role=MembershipRole.OWNER,
    )
    project = Project(
        id=uuid.uuid4(),
        organization_id=org.id,
        name="Core Engine",
        slug=f"engine-{uuid.uuid4().hex[:6]}",
        status=ProjectStatus.READY,
    )
    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-org-engine",
        integration_metadata={},
    )
    repo = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-1001",
        owner="org",
        name="core-engine",
        full_name="org/core-engine",
        default_branch="main",
        url="https://github.com/org/core-engine",
        is_private=True,
    )
    session.add_all([user, org, membership, project, integration, repo])
    await session.commit()
    return user, org, project, repo


@pytest.mark.asyncio
async def test_graph_service_returns_complete_code_graph(sqlite_session: AsyncSession):
    """
    Sprint 2: Verify that GraphService returns:
    1. File nodes
    2. Symbol nodes
    3. File -> Symbol DEFINES edges
    4. Symbol -> Child symbol CONTAINS edges
    5. Internal file -> file DEPENDS_ON edges
    6. External package nodes & DEPENDS_ON edges
    7. Deduplicated nodes and edges
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)

    snap = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )

    # Files
    f_controller = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap.id,
        path="src/controllers/payment_controller.py",
        filename="payment_controller.py",
        extension=".py",
        language="python",
        size_bytes=300,
        content_hash="h1",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=30,
    )
    f_service = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap.id,
        path="src/services/payment_service.py",
        filename="payment_service.py",
        extension=".py",
        language="python",
        size_bytes=500,
        content_hash="h2",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=50,
    )

    # Symbols: Class in service, method in class
    s_class = CodeSymbol(
        id=uuid.uuid4(),
        file_id=f_service.id,
        name="PaymentService",
        symbol_type=SymbolType.CLASS,
        qualified_name="src.services.payment_service.PaymentService",
        start_line=10,
        end_line=45,
        parent_symbol_id=None,
        symbol_metadata={"docstring": "Handles payment processing"},
    )
    s_method = CodeSymbol(
        id=uuid.uuid4(),
        file_id=f_service.id,
        name="create_payment",
        symbol_type=SymbolType.METHOD,
        qualified_name="src.services.payment_service.PaymentService.create_payment",
        start_line=15,
        end_line=30,
        parent_symbol_id=s_class.id,
        symbol_metadata={"async": True},
    )

    # Dependencies:
    # 1. Controller -> Service (internal file dependency)
    dep_internal = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f_controller.id,
        target_file_id=f_service.id,
        dependency_type=DependencyType.IMPORT,
        line_number=5,
    )
    # 2. Service -> stripe (external package)
    dep_external_1 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f_service.id,
        target_file_id=None,
        external_package="stripe",
        dependency_type=DependencyType.IMPORT,
        line_number=2,
    )
    # 3. Duplicate reference to stripe from controller
    dep_external_2 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f_controller.id,
        target_file_id=None,
        external_package="stripe",
        dependency_type=DependencyType.IMPORT,
        line_number=1,
    )

    session.add_all([
        snap,
        f_controller,
        f_service,
        s_class,
        s_method,
        dep_internal,
        dep_external_1,
        dep_external_2,
    ])
    await session.commit()

    graph = await GraphService.get_project_graph(session, user.id, project.id)

    assert isinstance(graph, GraphResponse)
    assert graph.snapshot_id == snap.id

    # Node verifications:
    node_ids = {n.id for n in graph.nodes}
    assert str(f_controller.id) in node_ids
    assert str(f_service.id) in node_ids
    assert str(s_class.id) in node_ids
    assert str(s_method.id) in node_ids
    assert "pkg:stripe" in node_ids

    # Verify external package deduplication: only ONE "pkg:stripe" node
    stripe_nodes = [n for n in graph.nodes if n.id == "pkg:stripe"]
    assert len(stripe_nodes) == 1
    assert stripe_nodes[0].type == GraphNodeType.EXTERNAL_PACKAGE
    assert stripe_nodes[0].label == "stripe"

    # Edge verifications:
    edges_by_type = {}
    for e in graph.edges:
        edges_by_type.setdefault(e.type, []).append(e)

    # 1. DEFINES edge: f_service -> s_class
    defines_edges = edges_by_type.get(GraphEdgeType.DEFINES, [])
    assert any(
        e.source == str(f_service.id) and e.target == str(s_class.id)
        for e in defines_edges
    )

    # 2. CONTAINS edge: s_class -> s_method (hierarchy)
    contains_edges = edges_by_type.get(GraphEdgeType.CONTAINS, [])
    assert any(
        e.source == str(s_class.id) and e.target == str(s_method.id)
        for e in contains_edges
    )

    # 3. DEPENDS_ON edges:
    depends_edges = edges_by_type.get(GraphEdgeType.DEPENDS_ON, [])
    # Controller -> Service (internal)
    assert any(
        e.source == str(f_controller.id) and e.target == str(f_service.id)
        for e in depends_edges
    )
    # Service -> stripe (external)
    assert any(
        e.source == str(f_service.id) and e.target == "pkg:stripe"
        for e in depends_edges
    )
    # Controller -> stripe (external)
    assert any(
        e.source == str(f_controller.id) and e.target == "pkg:stripe"
        for e in depends_edges
    )

    assert graph.total_nodes == len(graph.nodes)
    assert graph.total_edges == len(graph.edges)


@pytest.mark.asyncio
async def test_graph_scopes_strictly_to_latest_snapshot(sqlite_session: AsyncSession):
    """
    Sprint 2 / Step 15 Regression:
    Snapshot 1: A.py, B.py
    Snapshot 2: A.py, C.py

    The graph MUST contain: A.py, C.py
    The graph MUST NOT contain: B.py
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)
    now = datetime.now(UTC)

    # Snapshot 1 (Older)
    snap1 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
    )
    f1_a = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap1.id,
        path="src/A.py",
        filename="A.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="h1a",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=10,
    )
    f1_b = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap1.id,
        path="src/B.py",
        filename="B.py",
        extension=".py",
        language="python",
        size_bytes=200,
        content_hash="h1b",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=20,
    )
    s1_b = CodeSymbol(
        id=uuid.uuid4(),
        file_id=f1_b.id,
        name="OldSymbolInB",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="src.B.OldSymbolInB",
        start_line=1,
        end_line=5,
    )
    dep1_b = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f1_b.id,
        external_package="old_package_b",
        dependency_type=DependencyType.IMPORT,
        line_number=1,
    )

    # Snapshot 2 (Latest)
    snap2 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=1),
    )
    f2_a = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap2.id,
        path="src/A.py",
        filename="A.py",
        extension=".py",
        language="python",
        size_bytes=120,
        content_hash="h2a",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=12,
    )
    f2_c = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap2.id,
        path="src/C.py",
        filename="C.py",
        extension=".py",
        language="python",
        size_bytes=300,
        content_hash="h2c",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=30,
    )
    s2_c = CodeSymbol(
        id=uuid.uuid4(),
        file_id=f2_c.id,
        name="NewSymbolInC",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="src.C.NewSymbolInC",
        start_line=1,
        end_line=5,
    )
    dep2_c = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f2_c.id,
        external_package="new_package_c",
        dependency_type=DependencyType.IMPORT,
        line_number=1,
    )

    session.add_all([
        snap1,
        f1_a,
        f1_b,
        s1_b,
        dep1_b,
        snap2,
        f2_a,
        f2_c,
        s2_c,
        dep2_c,
    ])
    await session.commit()

    graph = await GraphService.get_project_graph(session, user.id, project.id)

    # MUST be scoped to Snapshot 2
    assert graph.snapshot_id == snap2.id

    node_labels = {n.label for n in graph.nodes}
    node_ids = {n.id for n in graph.nodes}

    # MUST contain A.py and C.py
    assert "src/A.py" in node_labels
    assert "src/C.py" in node_labels
    assert "NewSymbolInC" in node_labels
    assert "new_package_c" in node_labels

    # MUST NOT contain B.py or its symbols/dependencies
    assert "src/B.py" not in node_labels
    assert str(f1_b.id) not in node_ids
    assert "OldSymbolInB" not in node_labels
    assert str(s1_b.id) not in node_ids
    assert "old_package_b" not in node_labels
    assert "pkg:old_package_b" not in node_ids

    # Old snapshot 1 file A must NOT be the node ID
    assert str(f1_a.id) not in node_ids
    assert str(f2_a.id) in node_ids


@pytest.mark.asyncio
async def test_graph_empty_states(sqlite_session: AsyncSession):
    """
    Step 13: Handle edge cases:
    - Project with no snapshot -> empty graph
    - Snapshot with no files -> empty graph
    - Files with no symbols/dependencies -> files only, 0 edges
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)

    # 1. No snapshot
    g_no_snap = await GraphService.get_project_graph(session, user.id, project.id)
    assert g_no_snap.nodes == []
    assert g_no_snap.edges == []
    assert g_no_snap.snapshot_id is None
    assert g_no_snap.total_nodes == 0
    assert g_no_snap.total_edges == 0

    # 2. Empty snapshot (no files)
    snap = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )
    session.add(snap)
    await session.commit()

    g_empty_snap = await GraphService.get_project_graph(session, user.id, project.id)
    assert g_empty_snap.nodes == []
    assert g_empty_snap.edges == []
    assert g_empty_snap.snapshot_id == snap.id
    assert g_empty_snap.total_nodes == 0
    assert g_empty_snap.total_edges == 0

    # 3. Files but no symbols or dependencies
    f = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap.id,
        path="README.md",
        filename="README.md",
        extension=".md",
        language="markdown",
        size_bytes=100,
        content_hash="mdhash",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=10,
    )
    session.add(f)
    await session.commit()

    g_files_only = await GraphService.get_project_graph(session, user.id, project.id)
    assert len(g_files_only.nodes) == 1
    assert g_files_only.nodes[0].label == "README.md"
    assert g_files_only.nodes[0].type == GraphNodeType.FILE
    assert g_files_only.edges == []
    assert g_files_only.total_nodes == 1
    assert g_files_only.total_edges == 0


@pytest.mark.asyncio
async def test_graph_authorization_and_isolation(sqlite_session: AsyncSession):
    """
    Step 7: Verify multi-tenant isolation and error handling:
    - User without project access raises ForbiddenException
    - Nonexistent project raises NotFoundException
    """
    session = sqlite_session
    user, _, project, _ = await _setup_project_hierarchy(session)

    # 1. Nonexistent project
    random_project_id = uuid.uuid4()
    with pytest.raises(NotFoundException):
        await GraphService.get_project_graph(session, user.id, random_project_id)

    # 2. Unauthorized user
    unauthorized_user = User(
        id=uuid.uuid4(),
        email="outsider@othercorp.com",
        name="Outsider",
        password_hash="hash",
    )
    session.add(unauthorized_user)
    await session.commit()

    with pytest.raises(ForbiddenException):
        await GraphService.get_project_graph(session, unauthorized_user.id, project.id)


@pytest.mark.asyncio
async def test_graph_api_endpoint_integration(sqlite_session: AsyncSession):
    """
    Step 8 & 14: Verify GET /projects/{project_id}/graph via HTTP client:
    - Route responds with 200 OK
    - Returns valid GraphResponse structure
    - Preserves authentication and authorization
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)

    snap = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )
    f = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap.id,
        path="src/main.py",
        filename="main.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="h1",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=10,
    )
    s = CodeSymbol(
        id=uuid.uuid4(),
        file_id=f.id,
        name="start_app",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="src.main.start_app",
        start_line=1,
        end_line=5,
    )
    d = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f.id,
        external_package="uvicorn",
        dependency_type=DependencyType.IMPORT,
        line_number=1,
    )
    session.add_all([snap, f, s, d])
    await session.commit()

    # Configure dependency overrides for test client
    async def override_get_db():
        yield session

    async def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test both /api/v1/projects/{id}/graph and /projects/{id}/graph
            for endpoint_path in [
                f"/api/v1/projects/{project.id}/graph",
                f"/projects/{project.id}/graph",
            ]:
                response = await client.get(endpoint_path)
                assert response.status_code == 200, f"Failed for {endpoint_path}: {response.text}"

                data = response.json()
                assert "nodes" in data
                assert "edges" in data
                assert "snapshot_id" in data
                assert data["total_nodes"] == len(data["nodes"])
                assert data["total_edges"] == len(data["edges"])

                # Check nodes
                node_types = {n["type"] for n in data["nodes"]}
                assert GraphNodeType.FILE.value in node_types
                assert GraphNodeType.FUNCTION.value in node_types
                assert GraphNodeType.EXTERNAL_PACKAGE.value in node_types

                # Check edges
                edge_types = {e["type"] for e in data["edges"]}
                assert GraphEdgeType.DEFINES.value in edge_types
                assert GraphEdgeType.DEPENDS_ON.value in edge_types

    finally:
        app.dependency_overrides.clear()
