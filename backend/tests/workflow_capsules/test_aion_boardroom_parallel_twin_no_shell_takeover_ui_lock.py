from pathlib import Path

APP = Path("desktop/mac/src/app.js")


def test_parallel_twin_visible_render_path_does_not_auto_mount_on_load():
    text = APP.read_text()

    assert "window.__aionBoardroomParallelTwinAutoMountDisabledV0 = true" in text
    assert "Boardroom Parallel Twin Visible Render Path v0 installed; auto-mount disabled" in text

    forbidden = [
        "document.addEventListener(\"DOMContentLoaded\", function onBoardroomParallelTwinVisibleReady()",
        "setTimeout(function mountBoardroomParallelTwinVisibleSoon()",
    ]

    for item in forbidden:
        assert item not in text


def test_parallel_twin_mount_function_still_exists_for_explicit_boardroom_rendering():
    text = APP.read_text()

    assert "window.mountBoardroomParallelTwinVisibleRenderPathV0 = mountBoardroomParallelTwinVisibleRenderPathV0" in text
    assert "window.renderBoardroomParallelTwinVisibleRenderPathV0 = renderBoardroomParallelTwinVisibleRenderPathV0" in text


def test_main_shell_navigation_remains_owned_by_render_function():
    text = APP.read_text()

    assert "function render()" in text
    assert "${renderTopNav()}" in text
    assert "${renderDesktopWorkspace()}" in text
    assert "app.innerHTML" in text


def test_boardroom_surface_still_renders_app_tabs():
    text = APP.read_text()

    boardroom_start = text.find("function renderBoardroomSurface()")
    assert boardroom_start != -1

    boardroom_chunk = text[boardroom_start: boardroom_start + 1400]
    assert "${renderAppTabs()}" in boardroom_chunk
