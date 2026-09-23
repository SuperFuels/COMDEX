from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_founder_override_preview_controls_lock.tex")

def _text() -> str:
    assert DOC.exists(), "Founder Override Preview Controls lock doc must exist"
    return DOC.read_text()

def test_founder_override_doc_exists_and_is_locked():
    text = _text()
    assert "\\section{Phase 9F --- Founder Override Preview Controls v0}" in text
    assert "AION-BOARDROOM-FOUNDER-OVERRIDE-PREVIEW-CONTROLS-v0.1" in text
    assert "Status: LOCKED" in text

def test_founder_override_doc_lists_surface():
    text = _text()
    for term in [
        "desktop/mac/src/app.js",
        "installBoardroomFounderOverridePreviewControlsV0",
        "renderBoardroomFounderOverridePreviewControlsV0",
        "window.renderBoardroomFounderOverridePreviewControlsV0",
    ]:
        assert term in text

def test_founder_override_doc_lists_preview_actions():
    text = _text()
    for term in [
        "approve",
        "reject",
        "request\\_evidence",
        "escalate",
        "pause",
    ]:
        assert term in text

def test_founder_override_doc_mentions_guarded_path():
    text = _text()
    assert "future\\_guarded\\_approval\\_path" in text or "future_guarded_approval_path" in text

def test_founder_override_doc_states_safety():
    text = _text()
    for term in [
        "execute workflows",
        "create bookings",
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

def test_founder_override_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
