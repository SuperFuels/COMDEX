from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE H2")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE H2 */", start)
    return APP_JS[start:end]


def test_phase_h2_helpers_and_statuses_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_CROSS_FUNCTION_CONFLICT_STATUSES" in block
    assert "function normaliseAionGoalLoopCrossFunctionConflictStatus" in block
    assert "function buildAionGoalLoopCrossFunctionConflictNode" in block
    assert "function previewAionGoalLoopCrossFunctionConflictNodes" in block
    assert "function renderAionGoalLoopCrossFunctionConflictPanel" in block

    for status in ["open", "accepted", "rejected", "resolved"]:
        assert status in block


def test_phase_h2_conflict_node_fields_are_locked():
    block = function_block("buildAionGoalLoopCrossFunctionConflictNode")

    for field in [
        "conflict_id",
        "node_type",
        "cross_function_conflict",
        "goal_loop_id",
        "source_analysis_id",
        "pattern_id",
        "departments",
        "status",
        "severity",
        "finding",
        "recommendation",
        "required_action",
        "affected_department_links",
        "boardroom_review_link",
        "graph_patch_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_cross_function_conflict_node.v1" in block


def test_phase_h2_links_conflict_node_to_departments_boardroom_and_analysis():
    block = function_block("buildAionGoalLoopCrossFunctionConflictNode")

    assert "affected_department" in block
    assert "materialises_as_conflict_node" in block
    assert "affected_by_cross_function_conflict" in block
    assert "requires_boardroom_review" in block
    assert "cross_function_conflict" in block
    assert "needs_board_decision" in block


def test_phase_h2_preview_builds_conflict_nodes_from_h1_findings():
    block = function_block("previewAionGoalLoopCrossFunctionConflictNodes")

    assert "previewAionGoalLoopCrossFunctionAnalysis" in block
    assert "findings" in block
    assert "buildAionGoalLoopCrossFunctionConflictNode" in block
    assert "conflict_nodes" in block
    assert "boardroom_review_links" in block
    assert "node_updates" in block
    assert "edge_additions" in block
    assert "open_conflict_count" in block


def test_phase_h2_renderer_exposes_visible_conflict_panel():
    block = function_block("renderAionGoalLoopCrossFunctionConflictPanel")

    assert 'data-aion-goal-loop-cross-function-conflict-panel="true"' in block
    assert 'data-aion-goal-loop-conflict-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-conflict-count="true"' in block
    assert 'data-aion-goal-loop-open-conflict-count="true"' in block
    assert 'data-aion-goal-loop-conflict-safety="true"' in block
    assert 'data-aion-goal-loop-conflict-statuses="true"' in block
    assert 'data-aion-goal-loop-conflict-nodes="true"' in block
    assert 'data-aion-goal-loop-conflict-preview-boundary="true"' in block


def test_phase_h2_is_preview_only_safe_boundary():
    block = phase_block()
    forbidden = block.lower()

    assert "preview_only: true" in block
    assert "graph_mutation_required: false" in block
    assert "persistence_required: false" in block
    assert "execution_blocked: true" in block
    assert "external_side_effects: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block

    assert "fetch(" not in forbidden
    assert "send_email" not in forbidden
    assert "create_event" not in forbidden
    assert "payment_created: true" not in forbidden
    assert "booking_created: true" not in forbidden


def test_phase_h2_is_mounted_after_h1_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopCrossFunctionAnalysisPanel()}" in APP_JS
    assert "${renderAionGoalLoopCrossFunctionConflictPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    h1_index = APP_JS.index("${renderAionGoalLoopCrossFunctionAnalysisPanel()}")
    h2_index = APP_JS.index("${renderAionGoalLoopCrossFunctionConflictPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert h1_index < h2_index < cockpit_index
