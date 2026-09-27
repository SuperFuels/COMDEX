from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")


def test_sidebar_p_opens_central_departments_hub():
    assert 'if (route === "live_agents") {' in APP
    assert "window.__aionDepartmentsHubOpenV1 = true" in APP
    assert "function renderAionDepartmentsHubV1()" in APP
    assert 'data-aion-departments-hub="true"' in APP
    assert "return renderAionDepartmentsHubV1();" in APP


def test_sticky_and_hub_shortcuts_still_open_real_department_workspaces():
    assert "window.__aionDepartmentsHubOpenV1 = false" in APP
    assert 'data-aion-departments-hub-open-core="${escapeHtml(route)}"' in APP
    assert "openAionExecutiveDepartmentFromStickyHeaderV1(departmentKey" in APP
    for route in (
        "marketing",
        "sales",
        "finance",
        "operations",
        "support",
        "hr",
        "products_services",
    ):
        assert f'key: "{route}"' in APP


def test_hub_lists_specialists_without_claiming_uninstalled_harnesses_are_connected():
    for name in (
        "Legal support",
        "Cybersecurity",
        "IT & systems",
        "Compliance & privacy",
        "Procurement",
        "Project management",
        "Design & creative",
        "Software engineering",
        "Communications & PR",
    ):
        assert f'name: "{name}"' in APP
    assert "Specialist model · harness not installed" in APP
    assert "Available to add" in APP
    assert "getAionDepartmentsHubCustomMatchV1" in APP


def test_recruitment_is_part_of_people_not_a_duplicate_department():
    core_start = APP.index("const AION_DEPARTMENTS_HUB_CORE_V1")
    specialist_start = APP.index("const AION_DEPARTMENTS_HUB_SPECIALIST_V1")
    core = APP[core_start:specialist_start]
    specialists = APP[specialist_start:APP.index("function normaliseAionDepartmentHubMatchV1", specialist_start)]
    assert 'name: "People"' in core
    assert 'note: "Includes recruitment"' in core
    assert 'name: "Recruitment"' not in specialists

