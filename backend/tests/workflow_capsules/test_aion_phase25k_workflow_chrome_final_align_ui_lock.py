from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_workflow_chrome_final_align_lock_exists():
    assert "aion-phase25k-workflow-chrome-final-align-lock" in TEXT
    assert "installAionPhase25KWorkflowChromeFinalAlignLock" in TEXT


def test_phase25k_workflow_shell_starts_after_root_sidebar_without_top_gap():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-canvas-shell" in TEXT
    assert "margin: 0 0 0 64px !important" in TEXT
    assert "width: calc(100vw - 64px) !important" in TEXT
    assert "height: 100vh !important" in TEXT


def test_phase25k_workflow_topbar_no_longer_hides_behind_sidebar():
    assert "body.aion-phase19c-workflow-visible .aion-workflow-topbar" in TEXT
    assert "width: 100% !important" in TEXT
    assert "left: 0 !important" in TEXT
    assert "top: 0 !important" in TEXT


def test_phase25k_workflow_layout_has_no_dead_sidebar_column():
    assert "grid-template-columns: minmax(0, 1fr) !important" in TEXT
    assert "body.aion-phase19c-workflow-visible .aion-workflow-layout" in TEXT
