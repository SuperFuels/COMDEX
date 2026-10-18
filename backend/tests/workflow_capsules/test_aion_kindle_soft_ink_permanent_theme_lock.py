from pathlib import Path

APP = Path("desktop/mac/src/app.js")
SUITE = Path("scripts/run_goal_engine_focused_lock_suite.sh")

def source() -> str:
    return APP.read_text()

def test_kindle_soft_ink_theme_is_permanent_not_temp() -> None:
    text = source()
    assert "AION KINDLE SOFT INK THEME LOCK: permanent e-paper interface palette" in text
    assert "installAionKindleSoftInkTheme" in text
    assert "aion-kindle-soft-ink-theme" in text
    assert "TEMP STYLE TEST: Kindle soft ink" not in text
    assert "installAionKindleSoftInkStyleTest" not in text

def test_kindle_soft_ink_theme_tokens_exist() -> None:
    text = source()
    assert "--aion-ink-bg" in text
    assert "--aion-ink-paper" in text
    assert "--aion-ink-panel" in text
    assert "--aion-ink-border" in text
    assert "--aion-ink-text" in text
    assert "--aion-ink-muted" in text
    assert "--aion-ink-accent" in text

def test_kindle_soft_ink_theme_controls_core_surfaces() -> None:
    text = source()
    assert "background: var(--aion-ink-bg) !important" in text
    assert "color: var(--aion-ink-text) !important" in text
    assert "box-shadow: none !important" in text
    assert "background: var(--aion-ink-accent) !important" in text

def test_kindle_soft_ink_theme_is_in_focused_suite() -> None:
    assert "test_aion_kindle_soft_ink_permanent_theme_lock.py" in SUITE.read_text()
