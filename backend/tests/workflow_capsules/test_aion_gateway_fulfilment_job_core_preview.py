from backend.modules.aion_gateway.fulfilment_job import (
    FULFILMENT_JOB_SCHEMA_VERSION,
    FULFILMENT_JOB_STATES,
    build_fulfilment_job_core_preview,
    stable_job_preview_hash,
)


def test_fulfilment_job_preview_has_core_identity_fields():
    preview = build_fulfilment_job_core_preview(
        business_id="biz_123",
        service_type="plumber",
        location="Albox",
        requested_outcome="Fix leaking tap",
        workflow_run_id="run_123",
        goal_id="goal_123",
        source_intent_id="intent_123",
    )

    assert preview["schema_version"] == FULFILMENT_JOB_SCHEMA_VERSION
    assert preview["job_preview_id"].startswith("job_preview_")
    assert preview["business_id"] == "biz_123"
    assert preview["service_type"] == "plumber"
    assert preview["location"] == "Albox"
    assert preview["requested_outcome"] == "Fix leaking tap"
    assert preview["workflow_run_id"] == "run_123"
    assert preview["goal_id"] == "goal_123"


def test_fulfilment_job_preview_separates_jobs_from_workflow_runs():
    preview = build_fulfilment_job_core_preview(
        business_id="biz_123",
        service_type="electrician",
        location="Arboleas",
        requested_outcome="Install outdoor socket",
        workflow_run_id="workflow_run_001",
    )

    assert preview["job_preview_id"] != preview["workflow_run_id"]
    assert preview["workflow_run_id"] == "workflow_run_001"
    assert "job_preview_" in preview["job_preview_id"]


def test_fulfilment_job_lifecycle_states_are_locked():
    expected = {
        "requested",
        "quoted",
        "accepted",
        "scheduled",
        "in_progress",
        "completed",
        "disputed",
        "failed",
    }

    assert FULFILMENT_JOB_STATES == expected


def test_fulfilment_job_preview_has_stage_and_next_event():
    preview = build_fulfilment_job_core_preview(
        business_id="biz_123",
        service_type="handyman",
        location="Zurgena",
        requested_outcome="Repair pergola",
    )

    assert preview["lifecycle_state"] == "requested"
    assert preview["current_stage"] == "requested"
    assert preview["next_expected_event"] == "human_review"
    assert "preview_only_no_job_record_created" in preview["blocked_reason"]


def test_fulfilment_job_preview_has_append_only_timeline_shape():
    preview = build_fulfilment_job_core_preview(
        business_id="biz_123",
        service_type="cleaner",
        location="Alfoquia",
        requested_outcome="Deep clean villa",
        source_intent_id="intent_abc",
    )

    timeline = preview["job_timeline"]

    assert isinstance(timeline, list)
    assert len(timeline) == 1
    assert timeline[0]["event_type"] == "fulfilment_job_preview_created"
    assert timeline[0]["stage"] == "requested"
    assert timeline[0]["metadata"]["source_intent_id"] == "intent_abc"


def test_fulfilment_job_preview_is_dry_run_only_and_non_mutating():
    preview = build_fulfilment_job_core_preview(
        business_id="biz_123",
        service_type="plumber",
        location="Albox",
        requested_outcome="Fix leaking pipe",
    )

    assert preview["dry_run_only"] is True
    assert preview["would_create_fulfilment_job"] is False
    assert preview["would_write_database"] is False
    assert preview["would_execute_goal_engine"] is False
    assert preview["would_write_externally"] is False
    assert preview["requires_human_review"] is True
    assert preview["metadata"]["no_database_write"] is True
    assert preview["metadata"]["no_public_route"] is True


def test_fulfilment_job_preview_blocks_missing_required_fields():
    preview = build_fulfilment_job_core_preview(
        business_id="",
        service_type="",
        location="",
        requested_outcome="",
    )

    blocked = preview["metadata"]["blocked_reasons"]

    assert "missing_business_id" in blocked
    assert "missing_service_type" in blocked
    assert "missing_requested_outcome" in blocked
    assert "preview_only_no_job_record_created" in blocked


def test_fulfilment_job_preview_hash_is_stable_and_order_independent():
    left = {
        "business_id": "biz_123",
        "service_type": "plumber",
        "requested_outcome": "Fix leak",
    }
    right = {
        "requested_outcome": "Fix leak",
        "service_type": "plumber",
        "business_id": "biz_123",
    }

    assert stable_job_preview_hash(left) == stable_job_preview_hash(right)
