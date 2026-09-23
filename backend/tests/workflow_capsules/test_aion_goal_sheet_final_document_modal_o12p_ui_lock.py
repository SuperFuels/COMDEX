from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12p_installed():
    assert "BEGIN AION O12P FINAL GOAL SHEET DOCUMENT MODAL HEADER SCROLL FIX" in APP_JS
    assert "final Goal Sheet document modal header/scroll fix installed" in APP_JS


def test_o12p_forces_clean_white_modal_and_neutral_header():
    assert "data-aion-o12p-goal-doc-modal" in APP_JS
    assert "data-aion-o12p-goal-doc-header" in APP_JS
    assert "background: #ffffff" in APP_JS
    assert "background: #f8fafc" in APP_JS
    assert "border-radius: 18px 18px 0 0" in APP_JS


def test_o12p_body_is_scroll_container():
    assert "data-aion-o12p-goal-doc-body" in APP_JS
    assert "overflow-y: auto" in APP_JS
    assert "overscroll-behavior: contain" in APP_JS
    assert "body.scrollTop += event.deltaY" in APP_JS


def test_o12p_hides_staged_green_status_badges():
    assert "hideFloatingStatusBadges" in APP_JS
    assert "Boardroom Goal Sheet staged" in APP_JS
    assert "Pilot queue preview" in APP_JS
    assert "display\", \"none\", \"important\"" in APP_JS


def test_o12p_close_button_and_escape_work():
    assert "closeGoalDocModal" in APP_JS
    assert "data-aion-o12p-goal-doc-close" in APP_JS
    assert "event.key !== \"Escape\"" in APP_JS
    assert "window.aionCloseGoalSheetDocumentModalO12P" in APP_JS


def test_o12p_no_mutation_observer():
    block = APP_JS.split("BEGIN AION O12P FINAL GOAL SHEET DOCUMENT MODAL HEADER SCROLL FIX", 1)[1]
    block = block.split("END AION O12P FINAL GOAL SHEET DOCUMENT MODAL HEADER SCROLL FIX", 1)[0]
    assert "MutationObserver" not in block
