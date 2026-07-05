from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_workflow_shell_mounts_sitewide_sidebar_outside_layout():
    shell_index = TEXT.index('<section class="aion-workflow-canvas-shell">')
    layout_index = TEXT.index('<div class="aion-workflow-layout"', shell_index)
    shell_before_layout = TEXT[shell_index:layout_index]
    assert "${renderAppTabs()}" in shell_before_layout


def test_phase25k_workflow_layout_does_not_mount_sitewide_sidebar_inside_old_column():
    layout_index = TEXT.index('<div class="aion-workflow-layout"')
    canvas_index = TEXT.index('<main class="aion-workflow-canvas"', layout_index)
    layout_block = TEXT[layout_index:canvas_index]
    assert "${renderAppTabs()}" not in layout_block
    assert "${renderAionWorkflowGlyphLibraryDrawer()}" in layout_block


def test_phase25k_dead_old_sidebar_column_is_removed_by_css():
    assert "aion-phase25k-workflow-canvas-no-dead-sidebar-column" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-workflow-layout" in TEXT
    assert "grid-template-columns: minmax(0, 1fr) !important" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-workflow-canvas-shell" in TEXT


def test_phase25k_sitewide_sidebar_still_has_file_cabinet():
    assert 'class="aion-workflow-sidebar aion-main-sidebar"' in TEXT
    assert 'data-aion-main-sidebar="true"' in TEXT
    assert 'data-aion-sitewide-file-cabinet-tab="true"' in TEXT
    assert TEXT.count("${renderAionWorkflowFileCabinetDrawer()}") == 1
