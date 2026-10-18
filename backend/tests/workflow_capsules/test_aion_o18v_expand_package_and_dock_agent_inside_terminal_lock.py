from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18v_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18V EXPAND PACKAGE AND DOCK AGENT INSIDE TERMINAL LOCK" in text
    assert "aion-o18v-expand-package-dock-agent-style" in text
    assert "__debugAionO18VPackageAndAgentDock" in text

def test_o18v_package_expansion_content():
    text = APP.read_text(encoding="utf-8")
    assert "data-aion-o18v-marketing-package-expanded" in text
    assert "Required Discovery" in text
    assert "Expected Outputs" in text
    assert "workflow_goal_loop_marketing_goal_sheet" in text
    assert "Preview only: no task execution" in text

def test_o18v_agent_docked_inside_terminal():
    text = APP.read_text(encoding="utf-8")
    assert "dockAgentInsideTerminalO18V" in text
    assert "data-aion-o18v-agent-docked-inside-terminal" in text
    assert "agent_inside_terminal" in text
    assert "terminalBody.appendChild(shell)" in text
