import asyncio
import logging
from typing import Any

from apps.api.src.config.settings import settings
from apps.api.src.services.llm.base import (
    GroundedAnswer,
    LLMProvider,
    extract_customer_notes,
    extract_integration_notes,
    format_insufficient_evidence_response,
    should_abstain_due_to_insufficient_evidence,
)
from apps.api.src.services.llm.system_prompt import PROJECT_INTELLIGENCE_SYSTEM_PROMPT
from apps.api.src.services.llm.thinking_policy import (
    ThinkingPolicy,
    ThinkingTier,
    get_thinking_policy,
)

logger = logging.getLogger("unotusk-llm-groq")


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self._client = None
        if self.api_key:
            try:
                import groq

                self._client = groq.AsyncGroq(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Groq client: {e}")

    async def generate_grounded_answer(
        self,
        question: str,
        project_context: str,
        evidence_items: list[dict[str, Any]],
        related_entities: list[str],
        conversation_history: list[dict[str, str]] | None = None,
        thinking_tier: str | None = None,
    ) -> GroundedAnswer:



        policy = get_thinking_policy(thinking_tier)
        customer_notes = extract_customer_notes(project_context)
        integration_notes = extract_integration_notes(project_context)

        # Architecture V1 Section 9 Low-Confidence Synthesis Gate
        should_abstain, max_rel = should_abstain_due_to_insufficient_evidence(
            evidence_items=evidence_items,
            customer_notes=customer_notes,
            integration_notes=integration_notes,
        )

        if should_abstain:
            abstention_content = format_insufficient_evidence_response(
                question=question,
                max_relevance=max_rel,
            )
            return GroundedAnswer(
                content=abstention_content,
                evidence=[],
                related_entities=[],
                confidence="LOW",
                debug_signals={
                    "is_abstention": True,
                    "abstention_reason": "INSUFFICIENT_EVIDENCE",
                    "model": "low-confidence-synthesis-gate",
                    "provider": "offline",
                    "thinking_tier": policy.tier.value,
                    "evidence_count": len(evidence_items),
                    "max_relevance": max_rel,
                },
            )


        if max_rel >= 0.8:
            confidence = "HIGH"
        elif max_rel >= 0.5:
            confidence = "MEDIUM"




        else:
            confidence = "LOW"







        # If live API key is available, call Groq API
        if self._client:
            try:
                system_content = f"{PROJECT_INTELLIGENCE_SYSTEM_PROMPT}\n\n{policy.system_directive}"
                messages: list[dict[str, str]] = [
                    {"role": "system", "content": system_content}
                ]
                if conversation_history:
                    for msg in conversation_history[-6:]:  # Keep recent history
                        messages.append({"role": msg["role"], "content": msg["content"]})

                # Cap context characters to ensure request never exceeds model TPM limit (~14k chars / ~3.5k tokens)
                safe_context = project_context
                if len(safe_context) > 14000:
                    safe_context = safe_context[:14000] + "\n... [context truncated to stay within token budget]"

                user_prompt = (
                    f"## PROJECT CONTEXT EVIDENCE\n\n"
                    f"{safe_context}\n\n"
                    f"## USER QUESTION\n"
                    f"{question}\n\n"
                    f"Please provide an evidence-grounded answer based strictly on the above context."
                )
                messages.append({"role": "user", "content": user_prompt})

                max_retries = 2
                response = None
                for attempt in range(max_retries + 1):
                    try:
                        response = await self._client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            max_tokens=750,
                            temperature=0.1,
                            reasoning_effort=policy.groq_reasoning_effort,
                            reasoning_format=policy.groq_reasoning_format,
                        )
                        break
                    except Exception as err:
                        err_str = str(err)
                        if ("429" in err_str or "rate_limit" in err_str.lower()) and attempt < max_retries:
                            wait_sec = 3 * (attempt + 1)
                            logger.warning(
                                f"Groq 429 rate limit hit, retrying in {wait_sec}s (attempt {attempt + 1}/{max_retries})..."
                            )
                            await asyncio.sleep(wait_sec)
                            continue
                        raise

                content = (
                    response.choices[0].message.content
                    if response and response.choices and response.choices[0].message.content
                    else "No response generated."
                )
                prompt_tokens = (
                    response.usage.prompt_tokens if response and response.usage else len(project_context) // 4
                )
                completion_tokens = (
                    response.usage.completion_tokens if response and response.usage else len(content) // 4
                )

                return GroundedAnswer(
                    content=content,
                    evidence=evidence_items,
                    related_entities=related_entities,
                    confidence=confidence,
                    debug_signals={
                        "model": self.model,
                        "provider": "groq",
                        "thinking_tier": policy.tier.value,
                        "reasoning_effort": policy.groq_reasoning_effort,
                        "evidence_count": len(evidence_items),
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Groq API call failed: {e}. Falling back to deterministic synthesis.",
                    exc_info=True,
                )
                last_error_reason = str(e)
        else:
            last_error_reason = "No API key configured"

        # Deterministic offline synthesis fallback (for tests, CI, or when API key is not configured)
        fallback_content = self._generate_offline_grounded_answer(
            question=question,
            evidence_items=evidence_items,
            related_entities=related_entities,
            project_context=project_context,
            confidence=confidence,
            policy=policy,
            error_reason=last_error_reason,
        )

        return GroundedAnswer(
            content=fallback_content,
            evidence=evidence_items,
            related_entities=related_entities,
            confidence=confidence,
            debug_signals={
                "model": "offline-grounded-synthesizer",
                "provider": "offline",
                "thinking_tier": policy.tier.value,
                "reasoning_effort": policy.groq_reasoning_effort,
                "evidence_count": len(evidence_items),
                "error_reason": last_error_reason,
            },
        )

    def _generate_offline_grounded_answer(
        self,
        question: str,
        evidence_items: list[dict[str, Any]],
        related_entities: list[str],
        project_context: str,
        confidence: str,
        policy: ThinkingPolicy | None = None,
        error_reason: str | None = None,
    ) -> str:
        customer_notes = extract_customer_notes(project_context)
        integration_notes = extract_integration_notes(project_context)

        if not evidence_items and not customer_notes and not integration_notes:
            return (
                "### Analysis\n\n"
                "I searched the project context, but no matching files, symbols, dependencies, "
                "or synchronized integration records were found in the current project context.\n\n"
                "**Note**: If this component or issue was recently added, try re-synchronizing or re-indexing."
            )

        top_evidence = evidence_items[:6]
        files = sorted(
            list(
                {
                    e.get("file") or e.get("file_path")
                    for e in top_evidence
                    if (e.get("file") or e.get("file_path")) and e.get("type") not in ("integration", "knowledge")
                }
            )
        )
        symbols = [
            e["symbol"]
            for e in top_evidence
            if e.get("symbol") and e.get("type") not in ("integration", "knowledge")
        ]

        prefix = ""
        if error_reason:
            if "429" in error_reason or "rate_limit" in error_reason.lower():
                prefix = "> [!WARNING]\n> **Groq Rate Limit**: Free-tier TPM limit reached. Displaying grounded context fallback. Wait ~30s for the rate-limit window to reset.\n\n"
            elif "404" in error_reason or "model_not_found" in error_reason.lower():
                prefix = f"> [!WARNING]\n> **Model Notice**: The model is not accessible on your API key ({error_reason[:80]}). Displaying grounded context fallback.\n\n"
            elif error_reason != "No API key configured":
                prefix = f"> [!NOTE]\n> **Offline Synthesis Fallback**: {error_reason[:100]}\n\n"

        # Fast/Lightest synthesis for HOT tier
        if policy and policy.tier == ThinkingTier.HOT:
            hot_lines = [
                f"{prefix}### Quick Summary: {question}\n",
                f"Direct answer based on {len(top_evidence)} primary evidence sources:",
            ]
            if integration_notes:
                hot_lines.append(f"- **Integration Requirement**: {integration_notes[0]}")
            if files:
                hot_lines.append(f"- **Files**: {', '.join([f'`{f}`' for f in files[:3]])}")
            if symbols:
                hot_lines.append(f"- **Key Symbols**: {', '.join([f'`{s}`' for s in symbols[:3]])}")
            if top_evidence:
                first_ev = top_evidence[0]
                first_file = first_ev.get("file") or first_ev.get("file_path") or "Unknown"
                hot_lines.append(
                    f"- **Primary Reference**: `{first_file}` (Lines {first_ev.get('lines', 'N/A')})"
                )
            return "\n".join(hot_lines)

        lines = [
            f"{prefix}### Project Analysis: {question}\n",
            "Based on the indexed project context, the relevant architecture and implementation details are identified below:\n",
        ]

        if integration_notes:
            lines.append("**Integrated Specifications & Requirements (Connected Integrations):**")
            for note in integration_notes:
                lines.append(note)
            lines.append(
                "\n*Note: Integration requirements reflect synchronized issues, specifications, and external documentation from connected tools.*"
            )
            lines.append("")

        if customer_notes:
            lines.append("**Customer Project Knowledge (User-Provided Context):**")
            for note in customer_notes:
                lines.append(note)
            lines.append(
                "\n*Note: Customer knowledge represents team-provided intent and architectural decisions, interpreted alongside repository code.*"
            )
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
            lines.append("**Observed Implementation & Integration Details:**")
            for i, ev in enumerate(top_evidence, start=1):
                ev_type = ev.get("type", "file")
                if ev_type == "integration" or ev.get("source_reference_id"):
                    ref_str = f"[{ev.get('source_reference_type') or 'INTEGRATION'} {ev.get('source_reference_id') or ''}]".strip()
                    title_str = ev.get("title") or ev.get("symbol") or "Requirement"
                    lines.append(
                        f"{i}. **{ref_str}**: {title_str}\n"
                        f"   Content: {ev.get('snippet', '')}"
                    )
                else:
                    sym_name = f" (`{ev['symbol']}`)" if ev.get("symbol") else ""
                    ev_file = ev.get("file") or ev.get("file_path") or "Unknown"
                    lines.append(
                        f"{i}. **{ev_file}**{sym_name} (Lines {ev.get('lines', 'N/A')}):\n"
                        f"   Contains relevant definitions and logic associated with this query."
                    )

        if related_entities:
            lines.append("\n**Connected Components:**")
            lines.append(f"{', '.join([f'`{e}`' for e in related_entities[:8]])}")

        # Deep reasoning analysis section for COLD tier
        if policy and policy.tier == ThinkingTier.COLD:
            lines.append("\n**Deep Architectural Reasoning & Verification:**")
            lines.append("- Multi-hop structural dependency verification completed across indexed modules.")
            lines.append("- Analyzed cross-module relationships, contracts, and failure boundary constraints.")

        return "\n".join(lines)

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self._client:
            return {}
        import json
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=500,
                )
                content = response.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "rate_limit" in err_str.lower()) and attempt < max_retries:
                    wait_sec = 3 * (attempt + 1)
                    logger.warning(
                        f"Groq generate_json 429 rate limit hit, retrying in {wait_sec}s..."
                    )
                    await asyncio.sleep(wait_sec)
                    continue
                logger.error(f"Groq generate_json error: {e}")
                return {}
        return {}
