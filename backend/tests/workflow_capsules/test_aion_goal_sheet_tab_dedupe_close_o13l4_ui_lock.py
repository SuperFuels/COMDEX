from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    start = APP_JS.index("BEGIN AION O13L4 GOAL SHEET TAB DEDUPE AND CLOSE LOCK")
    end = APP_JS.index("END AION O13L4 GOAL SHEET TAB DEDUPE AND CLOSE LOCK")
    return APP_JS[start:end]


def test_o13l4_installed():
    text = block()
    assert "O13L.4 exact fix" in text
    assert "dedupeGoalSheetTabsO13L4" in text
    assert "closeTabO13L4" in text


def test_o13l4_dedupes_goal_sheet_tabs_by_id():
    text = block()
    assert "seenGoalSheetIds" in text
    assert "seenGoalSheetIds.has(id)" in text
    assert "seenGoalSheetIds.add(id)" in text


def test_o13l4_intercepts_goal_sheet_close_button():
    text = block()
    assert "data-aion-workflow-main-tab-close" in text
    assert "handleCloseO13L4" in text
    assert "event.stopImmediatePropagation" in text


def test_o13l4_wraps_existing_tab_renderer():
    text = block()
    assert "previousRender" in text
    assert "window.__aionRenderWorkflowCanvasTabs = wrapped" in text
    assert "wrapped.__aionO13L4Wrapped = true" in text


def test_o13l4_exposes_debug_helpers():
    text = block()
    assert "window.aionDedupeGoalSheetTabsO13L4" in text
    assert "window.aionCloseGoalSheetTabO13L4" in text
