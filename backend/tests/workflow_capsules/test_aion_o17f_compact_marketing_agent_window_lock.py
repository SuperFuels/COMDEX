from pathlib import Path

APP = Path("desktop/mac/src/app.js")

def test_o17f_compact_agent_window_installed():
    text = APP.read_text(encoding="utf-8")
    assert "BEGIN AION O17F COMPACT MARKETING AGENT WINDOW LOCK" in text
    assert "aion-o17f-compact-marketing-agent-window-style" in text
    assert "MARKETING AGENT" in text
    assert 'grid-template-columns: minmax(0, 1fr) 360px' in text
    assert "grid-area: agent" in text
    assert "height: 260px" in text
    assert "data-aion-o17e-marketing-spatial-mount" in text
    assert "data-aion-o17e-marketing-pilot-terminal" in text
