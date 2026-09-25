import logging

from apps.api.src.config.settings import settings
from apps.api.src.services.llm.base import LLMProvider
from apps.api.src.services.llm.claude import ClaudeProvider
from apps.api.src.services.llm.groq import GroqProvider

logger = logging.getLogger("unotusk-llm-factory")


def get_llm_provider(provider: str | None = None) -> LLMProvider:
    """
    Returns configured LLM provider explicitly based on settings.LLM_PROVIDER
    or explicit provider parameter.
    Supported: 'groq', 'claude' (or 'anthropic'), 'offline'.
    Raises ValueError for unsupported providers.
    """
    provider_name = (provider or settings.LLM_PROVIDER or "offline").strip().lower()

    if provider_name == "groq":
        return GroqProvider()
    elif provider_name in ("claude", "anthropic"):
        return ClaudeProvider()
    elif provider_name == "offline":
        return ClaudeProvider(api_key="")
    else:
        logger.error(f"Unsupported LLM provider: '{provider_name}'")
        raise ValueError(
            f"Unsupported LLM provider: '{provider_name}'. "
            f"Supported providers are: 'groq', 'claude' (or 'anthropic'), 'offline'."
        )


def get_report_synthesizer(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
):
    """
    Returns configured ReportSynthesizer based on settings.LLM_PROVIDER
    or explicit provider parameter.
    Supported: 'groq', 'claude', 'anthropic', 'offline'.
    """
    from apps.api.src.services.report_engine.synthesizer import (
        get_report_synthesizer as _get_synth,
    )

    return _get_synth(provider=provider, api_key=api_key, model=model)
