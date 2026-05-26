from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")


def test_parent_child_orchestration_panel_exists():
    text = APP.read_text()
    assert "AION-GOAL-ENGINE-PARENT-CHILD-ORCHESTRATION-PANEL-V1:START" in text
    assert "function renderAionGoalEngineParentChildOrchestrationPanelV1" in text
    assert 'data-aion-goal-engine-parent-child-orchestration="v1"' in text


def test_parent_child_orchestration_reads_canonical_preview():
    text = APP.read_text()
    assert 'value.trace_type === "orchestrator_parent_child_aggregation_preview"' in text
    assert "parent_child_aggregation_preview" in text
    assert "parent_child_aggregation_previews" in text
    assert "orchestrator_parent_child_aggregation_preview" in text


def test_parent_child_orchestration_is_visibility_only():
    text = APP.read_text()
    start = text.index("AION-GOAL-ENGINE-PARENT-CHILD-ORCHESTRATION-PANEL-V1:START")
    end = text.index("AION-GOAL-ENGINE-PARENT-CHILD-ORCHESTRATION-PANEL-V1:END")
    block = text[start:end]

    assert "does not execute children" in block
    assert "mutate parent goals" in block
    assert "write externally" in block
    assert "grant permission" in block
    assert "would_mutate_parent_goal" in block
    assert "would_grant_permission" in block


def test_parent_child_orchestration_mounted_in_visibility_audit():
    text = APP.read_text()
    assert "renderAionGoalEngineParentChildOrchestrationPanelV1(snapshot)" in text
    assert "renderAionGoalEngineBoardroomVisibilityMountAuditV1" in text


def test_parent_child_orchestration_demo_payload_exists():
    text = APP.read_text()
    assert 'parent_goal_id: "goal_visible_demo"' in text
    assert 'agent_id: "agent_marketing"' in text
    assert 'glyph_code: "WD-101"' in text
    assert 'aggregate_status: "blocked_child_requires_review"' in text


def test_parent_child_orchestration_css_exists():
    text = CSS.read_text()
    assert "AION-GOAL-ENGINE-PARENT-CHILD-ORCHESTRATION-CSS-V1:START" in text
    assert ".aion-boardroom-parent-child-orchestration-panel" in text
    assert ".aion-boardroom-parent-child-card" in text
    assert ".aion-boardroom-parent-child-row" in text
