from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o10_1_installed_and_unstable_o10_removed():
    assert "O10.1 stable visible Goal Loop canvas layout installed" in APP_JS
    assert "O10 unified infinite canvas + wide Goal Loop layout installed" not in APP_JS
    assert "window.aionApplyCurrentStableVisibleGoalLoopLayoutO101" in APP_JS
    assert "window.aionEnsureStableVisibleWorkflowCanvasO101" in APP_JS


def test_o10_1_uses_viewport_friendly_canvas_size():
    for marker in [
        "min-width: 4600px",
        "min-height: 2400px",
        "width: 4600px",
        "height: 2400px",
        "max-width: none",
        "max-height: none",
        "overflow: visible",
        "canvas-sheet",
        "canvas-paper",
        "background: transparent",
        "box-shadow: none",
    ]:
        assert marker in APP_JS


def test_o10_1_layout_is_stable_and_not_continuous_relayout():
    assert "no_continuous_relayout: true" in APP_JS
    assert "Do not auto-layout in the interval" in APP_JS
    assert "applyCurrentStableLayout" in APP_JS
    assert "syncButtonOnly" in APP_JS


def test_o10_1_has_clear_swimlane_columns_and_rows():
    for marker in [
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
        "boardroom",
        "marketing",
        "sales",
        "finance",
        "operations",
        "support",
        "review",
    ]:
        assert marker in APP_JS


def test_o10_1_preserves_preview_safety():
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
