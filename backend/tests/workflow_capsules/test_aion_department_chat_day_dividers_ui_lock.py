from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text()
BACKEND = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text()


def test_department_conversations_group_turns_by_local_calendar_day():
    assert "function getAionConversationCalendarDay" in APP
    assert "function renderAionConversationDayDivider" in APP
    assert "function renderAionDatedConversationTurns" in APP
    assert 'weekday: "long", day: "numeric", month: "long", year: "numeric"' in APP
    assert 'data-aion-conversation-day' in APP


def test_people_and_operations_use_dated_conversation_rendering():
    assert 'renderAionDatedConversationTurns(turns, renderAionPeopleConversationTurn, "#0f766e")' in APP
    assert 'renderAionDatedConversationTurns(turns, renderAionOperationsConversationTurn, "#4f46e5")' in APP
    assert 'renderAionDatedConversationTurns(turns, renderAionOperationsDepartmentTurn, "#0f766e")' in APP
    assert 'appendAionDatedConversationTurn(thread, { role: "user", content: text }, renderAionPeopleConversationTurn' in APP
    assert 'appendAionDatedConversationTurn(thread, { role: "user", content: text }, renderAionOperationsConversationTurn' in APP


def test_finance_grounded_conversation_renders_matching_day_bands():
    assert 'class="aion-finance-conversation-day"' in BACKEND
    assert "weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'" in BACKEND
    assert '.aion-finance-conversation-day span' in APP
