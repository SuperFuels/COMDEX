from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def block():
    text = APP.read_text(encoding="utf-8")
    start = text.index("/* BEGIN AION O14A7 HIDE GLOBAL GOAL SHEET ACTION ON DEPARTMENT PILOT */")
    end = text.index("/* END AION O14A7 HIDE GLOBAL GOAL SHEET ACTION ON DEPARTMENT PILOT */", start)
    return text[start:end]

def test_o14a7_hides_old_o12b_floating_action_on_live_agents():
    b = block()
    assert "aion-o12b-boardroom-action" in b
    assert "aion-o14a7-live-agents" in b
    assert "data-aion-o14a7-hidden-on-department-pilot" in b
    assert 'oldAction.setAttribute("data-visible", "false")' in b

def test_o14a7_keeps_department_pilot_existing_canvas_contract():
    b = block()
    assert "Existing Pilot only" in b
    assert "Existing canvas only" in b
    assert "Preview-only" in b

def test_o14a7_sidebar_safe_dock_padding_locked():
    b = block()
    assert "margin-left: 72px" in b
    assert "width: calc(100% - 96px)" in b
    assert "max-width: calc(100vw - 112px)" in b
    assert "data-aion-o14a7-sidebar-safe" in b

def test_o14a7_no_repeating_timer_loop():
    b = block()
    assert "setInterval" not in b
    assert "cloneNode" not in b
    assert "document.body.cloneNode" not in b
