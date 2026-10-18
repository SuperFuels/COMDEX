from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def read_app():
    return APP.read_text(encoding="utf-8")


def test_goal_engine_inspector_dom_injector_is_installed():
    text = read_app()

    assert "Goal Engine inspector DOM injector v2" in text
    assert "window.__syncAionGoalEngineInspectorDomV2" in text
    assert 'data-aion-goal-engine-inspector-injected' in text
    assert "__renderAionGoalEngineInspectorBlockV1" in text


def test_goal_engine_inspector_injector_is_read_only_append_only():
    text = read_app()

    assert "Does not replace existing inspector" in text
    assert "Does not execute anything" in text
    assert "Only appends read-only contract fields" in text
    assert "mount.appendChild(wrapper)" in text


def test_goal_engine_inspector_injector_listens_to_render_and_selection():
    text = read_app()

    assert 'window.addEventListener("aion:workflow-rendered", syncGoalEngineInspector)' in text
    assert 'window.addEventListener("aion:workflow-selection-changed", syncGoalEngineInspector)' in text
    assert "MutationObserver" in text


def test_goal_engine_inspector_injector_detects_goal_engine_nodes():
    text = read_app()

    assert "__isAionGoalEngineNode" in text
    assert 'value.includes("goal_engine.")' in text
    assert 'value.includes("aion_goal_engine")' in text
