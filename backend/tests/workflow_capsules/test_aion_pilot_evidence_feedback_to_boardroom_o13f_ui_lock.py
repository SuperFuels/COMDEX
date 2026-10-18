from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13F PILOT EVIDENCE FEEDBACK TO BOARDROOM GOAL SHEET" in APP_JS
    return APP_JS.split("BEGIN AION O13F PILOT EVIDENCE FEEDBACK TO BOARDROOM GOAL SHEET", 1)[1].split(
        "END AION O13F PILOT EVIDENCE FEEDBACK TO BOARDROOM GOAL SHEET", 1
    )[0]


def test_o13f_installed():
    b = block()
    assert "Pilot evidence feedback to Boardroom Goal Sheet installed" in b
    assert "aionBuildBoardroomEvidenceFeedbackPacketO13F" in b
    assert "aionAttachEvidenceFeedbackToBoardroomGoalSheetO13F" in b


def test_o13f_targets_evidence_feedback_node_and_board_decision_loop():
    b = block()
    assert 'EVIDENCE_NODE_ID = "goal_sheet_evidence_feedback"' in b
    assert 'DECISION_NODE_ID = "goal_sheet_board_decision"' in b
    assert "loop_back_to_boardroom_decision: true" in b
    assert "next_board_decision_required = true" in b


def test_o13f_builds_evidence_records_from_pilot_tasks():
    b = block()
    assert "buildEvidenceRecordFromTaskO13F" in b
    assert "task_packet_id" in b
    assert "source_workflow_id" in b
    assert "source_node_id" in b
    assert "agent_owner" in b
    assert "pilot_surface" in b


def test_o13f_updates_boardroom_goal_sheet_node_payload():
    b = block()
    assert "evidenceNode.data" in b
    assert "boardroom_evidence_feedback_packet" in b
    assert "department_summary" in b
    assert "evidence_records" in b
    assert "graph.goal_progress" in b


def test_o13f_preview_only_no_side_effects():
    b = block()
    assert "preview_only: true" in b
    assert "execution_allowed_now: false" in b
    assert "connector_call_required: false" in b
    assert "external_side_effects: false" in b
    assert "persistence_required: false" in b
    assert "graph_mutation_required: false" in b
    assert "no_live_execution: true" in b
    assert "no_connector_calls: true" in b


def test_o13f_renders_boardroom_evidence_feedback_panel():
    b = block()
    assert "renderBoardroomEvidenceFeedbackPanelO13F" in b
    assert "data-aion-o13f-boardroom-evidence-feedback-panel" in b
    assert "Pilot evidence → Boardroom Goal Sheet" in b
    assert "Evidence feedback waiting for Boardroom review" in b


def test_o13f_wraps_existing_boardroom_actions_panel():
    b = block()
    assert "renderAionCentralApprovedBoardroomActionsPanel" in b
    assert "renderAionCentralApprovedBoardroomActionsPanelWithEvidenceFeedback" in b
    assert "__aionO13FWrapped" in b
    assert "return `${panel}${originalHtml}`" in b


def test_o13f_listens_to_o13d_preview_state_event():
    b = block()
    assert "aion:goal-sheet-pilot-preview-state" in b
    assert "document.addEventListener" in b
    assert "window.addEventListener" in b


def test_o13f_supports_all_departments():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b
