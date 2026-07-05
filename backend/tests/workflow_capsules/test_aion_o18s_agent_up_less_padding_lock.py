from pathlib import Path

APP = Path("desktop/mac/src/app.js")
RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js")

def test_o18s_app_compact_position_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18S TERMINAL AGENT COMPACT POSITION LOCK" in text
    assert "aion-o18s-terminal-agent-compact-position-style" in text
    assert "padding-right:220px !important" in text
    assert "top:188px !important" in text
    assert "width:200px !important" in text
    assert "height:226px !important" in text

def test_o18s_renderer_agent_lift_installed():
    text = RENDERER.read_text(encoding="utf-8")
    assert "BEGIN AION O18S AGENT PORTRAIT LIFT LOCK" in text
    assert "agentRoot.position.set(0, 0.44, 0)" in text
    assert "camera.lookAt(0, 1.50, 0)" in text
