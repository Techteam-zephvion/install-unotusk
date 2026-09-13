import uuid

import pytest
from httpx import AsyncClient

from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    DependencyType,
    IntegrationProvider,
    IntegrationStatus,
    SnapshotStatus,
    SymbolType,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.integration import Integration
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol


@pytest.mark.asyncio
async def test_get_file_detail_api_success(
    client: AsyncClient,
    db_session,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    # Setup user, org, and project
    user = await create_test_user(email="file-detail-user@org.com")
    org, _ = await create_test_org(user=user, name="Org Detail")
    project = await create_test_project(organization=org, name="Project Detail")
    headers = auth_headers(user)

    # Create integration & repository & snapshot
    integration = Integration(
        id=uuid.uuid4(),
        project_id=project.id,
        provider=IntegrationProvider.GITHUB,
        status=IntegrationStatus.CONNECTED,
        external_id="gh-12345",
        integration_metadata={},
    )
    db_session.add(integration)
    await db_session.flush()

    repo = Repository(
        project_id=project.id,
        integration_id=integration.id,
        external_id="12345",
        owner="org",
        name="test-repo",
        full_name="org/test-repo",
        default_branch="main",
        url="https://github.com/org/test-repo",
    )
    db_session.add(repo)
    await db_session.flush()

    snapshot = RepositorySnapshot(
        repository_id=repo.id,
        commit_sha="abc1234",
        branch="main",
        status=SnapshotStatus.COMPLETED,
    )
    db_session.add(snapshot)
    await db_session.flush()

    # Create target and source files
    target_file = RepositoryFile(
        snapshot_id=snapshot.id,
        path="src/adapters.py",
        filename="adapters.py",
        extension=".py",
        language="Python",
        size_bytes=1024,
        content_hash="h1",
        line_count=50,
        parser_supported=True,
    )
    db_session.add(target_file)
    await db_session.flush()

    main_file = RepositoryFile(
        snapshot_id=snapshot.id,
        path="src/sessions.py",
        filename="sessions.py",
        extension=".py",
        language="Python",
        size_bytes=2048,
        content_hash="h2",
        line_count=100,
        parser_supported=True,
    )
    db_session.add(main_file)
    await db_session.flush()

    # Create symbol in main_file
    sym = CodeSymbol(
        file_id=main_file.id,
        name="Session",
        symbol_type=SymbolType.CLASS,
        qualified_name="sessions.Session",
        start_line=10,
        end_line=60,
    )
    db_session.add(sym)

    # Create outgoing dependency: main_file -> target_file
    out_dep = CodeDependency(
        source_file_id=main_file.id,
        target_file_id=target_file.id,
        dependency_type=DependencyType.IMPORT,
        line_number=5,
    )
    db_session.add(out_dep)

    # Create incoming dependency: target_file -> main_file
    in_dep = CodeDependency(
        source_file_id=target_file.id,
        target_file_id=main_file.id,
        dependency_type=DependencyType.IMPORT,
        line_number=8,
    )
    db_session.add(in_dep)

    # Create code chunk
    chunk = CodeChunk(
        snapshot_id=snapshot.id,
        file_id=main_file.id,
        symbol_id=sym.id,
        chunk_type="class",
        name="Session",
        path="src/sessions.py",
        content="class Session:\n    def __init__(self):\n        pass",
        start_line=10,
        end_line=60,
    )
    db_session.add(chunk)
    await db_session.commit()

    # Fetch file detail via API
    res = await client.get(
        f"/api/v1/projects/{project.id}/files/{main_file.id}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["file"]["id"] == str(main_file.id)
    assert data["file"]["filename"] == "sessions.py"
    assert len(data["symbols"]) == 1
    assert data["symbols"][0]["name"] == "Session"
    assert len(data["outgoing_dependencies"]) == 1
    assert data["outgoing_dependencies"][0]["target_path"] == "src/adapters.py"
    assert len(data["incoming_references"]) == 1
    assert data["incoming_references"][0]["source_path"] == "src/adapters.py"
    assert len(data["chunks"]) == 1
    assert "class Session" in data["full_content"]


@pytest.mark.asyncio
async def test_get_file_detail_api_not_found_and_isolation(
    client: AsyncClient,
    create_test_user,
    create_test_org,
    create_test_project,
    auth_headers,
):
    user_a = await create_test_user(email="user-a-detail@org.com")
    org_a, _ = await create_test_org(user=user_a, name="Org A")
    project_a = await create_test_project(organization=org_a, name="Project A")
    headers_a = auth_headers(user_a)

    user_b = await create_test_user(email="user-b-detail@org.com")
    headers_b = auth_headers(user_b)

    fake_file_id = uuid.uuid4()

    # 404 for nonexistent file
    res = await client.get(
        f"/api/v1/projects/{project_a.id}/files/{fake_file_id}",
        headers=headers_a,
    )
    assert res.status_code == 404

    # 403 for user B accessing project A
    cross_res = await client.get(
        f"/api/v1/projects/{project_a.id}/files/{fake_file_id}",
        headers=headers_b,
    )
    assert cross_res.status_code == 403
