from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GroundedAnswer:
    content: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
    confidence: str = "HIGH"
    debug_signals: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    @abstractmethod
    async def generate_grounded_answer(
        self,
        question: str,
        project_context: str,
        evidence_items: list[dict[str, Any]],
        related_entities: list[str],
        conversation_history: list[dict[str, str]] | None = None,
        thinking_tier: str | None = None,
    ) -> GroundedAnswer: ...

    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Generate a JSON response for structured extraction tasks."""
        ...


MIN_GROUNDED_SYNTHESIS_THRESHOLD: float = 0.20


def extract_customer_notes(project_context: str) -> list[str]:
    """
    Extracts structured customer project knowledge blocks from prompt context.
    Customer knowledge represents explicit user-taught domain context and constraints.
    """
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
                        content_txt = (
                            content_lines[0].replace("Content:", "").strip()
                            if content_lines
                            else ""
                        )
                        customer_notes.append(f"- **[CUSTOMER: {header}]**: {content_txt}")
        except Exception:
            pass

    return customer_notes


def should_abstain_due_to_insufficient_evidence(
    evidence_items: list[dict[str, Any]],
    customer_notes: list[str],
    threshold: float = MIN_GROUNDED_SYNTHESIS_THRESHOLD,
) -> tuple[bool, float]:
    """
    Evaluates the Architecture V1 Low-Confidence Synthesis Gate.
    Returns (should_abstain, max_relevance).

    Abstention triggers to prevent hallucination when:
    1. No customer project knowledge is available, AND
    2. Either evidence_items is empty OR the maximum candidate relevance is below threshold (< 0.20).
    """
    max_rel = max((float(e.get("relevance", 0.0)) for e in evidence_items), default=0.0)
    if customer_notes:
        return False, max_rel
    if not evidence_items or max_rel < threshold:
        return True, max_rel
    return False, max_rel


def format_insufficient_evidence_response(
    question: str,
    max_relevance: float,
    threshold: float = MIN_GROUNDED_SYNTHESIS_THRESHOLD,
) -> str:
    """
    Formats an explicit, safe insufficient-evidence response preventing unsupported factual claims.
    """
    if max_relevance > 0.0:
        detail = (
            f"The retrieved candidate components do not meet the minimum grounding threshold "
            f"(max relevance {max_relevance:.2f} < {threshold:.2f}) required to formulate a factual answer."
        )
    else:
        detail = "No matching files, symbols, or dependencies were found in the current repository snapshot."

    return (
        f"### Insufficient Evidence\n\n"
        f"I searched the repository and indexed project context for references to **'{question}'**, "
        f"but did not find sufficient grounded code evidence or architectural specifications.\n\n"
        f"{detail}\n\n"
        f"**Note**: If this component was recently added or modified, please ensure the repository is fully indexed."
    )
