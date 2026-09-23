from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_canvas_does_not_mount_sitewide_sidebar_inside_workflow_layout():
    assert 'data-phase25k_canvas_must_not_mount_renderAppTabs_inside_workflow_layout="true"' in TEXT
    assert '<div class="aion-workflow-layout">\\n        ${renderAppTabs()}' not in TEXT
    assert '<div class="aion-workflow-layout"' in TEXT
    assert "${renderAionWorkflowGlyphLibraryDrawer()}" in TEXT
    workflow_layout_index = TEXT.index('<div class="aion-workflow-layout"')
    canvas_index = TEXT.index('<main class="aion-workflow-canvas"', workflow_layout_index)
    workflow_layout_block = TEXT[workflow_layout_index:canvas_index]
    assert "${renderAppTabs()}" not in workflow_layout_block
    assert "${renderAionWorkflowGlyphLibraryDrawer()}" in workflow_layout_block


def test_phase25k_sitewide_sidebar_renderer_still_exists():
    assert "function renderAppTabs" in TEXT
    assert 'class="aion-workflow-sidebar aion-main-sidebar"' in TEXT
    assert 'data-aion-main-sidebar="true"' in TEXT
    assert 'data-aion-sitewide-file-cabinet-tab="true"' in TEXT


def test_phase25k_old_canvas_sidebar_is_not_hardcoded():
    assert '<aside class="aion-workflow-sidebar" data-aion-workflow-sidebar="true">' not in TEXT


def test_phase25k_file_cabinet_drawer_still_single_mount():
    assert TEXT.count("${renderAionWorkflowFileCabinetDrawer()}") == 1
