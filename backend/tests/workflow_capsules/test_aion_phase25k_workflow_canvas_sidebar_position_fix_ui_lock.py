from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_workflow_canvas_sidebar_position_fix_exists():
    assert "aion-phase25k-workflow-canvas-sidebar-position-fix" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-main-sidebar" in TEXT
    assert "z-index: 99999 !important" in TEXT
    assert "top: 0 !important" in TEXT
    assert "left: 0 !important" in TEXT


def test_phase25k_workflow_canvas_shell_is_pushed_by_sidebar_width_only():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-canvas-shell" in TEXT
    assert "padding-left: 72px !important" in TEXT
    assert "width: 100vw !important" in TEXT


def test_phase25k_workflow_layout_dead_column_stays_removed():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-layout" in TEXT
    assert "display: block !important" in TEXT
    assert "grid-template-columns: minmax(0, 1fr) !important" in TEXT


def test_phase25k_sidebar_expand_pushes_canvas_to_expanded_width():
    assert "body.aion-phase19c-workflow-visible.aion-workflow-sidebar-expanded .aion-main-sidebar" in TEXT
    assert "width: 236px !important" in TEXT
    assert "body.aion-phase19c-workflow-visible.aion-workflow-sidebar-expanded .aion-workflow-canvas-shell" in TEXT
    assert "padding-left: 236px !important" in TEXT
