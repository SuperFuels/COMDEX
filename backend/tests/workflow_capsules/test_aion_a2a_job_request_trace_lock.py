from backend.modules.aion_gateway.a2a_job_trace import (
    A2A_JOB_TRACE_VERSION,
    build_a2a_job_request_preview,
    build_a2a_job_trace_preview,
    build_a2a_job_request_trace_bundle,
    validate_a2a_job_request_preview,
)


def _request():
    return {
        "business_id": "home_fixed",
        "business_name": "Home Fixed",
        "vertical_key": "home_repair",
        "industry_key": "trades",
        "requested_outcome": "Fix leaking roof in Albox",
        "source_channel": "a2a_preview",
        "customer_location": "Albox",
        "preferred_time_window": "tomorrow morning",
        "budget_hint": "under 300 EUR",
        "evidence_requirements": ["before_photo", "after_photo"],
        "risk_flags": ["working_at_height"],
    }


def test_job_request_validation_requires_core_fields():
    result = validate_a2a_job_request_preview({})
    assert result["ok"] is False
    assert result["status"] == "blocked_missing_required_fields"
    assert "business_id" in result["missing_fields"]
    assert "vertical_key" in result["missing_fields"]
    assert "requested_outcome" in result["missing_fields"]


def test_job_request_preview_shape():
    result = build_a2a_job_request_preview(_request())
    assert result["ok"] is True
    assert result["status"] == "job_request_preview_ready"
    assert result["contract_version"] == A2A_JOB_TRACE_VERSION
    assert result["endpoint_key"] == "job_request_preview"
    assert result["method"] == "POST"
    assert result["business_id"] == "home_fixed"
    assert result["business_name"] == "Home Fixed"
    assert result["vertical_key"] == "home_repair"
    assert result["industry_key"] == "trades"
    assert result["requested_outcome"] == "Fix leaking roof in Albox"
    assert result["job_request_hash"]


def test_job_request_preview_is_not_live_job_creation():
    result = build_a2a_job_request_preview(_request())
    assert result["final_job_created"] is False
    assert result["workflow_run_created"] is False
    assert result["booking_created"] is False
    assert result["human_review_required"] is True
    assert result["next_step"] == "future_guarded_approval_path"


def test_job_trace_preview_shape():
    request = build_a2a_job_request_preview(_request())
    trace = build_a2a_job_trace_preview(request)
    assert trace["ok"] is True
    assert trace["status"] == "job_trace_preview_ready"
    assert trace["endpoint_key"] == "job_trace"
    assert trace["method"] == "GET"
    assert trace["business_id"] == "home_fixed"
    assert trace["current_stage"] == "waiting_human_review"
    assert trace["live_status_polling_enabled"] is False
    assert trace["trace_hash"]
    assert len(trace["trace_events"]) >= 3


def test_job_trace_events_are_preview_only():
    trace = build_a2a_job_trace_preview(build_a2a_job_request_preview(_request()))
    for event in trace["trace_events"]:
        assert event["human_review_required"] is True
        assert event.get("would_execute_workflow") is False or event.get("would_create_live_job") is False or event.get("would_create_booking") is False


def test_bundle_contains_request_and_trace():
    bundle = build_a2a_job_request_trace_bundle(_request())
    assert bundle["ok"] is True
    assert bundle["status"] == "a2a_job_request_trace_preview_ready"
    assert bundle["contract_version"] == A2A_JOB_TRACE_VERSION
    assert bundle["job_request_preview"]["endpoint_key"] == "job_request_preview"
    assert bundle["job_trace_preview"]["endpoint_key"] == "job_trace"
    assert bundle["bundle_hash"]


def test_hashes_are_deterministic():
    a = build_a2a_job_request_trace_bundle(_request())
    b = build_a2a_job_request_trace_bundle(_request())
    assert a["bundle_hash"] == b["bundle_hash"]
    assert a["job_request_preview"]["job_request_hash"] == b["job_request_preview"]["job_request_hash"]
    assert a["job_trace_preview"]["trace_hash"] == b["job_trace_preview"]["trace_hash"]


def test_hashes_change_with_requested_outcome():
    a = build_a2a_job_request_trace_bundle(_request())
    changed = _request()
    changed["requested_outcome"] = "Fix blocked drain in Arboleas"
    b = build_a2a_job_request_trace_bundle(changed)
    assert a["bundle_hash"] != b["bundle_hash"]


def test_safety_flags_are_locked():
    bundle = build_a2a_job_request_trace_bundle(_request())
    for safety in [
        bundle["safety"],
        bundle["job_request_preview"]["safety"],
        bundle["job_trace_preview"]["safety"],
    ]:
        assert safety["guarded"] is True
        assert safety["preview_only"] is True
        assert safety["public_route_exposed"] is False
        assert safety["requires_auth"] is True
        assert safety["human_review_required"] is True
        assert safety["would_execute_workflow"] is False
        assert safety["would_create_booking"] is False
        assert safety["would_create_live_job"] is False
        assert safety["would_move_money"] is False
        assert safety["would_move_pho"] is False
        assert safety["would_require_wallet"] is False
        assert safety["would_create_payment"] is False
        assert safety["would_create_escrow"] is False
        assert safety["would_send_external_message"] is False
        assert safety["live_status_polling_enabled"] is False


def test_blocked_reasons_explain_guardrails():
    bundle = build_a2a_job_request_trace_bundle(_request())
    request_reasons = bundle["job_request_preview"]["blocked_reasons"]
    trace_reasons = bundle["job_trace_preview"]["blocked_reasons"]

    assert "preview_only" in request_reasons
    assert "no_live_job_creation" in request_reasons
    assert "no_workflow_execution" in request_reasons
    assert "no_booking_side_effect" in request_reasons
    assert "no_live_status_polling" in trace_reasons
