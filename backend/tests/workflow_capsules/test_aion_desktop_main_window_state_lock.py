import json
from pathlib import Path


MAIN = Path("desktop/mac/electron/main.js").read_text(encoding="utf-8")
PACKAGE = json.loads(Path("desktop/mac/package.json").read_text(encoding="utf-8"))


def test_main_window_remembers_maximized_state_and_normal_bounds():
    assert '"main-window-state.json"' in MAIN
    assert 'return { maximized: true, normalBounds: null }' in MAIN
    assert 'mainWindow.on("maximize"' in MAIN
    assert 'mainWindow.on("unmaximize"' in MAIN
    assert 'mainWindow.on("resize", rememberNormalBounds)' in MAIN
    assert 'mainWindow.on("move", rememberNormalBounds)' in MAIN
    assert 'mainWindow.on("blur"' in MAIN


def test_existing_main_window_restores_preferred_mode_on_focus():
    assert 'mainWindow.on("focus"' in MAIN
    assert 'setTimeout(restorePreferredMainWindowMode, 0)' in MAIN
    assert 'mainWindow.maximize()' in MAIN
    assert 'if (mainWindow.isMinimized()) mainWindow.restore()' in MAIN
    assert 'mainWindow.show()' in MAIN
    assert 'mainWindow.focus()' in MAIN


def test_packaged_app_is_explicitly_a_regular_dock_application():
    assert PACKAGE["build"]["appId"] == "com.tessaris.desktop"
    extend_info = PACKAGE["build"]["mac"]["extendInfo"]
    assert extend_info["LSUIElement"] is False
    assert extend_info["LSBackgroundOnly"] is False
