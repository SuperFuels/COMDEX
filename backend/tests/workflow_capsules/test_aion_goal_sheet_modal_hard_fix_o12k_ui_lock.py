from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o12k_retired_by_o12l():
    assert "O12K disabled by O12L" in APP_JS
    assert "whole-DOM MutationObserver caused sluggish canvas response" in APP_JS


def test_o12m_replaces_o12k_runtime_behavior():
    assert "BEGIN AION O12M FINAL LIGHTWEIGHT GOAL SHEET MODAL POLISH" in APP_JS
    assert "final lightweight Goal Sheet modal polish installed" in APP_JS


def test_o12m_keeps_modal_lightweight():
    block = APP_JS.split("BEGIN AION O12M FINAL LIGHTWEIGHT GOAL SHEET MODAL POLISH", 1)[1]
    block = block.split("END AION O12M FINAL LIGHTWEIGHT GOAL SHEET MODAL POLISH", 1)[0]
    assert "MutationObserver" not in block
    assert "document.addEventListener(\"click\"" in block


def test_o12m_removes_cream_and_shadow():
    assert "forceWhiteModalSurface" in APP_JS
    assert "background: #ffffff" in APP_JS
    assert "box-shadow: none" in APP_JS
    assert "data-aion-o12m-modal-header" in APP_JS


def test_o12m_hides_green_status_badge():
    assert "hideStagedBadge" in APP_JS
    assert "Boardroom Goal Sheet staged" in APP_JS
    assert "aion-o12m-goal-modal-open" in APP_JS


def test_o12m_close_button_and_escape_close_modal():
    assert "closeGoalSheetModal" in APP_JS
    assert "data-aion-o12m-close" in APP_JS
    assert "window.aionCloseGoalSheetModalO12M" in APP_JS
    assert "event.key !== \"Escape\"" in APP_JS


def test_o12m_clears_modal_state():
    assert "clearModalState" in APP_JS
    assert "window.__aionGoalSheetDocumentModalOpen = false" in APP_JS
    assert "window.__aionSelectedGoalSheetDocument = null" in APP_JS
