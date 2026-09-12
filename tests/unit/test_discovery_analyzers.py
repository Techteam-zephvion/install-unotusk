import uuid

import pytest

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    DependencyType,
    FindingCategory,
    FindingSeverity,
    SymbolType,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.discovery_engine.base import CandidateFinding, DiscoveryContext
from apps.api.src.services.discovery_engine.circular_dependency_analyzer import (
    CircularDependencyAnalyzer,
)
from apps.api.src.services.discovery_engine.coupling_analyzer import CouplingAnalyzer
from apps.api.src.services.discovery_engine.deduplicator import deduplicate_findings
from apps.api.src.services.discovery_engine.ranker import rank_findings
from apps.api.src.services.discovery_engine.test_gap_analyzer import TestGapAnalyzer


@pytest.mark.asyncio
async def test_circular_dependency_analyzer_detects_cycles():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    file_a = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth.py", size_bytes=100)
    file_b = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/session.py", size_bytes=100)
    file_c = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/user.py", size_bytes=100)

    # Cycle: auth -> session -> user -> auth
    dep1 = CodeDependency(id=uuid.uuid4(), source_file_id=file_a.id, external_package="src.session", dependency_type=DependencyType.IMPORT, line_number=1)
    dep2 = CodeDependency(id=uuid.uuid4(), source_file_id=file_b.id, external_package="src.user", dependency_type=DependencyType.IMPORT, line_number=2)
    dep3 = CodeDependency(id=uuid.uuid4(), source_file_id=file_c.id, external_package="src.auth", dependency_type=DependencyType.IMPORT, line_number=3)

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[file_a, file_b, file_c],
        symbols=[],
        dependencies=[dep1, dep2, dep3],
        chunks=[],
    )

    analyzer = CircularDependencyAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.category == FindingCategory.CIRCULAR_DEPENDENCY
    assert f.severity == FindingSeverity.HIGH  # 3 files
    assert len(f.evidence) == 3
    assert set(f.related_entities) == {"src/auth.py", "src/session.py", "src/user.py"}


@pytest.mark.asyncio
async def test_coupling_analyzer_identifies_central_components():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    target_file = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/core/bus.py", size_bytes=200)
    consumers = [
        RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path=f"src/service_{i}.py", size_bytes=100)
        for i in range(8)
    ]

    deps = [
        CodeDependency(
            id=uuid.uuid4(),
            source_file_id=c.id,
            external_package="src/core/bus.py",
            dependency_type=DependencyType.IMPORT,
            line_number=1,
        )
        for c in consumers
    ]

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[target_file] + consumers,
        symbols=[],
        dependencies=deps,
        chunks=[],
    )

    analyzer = CouplingAnalyzer(medium_threshold=6, high_threshold=15)
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    f = findings[0]
    assert f.category == FindingCategory.COUPLING
    assert f.severity == FindingSeverity.MEDIUM
    assert "8 consumers" in f.title
    assert len(f.related_entities) >= 5


@pytest.mark.asyncio
async def test_test_gap_analyzer():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    src_file_no_test = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/billing/engine.py", size_bytes=200)
    src_file_with_test = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth/service.py", size_bytes=200)
    test_file = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="tests/test_service.py", size_bytes=100)

    sym1 = CodeSymbol(id=uuid.uuid4(), file_id=src_file_no_test.id, name="BillingEngine", symbol_type=SymbolType.CLASS, qualified_name="src.billing.BillingEngine", start_line=1, end_line=50)
    sym2 = CodeSymbol(id=uuid.uuid4(), file_id=src_file_with_test.id, name="AuthService", symbol_type=SymbolType.CLASS, qualified_name="src.auth.AuthService", start_line=1, end_line=50)

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[src_file_no_test, src_file_with_test, test_file],
        symbols=[sym1, sym2],
        dependencies=[],
        chunks=[],
    )

    analyzer = TestGapAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    assert findings[0].category == FindingCategory.TEST_GAP
    assert "billing/engine.py" in findings[0].title


def test_deduplicator_and_ranker():
    f1 = CandidateFinding(
        category=FindingCategory.CIRCULAR_DEPENDENCY,
        title="Cycle A",
        description="Cycle",
        why_it_matters="Matters",
        severity=FindingSeverity.HIGH,
        confidence=FindingSeverity.HIGH,
        recommendation="Fix it",
        related_entities=["src/a.py", "src/b.py"],
    )
    # Duplicate with different entity order
    f2 = CandidateFinding(
        category=FindingCategory.CIRCULAR_DEPENDENCY,
        title="Cycle B",
        description="Cycle",
        why_it_matters="Matters",
        severity=FindingSeverity.MEDIUM,
        confidence=FindingSeverity.HIGH,
        recommendation="Fix it",
        related_entities=["src/b.py", "src/a.py"],
    )
    f3 = CandidateFinding(
        category=FindingCategory.UNUSED_CODE,
        title="Unused X",
        description="Unused",
        why_it_matters="Matters",
        severity=FindingSeverity.LOW,
        confidence=FindingSeverity.MEDIUM,
        recommendation="Fix it",
        related_entities=["src/c.py"],
    )

    deduped = deduplicate_findings([f1, f2, f3])
    assert len(deduped) == 2

    ranked = rank_findings(deduped)
    # Circular dependency (HIGH severity) should rank above Unused code (LOW)
    assert ranked[0].category == FindingCategory.CIRCULAR_DEPENDENCY
    assert ranked[1].category == FindingCategory.UNUSED_CODE
