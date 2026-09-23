from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o10_installed():
    assert "O10 unified infinite canvas + wide Goal Loop layout installed" in APP_JS
    assert "window.aionApplyWideGoalLoopLayoutO10" in APP_JS
    assert "window.aionApplyCurrentWideGoalLoopLayoutO10" in APP_JS
    assert "window.aionEnsureUnifiedInfiniteWorkflowCanvasO10" in APP_JS


def test_o10_unifies_canvas_surface_and_removes_small_sheet_limits():
    for marker in [
        "min-width: 8200px",
        "min-height: 3200px",
        "width: 8200px",
        "height: 3200px",
        "max-width: none",
        "max-height: none",
        "overflow: visible",
        "canvas-sheet",
        "canvas-paper",
        "background: transparent",
        "box-shadow: none",
    ]:
        assert marker in APP_JS


def test_o10_uses_wide_left_to_right_layout_columns():
    for column in [
        "board_meeting",
        "board_decision",
        "goal_loop",
        "board_actions",
        "assignment",
        "sub_goal",
        "plan",
        "agent_tasks",
        "result",
        "evaluation",
        "ab_test",
        "feedback",
        "boardroom_decision",
        "cross_analysis",
        "conflict",
        "evidence",
        "audit",
        "founder_trace",
    ]:
        assert column in APP_JS

    assert "wide_layered_dag_department_swimlanes" in APP_JS
    assert "left_to_right" in APP_JS


def test_o10_uses_clear_department_lanes():
    for lane in [
        "boardroom",
        "marketing",
        "sales",
        "finance",
        "operations",
        "support",
        "hr",
        "review",
        "evidence",
    ]:
        assert lane in APP_JS

    assert "department_lanes" in APP_JS
    assert "review_lane_y" in APP_JS
    assert "evidence_lane_y" in APP_JS


def test_o10_wraps_o8_o9_and_preserves_preview_safety():
    assert "aionStageNativeGoalLoopWorkflowO8" in APP_JS
    assert "aionLayoutCurrentGoalLoopWorkflowO9" in APP_JS
    assert "wrapO8AndO9Stagers" in APP_JS

    for marker in [
        "preview_only: true",
        "creates_second_canvas: false",
        "creates_second_pilot: false",
        "connector_call_required = false",
        "external_side_effects = false",
        "booking_created = false",
        "payment_created = false",
        "customer_message_sent = false",
    ]:
        assert marker in APP_JS


def test_o10_has_manual_wide_layout_button():
    assert "Wide Goal Loop Layout" in APP_JS
    assert "data-aion-o10-wide-layout-goal-loop" in APP_JS
    assert "aion-o10-layout-button" in APP_JS
