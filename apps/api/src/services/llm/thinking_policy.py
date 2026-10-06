from dataclasses import dataclass
from enum import Enum
from typing import Any


class ThinkingTier(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


@dataclass(frozen=True)
class ThinkingPolicy:
    tier: ThinkingTier
    # Groq native reasoning controls
    groq_reasoning_effort: str  # "low", "medium", "high"
    groq_reasoning_format: str  # "parsed"
    # Anthropic native extended thinking controls
    anthropic_thinking: dict[str, Any] | None
    anthropic_max_tokens: int
    # Provider-agnostic system directive for reasoning depth
    system_directive: str


# System reasoning directives tailored to thinking tiers
HOT_DIRECTIVE = (
    "THINKING TIER: HOT (FAST RESPONSE MODE)\n"
    "Prioritize maximum response speed and conciseness. "
    "Execute minimal, rapid reasoning. Provide an immediate, direct factual answer "
    "grounded strictly in the primary evidence, without elaborate multi-step commentary."
)

WARM_DIRECTIVE = (
    "THINKING TIER: WARM (BALANCED MODE)\n"
    "Execute balanced reasoning. Systematically analyze the repository evidence, "
    "code symbols, and architectural context. Provide a well-structured, clear explanation "
    "with standard detail and grounded citations."
)

COLD_DIRECTIVE = (
    "THINKING TIER: COLD (DEEP REASONING MODE)\n"
    "Execute exhaustive, deep architectural reasoning. Thoroughly investigate cross-module "
    "dependencies, transitive call graphs, potential edge cases, trade-offs, and historical decisions. "
    "Rigourously verify all evidence and provide a comprehensive, multi-angle analytical breakdown."
)

_POLICIES: dict[ThinkingTier, ThinkingPolicy] = {
    ThinkingTier.HOT: ThinkingPolicy(
        tier=ThinkingTier.HOT,
        groq_reasoning_effort="low",
        groq_reasoning_format="parsed",
        anthropic_thinking=None,  # Disabled for fastest response
        anthropic_max_tokens=1500,
        system_directive=HOT_DIRECTIVE,
    ),
    ThinkingTier.WARM: ThinkingPolicy(
        tier=ThinkingTier.WARM,
        groq_reasoning_effort="medium",
        groq_reasoning_format="parsed",
        anthropic_thinking={"type": "enabled", "budget_tokens": 2048},
        anthropic_max_tokens=4096,
        system_directive=WARM_DIRECTIVE,
    ),
    ThinkingTier.COLD: ThinkingPolicy(
        tier=ThinkingTier.COLD,
        groq_reasoning_effort="high",
        groq_reasoning_format="parsed",
        anthropic_thinking={"type": "enabled", "budget_tokens": 4096},
        anthropic_max_tokens=8192,
        system_directive=COLD_DIRECTIVE,
    ),
}


def get_thinking_tier(val: str | ThinkingTier | None) -> ThinkingTier:
    """
    Parses and validates a thinking tier.
    Defaults to ThinkingTier.WARM if None or empty.
    Raises ValueError for invalid tiers.
    """
    if val is None:
        return ThinkingTier.WARM
    if isinstance(val, ThinkingTier):
        return val

    val_str = str(val).strip().lower()
    if not val_str:
        return ThinkingTier.WARM

    try:
        return ThinkingTier(val_str)
    except ValueError:
        raise ValueError(
            f"Invalid thinking tier: '{val}'. Supported tiers are: 'hot', 'warm', 'cold'."
        ) from None


def get_thinking_policy(tier: str | ThinkingTier | None) -> ThinkingPolicy:
    """
    Returns the centralized ThinkingPolicy for the specified tier.
    Defaults to WARM policy if tier is None.
    """
    validated_tier = get_thinking_tier(tier)
    return _POLICIES[validated_tier]
