from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
MAIN = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")


def test_new_isolated_browser_navigates_after_load_file_resolves():
    start = MAIN.index("async function openIsolatedBrowserWindow")
    end = MAIN.index("async function ensureBackendRunning", start)
    function = MAIN[start:end]

    load_file = function.rindex("await isolatedBrowserWindow.loadFile")
    navigate = function.index("const navigation = await loadUrlInIsolatedBrowser(startUrl)", load_file)
    new_window_navigation = function[load_file:]

    assert navigate > load_file
    assert 'webContents.once("did-finish-load"' not in new_window_navigation
    assert "if (!navigation?.ok)" in new_window_navigation
    assert "navigation," in new_window_navigation
