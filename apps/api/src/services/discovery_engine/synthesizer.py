import logging

from apps.api.src.config.settings import settings
from apps.api.src.services.discovery_engine.base import CandidateFinding

logger = logging.getLogger("unotusk-discovery")


class FindingSynthesizer:
    def __init__(self) -> None:
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client for synthesizer: {e}")

    async def enhance_recommendations(
        self,
        findings: list[CandidateFinding],
    ) -> list[CandidateFinding]:
        """Optionally uses Claude to polish recommendations for top-priority findings."""
        if not self._client or not findings:
            return findings

        # Enhance only top 3 findings to stay efficient and responsive
        top_findings = [f for f in findings[:3] if f.score >= 60.0]

        for finding in top_findings:
            try:
                prompt = (
                    f"You are Unotusk Discovery Synthesizer.\n"
                    f"A deterministic static analysis found the following issue in a connected codebase.\n\n"
                    f"Category: {finding.category.value}\n"
                    f"Title: {finding.title}\n"
                    f"Description: {finding.description}\n"
                    f"Evidence: {finding.evidence[:3]}\n\n"
                    f"Task:\n"
                    f"1. Explain in 2 concise sentences why this matters to a tech lead or developer.\n"
                    f"2. Provide 1 actionable recommendation on how to refactor or resolve it.\n"
                    f"Do NOT invent files or symbols not mentioned in the evidence.\n"
                    f"Format:\n"
                    f"WHY: <why it matters>\n"
                    f"REC: <recommendation>"
                )

                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=256,
                    messages=[{"role": "user", "content": prompt}],
                )

                text = response.content[0].text if response.content else ""
                if "WHY:" in text and "REC:" in text:
                    parts = text.split("REC:")
                    why_part = parts[0].replace("WHY:", "").strip()
                    rec_part = parts[1].strip()
                    if why_part:
                        finding.why_it_matters = why_part
                    if rec_part:
                        finding.recommendation = rec_part

            except Exception as e:
                logger.warning(f"Could not enhance finding {finding.title} with Claude: {e}")

        return findings
