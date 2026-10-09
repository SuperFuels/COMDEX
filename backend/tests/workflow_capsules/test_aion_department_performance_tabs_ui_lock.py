from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "desktop/mac/src/styles.css").read_text(encoding="utf-8")


def test_department_pages_own_their_performance_tabs():
    for department in ("sales", "operations", "people", "support"):
        assert f'renderAionDepartmentFunctionalTabsV1("{department}"' in APP or (
            f'renderAionDepartmentTabbedWorkspaceV1("{department}"' in APP
        )
        assert f'renderAionDepartmentPerformanceOverviewV1("{department}")' in APP or (
            'renderAionDepartmentPerformanceOverviewV1(department)' in APP
        )

    assert 'data-aion-finance-functional-section="performance"' in APP
    assert 'renderAionDepartmentPerformanceOverviewV1("finance")' in APP
    assert 'renderAionDepartmentTabbedWorkspaceV1("products_services", "Operating model"' in APP


def test_performance_tabs_reuse_verified_department_snapshots():
    for renderer in (
        "renderAionSalesFunctionSnapshotV1",
        "renderAionFinanceFunctionSnapshotV1",
        "renderAionSupportFunctionSnapshotV1",
        "renderAionPeopleFunctionSnapshotV1",
    ):
        assert renderer in APP

    assert "renderAionDepartmentGenericPerformanceV1" in APP
    assert 'modelKey = requestedKey === "people" ? "hr" : requestedKey' in APP


def test_department_performance_owns_targets_actuals_and_work_queue():
    assert "renderAionDepartmentTargetsAndQueueV1" in APP
    assert 'data-aion-department-targets-results="true"' in APP
    assert 'data-aion-department-work-queue="true"' in APP
    assert "Targets are set by the founder or Boardroom" in APP
    assert 'data-aion-department-kpi-boardroom=' in APP
    assert "renderAionDepartmentTargetsAndQueueV1(marketingDepartment)" in APP
    assert ".aion-department-accountability" in STYLES


def test_department_tab_branding_is_shared_after_dashboard_retirement():
    assert ".aion-department-functional-tabs" in STYLES
    assert ".aion-department-performance" in STYLES
    assert '{ key: "dashboard", label: "Dashboard" }' not in APP
    assert 'if (state.activeTab === "dashboard") {\n    return renderDashboardSurface();' not in APP
    assert 'const supportedTabKey = resolvedTabKey === "dashboard" ? "boardroom" : resolvedTabKey;' in APP
