from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18z_hide_bottom_pilot_task_bar_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18Z HIDE BOTTOM PILOT TASK BAR LOCK" in text
    assert "aion-o18z-hide-bottom-pilot-task-bar-style" in text
    assert "__debugAionO18ZHideBottomPilotTaskBar" in text
    assert "Pilot what to do..." in text
    assert "START TASK" in text

def test_o18z_hides_found_bar_not_terminal_inputs():
    text = APP.read_text(encoding="utf-8")
    assert "data-aion-o18z-bottom-pilot-task-bar" in text
    assert "findBottomPilotTaskBarO18Z" in text
    assert "hideBottomPilotTaskBarO18Z" in text
    assert "window.innerHeight * 0.65" in text
