from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18r_reduce_terminal_agent_frame_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18R REDUCE TERMINAL AGENT FRAME LOCK" in text
    assert "aion-o18r-reduce-terminal-agent-frame-style" in text
    assert "__debugAionO18RReduceTerminalAgentFrame" in text
    assert "width:207px !important" in text
    assert "height:234px !important" in text
    assert "padding-right:240px !important" in text
