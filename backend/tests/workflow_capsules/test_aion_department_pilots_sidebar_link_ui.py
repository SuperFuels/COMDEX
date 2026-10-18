from pathlib import Path


APP_JS = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"
STYLES_CSS = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "styles.css"


def test_left_sidebar_has_clear_department_pilots_route():
    source = APP_JS.read_text(encoding="utf-8")
    assert '{ key: "live_agents", label: "Department Pilots" }' in source
    assert 'live_agents: "P"' in source
    assert 'data-tab="${escapeHtml(tab.key)}"' in source
    assert 'return renderLiveAgentsSurface();' in source


def test_department_pilots_hover_flyout_only_lists_connected_workspaces():
    source = APP_JS.read_text(encoding="utf-8")
    flyout = source[source.index("function getAionDepartmentPilotFlyoutItemsV1"):source.index("function getAionActiveDepartmentPilotV1")]
    for route in (
        'key: "marketing"',
        'key: "sales"',
        'key: "finance"',
        'key: "operations"',
        'key: "support"',
        'key: "hr"',
        'key: "products_services"',
        'key: "legal"',
        'key: "cybersecurity"',
        'key: "procurement"',
        'key: "projects"',
    ):
        assert route in flyout
    for unavailable in ('key: "it"', 'key: "design"', 'key: "engineering"'):
        assert unavailable not in flyout
    assert "getAionDesktopCustomDepartmentsV1()" in flyout


def test_department_pilots_flyout_is_hover_keyboard_and_route_enabled():
    source = APP_JS.read_text(encoding="utf-8")
    styles = STYLES_CSS.read_text(encoding="utf-8")
    assert 'data-aion-department-pilot-trigger="true"' in source
    assert 'data-aion-department-pilot-flyout="true"' in source
    assert 'aria-haspopup="menu"' in source
    assert 'event.key !== "Escape"' in source
    assert 'openAionExecutiveDepartmentFromStickyHeaderV1(departmentKey)' in source
    assert ".aion-department-pilot-flyout.is-open" in styles
    assert "backdrop-filter: blur(22px)" in styles
    assert ".aion-department-pilot-flyout-item.is-active" in styles
