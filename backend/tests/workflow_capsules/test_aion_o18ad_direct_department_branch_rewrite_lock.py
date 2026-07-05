from pathlib import Path
import re

APP = Path("desktop/mac/src/app.js")

def test_o18ad_helper_installed_before_workspace_body():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18AD DIRECT DEPARTMENT BRANCH REWRITE LOCK" in text
    assert text.index("BEGIN AION O18AD DIRECT DEPARTMENT BRANCH REWRITE LOCK") < text.index("function renderLiveAgentsWorkspaceBody")
    assert "renderAionO18ADDepartmentConversationCockpit" in text
    assert "__debugAionO18ADDirectDepartmentBranchRewrite" in text

def test_o18ad_original_branches_directly_return_new_cockpit():
    text = APP.read_text(encoding="utf-8")
    for dept in ["sales", "finance", "operations", "support"]:
        pattern = (
            r'if\s*\(\s*departmentKey\s*===\s*"' + dept + r'"\s*\)\s*\{\s*'
            r'return\s+renderAionO18ADDepartmentConversationCockpit\("' + dept + r'",\s*selectedRuns,\s*selectedAgentCard\);\s*'
            r'\}'
        )
        assert re.search(pattern, text), f"missing direct O18AD return for {dept}"

def test_o18ad_terminal_content_present():
    text = APP.read_text(encoding="utf-8")
    assert "AI Pushback / Discovery Gate" in text
    assert "Discovery Question Inbox" in text
    assert "data-aion-o18ad-voice" in text
    assert "data-aion-o18ad-input" in text
    assert "Boardroom Package" in text
