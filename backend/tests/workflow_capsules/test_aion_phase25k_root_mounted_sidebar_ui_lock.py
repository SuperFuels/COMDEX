from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_sidebar_is_root_mounted_after_render():
    assert "aion-phase25k-root-mounted-sidebar-lock" in TEXT
    assert "function rootMountSidebar()" in TEXT
    assert 'document.body.appendChild(newest)' in TEXT
    assert 'data-aion-root-mounted-sidebar' in TEXT


def test_phase25k_root_sidebar_css_targets_body_child_only():
    assert "html body > .aion-main-sidebar" in TEXT
    assert "position: fixed !important" in TEXT
    assert "left: 0 !important" in TEXT
    assert "top: 0 !important" in TEXT
    assert "width: 64px !important" in TEXT


def test_phase25k_workflow_canvas_offsets_from_root_sidebar():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-canvas-shell" in TEXT
    assert "margin-left: 64px !important" in TEXT
    assert "width: calc(100vw - 64px) !important" in TEXT


def test_phase25k_old_final_visual_reset_removed():
    assert "aion-phase25k-final-sidebar-visual-reset" not in TEXT
