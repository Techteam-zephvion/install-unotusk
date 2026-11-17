import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.models.enums import ProjectStatus
from apps.api.src.models.membership import OrganizationMembership
from apps.api.src.models.project import Project
from apps.api.src.schemas.project import ServerSyncItem, ServerSyncRequest
from apps.api.src.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_sync_servers_does_not_delete_existing_projects():
    """Verify that sync_servers preserves previously created user projects."""
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    existing_proj_id = uuid.uuid4()

    mock_session = AsyncMock()

    # 1. Organization membership query
    mock_mem = MagicMock(spec=OrganizationMembership)
    mock_mem.organization_id = org_id

    mock_mem_res = MagicMock()
    mock_mem_res.scalars.return_value.first.return_value = mock_mem

    # 2. Existing projects query (Project A at port 28000, and a stale mock project)
    existing_real_project = MagicMock(spec=Project)
    existing_real_project.id = existing_proj_id
    existing_real_project.name = "Existing Service"
    existing_real_project.slug = "existing-service"
    existing_real_project.port = 28000
    existing_real_project.status = ProjectStatus.READY

    stale_mock_project = MagicMock(spec=Project)
    stale_mock_project.id = uuid.uuid4()
    stale_mock_project.name = "SyncGuard"
    stale_mock_project.slug = "syncguard"
    stale_mock_project.port = 27999

    mock_proj_res_1 = MagicMock()
    mock_proj_res_1.scalars.return_value.all.return_value = [
        existing_real_project,
        stale_mock_project,
    ]

    mock_proj_res_2 = MagicMock()
    mock_proj_res_2.scalars.return_value.all.return_value = [existing_real_project]

    # Session execution sequence:
    # 1: mem_query
    # 2: existing_projects_query (before cleanup)
    # 3: existing_projects_query (after cleanup)
    # 4: slug check (for new server)
    # 5: repo query
    # 6: integ query
    mock_session.execute.side_effect = [
        mock_mem_res,
        mock_proj_res_1,
        mock_proj_res_2,
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # slug check
        MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))),  # repo query
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # integ query
    ]

    # New server being synced on port 28100
    sync_request = ServerSyncRequest(
        servers=[
            ServerSyncItem(
                name="New Project Server",
                port=28100,
                state="running",
                repo_url="https://github.com/org/new-repo",
            )
        ]
    )

    with patch.object(ProjectService, "list_projects", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [existing_real_project]
        await ProjectService.sync_servers(mock_session, user_id, sync_request)

    # Stale mock project MUST be deleted
    mock_session.delete.assert_called_once_with(stale_mock_project)

    # Existing real project MUST NOT be deleted
    deleted_items = [call.args[0] for call in mock_session.delete.call_args_list]
    assert existing_real_project not in deleted_items
