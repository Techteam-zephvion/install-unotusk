import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from apps.api.src.api.exceptions import ForbiddenException
from apps.api.src.db.base import Base
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
from apps.api.src.services.repository_service import RepositoryService


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
async def test_list_files_scopes_to_latest_snapshot(sqlite_session: AsyncSession):
    """
    Sprint 1 Regression:
    Verify that list_files() returns only files belonging to the latest snapshot
    and excludes duplicate/stale files from previous snapshots.
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)
    now = datetime.now(UTC)

    # 1. Snapshot 1 (Older)
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
        path="src/file_a.py",
        filename="file_a.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="hash-1a",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=10,
    )
    f1_b = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap1.id,
        path="src/file_b.py",
        filename="file_b.py",
        extension=".py",
        language="python",
        size_bytes=200,
        content_hash="hash-1b",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=20,
    )

    # 2. Snapshot 2 (Latest - Re-ingested)
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
        path="src/file_a.py",
        filename="file_a.py",
        extension=".py",
        language="python",
        size_bytes=150,
        content_hash="hash-2a",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=15,
    )
    f2_b = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap2.id,
        path="src/file_b.py",
        filename="file_b.py",
        extension=".py",
        language="python",
        size_bytes=200,
        content_hash="hash-2b",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=20,
    )
    f2_c = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap2.id,
        path="src/file_c.py",
        filename="file_c.py",
        extension=".py",
        language="python",
        size_bytes=300,
        content_hash="hash-2c",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=30,
    )

    session.add_all([snap1, f1_a, f1_b, snap2, f2_a, f2_b, f2_c])
    await session.commit()

    # Query files via service
    files = await RepositoryService.list_files(session, user.id, project.id)

    # Verify only Snapshot 2 files returned
    assert len(files) == 3
    file_ids = {f.id for f in files}
    assert file_ids == {f2_a.id, f2_b.id, f2_c.id}

    # Verify Snapshot 1 files NOT returned
    assert f1_a.id not in file_ids
    assert f1_b.id not in file_ids

    # Verify paths and ordering
    assert [f.path for f in files] == ["src/file_a.py", "src/file_b.py", "src/file_c.py"]


@pytest.mark.asyncio
async def test_list_symbols_scopes_to_latest_snapshot(sqlite_session: AsyncSession):
    """
    Sprint 1 Regression:
    Verify that list_symbols() returns only symbols from the latest snapshot.
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)
    now = datetime.now(UTC)

    # Snapshot 1
    snap1 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
    )
    f1 = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap1.id,
        path="src/parser.py",
        filename="parser.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="h1",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=10,
    )
    s1_old = CodeSymbol(
        id=uuid.uuid4(),
        file_id=f1.id,
        name="OldParser",
        symbol_type=SymbolType.CLASS,
        qualified_name="src.parser.OldParser",
        start_line=1,
        end_line=5,
        symbol_metadata={},
    )

    # Snapshot 2 (Latest)
    snap2 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=1),
    )
    f2 = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap2.id,
        path="src/parser.py",
        filename="parser.py",
        extension=".py",
        language="python",
        size_bytes=120,
        content_hash="h2",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=12,
    )
    s2_new = CodeSymbol(
        id=uuid.uuid4(),
        file_id=f2.id,
        name="NewParser",
        symbol_type=SymbolType.CLASS,
        qualified_name="src.parser.NewParser",
        start_line=1,
        end_line=8,
        symbol_metadata={},
    )

    session.add_all([snap1, f1, s1_old, snap2, f2, s2_new])
    await session.commit()

    symbols = await RepositoryService.list_symbols(session, user.id, project.id)

    assert len(symbols) == 1
    assert symbols[0].id == s2_new.id
    assert symbols[0].name == "NewParser"
    assert symbols[0].file_path == "src/parser.py"


@pytest.mark.asyncio
async def test_list_dependencies_scopes_to_latest_snapshot(sqlite_session: AsyncSession):
    """
    Sprint 1 Regression:
    Verify that list_dependencies() returns only dependencies from the latest snapshot.
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)
    now = datetime.now(UTC)

    # Snapshot 1
    snap1 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
    )
    f1 = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap1.id,
        path="src/client.py",
        filename="client.py",
        extension=".py",
        language="python",
        size_bytes=100,
        content_hash="h1",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=10,
    )
    d1_old = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f1.id,
        external_package="requests",
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
    f2 = RepositoryFile(
        id=uuid.uuid4(),
        snapshot_id=snap2.id,
        path="src/client.py",
        filename="client.py",
        extension=".py",
        language="python",
        size_bytes=110,
        content_hash="h2",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=11,
    )
    d2_new = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=f2.id,
        external_package="httpx",
        dependency_type=DependencyType.IMPORT,
        line_number=2,
    )

    session.add_all([snap1, f1, d1_old, snap2, f2, d2_new])
    await session.commit()

    deps = await RepositoryService.list_dependencies(session, user.id, project.id)

    assert len(deps) == 1
    assert deps[0].id == d2_new.id
    assert deps[0].external_package == "httpx"
    assert deps[0].source_path == "src/client.py"


@pytest.mark.asyncio
async def test_repeated_reingestion_scopes_to_latest_snapshot(sqlite_session: AsyncSession):
    """
    Sprint 1 Regression:
    Test repeated re-indexing: Snapshot 1 -> Snapshot 2 -> Snapshot 3.
    Verifies that ONLY Snapshot 3 entities are returned.
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)
    now = datetime.now(UTC)

    snaps = []
    files = []
    symbols = []
    deps = []

    # Create 3 sequential snapshots
    for i in range(1, 4):
        snap = RepositorySnapshot(
            id=uuid.uuid4(),
            repository_id=repo.id,
            branch="main",
            status=SnapshotStatus.COMPLETED,
            created_at=now - timedelta(hours=(4 - i)),
        )
        snaps.append(snap)

        f = RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snap.id,
            path=f"src/module_{i}.py",
            filename=f"module_{i}.py",
            extension=".py",
            language="python",
            size_bytes=100 * i,
            content_hash=f"hash-{i}",
            is_binary=False,
            is_generated=False,
            is_test=False,
            line_count=10 * i,
        )
        files.append(f)

        sym = CodeSymbol(
            id=uuid.uuid4(),
            file_id=f.id,
            name=f"ServiceV{i}",
            symbol_type=SymbolType.CLASS,
            qualified_name=f"src.module_{i}.ServiceV{i}",
            start_line=1,
            end_line=10,
            symbol_metadata={},
        )
        symbols.append(sym)

        dep = CodeDependency(
            id=uuid.uuid4(),
            source_file_id=f.id,
            external_package=f"package_v{i}",
            dependency_type=DependencyType.IMPORT,
            line_number=1,
        )
        deps.append(dep)

    session.add_all(snaps + files + symbols + deps)
    await session.commit()

    # Query all three endpoints
    res_files = await RepositoryService.list_files(session, user.id, project.id)
    res_symbols = await RepositoryService.list_symbols(session, user.id, project.id)
    res_deps = await RepositoryService.list_dependencies(session, user.id, project.id)

    # Verify ONLY Snapshot 3 entities returned
    assert len(res_files) == 1
    assert res_files[0].id == files[2].id
    assert res_files[0].path == "src/module_3.py"

    assert len(res_symbols) == 1
    assert res_symbols[0].id == symbols[2].id
    assert res_symbols[0].name == "ServiceV3"

    assert len(res_deps) == 1
    assert res_deps[0].id == deps[2].id
    assert res_deps[0].external_package == "package_v3"


@pytest.mark.asyncio
async def test_single_snapshot_behavior(sqlite_session: AsyncSession):
    """Verify standard functionality when project has only one snapshot."""
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
        path="main.py",
        filename="main.py",
        extension=".py",
        language="python",
        size_bytes=50,
        content_hash="h",
        is_binary=False,
        is_generated=False,
        is_test=False,
        line_count=5,
    )
    session.add_all([snap, f])
    await session.commit()

    files = await RepositoryService.list_files(session, user.id, project.id)
    assert len(files) == 1
    assert files[0].id == f.id


@pytest.mark.asyncio
async def test_latest_snapshot_fewer_files_deleted_files_omitted(sqlite_session: AsyncSession):
    """
    Verify that when Snapshot 2 contains fewer files than Snapshot 1
    (e.g., files were deleted), the deleted files from Snapshot 1 do NOT appear.
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)
    now = datetime.now(UTC)

    # Snapshot 1 had 5 files
    snap1 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
    )
    s1_files = [
        RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snap1.id,
            path=f"file_{i}.py",
            filename=f"file_{i}.py",
            extension=".py",
            language="python",
            size_bytes=50,
            content_hash=f"h1_{i}",
            is_binary=False,
            is_generated=False,
            is_test=False,
            line_count=5,
        )
        for i in range(1, 6)
    ]

    # Snapshot 2 has only 2 files (3 files were deleted)
    snap2 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=1),
    )
    s2_files = [
        RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snap2.id,
            path=f"file_{i}.py",
            filename=f"file_{i}.py",
            extension=".py",
            language="python",
            size_bytes=60,
            content_hash=f"h2_{i}",
            is_binary=False,
            is_generated=False,
            is_test=False,
            line_count=6,
        )
        for i in range(1, 3)
    ]

    session.add_all([snap1, *s1_files, snap2, *s2_files])
    await session.commit()

    files = await RepositoryService.list_files(session, user.id, project.id)
    assert len(files) == 2
    paths = [f.path for f in files]
    assert paths == ["file_1.py", "file_2.py"]
    assert "file_3.py" not in paths
    assert "file_4.py" not in paths
    assert "file_5.py" not in paths


@pytest.mark.asyncio
async def test_pagination_does_not_reintroduce_old_snapshot_records(sqlite_session: AsyncSession):
    """
    Verify pagination limit applies only to the latest snapshot
    and does not pull in records from previous snapshots.
    """
    session = sqlite_session
    user, _, project, repo = await _setup_project_hierarchy(session)
    now = datetime.now(UTC)

    # Snapshot 1 with 5 files
    snap1 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=2),
    )
    s1_files = [
        RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snap1.id,
            path=f"file_{i}.py",
            filename=f"file_{i}.py",
            extension=".py",
            language="python",
            size_bytes=50,
            content_hash=f"h1_{i}",
            is_binary=False,
            is_generated=False,
            is_test=False,
            line_count=5,
        )
        for i in range(1, 6)
    ]

    # Snapshot 2 with 3 files
    snap2 = RepositorySnapshot(
        id=uuid.uuid4(),
        repository_id=repo.id,
        branch="main",
        status=SnapshotStatus.COMPLETED,
        created_at=now - timedelta(hours=1),
    )
    s2_files = [
        RepositoryFile(
            id=uuid.uuid4(),
            snapshot_id=snap2.id,
            path=f"file_{i}.py",
            filename=f"file_{i}.py",
            extension=".py",
            language="python",
            size_bytes=60,
            content_hash=f"h2_{i}",
            is_binary=False,
            is_generated=False,
            is_test=False,
            line_count=6,
        )
        for i in range(1, 4)
    ]

    session.add_all([snap1, *s1_files, snap2, *s2_files])
    await session.commit()

    # Limit = 2 (less than total 3 files in Snapshot 2)
    files = await RepositoryService.list_files(session, user.id, project.id, limit=2)
    assert len(files) == 2
    # Both must belong to Snapshot 2
    file_ids = {f.id for f in files}
    assert file_ids == {s2_files[0].id, s2_files[1].id}
    # No Snapshot 1 files
    assert not any(f.id in {sf.id for sf in s1_files} for f in files)


@pytest.mark.asyncio
async def test_project_with_no_snapshots_returns_empty(sqlite_session: AsyncSession):
    """Verify that a project with no snapshots returns empty lists cleanly."""
    session = sqlite_session
    user, _, project, _ = await _setup_project_hierarchy(session)

    files = await RepositoryService.list_files(session, user.id, project.id)
    symbols = await RepositoryService.list_symbols(session, user.id, project.id)
    deps = await RepositoryService.list_dependencies(session, user.id, project.id)

    assert files == []
    assert symbols == []
    assert deps == []


@pytest.mark.asyncio
async def test_project_access_control_maintained(sqlite_session: AsyncSession):
    """Verify organization/project access control is maintained."""
    session = sqlite_session
    user, _, project, _ = await _setup_project_hierarchy(session)

    # Create unassociated user
    other_user = User(
        id=uuid.uuid4(),
        email="unauthorized@example.com",
        name="Outsider",
        password_hash="hash",
    )
    session.add(other_user)
    await session.commit()

    with pytest.raises(ForbiddenException):
        await RepositoryService.list_files(session, other_user.id, project.id)

    with pytest.raises(ForbiddenException):
        await RepositoryService.list_symbols(session, other_user.id, project.id)

    with pytest.raises(ForbiddenException):
        await RepositoryService.list_dependencies(session, other_user.id, project.id)
