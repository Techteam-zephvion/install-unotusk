import json
import sys
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# Provide mock for asyncpg if not installed in host environment
if "asyncpg" not in sys.modules:
    sys.modules["asyncpg"] = MagicMock()

from apps.api.src.config.settings import settings
from apps.api.src.models.enums import ReportStatus
from apps.api.src.models.report import ProjectIntelligenceReport
from apps.api.src.schemas.report import (
    ExecutiveSummary,
    ProjectUnderstanding,
    ReportDocument,
    TestingAndDocs,
    VitalMetrics,
)
from apps.api.src.services.llm.claude import ClaudeProvider
from apps.api.src.services.llm.factory import get_llm_provider
from apps.api.src.services.llm.factory import (
    get_report_synthesizer as factory_get_report_synthesizer,
)
from apps.api.src.services.llm.groq import GroqProvider
from apps.api.src.services.report_engine.engine import ProjectReportEngine
from apps.api.src.services.report_engine.synthesizer import (
    AnthropicReportSynthesizer,
    ClaudeReportSynthesizer,
    GroqReportSynthesizer,
    ReportSynthesizer,
    get_report_synthesizer,
)


def create_sample_report_document() -> ReportDocument:
    return ReportDocument(
        metadata={
            "project_name": "Test Platform",
            "project_slug": "test-platform",
            "snapshot_id": str(uuid.uuid4()),
        },
        executive_summary=ExecutiveSummary(
            project_summary="Original deterministic summary statement.",
            state_assessment="STABLE",
            vital_metrics=VitalMetrics(
                total_files=8,
                total_symbols=15,
                total_dependencies=6,
                total_findings=2,
            ),
        ),
        project_understanding=ProjectUnderstanding(
            primary_languages={"Python": 8},
            major_areas=[{"path": "src/api", "files_count": 4}, {"path": "src/core", "files_count": 4}],
            key_symbols=[
                {"name": "AuthService", "file": "src/auth.py"},
                {"name": "PaymentService", "file": "src/pay.py"},
            ],
            business_purpose_note="Inferred enterprise web backend service",
        ),
        observed=[],
        discoveries=[],
        risk_areas=[],
        technical_debt=[],
        dependencies=[],
        testing_and_documentation=TestingAndDocs(
            testing_observed=[],
            testing_derived="Test suite detected",
            testing_recommended="Increase unit coverage",
            testing_coverage_note="Adequate",
            docs_observed=[],
            docs_recommended="Document API routes",
        ),
        next_actions=[],
        project_knowledge=[],
    )


class TestReportSynthesizerProviderSelection(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._orig_provider = settings.LLM_PROVIDER
        self._orig_groq_key = settings.GROQ_API_KEY
        self._orig_anthropic_key = settings.ANTHROPIC_API_KEY

    def tearDown(self):
        settings.LLM_PROVIDER = self._orig_provider
        settings.GROQ_API_KEY = self._orig_groq_key
        settings.ANTHROPIC_API_KEY = self._orig_anthropic_key

    def test_configured_groq_uses_groq(self):
        """Verify that when Groq is configured, GroqReportSynthesizer is instantiated with groq provider."""
        settings.LLM_PROVIDER = "groq"
        synth = get_report_synthesizer()

        self.assertIsInstance(synth, GroqReportSynthesizer)
        self.assertEqual(synth.provider, "groq")
        self.assertNotIsInstance(synth, ClaudeReportSynthesizer)
        self.assertNotIsInstance(synth, AnthropicReportSynthesizer)

    def test_configured_claude_uses_claude(self):
        """Verify that when Claude is configured, ClaudeReportSynthesizer is instantiated with claude provider."""
        settings.LLM_PROVIDER = "claude"
        synth = get_report_synthesizer()

        self.assertIsInstance(synth, ClaudeReportSynthesizer)
        self.assertEqual(synth.provider, "claude")
        self.assertNotIsInstance(synth, GroqReportSynthesizer)

    def test_configured_anthropic_uses_anthropic(self):
        """Verify that when Anthropic is configured, AnthropicReportSynthesizer is instantiated with anthropic provider."""
        settings.LLM_PROVIDER = "anthropic"
        synth = get_report_synthesizer()

        self.assertIsInstance(synth, AnthropicReportSynthesizer)
        self.assertEqual(synth.provider, "anthropic")
        self.assertNotIsInstance(synth, GroqReportSynthesizer)

    def test_claude_not_selected_when_another_provider_configured(self):
        """Verify that Claude is never selected when Groq or offline is configured."""
        settings.LLM_PROVIDER = "groq"
        groq_synth = get_report_synthesizer()
        self.assertNotIsInstance(groq_synth, ClaudeReportSynthesizer)
        self.assertNotEqual(groq_synth.provider, "claude")

        settings.LLM_PROVIDER = "offline"
        offline_synth = get_report_synthesizer()
        self.assertNotIsInstance(offline_synth, ClaudeReportSynthesizer)
        self.assertNotIsInstance(offline_synth, AnthropicReportSynthesizer)
        self.assertEqual(offline_synth.provider, "offline")

    def test_configured_offline_uses_deterministic_fallback(self):
        """Verify that when offline is configured, ReportSynthesizer returns deterministic report without API calls."""
        settings.LLM_PROVIDER = "offline"
        synth = get_report_synthesizer()

        self.assertEqual(synth.provider, "offline")
        self.assertIsNone(synth._client)
        self.assertIsNone(synth._groq_client)
        self.assertIsNone(synth._anthropic_client)

    def test_changing_configuration_changes_provider_dynamically(self):
        """Verify changing settings.LLM_PROVIDER immediately changes the synthesizer at runtime."""
        # 1. Switch to groq
        settings.LLM_PROVIDER = "groq"
        s1 = get_report_synthesizer()
        self.assertEqual(s1.provider, "groq")
        self.assertIsInstance(s1, GroqReportSynthesizer)

        # 2. Switch to claude
        settings.LLM_PROVIDER = "claude"
        s2 = get_report_synthesizer()
        self.assertEqual(s2.provider, "claude")
        self.assertIsInstance(s2, ClaudeReportSynthesizer)

        # 3. Switch to anthropic
        settings.LLM_PROVIDER = "anthropic"
        s3 = get_report_synthesizer()
        self.assertEqual(s3.provider, "anthropic")
        self.assertIsInstance(s3, AnthropicReportSynthesizer)

        # 4. Switch to offline
        settings.LLM_PROVIDER = "offline"
        s4 = get_report_synthesizer()
        self.assertEqual(s4.provider, "offline")

    def test_unsupported_provider_fails_cleanly(self):
        """Verify that unsupported providers fail cleanly with ValueError and do not silently fall back to Claude."""
        for invalid_provider in ["openai", "gemini", "llama_cpp", "custom_unknown"]:
            settings.LLM_PROVIDER = invalid_provider
            with self.assertRaises(ValueError) as ctx:
                get_report_synthesizer()
            self.assertIn("Unsupported LLM provider", str(ctx.exception))
            self.assertIn(invalid_provider, str(ctx.exception))

            # Direct class instantiation with invalid provider also fails
            with self.assertRaises(ValueError):
                ReportSynthesizer(provider=invalid_provider)

    def test_llm_factory_integration(self):
        """Verify factory.py functions respect provider settings and fail cleanly on invalid ones."""
        # Test factory_get_report_synthesizer
        settings.LLM_PROVIDER = "groq"
        self.assertEqual(factory_get_report_synthesizer().provider, "groq")

        settings.LLM_PROVIDER = "anthropic"
        self.assertEqual(factory_get_report_synthesizer().provider, "anthropic")

        settings.LLM_PROVIDER = "invalid_foo"
        with self.assertRaises(ValueError):
            factory_get_report_synthesizer()

        # Test get_llm_provider
        settings.LLM_PROVIDER = "groq"
        self.assertIsInstance(get_llm_provider(), GroqProvider)

        settings.LLM_PROVIDER = "anthropic"
        self.assertIsInstance(get_llm_provider(), ClaudeProvider)

        settings.LLM_PROVIDER = "invalid_bar"
        with self.assertRaises(ValueError):
            get_llm_provider()

    async def test_groq_synthesizer_synthesis_flow(self):
        """Verify that Groq synthesizer calls Groq completions API and updates report fields."""
        doc = create_sample_report_document()
        synth = GroqReportSynthesizer(api_key="mock-groq-key")

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps({
            "executive_summary_text": "Enhanced Groq technical narrative of python services.",
            "state_assessment": "LOW_ARCHITECTURAL_RISK",
            "business_purpose_note": "Production payment processing engine.",
        })
        mock_response = MagicMock(choices=[mock_choice])

        mock_client = MagicMock()
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        synth._client = mock_client
        enhanced = await synth.synthesize(doc)

        self.assertEqual(enhanced.executive_summary.project_summary, "Enhanced Groq technical narrative of python services.")
        self.assertEqual(enhanced.executive_summary.state_assessment, "LOW_ARCHITECTURAL_RISK")
        self.assertEqual(enhanced.project_understanding.business_purpose_note, "Production payment processing engine.")
        mock_client.chat.completions.create.assert_awaited_once()

    async def test_anthropic_synthesizer_synthesis_flow(self):
        """Verify that Anthropic synthesizer calls Anthropic messages API and updates report fields."""
        doc = create_sample_report_document()
        synth = AnthropicReportSynthesizer(api_key="mock-anthropic-key")

        mock_content = MagicMock(
            text=json.dumps({
                "executive_summary_text": "Enhanced Anthropic Claude technical briefing.",
                "state_assessment": "MODERATE_COUPLING",
                "business_purpose_note": "Multi-tier microservices architecture.",
            })
        )
        mock_response = MagicMock(content=[mock_content])

        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        synth._client = mock_client
        enhanced = await synth.synthesize(doc)

        self.assertEqual(enhanced.executive_summary.project_summary, "Enhanced Anthropic Claude technical briefing.")
        self.assertEqual(enhanced.executive_summary.state_assessment, "MODERATE_COUPLING")
        self.assertEqual(enhanced.project_understanding.business_purpose_note, "Multi-tier microservices architecture.")
        mock_client.messages.create.assert_awaited_once()

    async def test_report_engine_unsupported_provider_marks_report_failed(self):
        """Verify that ProjectReportEngine records ReportStatus.FAILED when an unsupported provider is configured."""
        settings.LLM_PROVIDER = "unsupported_cloud_provider"

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.add = MagicMock()

        # Mock scalar_one for report query
        report = ProjectIntelligenceReport(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            status=ReportStatus.GENERATING,
            report_version="1.0.0",
            summary="",
            report_data={},
        )
        mock_res = MagicMock()
        mock_res.scalar_one = MagicMock(return_value=report)
        mock_session.execute.return_value = mock_res

        with patch("apps.api.src.services.report_engine.fact_builder.FactBuilder.build_facts", new_callable=AsyncMock) as mock_facts:
            with patch("apps.api.src.services.report_engine.interpretation_engine.InterpretationEngine.build_report_document") as mock_doc:
                mock_facts.return_value = MagicMock(discovery_run=None)
                mock_doc.return_value = create_sample_report_document()

                with self.assertRaises(ValueError) as ctx:
                    await ProjectReportEngine.generate_report(
                        project_id=report.project_id,
                        snapshot_id=report.snapshot_id,
                        report_id=report.id,
                        session=mock_session,
                    )

                self.assertIn("Unsupported LLM provider", str(ctx.exception))
                self.assertEqual(report.status, ReportStatus.FAILED)
                self.assertIn("Unsupported LLM provider", report.error_message)
                mock_session.rollback.assert_awaited()

    async def test_report_engine_injects_custom_synthesizer(self):
        """Verify that ProjectReportEngine respects an explicitly injected synthesizer."""
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.add = MagicMock()

        report = ProjectIntelligenceReport(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            status=ReportStatus.GENERATING,
            report_version="1.0.0",
            summary="",
            report_data={},
        )
        mock_res = MagicMock()
        mock_res.scalar_one = MagicMock(return_value=report)
        mock_session.execute.return_value = mock_res

        mock_synthesizer = MagicMock(spec=ReportSynthesizer)
        synthesized_doc = create_sample_report_document()
        synthesized_doc.executive_summary.project_summary = "Injected custom synthesizer output."
        mock_synthesizer.synthesize = AsyncMock(return_value=synthesized_doc)

        with patch("apps.api.src.services.report_engine.fact_builder.FactBuilder.build_facts", new_callable=AsyncMock) as mock_facts:
            with patch("apps.api.src.services.report_engine.interpretation_engine.InterpretationEngine.build_report_document") as mock_doc:
                mock_facts.return_value = MagicMock(discovery_run=None)
                mock_doc.return_value = create_sample_report_document()

                res = await ProjectReportEngine.generate_report(
                    project_id=report.project_id,
                    snapshot_id=report.snapshot_id,
                    report_id=report.id,
                    session=mock_session,
                    synthesizer=mock_synthesizer,
                )

                mock_synthesizer.synthesize.assert_awaited_once()
                self.assertEqual(res.status, ReportStatus.COMPLETED)
                self.assertEqual(res.summary, "Injected custom synthesizer output.")


if __name__ == "__main__":
    unittest.main()
