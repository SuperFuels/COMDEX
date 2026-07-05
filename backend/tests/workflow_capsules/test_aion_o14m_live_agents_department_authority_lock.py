from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_o14m_department_authority_lock_installed():
    assert "BEGIN AION O14M LIVE AGENTS DEPARTMENT AUTHORITY LOCK" in APP
    assert "aionO14MSetLiveAgentsDepartmentAuthority" in APP
    assert "installAionO14MLiveAgentsDepartmentAuthorityLock" in APP


def test_o14m_finance_guard_is_one_shot_not_permanent_trap():
    assert "financeFirstRouted.v1" in APP
    assert "const forced = (financeFirst && !alreadyRouted) || explicitFinance;" in APP
    assert 'localStorage.setItem("aion.businessTwin.financeFirstRouted.v1", "true");' in APP


def test_o14m_non_finance_department_clears_finance_trap():
    assert 'localStorage.removeItem("aion.businessTwin.financeFirst.v1");' in APP
    assert 'localStorage.removeItem("aion.businessTwin.financeFirstRouted.v1");' in APP
    assert 'localStorage.removeItem("aion.liveAgents.forceFinance.v1");' in APP


def test_o14m_click_capture_uses_department_attributes():
    assert "[data-aion-o14l-executive-department]" in APP
    assert "[data-aion-live-agents-department]" in APP
    assert "[data-live-agents-department]" in APP
    assert "[data-aion-department-pilot]" in APP
    assert "[data-aion-department-key]" in APP
    assert 'window.addEventListener(eventName, handleDepartmentClickO14M, true);' in APP
    assert 'document.addEventListener(eventName, handleDepartmentClickO14M, true);' in APP


def test_o14m_department_authority_updates_state_and_windows():
    assert 'state.selectedLiveAgentDepartment = key;' in APP
    assert 'state.liveAgentsSelectedDepartment = key;' in APP
    assert 'state.activeLiveAgentDepartment = key;' in APP
    assert 'state.liveAgentsWorkspaceMode = key;' in APP
    assert 'window.__aionActiveLiveAgentsDepartment = key;' in APP
    assert 'window.__aionO14A6ActiveDepartmentPilot = key;' in APP
