from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    return APP_JS.split("BEGIN AION O12S CANONICAL GOAL SHEET DOCUMENT MODAL TAKEOVER", 1)[1].split(
        "END AION O12S CANONICAL GOAL SHEET DOCUMENT MODAL TAKEOVER", 1
    )[0]


def test_o12s_installed():
    assert "BEGIN AION O12S CANONICAL GOAL SHEET DOCUMENT MODAL TAKEOVER" in APP_JS
    assert "canonical Goal Sheet document modal takeover installed" in APP_JS


def test_o12s_intercepts_goal_sheet_node_click_before_old_handlers():
    b = block()
    assert "isGoalSheetNodeClick" in b
    assert "openCanonicalModal(nodeId, event)" in b
    assert "event.stopImmediatePropagation()" in b


def test_o12s_uses_single_canonical_modal_id():
    b = block()
    assert 'MODAL_ID = "aion-o12s-canonical-goal-sheet-document-modal"' in b
    assert "document.getElementById(MODAL_ID)" in b
    assert "modal.innerHTML = buildModalHtml(node)" in b


def test_o12s_header_is_not_cream_and_has_no_mixed_radius():
    b = block()
    assert ".aion-o12s-goal-doc-header" in b
    assert "background: #f8fafc" in b
    assert "border-radius: 0" in b
    assert "#fbf3e7" not in b
    assert "#fff7ed" not in b


def test_o12s_body_scroll_is_enabled_and_canvas_wheel_is_blocked():
    b = block()
    assert "overflow-y: auto" in b
    assert "data-aion-o12s-goal-doc-body" in b
    assert 'document.addEventListener("wheel"' in b
    assert "event.stopPropagation()" in b


def test_o12s_close_does_not_request_render_and_removes_modal():
    b = block()
    assert "closeCanonicalModal" in b
    assert "modal.remove()" in b
    assert "requestRender" not in b


def test_o12s_hides_old_modals_and_old_status_badge():
    b = block()
    assert "removeOldGoalSheetModals" in b
    assert "data-aion-o12p-goal-doc-modal" in b
    assert "Boardroom Goal Sheet staged" in b
    assert "Pilot queue preview" in b


def test_o12s_exposes_manual_console_hooks():
    assert "window.aionOpenCanonicalGoalSheetDocumentModalO12S" in APP_JS
    assert "window.aionCloseCanonicalGoalSheetDocumentModalO12S" in APP_JS
    assert "window.aionRemoveOldGoalSheetDocumentModalsO12S" in APP_JS
