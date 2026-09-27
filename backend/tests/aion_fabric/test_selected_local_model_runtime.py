from backend.services.aion_mission_mode.pilot_local_model_runtime import (
    OPENAI_COMPATIBLE_BOUNDED_CHAT_ADAPTER,
    run_selected_local_chat,
    selected_local_runtime_profile,
)


def test_selected_local_runtime_uses_vault_model_identity_and_profile_options():
    captured = {}

    def transport(endpoint, body, timeout):
        captured.update({"endpoint": endpoint, "body": body, "timeout": timeout})
        return {"choices": [{"message": {"content": '{"answer":"ok"}'}}]}

    profile = selected_local_runtime_profile(
        model_id="another-accepted-local-model",
        adapter=OPENAI_COMPATIBLE_BOUNDED_CHAT_ADAPTER,
        endpoint="http://127.0.0.1:9911",
        model_sha256="b" * 64,
        finance_arithmetic="verified_tessaris_tools_required",
        chat_template_kwargs={"enable_thinking": False},
        max_output_tokens=256,
        context_size=4096,
        parallel_slots=1,
    )
    result = run_selected_local_chat(
        prompt="Return a bounded proposal", runtime_profile=profile, transport=transport,
    )

    assert captured["body"]["model"] == "another-accepted-local-model"
    assert captured["body"]["max_tokens"] == 256
    assert captured["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert profile["context_size"] == 4096
    assert profile["parallel_slots"] == 1
    assert result["model"] == "another-accepted-local-model"
