from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_parallel_twin_panel_polish_lock.tex")

def _text() -> str:
    assert DOC.exists(), "panel polish lock doc must exist"
    return DOC.read_text()

def test_panel_polish_doc_exists_and_is_locked():
    text = _text()
    assert "\\section{Boardroom Parallel Twin Panel Polish v0}" in text
    assert "AION-BOARDROOM-PARALLEL-TWIN-PANEL-POLISH-v0.1" in text
    assert "Status: LOCKED" in text

def test_panel_polish_doc_lists_implemented_surface():
    text = _text()
    for term in [
        "desktop/mac/src/app.js",
        "installBoardroomParallelTwinPanelPolishV0",
        "renderBoardroomParallelTwinPanelPolishV0",
        "window.renderBoardroomParallelTwinPanelPolishV0",
    ]:
        assert term in text

def test_panel_polish_doc_lists_summary_cards():
    text = _text()
    for term in [
        "Business ID",
        "Job ID",
        "Vertical",
        "Payload Hash",
        "Human Review",
        "Proof Status",
        "Exception State",
    ]:
        assert term in text

def test_panel_polish_doc_lists_core_sections():
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

def test_panel_polish_doc_states_safety_boundary():
    text = _text()
    for term in [
        "read-only",
        "execute button",
        "create a booking",
        "execute the Goal Engine",
        "bypass human review",
        "move money",
        "move PHO",
        "require a wallet",
        "create a payment",
        "create escrow",
        "send external messages",
        "public A2A route",
    ]:
        assert term in text

def test_panel_polish_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
