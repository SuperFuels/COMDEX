from __future__ import annotations

from backend.modules.aion_business.runtime.retell_homefixed_agent import (
    HOMEFIXED_GENERAL_PROMPT,
    RetellAdminClient,
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
    assert "{{call_goal_contract}}" in HOMEFIXED_GENERAL_PROMPT
    assert "{{customer_name}}" in HOMEFIXED_GENERAL_PROMPT
    assert "{{enquiry_reason}}" in HOMEFIXED_GENERAL_PROMPT
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
    assert all(isinstance(value, str) for value in payload["default_dynamic_variables"].values())


def test_homefixed_voice_agent_is_bilingual_private_and_not_live_call_configuration():
    payload = build_voice_agent_payload("llm-test")
    assert payload["response_engine"]["llm_id"] == "llm-test"
    assert payload["language"] == ["en-GB", "es-ES"]
    assert payload["is_public"] is False
    assert "webhook_url" not in payload
    assert "phone_number" not in payload


def test_retell_admin_updates_exact_llm_version_before_agent_publish(monkeypatch):
    client = object.__new__(RetellAdminClient)
    calls = []
    monkeypatch.setattr(client, "request", lambda method, path, payload=None: (
        calls.append((method, path, payload)) or {"version": 4}
    ))

    client.update_llm("llm-test")
    client.update_agent_response_engine("agent-test", "llm-test", 4)

    assert calls[0][0:2] == ("PATCH", "/update-retell-llm/llm-test")
    assert "{{call_goal_contract}}" in calls[0][2]["general_prompt"]
    assert calls[1] == (
        "PATCH",
        "/update-agent/agent-test",
        {"response_engine": {"type": "retell-llm", "llm_id": "llm-test", "version": 4}},
    )
