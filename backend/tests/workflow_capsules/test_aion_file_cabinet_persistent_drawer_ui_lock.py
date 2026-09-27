from pathlib import Path


TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_file_cabinet_uses_one_persisted_open_state():
    assert "function setAionWorkflowFileCabinetOpen" in TEXT
    assert '"aion.workflow_file_cabinet.open.v1"' in TEXT
    assert "setAionWorkflowFileCabinetOpen(true" in TEXT
    assert "setAionWorkflowFileCabinetOpen(false" in TEXT


def test_file_cabinet_sidebar_never_toggles_closed_on_click():
    assert "setCabinetOpen(window.__aionWorkflowFileCabinetOpen !== true)" not in TEXT
    assert "window.__aionWorkflowFileCabinetOpen = window.__aionWorkflowFileCabinetOpen !== true" not in TEXT


def test_opening_file_cabinet_does_not_auto_save_a_workflow_copy():
    file_tab_handler = TEXT[TEXT.index("function handleCabinetAction(event)") :]
    file_tab_handler = file_tab_handler[: file_tab_handler.index("if (!root) return;")]
    assert "syncCurrentWorkflowIntoTree()" not in file_tab_handler
    assert "setAionWorkflowFileCabinetOpen(true)" in file_tab_handler


def test_file_cabinet_has_one_runtime_drawer_mount():
    assert TEXT.count("data-aion-sitewide-file-cabinet-mount=\"true\"") == 1


def test_file_cabinet_icon_suppresses_the_second_glyph_layer():
    assert "html body .aion-sitewide-file-cabinet-tab .aion-workflow-nav-icon" in TEXT
    assert "display: none !important" in TEXT
    assert "content: none !important" in TEXT


def test_file_cabinet_drawer_clears_the_sticky_business_header():
    assert "html body .aion-workflow-file-cabinet" in TEXT
    assert "position: fixed !important" in TEXT
    assert "top: 80px !important" in TEXT
    assert "max-height: calc(100vh - 94px) !important" in TEXT


def test_reopened_file_cabinet_starts_with_header_visible():
    assert "const wasOpen = window.__aionWorkflowFileCabinetOpen === true" in TEXT
    assert "if (nextOpen && !wasOpen)" in TEXT
    assert "if (drawer) drawer.scrollTop = 0" in TEXT


def test_file_cabinet_background_dismiss_is_disabled():
    assert "window.__aionFileCabinetBackgroundDismissDisabledV15 = true" in TEXT
    assert 'window.addEventListener("pointerdown", handleOutsideClick, true)' not in TEXT
