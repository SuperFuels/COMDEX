from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_support_workspace_replaces_placeholder_with_governed_case_centre():
    index = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    support = (ROOT / "desktop/mac/src/aion_support_case_workspace.js").read_text(encoding="utf-8")
    assert '<script src="./aion_support_case_workspace.js"></script>' in index
    assert 'data-aion-support-live-agents-workspace-o14d="true"' in app
    support_renderer = app.split("function renderSupportWorkspaceSurface", 1)[1].split(
        "function renderHRWorkspaceSurface", 1)[0]
    assert 'data-aion-support-case-mount="true"' in support_renderer
    assert "renderSupportCompactDirectorCard()" in support_renderer
    assert 'renderAionDepartment121BoardroomPanelO14D("support")' not in support_renderer
    assert 'renderAionDepartmentScopedPilotSurface("support"' not in support_renderer
    compact_director = app.split("function renderSupportCompactDirectorCard", 1)[1].split(
        "function renderSupportWorkspaceSurface", 1)[0]
    assert 'renderDepartmentCompactDirectorCard("support")' in compact_director
    unified_director = app.split("function renderDepartmentCompactDirectorCard", 1)[1].split(
        "function renderFinanceWorkspaceSurface", 1
    )[0]
    assert 'data-aion-unified-department-director=' in unified_director
    assert 'data-aion-unified-department-copy=' in unified_director
    assert 'data-aion-unified-department-portrait=' in unified_director
    assert "SPATIAL SUPPORT BOARDROOM" not in compact_director
    live_router = app.split("function renderLiveAgentsWorkspaceBody", 1)[1].split(
        "function renderLiveAgentRunRow", 1)[0]
    assert 'if (departmentKey === "support")' in live_router
    assert "return renderSupportWorkspaceSurface(selectedRuns, scopedSelectedAgentCard);" in live_router
    assert '["marketing", "sales", "operations", "support", "hr"]' not in live_router
    assert "Support Case Centre" in support
    assert "SUPPORT AGENT STUDIO" in support
    assert "NO AUTONOMOUS REFUNDS" in support
    assert "Prepare—do not send—a support reply" in support
    assert "Record verified resolution" in support
    assert "consumer-law" in support


def test_support_ui_exposes_authority_and_evidence_controls():
    support = (ROOT / "desktop/mac/src/aion_support_case_workspace.js").read_text(encoding="utf-8")
    assert "Exact-approved refund ceiling" in support
    assert "Legal self-authority: never" in support
    assert "Provider thread ID" in support
    assert "Evidence reference" in support
    assert "Customer confirmation" in support
    assert "Legal/privacy authority" in support
    assert "Import support email" in support
    assert "Create secured website door" in support
    assert "Create Gmail draft" in support


def test_support_workspace_exposes_read_only_dashboard_bridge_and_case_deep_link():
    support = (ROOT / "desktop/mac/src/aion_support_case_workspace.js").read_text(encoding="utf-8")
    assert "ensureDashboardData" in support
    assert "snapshot:()=>state.data" in support
    assert "openCase" in support
    assert "aion:support-workspace-updated" in support
    assert "load(false)" in support


def test_support_visible_load_does_not_redraw_the_app_or_poll_the_mount_each_second():
    support = (ROOT / "desktop/mac/src/aion_support_case_workspace.js").read_text(encoding="utf-8")
    app = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
    assert "if (requireVisibleMount) {\n        render();\n      } else {" in support
    assert "if (!root.querySelector('[data-aion-support-cases]')) render();" in support
    assert "setInterval(attemptMount, 1000)" not in support
    assert 'if (state.activeTab === "dashboard") requestRender?.();' in app
