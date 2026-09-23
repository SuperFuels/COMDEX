from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13E3 REAL DEPARTMENT PILOT SURFACE GOAL SHEET QUEUES" in APP_JS
    return APP_JS.split("BEGIN AION O13E3 REAL DEPARTMENT PILOT SURFACE GOAL SHEET QUEUES", 1)[1].split(
        "END AION O13E3 REAL DEPARTMENT PILOT SURFACE GOAL SHEET QUEUES", 1
    )[0]


def test_o13e3_installed():
    b = block()
    assert "real department Pilot surface Goal Sheet queues installed" in b
    assert "aionRenderDepartmentPilotGoalSheetQueuePanelO13E3" in b
    assert "aionRenderCentralPilotGoalSheetQueuePanelO13E3" in b


def test_o13e3_wraps_real_department_scoped_pilot_surface():
    b = block()
    assert "renderAionDepartmentScopedPilotSurface" in b
    assert "renderAionDepartmentScopedPilotSurfaceWithGoalSheetQueue" in b
    assert "__aionO13E3Wrapped" in b
    assert "return `${panel}${originalHtml}`" in b


def test_o13e3_wraps_real_central_pilot_work_package_card():
    b = block()
    assert "renderAionPilotWorkPackageCard" in b
    assert "renderAionPilotWorkPackageCardWithGoalSheetQueue" in b
    assert "Central Pilot coordination queue" in b


def test_o13e3_uses_o13d_preview_state_and_o13c_packets():
    b = block()
    assert "aionPublishPilotPreviewStateO13D" in b
    assert "__aionGoalLoopPilotQueuePreview" in b
    assert "__aionGoalSheetPilotTaskQueueO13C" in b
    assert "__aionCentralPilotGoalSheetTaskQueuePreview" in b


def test_o13e3_department_panel_shows_real_packet_rows():
    b = block()
    assert "renderAionDepartmentPilotGoalSheetQueuePanelO13E3" in b
    assert "data-aion-o13e3-real-department-pilot-goal-sheet-queue" in b
    assert "data-aion-o13e3-pilot-task" in b
    assert "source_workflow_id" in b
    assert "source_node_type" in b


def test_o13e3_supports_all_real_department_pilots():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
        assert f'"{department}"' in b


def test_o13e3_safety_contract_visible():
    b = block()
    assert "Preview only" in b
    assert "No execution" in b
    assert "No connector calls" in b
    assert "Approval required" in b
    assert "No live execution" in b
    assert "No customer actions" in b


def test_o13e3_not_floating_overlay():
    b = block()
    assert "position: fixed" not in b
    assert "document.body.appendChild" not in b
    assert "appendChild(shell)" not in b
    assert "return `${panel}${originalHtml}`" in b
