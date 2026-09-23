from pathlib import Path
import json

pkg = json.loads(Path("desktop/mac/package.json").read_text(encoding="utf-8"))
MAIN_PATH = Path("desktop/mac") / pkg.get("main", "main.js")
MAIN_JS = MAIN_PATH.read_text(encoding="utf-8")


def test_d1_devtools_shortcut_installed():
    assert "BEGIN AION D1 DEVTOOLS SHORTCUT REPAIR" in MAIN_JS
    assert "D1 DevTools shortcut repair installed" in MAIN_JS


def test_d1_has_cmd_option_i_and_f12():
    assert "CommandOrControl+Alt+I" in MAIN_JS
    assert "F12" in MAIN_JS


def test_d1_opens_devtools_detached():
    assert 'openDevTools({ mode: "detach" })' in MAIN_JS


def test_d1_registers_global_shortcut_and_menu():
    assert "globalShortcut.register" in MAIN_JS
    assert "Menu.setApplicationMenu" in MAIN_JS
    assert "Toggle DevTools" in MAIN_JS
