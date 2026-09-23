from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_o19m2_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O19M2 HARD BIND AION START BUTTON LOCK" in text
    assert "O19M2 hard-bind AION start button installed" in text
    assert "__debugAionO19M2StartButtonBinding" in text


def test_o19m2_binds_existing_o19m_start_button_only():
    text = APP.read_text(encoding="utf-8")
    assert "[data-aion-o19m-start]" in text
    assert "data-aion-o19m2-bound" in text
    assert "startAionO19MOnboarding" in text
    assert "direct_click_bind" in text
    assert "document_capture_click" in text
    assert "pointerup" in text


def test_o19m2_does_not_create_new_voice_panel_or_o19l_overlay():
    text = APP.read_text(encoding="utf-8")
    block = text.split("BEGIN AION O19M2 HARD BIND AION START BUTTON LOCK", 1)[1].split("END AION O19M2 HARD BIND AION START BUTTON LOCK", 1)[0]
    assert "insertAdjacentHTML" not in block
    assert "data-aion-o19l-launcher" not in block
    assert "panelHtmlO19I" not in block
