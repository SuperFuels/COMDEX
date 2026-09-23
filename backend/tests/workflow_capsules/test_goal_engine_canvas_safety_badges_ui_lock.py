from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app() -> str:
    return APP.read_text(encoding="utf-8")


def test_goal_engine_canvas_safety_badge_renderer_exists():
    text = read_app()

    assert "renderAionGoalEngineCanvasSafetyBadgesV1" in text
    assert "getAionGoalEngineCanvasSafetyBadgesV1" in text
    assert 'data-aion-goal-engine-canvas-safety-badges="true"' in text


def test_goal_engine_canvas_safety_badges_include_required_labels():
    text = read_app()

    assert "Dry-run" in text
    assert "Approval gated" in text
    assert "Budget guarded" in text
    assert "Checkpointed" in text
    assert "Evidence required" in text
    assert "Red-team warning" in text


def test_goal_engine_canvas_safety_badges_are_injected_into_node_cards():
    text = read_app()

    assert "injectAionGoalEngineCanvasSafetyBadgesV1" in text
    assert "renderAionGoalEngineCanvasSafetyBadgesV1(node)" in text
    assert "goal_engine_preview_bundle" in text
