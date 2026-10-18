from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
PACKAGED_APP = (ROOT / "desktop/mac/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")
PRELOAD = (ROOT / "desktop/mac/electron/preload.js").read_text(encoding="utf-8")
GATEWAY = (ROOT / "backend/modules/pilot_unified/workspace_gateway.py").read_text(encoding="utf-8")


def test_custom_department_selector_is_present_on_every_sticky_header_variant():
    assert "function renderAionCustomDepartmentSelectV1" in APP
    assert "Open a user-created department or sub-department" in APP
    assert APP.count("trailingControl: renderAionCustomDepartmentSelectV1(") == 3
    assert "renderAionBoardroomStickyTeamHeaderV1" in APP
    assert "renderAionDepartmentPilotsStickyHeaderV1" in APP
    assert "renderAionSharedPageExecutiveHeaderV1" in APP


def test_selector_is_hierarchy_aware_and_keeps_custom_navigation_contract():
    selector_start = APP.index("function renderAionCustomDepartmentSelectV1")
    selector_end = APP.index("function renderAionCustomDepartmentCreatorV1", selector_start)
    selector = APP[selector_start:selector_end]
    assert "parent_department_id" in selector
    assert "children.get(id)" in selector
    assert '"↳ ".repeat(depth)' in selector
    assert 'data-aion-custom-department-select="true"' in selector
    assert "openAionExecutiveDepartmentFromStickyHeaderV1(select.value)" in APP


def test_custom_departments_are_loaded_for_the_active_business_workspace():
    assert "function getAionDesktopDepartmentWorkspaceIdV1" in APP
    assert "AionBusinessContainerClient?.resolveBusinessId?.()" in APP
    assert "listCustomDepartments?.({ workspace_id: workspaceId })" in APP
    assert 'ipcRenderer.invoke("aion-custom-departments-list", payload)' in PRELOAD
    assert "normalizeAionCustomDepartmentWorkspaceId" in MAIN
    assert "readAionCustomDepartments(workspaceId)" in MAIN


def test_parent_department_metadata_survives_desktop_and_gateway_normalization():
    assert "parent_department_id: item.parent_department_id || item.parent_id || null" in MAIN
    assert '"parent_department_id", "created_at"' in GATEWAY
    assert 'department.get("parent_department_id")' in GATEWAY
    assert 'raise ValueError("parent custom department was not found")' in GATEWAY


def test_source_and_packaged_desktop_bundles_remain_identical():
    assert APP == PACKAGED_APP

