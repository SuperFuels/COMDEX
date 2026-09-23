from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_final_left_offset_patch_exists():
    assert "aion-phase25k-workflow-canvas-left-offset-final" in TEXT
    assert "Final canvas rule:" in TEXT


def test_phase25k_sidebar_padding_is_tighter_on_canvas():
    assert "body.aion-phase19c-workflow-visible .aion-main-sidebar" in TEXT
    assert "width: 72px !important" in TEXT
    assert "padding: 26px 6px 18px !important" in TEXT
    assert "gap: 14px !important" in TEXT


def test_phase25k_workflow_topbar_starts_after_sidebar():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-canvas-shell" in TEXT
    assert "padding-left: 72px !important" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-workflow-topbar" in TEXT
    assert "padding-left: 32px !important" in TEXT


def test_phase25k_workflow_layout_has_no_sidebar_column():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-layout" in TEXT
    assert "display: block !important" in TEXT
    assert "grid-template-columns: minmax(0, 1fr) !important" in TEXT


def test_phase25k_expanded_sidebar_updates_canvas_offset():
    assert "body.aion-phase19c-workflow-visible.aion-workflow-sidebar-expanded .aion-main-sidebar" in TEXT
    assert "width: 236px !important" in TEXT
    assert "body.aion-phase19c-workflow-visible.aion-workflow-sidebar-expanded .aion-workflow-canvas-shell" in TEXT
    assert "padding-left: 236px !important" in TEXT
