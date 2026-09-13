import logging

from apps.api.src.config.settings import settings
from apps.api.src.services.llm.base import LLMProvider
from apps.api.src.services.llm.claude import ClaudeProvider
from apps.api.src.services.llm.groq import GroqProvider

logger = logging.getLogger("unotusk-llm-factory")


def get_llm_provider() -> LLMProvider:
    """
    Returns configured LLM provider explicitly based on settings.LLM_PROVIDER.
    Supported: 'groq', 'claude', 'offline'.
    """
    provider_name = (settings.LLM_PROVIDER or "offline").lower()

    if provider_name == "groq":
        return GroqProvider()
    elif provider_name == "claude":
        return ClaudeProvider()
    else:
        # Default to ClaudeProvider with offline fallback or GroqProvider with offline fallback
        return ClaudeProvider()
