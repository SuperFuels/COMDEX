from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12q_installed():
    assert "BEGIN AION O12Q HARD GOAL SHEET DOCUMENT MODAL CLOSE FIX" in APP_JS
    assert "hard Goal Sheet document modal close fix installed" in APP_JS


def test_o12q_finds_all_modal_variants():
    assert "getAllGoalSheetModalCandidates" in APP_JS
    assert "BOARDROOM GOAL SHEET DOCUMENT" in APP_JS
    assert "data-aion-o12p-goal-doc-modal" in APP_JS
    assert "data-aion-o12l-goal-modal" in APP_JS


def test_o12q_clears_all_modal_state():
    assert "clearGoalSheetModalState" in APP_JS
    assert "window.__aionO12BGoalSheetSelectedDocumentId = null" in APP_JS
    assert "window.__aionGoalSheetDocumentModalOpen = false" in APP_JS


def test_o12q_removes_modal_from_dom():
    assert "hardCloseGoalSheetDocumentModal" in APP_JS
    assert "modal.remove()" in APP_JS
    assert "data-aion-o12q-force-hidden" in APP_JS


def test_o12q_uses_pointerdown_and_click_capture():
    assert 'document.addEventListener("pointerdown"' in APP_JS
    assert 'document.addEventListener("click"' in APP_JS
    assert "stopImmediatePropagation" in APP_JS


def test_o12q_escape_closes_modal():
    assert 'event.key !== "Escape"' in APP_JS
    assert "aionHardCloseGoalSheetDocumentModalO12Q" in APP_JS


def test_o12q_no_mutation_observer():
    block = APP_JS.split("BEGIN AION O12Q HARD GOAL SHEET DOCUMENT MODAL CLOSE FIX", 1)[1]
    block = block.split("END AION O12Q HARD GOAL SHEET DOCUMENT MODAL CLOSE FIX", 1)[0]
    assert "MutationObserver" not in block
