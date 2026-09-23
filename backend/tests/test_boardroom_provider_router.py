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


def test_pilot_draft_uses_one_connected_provider_and_never_executes(monkeypatch) -> None:
    valid_content = (
        '{"position":"Subject: A lighter, modular carport for your project\\n\\nHello,\\n\\nCarbonCore combines a clean architectural finish with low-mass handling and modular repairability. This can make installation more practical for smaller crews while retaining reinforcement at selected high-load points. Would you like us to prepare a quotation for your site?\\n\\nKind regards,\\n[Name]",'
        '"recommendations":[],"risks":["Confirm final specification"],'
        '"missing_inputs":[],"plan_changes":["safe draft only; not sent"],"confidence":0.91}'
    )
    calls = []
    monkeypatch.setattr(router, "_provider_status", lambda: [
        {"id": "openai", "label": "OpenAI", "connected": True, "mode": "test", "model": "test-model"},
        {"id": "gemini", "label": "Gemini", "connected": True, "mode": "test", "model": "test-model"},
    ])

    def fake_call(provider_id, prompt):
        calls.append((provider_id, prompt))
        return {"content": valid_content, "model": "test-model", "latency_ms": 2}

    monkeypatch.setattr(router, "_call_connected_provider", fake_call)
    result = router.pilot_draft(router.PilotDraftRequest(
        business_id="home-fixed",
        request="write me a client email explaining the benefits",
        approved_facts=[{"claim_id": "fact-1", "text": "CarbonCore uses a hybrid aluminium and carbon composite frame."}],
        business_context={
            "business_name": "Home Fixed",
            "website_url": "www.homefixed.com",
            "sender_name": "Kevin Robinson",
            "sender_title": "Founder / Director",
            "ignored_secret": "must not enter the prompt",
        },
        requested_providers=["openai", "gemini"],
    ))
    assert result["status"] == "draft_ready"
    assert result["external_action_performed"] is False
    assert result["boundary"] == "draft_only_not_sent"
    assert result["approved_fact_count"] == 1
    assert result["business_context_fields_used"] == [
        "business_name",
        "sender_name",
        "sender_title",
        "website_url",
    ]
    assert result["receipt_hash"].startswith("sha256:")
    assert len(calls) == 1
    assert calls[0][0] == "openai"
    assert "hybrid aluminium and carbon composite frame" in calls[0][1]
    assert "Home Fixed" in calls[0][1]
    assert "Kevin Robinson" in calls[0][1]
    assert "Founder / Director" in calls[0][1]
    assert "ignored_secret" not in calls[0][1]
    assert "Do not replace a known identity value with a placeholder" in calls[0][1]
    assert "complete artifact" in calls[0][1]


def test_pilot_draft_rejects_schema_placeholder_as_a_finished_artifact(monkeypatch) -> None:
    monkeypatch.setattr(router, "_provider_status", lambda: [
        {"id": "openai", "label": "OpenAI", "connected": True, "mode": "test", "model": "test-model"},
    ])
    monkeypatch.setattr(router, "_call_connected_provider", lambda *_: {
        "content": '{"position":"complete finished draft","recommendations":[],"risks":[],"missing_inputs":[],"plan_changes":[],"confidence":0.5}',
        "model": "test-model",
        "latency_ms": 1,
    })

    result = router.pilot_draft(router.PilotDraftRequest(request="write a client email"))

    assert result["status"] == "failed"
    assert result["reason"] == "incomplete_pilot_draft_response"
    assert result["external_action_performed"] is False


def test_pilot_draft_fails_closed_without_a_connected_provider(monkeypatch) -> None:
    monkeypatch.setattr(router, "_provider_status", lambda: [
        {"id": "openai", "label": "OpenAI", "connected": False, "reason": "missing_api_key"},
    ])
    result = router.pilot_draft(router.PilotDraftRequest(request="write a client email"))
    assert result == {
        "schema_version": "aion.pilot_draft_result.v1",
        "status": "unavailable",
        "reason": "no_connected_drafting_provider",
        "external_action_performed": False,
    }


def test_quote_interview_extracts_only_validated_quote_fields_and_fails_over(monkeypatch) -> None:
    monkeypatch.setattr(router, "_provider_status", lambda: [
        {"id": "gemini", "label": "Gemini", "connected": True, "model": "test-gemini"},
        {"id": "openai", "label": "OpenAI", "connected": True, "model": "test-openai"},
    ])
    calls = []

    def fake_call(provider_id, prompt):
        calls.append(provider_id)
        if provider_id == "gemini":
            raise RuntimeError("temporary_provider_failure")
        assert "original customer enquiry is not supplied" in prompt
        return {
            "content": '{"scope_summary":"We propose to renew the flat roof.","scope_items":["Remove the existing roof covering","Supply and install a new felt roof system"],"exclusions":["Customer provides parking"],"duration":"2 days","charge_lines":[{"category":"labour","description":"Installation labour","quantity":2,"internal_unit_cost":150,"customer_unit_price":350,"person_name":"Kevin"}],"terms":"","next_stage":"evidence","quote_complete_requested":false}',
            "model": "test-openai", "latency_ms": 4,
        }

    monkeypatch.setattr(router, "_call_connected_provider", fake_call)
    result = router.quote_interview(router.QuoteInterviewRequest(
        business_id="home-fixed", stage="customer_charges", currency="GBP",
        user_turn="erm charge 350 per day for two days",
        current_draft={"scope": "Supply and install a felt flat roof."},
        requested_providers=["gemini", "openai"],
    ))

    assert calls == ["gemini", "openai"]
    assert result["status"] == "extracted"
    assert result["provider_id"] == "openai"
    assert result["external_action_performed"] is False
    assert result["extraction"]["charge_lines"][0] == {
        "category": "labour", "description": "Installation labour", "quantity": 2.0,
        "internal_unit_cost": 150.0, "customer_unit_price": 350.0, "person_name": "Kevin",
    }
    assert result["extraction"]["scope_items"] == [
        "Remove the existing roof covering", "Supply and install a new felt roof system",
    ]
    assert len(result["receipt_hash"]) == 64


def test_quote_interview_rejects_invalid_or_negative_financial_output(monkeypatch) -> None:
    monkeypatch.setattr(router, "_provider_status", lambda: [
        {"id": "gemini", "label": "Gemini", "connected": True, "model": "test"},
    ])
    monkeypatch.setattr(router, "_call_connected_provider", lambda *_: {
        "content": '{"scope_summary":"","scope_items":[],"exclusions":[],"duration":"","charge_lines":[{"category":"labour","description":"Labour","quantity":1,"internal_unit_cost":-50,"customer_unit_price":100,"person_name":""}],"terms":"","next_stage":"review","quote_complete_requested":false}',
    })
    result = router.quote_interview(router.QuoteInterviewRequest(user_turn="labour costs minus fifty"))
    assert result["status"] == "unavailable"
    assert result["external_action_performed"] is False
    assert result["attempts"][0]["reason"] == "invalid_quote_interview_internal_unit_cost"
