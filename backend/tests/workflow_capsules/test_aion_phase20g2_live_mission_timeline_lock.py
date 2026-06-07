from backend.services.aion_mission_mode.live_mission_timeline import (
    assert_live_timeline_safety,
    compile_live_timeline,
    create_timeline_event,
)


def _events():
    base = {
        "mission_id": "mission_001",
        "mission_run_id": "run_001",
        "business_id": "home_fixed",
    }
    return [
        {
            **base,
            "sequence_number": 0,
            "event_type": "mission_started",
            "title": "Mission started",
            "state_after": "running",
            "source_hash": "sha256:start",
        },
        {
            **base,
            "sequence_number": 1,
            "event_type": "step_completed",
            "step_id": "plan",
            "title": "Plan completed",
            "state_after": "running",
            "source_hash": "sha256:plan",
            "receipt_hash": "sha256:receipt_plan",
        },
        {
            **base,
            "sequence_number": 2,
            "event_type": "approval_requested",
            "step_id": "domain",
            "title": "Domain approval requested",
            "state_after": "waiting_approval",
            "source_hash": "sha256:approval",
            "approval_hash": "sha256:approval_domain",
        },
        {
            **base,
            "sequence_number": 3,
            "event_type": "human_task_created",
            "step_id": "facebook",
            "title": "Facebook page task",
            "state_after": "waiting_human_task",
            "source_hash": "sha256:task",
            "human_task_hash": "sha256:human_task",
        },
        {
            **base,
            "sequence_number": 4,
            "event_type": "action_blocked",
            "step_id": "publish",
            "title": "Publish blocked",
            "state_after": "blocked_for_safety",
            "source_hash": "sha256:blocked",
            "blocked_action_hash": "sha256:blocked_action",
        },
    ]


def test_phase20g2_create_timeline_event_hashes() -> None:
    event = create_timeline_event(_events()[0])

    assert event["event_type"] == "mission_started"
    assert event["event_hash"].startswith("sha256:")


def test_phase20g2_rejects_invalid_event_type() -> None:
    event = _events()[0]
    event["event_type"] = "execute_live_tool"

    try:
        create_timeline_event(event)
    except ValueError as exc:
        assert "invalid timeline event type" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20g2_rejects_bad_source_hash() -> None:
    event = _events()[0]
    event["source_hash"] = "bad"

    try:
        create_timeline_event(event)
    except ValueError as exc:
        assert "source_hash must be sha256-prefixed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20g2_compile_timeline_counts() -> None:
    timeline = compile_live_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_hash="sha256:panel",
        events=_events(),
    )

    assert timeline["event_count"] == 5
    assert timeline["completed_steps"] == 1
    assert timeline["approval_waits"] == 1
    assert timeline["human_task_waits"] == 1
    assert timeline["blocked_actions"] == 1


def test_phase20g2_timeline_is_non_executing() -> None:
    timeline = compile_live_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_hash="sha256:panel",
        events=_events(),
    )

    assert timeline["timeline_executes_tools"] is False
    assert timeline["timeline_mutates_provider_state"] is False


def test_phase20g2_duplicate_sequence_rejected() -> None:
    events = _events()
    events[1]["sequence_number"] = 0

    try:
        compile_live_timeline(
            mission_id="mission_001",
            mission_run_id="run_001",
            business_id="home_fixed",
            panel_hash="sha256:panel",
            events=events,
        )
    except ValueError as exc:
        assert "duplicate timeline sequence_number" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20g2_timeline_safety_allows_valid_timeline() -> None:
    timeline = compile_live_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_hash="sha256:panel",
        events=_events(),
    )

    safety = assert_live_timeline_safety(timeline)

    assert safety["allowed"] is True
    assert safety["safety_state"] == "timeline_safe"


def test_phase20g2_timeline_safety_blocks_tamper() -> None:
    timeline = compile_live_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_hash="sha256:panel",
        events=_events(),
    )
    timeline["event_count"] = 99

    safety = assert_live_timeline_safety(timeline)

    assert safety["allowed"] is False
    assert "timeline_hash_mismatch" in safety["reasons"]


def test_phase20g2_timeline_safety_blocks_execution_flags() -> None:
    timeline = compile_live_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_hash="sha256:panel",
        events=_events(),
    )
    timeline["timeline_executes_tools"] = True

    safety = assert_live_timeline_safety(timeline)

    assert safety["allowed"] is False
    assert "timeline_must_not_execute_tools" in safety["reasons"]


def test_phase20g2_timeline_hash_is_deterministic() -> None:
    first = compile_live_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_hash="sha256:panel",
        events=_events(),
    )
    second = compile_live_timeline(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_hash="sha256:panel",
        events=_events(),
    )

    assert first["timeline_hash"] == second["timeline_hash"]
