from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")
DOC = Path("docs/rfc/aion_phase16i_home_fixed_intake_quote_preview_lock.tex")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")


def test_phase16i_lock_markers_exist():
    text = APP.read_text()
    css = CSS.read_text()

    assert "PHASE 16I LOCK: Home Fixed intake + quote preview" in text
    assert "PHASE 16I LOCK: Home Fixed intake + quote preview" in css
    assert DOC.exists()


def test_phase16i_home_fixed_intake_payload_is_realistic():
    text = APP.read_text()

    for phrase in [
        "leaking pergola roof repaired in Arboleas",
        "Pergola / roof repair",
        "Arboleas, Almería",
        "Medium / rain-related",
        "Home Fixed website widget",
    ]:
        assert phrase in text


def test_phase16i_quote_preview_is_visible_and_guarded():
    text = APP.read_text()

    for phrase in [
        "Machine Cart Quote Preview",
        "Pergola roof leak repair",
        "€120–€380 preview range",
        "inspection_required",
        "Site visit required before final quote",
        "No booking created",
        "No payment created",
        "No escrow created",
        "Human review required",
    ]:
        assert phrase in text


def test_phase16i_founder_loop_renders_intake_card():
    text = APP.read_text()

    assert "function renderAionHomeFixedIntakeQuotePreview" in text
    assert "data-aion-phase16i-intake-quote-preview" in text
    assert "data-aion-machine-cart-quote-preview" in text
    assert "renderAionHomeFixedIntakeQuotePreview()" in text


def test_phase16i_route_keeps_a2a_path_visible():
    text = APP.read_text()

    for phrase in [
        "Website widget",
        "Public Intent Gateway",
        "Guard Envelope",
        "AgentMap route",
        "Machine Cart quote preview",
        "Human Review handoff",
    ]:
        assert phrase in text


def test_phase16i_css_has_intake_and_quote_styles():
    css = CSS.read_text()

    for selector in [
        ".aion-phase16i-intake-card",
        ".aion-phase16i-intake-grid",
        ".aion-phase16i-route",
        ".aion-phase16i-quote-card",
        ".aion-phase16i-guard-grid",
    ]:
        assert selector in css


def test_phase16i_is_in_focused_suite():
    suite = SUITE.read_text()
    assert "test_aion_phase16i_home_fixed_intake_quote_preview_lock.py" in suite

def test_phase16i_intake_quote_is_mounted_when_run_preview_selected():
    text = APP.read_text()

    assert 'activeStep === "machine_cart_quote_preview"' in text
    assert 'lastAction === "run_preview"' in text
    assert "showHomeFixedIntakeQuote" in text
    assert "renderAionHomeFixedIntakeQuotePreview()" in text

