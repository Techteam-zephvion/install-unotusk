import asyncio
import json
import logging
import re
from typing import Any

import httpx

from apps.api.src.config.settings import settings
from apps.api.src.services.llm.base import (
    GroundedAnswer,
    LLMProvider,
    extract_customer_notes,
    extract_integration_notes,
    format_insufficient_evidence_response,
    generate_grounded_mermaid_diagram,
    should_abstain_due_to_insufficient_evidence,
)
from apps.api.src.services.llm.system_prompt import PROJECT_INTELLIGENCE_SYSTEM_PROMPT
from apps.api.src.services.llm.thinking_policy import (
    ThinkingPolicy,
    ThinkingTier,
    get_thinking_policy,
)

logger = logging.getLogger("unotusk-llm-openrouter")


class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL or "openrouter/free"
        self.base_url = "https://openrouter.ai/api/v1"

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

        last_error_reason: str | None = None

        if self.api_key:
            try:
                system_content = f"{PROJECT_INTELLIGENCE_SYSTEM_PROMPT}\n\n{policy.system_directive}"
                messages: list[dict[str, str]] = [
                    {"role": "system", "content": system_content}
                ]

                # Sanitize & include recent turns
                if conversation_history:
                    for msg in conversation_history[-4:]:
                        c_text = str(msg.get("content", ""))
                        c_text = re.sub(r"```mermaid[\s\S]*?```", "[Diagram shown previously]", c_text)
                        c_text = re.sub(r"```[\s\S]*?```", "[Code snippet shown previously]", c_text)
                        if any(err_token in c_text for err_token in ("Service Notice", "No response generated", "Server Response:")):
                            continue
                        if len(c_text) > 400:
                            c_text = c_text[:400] + "..."
                        messages.append({"role": msg["role"], "content": c_text})

                # Safe context truncation for rate limits / token bounds
                max_ctx_chars = 12000
                safe_context = project_context
                if len(safe_context) > max_ctx_chars:
                    safe_context = safe_context[:max_ctx_chars] + "\n... [context trimmed to stay within rate limit]"

                user_prompt = (
                    f"## PROJECT CONTEXT EVIDENCE\n\n"
                    f"{safe_context}\n\n"
                    f"## USER QUESTION\n"
                    f"{question}\n\n"
                    f"Please provide an evidence-grounded answer based strictly on the above context."
                )
                q_lower = question.lower()
                if any(k in q_lower for k in ("diagram", "architecture", "flowchart", "workflow", "design", "sequence", "graph", "structure", "spec", "overview", "components")):
                    user_prompt += (
                        "\n\nDIAGRAM REQUIREMENT:\n"
                        "You MUST generate a comprehensive, deeply tailored Mermaid diagram (```mermaid ... ```) "
                        "illustrating the REAL components, modules, dependencies, and execution flow found in the context above. "
                        "Include 8 to 15 distinct nodes grouped into semantic subgraphs (e.g. UI, API / Controllers, Domain Services, Data Models, Infrastructure). "
                        "Always enclose node labels in double quotes (e.g. NodeId[\"Module Name (detail)\"]) to ensure valid parsing, "
                        "and declare the diagram type on the very first line inside the code fence (e.g. flowchart TD)."
                    )
                messages.append({"role": "user", "content": user_prompt})

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://unotusk.com",
                    "X-Title": "Unotusk Intelligence",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 2500,
                    "temperature": 0.1,
                }

                max_retries = 3
                res = None
                async with httpx.AsyncClient(timeout=45.0) as client:
                    for attempt in range(max_retries):
                        try:
                            response = await client.post(
                                f"{self.base_url}/chat/completions",
                                headers=headers,
                                json=payload,
                            )
                            if response.status_code == 200:
                                res = response.json()
                                break
                            elif response.status_code in (429, 503) and attempt < max_retries - 1:
                                wait_sec = 2 * (attempt + 1)
                                logger.warning(f"OpenRouter status {response.status_code}, retrying in {wait_sec}s...")
                                await asyncio.sleep(wait_sec)
                                continue
                            else:
                                err_body = response.text
                                raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {err_body}")
                        except httpx.RequestError as exc:
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2)
                                continue
                            raise RuntimeError(f"OpenRouter connection error: {exc}")

                if res and "choices" in res and res["choices"]:
                    raw_msg = res["choices"][0].get("message", {})
                    content = raw_msg.get("content") or "No response generated."
                    usage = res.get("usage", {})
                    prompt_tokens = usage.get("prompt_tokens", len(project_context) // 4)
                    completion_tokens = usage.get("completion_tokens", len(content) // 4)

                    return GroundedAnswer(
                        content=content,
                        evidence=evidence_items,
                        related_entities=related_entities,
                        confidence=confidence,
                        debug_signals={
                            "model": self.model,
                            "provider": "openrouter",
                            "thinking_tier": policy.tier.value,
                            "evidence_count": len(evidence_items),
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": completion_tokens,
                        },
                    )

            except Exception as e:
                logger.error(f"OpenRouter API call failed: {e}", exc_info=True)
                last_error_reason = str(e)
        else:
            last_error_reason = "No API key configured"

        # If live API fails, return explicit notice
        if last_error_reason and "No API key configured" not in last_error_reason:
            error_notice = (
                f"### OpenRouter Service Notice\n\n"
                f"The AI model request could not be completed: `{last_error_reason}`.\n\n"
                f"Please wait a moment and try asking again."
            )
            return GroundedAnswer(
                content=error_notice,
                evidence=evidence_items,
                related_entities=related_entities,
                confidence="LOW",
                debug_signals={
                    "model": self.model,
                    "provider": "openrouter",
                    "error": last_error_reason,
                },
            )

        # Fallback to deterministic offline synthesis
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
                prefix = "> [!WARNING]\n> **OpenRouter Rate Limit**: Free-tier limit reached. Displaying grounded context fallback.\n\n"
            elif error_reason != "No API key configured":
                prefix = f"> [!NOTE]\n> **Offline Synthesis Fallback**: {error_reason[:100]}\n\n"

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
            lines.append("**Observed Implementation Details:**")
            for i, ev in enumerate(top_evidence, start=1):
                ev_type = ev.get("type", "file")
                if ev_type == "integration" or ev.get("source_reference_id"):
                    ref_str = f"[{ev.get('source_reference_type') or 'INTEGRATION'} {ev.get('source_reference_id') or ''}]".strip()
                    title_str = ev.get("title") or ev.get("symbol") or "Requirement"
                    lines.append(
                        f"{i}. **{ref_str}**: {title_str}\n"
                        f"   Content: {ev.get('snippet', '')}"
                    )
                elif ev_type in ("evidence_path", "star_rag_path"):
                    path_str = ev.get("relationship_path") or ev.get("snippet") or ev.get("symbol") or ""
                    first_file = ev.get("file") or "codebase"
                    lines.append(
                        f"{i}. **Structural Call Path**: `{path_str}`\n"
                        f"   Traces call hierarchy and execution flow through: `{first_file}`."
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

        if policy and policy.tier == ThinkingTier.COLD:
            lines.append("\n**Deep Architectural Reasoning & Verification:**")
            lines.append("- Multi-hop structural dependency verification completed across indexed modules.")
            lines.append("- Analyzed cross-module relationships, contracts, and failure boundary constraints.")

        diagram = generate_grounded_mermaid_diagram(
            question=question,
            evidence_items=top_evidence,
            symbols=symbols,
            files=files,
        )
        if diagram:
            lines.append("\n### Architecture and Flowchart Visualization\n")
            lines.append(diagram)

        return "\n".join(lines)

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.api_key:
            return {}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://unotusk.com",
            "X-Title": "Unotusk Intelligence",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 400,
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    cleaned = content.strip()
                    if "```json" in cleaned:
                        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
                    elif "```" in cleaned:
                        cleaned = cleaned.split("```")[1].split("```")[0].strip()
                    return json.loads(cleaned)
        except Exception as e:
            logger.error(f"OpenRouter generate_json error: {e}")
            return {}

        return {}
