from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_workflow_sidebar_is_before_canvas_shell_not_inside_it():
    marker = '${renderAppTabs()}'
    shell = '<section class="aion-workflow-canvas-shell">'
    sidebar_index = TEXT.index(marker)
    shell_index = TEXT.index(shell)
    assert sidebar_index < shell_index

    shell_end = TEXT.index('<div class="aion-workflow-layout"', shell_index)
    shell_opening = TEXT[shell_index:shell_end]
    assert marker not in shell_opening


def test_phase25k_workflow_layout_has_no_sidebar_mount_or_dead_column():
    layout_index = TEXT.index('<div class="aion-workflow-layout"')
    canvas_index = TEXT.index('<main class="aion-workflow-canvas"', layout_index)
    layout_block = TEXT[layout_index:canvas_index]
    assert '${renderAppTabs()}' not in layout_block
    assert '<aside class="aion-workflow-sidebar" data-aion-workflow-sidebar="true">' not in TEXT


def test_phase25k_external_sidebar_css_lock_exists():
    assert "aion-phase25k-workflow-canvas-external-sidebar-lock" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-main-sidebar" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-workflow-canvas-shell" in TEXT
    assert "margin-left: 72px !important" in TEXT
    assert "grid-template-columns: minmax(0, 1fr) !important" in TEXT


def test_phase25k_file_cabinet_still_single_sitewide_mount():
    assert 'data-aion-sitewide-file-cabinet-tab="true"' in TEXT
    assert TEXT.count("${renderAionWorkflowFileCabinetDrawer()}") == 1
