import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.src.api.dependencies.auth import get_current_user
from apps.api.src.api.dependencies.database import get_db
from apps.api.src.api.exceptions import ConflictException, NotFoundException
from apps.api.src.db.base import Base
from apps.api.src.main import app
from apps.api.src.models.enums import (
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
from apps.api.src.schemas.graph import GraphEdgeType, GraphNodeType, GraphResponse
from apps.api.src.schemas.service import ServiceCreate, ServiceUpdate
from apps.api.src.services.graph_service import GraphService
from apps.api.src.services.service_service import ServiceService


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


async def _setup_project(
    session: AsyncSession,
) -> tuple[User, Organization, Project, Repository]:
    user = User(
        id=uuid.uuid4(),
        email=f"dev-{uuid.uuid4().hex[:6]}@example.com",
        name="Engineer",
        password_hash="hash",
    )
    org = Organization(
        id=uuid.uuid4(),
        name="Platform Team",
        slug=f"platform-{uuid.uuid4().hex[:6]}",
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
        name="E-Commerce Platform",
        slug=f"shop-{uuid.uuid4().hex[:6]}",
        status=ProjectStatus.READY,
    )
    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-shop-repo",
        integration_metadata={},
    )
    repo = Repository(
        id=uuid.uuid4(),
        project_id=project.id,
        integration_id=integration.id,
        provider=IntegrationProvider.GITHUB,
        external_id="repo-2001",
        owner="org",
        name="shop-backend",
        full_name="org/shop-backend",
        default_branch="main",
        url="https://github.com/org/shop-backend",
        is_private=True,
    )
    session.add_all([user, org, membership, project, integration, repo])
    await session.commit()
    return user, org, project, repo


@pytest.mark.asyncio
async def test_service_crud_lifecycle(sqlite_session: AsyncSession):
    session = sqlite_session
    user, _, project, repo = await _setup_project(session)

    # 1. Create Service
    create_data = ServiceCreate(
        name="Auth Service",
        description="Handles authentication and JWT issuance",
        tier="tier-1",
        service_metadata={"protocol": "gRPC"},
    )
    service = await ServiceService.create_service(session, user.id, project.id, create_data)

    assert service.name == "Auth Service"
    assert service.slug == "auth-service"
    assert service.tier == "tier-1"
    assert service.description == "Handles authentication and JWT issuance"
    assert service.service_metadata == {"protocol": "gRPC"}
    assert service.repository_ids == []

    # 2. Duplicate slug conflict in same project
    with pytest.raises(ConflictException):
        await ServiceService.create_service(session, user.id, project.id, create_data)

    # 3. List Services
    services = await ServiceService.list_services(session, user.id, project.id)
    assert len(services) == 1
    assert services[0].id == service.id

    # 4. Get Service
    fetched = await ServiceService.get_service(session, user.id, project.id, service.id)
    assert fetched.id == service.id

    # 5. Update Service
    update_data = ServiceUpdate(
        name="Identity & Auth Service",
        tier="tier-0",
    )
    updated = await ServiceService.update_service(session, user.id, project.id, service.id, update_data)
    assert updated.name == "Identity & Auth Service"
    assert updated.tier == "tier-0"

    # 6. Associate Repository
    associated = await ServiceService.associate_repository(
        session, user.id, project.id, service.id, repo.id
    )
    assert repo.id in associated.repository_ids

    # 7. Dissociate Repository
    dissociated = await ServiceService.dissociate_repository(
        session, user.id, project.id, service.id, repo.id
    )
    assert repo.id not in dissociated.repository_ids

    # 8. Delete Service
    await ServiceService.delete_service(session, user.id, project.id, service.id)
    with pytest.raises(NotFoundException):
        await ServiceService.get_service(session, user.id, project.id, service.id)


@pytest.mark.asyncio
async def test_service_graph_end_to_end_hierarchy(sqlite_session: AsyncSession):
    """
    Verify complete hierarchy:
    Project -> Service -> Repository -> File -> Symbol
    And GraphResponse contains:
    1. SERVICE node
    2. REPOSITORY node
    3. SERVICE -> REPOSITORY (CONTAINS)
    4. REPOSITORY -> FILE (CONTAINS)
    5. FILE -> SYMBOL (DEFINES)
    6. Inter-service DEPENDS_ON edge
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project(session)

    # 1. Create two services: Auth Service and Order Service
    # Order Service depends on Auth Service via service_metadata
    auth_srv = await ServiceService.create_service(
        session,
        user.id,
        project.id,
        ServiceCreate(name="Auth Service", tier="tier-0"),
    )
    order_srv = await ServiceService.create_service(
        session,
        user.id,
        project.id,
        ServiceCreate(
            name="Order Service",
            tier="tier-1",
            service_metadata={"depends_on": ["auth-service"]},
        ),
    )

    # 2. Associate repo with Order Service
    await ServiceService.associate_repository(
        session, user.id, project.id, order_srv.id, repo.id
    )

    # 3. Create snapshot, file, and symbol under repo
    snap = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )
    file = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap.id,
        path="src/orders/checkout.py",
        filename="checkout.py",
        extension=".py",
        language="python",
        size_bytes=200,
        content_hash="hash_orders",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=50,
    )
    symbol = CodeSymbol(
        id=uuid.uuid4(),
        file_id=file.id,
        name="CheckoutService",
        symbol_type=SymbolType.CLASS,
        qualified_name="src.orders.checkout.CheckoutService",
        start_line=10,
        end_line=45,
    )
    session.add_all([snap, file, symbol])
    await session.commit()

    # 4. Generate Graph
    graph = await GraphService.get_project_graph(session, user.id, project.id)

    assert isinstance(graph, GraphResponse)
    node_ids = {n.id for n in graph.nodes}
    node_map = {n.id: n for n in graph.nodes}

    # Verify SERVICE nodes
    assert str(auth_srv.id) in node_ids
    assert node_map[str(auth_srv.id)].type == GraphNodeType.SERVICE
    assert node_map[str(auth_srv.id)].label == "Auth Service"

    assert str(order_srv.id) in node_ids
    assert node_map[str(order_srv.id)].type == GraphNodeType.SERVICE
    assert node_map[str(order_srv.id)].label == "Order Service"

    # Verify REPOSITORY node
    assert str(repo.id) in node_ids
    assert node_map[str(repo.id)].type == GraphNodeType.REPOSITORY

    # Verify FILE and SYMBOL nodes
    assert str(file.id) in node_ids
    assert node_map[str(file.id)].type == GraphNodeType.FILE
    assert str(symbol.id) in node_ids
    assert node_map[str(symbol.id)].type == GraphNodeType.CLASS

    # Edge verifications
    edges = graph.edges

    # Service -> Service DEPENDS_ON edge
    assert any(
        e.source == str(order_srv.id)
        and e.target == str(auth_srv.id)
        and e.type == GraphEdgeType.DEPENDS_ON
        for e in edges
    )

    # Service -> Repository CONTAINS edge
    assert any(
        e.source == str(order_srv.id)
        and e.target == str(repo.id)
        and e.type == GraphEdgeType.CONTAINS
        for e in edges
    )

    # Repository -> File CONTAINS edge
    assert any(
        e.source == str(repo.id)
        and e.target == str(file.id)
        and e.type == GraphEdgeType.CONTAINS
        for e in edges
    )

    # File -> Symbol DEFINES edge
    assert any(
        e.source == str(file.id)
        and e.target == str(symbol.id)
        and e.type == GraphEdgeType.DEFINES
        for e in edges
    )


@pytest.mark.asyncio
async def test_service_api_endpoints(sqlite_session: AsyncSession):
    """Verify REST API endpoints for Service ontology."""
    session = sqlite_session
    user, _, project, repo = await _setup_project(session)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /projects/{project_id}/services
        resp = await client.post(
            f"/api/v1/projects/{project.id}/services",
            json={"name": "Billing Service", "tier": "tier-1", "description": "Invoicing & payments"},
        )
        assert resp.status_code == 201
        data = resp.json()
        service_id = data["id"]
        assert data["name"] == "Billing Service"
        assert data["slug"] == "billing-service"

        # 2. GET /projects/{project_id}/services
        list_resp = await client.get(f"/api/v1/projects/{project.id}/services")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        # 3. GET /projects/{project_id}/services/{service_id}
        get_resp = await client.get(f"/api/v1/projects/{project.id}/services/{service_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == service_id

        # 4. POST /projects/{project_id}/services/{service_id}/repositories/{repo_id}
        assoc_resp = await client.post(
            f"/api/v1/projects/{project.id}/services/{service_id}/repositories/{repo.id}"
        )
        assert assoc_resp.status_code == 200
        assert str(repo.id) in assoc_resp.json()["repository_ids"]

        # 5. GET /projects/{project_id}/graph includes Service and Repository
        graph_resp = await client.get(f"/api/v1/projects/{project.id}/graph")
        assert graph_resp.status_code == 200
        g_data = graph_resp.json()
        node_labels = [n["label"] for n in g_data["nodes"]]
        assert "Billing Service" in node_labels

    app.dependency_overrides.clear()
