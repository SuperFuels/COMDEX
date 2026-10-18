from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "desktop" / "mac" / "src" / "app.js"

def test_o16b_department_resolver_lock_installed():
    text = APP.read_text(encoding="utf-8")
    assert "O16B LIVE AGENTS DEPARTMENT RESOLVER LOCK" in text
    assert "function getSelectedLiveDepartmentKey()" in text
    assert "window.__aionO16ASelectedLiveAgentsDepartment" in text

def test_o16b_resolver_accepts_all_live_agents_departments():
    text = APP.read_text(encoding="utf-8")
    block = text[text.find("BEGIN AION O16B"):text.find("END AION O16B")]
    for key in ["marketing", "sales", "finance", "operations", "support", "hr", "pilot", "builder"]:
        assert f'"{key}"' in block

def test_o16b_resolver_prefers_selected_state_before_default():
    text = APP.read_text(encoding="utf-8")
    block = text[text.find("BEGIN AION O16B"):text.find("END AION O16B")]
    assert "window.__aionO16ASelectedLiveAgentsDepartment" in block
    assert "window.__aionO14A6ClickedDepartmentPilot" in block
    assert 'return "marketing"' in block
