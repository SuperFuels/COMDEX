from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16h_founder_demo_visible_outputs_lock.tex")


def _extract_last_function(text: str, name: str) -> str:
    marker = f"function {name}("
    start = text.rfind(marker)
    assert start != -1, f"missing {name}"
    next_start = text.find("\nfunction ", start + len(marker))
    end_marker = text.find("/* END PHASE", start)
    candidates = [x for x in [next_start, end_marker] if x != -1]
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def test_phase16h_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()

    assert "PHASE 16H LOCK: Founder demo visible action output panels" in text
    assert "PHASE 16H LOCK: Founder demo visible action output panels" in css
    assert DOC.exists()


def test_phase16h_founder_loop_renders_visible_output_panel():
    text = APP.read_text()
    panel = _extract_last_function(text, "renderBoardroomFounderDemoLoopPanel")

    assert "renderAionFounderDemoVisibleOutputPanel(state)" in panel
    assert "data-aion-founder-visible-output" in text


def test_phase16h_run_preview_has_visible_request_artifact():
    text = APP.read_text()
    output = _extract_last_function(text, "getAionFounderDemoVisibleOutput")

    for phrase in [
        "Incoming website/widget request",
        "Home Fixed website/widget",
        "Roof leak / home repair request",
        "Public Intent Gateway → Guard Envelope → AgentMap route → Machine Cart",
        "Quote preview",
        "Not created",
    ]:
        assert phrase in output


def test_phase16h_human_review_has_visible_decision_artifact():
    text = APP.read_text()
    output = _extract_last_function(text, "getAionFounderDemoVisibleOutput")

    for phrase in [
        "Founder approval required",
        "Approve quote preview / reject / request more evidence",
        "External action blocked until founder approval",
        "Live execution",
        "Blocked",
    ]:
        assert phrase in output


def test_phase16h_proof_receipt_has_visible_receipt_artifact():
    text = APP.read_text()
    output = _extract_last_function(text, "getAionFounderDemoVisibleOutput")

    for phrase in [
        "Proof receipt preview",
        "Replay/hash proof available",
        "home_fixed_widget_trace_preview",
        "proof_receipt_preview",
        "preview-proof-hash",
        "GlyphChain write",
        "Not performed",
    ]:
        assert phrase in output


def test_phase16h_replay_trace_has_visible_timeline_artifact():
    text = APP.read_text()
    output = _extract_last_function(text, "getAionFounderDemoVisibleOutput")

    for phrase in [
        "Replay timeline",
        "Website/widget request",
        "Public Intent Gateway",
        "Guard Envelope",
        "AgentMap route",
        "Machine Cart quote preview",
        "Human Review handoff",
        "Boardroom replay",
    ]:
        assert phrase in output


def test_phase16h_visible_outputs_repeat_side_effect_guards():
    text = APP.read_text()
    output = _extract_last_function(text, "getAionFounderDemoVisibleOutput")

    for phrase in [
        "No booking created",
        "No payment created",
        "No escrow created",
        "No external message sent",
        "No live chain write",
        "Preview only",
    ]:
        assert phrase in output
