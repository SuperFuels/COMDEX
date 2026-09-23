import pytest

from backend.services.aion_mission_mode.pilot_local_model_runtime import (
    LocalModelRuntimeError,
    gpt_oss_local_runtime_profile,
    run_gpt_oss_harness_locally,
)
from backend.services.aion_mission_mode.pilot_model_harness import build_gpt_oss_private_reasoning_request


def contract():
    return build_gpt_oss_private_reasoning_request(pilot_request={
        "business_id": "home-fixed", "mission_id": "support", "mission_run_id": "run_1",
        "pilot_id": "support", "task_id": "case_1", "task": "Prepare a grounded draft.",
        "verified_business_facts": [{"source_id": "case_1", "status": "open"}],
        "output_schema": {"type": "object", "required": ["summary"]},
        "allowed_tools": ["retrieve_business_facts", "prepare_business_draft"],
    })


def test_loopback_runtime_returns_proposal_and_receipt_without_execution():
    profile = gpt_oss_local_runtime_profile(
        endpoint="http://127.0.0.1:8080", model_sha256="a" * 64,
    )
    observed = {}

    def fake_transport(endpoint, request, timeout):
        observed.update({"endpoint": endpoint, "request": request, "timeout": timeout})
        return {"choices": [{"message": {"content": '<|return|>{"summary":"Draft ready."}<|end|>'}}]}

    result = run_gpt_oss_harness_locally(contract=contract(), runtime_profile=profile, transport=fake_transport)
    assert observed["endpoint"] == "http://127.0.0.1:8080"
    assert observed["request"]["messages"][0]["role"] == "developer"
    assert result["event"]["proposal"]["event_type"] == "final_proposal"
    assert result["receipt"]["tool_executed"] is False
    assert result["memory_mutated"] is False


def test_runtime_rejects_network_endpoint_and_fallback():
    with pytest.raises(LocalModelRuntimeError, match="loopback"):
        gpt_oss_local_runtime_profile(endpoint="https://example.com", model_sha256="a" * 64)

    profile = gpt_oss_local_runtime_profile(endpoint="http://localhost:8080", model_sha256="a" * 64)
    profile["allow_network_fallback"] = True
    with pytest.raises(LocalModelRuntimeError, match="fallback"):
        run_gpt_oss_harness_locally(contract=contract(), runtime_profile=profile)


def test_openai_compatible_tool_call_is_still_only_a_proposal():
    profile = gpt_oss_local_runtime_profile(endpoint="http://127.0.0.1:8080", model_sha256="b" * 64)
    response = {"choices": [{"message": {"tool_calls": [{"function": {
        "name": "retrieve_business_facts", "arguments": '{"query":"case terms"}'
    }}]}}]}
    result = run_gpt_oss_harness_locally(
        contract=contract(), runtime_profile=profile,
        transport=lambda *_: response,
    )
    assert result["event"]["proposal"]["requires_aion_gateway"] is True
    assert result["event"]["proposal"]["tool_executed"] is False
