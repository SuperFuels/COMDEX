from __future__ import annotations

from backend.api import boardroom_provider_router as router


def test_provider_registry_exposes_main_suite_and_task_capabilities(monkeypatch) -> None:
    monkeypatch.setattr(router, "_ollama_status", lambda: {
        "id": "gemma", "label": "Gemma", "connected": False, "reason": "not_loaded",
    })
    monkeypatch.setattr(router, "get_ai_provider_public_record", lambda provider: {
        "id": provider, "label": provider.title(), "connected": False, "reason": "missing_api_key",
    })
    records = {item["id"]: item for item in router._provider_status()}
    assert set(records) == {"gemma", "openai", "claude", "gemini", "grok", "kimi", "meta", "mistral", "deepseek"}
    assert records["deepseek"]["capabilities"] == {"boardroom": True, "receipt_vision": False}
    assert records["mistral"]["capabilities"]["receipt_vision"] is True


def test_all_connected_mainstream_providers_can_be_board_members(monkeypatch) -> None:
    providers = ["gemma", "openai", "claude", "gemini", "grok", "kimi", "meta", "mistral", "deepseek"]
    valid_content = (
        '{"position":"Ready","recommendations":["Continue"],"risks":["None observed"],'
        '"missing_inputs":["None"],"plan_changes":["No change"],"confidence":0.9}'
    )
    monkeypatch.setattr(router, "_provider_status", lambda: [
        {"id": item, "label": item.title(), "connected": True, "mode": "test", "model": f"{item}-model"}
        for item in providers
    ])
    monkeypatch.setattr(router, "_call_ollama", lambda prompt: {"content": valid_content, "model": "gemma-model", "latency_ms": 1})
    monkeypatch.setattr(router, "_call_gemini", lambda prompt: {"content": valid_content, "model": "gemini-model", "latency_ms": 1})
    monkeypatch.setattr(router, "_call_claude", lambda prompt: {"content": valid_content, "model": "claude-model", "latency_ms": 1})
    monkeypatch.setattr(router, "_call_meta", lambda prompt: {"content": valid_content, "model": "meta-model", "latency_ms": 1})
    monkeypatch.setattr(router, "_call_openai_compatible", lambda provider, prompt: {"content": valid_content, "model": f"{provider}-model", "latency_ms": 1})
    result = router.boardroom_ask(router.BoardroomAskRequest(requested_providers=providers))
    assert result["succeeded_count"] == 9
    assert not result["missing_or_unavailable"]


def test_openai_compatible_board_member_uses_provider_specific_endpoint(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr(router, "get_ai_provider_secret", lambda provider: "key")
    monkeypatch.setattr(router, "get_ai_provider_model", lambda provider: f"{provider}-model")

    def fake_http(url, payload=None, headers=None, timeout=60):
        captured.update(url=url, payload=payload, headers=headers)
        return {"choices": [{"message": {"content": '{"position":"ok"}'}}]}

    monkeypatch.setattr(router, "_http_json", fake_http)
    result = router._call_openai_compatible("deepseek", "Board prompt")
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert result["model"] == "deepseek-model"


def test_meta_and_claude_use_their_native_structured_routes(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(router, "get_ai_provider_secret", lambda provider: "key")
    monkeypatch.setattr(router, "get_ai_provider_model", lambda provider: f"{provider}-model")

    def fake_http(url, payload=None, headers=None, timeout=60):
        calls.append((url, payload))
        if "anthropic" in url:
            return {"content": [{"type": "text", "text": "{}"}]}
        return {"output": [{"type": "message", "content": [{"type": "output_text", "text": "{}"}]}]}

    monkeypatch.setattr(router, "_http_json", fake_http)
    assert router._call_claude("Board prompt")["model"] == "claude-model"
    assert router._call_meta("Board prompt")["model"] == "meta-model"
    assert calls[0][0] == "https://api.anthropic.com/v1/messages"
    assert calls[1][0] == "https://api.meta.ai/v1/responses"


def test_board_prompt_compacts_canonical_context_without_dropping_late_authority_evidence() -> None:
    huge_facts = [
        {"field": f"external_data.row_{index}", "value": index, "verification_status": "source_backed"}
        for index in range(500)
    ]
    canonical = {
        "business_id": "home-fixed",
        "persistent_truth_source": "business_containers",
        "business_identity": {"trading_name": "Home Fixed", "business_type": "service_business"},
        "business_map_projection": {"revision": 15, "facts": huge_facts},
        "function_models": {
            "finance": {
                "model_status": "complete",
                "authoritative_metrics": {"operating_expenses": {"value": 82670, "verification": "source_backed"}},
                "financial_statements": {
                    "profit_and_loss": {"lines": [{"key": "overheads", "value": 82670, "verification": "source_backed"}]}
                },
            }
        },
        "department_intelligence": {
            "finance": {"status": "complete", "boardroom_summary": "Finance discovery 5/5; status complete."},
            "operations": {"status": "ready_to_activate"},
            "hr": {"status": "authority_ready"},
        },
        "source_revisions": {"business_map": 15, "finance": 377},
    }
    request = router.BoardroomAskRequest(
        requested_providers=["gemini"],
        context_packet={"canonical_context_envelope": canonical},
    )

    prompt = router._board_prompt(request, "Gemini")

    assert '"operating_expenses"' in prompt
    assert "82670" in prompt
    assert '"ready_to_activate"' in prompt
    assert '"authority_ready"' in prompt
    assert "external_data.row_499" not in prompt
