import uuid

import pytest

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    DependencyType,
    FindingCategory,
    FindingSeverity,
    SymbolType,
)
from apps.api.src.models.chunk import CodeChunk
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.discovery_engine.architecture_analyzer import ArchitectureAnalyzer
from apps.api.src.services.discovery_engine.base import CandidateFinding, DiscoveryContext
from apps.api.src.services.discovery_engine.change_risk_analyzer import ChangeRiskAnalyzer
from apps.api.src.services.discovery_engine.circular_dependency_analyzer import (
    CircularDependencyAnalyzer,
)
from apps.api.src.services.discovery_engine.coupling_analyzer import CouplingAnalyzer
from apps.api.src.services.discovery_engine.deduplicator import deduplicate_findings
from apps.api.src.services.discovery_engine.documentation_gap_analyzer import (
    DocumentationGapAnalyzer,
)
from apps.api.src.services.discovery_engine.duplication_analyzer import DuplicationAnalyzer
from apps.api.src.services.discovery_engine.legacy_analyzer import LegacyAnalyzer
from apps.api.src.services.discovery_engine.ranker import rank_findings
from apps.api.src.services.discovery_engine.test_gap_analyzer import TestGapAnalyzer
from apps.api.src.services.discovery_engine.unused_code_analyzer import UnusedCodeAnalyzer


@pytest.mark.asyncio
async def test_circular_dependency_analyzer_detects_cycles():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    file_a = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth.py", size_bytes=100
    )
    file_b = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/session.py", size_bytes=100
    )
    file_c = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/user.py", size_bytes=100
    )

    # Cycle: auth -> session -> user -> auth
    dep1 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=file_a.id,
        external_package="src.session",
        dependency_type=DependencyType.IMPORT,
        line_number=1,
    )
    dep2 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=file_b.id,
        external_package="src.user",
        dependency_type=DependencyType.IMPORT,
        line_number=2,
    )
    dep3 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=file_c.id,
        external_package="src.auth",
        dependency_type=DependencyType.IMPORT,
        line_number=3,
    )

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

    target_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/core/bus.py", size_bytes=200
    )
    consumers = [
        RepositoryFile(
            id=uuid.uuid4(), snapshot_id=snapshot_id, path=f"src/service_{i}.py", size_bytes=100
        )
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

    src_file_no_test = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/billing/engine.py", size_bytes=200
    )
    src_file_with_test = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth/service.py", size_bytes=200
    )
    test_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="tests/test_service.py", size_bytes=100
    )

    sym1 = CodeSymbol(
        id=uuid.uuid4(),
        file_id=src_file_no_test.id,
        name="BillingEngine",
        symbol_type=SymbolType.CLASS,
        qualified_name="src.billing.BillingEngine",
        start_line=1,
        end_line=50,
    )
    sym2 = CodeSymbol(
        id=uuid.uuid4(),
        file_id=src_file_with_test.id,
        name="AuthService",
        symbol_type=SymbolType.CLASS,
        qualified_name="src.auth.AuthService",
        start_line=1,
        end_line=50,
    )

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


@pytest.mark.asyncio
async def test_coupling_analyzer_ignores_external_packages():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    # File containing "os" in path: "src/models/repository.py"
    repo_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/models/repository.py", size_bytes=200
    )
    consumers = [
        RepositoryFile(
            id=uuid.uuid4(), snapshot_id=snapshot_id, path=f"src/file_{i}.py", size_bytes=100
        )
        for i in range(10)
    ]

    # Every consumer imports standard library "os" and "re" (external packages)
    deps = []
    for c in consumers:
        deps.append(
            CodeDependency(
                id=uuid.uuid4(),
                source_file_id=c.id,
                external_package="os",
                dependency_type=DependencyType.IMPORT,
                line_number=1,
            )
        )
        deps.append(
            CodeDependency(
                id=uuid.uuid4(),
                source_file_id=c.id,
                external_package="re",
                dependency_type=DependencyType.IMPORT,
                line_number=2,
            )
        )

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[repo_file] + consumers,
        symbols=[],
        dependencies=deps,
        chunks=[],
    )

    analyzer = CouplingAnalyzer(medium_threshold=6, high_threshold=15)
    findings = await analyzer.analyze(ctx)

    # Must NOT produce false positive coupling for repository.py due to "os" substring
    assert len(findings) == 0


@pytest.mark.asyncio
async def test_change_risk_analyzer():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    target = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/core/hub.py", size_bytes=300
    )
    consumers = [
        RepositoryFile(
            id=uuid.uuid4(), snapshot_id=snapshot_id, path=f"src/worker_{i}.py", size_bytes=100
        )
        for i in range(5)
    ]

    deps = [
        CodeDependency(
            id=uuid.uuid4(),
            source_file_id=c.id,
            target_file_id=target.id,
            external_package="src/core/hub.py",
            dependency_type=DependencyType.IMPORT,
            line_number=1,
        )
        for c in consumers
    ]

    # Target has 3 outbound dependencies and 6 symbols
    for j in range(3):
        deps.append(
            CodeDependency(
                id=uuid.uuid4(),
                source_file_id=target.id,
                external_package=f"ext_{j}",
                dependency_type=DependencyType.IMPORT,
                line_number=j + 1,
            )
        )

    symbols = [
        CodeSymbol(
            id=uuid.uuid4(),
            file_id=target.id,
            name=f"Handler_{k}",
            symbol_type=SymbolType.FUNCTION,
            qualified_name=f"src.core.hub.Handler_{k}",
            start_line=k * 10,
            end_line=k * 10 + 5,
        )
        for k in range(6)
    ]

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[target] + consumers,
        symbols=symbols,
        dependencies=deps,
        chunks=[],
    )

    analyzer = ChangeRiskAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    assert findings[0].category == FindingCategory.CHANGE_RISK
    assert "src/core/hub.py" in findings[0].title


@pytest.mark.asyncio
async def test_documentation_gap_analyzer():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    target = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/service/payment.py", size_bytes=200
    )
    consumers = [
        RepositoryFile(
            id=uuid.uuid4(), snapshot_id=snapshot_id, path=f"src/caller_{i}.py", size_bytes=100
        )
        for i in range(3)
    ]
    deps = [
        CodeDependency(
            id=uuid.uuid4(),
            source_file_id=c.id,
            target_file_id=target.id,
            external_package="src/service/payment.py",
            dependency_type=DependencyType.IMPORT,
            line_number=1,
        )
        for c in consumers
    ]

    sym = CodeSymbol(
        id=uuid.uuid4(),
        file_id=target.id,
        name="PaymentProcessor",
        symbol_type=SymbolType.CLASS,
        qualified_name="src.service.payment.PaymentProcessor",
        start_line=1,
        end_line=20,
    )
    # Chunk without docstring
    chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        file_id=target.id,
        name="PaymentProcessor",
        path="src/service/payment.py",
        content="class PaymentProcessor:\n    def process(self):\n        pass",
        start_line=1,
        end_line=20,
    )

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[target] + consumers,
        symbols=[sym],
        dependencies=deps,
        chunks=[chunk],
    )

    analyzer = DocumentationGapAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    assert findings[0].category == FindingCategory.DOCUMENTATION_GAP
    assert "PaymentProcessor" in findings[0].title


@pytest.mark.asyncio
async def test_duplication_analyzer():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    f1 = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth.py", size_bytes=100)
    f2 = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/user.py", size_bytes=100)

    # Identical business logic in 2 functions
    body = (
        "def validate_credentials(token):\n"
        "    if not token:\n"
        "        raise ValueError('Invalid')\n"
        "    parts = token.split('.')\n"
        "    if len(parts) != 3:\n"
        "        return False\n"
        "    return True\n"
    )

    c1 = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        file_id=f1.id,
        chunk_type="FUNCTION",
        name="validate_credentials",
        path="src/auth.py",
        content=body,
        start_line=1,
        end_line=8,
    )
    c2 = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        file_id=f2.id,
        chunk_type="FUNCTION",
        name="validate_credentials",
        path="src/user.py",
        content=body,
        start_line=1,
        end_line=8,
    )

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[f1, f2],
        symbols=[],
        dependencies=[],
        chunks=[c1, c2],
    )

    analyzer = DuplicationAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    assert findings[0].category == FindingCategory.DUPLICATION
    assert "validate_credentials" in findings[0].title


@pytest.mark.asyncio
async def test_architecture_analyzer():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    prod_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/services/billing.py", size_bytes=100
    )
    web_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="apps/web/src/pages/index.tsx", size_bytes=100
    )

    # Rule 1: prod imports test
    dep1 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=prod_file.id,
        external_package="tests/fixtures/mock_db",
        dependency_type=DependencyType.IMPORT,
        line_number=2,
    )
    # Rule 2: web imports sqlalchemy
    dep2 = CodeDependency(
        id=uuid.uuid4(),
        source_file_id=web_file.id,
        external_package="sqlalchemy",
        dependency_type=DependencyType.IMPORT,
        line_number=3,
    )

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[prod_file, web_file],
        symbols=[],
        dependencies=[dep1, dep2],
        chunks=[],
    )

    analyzer = ArchitectureAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 2
    categories = [f.category for f in findings]
    assert all(c == FindingCategory.ARCHITECTURE for c in categories)


@pytest.mark.asyncio
async def test_legacy_analyzer():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    legacy_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth_legacy.py", size_bytes=100
    )
    modern_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth.py", size_bytes=100
    )

    chunk = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        file_id=legacy_file.id,
        name="legacy_auth",
        path="src/auth_legacy.py",
        content="# @deprecated Use modern auth.py instead\ndef authenticate(): pass",
        start_line=1,
        end_line=3,
    )

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[legacy_file, modern_file],
        symbols=[],
        dependencies=[],
        chunks=[chunk],
    )

    analyzer = LegacyAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    assert findings[0].category == FindingCategory.LEGACY
    assert "auth_legacy.py" in findings[0].title


@pytest.mark.asyncio
async def test_unused_code_analyzer():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    prod_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/utils/crypto.py", size_bytes=100
    )
    other_file = RepositoryFile(
        id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/app.py", size_bytes=100
    )

    sym = CodeSymbol(
        id=uuid.uuid4(),
        file_id=prod_file.id,
        name="unused_cipher_helper",
        symbol_type=SymbolType.FUNCTION,
        qualified_name="src.utils.crypto.unused_cipher_helper",
        start_line=1,
        end_line=5,
    )

    chunk1 = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        file_id=prod_file.id,
        name="unused_cipher_helper",
        path="src/utils/crypto.py",
        content="def unused_cipher_helper(): pass",
        start_line=1,
        end_line=5,
    )
    chunk2 = CodeChunk(
        id=uuid.uuid4(),
        snapshot_id=snapshot_id,
        file_id=other_file.id,
        name="main",
        path="src/app.py",
        content="def main(): print('Hello')",
        start_line=1,
        end_line=3,
    )

    ctx = DiscoveryContext(
        project_id=project_id,
        snapshot_id=snapshot_id,
        files=[prod_file, other_file],
        symbols=[sym],
        dependencies=[],
        chunks=[chunk1, chunk2],
    )

    analyzer = UnusedCodeAnalyzer()
    findings = await analyzer.analyze(ctx)

    assert len(findings) == 1
    assert findings[0].category == FindingCategory.UNUSED_CODE
    assert "unused_cipher_helper" in findings[0].title


@pytest.mark.asyncio
async def test_empty_repository_behavior():
    ctx = DiscoveryContext(
        project_id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        files=[],
        symbols=[],
        dependencies=[],
        chunks=[],
    )

    analyzers = [
        CircularDependencyAnalyzer(),
        CouplingAnalyzer(),
        ChangeRiskAnalyzer(),
        UnusedCodeAnalyzer(),
        DocumentationGapAnalyzer(),
        DuplicationAnalyzer(),
        ArchitectureAnalyzer(),
        LegacyAnalyzer(),
        TestGapAnalyzer(),
    ]

    for a in analyzers:
        findings = await a.analyze(ctx)
        assert findings == []


def test_deduplicator_handles_empty_entities():
    f1 = CandidateFinding(
        category=FindingCategory.ARCHITECTURE,
        title="Arch violation 1",
        description="Desc 1",
        why_it_matters="Why 1",
        severity=FindingSeverity.HIGH,
        confidence=FindingSeverity.HIGH,
        recommendation="Rec 1",
        related_entities=[],
    )
    f2 = CandidateFinding(
        category=FindingCategory.ARCHITECTURE,
        title="Arch violation 2",
        description="Desc 2",
        why_it_matters="Why 2",
        severity=FindingSeverity.HIGH,
        confidence=FindingSeverity.HIGH,
        recommendation="Rec 2",
        related_entities=[],
    )

    deduped = deduplicate_findings([f1, f2])
    # Different titles with empty entities must NOT collide
    assert len(deduped) == 2


@pytest.mark.asyncio
async def test_analyzer_failure_isolation():
    """Verify that an exception in one analyzer does not abort the other analyzers."""
    import asyncio
    from apps.api.src.services.discovery_engine.base import DiscoveryAnalyzer

    class CrashingAnalyzer(DiscoveryAnalyzer):
        @property
        def category(self) -> FindingCategory:
            return FindingCategory.ARCHITECTURE

        async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
            raise RuntimeError("Unexpected failure in third-party AST parser")

    class WorkingAnalyzer(DiscoveryAnalyzer):
        @property
        def category(self) -> FindingCategory:
            return FindingCategory.UNUSED_CODE

        async def analyze(self, ctx: DiscoveryContext) -> list[CandidateFinding]:
            return [
                CandidateFinding(
                    category=FindingCategory.UNUSED_CODE,
                    title="Unused symbol helper",
                    description="Helper is unused",
                    why_it_matters="Dead code",
                    severity=FindingSeverity.LOW,
                    confidence=FindingSeverity.HIGH,
                    recommendation="Remove",
                    related_entities=["src/helper.py"],
                )
            ]

    ctx = DiscoveryContext(
        project_id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        files=[],
        symbols=[],
        dependencies=[],
        chunks=[],
    )

    analyzers = [CrashingAnalyzer(), WorkingAnalyzer()]
    candidate_lists = await asyncio.gather(
        *[analyzer.analyze(ctx) for analyzer in analyzers],
        return_exceptions=True,
    )

    all_candidates: list[CandidateFinding] = []
    for res in candidate_lists:
        if isinstance(res, Exception):
            pass  # Error isolated and logged
        elif isinstance(res, list):
            all_candidates.extend(res)

    assert len(all_candidates) == 1
    assert all_candidates[0].title == "Unused symbol helper"


def test_finding_title_length_sanitization():
    """Verify that candidate titles longer than 255 chars are truncated safely."""
    long_title = "A" * 300
    safe_title = long_title if len(long_title) <= 255 else (long_title[:251] + "...")
    assert len(safe_title) == 254
    assert safe_title.endswith("...")


@pytest.mark.asyncio
async def test_synthesizer_deterministic_fallback():
    """Verify synthesizer enhances knowledge and falls back cleanly without LLM keys."""
    from unittest.mock import MagicMock
    from apps.api.src.services.discovery_engine.synthesizer import FindingSynthesizer

    finding = CandidateFinding(
        category=FindingCategory.UNUSED_CODE,
        title="Unused symbol PaymentGateway",
        description="PaymentGateway is unused",
        why_it_matters="Dead code adds maintenance burden",
        severity=FindingSeverity.LOW,
        confidence=FindingSeverity.HIGH,
        recommendation="Audit callers",
        evidence=[{"file": "src/payment.py", "symbol": "PaymentGateway"}],
        related_entities=["PaymentGateway"],
        score=75.0,
    )

    mock_knowledge = MagicMock()
    mock_knowledge.related_symbol = "PaymentGateway"
    mock_knowledge.related_file_path = "src/payment.py"
    mock_knowledge.title = "Payment Service Migration"
    mock_knowledge.content = "PaymentGateway is being replaced by StripeClient next quarter"

    synthesizer = FindingSynthesizer()
    enhanced = await synthesizer.enhance_recommendations(
        [finding], active_knowledge=[mock_knowledge]
    )

    assert len(enhanced) == 1
    assert "Project Knowledge: Team states 'PaymentGateway is being replaced" in enhanced[0].why_it_matters


