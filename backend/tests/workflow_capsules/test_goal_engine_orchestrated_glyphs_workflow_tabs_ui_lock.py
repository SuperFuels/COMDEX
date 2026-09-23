from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_orchestrated_glyphs_panel_renderer_exists():
    text = APP.read_text()
    assert "function renderAionGoalEngineOrchestratedGlyphsPanelV1" in text
    assert 'data-aion-goal-engine-orchestrated-glyphs="v1"' in text
    assert "Orchestrated Glyphs" in text


def test_orchestrated_glyphs_panel_reads_parent_child_payloads():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineOrchestratedGlyphsPanelV1"):
        text.index("window.renderAionGoalEngineOrchestratedGlyphsPanelV1")
    ]
    assert "orchestrator_parent_child_aggregation_runtime_summary" in block
    assert "parent_child_aggregation_runtime_summary" in block
    assert "orchestrator_parent_child_aggregation_previews" in block
    assert "parent_child_aggregation_previews" in block
    assert "child_glyphs" in block


def test_orchestrated_glyphs_panel_is_visibility_only():
    text = APP.read_text()
    block = text[
        text.index("function renderAionGoalEngineOrchestratedGlyphsPanelV1"):
        text.index("window.renderAionGoalEngineOrchestratedGlyphsPanelV1")
    ]
    assert "visibility only" in block
    assert "does not execute child glyphs" in block
    assert "would_mutate_parent_goal" in block


def test_orchestrated_glyphs_panel_mounts_into_glyph_workflow_tab():
    text = APP.read_text()
    assert "renderAionGoalEngineOrchestratedGlyphsPanelV1(source)" in text
    assert "renderGlyphWorkflowTab" in text
    assert "window.__renderAionGlyphWorkflowTab" in text


def test_orchestrated_glyphs_panel_exports_window_renderer():
    text = APP.read_text()
    assert "window.renderAionGoalEngineOrchestratedGlyphsPanelV1" in text


def test_orchestrated_glyphs_lock_in_focused_suite():
    text = SUITE.read_text()
    assert "test_goal_engine_orchestrated_glyphs_workflow_tabs_ui_lock.py" in text
