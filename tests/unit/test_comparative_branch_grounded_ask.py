import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from apps.api.src.models.enums import SnapshotStatus
from apps.api.src.models.project import Project
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.services.intelligence_service import IntelligenceService


class TestComparativeBranchGroundedAsk(unittest.IsolatedAsyncioTestCase):
    @patch.object(IntelligenceService, "_verify_project_access", new_callable=AsyncMock)
    @patch.object(IntelligenceService, "_get_active_snapshot", new_callable=AsyncMock)
    @patch("apps.api.src.services.intelligence_service.ProjectContextEngine")
    async def test_ask_question_with_compare_branch_grounds_comparative_context(
        self, mock_engine_cls, mock_get_snap, mock_verify
    ):
        session = AsyncMock()
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        snap_main_id = uuid.uuid4()
        snap_feat_id = uuid.uuid4()

        mock_project = Project(id=project_id, organization_id=uuid.uuid4(), name="Test Project")
        mock_verify.return_value = mock_project

        mock_snap_main = RepositorySnapshot(id=snap_main_id, repository_id=uuid.uuid4(), branch="main", status=SnapshotStatus.COMPLETED)
        mock_snap_feat = RepositorySnapshot(id=snap_feat_id, repository_id=uuid.uuid4(), branch="feature/auth-v2", status=SnapshotStatus.COMPLETED)

        def get_snap_side_effect(session, project_id, branch=None):
            if branch == "feature/auth-v2":
                return mock_snap_feat
            return mock_snap_main

        mock_get_snap.side_effect = get_snap_side_effect

        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_grounded_res = MagicMock()
        mock_grounded_res.content = "In feature/auth-v2, JWT signing was migrated to Ed25519."
        mock_grounded_res.evidence = [{"type": "file", "file": "apps/api/src/auth.py", "relevance": 0.9}]
        mock_grounded_res.related_entities = ["JWT", "Ed25519"]
        mock_grounded_res.confidence = "HIGH"
        mock_grounded_res.debug_signals = {}
        mock_engine.investigate = AsyncMock(return_value=mock_grounded_res)

        mock_scalar_res = MagicMock()
        mock_scalar_res.scalar_one_or_none.return_value = None
        mock_scalars_res = MagicMock()
        mock_scalars_res.all.return_value = []
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value = mock_scalars_res
        session.execute = AsyncMock(side_effect=[mock_scalars])

        response = await IntelligenceService.ask_question(
            session=session,
            user_id=user_id,
            project_id=project_id,
            question="What changed in authentication architecture?",
            branch="main",
            compare_branch="feature/auth-v2",
        )

        self.assertIn("feature/auth-v2", response.content)
        # Verify engine.investigate received comparative prompt grounding
        investigate_args = mock_engine.investigate.call_args.kwargs
        self.assertIn("Comparative Grounding", investigate_args["question"])
        self.assertIn("feature/auth-v2", investigate_args["question"])


if __name__ == "__main__":
    unittest.main()
