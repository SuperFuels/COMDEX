from pathlib import Path

DOC = Path("docs/rfc/aion_boardroom_frontend_manual_smoke_confirmation_lock.tex")

def _text() -> str:
    assert DOC.exists(), "frontend manual smoke confirmation lock doc must exist"
    return DOC.read_text()

def test_manual_smoke_doc_exists():
    text = _text()
    assert "\\section{Phase 9G --- Frontend Manual Smoke Confirmation v0}" in text
    assert "AION-BOARDROOM-FRONTEND-MANUAL-SMOKE-CONFIRMATION-v0.1" in text

def test_manual_smoke_doc_lists_boardroom_visibility_checks():
    text = _text()
    for term in [
        "Boardroom view opens",
        "Home Fixed Parallel Twin panel is visible",
        "fallback payload renders",
        "summary cards are visible",
        "payload hash",
        "business identifier",
        "job identifier",
        "vertical key",
        "proof status",
        "exception state",
        "human review status",
    ]:
        assert term in text

def test_manual_smoke_doc_lists_founder_controls():
    text = _text()
    assert "Founder Override preview controls are visible" in text
    assert "Founder Override controls are disabled" in text

def test_manual_smoke_doc_states_no_live_actions():
    text = _text()
    for term in [
        "no live execute button appears",
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

def test_manual_smoke_doc_uses_tessaris_footer():
    text = _text()
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
