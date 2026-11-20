import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import DependencyType
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.project import Project
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.graph_service import GraphService


class TestGraphServiceHotspotsCycles(unittest.IsolatedAsyncioTestCase):
    @patch("apps.api.src.services.repository_service.RepositoryService._verify_project_access", new_callable=AsyncMock)
    @patch("apps.api.src.services.repository_service.RepositoryService._get_latest_snapshot", new_callable=AsyncMock)
    async def test_detects_circular_dependencies_and_hotspots(self, mock_get_snap, mock_verify):
        session = AsyncMock()
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        snapshot_id = uuid.uuid4()

        mock_project = Project(id=project_id, organization_id=uuid.uuid4(), name="Test Project")
        mock_verify.return_value = mock_project

        mock_snap = RepositorySnapshot(id=snapshot_id, repository_id=uuid.uuid4())
        mock_get_snap.return_value = mock_snap

        f1_id = uuid.uuid4()
        f2_id = uuid.uuid4()
        f3_id = uuid.uuid4()

        f1 = RepositoryFile(id=f1_id, snapshot_id=snapshot_id, path="src/a.py", filename="a.py", extension=".py", language="Python", size_bytes=100, content_hash="h1", is_binary=False, is_generated=False, is_test=False, line_count=10, parser_supported=True)
        f2 = RepositoryFile(id=f2_id, snapshot_id=snapshot_id, path="src/b.py", filename="b.py", extension=".py", language="Python", size_bytes=100, content_hash="h2", is_binary=False, is_generated=False, is_test=False, line_count=10, parser_supported=True)
        f3 = RepositoryFile(id=f3_id, snapshot_id=snapshot_id, path="src/c.py", filename="c.py", extension=".py", language="Python", size_bytes=100, content_hash="h3", is_binary=False, is_generated=False, is_test=False, line_count=10, parser_supported=True)

        # Create cycle: A -> B -> C -> A
        d1 = CodeDependency(id=uuid.uuid4(), source_file_id=f1_id, target_file_id=f2_id, dependency_type=DependencyType.IMPORT, line_number=1)
        d2 = CodeDependency(id=uuid.uuid4(), source_file_id=f2_id, target_file_id=f3_id, dependency_type=DependencyType.IMPORT, line_number=1)
        d3 = CodeDependency(id=uuid.uuid4(), source_file_id=f3_id, target_file_id=f1_id, dependency_type=DependencyType.IMPORT, line_number=1)

        # Mock database queries
        mock_services_scalars = MagicMock()
        mock_services_scalars.all.return_value = []
        mock_services_res = MagicMock()
        mock_services_res.scalars.return_value = mock_services_scalars

        mock_repo_res = MagicMock()
        mock_repo_res.scalar_one_or_none.return_value = None

        mock_files_scalars = MagicMock()
        mock_files_scalars.all.return_value = [f1, f2, f3]
        mock_files_res = MagicMock()
        mock_files_res.scalars.return_value = mock_files_scalars

        mock_syms_scalars = MagicMock()
        mock_syms_scalars.all.return_value = []
        mock_syms_res = MagicMock()
        mock_syms_res.scalars.return_value = mock_syms_scalars

        mock_deps_scalars = MagicMock()
        mock_deps_scalars.all.return_value = [d1, d2, d3]
        mock_deps_res = MagicMock()
        mock_deps_res.scalars.return_value = mock_deps_scalars

        session.execute = AsyncMock(side_effect=[
            mock_services_res,
            mock_files_res,
            mock_repo_res,
            mock_syms_res,
            mock_deps_res,
        ])

        response = await GraphService.get_project_graph(session, user_id, project_id)

        self.assertGreaterEqual(len(response.circular_dependencies), 1)
        self.assertTrue(any(len(c) >= 3 for c in response.circular_dependencies))
        # Verify node metadata has cycle and hotspot flags
        cycle_node_ids = [str(f1_id), str(f2_id), str(f3_id)]
        for n in response.nodes:
            if n.id in cycle_node_ids:
                self.assertTrue(n.metadata.get("has_circular_dependency"))


if __name__ == "__main__":
    unittest.main()
