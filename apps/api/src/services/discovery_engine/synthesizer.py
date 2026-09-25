import logging
from typing import Any

from apps.api.src.config.settings import settings
from apps.api.src.services.discovery_engine.base import CandidateFinding

logger = logging.getLogger("unotusk-discovery")


class FindingSynthesizer:
    def __init__(self) -> None:
        self.provider = (settings.LLM_PROVIDER or "offline").lower()
        self._client = None
        self._groq_client = None
        self.model = settings.GROQ_MODEL if self.provider == "groq" else settings.ANTHROPIC_MODEL

        if self.provider == "groq" and settings.GROQ_API_KEY:
            try:
                import groq

                self._groq_client = groq.AsyncGroq(api_key=settings.GROQ_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client for synthesizer: {e}")
        elif self.provider == "claude" and settings.ANTHROPIC_API_KEY:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client for synthesizer: {e}")

    async def enhance_recommendations(
        self,
        findings: list[CandidateFinding],
        active_knowledge: list[Any] | None = None,
    ) -> list[CandidateFinding]:
        """Optionally incorporates customer knowledge context and uses Claude to polish recommendations."""
        # 1. Apply deterministic customer knowledge context
        if active_knowledge:
            for finding in findings:
                ev_paths = {
                    str(e.get("file", "")).lower() for e in finding.evidence if isinstance(e, dict)
                }
                ev_syms = {
                    str(e.get("symbol", "")).lower()
                    for e in finding.evidence
                    if isinstance(e, dict)
                }
                finding_text = f"{finding.title} {finding.description}".lower()

                matching_knowledge = []
                for k in active_knowledge:
                    k_sym = getattr(k, "related_symbol", None)
                    k_path = getattr(k, "related_file_path", None)
                    k_title = getattr(k, "title", "").lower()

                    if k_sym and k_sym.lower() in ev_syms:
                        matching_knowledge.append(k)
                    elif k_path and any(k_path.lower() in p for p in ev_paths):
                        matching_knowledge.append(k)
                    elif k_sym and k_sym.lower() in finding_text:
                        matching_knowledge.append(k)
                    elif any(word in finding_text for word in k_title.split() if len(word) > 4):
                        matching_knowledge.append(k)

                if matching_knowledge:
                    top_k = matching_knowledge[0]
                    finding.why_it_matters += (
                        f" (Project Knowledge: Team states '{top_k.content}')."
                    )

        has_client = self._client is not None or self._groq_client is not None
        if not has_client or not findings:
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

                text = ""
                if self._groq_client:
                    response = await self._groq_client.chat.completions.create(
                        model=self.model,
                        max_tokens=256,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    if response.choices and response.choices[0].message:
                        text = response.choices[0].message.content or ""
                elif self._client:
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
                logger.warning(f"Could not enhance finding {finding.title} with LLM: {e}")

        return findings
