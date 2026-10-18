from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def phase_block():
    start = APP_JS.index("/* AION GOAL LOOP CANVAS PHASE H1")
    end = APP_JS.index("/* END AION GOAL LOOP CANVAS PHASE H1 */", start)
    return APP_JS[start:end]


def test_phase_h1_helpers_and_patterns_exist():
    block = phase_block()

    assert "AION_GOAL_LOOP_CROSS_FUNCTION_PATTERNS" in block
    assert "function getAionGoalLoopDepartmentSignalFromFeedback" in block
    assert "function buildAionGoalLoopCrossFunctionAnalysis" in block
    assert "function previewAionGoalLoopCrossFunctionAnalysis" in block
    assert "function renderAionGoalLoopCrossFunctionAnalysisPanel" in block


def test_phase_h1_detects_required_cross_function_patterns():
    block = phase_block()

    for pattern in [
        "marketing_sales_mismatch",
        "sales_operations_mismatch",
        "marketing_finance_mismatch",
        "support_sales_objection_mismatch",
        "operations_support_review_mismatch",
    ]:
        assert pattern in block

    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert department in block


def test_phase_h1_finding_object_fields_are_locked():
    block = function_block("buildAionGoalLoopCrossFunctionAnalysis")

    for field in [
        "analysis_id",
        "pattern_id",
        "goal_loop_id",
        "finding",
        "departments",
        "severity",
        "triggered",
        "recommendation",
        "required_action",
        "department_signals",
        "related_decision_ids",
        "boardroom_review_item",
        "graph_patch_preview",
        "provenance",
    ]:
        assert field in block

    assert "aion.goal_loop_cross_function_analysis.v1" in block
    assert "aion.goal_loop_cross_function_finding.v1" in block


def test_phase_h1_boardroom_review_and_graph_patch_are_preview_safe():
    block = function_block("buildAionGoalLoopCrossFunctionAnalysis")

    assert "cross_function_analysis" in block
    assert "needs_board_decision" in block
    assert "add_or_update_node" in block
    assert "contributes_to_cross_function_analysis" in block
    assert "graph_mutation_required: false" in block
    assert "boardroom_review_items" in block
    assert "node_updates" in block
    assert "edge_additions" in block


def test_phase_h1_renderer_exposes_visible_cross_function_panel():
    block = function_block("renderAionGoalLoopCrossFunctionAnalysisPanel")

    assert 'data-aion-goal-loop-cross-function-analysis-panel="true"' in block
    assert 'data-aion-goal-loop-cross-function-goal-loop-id="true"' in block
    assert 'data-aion-goal-loop-cross-function-finding-count="true"' in block
    assert 'data-aion-goal-loop-cross-function-triggered-count="true"' in block
    assert 'data-aion-goal-loop-cross-function-safety="true"' in block
    assert 'data-aion-goal-loop-cross-function-findings="true"' in block
    assert 'data-aion-goal-loop-cross-function-preview-boundary="true"' in block


def test_phase_h1_is_preview_only_safe_boundary():
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


def test_phase_h1_is_mounted_after_g2_inside_existing_central_pilot_area():
    assert "${renderAionGoalLoopBoardroomFeedbackDecisionPanel()}" in APP_JS
    assert "${renderAionGoalLoopCrossFunctionAnalysisPanel()}" in APP_JS
    assert "${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}" in APP_JS

    g2_index = APP_JS.index("${renderAionGoalLoopBoardroomFeedbackDecisionPanel()}")
    h1_index = APP_JS.index("${renderAionGoalLoopCrossFunctionAnalysisPanel()}")
    cockpit_index = APP_JS.index("${renderAionPilotCockpitPanel(getAionPilotCockpitSnapshot())}")

    assert g2_index < h1_index < cockpit_index
