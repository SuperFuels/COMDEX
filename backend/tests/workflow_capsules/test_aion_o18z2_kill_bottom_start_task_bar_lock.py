from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18z2_kill_bottom_start_task_bar_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18Z2 KILL BOTTOM START TASK BAR LOCK" in text
    assert "aion-o18z2-kill-bottom-start-task-bar-style" in text
    assert "__debugAionO18Z2KillBottomStartTaskBar" in text
    assert "findStartTaskButtonO18Z2" in text
    assert "START TASK" in text

def test_o18z2_targets_button_and_footer_ancestor():
    text = APP.read_text(encoding="utf-8")
    assert "data-aion-o18z2-start-task-button" in text
    assert "data-aion-o18z2-bottom-start-task-bar" in text
    assert "findBottomBarFromStartButtonO18Z2" in text
    assert "window.innerHeight * 0.55" in text
