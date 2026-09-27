from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14k_collapsed_package_dock_renderer_exists():
    assert "BEGIN AION O14K SOURCE-LEVEL COLLAPSED PACKAGE DOCK" in APP
    assert "function renderAionO14KCollapsedPackageDockUnderBoardroom" in APP
    assert 'data-aion-o14k-collapsed-package-dock="true"' in APP
    assert "Open package" in APP


def test_o14k_dock_is_inserted_directly_after_each_department_121_boardroom():
    for department in ["marketing", "sales", "finance", "operations", "support", "hr"]:
        boardroom = f'renderAionDepartment121BoardroomPanelO14D("{department}")'
        dock = f'renderAionO14KCollapsedPackageDockUnderBoardroom("{department}")'
        assert boardroom in APP
        assert dock in APP
        assert APP.index(boardroom) < APP.index(dock)


def test_o14k_hides_original_top_package_docks_but_not_nested_content():
    assert "installAionO14KHideOriginalTopPackageDocks" in APP
    assert 'data-aion-o14k-hidden-original-top-dock' in APP
    assert 'closest("[data-aion-o14k-package-content]")' in APP
    assert 'data-aion-o14k-package-content="true"' in APP


def test_o14k_exported_for_workspace_renderers():
    assert "window.renderAionO14KCollapsedPackageDockUnderBoardroom = renderAionO14KCollapsedPackageDockUnderBoardroom" in APP


def test_operations_flow_moves_from_global_sidebar_to_operations_workspace_dashboard_button():
    app_tabs = APP[APP.index("const APP_TABS = ["):APP.index("];", APP.index("const APP_TABS = ["))]
    sidebar_icons = APP[APP.index("function getAionMainSidebarIcon"):APP.index("function renderAppTabs")]
    command_centre = APP[APP.index("function renderOperationsCommandCentre"):
                         APP.index("function renderSupportCompactDirectorCard")]
    assert '{ key: "operations_flow", label: "Operations Flow" }' not in app_tabs
    assert 'operations_flow: "⌁"' not in sidebar_icons
    assert 'data-aion-operations-dashboard="true"' in command_centre
    assert 'data-tab="operations_flow"' in command_centre
    assert '>Dashboard</button>' in command_centre
    assert command_centre.index('>Dashboard</button>') < command_centre.index('>Open package</button>')
    assert 'window.setAionSidebarActiveTabHardV1("operations_flow")' in APP
