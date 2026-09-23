from __future__ import annotations

import json
import hashlib
from decimal import Decimal

import pytest

from backend.modules.aion_inference import (
    AdaptiveInferenceRuntime,
    ContextSelector,
    LearnedAtomSheetStore,
    VerifiedModelOutcome,
    VerifiedCalculationRouter,
    select_task_model,
    verify_proof_receipt,
    verify_task_model_route,
    verify_trace_chain,
)
from backend.modules.codex.beam_event_bus import beam_event_bus


@pytest.mark.parametrize(
    ("prompt", "intent", "expected"),
    [
        ("What is 15% of 240?", "CALCULATE_PERCENTAGE", {"value": "36", "unit": "scalar"}),
        ("Calculate the area of 5 m by 4 m.", "CALCULATE_RECTANGLE_AREA", {"area": "20", "unit": "m²"}),
        ("Calculate volume of 5 m by 4 m by 2.5 m.", "CALCULATE_RECTANGULAR_VOLUME", {"volume": "50", "unit": "m³"}),
        ("Convert 2.5 metres to centimetres.", "CONVERT_LENGTH", {"value": "250", "unit": "cm"}),
        ("Convert 3 metres to centimetres; give the exact result.", "CONVERT_LENGTH", {"value": "300", "unit": "cm"}),
        ("Convert 2.5 kilograms to grams.", "CONVERT_MASS", {"value": "2500", "unit": "g"}),
        (
            "Revenue is EUR 84000 and cost is EUR 51500. Return only JSON with gross_profit and gross_margin_percent, rounded to two decimals.",
            "CALCULATE_GROSS_MARGIN",
            {"gross_profit": "32500", "gross_margin_percent": "38.69"},
        ),
        ("Calculate the area of 10 ft by 12 ft.", "CALCULATE_RECTANGLE_AREA", {"area": "11.1483648", "unit": "m²"}),
    ],
)
def test_verified_calculation_catalog(prompt, intent, expected):
    result = VerifiedCalculationRouter().route(prompt)
    assert result.route == "verified_atomsheet"
    assert result.model_call_required is False
    assert result.intent == intent
    assert result.structured_result == expected
    assert result.proof_receipt["inverse_verified"] is True
    assert result.proof_receipt["model_calls"] == 0


@pytest.mark.parametrize(
    "prompt",
    [
        "What percentage should I use?",
        "Calculate the area of 5 m.",
        "Calculate the area of -5 m by 4 m.",
        "Convert roughly a few metres to centimetres.",
        "Calculate volume of 5 m by 4 m.",
        "Convert 2 kilograms or 3 kilograms to grams.",
        "Revenue is 0 and cost is 50. Return gross margin.",
        "Revenue and cost are unknown. Return gross margin.",
    ],
)
def test_ambiguous_or_invalid_calculations_require_model(prompt):
    result = VerifiedCalculationRouter().route(prompt)
    assert result.route == "full_model"
    assert result.model_call_required is True
    assert result.proof_receipt["gate_passed"] is False


def test_adaptive_runtime_mints_then_replays_verified_result(tmp_path):
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
    )
    prompt = "What is 15% of 240?"
    first = runtime.route(prompt)
    second = runtime.route(prompt)

    assert first.route == "verified_atomsheet"
    assert first.proof_receipt["replay_hit"] is False
    assert second.route == "verified_replay"
    assert second.answer == first.answer == "36"
    assert second.proof_receipt["replay_hit"] is True
    assert second.model_call_required is False

    events = [json.loads(line) for line in (tmp_path / "trace.jsonl").read_text().splitlines()]
    assert [event["route"] for event in events] == ["verified_atomsheet", "verified_replay"]
    assert all(event["model_call_required"] is False for event in events)


def test_context_selection_deduplicates_and_never_drops_policy_for_size_limit():
    selector = ContextSelector()
    selection = selector.select(
        "Prepare the patio quotation",
        [
            "Patio dimensions are 5 m by 4 m.",
            "Patio dimensions are 5 m by 4 m.",
            "Policy: a human must approve every quotation.",
            "The office coffee machine is blue.",
            "Do not take payment and do not make a booking.",
        ],
        max_bytes=140,
    )
    combined = " ".join(selection.selected)
    assert combined.count("Patio dimensions") == 1
    assert "human must approve" in combined
    assert "Do not take payment" in combined
    assert selection.policy_passages_preserved == 2
    assert selection.selected_utf8_bytes < selection.original_utf8_bytes


def test_full_model_fallback_preserves_policy_context_and_emits_trace(tmp_path):
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
    )
    result = runtime.route(
        "Write a customer response. Do not book or take payment; human review is required.",
        context=[
            "Customer asked about a patio.",
            "Policy: quotations must receive human approval.",
            "Unrelated warehouse note.",
        ],
    )
    assert result.route == "full_model"
    assert result.model_call_required is True
    assert "BOOKING_PROHIBITED" in result.fallback_prompt
    assert "PAYMENT_PROHIBITED" in result.fallback_prompt
    assert "HUMAN_REVIEW_REQUIRED" in result.fallback_prompt
    assert "quotations must receive human approval" in result.fallback_prompt
    assert "Write a customer response" in result.fallback_prompt
    event = json.loads((tmp_path / "trace.jsonl").read_text().strip())
    assert event["route"] == "full_model"
    assert event["model_call_required"] is True


@pytest.mark.parametrize(
    "prompt",
    [
        "What is 15% of 240 and then book the job?",
        "What is 15% of 240 and 20% of 100?",
        "Convert 2 m to cm and send the result by email.",
    ],
)
def test_fast_path_rejects_compound_or_multiple_requests(prompt):
    result = VerifiedCalculationRouter().route(prompt)
    assert result.route == "full_model"
    assert result.model_call_required is True


def test_normal_adaptive_route_uses_promoted_english_atomsheet_then_replay(tmp_path):
    learned = LearnedAtomSheetStore(tmp_path / "learning.sqlite3", tmp_path / "promoted")
    fixtures = [("100", "10"), ("80", "25"), ("50", "20"), ("240", "15"), ("12", "50"), ("400", "7")]
    for index, (cost, percent) in enumerate(fixtures):
        result = Decimal(cost) * (Decimal("1") + Decimal(percent) / Decimal("100"))
        learned.observe(VerifiedModelOutcome(
            intent="CALCULATE_MARKED_UP_PRICE",
            inputs={"cost": cost, "markup_percent": percent},
            result=str(result),
            verifier_id=f"decimal-verifier-{index % 2}",
            model_id="model-a",
            response_sha256=hashlib.sha256(f"response-{index}".encode()).hexdigest(),
            created_at=f"2026-09-05T22:00:{index:02d}+00:00",
        ))
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
        learned_store=learned,
    )
    first = runtime.route("What is 225 with a 16% markup?")
    second = runtime.route("225 with a 16 percent markup")
    assert first.answer == second.answer == "261"
    assert first.route == "verified_atomsheet"
    assert first.proof_receipt["sheet_id"] == "aion.learned.calculate.marked.up.price.v1"
    assert second.route == "verified_replay"


def test_sqi_parallel_beams_collapse_to_verified_atomsheet_with_full_receipt(tmp_path):
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
    )
    result = runtime.route("What is 15% of 240?")
    receipt = result.proof_receipt
    assert receipt["sqi_beam_mode"] == "bounded_deterministic_parallel_candidates"
    assert receipt["route_collapse"]["selected_beam_id"] == "calculation_atomsheet"
    assert receipt["model_route_prediction"]["expert_prefetch_profile"] == "arithmetic_business"
    assert {beam["beam_id"] for beam in receipt["sqi_candidate_beams"]} == {
        "profit_atomsheet", "calculation_atomsheet", "workflow_lookup", "model_fallback",
    }
    assert receipt["semantic_gateway_pipeline"] == [
        "canonical_intent_extraction", "entity_and_unit_extraction", "constraint_preservation",
        "ambiguity_scoring", "atomsheet_lookup", "workflow_lookup", "context_selection",
        "model_route_prediction", "minimal_prompt_construction", "trace_and_proof_receipt",
    ]
    assert receipt["beam_events"][-1]["type"] == "semantic_route_collapse"
    assert all(
        event["metadata"]["metric_basis"] == "deterministic_route_evidence_not_photonic_measurement"
        for event in receipt["beam_events"]
    )


def test_workflow_and_model_route_beams_enrich_safe_fallback(tmp_path):
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
    )
    observed = []
    callback = observed.append
    beam_event_bus.subscribe("semantic_route_collapse", callback)
    try:
        result = runtime.route(
            "Prepare a customer quotation. Do not book or take payment; human review is required.",
            context=["Policy: every quotation must receive human approval."],
        )
    finally:
        beam_event_bus.unsubscribe("semantic_route_collapse", callback)
    assert result.route == "full_model"
    assert result.proof_receipt["workflow_lookup"]["workflow_id"] == "aion.workflow.quotation.review.v1"
    assert result.proof_receipt["workflow_lookup"]["executor_bound"] is False
    assert result.proof_receipt["model_route_prediction"]["route_class"] == "policy_reasoning"
    assert result.proof_receipt["route_collapse"]["selected_beam_id"] == "model_fallback"
    assert "selected_workflow" in result.fallback_prompt
    assert "expert_prefetch_profile" in result.fallback_prompt
    assert observed and observed[0].target == "full_model"


def test_general_fallback_glyphs_do_not_alias_unrelated_requests(tmp_path):
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
    )
    first = runtime.route("Explain why leaves change colour.")
    second = runtime.route("Describe a quiet weekend walk.")
    assert first.glyph_address != second.glyph_address


def test_canonical_receipt_binding_and_trace_ancestry_reject_tampering(tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=trace_path,
    )
    first = runtime.route("What is 15% of 240?")
    runtime.route("Explain why leaves change colour.")
    assert verify_proof_receipt(first.proof_receipt) is True
    assert verify_trace_chain(trace_path) is True

    tampered = dict(first.proof_receipt)
    tampered["model_calls"] = 99
    assert verify_proof_receipt(tampered) is False

    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    events[0]["route"] = "tampered"
    trace_path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n")
    assert verify_trace_chain(trace_path) is False


def test_task_model_router_uses_verified_qwen_and_granite_capability_gates(tmp_path):
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
    )
    exact = select_task_model(runtime.route("What is 15% of 240?"), "What is 15% of 240?")
    short = select_task_model(
        runtime.route("Extract the customer name and invoice number from this note."),
        "Extract the customer name and invoice number from this note.",
    )
    deep = select_task_model(
        runtime.route("Write a detailed diagnostic guide with at least ten measurements."),
        "Write a detailed diagnostic guide with at least ten measurements.",
    )
    policy = select_task_model(
        runtime.route("Explain the payment approval policy."),
        "Explain the payment approval policy.",
    )
    assert exact.model is None and exact.route == "verified_atomsheet"
    assert short.model == "qwen3:1.7b" and short.route == "qwen_low_cost"
    assert deep.route == "granite_storage_first"
    assert policy.route == "granite_storage_first"
    assert all(verify_task_model_route(item) for item in (exact, short, deep, policy))
    tampered = short.to_dict()
    tampered["model"] = "unverified"
    assert verify_task_model_route(tampered) is False
