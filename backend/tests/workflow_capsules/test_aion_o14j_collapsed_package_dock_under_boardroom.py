from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14j_installed():
    assert "BEGIN AION O14J COLLAPSED PACKAGE DOCK UNDER BOARDROOM" in APP
    assert "installAionO14JCollapsedPackageDockUnderBoardroom" in APP


def test_o14j_finds_package_dock_and_boardroom_anchor():
    assert "function findPackageDockO14J()" in APP
    assert "function findBoardroomAnchorO14J()" in APP
    assert "[data-aion-o14a-department-pilot-package-dock]" in APP
    assert "[data-aion-department-121-boardroom-panel-o14d]" in APP
    assert "[data-aion-department-121-spatial-boardroom-mount]" in APP


def test_o14j_moves_dock_after_boardroom_anchor():
    assert 'anchor.insertAdjacentElement("afterend", shell)' in APP
    assert 'data-aion-o14j-package-collapse' in APP
    assert "buildCollapsedShellO14J" in APP


def test_o14j_collapses_package_as_button_not_top_panel():
    assert "<summary" in APP
    assert "Boardroom package" in APP
    assert "Show package" in APP
    assert "aion-o14j-package-dock-collapse[open]" in APP


def test_o14j_observer_is_scheduled_not_immediate_render_loop():
    assert "scheduledO14J" in APP
    assert "window.requestAnimationFrame" in APP
    assert "new MutationObserver(() => scheduleMoveO14J())" in APP
