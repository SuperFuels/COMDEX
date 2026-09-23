from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_sitewide_sidebar_is_outside_workflow_canvas_shell():
    shell_index = TEXT.index('<section class="aion-workflow-canvas-shell">')
    sidebar_index = TEXT.rfind("${renderAppTabs()}", 0, shell_index)

    assert sidebar_index != -1
    assert sidebar_index < shell_index


def test_phase25k_workflow_canvas_shell_no_longer_contains_sitewide_sidebar_mount():
    shell_index = TEXT.index('<section class="aion-workflow-canvas-shell">')
    layout_index = TEXT.index('<div class="aion-workflow-layout"', shell_index)
    shell_header_block = TEXT[shell_index:layout_index]

    assert "${renderAppTabs()}" not in shell_header_block


def test_phase25k_workflow_layout_no_longer_mounts_sitewide_sidebar():
    layout_index = TEXT.index('<div class="aion-workflow-layout"')
    canvas_index = TEXT.index('<main class="aion-workflow-canvas"', layout_index)
    layout_block = TEXT[layout_index:canvas_index]

    assert "${renderAppTabs()}" not in layout_block
    assert "${renderAionWorkflowGlyphLibraryDrawer()}" in layout_block


def test_phase25k_failed_sidebar_offset_hacks_removed():
    assert "aion-phase25k-workflow-canvas-left-offset-final" not in TEXT
    assert "aion-phase25k-workflow-canvas-no-dead-sidebar-column" not in TEXT
    assert "aion-phase25k-true-global-sidebar-style" not in TEXT
    assert "aion-phase25k-single-sidebar-force" not in TEXT


def test_phase25k_sidebar_and_file_cabinet_still_exist_once():
    assert 'class="aion-workflow-sidebar aion-main-sidebar"' in TEXT
    assert 'data-aion-main-sidebar="true"' in TEXT
    assert 'data-aion-sitewide-file-cabinet-tab="true"' in TEXT
    assert TEXT.count("${renderAionWorkflowFileCabinetDrawer()}") == 1
