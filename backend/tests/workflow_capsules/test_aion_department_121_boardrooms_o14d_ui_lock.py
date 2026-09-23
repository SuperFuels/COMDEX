from pathlib import Path

APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
RENDERER = Path("desktop/mac/src/lib/desktop-boardroom-renderer.js").read_text(encoding="utf-8")


def test_renderer_filters_forced_visible_seats_by_visible_departments():
    assert "allowedForcedDepartments" in RENDERER
    assert "options.visibleDepartments" in RENDERER
    assert ".filter(([key]) => !allowedForcedDepartments || allowedForcedDepartments.has" in RENDERER


def test_renderer_supports_generic_department_121_mode():
    assert "department121Match" in RENDERER
    assert "String(teamMode || \"\").match(/^([a-z0-9_]+)_121$/)" in RENDERER
    assert "seatsToRender = [[department121Key, department121Label[0], department121Label[1]]]" in RENDERER
    assert "1:1 DEPARTMENT ROOM · SAFE EXECUTION" in RENDERER


def test_app_has_generic_department_121_snapshot_and_mount():
    assert "AION_O14D_DEPARTMENT_121_CONFIG" in APP
    assert "buildAionDepartment121BoardroomSnapshotO14D" in APP
    assert "renderAionDepartment121BoardroomPanelO14D" in APP
    assert "mountAionDepartment121BoardroomRendererO14D" in APP
    assert "visibleDepartments: [key]" in APP
    assert "boardroomTeamMode: `${key}_121`" in APP


def test_all_key_live_agent_departments_render_own_121_room():
    for department in ["finance", "sales", "operations", "support", "hr"]:
        assert f'renderAionDepartment121BoardroomPanelO14D("{department}")' in APP

    assert "renderAionDepartmentScopedPilotSurface(\"finance\"" in APP
    assert "renderAionDepartmentScopedPilotSurface(\"sales\"" in APP
    assert "renderAionDepartmentScopedPilotSurface(\"operations\"" in APP
    assert "renderAionDepartmentScopedPilotSurface(\"support\"" in APP
