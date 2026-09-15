import json
import logging

from apps.api.src.config.settings import settings
from apps.api.src.schemas.report import ReportDocument

logger = logging.getLogger("unotusk-report")


class ReportSynthesizer:
    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self.provider = (provider or settings.LLM_PROVIDER or "offline").lower()
        self.groq_api_key = api_key if self.provider == "groq" else settings.GROQ_API_KEY
        self.groq_model = model if self.provider == "groq" else settings.GROQ_MODEL
        self.anthropic_api_key = (
            api_key if self.provider == "claude" else settings.ANTHROPIC_API_KEY
        )
        self.anthropic_model = model if self.provider == "claude" else settings.ANTHROPIC_MODEL

        self._groq_client = None
        self._anthropic_client = None
        self._client = None

        if self.provider == "groq" and self.groq_api_key:
            try:
                import groq

                self._groq_client = groq.AsyncGroq(api_key=self.groq_api_key)
                self._client = self._groq_client
            except Exception as e:
                logger.warning(f"Could not initialize Groq client for report synthesizer: {e}")

        elif self.provider == "claude" and self.anthropic_api_key:
            try:
                import anthropic

                self._anthropic_client = anthropic.AsyncAnthropic(api_key=self.anthropic_api_key)
                self._client = self._anthropic_client
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client for report synthesizer: {e}")

    async def synthesize(self, doc: ReportDocument) -> ReportDocument:
        """
        Enhances executive summary narrative and descriptions using configured LLM (Groq or Claude).
        Guarantees deterministic fallback if LLM fails, times out, or returns invalid JSON.
        """
        if self.provider == "groq" and self._groq_client:
            return await self._synthesize_with_groq(doc)
        elif self.provider == "claude" and (
            self._anthropic_client or (self._client and hasattr(self._client, "messages"))
        ):
            return await self._synthesize_with_claude(doc)

        logger.info("Remote LLM client unavailable; using deterministic report document directly.")
        return doc

    def _build_facts_payload(self, doc: ReportDocument) -> dict:
        return {
            "project_name": doc.metadata.get("project_name"),
            "vital_metrics": doc.executive_summary.vital_metrics.model_dump(),
            "major_areas": doc.project_understanding.major_areas,
            "key_symbols": doc.project_understanding.key_symbols[:5],
            "top_discoveries": [
                {
                    "title": d.title,
                    "category": d.category,
                    "severity": d.severity,
                    "what_we_found": d.what_we_found,
                    "why_it_matters": d.why_it_matters,
                }
                for d in doc.discoveries[:4]
            ],
            "observed_facts": [
                {"title": obs.title, "statement": obs.statement} for obs in doc.observed[:5]
            ],
        }

    def _get_system_instruction(self) -> str:
        return (
            "You are Unotusk Project Intelligence Executive Briefing Synthesizer.\n"
            "You are reviewing deterministic structural and architectural facts extracted from a real codebase.\n"
            "STRICT RULES:\n"
            "1. DO NOT invent any file paths, symbol names, external tools, or numbers not present in the supplied facts.\n"
            "2. DO NOT make ungrounded assertions about business purpose beyond what the facts establish.\n"
            "3. If evidence is insufficient to determine purpose or test coverage, state: 'Insufficient evidence.'\n"
            "4. Keep the tone professional, objective, concise, and focused on technical trade-offs.\n"
            "5. Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "executive_summary_text": "2-3 concise sentences summarizing what this codebase is and its primary structural state",\n'
            '  "state_assessment": "Short status sentence regarding architectural risk",\n'
            '  "business_purpose_note": "1-2 sentences stating what repository structure shows and acknowledging limits of inference"\n'
            "}"
        )

    async def _synthesize_with_groq(self, doc: ReportDocument) -> ReportDocument:
        try:
            facts_payload = self._build_facts_payload(doc)
            prompt = (
                f"Assembled Deterministic Facts:\n{json.dumps(facts_payload, indent=2)}\n\n"
                "Synthesize the executive summary fields adhering strictly to the above facts."
            )

            client = self._client or self._groq_client
            response = await client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": self._get_system_instruction()},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content if response.choices else ""
            parsed = json.loads(content.strip())
            self._apply_parsed_synthesis(doc, parsed)
            logger.info("Successfully synthesized executive summary with Groq.")

        except Exception as exc:
            logger.warning(
                f"Groq report synthesis failed ({exc}); falling back to deterministic report.",
                exc_info=False,
            )

        return doc

    async def _synthesize_with_claude(self, doc: ReportDocument) -> ReportDocument:
        try:
            facts_payload = self._build_facts_payload(doc)
            prompt = (
                f"Assembled Deterministic Facts:\n{json.dumps(facts_payload, indent=2)}\n\n"
                "Synthesize the executive summary fields adhering strictly to the above facts."
            )

            client = self._client or self._anthropic_client
            response = await client.messages.create(
                model=self.anthropic_model,
                max_tokens=600,
                system=self._get_system_instruction(),
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text if response.content else ""
            cleaned = content.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned)
            self._apply_parsed_synthesis(doc, parsed)
            logger.info("Successfully synthesized executive summary with Claude.")

        except Exception as exc:
            logger.warning(
                f"Claude report synthesis failed ({exc}); falling back to deterministic report.",
                exc_info=False,
            )

        return doc

    def _apply_parsed_synthesis(self, doc: ReportDocument, parsed: dict) -> None:
        if isinstance(parsed, dict) and (
            "executive_summary_text" in parsed or "project_summary" in parsed
        ):
            summary_text = parsed.get("executive_summary_text") or parsed.get("project_summary")
            if summary_text:
                doc.executive_summary.project_summary = str(summary_text).strip()
            if "state_assessment" in parsed and parsed["state_assessment"]:
                doc.executive_summary.state_assessment = str(parsed["state_assessment"]).strip()
            if "business_purpose_note" in parsed and parsed["business_purpose_note"]:
                doc.project_understanding.business_purpose_note = str(
                    parsed["business_purpose_note"]
                ).strip()


class ClaudeReportSynthesizer(ReportSynthesizer):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(provider="claude", api_key=api_key, model=model)


class GroqReportSynthesizer(ReportSynthesizer):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        super().__init__(provider="groq", api_key=api_key, model=model)
