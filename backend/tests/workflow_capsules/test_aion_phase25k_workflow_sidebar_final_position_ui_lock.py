from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_workflow_sidebar_final_position_patch_exists():
    assert "aion-phase25k-workflow-canvas-sidebar-final-position" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-main-sidebar" in TEXT
    assert "padding: 14px 6px 14px !important" in TEXT
    assert "gap: 8px !important" in TEXT


def test_phase25k_workflow_surface_offsets_from_fixed_sidebar():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-canvas-shell" in TEXT
    assert "margin-left: 72px !important" in TEXT
    assert "width: calc(100vw - 72px) !important" in TEXT
    assert "max-width: calc(100vw - 72px) !important" in TEXT


def test_phase25k_workflow_layout_has_no_dead_sidebar_column():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-layout" in TEXT
    assert "grid-template-columns: minmax(0, 1fr) !important" in TEXT


def test_phase25k_sidebar_expanded_offset_is_locked():
    assert "body.aion-phase19c-workflow-visible.aion-workflow-sidebar-expanded .aion-main-sidebar" in TEXT
    assert "width: 236px !important" in TEXT
    assert "margin-left: 236px !important" in TEXT
    assert "width: calc(100vw - 236px) !important" in TEXT
