from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP_JS = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
SALES_JS = (ROOT / "desktop/mac/src/aion_sales_revenue_workspace.js").read_text(encoding="utf-8")
HR_JS = (ROOT / "desktop/mac/src/aion_hr_people_workspace.js").read_text(encoding="utf-8")


def test_six_operating_departments_share_one_compact_director_and_package_system():
    for key in ("marketing", "sales", "finance", "operations", "support", "hr"):
        assert f'{key}: {{' in APP_JS
        assert f'renderDepartmentCompactDirectorCard("{key}")' in APP_JS
        assert f'renderAionO14KCollapsedPackageDockUnderBoardroom("{key}")' in APP_JS

    assert 'data-aion-unified-department-director=' in APP_JS
    assert 'height:176px;min-height:176px;max-height:176px' in APP_JS
    assert 'data-aion-unified-department-conversation=' in APP_JS
    assert "openUnifiedDepartmentPilotConversation" in APP_JS
    assert "department-scoped conversation" in APP_JS


def test_main_department_routes_use_the_unified_workspaces_not_legacy_black_pilots():
    expected_routes = {
        "marketing": "renderPilotMarketingWorkspaceSurface",
        "sales": "renderSalesWorkspaceSurface",
        "finance": "renderFinanceWorkspaceSurface",
        "operations": "renderOperationsWorkspaceSurface",
        "support": "renderSupportWorkspaceSurface",
        "hr": "renderHRWorkspaceSurface",
    }
    for key, renderer in expected_routes.items():
        assert f'if (departmentKey === "{key}")' in APP_JS
        assert f'return {renderer}(' in APP_JS

    assert "SUPPORTED.includes(key) && !usesUnifiedDepartmentShell" in APP_JS
    assert "AION_UNIFIED_DEPARTMENT_SHELLS" in APP_JS


def test_real_sales_and_hr_workspaces_mount_below_their_boardroom_packages():
    assert 'data-aion-sales-revenue-mount="true"' in APP_JS
    assert "'[data-aion-sales-revenue-mount=\"true\"]" in SALES_JS
    assert 'data-aion-hr-people-mount="true"' in APP_JS
    assert "'[data-aion-hr-people-mount=\"true\"]" in HR_JS


def test_finance_and_support_keep_their_completed_operational_workspaces():
    assert "window.AionFinancePilot.render()" in APP_JS
    assert 'data-aion-support-case-mount="true"' in APP_JS


def test_marketing_and_operations_no_longer_embed_the_legacy_terminal_surface():
    marketing_start = APP_JS.index("function renderPilotMarketingWorkspaceSurface")
    marketing_end = APP_JS.index("function renderMarketingManualWorkspaceSurface", marketing_start)
    marketing = APP_JS[marketing_start:marketing_end]
    assert "renderAionDepartmentScopedPilotSurface" not in marketing

    operations_start = APP_JS.index("function renderOperationsWorkspaceSurface")
    operations_end = APP_JS.index("function renderSupportCompactDirectorCard", operations_start)
    operations = APP_JS[operations_start:operations_end]
    assert "renderAionDepartmentScopedPilotSurface" not in operations
    assert 'data-aion-operations-delivery-workspace="true"' in operations


def test_hr_person_modal_preserves_unsaved_draft_during_background_refreshes():
    assert "if (!panel.draft) panel.draft = clone(initialPerson);" in HR_JS
    assert "function syncPersonDraft(form)" in HR_JS
    assert "state.panel.draft = { ...(state.panel.draft || {}), ...values };" in HR_JS
    assert "function rememberPersonDraftFocus(field)" in HR_JS
    assert "field.focus({ preventScroll: true });" in HR_JS
    assert "field.setSelectionRange(state.panel.selectionStart" in HR_JS
    assert "state.panel.scrollTop = panel.scrollTop" in HR_JS
