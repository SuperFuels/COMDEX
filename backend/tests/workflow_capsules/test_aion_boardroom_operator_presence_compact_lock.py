from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def source() -> str:
    return APP.read_text()

def test_operator_presence_renderer_uses_compact_target_not_large_panel() -> None:
    text = source()
    start = text.find("function renderBoardroomOperatorPresence()")
    end = text.find("function getWorkflowCapsuleApprovalsForBoardroom", start)
    block = text[start:end]

    assert 'class="panel operator-presence"' in block
    assert 'data-aion-boardroom-operator-presence="true"' in block
    assert 'class="panel large-panel"' not in block

def test_operator_presence_existing_compact_css_targets_renderer() -> None:
    text = source()
    assert ".aion-boardroom-frontpage-simplified .operator-presence" in text
    assert "[data-aion-boardroom-operator-presence]" in text
    assert "min-height: unset" in text
