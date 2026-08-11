from pathlib import Path


APP_JS = Path(__file__).resolve().parents[3] / "desktop" / "mac" / "src" / "app.js"


def test_left_sidebar_has_clear_department_pilots_route():
    source = APP_JS.read_text(encoding="utf-8")
    assert '{ key: "live_agents", label: "Department Pilots" }' in source
    assert 'live_agents: "P"' in source
    assert 'data-tab="${escapeHtml(tab.key)}"' in source
    assert 'return renderLiveAgentsSurface();' in source
