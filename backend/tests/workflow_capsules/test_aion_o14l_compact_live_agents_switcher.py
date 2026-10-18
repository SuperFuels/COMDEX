from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14l_compact_switcher_installed():
    assert "BEGIN AION O14L COMPACT LIVE AGENTS EXECUTIVE SWITCHER" in APP
    assert "installAionO14LCompactLiveAgentsExecutiveSwitcher" in APP
    assert "data-aion-o14l-executive-switcher" in APP
    assert "[AION] O14L compact Live Agents executive boardroom switcher installed" in APP


def test_o14l_has_executive_department_route_buttons():
    for dept in ["marketing", "sales", "finance", "operations", "support", "pilot"]:
        assert f'data-aion-o14l-executive-department="${dept}"' in APP or "data-aion-o14l-executive-department" in APP
    assert "Live Agents" in APP
    assert "Boardroom" in APP


def test_o14l_hides_file_cabinet_only_on_live_agents():
    assert "aion-o14l-live-agents-compact" in APP
    assert "data-aion-o14l-hidden-top-file-cabinet" in APP
    assert "Aion File Cabinet" in APP
    assert "Workflow Library" in APP
    assert "Current workflow" in APP


def test_o14l_hides_legacy_department_tabs_but_keeps_workspace():
    assert "data-aion-o14l-hidden-legacy-department-tabs" in APP
    assert "data-aion-o14l-workspace-tightened" in APP
    assert 'el.matches?.("#app, .desktop-root, .desktop-workspace-layout-no-rail, main, .surface-shell, [data-aion-o14p-live-agents-shell]")' in APP
    assert "const leafMatches = matches.filter" in APP
    assert "el.removeAttribute(\"data-aion-o14l-hidden-legacy-department-tabs\")" in APP
    assert "SPATIAL MARKETING BOARDROOM" in APP
    assert "SPATIAL SALES BOARDROOM" in APP


def test_o14l_switcher_does_not_touch_boardroom_route():
    assert 'activeTabO14L() === "live_agents"' in APP
    assert "document.body.classList.toggle" in APP
    assert "document.querySelector(\"[data-aion-o14l-executive-switcher='true']\")?.remove()" in APP
