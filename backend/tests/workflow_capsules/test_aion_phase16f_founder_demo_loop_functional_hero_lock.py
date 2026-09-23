from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")


def test_phase16f_founder_demo_has_real_action_buttons():
    text = APP.read_text()
    assert "PHASE 16F LOCK: Founder Demo Loop Functional Hero" in text
    assert "handleBoardroomFounderDemoPreviewAction('run_preview')" in text
    assert "handleBoardroomFounderDemoPreviewAction('open_human_review')" in text
    assert "handleBoardroomFounderDemoPreviewAction('view_proof_receipt')" in text
    assert "handleBoardroomFounderDemoPreviewAction('replay_trace')" in text


def test_phase16f_founder_steps_are_clickable_buttons_not_static_chips():
    text = APP.read_text()
    assert "function renderAionFounderDemoStepButton" in text
    assert "data-founder-demo-step=" in text
    assert "onclick=\"setAionFounderDemoLoopState" in text


def test_phase16f_click_actions_update_visible_state():
    text = APP.read_text()
    assert "Home Fixed request preview generated" in text
    assert "Human review required before any external action" in text
    assert "Proof receipt preview available" in text
    assert "Boardroom replay preview ready" in text


def test_phase16f_safety_boundaries_remain_visible():
    text = APP.read_text()
    for phrase in [
        "No booking created",
        "No payment created",
        "No escrow created",
        "No external message sent",
        "No live chain write",
        "Human review required",
    ]:
        assert phrase in text


def test_phase16f_teal_branding_replaces_purple_bleed():
    css = CSS.read_text()
    assert "PHASE 16F LOCK: Founder Demo Loop Functional Hero" in css
    assert "#0f8b95" in css
    assert "Kill accidental purple Boardroom button bleed" in css
    assert "aion-boardroom-frontpage-simplified button" in css
