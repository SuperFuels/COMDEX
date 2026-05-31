from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")
DOC = Path("docs/rfc/aion_phase16e_founder_demo_action_wiring_lock.tex")


def _extract_last_function(text: str, name: str) -> str:
    marker = f"function {name}"
    start = text.rfind(marker)
    assert start != -1, f"missing {name}"
    next_start = text.find("\nfunction ", start + len(marker))
    end_marker = text.find("/* END PHASE 16E LOCK */", start)
    candidates = [x for x in [next_start, end_marker] if x != -1]
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def test_phase16e_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()

    assert "PHASE 16E LOCK: Founder demo action wiring" in text
    assert "PHASE 16E LOCK: Founder demo action wiring" in css
    assert DOC.exists()


def test_phase16e_payload_contains_full_founder_demo_route():
    text = APP.read_text()
    payload = _extract_last_function(text, "getBoardroomFounderDemoPreviewPayload")

    for phrase in [
        "Home Fixed website/widget request",
        "Public Intent Gateway",
        "Guard Envelope",
        "AgentMap / capability route",
        "Machine Cart / quote preview",
        "Human Review handoff",
        "Founder decision preview",
        "FulfilmentJob preview",
        "Evidence preview",
        "Proof receipt preview",
        "ETS preview",
        "Boardroom replay",
    ]:
        assert phrase in payload


def test_phase16e_action_handler_wires_four_demo_actions():
    text = APP.read_text()
    handler = _extract_last_function(text, "handleBoardroomFounderDemoPreviewAction")

    for action in [
        "run_preview",
        "open_human_review",
        "view_proof_receipt",
        "replay_trace",
    ]:
        assert action in handler

    for guard in [
        "booking_created: false",
        "payment_created: false",
        "escrow_created: false",
        "external_message_sent: false",
        "live_chain_write: false",
        "live_execution_allowed: false",
        "human_review_required: true",
        "replay_hash_available: true",
    ]:
        assert guard in handler

    assert "requestRender?.()" in handler


def test_phase16e_front_page_buttons_call_action_handler():
    text = APP.read_text()
    panel = _extract_last_function(text, "renderBoardroomFounderDemoLoopPanel")

    assert "data-aion-phase16e-founder-demo-actions" in panel
    assert "handleBoardroomFounderDemoPreviewAction" in panel
    assert "data-founder-demo-action" in panel
    assert "data-aion-founder-demo-active-state" in panel
    assert "renderBoardroomFounderDemoSafetyStrip" in panel


def test_phase16e_human_review_queue_wraps_old_approval_queue():
    text = APP.read_text()
    panel = _extract_last_function(text, "renderBoardroomHumanReviewQueuePanel")

    assert "data-aion-boardroom-human-review-queue" in panel
    assert "Founder decision preview" in panel
    assert "renderBoardroomWorkflowCapsuleApprovalQueue(approvals)" in panel
    assert "No booking/payment/escrow" in panel


def test_phase16e_proof_replay_prioritises_home_fixed_and_guards():
    text = APP.read_text()
    panel = _extract_last_function(text, "renderBoardroomProofReplayPanel")

    for phrase in [
        "Home Fixed widget request",
        "Proof receipt",
        "ETS preview",
        "Replay hash",
        "No booking created",
        "No payment created",
        "No escrow created",
        "No external message sent",
        "No live chain write",
        "Human review required",
        "Older workflow run history",
    ]:
        assert phrase in panel

    assert "handleBoardroomFounderDemoPreviewAction('view_proof_receipt')" in panel
    assert "handleBoardroomFounderDemoPreviewAction('replay_trace')" in panel


def test_phase16e_css_has_action_and_guard_polish():
    css = CSS.read_text()

    for selector in [
        ".aion-phase16e-founder-demo-actions",
        ".aion-founder-demo-active-state",
        ".aion-founder-demo-step-card",
        ".aion-founder-demo-guard-grid",
        ".aion-phase16e-proof-replay",
    ]:
        assert selector in css


def test_phase16e_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "backend/tests/workflow_capsules/test_aion_phase16e_founder_demo_action_wiring_lock.py" in suite
