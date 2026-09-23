from pathlib import Path
import re

APP = Path("desktop/mac/src/app.js")

def test_o18ad_helper_installed_before_workspace_body():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18AD DIRECT DEPARTMENT BRANCH REWRITE LOCK" in text
    assert text.index("BEGIN AION O18AD DIRECT DEPARTMENT BRANCH REWRITE LOCK") < text.index("function renderLiveAgentsWorkspaceBody")
    assert "renderAionO18ADDepartmentConversationCockpit" in text
    assert "__debugAionO18ADDirectDepartmentBranchRewrite" in text

def test_o18ad_conversation_cockpit_is_retained_as_on_demand_department_pilot():
    text = APP.read_text(encoding="utf-8")
    assert "openUnifiedDepartmentPilotConversation" in text
    assert "window.renderAionO18ADDepartmentConversationCockpit" in text
    assert 'data-aion-unified-department-conversation=' in text
    for dept in ["sales", "finance", "operations", "support"]:
        assert f'if (departmentKey === "{dept}")' in text

def test_o18ad_terminal_content_present():
    text = APP.read_text(encoding="utf-8")
    assert "AI Pushback / Discovery Gate" in text
    assert "Discovery Question Inbox" in text
    assert "data-aion-o18ad-voice" in text
    assert "data-aion-o18ad-input" in text
    assert "Boardroom Package" in text
