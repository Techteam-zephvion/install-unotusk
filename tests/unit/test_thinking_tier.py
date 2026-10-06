from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from apps.api.src.config.settings import settings
from apps.api.src.schemas.intelligence import GroundedAskRequest
from apps.api.src.services.llm.base import GroundedAnswer, LLMProvider
from apps.api.src.services.llm.claude import ClaudeProvider
from apps.api.src.services.llm.factory import get_llm_provider
from apps.api.src.services.llm.groq import GroqProvider
from apps.api.src.services.llm.thinking_policy import (
    ThinkingTier,
    get_thinking_policy,
    get_thinking_tier,
)


def test_thinking_tier_enum_and_validation():
    # hot accepted
    assert get_thinking_tier("hot") == ThinkingTier.HOT
    assert get_thinking_tier("HOT") == ThinkingTier.HOT
    assert get_thinking_tier(ThinkingTier.HOT) == ThinkingTier.HOT

    # warm accepted
    assert get_thinking_tier("warm") == ThinkingTier.WARM
    assert get_thinking_tier(" WARM ") == ThinkingTier.WARM
    assert get_thinking_tier(ThinkingTier.WARM) == ThinkingTier.WARM

    # cold accepted
    assert get_thinking_tier("cold") == ThinkingTier.COLD
    assert get_thinking_tier("Cold") == ThinkingTier.COLD
    assert get_thinking_tier(ThinkingTier.COLD) == ThinkingTier.COLD

    # missing/None tier uses default (warm)
    assert get_thinking_tier(None) == ThinkingTier.WARM
    assert get_thinking_tier("") == ThinkingTier.WARM

    # invalid tier rejected
    with pytest.raises(ValueError, match="Invalid thinking tier"):
        get_thinking_tier("blazing")

    with pytest.raises(ValueError, match="Invalid thinking tier"):
        get_thinking_tier("freezing")


def test_thinking_policy_mapping():
    # hot maps to lowest reasoning policy
    hot_policy = get_thinking_policy("hot")
    assert hot_policy.tier == ThinkingTier.HOT
    assert hot_policy.groq_reasoning_effort == "low"
    assert hot_policy.groq_reasoning_format == "parsed"
    assert hot_policy.anthropic_thinking is None
    assert "FAST RESPONSE MODE" in hot_policy.system_directive

    # warm maps to balanced policy
    warm_policy = get_thinking_policy("warm")
    assert warm_policy.tier == ThinkingTier.WARM
    assert warm_policy.groq_reasoning_effort == "medium"
    assert warm_policy.groq_reasoning_format == "parsed"
    assert warm_policy.anthropic_thinking == {"type": "enabled", "budget_tokens": 2048}
    assert "BALANCED MODE" in warm_policy.system_directive

    # cold maps to highest reasoning policy
    cold_policy = get_thinking_policy("cold")
    assert cold_policy.tier == ThinkingTier.COLD
    assert cold_policy.groq_reasoning_effort == "high"
    assert cold_policy.groq_reasoning_format == "parsed"
    assert cold_policy.anthropic_thinking == {"type": "enabled", "budget_tokens": 4096}
    assert "DEEP REASONING MODE" in cold_policy.system_directive

    # missing tier defaults to warm policy
    default_policy = get_thinking_policy(None)
    assert default_policy.tier == ThinkingTier.WARM
    assert default_policy.groq_reasoning_effort == "medium"


def test_grounded_ask_request_schema():
    # hot, warm, cold accepted
    req_hot = GroundedAskRequest(question="What is the auth flow?", thinking_tier="hot")
    assert req_hot.thinking_tier == "hot"

    req_warm = GroundedAskRequest(question="What is the auth flow?", thinking_tier="warm")
    assert req_warm.thinking_tier == "warm"

    req_cold = GroundedAskRequest(question="What is the auth flow?", thinking_tier="cold")
    assert req_cold.thinking_tier == "cold"

    # missing tier uses default "warm"
    req_default = GroundedAskRequest(question="What is the auth flow?")
    assert req_default.thinking_tier == "warm"

    # None tier defaults to "warm"
    req_none = GroundedAskRequest(question="What is the auth flow?", thinking_tier=None)
    assert req_none.thinking_tier == "warm"

    # invalid tier rejected by validator
    with pytest.raises(ValidationError) as exc_info:
        GroundedAskRequest(question="What is the auth flow?", thinking_tier="super_deep")
    assert "Invalid thinking_tier" in str(exc_info.value)


@pytest.mark.asyncio
async def test_groq_provider_actual_request_configurations():
    """Verify that Groq provider passes distinct reasoning arguments for Hot, Warm, Cold."""
    provider = GroqProvider(api_key="mock-groq-key", model="qwen/qwen3.8-27b")
    mock_client = MagicMock()
    mock_completions = AsyncMock()

    # Setup mock response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Answer with reasoning"
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_completions.create = AsyncMock(return_value=mock_response)
    mock_client.chat.completions = mock_completions
    provider._client = mock_client

    evidence = [{"type": "file", "file": "src/auth.py", "lines": "1-10", "relevance": 0.9}]

    # 1. HOT request check
    answer_hot = await provider.generate_grounded_answer(
        question="How does auth work?",
        project_context="src/auth.py code",
        evidence_items=evidence,
        related_entities=["auth"],
        thinking_tier="hot",
    )
    assert mock_completions.create.call_count == 1
    hot_call_kwargs = mock_completions.create.call_args.kwargs
    assert hot_call_kwargs["reasoning_effort"] == "low"
    assert hot_call_kwargs["reasoning_format"] == "parsed"
    assert "FAST RESPONSE MODE" in hot_call_kwargs["messages"][0]["content"]
    assert answer_hot.debug_signals["thinking_tier"] == "hot"
    assert answer_hot.debug_signals["reasoning_effort"] == "low"

    # 2. WARM request check
    mock_completions.create.reset_mock()
    answer_warm = await provider.generate_grounded_answer(
        question="How does auth work?",
        project_context="src/auth.py code",
        evidence_items=evidence,
        related_entities=["auth"],
        thinking_tier="warm",
    )
    assert mock_completions.create.call_count == 1
    warm_call_kwargs = mock_completions.create.call_args.kwargs
    assert warm_call_kwargs["reasoning_effort"] == "medium"
    assert warm_call_kwargs["reasoning_format"] == "parsed"
    assert "BALANCED MODE" in warm_call_kwargs["messages"][0]["content"]
    assert answer_warm.debug_signals["thinking_tier"] == "warm"
    assert answer_warm.debug_signals["reasoning_effort"] == "medium"

    # 3. COLD request check
    mock_completions.create.reset_mock()
    answer_cold = await provider.generate_grounded_answer(
        question="How does auth work?",
        project_context="src/auth.py code",
        evidence_items=evidence,
        related_entities=["auth"],
        thinking_tier="cold",
    )
    assert mock_completions.create.call_count == 1
    cold_call_kwargs = mock_completions.create.call_args.kwargs
    assert cold_call_kwargs["reasoning_effort"] == "high"
    assert cold_call_kwargs["reasoning_format"] == "parsed"
    assert "DEEP REASONING MODE" in cold_call_kwargs["messages"][0]["content"]
    assert answer_cold.debug_signals["thinking_tier"] == "cold"
    assert answer_cold.debug_signals["reasoning_effort"] == "high"

    # PROOF: All 3 tiers produced demonstrably different reasoning_effort arguments
    assert hot_call_kwargs["reasoning_effort"] != warm_call_kwargs["reasoning_effort"]
    assert warm_call_kwargs["reasoning_effort"] != cold_call_kwargs["reasoning_effort"]
    assert hot_call_kwargs["reasoning_effort"] != cold_call_kwargs["reasoning_effort"]


@pytest.mark.asyncio
async def test_claude_provider_native_thinking_model():
    """Verify that Claude provider uses native thinking parameters when model supports it."""
    provider = ClaudeProvider(api_key="mock-key", model="claude-3-7-sonnet-20250219")
    mock_client = MagicMock()
    mock_messages = AsyncMock()

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Claude reasoning answer")]
    mock_messages.create = AsyncMock(return_value=mock_resp)
    mock_client.messages = mock_messages
    provider._client = mock_client

    evidence = [{"type": "file", "file": "src/core.py", "lines": "10-20", "relevance": 0.85}]

    # HOT: Thinking disabled
    await provider.generate_grounded_answer(
        question="Explain core architecture",
        project_context="core.py context",
        evidence_items=evidence,
        related_entities=["core"],
        thinking_tier="hot",
    )
    hot_kwargs = mock_messages.create.call_args.kwargs
    assert hot_kwargs["thinking"] == {"type": "disabled"}

    # WARM: Thinking enabled with 2048 budget
    mock_messages.create.reset_mock()
    await provider.generate_grounded_answer(
        question="Explain core architecture",
        project_context="core.py context",
        evidence_items=evidence,
        related_entities=["core"],
        thinking_tier="warm",
    )
    warm_kwargs = mock_messages.create.call_args.kwargs
    assert warm_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 2048}
    assert warm_kwargs["temperature"] == 1.0

    # COLD: Thinking enabled with 4096 budget
    mock_messages.create.reset_mock()
    await provider.generate_grounded_answer(
        question="Explain core architecture",
        project_context="core.py context",
        evidence_items=evidence,
        related_entities=["core"],
        thinking_tier="cold",
    )
    cold_kwargs = mock_messages.create.call_args.kwargs
    assert cold_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 4096}
    assert cold_kwargs["temperature"] == 1.0

    # Compare: Hot, Warm, Cold all result in different configurations
    assert hot_kwargs["thinking"] != warm_kwargs["thinking"]
    assert warm_kwargs["thinking"] != cold_kwargs["thinking"]


@pytest.mark.asyncio
async def test_claude_provider_prompt_guided_model():
    """Verify that Claude provider falls back to token budgets & system directives for models without native thinking."""
    provider = ClaudeProvider(api_key="mock-key", model="claude-3-5-sonnet-20241022")
    mock_client = MagicMock()
    mock_messages = AsyncMock()

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Sonnet 3.5 answer")]
    mock_messages.create = AsyncMock(return_value=mock_resp)
    mock_client.messages = mock_messages
    provider._client = mock_client

    evidence = [{"type": "file", "file": "src/core.py", "lines": "10-20", "relevance": 0.85}]

    # HOT: 1024 max tokens + FAST RESPONSE directive
    await provider.generate_grounded_answer(
        question="Explain core architecture",
        project_context="core.py context",
        evidence_items=evidence,
        related_entities=["core"],
        thinking_tier="hot",
    )
    hot_kwargs = mock_messages.create.call_args.kwargs
    assert "thinking" not in hot_kwargs  # Unsupported parameter not sent
    assert hot_kwargs["max_tokens"] == 1024
    assert "FAST RESPONSE MODE" in hot_kwargs["system"]

    # WARM: 2048 max tokens + BALANCED directive
    mock_messages.create.reset_mock()
    await provider.generate_grounded_answer(
        question="Explain core architecture",
        project_context="core.py context",
        evidence_items=evidence,
        related_entities=["core"],
        thinking_tier="warm",
    )
    warm_kwargs = mock_messages.create.call_args.kwargs
    assert "thinking" not in warm_kwargs
    assert warm_kwargs["max_tokens"] == 2048
    assert "BALANCED MODE" in warm_kwargs["system"]

    # COLD: 4096 max tokens + DEEP REASONING directive
    mock_messages.create.reset_mock()
    await provider.generate_grounded_answer(
        question="Explain core architecture",
        project_context="core.py context",
        evidence_items=evidence,
        related_entities=["core"],
        thinking_tier="cold",
    )
    cold_kwargs = mock_messages.create.call_args.kwargs
    assert "thinking" not in cold_kwargs
    assert cold_kwargs["max_tokens"] == 4096
    assert "DEEP REASONING MODE" in cold_kwargs["system"]


@pytest.mark.asyncio
async def test_offline_synthesis_differentiation():
    """Verify offline synthesizer returns distinct answer structures for Hot, Warm, Cold."""
    groq_offline = GroqProvider(api_key=None)
    evidence = [
        {"type": "symbol", "file": "src/auth.py", "symbol": "login", "lines": "10-25", "relevance": 0.9}
    ]

    hot_ans = await groq_offline.generate_grounded_answer(
        question="How does login work?",
        project_context="### [SYMBOL] src/auth.py\ndef login(): pass",
        evidence_items=evidence,
        related_entities=["login"],
        thinking_tier="hot",
    )
    assert hot_ans.debug_signals["thinking_tier"] == "hot"
    assert "Quick Summary" in hot_ans.content

    cold_ans = await groq_offline.generate_grounded_answer(
        question="How does login work?",
        project_context="### [SYMBOL] src/auth.py\ndef login(): pass",
        evidence_items=evidence,
        related_entities=["login"],
        thinking_tier="cold",
    )
    assert cold_ans.debug_signals["thinking_tier"] == "cold"
    assert "Deep Architectural Reasoning" in cold_ans.content
    assert len(cold_ans.content) > len(hot_ans.content)


def test_provider_routing_remains_correct(monkeypatch):
    """Verify that settings.LLM_PROVIDER routing is preserved and remains functional."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
    p1 = get_llm_provider()
    assert isinstance(p1, GroqProvider)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "claude")
    p2 = get_llm_provider()
    assert isinstance(p2, ClaudeProvider)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
    p3 = get_llm_provider()
    assert isinstance(p3, ClaudeProvider)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "offline")
    p4 = get_llm_provider()
    assert isinstance(p4, ClaudeProvider)
    assert not p4.api_key


@pytest.mark.asyncio
async def test_context_engine_forwards_thinking_tier():
    """Verify that ProjectContextEngine forwards the thinking_tier to the LLM provider without dropping or modifying it."""
    from apps.api.src.services.context_engine.engine import ProjectContextEngine

    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.generate_grounded_answer = AsyncMock(
        return_value=GroundedAnswer(
            content="Grounded test answer",
            evidence=[],
            related_entities=[],
            confidence="HIGH",
            debug_signals={"thinking_tier": "cold"},
        )
    )

    engine = ProjectContextEngine(llm_provider=mock_provider)

    mock_session = AsyncMock()

    # Mock MultiSignalRetriever and other steps
    from unittest.mock import patch
    with patch("apps.api.src.services.context_engine.retriever.MultiSignalRetriever.retrieve_candidates", new_callable=AsyncMock) as mock_retriever, \
         patch("apps.api.src.services.context_engine.graph_expander.RelationshipExpander.expand_candidates", new_callable=AsyncMock) as mock_expander, \
         patch("apps.api.src.services.context_engine.ranker.MultiSignalRanker.rank_candidates") as mock_ranker, \
         patch("apps.api.src.services.context_engine.assembler.ContextAssembler.assemble_context") as mock_assembler, \
         patch("apps.api.src.services.context_engine.knowledge_retriever.KnowledgeRetriever.retrieve_project_knowledge", new_callable=AsyncMock) as mock_knowledge:

        mock_retriever.return_value = []
        mock_expander.return_value = []
        mock_ranker.return_value = []
        mock_assembled = MagicMock()
        mock_assembled.prompt_context = "test context"
        mock_assembled.evidence_items = []
        mock_assembled.related_entities = []
        mock_assembler.return_value = mock_assembled
        mock_knowledge.return_value = ("", [])

        import uuid
        test_snap_id = uuid.uuid4()
        test_proj_id = uuid.uuid4()

        res = await engine.investigate(
            session=mock_session,
            snapshot_id=test_snap_id,
            question="What is the architecture?",
            project_id=test_proj_id,
            thinking_tier="cold",
        )

        assert mock_provider.generate_grounded_answer.call_count == 1
        call_kwargs = mock_provider.generate_grounded_answer.call_args.kwargs
        assert call_kwargs["thinking_tier"] == "cold"
        assert res.debug_signals["thinking_tier"] == "cold"

