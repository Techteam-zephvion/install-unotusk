from dataclasses import dataclass, field
from typing import Any

from apps.api.src.config.settings import settings
from apps.api.src.services.context_engine.ranker import RankedCandidate


@dataclass
class AssembledContext:
    prompt_context: str
    evidence_items: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    total_characters: int = 0
    candidate_count: int = 0


class ContextAssembler:
    @staticmethod
    def assemble_context(
        ranked_candidates: list[RankedCandidate],
        max_tokens: int | None = None,
    ) -> AssembledContext:
        budget_tokens = max_tokens or settings.CONTEXT_BUDGET_TOKENS
        # Approximate 4 characters per token
        char_budget = budget_tokens * 4

        sections: list[str] = []
        evidence_items: list[dict[str, Any]] = []
        related_entities: set[str] = set()

        current_chars = 0
        used_count = 0

        for r in ranked_candidates:
            cand = r.candidate

            # Truncate overly long content (e.g., max 1500 chars per single candidate)
            truncated_content = cand.content[:1500]
            if len(cand.content) > 1500:
                truncated_content += "\n... [truncated]"

            candidate_section = (
                f"### [{cand.entity_type}] {cand.path}\n"
                f"- Entity: {cand.name} (Lines {cand.start_line}-{cand.end_line})\n"
                f"- Relevance Score: {r.score}\n"
                f"- Code / Evidence Snippet:\n"
                f"```\n{truncated_content}\n```\n"
            )

            # Check budget
            if current_chars + len(candidate_section) > char_budget and used_count >= 3:
                # Always allow at least 3 candidates even if tight
                break

            sections.append(candidate_section)
            current_chars += len(candidate_section)
            used_count += 1

            # Prepare structured evidence item
            evidence_items.append(
                {
                    "type": cand.entity_type.lower(),
                    "file": cand.path,
                    "symbol": cand.name if cand.entity_type in ("SYMBOL", "CHUNK") else None,
                    "lines": f"{cand.start_line}-{cand.end_line}",
                    "relevance": r.score,
                    "snippet": cand.content[:200],
                }
            )

            if cand.name and cand.name not in ("dependency", "import"):
                related_entities.add(cand.name)

        final_prompt_context = "\n".join(sections) if sections else "No specific code evidence retrieved for this query."

        return AssembledContext(
            prompt_context=final_prompt_context,
            evidence_items=evidence_items,
            related_entities=sorted(related_entities),
            total_characters=len(final_prompt_context),
            candidate_count=used_count,
        )
