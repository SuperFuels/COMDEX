import pytest

from backend.services.aion_mission_mode.pilot_model_harness import (
    PilotModelHarnessError,
    build_gpt_oss_private_reasoning_request,
    create_harness_receipt,
    parse_gpt_oss_proposal,
)


def pilot_request():
    return {
        "business_id": "home-fixed",
        "mission_id": "finance_close",
        "mission_run_id": "run_001",
        "pilot_id": "finance",
        "task_id": "variance_001",
        "task": "Explain the verified monthly revenue variance.",
        "verified_business_facts": [{"source_id": "ledger-jan", "revenue": 12000}],
        "output_schema": {"type": "object", "required": ["summary"]},
        "allowed_tools": ["retrieve_business_facts", "calculate_finance", "prepare_business_draft"],
    }


def test_harness_is_a_pilot_to_model_bridge_not_a_second_pilot():
    contract = build_gpt_oss_private_reasoning_request(pilot_request=pilot_request())
    authority = contract["authority"]
    assert authority["aion_owns_routing"] is True
    assert authority["pilot_owns_workflow"] is True
    assert authority["harness_is_not_a_pilot"] is True
    assert authority["model_may_execute"] is False
    assert authority["model_may_call_raw_tools"] is False
    assert contract["adapter_request"]["format"] == "openai_harmony"


def test_harmony_tool_call_is_only_an_aion_gateway_proposal():
    contract = build_gpt_oss_private_reasoning_request(pilot_request=pilot_request())
    event = parse_gpt_oss_proposal(
        contract=contract,
        model_text='<|call|>{"name":"calculate_finance","arguments":{"calculation":"12000-10000"}}<|end|>',
    )
    assert event["proposal"]["event_type"] == "tool_proposal"
    assert event["proposal"]["requires_aion_gateway"] is True
    assert event["proposal"]["tool_executed"] is False
    assert event["model_may_mutate_business_memory"] is False

    receipt = create_harness_receipt(contract=contract, event=event, elapsed_ms=418)
    assert receipt["next_owner"] == "aion_tool_gateway"
    assert receipt["external_side_effect_executed"] is False
    assert receipt["receipt_hash"].startswith("sha256:")


def test_harness_rejects_unlisted_or_malformed_tool_proposals():
    contract = build_gpt_oss_private_reasoning_request(pilot_request=pilot_request())
    with pytest.raises(PilotModelHarnessError, match="tool_not_allowed_by_pilot"):
        parse_gpt_oss_proposal(
            contract=contract,
            model_text='<|call|>{"name":"send_email","arguments":{}}<|end|>',
        )
    with pytest.raises(PilotModelHarnessError, match="invalid_harmony_tool_proposal_json"):
        parse_gpt_oss_proposal(contract=contract, model_text="<|call|>not-json<|end|>")


def test_pilot_cannot_smuggle_raw_execution_or_hidden_reasoning_through_harness():
    request = pilot_request()
    request["execute_now"] = True
    with pytest.raises(PilotModelHarnessError, match="forbidden_key"):
        build_gpt_oss_private_reasoning_request(pilot_request=request)

@pytest.mark.parametrize(
    "pilot_id,task_id,task,allowed_tools,response,expected_event",
    [
        (
            "finance",
            "vat_variance_001",
            "Explain a verified VAT variance and request a deterministic check if needed.",
            ["retrieve_business_facts", "calculate_finance"],
            '<|call|>{"name":"calculate_finance","arguments":{"calculation":"net*0.21"}}<|end|>',
            "tool_proposal",
        ),
        (
            "sales",
            "lead_followup_001",
            "Prepare a grounded follow-up for a qualified lead.",
            ["retrieve_business_facts", "prepare_business_draft"],
            '<|return|>{"summary":"Draft ready for Pilot review."}<|end|>',
            "final_proposal",
        ),
        (
            "support",
            "case_reply_001",
            "Prepare a factual reply from the verified support case record.",
            ["retrieve_business_facts", "classify_business_item", "prepare_business_draft"],
            '<|return|>{"summary":"Reply draft references the verified case facts."}<|end|>',
            "final_proposal",
        ),
    ],
)
def test_finance_sales_and_support_share_one_harness_core(
    pilot_id, task_id, task, allowed_tools, response, expected_event
):
    request = pilot_request()
    request.update({
        "pilot_id": pilot_id,
        "task_id": task_id,
        "task": task,
        "allowed_tools": allowed_tools,
    })
    contract = build_gpt_oss_private_reasoning_request(pilot_request=request)
    event = parse_gpt_oss_proposal(contract=contract, model_text=response)
    receipt = create_harness_receipt(contract=contract, event=event, elapsed_ms=105)

    assert contract["pilot_id"] == pilot_id
    assert event["proposal"]["event_type"] == expected_event
    assert receipt["pilot_id"] == pilot_id
    assert receipt["tool_executed"] is False
    assert receipt["memory_mutated"] is False

from backend.services.aion_mission_mode.pilot_model_harness import (
    build_qwen30_fast_local_request,
    parse_qwen3_proposal,
)


def test_qwen_fast_local_uses_the_same_pilot_boundary_and_native_tool_format():
    request = pilot_request()
    request.update({"pilot_id": "sales", "task_id": "followup_01", "allowed_tools": ["prepare_business_draft"]})
    contract = build_qwen30_fast_local_request(pilot_request=request)
    event = parse_qwen3_proposal(
        contract=contract,
        model_text='<tool_call>{"name":"prepare_business_draft","arguments":{"purpose":"lead follow-up"}}</tool_call>',
    )
    assert contract["harness_id"] == "qwen30_fast_local"
    assert contract["authority"]["pilot_owns_workflow"] is True
    assert contract["authority"]["harness_is_not_a_pilot"] is True
    assert event["proposal"]["requires_aion_gateway"] is True
    assert event["proposal"]["tool_executed"] is False
