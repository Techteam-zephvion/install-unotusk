import pytest

from apps.api.src.config.settings import settings
from apps.api.src.services.llm.factory import get_llm_provider
from apps.api.src.services.llm.groq import GroqProvider


@pytest.mark.asyncio
async def test_groq_provider_offline_fallback(monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    provider = GroqProvider(api_key="")

    evidence = [
        {
            "type": "symbol",
            "file": "src/sessions.py",
            "symbol": "Session",
            "lines": "350-420",
            "relevance": 0.95,
            "snippet": "class Session: pass",
        }
    ]

    answer = await provider.generate_grounded_answer(
        question="How does Session work?",
        project_context="### [SYMBOL] src/sessions.py\nclass Session: pass",
        evidence_items=evidence,
        related_entities=["Session"],
    )

    assert answer.confidence == "HIGH"
    assert "Session" in answer.content
    assert "src/sessions.py" in answer.content
    assert len(answer.evidence) == 1
    assert answer.debug_signals["provider"] == "offline"


def test_llm_factory_routing(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    p1 = get_llm_provider()
    assert isinstance(p1, GroqProvider)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "claude")
    p2 = get_llm_provider()
    assert p2.__class__.__name__ == "ClaudeProvider"

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openrouter")
    p3 = get_llm_provider()
    assert p3.__class__.__name__ == "OpenRouterProvider"


@pytest.mark.asyncio
async def test_groq_to_openrouter_failover_on_rate_limit(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock, patch

    from apps.api.src.services.llm.base import GroundedAnswer

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "mock-openrouter-key")

    provider = GroqProvider(api_key="mock-groq-key")
    mock_groq_client = MagicMock()
    mock_groq_client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("429 Rate limit reached on Groq")
    )
    provider._client = mock_groq_client

    mock_openrouter_answer = GroundedAnswer(
        content="Answer generated via OpenRouter fallback.",
        evidence=[],
        related_entities=[],
        confidence="HIGH",
        debug_signals={"provider": "openrouter", "model": "openrouter/free"},
    )

    with patch(
        "apps.api.src.services.llm.openrouter.OpenRouterProvider.generate_grounded_answer",
        new=AsyncMock(return_value=mock_openrouter_answer),
    ):
        evidence = [{"type": "symbol", "file": "src/api.py", "symbol": "Api", "relevance": 0.9}]
        answer = await provider.generate_grounded_answer(
            question="What is Api?",
            project_context="### [SYMBOL] src/api.py\nclass Api: pass",
            evidence_items=evidence,
            related_entities=["Api"],
        )

        assert answer.content == "Answer generated via OpenRouter fallback."
        assert answer.debug_signals.get("failover_from") == "groq"
        assert "429" in answer.debug_signals.get("groq_error", "")


@pytest.mark.asyncio
async def test_openrouter_provider_offline_fallback(monkeypatch):
    from apps.api.src.services.llm.openrouter import OpenRouterProvider

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    provider = OpenRouterProvider(api_key="")

    evidence = [
        {
            "type": "symbol",
            "file": "src/sessions.py",
            "symbol": "Session",
            "lines": "350-420",
            "relevance": 0.95,
            "snippet": "class Session: pass",
        }
    ]

    answer = await provider.generate_grounded_answer(
        question="How does Session work?",
        project_context="### [SYMBOL] src/sessions.py\nclass Session: pass",
        evidence_items=evidence,
        related_entities=["Session"],
    )

    assert answer.confidence == "HIGH"
    assert "Session" in answer.content
    assert "src/sessions.py" in answer.content
    assert len(answer.evidence) == 1
    assert answer.debug_signals["provider"] == "offline"


@pytest.mark.asyncio
async def test_groq_report_synthesizer_with_mock():
    from unittest.mock import AsyncMock, MagicMock, patch

    from apps.api.src.schemas.report import (
        ExecutiveSummary,
        ProjectUnderstanding,
        ReportDocument,
        TestingAndDocs,
        VitalMetrics,
    )
    from apps.api.src.services.report_engine.synthesizer import GroqReportSynthesizer

    doc = ReportDocument(
        metadata={
            "project_name": "Test Project",
            "project_slug": "test-project",
            "snapshot_id": "123",
        },
        executive_summary=ExecutiveSummary(
            project_summary="Original deterministic summary",
            state_assessment="STABLE",
            vital_metrics=VitalMetrics(
                total_files=5, total_symbols=10, total_dependencies=4, total_findings=1
            ),
        ),
        project_understanding=ProjectUnderstanding(
            primary_languages={"Python": 5},
            major_areas=[{"path": "api", "files_count": 2}, {"path": "core", "files_count": 3}],
            key_symbols=[
                {"name": "Session", "file": "sessions.py"},
                {"name": "Request", "file": "models.py"},
            ],
            business_purpose_note="Inferred HTTP library",
        ),
        observed=[],
        discoveries=[],
        risk_areas=[],
        technical_debt=[],
        dependencies=[],
        testing_and_documentation=TestingAndDocs(
            testing_observed=[],
            testing_derived="Tests located",
            testing_recommended="Maintain coverage",
            testing_coverage_note="Adequate",
            docs_observed=[],
            docs_recommended="Maintain docs",
        ),
        next_actions=[],
        project_knowledge=[],
    )

    synthesizer = GroqReportSynthesizer(api_key="mock-groq-key")
    mock_choice = MagicMock()
    mock_choice.message.content = '{"executive_summary_text": "Enhanced Groq narrative on HTTP architecture.", "state_assessment": "HEALTHY", "business_purpose_note": "Production HTTP client library."}'
    mock_response = MagicMock(choices=[mock_choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch.object(synthesizer, "_client", mock_client):
        res = await synthesizer.synthesize(doc)
        assert (
            res.executive_summary.project_summary == "Enhanced Groq narrative on HTTP architecture."
        )
        assert res.executive_summary.state_assessment == "HEALTHY"
        assert res.project_understanding.business_purpose_note == "Production HTTP client library."
