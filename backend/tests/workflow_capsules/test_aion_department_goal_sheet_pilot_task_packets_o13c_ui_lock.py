from pathlib import Path

APP_JS = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def block():
    assert "BEGIN AION O13C DEPARTMENT GOAL SHEET PILOT TASK PACKETS" in APP_JS
    return APP_JS.split("BEGIN AION O13C DEPARTMENT GOAL SHEET PILOT TASK PACKETS", 1)[1].split(
        "END AION O13C DEPARTMENT GOAL SHEET PILOT TASK PACKETS", 1
    )[0]


def test_o13c_installed():
    b = block()
    assert "department Goal Sheet Pilot task packets installed" in b
    assert "aionBuildPilotTaskPacketsForDepartmentSheetO13C" in b
    assert "aionBuildAllDepartmentPilotTaskPacketsO13C" in b
    assert "aionBuildActiveDepartmentPilotTaskPacketsO13C" in b


def test_o13c_builds_packet_from_department_sheet_nodes():
    b = block()
    assert "buildPilotTaskPacketFromNodeO13C" in b
    assert "extractTaskSourceNodesO13C" in b
    assert "source_node_id" in b
    assert "source_workflow_id" in b
    assert "source_node_type" in b


def test_o13c_packets_have_pilot_owners_and_surfaces():
    b = block()
    assert "agent_owner" in b
    assert "pilot_surface" in b
    assert "live_agents.${department}" in b
    assert "central_pilot_visible: true" in b
    assert "department_pilot_visible: true" in b


def test_o13c_preview_safety_flags_block_execution():
    b = block()
    assert "preview_only: true" in b
    assert "approval_required: true" in b
    assert "execution_allowed_now: false" in b
    assert "connector_call_required: false" in b
    assert "external_side_effects: false" in b
    assert "booking_created: false" in b
    assert "payment_created: false" in b
    assert "customer_message_sent: false" in b


def test_o13c_queue_reuses_existing_pilot_surfaces():
    b = block()
    assert "existing_central_pilot_reused: true" in b
    assert "existing_department_pilots_reused: true" in b
    assert "visible_in_existing_central_pilot: true" in b
    assert "visible_in_existing_department_pilots: true" in b


def test_o13c_supports_all_five_departments():
    b = block()
    for department in ["marketing", "sales", "finance", "operations", "support"]:
      assert f'"{department}"' in b


def test_o13c_global_queue_exports_are_available():
    b = block()
    assert "window.__aionGoalSheetPilotTaskQueueO13C" in b
    assert "window.__aionGoalLoopPilotQueuePreview" in b
    assert "window.__aionCentralPilotGoalSheetTaskQueuePreview" in b
    assert "window.__aionGoalSheetActiveDepartmentPilotTaskQueueO13C" in b


def test_o13c_has_department_sheet_toolbar_not_modal():
    b = block()
    assert "aion-o13c-pilot-task-toolbar" in b
    assert "Build Pilot Task Packets" in b
    assert "data-aion-o13c-build-active-pilot-task-packets" in b
