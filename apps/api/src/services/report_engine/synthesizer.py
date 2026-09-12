import json
import logging

from apps.api.src.config.settings import settings
from apps.api.src.schemas.report import ReportDocument

logger = logging.getLogger("unotusk-report")


class ClaudeReportSynthesizer:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client for report synthesizer: {e}")

    async def synthesize(self, doc: ReportDocument) -> ReportDocument:
        """
        Enhances the executive summary narrative and descriptions using Claude 3.5 Sonnet.
        Guarantees deterministic fallback if Claude fails, times out, or returns invalid JSON.
        """
        if not self._client:
            logger.info("Anthropic client unavailable; using deterministic report document directly.")
            return doc

        try:
            # Build constrained facts payload for Claude
            facts_payload = {
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
                    {"title": obs.title, "statement": obs.statement}
                    for obs in doc.observed[:5]
                ],
            }

            system_instruction = (
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

            prompt = (
                f"Assembled Deterministic Facts:\n{json.dumps(facts_payload, indent=2)}\n\n"
                "Synthesize the executive summary fields adhering strictly to the above facts."
            )

            response = await self._client.messages.create(
                model=self.model,
                max_tokens=600,
                system=system_instruction,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text if response.content else ""
            cleaned = content.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned)

            # Validate required fields
            if isinstance(parsed, dict) and ("executive_summary_text" in parsed or "project_summary" in parsed):
                summary_text = parsed.get("executive_summary_text") or parsed.get("project_summary")
                doc.executive_summary.project_summary = str(summary_text).strip()
                if "state_assessment" in parsed and parsed["state_assessment"]:
                    doc.executive_summary.state_assessment = str(parsed["state_assessment"]).strip()
                if "business_purpose_note" in parsed and parsed["business_purpose_note"]:
                    doc.project_understanding.business_purpose_note = str(parsed["business_purpose_note"]).strip()
                logger.info("Successfully synthesized executive summary with Claude.")

        except Exception as exc:
            logger.warning(
                f"Claude synthesis failed or returned invalid response ({exc}); falling back to deterministic report.",
                exc_info=False,
            )

        return doc
