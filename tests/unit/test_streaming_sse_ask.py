import json
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


class TestStreamingSSEAsk(unittest.IsolatedAsyncioTestCase):
    @patch.object(IntelligenceService, "_verify_project_access", new_callable=AsyncMock)
    @patch.object(IntelligenceService, "_get_active_snapshot", new_callable=AsyncMock)
    @patch("apps.api.src.services.intelligence_service.ProjectContextEngine")
    async def test_ask_question_stream_yields_phases_and_tokens(
        self, mock_engine_cls, mock_get_snap, mock_verify
    ):
        session = AsyncMock()
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        snapshot_id = uuid.uuid4()

        mock_project = Project(id=project_id, organization_id=uuid.uuid4(), name="Test Project")
        mock_verify.return_value = mock_project

        mock_snap = RepositorySnapshot(id=snapshot_id, repository_id=uuid.uuid4(), status=SnapshotStatus.COMPLETED)
        mock_get_snap.return_value = mock_snap

        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_grounded_res = MagicMock()
        mock_grounded_res.content = "FastAPI is our backend API framework."
        mock_grounded_res.evidence = [{"type": "file", "file": "apps/api/src/main.py", "relevance": 0.95}]
        mock_grounded_res.related_entities = ["FastAPI"]
        mock_grounded_res.confidence = "HIGH"
        mock_grounded_res.debug_signals = {}
        mock_engine.investigate = AsyncMock(return_value=mock_grounded_res)

        # Mock conversation query result
        mock_scalar_res = MagicMock()
        mock_scalar_res.scalar_one_or_none.return_value = None
        mock_scalars_res = MagicMock()
        mock_scalars_res.all.return_value = []
        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value = mock_scalars_res
        session.execute = AsyncMock(side_effect=[mock_scalars])

        events = []
        async for chunk in IntelligenceService.ask_question_stream(
            session=session,
            user_id=user_id,
            project_id=project_id,
            question="What is our API framework?",
        ):
            events.append(chunk)

        self.assertGreaterEqual(len(events), 4)

        # Verify phase events
        phase_events = [e for e in events if '"event": "phase"' in e]
        self.assertGreaterEqual(len(phase_events), 2)
        self.assertTrue(any("SCANNING_AST" in e for e in phase_events))
        self.assertTrue(any("GRAPH_TRAVERSAL" in e for e in phase_events))

        # Verify token events
        token_events = [e for e in events if '"event": "token"' in e]
        self.assertGreaterEqual(len(token_events), 1)

        # Verify complete event
        complete_events = [e for e in events if '"event": "complete"' in e]
        self.assertEqual(len(complete_events), 1)
        complete_data = json.loads(complete_events[0].replace("data: ", "").strip())
        self.assertIn("response", complete_data)
        self.assertEqual(complete_data["response"]["content"], "FastAPI is our backend API framework.")


if __name__ == "__main__":
    unittest.main()
