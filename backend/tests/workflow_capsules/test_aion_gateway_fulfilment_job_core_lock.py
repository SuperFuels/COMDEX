from backend.modules.aion_gateway.fulfilment_job_core import (
    FULFILMENT_JOB_SCHEMA_VERSION,
    FULFILMENT_JOB_STATES,
    append_fulfilment_job_timeline_event,
    create_fulfilment_job,
    stable_job_id,
)
from backend.modules.aion_gateway.inbound_gateway import preview_inbound_gateway_intent


def test_fulfilment_job_core_creates_real_job_object():
    job = create_fulfilment_job(
        business_id="biz_123",
        service_type="plumber",
        location="Albox",
        requested_outcome="Fix leaking tap",
        workflow_run_id="run_001",
        goal_id="goal_001",
        created_at="2026-05-26T20:00:00+00:00",
    )

    assert job["schema_version"] == FULFILMENT_JOB_SCHEMA_VERSION
    assert job["job_id"].startswith("job_")
    assert job["business_id"] == "biz_123"
    assert job["service_type"] == "plumber"
    assert job["location"] == "Albox"
    assert job["requested_outcome"] == "Fix leaking tap"
    assert job["workflow_run_id"] == "run_001"
    assert job["goal_id"] == "goal_001"


def test_fulfilment_job_lifecycle_states_are_locked():
    assert FULFILMENT_JOB_STATES == {
        "requested",
        "quoted",
        "accepted",
        "scheduled",
        "in_progress",
        "completed",
        "disputed",
        "failed",
    }


def test_fulfilment_job_has_current_stage_next_expected_event_and_blocked_reason():
    job = create_fulfilment_job(
        business_id="biz_123",
        service_type="electrician",
        location="Arboleas",
        requested_outcome="Install outdoor socket",
        created_at="2026-05-26T20:00:00+00:00",
    )

    assert job["lifecycle_state"] == "requested"
    assert job["current_stage"] == "requested"
    assert job["next_expected_event"] == "quote_required"
    assert job["blocked_reason"] == ""


def test_fulfilment_job_timeline_is_append_only_style():
    job = create_fulfilment_job(
        business_id="biz_123",
        service_type="handyman",
        location="Zurgena",
        requested_outcome="Repair pergola",
        created_at="2026-05-26T20:00:00+00:00",
    )

    original_timeline = list(job["job_timeline"])

    updated = append_fulfilment_job_timeline_event(
        job,
        event_type="quote_requested",
        stage="quoted",
        message="Provider quote requested.",
        actor="aion",
        created_at="2026-05-26T20:10:00+00:00",
        metadata={"next_expected_event": "customer_acceptance_required"},
    )

    assert job["job_timeline"] == original_timeline
    assert len(updated["job_timeline"]) == len(original_timeline) + 1
    assert updated["current_stage"] == "quoted"
    assert updated["next_expected_event"] == "customer_acceptance_required"


def test_fulfilment_job_blocks_missing_required_fields():
    job = create_fulfilment_job(
        business_id="",
        service_type="",
        location="",
        requested_outcome="",
        created_at="2026-05-26T20:00:00+00:00",
    )

    assert job["lifecycle_state"] == "failed"
    assert "missing_business_id" in job["blocked_reason"]
    assert "missing_service_type" in job["blocked_reason"]
    assert "missing_location" in job["blocked_reason"]
    assert "missing_requested_outcome" in job["blocked_reason"]
    assert job["next_expected_event"] == "human_review_required"


def test_stable_job_id_is_deterministic_and_lowercases_stable_fields():
    first = stable_job_id(
        business_id="BIZ_123",
        service_type="Plumber",
        location="ALBOX",
        requested_outcome="Fix tap",
        created_at="2026-05-26T20:00:00+00:00",
    )
    second = stable_job_id(
        business_id="biz_123",
        service_type="plumber",
        location="albox",
        requested_outcome="Fix tap",
        created_at="2026-05-26T20:00:00+00:00",
    )

    assert first == second


def test_gateway_v0_still_does_not_create_real_fulfilment_job():
    result = preview_inbound_gateway_intent(
        business_id="biz_123",
        source_channel="legacy_web_form",
        vertical_key="plumber",
        intent_type="service_request",
        raw_payload={"summary": "Fix leaking tap"},
    )

    preview = result["fulfilment_job_preview"]
    trace = result["machine_trace"]

    assert preview["would_create_fulfilment_job"] is False
    assert trace["would_create_fulfilment_job"] is False
    assert "job_id" not in preview
    assert "lifecycle_state" not in preview


def test_fulfilment_job_completion_sets_no_next_event():
    job = create_fulfilment_job(
        business_id="biz_123",
        service_type="cleaner",
        location="Albox",
        requested_outcome="End of tenancy clean",
        created_at="2026-05-26T20:00:00+00:00",
    )

    completed = append_fulfilment_job_timeline_event(
        job,
        event_type="job_completed",
        stage="completed",
        message="Job completed with evidence.",
        created_at="2026-05-26T21:00:00+00:00",
    )

    assert completed["lifecycle_state"] == "completed"
    assert completed["current_stage"] == "completed"
    assert completed["next_expected_event"] == "none"
