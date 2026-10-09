from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INDEX = ROOT / "desktop" / "mac" / "src" / "index.html"
STYLES = ROOT / "desktop" / "mac" / "src" / "styles.css"
APP = ROOT / "desktop" / "mac" / "src" / "app.js"


def test_startup_uses_branded_animated_tessaris_mark():
    index = INDEX.read_text()
    styles = STYLES.read_text()

    assert 'id="tessaris-startup-splash"' in index
    assert 'src="../assets/icon.png"' in index
    assert "tessaris-startup-orbit" in index
    assert "@keyframes tessaris-startup-spiral" in styles
    assert "conic-gradient" in styles


def test_startup_splash_stays_for_at_least_one_second_then_releases():
    index = INDEX.read_text()

    assert "window.__tessarisStartupInProgress = true" in index
    assert "Math.max(0, 1000 - elapsed)" in index
    assert 'window.addEventListener("load", window.__tessarisDismissStartupSplash' in index
    assert 'splash.classList.add("is-leaving")' in index


def test_goal_sheet_queue_builders_do_not_open_preview_on_startup():
    app = APP.read_text()
    start = app.index("/* BEGIN AION O13D LIVE AGENTS PILOT PREVIEW STATE BRIDGE */")
    end = app.index("/* END AION O13D LIVE AGENTS PILOT PREVIEW STATE BRIDGE */")
    block = app[start:end]

    build_all_start = block.index("const wrappedBuildAll")
    build_active_start = block.index("const wrappedBuildActive")
    exports_start = block.index("window.aionEnsurePilotQueueO13D")

    build_all = block[build_all_start:build_active_start]
    build_active = block[build_active_start:exports_start]

    assert "buildPilotPreviewStateO13D(queue);" in build_all
    assert "renderPilotPreviewPanelO13D" not in build_all
    assert "buildPilotPreviewStateO13D(queue || undefined);" in build_active
    assert "renderPilotPreviewPanelO13D" not in build_active
    assert "window.__tessarisStartupInProgress === true" in block
