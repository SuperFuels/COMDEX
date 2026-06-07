from backend.services.aion_mission_mode.boardroom_mission_control_contract import (
    REQUIRED_VISIBLE_MESSAGE,
    assert_boardroom_panel_safety,
    create_boardroom_control_panel,
    create_boardroom_replay_projection,
    create_mission_step_view,
)


def _steps():
    return [
        {
            "step_id": "plan",
            "title": "Create mission plan",
            "state": "completed",
            "lane": "planning",
            "risk_level": "low",
            "control_mode": "autonomous",
            "receipt_hash": "sha256:receipt1",
        },
        {
            "step_id": "domain",
            "title": "Prepare domain checkout",
            "state": "waiting_approval",
            "lane": "external_action",
            "risk_level": "high",
            "control_mode": "human_approval_required",
            "requires_approval": True,
        },
        {
            "step_id": "facebook",
            "title": "Create Facebook page",
            "state": "waiting_human_task",
            "lane": "human_task",
            "risk_level": "medium",
            "control_mode": "human_task_required",
            "requires_human_task": True,
        },
    ]


def _panel(**overrides):
    base = dict(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="home_fixed",
        panel_state="waiting_approval",
        current_step_id="domain",
        next_checkpoint_id="domain",
        plan_approval_matrix_hash="sha256:matrix",
        mission_trace_hash="sha256:trace",
        replay_hash="sha256:replay",
        ets_preview_hash="sha256:ets",
        demo_summary_hash="sha256:demo",
        steps=_steps(),
        blocked_actions=[
            {"action_type": "publish_facebook_post", "reason": "approval_required"}
        ],
        human_tasks=[
            {"task_id": "task_facebook", "title": "Create Facebook page"}
        ],
        approval_gates=[
            {"approval_id": "approval_domain", "title": "Approve domain purchase"}
        ],
    )
    base.update(overrides)
    return create_boardroom_control_panel(**base)


def test_phase20g1_step_view_hashes_receipt_step() -> None:
    view = create_mission_step_view(_steps()[0])

    assert view["step_id"] == "plan"
    assert view["receipt_hash"] == "sha256:receipt1"
    assert view["step_view_hash"].startswith("sha256:")


def test_phase20g1_step_view_rejects_invalid_state() -> None:
    step = _steps()[0]
    step["state"] = "teleporting"

    try:
        create_mission_step_view(step)
    except ValueError as exc:
        assert "invalid step state" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20g1_panel_contains_required_visible_message() -> None:
    panel = _panel()

    assert panel["required_visible_message"] == REQUIRED_VISIBLE_MESSAGE
    assert panel["live_action_buttons_enabled"] is False
    assert panel["replay_mode_executes_tools"] is False


def test_phase20g1_panel_counts_step_states() -> None:
    panel = _panel()

    assert panel["step_count"] == 3
    assert panel["completed_count"] == 1
    assert panel["waiting_approval_count"] == 1
    assert panel["waiting_human_task_count"] == 1


def test_phase20g1_panel_rejects_missing_current_step() -> None:
    try:
        _panel(current_step_id="missing")
    except ValueError as exc:
        assert "current_step_id is not present in steps" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20g1_panel_rejects_bad_hash() -> None:
    try:
        _panel(plan_approval_matrix_hash="bad")
    except ValueError as exc:
        assert "plan_approval_matrix_hash must be sha256-prefixed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20g1_panel_safety_allows_valid_panel() -> None:
    panel = _panel()
    safety = assert_boardroom_panel_safety(panel)

    assert safety["allowed"] is True
    assert safety["safety_state"] == "boardroom_panel_safe"


def test_phase20g1_panel_safety_blocks_tampered_hash() -> None:
    panel = _panel()
    panel["completed_count"] = 99

    safety = assert_boardroom_panel_safety(panel)

    assert safety["allowed"] is False
    assert "panel_hash_mismatch" in safety["reasons"]


def test_phase20g1_panel_safety_blocks_live_buttons() -> None:
    panel = _panel()
    panel["live_action_buttons_enabled"] = True

    safety = assert_boardroom_panel_safety(panel)

    assert safety["allowed"] is False
    assert "panel_hash_mismatch" in safety["reasons"]
    assert "live_action_buttons_must_be_disabled" in safety["reasons"]


def test_phase20g1_replay_projection_is_read_only() -> None:
    projection = create_boardroom_replay_projection(_panel())

    assert projection["read_only"] is True
    assert projection["tools_executable"] is False
    assert projection["live_provider_mutation_allowed"] is False


def test_phase20g1_replay_projection_rejects_unsafe_panel() -> None:
    panel = _panel()
    panel["required_visible_message"] = "wrong"

    try:
        create_boardroom_replay_projection(panel)
    except ValueError as exc:
        assert "unsafe panel" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_phase20g1_panel_hash_is_deterministic() -> None:
    first = _panel()
    second = _panel()

    assert first["panel_hash"] == second["panel_hash"]
