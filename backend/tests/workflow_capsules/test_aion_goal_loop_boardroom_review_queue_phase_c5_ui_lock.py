from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = APP_JS.index(f"function {name}")
    next_fn = APP_JS.find("\nfunction ", start + 1)
    if next_fn == -1:
        return APP_JS[start:]
    return APP_JS[start:next_fn]


def test_phase_c5_review_queue_is_mounted_after_status_panel():
    assert "${renderAionBoardroomGoalLoopActiveStatusPanel(snapshot)}" in APP_JS
    assert "${renderAionBoardroomGoalLoopReviewQueuePanel(snapshot)}" in APP_JS

    status_index = APP_JS.index("${renderAionBoardroomGoalLoopActiveStatusPanel(snapshot)}")
    queue_index = APP_JS.index("${renderAionBoardroomGoalLoopReviewQueuePanel(snapshot)}")

    assert status_index < queue_index


def test_phase_c5_queue_builder_reads_goal_loop_status_and_graph_nodes():
    block = function_block("buildAionBoardroomGoalLoopReviewQueue")

    assert "getAionBoardroomActiveGoalLoopStatus" in block
    assert "window.__aionWorkflowGraph" in block
    assert "window.__aionGoalLoopWorkflowGraph" in block
    assert 'findNodes("feedback_to_board")' in block
    assert 'findNodes("evaluation")' in block
    assert 'findNodes("evidence_receipt")' in block
    assert 'findNodes("board_adjustment")' in block
    assert 'findNodes("department_assignment")' in block
    assert 'findNodes("department_plan")' in block


def test_phase_c5_queue_statuses_are_visible_and_preview_safe():
    block = function_block("buildAionBoardroomGoalLoopReviewQueue")

    assert "needs_review" in block
    assert "needs_board_decision" in block
    assert "evidence_ready" in block
    assert "adjustment_proposed" in block
    assert "preview_only: true" in block
    assert "execution_blocked: true" in block
    assert "persistence_required: false" in block
    assert "route_mutation_required: false" in block


def test_phase_c5_renderer_exposes_visible_review_queue_controls():
    block = function_block("renderAionBoardroomGoalLoopReviewQueuePanel")

    assert 'data-aion-goal-loop-review-queue-panel="true"' in block
    assert 'data-aion-goal-loop-review-item-count="true"' in block
    assert 'data-aion-goal-loop-review-queue-list="true"' in block
    assert 'data-aion-goal-loop-review-action="review"' in block
    assert 'data-aion-goal-loop-review-action="pause"' in block
    assert 'data-aion-goal-loop-review-action="continue"' in block
    assert 'data-aion-goal-loop-review-action="request_more_data"' in block
    assert "Preview boundary" in block
    assert "do not persist, execute, approve" in block


def test_phase_c5_action_handler_has_no_side_effects():
    block = function_block("handleAionBoardroomGoalLoopReviewQueueAction")

    assert "preview_only: true" in block
    assert "execution_blocked: true" in block
    assert "persistence_required: false" in block
    assert "route_mutation_required: false" in block
    assert "external_side_effects: false" in block
    assert "message_sent: false" in block
    assert "booking_created: false" in block
    assert "payment_created: false" in block


def test_phase_c5_does_not_create_second_canvas_or_second_pilot():
    block = APP_JS[
        APP_JS.index("/* AION GOAL LOOP BOARDROOM PHASE C5"):
        APP_JS.index("/* END AION GOAL LOOP BOARDROOM PHASE C5 */")
    ]

    forbidden = block.lower()
    assert "new aionpilot" not in forbidden
    assert "renderaiongoalloopcanvas(" not in forbidden
    assert "data-aion-goal-loop-canvas-root" not in forbidden
    assert "creates_second_canvas: false" in block
    assert "creates_second_pilot: false" in block
