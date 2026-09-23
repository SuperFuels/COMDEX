from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18b_function_agent_hud_replacement_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18B REPLACE MINI BOARDROOM WITH FUNCTION AGENT HUD" in text
    assert "aion-o18b-function-agent-hud-replacement" in text
    assert "MARKETING AGENT\\\\A" in text
    assert "SYSTEM ONLINE" in text
    assert "CAMPAIGN READINESS" in text
    assert "data-aion-o18b-agent-figure" in text

def test_o18b_visually_suppresses_mini_boardroom_canvas():
    text = APP.read_text(encoding="utf-8")
    assert "opacity:0.06" in text
    assert "filter:blur(1px) grayscale(1)" in text
    assert "injectAgentFigure" in text
    assert "__debugAionO18BFunctionAgentHud" in text
