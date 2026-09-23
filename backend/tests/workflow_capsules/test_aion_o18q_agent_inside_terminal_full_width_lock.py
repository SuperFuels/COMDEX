from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18q_layout_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18Q AGENT INSIDE TERMINAL FULL WIDTH LOCK" in text
    assert "aion-o18q-agent-inside-terminal-full-width-style" in text
    assert "__debugAionO18QAgentInsideTerminal" in text
    assert "Terminal becomes full-width function cockpit surface" in text

def test_o18q_terminal_full_width_and_agent_overlay():
    text = APP.read_text(encoding="utf-8")
    assert 'data-aion-o17e-marketing-pilot-terminal="true"' in text
    assert "width:100% !important" in text
    assert "padding-right:360px !important" in text
    assert "top:192px !important" in text
    assert "right:34px !important" in text
    assert "width:318px !important" in text
    assert "height:360px !important" in text
