from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o6_visible_goal_loop_bridge_installed():
    assert "O6 visible Goal Loop Canvas bridge installed" in APP_JS
    assert "window.aionGenerateVisibleGoalLoopCanvas" in APP_JS
    assert "data-aion-visible-goal-loop-canvas" in APP_JS
    assert "data-aion-goal-loop-launcher" in APP_JS


def test_o6_visible_goal_loop_nodes_are_present():
    for label in [
        "Goal Loop",
        "Department Canvases",
        "Stage Agent Tasks",
        "Approval Gate",
        "Record Result",
        "Evaluate Result",
        "Generate A/B Test",
        "Feedback to Boardroom",
        "Boardroom Decision",
        "Cross-Function Analysis",
        "Cross-Function Conflict",
        "Evidence / Proof Receipt",
        "Revision / Audit Trail",
        "Founder Demo Trace",
    ]:
        assert label in APP_JS


def test_o6_visible_goal_loop_panels_are_present():
    for label in [
        "Canvas Execution Controls",
        "Business Container Persistence",
        "Replay / Restore",
        "Executive Decision Package",
        "Approved Action Staging",
        "Guarded Execution Handoff",
        "Founder Demo Trace",
    ]:
        assert label in APP_JS


def test_o6_visible_goal_loop_is_preview_safe_and_uses_existing_surfaces():
    for marker in [
        "Preview-only",
        "No live execution",
        "No connector calls",
        "No bookings",
        "No payments",
        "No customer messages",
        "creates_second_canvas: false",
        "creates_second_pilot: false",
        'data-creates-second-canvas", "false"',
        'data-creates-second-pilot", "false"',
    ]:
        assert marker in APP_JS


def test_o6_visible_goal_loop_has_console_debug_object():
    assert "window.__aionVisibleGoalLoopCanvasO6" in APP_JS
    assert "nodes: GOAL_LOOP_NODES.map" in APP_JS
    assert "edges: GOAL_LOOP_EDGES.map" in APP_JS
    assert "preview_panels: PREVIEW_PANELS.map" in APP_JS
