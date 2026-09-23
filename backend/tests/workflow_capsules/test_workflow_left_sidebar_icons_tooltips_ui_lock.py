from pathlib import Path

APP = Path("desktop/mac/src/app.js")
CSS = Path("desktop/mac/src/styles.css")


def app_text() -> str:
    return APP.read_text(encoding="utf-8")


def css_text() -> str:
    return CSS.read_text(encoding="utf-8")


def test_sidebar_renderer_has_clean_nav_contract() -> None:
    text = app_text()
    assert 'class="aion-workflow-app-nav"' in text
    assert 'class="aion-workflow-nav-btn' in text
    assert 'data-tab="${escapeHtml(tab)}"' in text
    assert 'data-aion-sidebar-label="${escapeHtml(label)}"' in text
    assert 'class="aion-workflow-nav-icon"' in text
    assert 'data-icon="${escapeHtml(icon)}"' in text
    assert 'class="aion-workflow-nav-label"' in text


def test_sidebar_toggle_uses_expanded_shell_class() -> None:
    text = app_text()
    assert "function installAionWorkflowSidebarToggle()" in text
    assert 'shell.classList.toggle(' in text
    assert '"aion-workflow-sidebar-expanded"' in text
    assert "window.__aionWorkflowSidebarOpen === true" in text


def test_sidebar_css_lives_in_stylesheet() -> None:
    text = css_text()
    assert "AION Workflow Left Sidebar — source of truth" in text
    assert ".aion-workflow-canvas-shell.aion-workflow-sidebar-expanded .aion-workflow-layout" in text
    assert ".aion-workflow-sidebar-toggle::before" in text
    assert ".aion-workflow-nav-icon::before" in text
    assert "content: attr(data-icon)" in text
    assert ".aion-workflow-nav-label" in text


def test_old_app_js_bottom_patch_removed() -> None:
    text = app_text()
    assert "Left Sidebar Icons Tooltips" not in text
    assert "aion-left-rail-nav-btn" not in text
    assert "__aionWorkflowLeftSidebarIconsTooltipsV1Installed" not in text


def test_file_cabinet_pseudo_icon_is_disabled_in_stylesheet() -> None:
    text = css_text()
    assert '[data-tab="file_cabinet"]::before' in text
    assert '[data-tab="file_cabinet"]::after' in text
    assert "renderer now owns icon slot" in text
