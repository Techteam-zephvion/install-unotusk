import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.src.models.dependency import CodeDependency
from apps.api.src.models.enums import (
    DependencyType,
    FindingCategory,
    FindingSeverity,
    KnowledgeClass,
    SymbolType,
)
from apps.api.src.models.file import RepositoryFile
from apps.api.src.models.finding import Finding
from apps.api.src.models.project import Project
from apps.api.src.models.snapshot import RepositorySnapshot
from apps.api.src.models.symbol import CodeSymbol
from apps.api.src.services.report_engine.base import FactData
from apps.api.src.services.report_engine.interpretation_engine import InterpretationEngine
from apps.api.src.services.report_engine.synthesizer import ClaudeReportSynthesizer


@pytest.fixture
def sample_fact_data():
    project_id = uuid.uuid4()
    snapshot_id = uuid.uuid4()

    project = Project(id=project_id, name="Acme Service", slug="acme-service")
    snapshot = RepositorySnapshot(id=snapshot_id, commit_sha="abcdef123456")

    # Files
    f_auth = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/auth/service.py", language="python", line_count=120, size_bytes=2400)
    f_api = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/api/routes.py", language="python", line_count=80, size_bytes=1600)
    f_pay = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/core/payment_service.py", language="python", line_count=90, size_bytes=1800)
    f_a = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/a.py", language="python", line_count=40, size_bytes=800)
    f_b = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/b.py", language="python", line_count=40, size_bytes=800)
    f_c = RepositoryFile(id=uuid.uuid4(), snapshot_id=snapshot_id, path="src/c.py", language="python", line_count=40, size_bytes=800)

    files = [f_auth, f_api, f_pay, f_a, f_b, f_c]

    # Symbols
    sym_auth = CodeSymbol(id=uuid.uuid4(), file_id=f_auth.id, name="AuthService", qualified_name="AuthService", symbol_type=SymbolType.CLASS, start_line=5, end_line=50)
    sym_pay = CodeSymbol(id=uuid.uuid4(), file_id=f_pay.id, name="PaymentService", qualified_name="PaymentService", symbol_type=SymbolType.CLASS, start_line=5, end_line=60)
    symbols = [sym_auth, sym_pay]

    # Dependencies
    dep1 = CodeDependency(id=uuid.uuid4(), source_file_id=f_api.id, target_file_id=f_auth.id, dependency_type=DependencyType.IMPORT, line_number=1)
    dep2 = CodeDependency(id=uuid.uuid4(), source_file_id=f_pay.id, target_file_id=f_auth.id, dependency_type=DependencyType.IMPORT, line_number=2)
    dependencies = [dep1, dep2]

    # Findings
    f1 = Finding(
        id=uuid.uuid4(),
        project_id=project_id,
        title="High coupling around AuthService",
        category=FindingCategory.COUPLING,
        severity=FindingSeverity.HIGH,
        confidence="HIGH",
        description="AuthService has 17 downstream consumers.",
        why_it_matters="Changes may break downstream services.",
        recommendation="Decouple into smaller contracts.",
        evidence=[{"file": "src/auth/service.py", "symbol": "AuthService"}],
    )
    f2 = Finding(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Circular dependency detected",
        category=FindingCategory.ARCHITECTURE,
        severity=FindingSeverity.CRITICAL,
        confidence="HIGH",
        description="Cycle detected: a -> b -> c -> a.",
        why_it_matters="Prevents modular testing and imports.",
        recommendation="Break cycle using interfaces.",
        evidence=[{"file": "src/a.py"}, {"file": "src/b.py"}],
    )
    f3 = Finding(
        id=uuid.uuid4(),
        project_id=project_id,
        title="Core module lacks tests",
        category=FindingCategory.TEST_GAP,
        severity=FindingSeverity.MEDIUM,
        confidence="HIGH",
        description="payment_service.py has no corresponding test module.",
        why_it_matters="High regression risk.",
        recommendation="Add unit test suite.",
        evidence=[{"file": "src/core/payment_service.py"}],
    )
    findings = [f1, f2, f3]

    return FactData(
        project=project,
        snapshot=snapshot,
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        findings=findings,
        discovery_run=None,
        language_counts={"python": 6},
        total_lines=410,
        total_bytes=8200,
        file_by_id={f.id: f for f in files},
        file_by_path={f.path: f for f in files},
        file_consumers={"src/auth/service.py": {"src/api/routes.py", "src/core/payment_service.py"}},
        symbol_consumers={"AuthService": 17},
        external_packages={"fastapi", "sqlalchemy"},
        cycles=[["src/a.py", "src/b.py", "src/c.py", "src/a.py"]],
    )


def test_deterministic_interpretation_assembly(sample_fact_data):
    report_doc = InterpretationEngine.build_report_document(sample_fact_data)

    # Validate Executive Summary & Vital Metrics
    assert report_doc.executive_summary.vital_metrics.total_files == 6
    assert report_doc.executive_summary.vital_metrics.total_symbols == 2
    assert report_doc.executive_summary.vital_metrics.total_dependencies == 2
    assert report_doc.executive_summary.vital_metrics.total_discoveries == 3
    assert report_doc.executive_summary.vital_metrics.critical_findings == 1
    assert report_doc.executive_summary.vital_metrics.high_findings == 1
    assert "Risk" in report_doc.executive_summary.state_assessment

    # Validate Observed / Derived / Recommended Classifications
    for item in report_doc.executive_summary.top_things_to_know:
        assert item.claim_type in [KnowledgeClass.OBSERVED, KnowledgeClass.DERIVED]
        assert len(item.evidence) > 0

    # Validate Discoveries
    assert len(report_doc.discoveries) == 3
    assert report_doc.discoveries[0].severity == "CRITICAL"

    # Validate Risk Areas
    risk_names = [r.area for r in report_doc.risk_areas]
    assert any("Architecture" in name for name in risk_names)
    assert any("Coupling" in name for name in risk_names)

    # Check observed vs derived vs recommended in risk area
    coupling_area = next(r for r in report_doc.risk_areas if "Coupling" in r.area)
    assert len(coupling_area.observed) > 0
    assert coupling_area.observed[0].claim_type == KnowledgeClass.OBSERVED
    assert coupling_area.derived != ""
    assert coupling_area.recommended != ""

    # Validate Next Actions
    assert len(report_doc.next_actions) == 3
    assert report_doc.next_actions[0].priority in ["CRITICAL", "HIGH"]
    assert report_doc.next_actions[0].claim_type == KnowledgeClass.RECOMMENDED


@pytest.mark.asyncio
async def test_synthesizer_offline_fallback(sample_fact_data):
    deterministic_doc = InterpretationEngine.build_report_document(sample_fact_data)

    # When no API key is provided, synthesizer must fall back cleanly
    synthesizer = ClaudeReportSynthesizer(api_key="")
    final_doc = await synthesizer.synthesize(deterministic_doc)

    assert final_doc.executive_summary.project_summary == deterministic_doc.executive_summary.project_summary
    assert final_doc.executive_summary.vital_metrics.total_files == 6
    assert len(final_doc.discoveries) == 3


@pytest.mark.asyncio
async def test_synthesizer_malformed_ai_output_fallback(sample_fact_data):
    deterministic_doc = InterpretationEngine.build_report_document(sample_fact_data)

    synthesizer = ClaudeReportSynthesizer(api_key="mock-key")
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("Anthropic 500 API Error"))

    with patch.object(synthesizer, "_client", mock_client):
        final_doc = await synthesizer.synthesize(deterministic_doc)

        # Must fall back gracefully to deterministic document
        assert final_doc.executive_summary.vital_metrics.total_files == 6
        assert len(final_doc.discoveries) == 3
        assert len(final_doc.next_actions) == 3


@pytest.mark.asyncio
async def test_synthesizer_valid_ai_response(sample_fact_data):
    deterministic_doc = InterpretationEngine.build_report_document(sample_fact_data)

    synthesizer = ClaudeReportSynthesizer(api_key="mock-key")

    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text='{"project_summary": "Engineered Python backend with high coupling around AuthService and architectural circular imports.", "state_assessment": "CRITICAL_RISK", "business_purpose_note": "Repository evidence indicates an enterprise service."}')
    ]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch.object(synthesizer, "_client", mock_client):
        final_doc = await synthesizer.synthesize(deterministic_doc)

        # Verify synthesized fields updated while deterministic metrics and findings are strictly preserved
        assert "Engineered Python backend" in final_doc.executive_summary.project_summary
        assert final_doc.executive_summary.vital_metrics.total_files == 6
        assert len(final_doc.discoveries) == 3
        assert final_doc.discoveries[0].title == deterministic_doc.discoveries[0].title
