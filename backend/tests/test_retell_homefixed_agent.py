from __future__ import annotations

from backend.modules.aion_business.runtime.retell_homefixed_agent import (
    HOMEFIXED_GENERAL_PROMPT,
    build_retell_llm_payload,
    build_voice_agent_payload,
)


def test_homefixed_prompt_has_identity_and_authority_boundaries():
    prompt = HOMEFIXED_GENERAL_PROMPT.lower()
    assert "ai assistant" in prompt
    assert "cannot confirm a price" in prompt
    assert "cannot take payment-card details" in prompt
    assert "person will review" in prompt
    assert "emergency service" in prompt
    assert "ignore these rules" in prompt
    assert "call_goal_contract" in prompt
    assert "never silently guess" in prompt
    assert "do not ask a caller to dictate a long email address" in prompt


def test_homefixed_llm_uses_bounded_sales_states():
    payload = build_retell_llm_payload()
    assert payload["start_speaker"] == "agent"
    assert "AI assistant" in payload["begin_message"]
    assert payload["model_temperature"] <= 0.2
    assert [state["name"] for state in payload["states"]] == [
        "discovery", "qualification", "close_or_handoff"
    ]
    assert payload["starting_state"] == "discovery"
    assert {tool["type"] for tool in payload["general_tools"]} == {"end_call"}
    assert "call_goal_contract" in payload["default_dynamic_variables"]


def test_homefixed_voice_agent_is_bilingual_private_and_not_live_call_configuration():
    payload = build_voice_agent_payload("llm-test")
    assert payload["response_engine"]["llm_id"] == "llm-test"
    assert payload["language"] == ["en-GB", "es-ES"]
    assert payload["is_public"] is False
    assert "webhook_url" not in payload
    assert "phone_number" not in payload
