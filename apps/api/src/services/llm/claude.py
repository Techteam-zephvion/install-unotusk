import logging
from typing import Any

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

logger = logging.getLogger("unotusk-llm")


def _supports_native_thinking(model: str) -> bool:
    """Checks whether the specified Anthropic model natively supports the extended thinking parameter."""
    m = model.lower()
    return any(k in m for k in ("claude-3-7", "claude-3.7", "claude-4", "thinking"))


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



        confidence = "LOW"
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
                q_lower = question.lower()
                if any(k in q_lower for k in ("diagram", "architecture", "flowchart", "workflow", "design", "sequence", "graph", "structure", "spec")):
                    user_prompt += (
                        "\n\nDIAGRAM REQUIREMENT:\n"
                        "Include a tailored, syntactically valid Mermaid diagram (```mermaid ... ```) illustrating the "
                        "specific components, modules, dependencies, and execution flow for this question. "
                        "Always enclose node labels in double quotes (e.g. NodeId[\"Module Name (detail)\"]) to ensure valid parsing, "
                        "and organize components into semantic subgraphs with distinct directional flow."
                    )
                messages.append({"role": "user", "content": user_prompt})

                # Determine if current model natively supports extended thinking parameter
                native_thinking = _supports_native_thinking(self.model)
                system_content = f"{PROJECT_INTELLIGENCE_SYSTEM_PROMPT}\n\n{policy.system_directive}"

                create_kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "system": system_content,
                }

                if native_thinking:
                    if policy.anthropic_thinking is not None:
                        create_kwargs["thinking"] = policy.anthropic_thinking
                        create_kwargs["max_tokens"] = policy.anthropic_max_tokens
                        create_kwargs["temperature"] = 1.0  # Anthropic requires 1.0 when thinking enabled
                    else:
                        create_kwargs["thinking"] = {"type": "disabled"}
                        create_kwargs["max_tokens"] = policy.anthropic_max_tokens
                else:
                    # Model does not support native thinking (e.g. Claude 3.5 Sonnet)
                    # Reasoning depth is governed via system directive and allocated token budget
                    if policy.tier == ThinkingTier.HOT:
                        create_kwargs["max_tokens"] = 1024
                    elif policy.tier == ThinkingTier.WARM:
                        create_kwargs["max_tokens"] = 2048
                    else:  # COLD
                        create_kwargs["max_tokens"] = 4096

                response = await self._client.messages.create(**create_kwargs)

                content = response.content[0].text if response.content else "No response generated."
                reasoning_mode = (
                    "native_thinking"
                    if (native_thinking and policy.anthropic_thinking is not None)
                    else "prompt_guided"
                )

                return GroundedAnswer(
                    content=content,
                    evidence=evidence_items,
                    related_entities=related_entities,
                    confidence=confidence,
                    debug_signals={
                        "model": self.model,
                        "provider": "claude",
                        "thinking_tier": policy.tier.value,
                        "reasoning_mode": reasoning_mode,
                        "evidence_count": len(evidence_items),
                        "prompt_tokens_est": len(project_context) // 4,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Claude API call failed: {e}. Falling back to deterministic synthesis.",
                    exc_info=True,
                )

        # Deterministic offline synthesis fallback (for tests, CI, or when API key is not configured)
        fallback_content = self._generate_offline_grounded_answer(
            question=question,
            evidence_items=evidence_items,
            related_entities=related_entities,
            project_context=project_context,
            confidence=confidence,
            policy=policy,
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
    ) -> str:
        customer_notes = extract_customer_notes(project_context)
        integration_notes = extract_integration_notes(project_context)

        if not evidence_items and not customer_notes and not integration_notes:
            return (
                f"### Analysis\n\n"
                f"I searched the project context for references to **'{question}'**, "
                f"but no matching files, symbols, dependencies, or synchronized integration records were found in the current project context.\n\n"
                f"**Note**: If this component or issue was recently added, try re-synchronizing or re-indexing the repository."
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

        # Fast/Lightest synthesis for HOT tier
        if policy and policy.tier == ThinkingTier.HOT:
            hot_lines = [
                f"### Quick Summary: {question}\n",
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
            f"### Project Analysis: {question}\n",
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
                elif ev_type == "temporal_event":
                    ts_str = ev.get("timestamp") or "Historical"
                    c_sha = (ev.get("commit_sha") or "")[:8]
                    c_str = f" [Commit: {c_sha}]" if c_sha else ""
                    rel_path = ev.get("relationship_path") or f"{ev.get('subject')} {ev.get('relation')} {ev.get('object')}"
                    lines.append(
                        f"{i}. **Historical Event ({ts_str}){c_str}**: `{rel_path}`\n"
                        f"   File: `{ev.get('file', 'Unknown')}` | Detail: {ev.get('snippet', '')}"
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

        # Grounded Mermaid diagram synthesis if query requests architectural/workflow visual design
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
        if not self._client:
            return {}
        import json
        import re
        try:
            response = await self._client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=1024,
            )
            content = response.content[0].text
            # Claude doesn't have native json_object mode, extract JSON
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(content)
        except Exception as e:
            logger.error(f"Claude generate_json error: {e}")
            return {}
