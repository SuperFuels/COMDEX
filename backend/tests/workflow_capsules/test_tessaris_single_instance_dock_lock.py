from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MAIN = ROOT / "desktop" / "mac" / "electron" / "main.js"


def test_tessaris_uses_one_desktop_process_and_dock_item():
    text = MAIN.read_text()

    assert '"desktop-instance.pid"' in text
    assert 'fs.openSync(TESSARIS_DESKTOP_INSTANCE_PATH, "wx", 0o600)' in text
    assert "isTessarisProcessAlive(ownerPid)" in text
    assert "process.exit(0);" in text
    assert "app.requestSingleInstanceLock()" in text
    assert 'app.on("second-instance"' in text
    assert "if (!tessarisHasSingleInstanceLock)" in text
    assert "releaseTessarisDesktopProcessLock();" in text


def test_second_launch_focuses_the_existing_window():
    text = MAIN.read_text()
    start = text.index('app.on("second-instance"')
    end = text.index("const DEV_PROJECT_ROOT", start)
    block = text[start:end]

    assert "mainWindow.isMinimized()" in block
    assert "mainWindow.restore()" in block
    assert "mainWindow.show()" in block
    assert "mainWindow.focus()" in block
