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
    ) -> GroundedAnswer:
        pass
