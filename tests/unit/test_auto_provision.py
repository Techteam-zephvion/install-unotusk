import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.models.enums import ProjectStatus
from apps.api.src.models.project import Project
from apps.api.src.models.repository import Repository
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_auto_provision_calls_repository_service_trigger_ingestion():
    """Verify that auto-provisioning calls RepositoryService.trigger_ingestion and not IngestionService."""
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_session = AsyncMock()

    # Query 1: Check existing project -> returns None (fresh provision)
    mock_proj_result = MagicMock()
    mock_proj_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_proj_result

    created_project = MagicMock(id=project_id)
    selected_repo = MagicMock(id=repo_id)

    with (
        patch("apps.api.src.config.settings.settings.TARGET_REPO_URL", "https://github.com/Techteam-zephvion/School-management-app"),
        patch("apps.api.src.services.project_service.ProjectService.create_project", new_callable=AsyncMock) as mock_create_proj,
        patch("apps.api.src.services.repository_service.RepositoryService.select_repository", new_callable=AsyncMock) as mock_select_repo,
        patch("apps.api.src.services.repository_service.RepositoryService.trigger_ingestion", new_callable=AsyncMock) as mock_trigger_ingestion,
    ):
        mock_create_proj.return_value = created_project
        mock_select_repo.return_value = selected_repo

        await AuthService._auto_provision_if_needed(mock_session, user_id, org_id)

        mock_create_proj.assert_called_once()
        mock_select_repo.assert_called_once()
        mock_trigger_ingestion.assert_called_once_with(mock_session, user_id, project_id, repo_id)


@pytest.mark.asyncio
async def test_auto_provision_recovers_stuck_project_without_snapshots():
    """Verify that if a project exists but was left with 0 snapshots, ingestion is triggered."""
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_session = AsyncMock()

    existing_proj = Project(
        id=project_id,
        organization_id=org_id,
        name="School-management-app",
        status=ProjectStatus.CONNECTING,
    )
    existing_repo = Repository(
        id=repo_id,
        project_id=project_id,
        full_name="Techteam-zephvion/School-management-app",
        url="https://github.com/Techteam-zephvion/School-management-app",
    )

    # First execute: select Project -> returns existing_proj
    mock_res_proj = MagicMock()
    mock_res_proj.scalars.return_value.first.return_value = existing_proj

    # Second execute: select Repository -> returns existing_repo
    mock_res_repo = MagicMock()
    mock_res_repo.scalars.return_value.first.return_value = existing_repo

    # Third execute: select RepositorySnapshot -> returns None (0 snapshots)
    mock_res_snap = MagicMock()
    mock_res_snap.scalars.return_value.first.return_value = None

    mock_session.execute.side_effect = [mock_res_proj, mock_res_repo, mock_res_snap]

    with (
        patch("apps.api.src.config.settings.settings.TARGET_REPO_URL", "https://github.com/Techteam-zephvion/School-management-app"),
        patch("apps.api.src.services.repository_service.RepositoryService.trigger_ingestion", new_callable=AsyncMock) as mock_trigger_ingestion,
    ):
        await AuthService._auto_provision_if_needed(mock_session, user_id, org_id)

        # Ingestion should have been triggered for the stuck repo
        mock_trigger_ingestion.assert_called_once_with(mock_session, user_id, project_id, repo_id)


@pytest.mark.asyncio
async def test_auto_provision_skips_when_snapshot_already_exists():
    """Verify that if project already has a snapshot, ingestion is not re-triggered."""
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    project_id = uuid.uuid4()
    repo_id = uuid.uuid4()

    mock_session = AsyncMock()

    existing_proj = Project(id=project_id, organization_id=org_id, name="TestProj")
    existing_repo = Repository(id=repo_id, project_id=project_id)
    existing_snap = RepositorySnapshot(id=uuid.uuid4(), repository_id=repo_id)

    mock_res_proj = MagicMock()
    mock_res_proj.scalars.return_value.first.return_value = existing_proj

    mock_res_repo = MagicMock()
    mock_res_repo.scalars.return_value.first.return_value = existing_repo

    mock_res_snap = MagicMock()
    mock_res_snap.scalars.return_value.first.return_value = existing_snap

    mock_session.execute.side_effect = [mock_res_proj, mock_res_repo, mock_res_snap]

    with (
        patch("apps.api.src.config.settings.settings.TARGET_REPO_URL", "https://github.com/Techteam-zephvion/School-management-app"),
        patch("apps.api.src.services.repository_service.RepositoryService.trigger_ingestion", new_callable=AsyncMock) as mock_trigger_ingestion,
    ):
        await AuthService._auto_provision_if_needed(mock_session, user_id, org_id)
        mock_trigger_ingestion.assert_not_called()
