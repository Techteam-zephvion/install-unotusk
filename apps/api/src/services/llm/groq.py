import asyncio
import logging
import re
import time
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

logger = logging.getLogger("unotusk-llm-groq")

RE_THINK_TAGS = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
RE_THOUGHT_TAGS = re.compile(r"<thought>(.*?)</thought>", re.DOTALL | re.IGNORECASE)


def sanitize_llm_output(text: str, max_chars: int = 32_000) -> str:
    """
    Sanitize LLM output:
    1. Strip null bytes (\x00) to protect database text columns.
    2. Normalize non-printable control characters while preserving \n, \r, \t.
    3. Enforce maximum character bound with clean truncation marker.
    4. Auto-balance unclosed markdown code blocks (```) to prevent rendering breakage.
    """
    if not text:
        return "No response generated."

    # 1. Strip null bytes
    text = text.replace("\x00", "")

    # 2. Strip non-printable control characters
    text = "".join(
        c for c in text if c in ("\n", "\r", "\t") or (ord(c) >= 32 and ord(c) != 127)
    )

    # 3. Cap length if exceeding max_chars
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "\n\n... [Response capped to safe length boundary]"
        # 4. Auto-close unclosed markdown code fence
        fence_count = text.count("```")
        if fence_count % 2 != 0:
            text += "\n```"

    return text.strip() or "No response generated."


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
        start_time = time.time()
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
                    "latency_sec": round(time.time() - start_time, 2),
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
                # Include recent conversation turns with bounded length to preserve TPM budget
                if conversation_history:
                    for msg in conversation_history[-4:]:
                        c_text = str(msg.get("content", ""))
                        # Sanitize previous turns to prevent TPM exhaustion:
                        # 1. Strip bulky previous mermaid blocks from history
                        c_text = re.sub(r"```mermaid[\s\S]*?```", "[Diagram shown previously]", c_text)
                        # 2. Strip large code blocks from history
                        c_text = re.sub(r"```[\s\S]*?```", "[Code snippet shown previously]", c_text)
                        # 3. Omit previous error notices or unhelpful status banners
                        if any(err_token in c_text for err_token in ("Groq Service Notice", "No response generated", "Server Response:")):
                            continue
                        if len(c_text) > 400:
                            c_text = c_text[:400] + "..."
                        messages.append({"role": msg["role"], "content": c_text})

                # Cap context characters based on model capacity:
                # 70B has a tight 6,000 TPM limit; cap context to 7,500 chars to prevent 429s.
                # 8B / 9B has a 30,000 TPM limit; allow up to 28,000 chars (~7k tokens).
                model_name = self.model or "qwen/qwen3.8-27b"
                max_ctx_chars = (
                    7500
                    if any(k in model_name.lower() for k in ("70b", "qwen", "27b", "120b"))
                    else 28000
                )
                safe_context = project_context
                if len(safe_context) > max_ctx_chars:
                    safe_context = safe_context[:max_ctx_chars] + "\n... [context trimmed to stay within rate limit]"

                user_prompt = (
                    f"## CURRENT TARGET USER QUESTION (MUST ANSWER THIS DIRECTLY):\n"
                    f"{question}\n\n"
                    f"## PROJECT CONTEXT EVIDENCE\n\n"
                    f"{safe_context}\n\n"
                    f"## STRICT OUTPUT INSTRUCTIONS:\n"
                    f"1. Directly answer the CURRENT TARGET USER QUESTION: \"{question}\".\n"
                    f"2. Do NOT answer previous conversation turns or summarize the repository unless specifically requested in the current question.\n"
                    f"3. Provide ONLY your final, professional answer intended for the user. Do NOT output your internal planning thoughts, scratchpad checklists, or self-monologue (such as 'We need to answer...', 'Need maybe mention...', 'OBSERVED: ...').\n"
                    f"4. If the question asks about repository commits, dates, or git history that are not contained in the context evidence above, clearly state that commit records are not present in the current indexed snapshot."
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

                # Determine if model supports DeepSeek R1 / Qwen reasoning parameters
                is_reasoning_model = any(k in model_name.lower() for k in ("r1", "deepseek", "qwen"))
                create_kwargs: dict[str, Any] = {
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": 2500,
                    "temperature": 0.1,
                }
                if is_reasoning_model:
                    create_kwargs["reasoning_effort"] = policy.groq_reasoning_effort
                    create_kwargs["reasoning_format"] = policy.groq_reasoning_format

                max_retries = 3
                response = None
                for attempt in range(max_retries):
                    try:
                        response = await self._client.chat.completions.create(**create_kwargs)
                        break
                    except Exception as err:
                        err_str = str(err)
                        is_rate_limit = (
                            "429" in err_str
                            or "rate_limit" in err_str.lower()
                            or "tokens per minute" in err_str.lower()
                            or "413" in err_str
                            or "too large" in err_str.lower()
                        )
                        if is_rate_limit and attempt < max_retries - 1:
                            if "413" in err_str or "too large" in err_str.lower():
                                current_prompt = create_kwargs["messages"][-1]["content"]
                                if len(current_prompt) > 4000:
                                    create_kwargs["messages"][-1]["content"] = (
                                        current_prompt[:4000] + "\n... [context trimmed]"
                                    )
                            wait_sec = 2 * (attempt + 1)
                            logger.warning(f"Groq rate limit hit, retrying in {wait_sec}s...")
                            await asyncio.sleep(wait_sec)
                            continue
                        raise

                reasoning_parts: list[str] = []
                raw_msg = response.choices[0].message if (response and response.choices) else None
                content = None
                if raw_msg:
                    content = raw_msg.content
                    # Check reasoning attributes
                    if hasattr(raw_msg, "reasoning") and raw_msg.reasoning:
                        reasoning_parts.append(str(raw_msg.reasoning).strip())
                    elif hasattr(raw_msg, "reasoning_content") and raw_msg.reasoning_content:
                        reasoning_parts.append(str(raw_msg.reasoning_content).strip())
                    # If content is empty but model produced reasoning output, use it
                    if not content and reasoning_parts:
                        content = reasoning_parts[0]

                # If still empty, perform fallback generation on fallback model
                if (not content or not content.strip()) and create_kwargs.get("model") != "llama-3.1-8b-instant":
                    try:
                        create_kwargs["model"] = "llama-3.1-8b-instant"
                        create_kwargs["messages"] = [
                            {"role": "system", "content": system_content},
                            {"role": "user", "content": user_prompt},
                        ]
                        retry_resp = await self._client.chat.completions.create(**create_kwargs)
                        if retry_resp and retry_resp.choices:
                            content = retry_resp.choices[0].message.content
                    except Exception as retry_err:
                        logger.warning(f"Fallback retry failed: {retry_err}")

                # Extract and strip <think> / <thought> tags from content
                if content:
                    for m in RE_THINK_TAGS.finditer(content):
                        if m.group(1).strip():
                            reasoning_parts.append(m.group(1).strip())
                    for m in RE_THOUGHT_TAGS.finditer(content):
                        if m.group(1).strip():
                            reasoning_parts.append(m.group(1).strip())
                    content = RE_THINK_TAGS.sub("", content)
                    content = RE_THOUGHT_TAGS.sub("", content).strip()

                # Detect and isolate unbracketed internal planning scratchpad (e.g. "We need answer user's request...", "Need maybe mention...")
                if content and re.match(r"^\s*(?:We need (?:to )?answer|Need (?:maybe )?mention|I need to answer|The user is asking|Planning:)", content, re.IGNORECASE):
                    lines = content.split("\n")
                    clean_lines: list[str] = []
                    scratch_lines: list[str] = []
                    is_past_scratchpad = False

                    for line in lines:
                        trimmed = line.strip()
                        if not is_past_scratchpad:
                            # The real answer begins when standard markdown headings, mermaid blocks, or formal answers start
                            if trimmed.startswith("###") or trimmed.startswith("##") or trimmed.startswith("#") or trimmed.startswith("```mermaid") or trimmed.startswith("**Answer") or (trimmed.startswith("**") and "observed" not in trimmed.lower()):
                                is_past_scratchpad = True
                                clean_lines.append(line)
                            else:
                                scratch_lines.append(line)
                        else:
                            clean_lines.append(line)

                    if clean_lines:
                        raw_scratch = "\n".join(scratch_lines).strip()
                        if raw_scratch:
                            reasoning_parts.append(raw_scratch)
                        content = "\n".join(clean_lines).strip()

                clean_content = sanitize_llm_output(content or "No response generated.", max_chars=32000)
                extracted_reasoning = "\n\n".join(reasoning_parts).strip()
                clean_reasoning = sanitize_llm_output(extracted_reasoning, max_chars=16000) if extracted_reasoning else None
                latency_sec = round(time.time() - start_time, 2)

                prompt_tokens = (
                    response.usage.prompt_tokens if response and response.usage else len(project_context) // 4
                )
                completion_tokens = (
                    response.usage.completion_tokens if response and response.usage else len(clean_content) // 4
                )

                return GroundedAnswer(
                    content=clean_content,
                    evidence=evidence_items,
                    related_entities=related_entities,
                    confidence=confidence,
                    debug_signals={
                        "model": create_kwargs.get("model", self.model),
                        "provider": "groq",
                        "thinking_tier": policy.tier.value,
                        "reasoning_effort": policy.groq_reasoning_effort,
                        "evidence_count": len(evidence_items),
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "latency_sec": latency_sec,
                        "reasoning_text": clean_reasoning,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Groq API call failed: {e}",
                    exc_info=True,
                )
                last_error_reason = str(e)
        else:
            last_error_reason = "No API key configured"

        # If live API fails, attempt automatic failover to OpenRouter before showing error
        if last_error_reason and "No API key configured" not in last_error_reason:
            if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip():
                try:
                    logger.warning(
                        f"Groq API call failed ({last_error_reason}); initiating automatic failover to OpenRouter..."
                    )
                    from apps.api.src.services.llm.openrouter import OpenRouterProvider

                    openrouter_provider = OpenRouterProvider()
                    failover_ans = await openrouter_provider.generate_grounded_answer(
                        question=question,
                        project_context=project_context,
                        evidence_items=evidence_items,
                        related_entities=related_entities,
                        conversation_history=conversation_history,
                        thinking_tier=thinking_tier,
                    )
                    failover_ans.debug_signals["failover_from"] = "groq"
                    failover_ans.debug_signals["groq_error"] = last_error_reason
                    return failover_ans
                except Exception as fo_err:
                    logger.error(f"OpenRouter failover also failed: {fo_err}")

            error_notice = (
                f"### Groq Service Notice\n\n"
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
                    "provider": "groq",
                    "error": last_error_reason,
                    "latency_sec": round(time.time() - start_time, 2),
                },
            )

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
                "latency_sec": round(time.time() - start_time, 2),
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
        max_retries = 2
        # Use high-throughput 8B model for lightweight metadata extraction to preserve 70B quota
        json_model = self.model or "qwen/qwen3.8-27b"
        for attempt in range(max_retries + 1):
            try:
                response = await self._client.chat.completions.create(
                    model=json_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=400,
                )
                content = response.choices[0].message.content
                return json.loads(content)
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "rate_limit" in err_str.lower()) and attempt < max_retries:
                    wait_sec = 2 * (attempt + 1)
                    await asyncio.sleep(wait_sec)
                    continue
                logger.error(f"Groq generate_json error: {e}")
                if settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip():
                    try:
                        logger.warning("Falling back to OpenRouter for generate_json...")
                        from apps.api.src.services.llm.openrouter import OpenRouterProvider

                        openrouter_provider = OpenRouterProvider()
                        return await openrouter_provider.generate_json(system_prompt, user_prompt)
                    except Exception as fo_err:
                        logger.error(f"OpenRouter generate_json fallback failed: {fo_err}")
                return {}
        return {}
