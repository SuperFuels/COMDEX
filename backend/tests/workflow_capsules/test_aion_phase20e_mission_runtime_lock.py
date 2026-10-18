from backend.services.aion_mission_mode.mission_runtime import (
    MissionRuntimeLimits,
    mount_mission_runtime,
    run_mission_runtime_preview,
)


SAFE_STEPS = [
    {"step_id": "step_01", "action_type": "draft_offer", "title": "Draft offer"},
    {"step_id": "step_02", "action_type": "draft_facebook_advert", "title": "Draft advert"},
    {"step_id": "step_03", "action_type": "create_workflow_preview", "title": "Create workflow preview"},
]


def test_phase20e_safe_batch_mounts_runtime() -> None:
    result = mount_mission_runtime(
        mission_id="mission_20e_001",
        mission_run_id="run_001",
        steps=SAFE_STEPS,
    )

    assert result["mounted"] is True
    assert result["state"]["status"] == "ready_for_runtime"
    assert result["state"]["state_hash"].startswith("sha256:")


def test_phase20e_restricted_step_does_not_mount_runtime() -> None:
    result = mount_mission_runtime(
        mission_id="mission_20e_002",
        mission_run_id="run_001",
        steps=[
            {"step_id": "step_01", "action_type": "draft_offer"},
            {"step_id": "step_02", "action_type": "publish_advert", "decision": "safe_autonomous"},
        ],
    )

    assert result["mounted"] is False
    assert result["state"]["status"] in {"waiting_human_review", "blocked"}
    assert result["state"]["blocked_reason"]


def test_phase20e_runtime_completes_safe_preview_steps() -> None:
    result = run_mission_runtime_preview(
        mission_id="mission_20e_003",
        mission_run_id="run_001",
        steps=SAFE_STEPS,
    )

    assert result["completed"] is True
    assert result["state"]["status"] == "completed"
    assert result["state"]["completed_step_ids"] == ["step_01", "step_02", "step_03"]
    assert result["live_side_effects_enabled"] is False


def test_phase20e_runtime_halts_before_live_side_effects() -> None:
    result = run_mission_runtime_preview(
        mission_id="mission_20e_004",
        mission_run_id="run_001",
        steps=[
            {"step_id": "step_01", "action_type": "draft_offer"},
            {"step_id": "step_02", "action_type": "send_email_live", "decision": "safe_autonomous"},
        ],
    )

    assert result["completed"] is False
    assert result["state"]["status"] in {"waiting_human_review", "blocked", "paused_at_checkpoint"}
    assert result["live_side_effects_enabled"] is False


def test_phase20e_runtime_enforces_tool_call_limit() -> None:
    result = run_mission_runtime_preview(
        mission_id="mission_20e_005",
        mission_run_id="run_001",
        steps=SAFE_STEPS,
        limits=MissionRuntimeLimits(max_tool_calls=2, max_cost=0.0),
    )

    assert result["completed"] is False
    assert result["state"]["status"] == "blocked"
    assert result["state"]["blocked_reason"] == "max_tool_calls_exceeded"
    assert result["state"]["completed_step_ids"] == ["step_01", "step_02"]


def test_phase20e_runtime_trace_records_safe_steps() -> None:
    result = run_mission_runtime_preview(
        mission_id="mission_20e_006",
        mission_run_id="run_001",
        steps=SAFE_STEPS,
    )

    event_types = [event["event_type"] for event in result["state"]["trace_events"]]

    assert "runtime_mounted" in event_types
    assert "runtime_safe_step_completed" in event_types
    assert "runtime_completed_preview" in event_types


def test_phase20e_state_hash_is_deterministic() -> None:
    first = run_mission_runtime_preview(
        mission_id="mission_20e_007",
        mission_run_id="run_001",
        steps=SAFE_STEPS,
    )
    second = run_mission_runtime_preview(
        mission_id="mission_20e_007",
        mission_run_id="run_001",
        steps=SAFE_STEPS,
    )

    assert first["state"]["state_hash"] == second["state"]["state_hash"]
    assert first["state"]["state_hash"].startswith("sha256:")


def test_phase20e_runtime_does_not_enable_live_channels() -> None:
    result = run_mission_runtime_preview(
        mission_id="mission_20e_008",
        mission_run_id="run_001",
        steps=SAFE_STEPS,
    )

    dumped = str(result).lower()

    assert result["live_side_effects_enabled"] is False
    assert "payment_enabled': true" not in dumped
    assert "booking_enabled': true" not in dumped
    assert "deployment_enabled': true" not in dumped
    assert "reputation_mutation_enabled': true" not in dumped
