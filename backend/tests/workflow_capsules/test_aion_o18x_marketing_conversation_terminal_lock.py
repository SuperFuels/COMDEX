from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o18x_marketing_conversation_terminal_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O18X MARKETING CONVERSATION TERMINAL LOCK" in text
    assert "aion-o18x-marketing-conversation-terminal-style" in text
    assert "__debugAionO18XMarketingConversationTerminal" in text
    assert "Marketing Pilot terminal becomes a Boardroom-style conversation terminal" in text

def test_o18x_ready_live_voice_and_transcript():
    text = APP.read_text(encoding="utf-8")
    assert "Press Enter to activate Marketing Pilot discovery conversation" in text
    assert "Marketing Pilot · live discovery conversation" in text
    assert "Discovery Question Inbox" in text
    assert "SpeechRecognition" in text
    assert "webkitSpeechRecognition" in text
    assert "appendTranscriptO18X" in text
    assert "saveDiscoveryAnswerO18X" in text

def test_o18x_discovery_questions_and_ledger():
    text = APP.read_text(encoding="utf-8")
    assert "active_offer" in text
    assert "monthly_budget" in text
    assert "lead_capture" in text
    assert "approval_boundary" in text
    assert "aion.departmentIntelligence.marketing" in text
    assert "live_external_actions_blocked" in text
    assert "approval_gated" in text

def test_o18x_agent_docked_inside_terminal():
    text = APP.read_text(encoding="utf-8")
    assert "dockAgentInsideTerminalO18X" in text
    assert "data-aion-o18x-agent-docked-inside-terminal" in text
    assert "agent_inside_terminal" in text
