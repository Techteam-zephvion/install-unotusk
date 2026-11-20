import asyncio
import importlib.machinery
import sys
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

from apps.api.src.models.enums import (
    FindingCategory,
    FindingSeverity,
)
from apps.api.src.services.discovery_engine.base import (
    DiscoveryContext,
)
from apps.api.src.services.discovery_engine.circular_dependency_analyzer import (
    CircularDependencyAnalyzer,
)
from apps.api.src.services.discovery_engine.coupling_analyzer import CouplingAnalyzer
from apps.api.src.services.discovery_engine.security_analyzer import SecurityAnalyzer


class MockFile:
    def __init__(self, file_id: uuid.UUID, path: str):
        self.id = file_id
        self.path = path


class MockDependency:
    def __init__(
        self,
        dep_id: uuid.UUID,
        source_file_id: uuid.UUID,
        external_package: str,
        line_number: int = 1,
        target_file_id: uuid.UUID | None = None,
    ):
        self.id = dep_id
        self.source_file_id = source_file_id
        self.external_package = external_package
        self.line_number = line_number
        self.target_file_id = target_file_id


class MockChunk:
    def __init__(self, name: str, path: str, content: str, start_line: int = 1):
        self.name = name
        self.path = path
        self.content = content
        self.start_line = start_line


class TestMultiLangDiscoveryAnalyzers(unittest.TestCase):
    def test_dart_package_and_relative_circular_dependency(self):
        """Verify that CircularDependencyAnalyzer resolves package: and relative imports in Flutter/Dart."""
        snap_id = uuid.uuid4()
        f1_id = uuid.uuid4()
        f2_id = uuid.uuid4()
        f3_id = uuid.uuid4()

        file1 = MockFile(f1_id, "lib/screens/login.dart")
        file2 = MockFile(f2_id, "lib/services/auth_service.dart")
        file3 = MockFile(f3_id, "lib/models/session.dart")

        # Cycle: login -> auth_service -> session -> login
        dep1 = MockDependency(uuid.uuid4(), f1_id, "package:my_app/services/auth_service.dart", 2)
        dep2 = MockDependency(uuid.uuid4(), f2_id, "../models/session.dart", 5)
        dep3 = MockDependency(uuid.uuid4(), f3_id, "package:my_app/screens/login.dart", 1)

        ctx = DiscoveryContext(
            project_id=uuid.uuid4(),
            snapshot_id=snap_id,
            files=[file1, file2, file3],
            symbols=[],
            dependencies=[dep1, dep2, dep3],
            chunks=[],
        )

        analyzer = CircularDependencyAnalyzer()
        findings = asyncio.run(analyzer.analyze(ctx))

        self.assertEqual(len(findings), 1)
        finding = findings[0]
        self.assertEqual(finding.category, FindingCategory.CIRCULAR_DEPENDENCY)
        self.assertEqual(finding.severity, FindingSeverity.HIGH)
        self.assertEqual(len(finding.related_entities), 3)

    def test_coupling_analyzer_multilang_consumers(self):
        """Verify that CouplingAnalyzer identifies high fan-in hubs across Go/Rust files."""
        hub_id = uuid.uuid4()
        hub_file = MockFile(hub_id, "pkg/logger/logger.go")

        consumer_files = []
        deps = []
        for i in range(8):
            c_id = uuid.uuid4()
            c_file = MockFile(c_id, f"cmd/service_{i}/main.go")
            consumer_files.append(c_file)
            deps.append(MockDependency(uuid.uuid4(), c_id, "pkg.logger", 10))

        ctx = DiscoveryContext(
            project_id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            files=[hub_file] + consumer_files,
            symbols=[],
            dependencies=deps,
            chunks=[],
        )

        analyzer = CouplingAnalyzer(medium_threshold=6)
        findings = asyncio.run(analyzer.analyze(ctx))

        self.assertGreaterEqual(len(findings), 1)
        coupling_f = findings[0]
        self.assertEqual(coupling_f.category, FindingCategory.COUPLING)
        self.assertIn("pkg/logger/logger.go", coupling_f.title)
        self.assertEqual(coupling_f.metadata["consumer_count"], 8)

    def test_security_analyzer_catches_api_keys(self):
        """Verify that SecurityAnalyzer detects exposed API keys in code chunks."""
        chunk = MockChunk(
            name="config_chunk",
            path="lib/config.dart",
            content='const apiKey = "sk-123456789012345678901234567890123456789012345678";',
        )

        ctx = DiscoveryContext(
            project_id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            files=[],
            symbols=[],
            dependencies=[],
            chunks=[chunk],
        )

        analyzer = SecurityAnalyzer()
        findings = asyncio.run(analyzer.analyze(ctx))

        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].category, FindingCategory.SECURITY_RISK)
        self.assertEqual(findings[0].severity, FindingSeverity.CRITICAL)


if __name__ == "__main__":
    unittest.main()
