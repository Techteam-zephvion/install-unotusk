import logging
from typing import Any

from apps.api.src.config.settings import settings
from apps.api.src.services.llm.base import GroundedAnswer, LLMProvider
from apps.api.src.services.llm.system_prompt import PROJECT_INTELLIGENCE_SYSTEM_PROMPT

logger = logging.getLogger("unotusk-llm")


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.ANTHROPIC_MODEL
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client: {e}")

    async def generate_grounded_answer(
        self,
        question: str,
        project_context: str,
        evidence_items: list[dict[str, Any]],
        related_entities: list[str],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> GroundedAnswer:
        # Determine confidence based on retrieved evidence density & relevance
        confidence = "LOW"
        if evidence_items:
            max_rel = max((e.get("relevance", 0.0) for e in evidence_items), default=0.0)
            if max_rel >= 0.8:
                confidence = "HIGH"
            elif max_rel >= 0.5:
                confidence = "MEDIUM"

        # If live API key is available, call Claude API
        if self._client:
            try:
                messages: list[dict[str, str]] = []
                if conversation_history:
                    for msg in conversation_history[-6:]:  # Keep recent history
                        messages.append({"role": msg["role"], "content": msg["content"]})

                user_prompt = (
                    f"## PROJECT CONTEXT EVIDENCE\n\n"
                    f"{project_context}\n\n"
                    f"## USER QUESTION\n"
                    f"{question}\n\n"
                    f"Please provide an evidence-grounded answer based strictly on the above context."
                )
                messages.append({"role": "user", "content": user_prompt})

                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=2048,
                    system=PROJECT_INTELLIGENCE_SYSTEM_PROMPT,
                    messages=messages,
                )

                content = response.content[0].text if response.content else "No response generated."
                return GroundedAnswer(
                    content=content,
                    evidence=evidence_items,
                    related_entities=related_entities,
                    confidence=confidence,
                    debug_signals={
                        "model": self.model,
                        "provider": "claude",
                        "evidence_count": len(evidence_items),
                        "prompt_tokens_est": len(project_context) // 4,
                    },
                )
            except Exception as e:
                logger.error(f"Claude API call failed: {e}. Falling back to deterministic synthesis.", exc_info=True)

        # Deterministic offline synthesis fallback (for tests, CI, or when API key is not configured)
        fallback_content = self._generate_offline_grounded_answer(
            question=question,
            evidence_items=evidence_items,
            related_entities=related_entities,
            project_context=project_context,
            confidence=confidence,
        )

        return GroundedAnswer(
            content=fallback_content,
            evidence=evidence_items,
            related_entities=related_entities,
            confidence=confidence,
            debug_signals={
                "model": "offline-grounded-synthesizer",
                "provider": "offline",
                "evidence_count": len(evidence_items),
            },
        )

    def _generate_offline_grounded_answer(
        self,
        question: str,
        evidence_items: list[dict[str, Any]],
        related_entities: list[str],
        project_context: str,
        confidence: str,
    ) -> str:
        # Extract any active customer knowledge from context
        customer_notes: list[str] = []
        if "<customer_project_knowledge>" in project_context:
            try:
                start_tag = "<customer_project_knowledge>"
                end_tag = "</customer_project_knowledge>"
                start_idx = project_context.find(start_tag) + len(start_tag)
                end_idx = project_context.find(end_tag)
                if start_idx != -1 and end_idx != -1:
                    raw_knowledge = project_context[start_idx:end_idx].strip()
                    for block in raw_knowledge.split("### [CUSTOMER:"):
                        block = block.strip()
                        if block and not block.startswith("This is user-provided"):
                            lines_b = block.splitlines()
                            header = lines_b[0].strip()
                            content_lines = [
                                line_text
                                for line_text in lines_b[1:]
                                if line_text.strip().startswith("Content:")
                            ]
                            content_txt = content_lines[0].replace("Content:", "").strip() if content_lines else ""
                            customer_notes.append(f"- **[CUSTOMER: {header}]**: {content_txt}")
            except Exception:
                pass

        if not evidence_items and not customer_notes:
            return (
                f"### Analysis\n\n"
                f"I searched the project context for references to **'{question}'**, "
                f"but no matching files, symbols, or dependencies were found in the current repository snapshot.\n\n"
                f"**Note**: If this component was recently added, try re-indexing the repository."
            )

        top_evidence = evidence_items[:5]
        files = sorted(list({e["file"] for e in top_evidence if e.get("file")}))
        symbols = [e["symbol"] for e in top_evidence if e.get("symbol")]

        lines = [
            f"### Project Analysis: {question}\n",
            "Based on the indexed project context, the relevant architecture and implementation details are identified below:\n",
        ]

        if customer_notes:
            lines.append("**Customer Project Knowledge (User-Provided Context):**")
            for note in customer_notes:
                lines.append(note)
            lines.append("\n*Note: Customer knowledge represents team-provided intent and architectural decisions, interpreted alongside repository code.*")
            lines.append("")

        if symbols:
            lines.append("**Key Symbols & Entities Identified in Code:**")
            for sym in symbols[:6]:
                lines.append(f"- `{sym}`")
            lines.append("")

        if files:
            lines.append("**Primary Files Involved:**")
            for f in files:
                lines.append(f"- `{f}`")
            lines.append("")

        if top_evidence:
            lines.append("**Observed Implementation Details:**")
            for i, ev in enumerate(top_evidence, start=1):
                sym_name = f" (`{ev['symbol']}`)" if ev.get("symbol") else ""
                lines.append(
                    f"{i}. **{ev['file']}**{sym_name} (Lines {ev.get('lines', 'N/A')}):\n"
                    f"   Contains relevant definitions and logic associated with this query."
                )

        if related_entities:
            lines.append("\n**Connected Components:**")
            lines.append(f"{', '.join([f'`{e}`' for e in related_entities[:8]])}")

        return "\n".join(lines)
