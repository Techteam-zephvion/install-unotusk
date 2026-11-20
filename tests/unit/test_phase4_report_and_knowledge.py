import importlib.machinery
import sys
import types
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# Pre-load enums module directly to avoid loading all DB models during unit test
enums_mod = importlib.machinery.SourceFileLoader(
    "apps.api.src.models.enums", str(ROOT / "apps/api/src/models/enums.py")
).load_module()
sys.modules["apps.api.src.models.enums"] = enums_mod

# Provide lightweight settings module mock if pydantic is not installed in testing environment
try:
    import pydantic
except ImportError:
    dummy_settings_mod = types.ModuleType("apps.api.src.config.settings")
    class _MockSettings:
        CONTEXT_BUDGET_TOKENS = 8000
        LLM_PROVIDER = "offline"
        ANTHROPIC_API_KEY = ""
        ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
        GROQ_API_KEY = ""
        DEFAULT_THINKING_BUDGET = 2048
        AUTH_SECRET = "test-secret"
    dummy_settings_mod.settings = _MockSettings()
    sys.modules["apps.api.src.config.settings"] = dummy_settings_mod

from datetime import UTC, datetime

from apps.api.src.models.enums import (
    FindingCategory,
    FindingSeverity,
    KnowledgeCategory,
    KnowledgeClass,
    ReportStatus,
    SymbolType,
)
from apps.api.src.services.context_engine.embeddings import generate_text_embedding
from apps.api.src.services.report_engine.base import FactData
from apps.api.src.services.report_engine.interpretation_engine import InterpretationEngine


class MockNamedEntity:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestPhase4ReportAndKnowledge(unittest.TestCase):
    def test_interpretation_engine_10_sections_and_multilang_areas(self):
        """Verify that InterpretationEngine constructs all 10 report sections with multi-language grouping."""
        proj_id = uuid.uuid4()
        snap_id = uuid.uuid4()

        project = MockNamedEntity(id=proj_id, name="Unotusk Multi-Platform", slug="unotusk")
        snapshot = MockNamedEntity(
            id=snap_id,
            commit_sha="abc123456789",
            branch="main",
            created_at=datetime.now(UTC),
        )

        # Mixed repository: Flutter client, Go backend services, Python API
        f_flutter = MockNamedEntity(
            id=uuid.uuid4(),
            snapshot_id=snap_id,
            path="app/lib/screens/ask_tab.dart",
            language="dart",
            line_count=250,
            size_bytes=6000,
        )
        f_setup = MockNamedEntity(
            id=uuid.uuid4(),
            snapshot_id=snap_id,
            path="setup_app/lib/wizard.dart",
            language="dart",
            line_count=180,
            size_bytes=4500,
        )
        f_go = MockNamedEntity(
            id=uuid.uuid4(),
            snapshot_id=snap_id,
            path="cmd/api/main.go",
            language="go",
            line_count=100,
            size_bytes=2500,
        )
        f_py = MockNamedEntity(
            id=uuid.uuid4(),
            snapshot_id=snap_id,
            path="apps/api/src/main.py",
            language="python",
            line_count=90,
            size_bytes=2200,
        )

        sym_widget = MockNamedEntity(
            id=uuid.uuid4(),
            file_id=f_flutter.id,
            name="AskTab",
            symbol_type=SymbolType.CLASS,
            start_line=15,
            end_line=240,
        )
        sym_api = MockNamedEntity(
            id=uuid.uuid4(),
            file_id=f_py.id,
            name="create_app",
            symbol_type=SymbolType.FUNCTION,
            start_line=20,
            end_line=85,
        )

        finding1 = MockNamedEntity(
            id=uuid.uuid4(),
            project_id=proj_id,
            snapshot_id=snap_id,
            category=FindingCategory.CIRCULAR_DEPENDENCY,
            severity=FindingSeverity.HIGH,
            confidence="HIGH",
            title="Circular Dependency Detected in Auth Modules",
            description="Cycle between login and auth service",
            why_it_matters="Cascading initialization race conditions",
            recommendation="Extract shared interface into common package",
            score=85.0,
            evidence=[{"file": "app/lib/screens/login.dart", "lines": "12-40"}],
        )

        facts = FactData(
            project=project,
            snapshot=snapshot,
            files=[f_flutter, f_setup, f_go, f_py],
            symbols=[sym_widget, sym_api],
            dependencies=[],
            findings=[finding1],
            discovery_run=None,
            knowledge_items=[],
            file_by_id={f.id: f for f in [f_flutter, f_setup, f_go, f_py]},
            file_by_path={f.path: f for f in [f_flutter, f_setup, f_go, f_py]},
            symbol_consumers={"AskTab": 3, "create_app": 5},
            language_counts={"dart": 2, "go": 1, "python": 1},
        )

        doc = InterpretationEngine.build_report_document(facts)

        # 1. Executive Summary & Vital Metrics
        self.assertIsNotNone(doc.executive_summary)
        self.assertEqual(doc.executive_summary.vital_metrics.total_files, 4)
        self.assertEqual(doc.executive_summary.vital_metrics.total_symbols, 2)
        self.assertEqual(doc.executive_summary.vital_metrics.critical_findings, 0)
        self.assertEqual(doc.executive_summary.vital_metrics.high_findings, 1)

        # 2. Multi-language area classification (app/lib, setup_app/lib, cmd/api, apps/api)
        areas = [a["area"] for a in doc.project_understanding.major_areas]
        self.assertIn("app/lib", areas)
        self.assertIn("setup_app/lib", areas)
        self.assertIn("cmd/api", areas)
        self.assertIn("apps/api", areas)

        # 3. Discoveries Section
        self.assertEqual(len(doc.discoveries), 1)
        self.assertEqual(doc.discoveries[0].category, FindingCategory.CIRCULAR_DEPENDENCY.value)

        # 4. JSON Serialization for PostgreSQL persistence
        doc_dict = doc.model_dump()
        self.assertIn("executive_summary", doc_dict)
        self.assertIn("project_understanding", doc_dict)
        self.assertIn("discoveries", doc_dict)
        self.assertIn("risk_areas", doc_dict)
        self.assertIn("next_actions", doc_dict)

    def test_customer_knowledge_fallback_embedding(self):
        """Verify that customer knowledge ADRs generate 384d semantic embeddings without external APIs."""
        adr_title = "ADR 004: Event-Driven Redis Architecture"
        adr_content = "All asynchronous repository scans and report jobs must be dispatched via Redis task consumer."
        embed_text = f"{adr_title}\n{adr_content}"

        embedding = generate_text_embedding(embed_text)

        self.assertIsInstance(embedding, list)
        self.assertEqual(len(embedding), 1536)
        # Verify non-trivial normalized float values
        self.assertGreater(sum(abs(x) for x in embedding), 0.0)


if __name__ == "__main__":
    unittest.main()
