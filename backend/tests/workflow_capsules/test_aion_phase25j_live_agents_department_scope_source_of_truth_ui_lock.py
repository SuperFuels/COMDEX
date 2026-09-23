from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def live_agents_workspace_body_block():
    start = TEXT.index("function renderLiveAgentsWorkspaceBody(selectedRuns, selectedAgentCard)")
    end = TEXT.index("function renderLiveAgentsSurface", start)
    return TEXT[start:end]


def test_phase25j_department_tab_overrides_stale_agent_card_department():
    block = live_agents_workspace_body_block()

    assert "PHASE 25J HOTFIX" in block
    assert "const departmentKey = getSelectedLiveDepartmentKey();" in block
    assert "const scopedSelectedAgentCard" in block
    assert "departmentKey," in block
    assert "department: departmentKey" in block


def test_phase25j_router_passes_scoped_agent_card_to_department_surfaces():
    block = live_agents_workspace_body_block()

    assert "renderPilotMarketingWorkspaceSurface(selectedRuns, scopedSelectedAgentCard)" in block
    assert "renderFinanceWorkspaceSurface(selectedRuns, scopedSelectedAgentCard)" in block
    assert "renderSalesWorkspaceSurface(selectedRuns, scopedSelectedAgentCard)" in block
    assert "renderOperationsWorkspaceSurface(selectedRuns, scopedSelectedAgentCard)" in block
    assert "renderSupportWorkspaceSurface(selectedRuns, scopedSelectedAgentCard)" in block


def test_phase25j_router_no_longer_passes_stale_card_to_core_department_surfaces():
    block = live_agents_workspace_body_block()

    forbidden = [
        "renderPilotMarketingWorkspaceSurface(selectedRuns, selectedAgentCard)",
        "renderFinanceWorkspaceSurface(selectedRuns, selectedAgentCard)",
        "renderSalesWorkspaceSurface(selectedRuns, selectedAgentCard)",
        "renderOperationsWorkspaceSurface(selectedRuns, selectedAgentCard)",
        "renderSupportWorkspaceSurface(selectedRuns, selectedAgentCard)",
    ]

    for token in forbidden:
        assert token not in block
