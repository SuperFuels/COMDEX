from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def _text() -> str:
    assert APP.exists(), "desktop/mac/src/app.js must exist"
    return APP.read_text()


def test_parallel_twin_panel_polish_renderer_exists():
    text = _text()
    assert "installBoardroomParallelTwinPanelPolishV0" in text
    assert "renderBoardroomParallelTwinPanelPolishV0" in text
    assert "window.renderBoardroomParallelTwinPanelPolishV0" in text
    assert "boardroom-parallel-twin-panel-polish-v0" in text


def test_parallel_twin_panel_polish_has_summary_cards():
    text = _text()
    for term in [
        "Summary Cards",
        "Business ID",
        "Job ID",
        "Vertical",
        "Payload Hash",
        "Human Review",
        "Proof Status",
        "Exception State",
    ]:
        assert term in text


def test_parallel_twin_panel_polish_keeps_core_sections():
    text = _text()
    for term in [
        "Machine Catalog",
        "Machine Cart",
        "Quote Preview",
        "Fulfilment Job",
        "Settlement Readiness",
        "Proof Receipt",
        "Exception Recovery",
        "Machine Trace",
    ]:
        assert term in text


def test_parallel_twin_panel_polish_preserves_read_only_safety():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinPanelPolishV0")
    assert section_start >= 0
    section = text[section_start:]

    for term in [
        "visibility_only",
        "human_review_required",
        "autonomous_execution_allowed",
        "would_execute_workflow",
        "would_create_booking",
        "would_move_money",
        "would_move_pho",
        "would_require_wallet",
        "would_create_payment",
        "would_create_escrow",
        "would_send_external_message",
        "public_a2a_route_exposed",
    ]:
        assert term in section


def test_parallel_twin_panel_polish_has_no_live_execute_controls():
    text = _text()
    section_start = text.find("installBoardroomParallelTwinPanelPolishV0")
    assert section_start >= 0
    section = text[section_start:]

    banned = [
        "Execute Now",
        "Run Live",
        "Create Booking",
        "Take Payment",
        "Create Escrow",
        "Send Message",
        "Charge Customer",
        "Submit Public A2A",
    ]

    for term in banned:
        assert term not in section
