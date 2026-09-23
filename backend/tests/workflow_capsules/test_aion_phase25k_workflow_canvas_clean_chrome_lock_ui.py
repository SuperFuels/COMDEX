from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_phase25k_clean_chrome_lock_exists():
    assert "aion-phase25k-workflow-canvas-clean-chrome-lock-v3" in TEXT
    assert "left: 56px !important" in TEXT
    assert "top: 0 !important" in TEXT


def test_phase25k_tabs_have_own_row_below_header():
    assert "top: 118px !important" in TEXT
    assert "height: 36px !important" in TEXT
    assert "top: 154px !important" in TEXT
    assert "height: calc(100vh - 154px) !important" in TEXT


def test_phase25k_failed_final_patches_removed():
    assert "aion-phase25k-workflow-canvas-final-align-v2" not in TEXT
    assert "aion-phase25k-final-sidebar-visual-reset" not in TEXT
