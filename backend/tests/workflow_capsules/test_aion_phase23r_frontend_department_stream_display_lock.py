from pathlib import Path

FRONTEND = Path("desktop/mac/src/app.js").read_text()
BACKEND = Path("backend/api/local_node_router.py").read_text()


def test_phase23r_frontend_department_set_is_new_business_control_room_set():
    assert '["marketing", "Marketing"]' in FRONTEND
    assert '["pilot", "Pilot"]' in FRONTEND
    assert '["sales", "Sales"]' in FRONTEND
    assert '["finance", "Finance"]' in FRONTEND
    assert '["operations", "Operations"]' in FRONTEND
    assert '["support", "Support"]' in FRONTEND
    assert '["builder", "Builder"]' in FRONTEND


def test_phase23r_operations_agent_selector_uses_new_department_set():
    assert 'const OPERATIONS_AGENT_DEPARTMENTS = [' in FRONTEND
    assert '"Builder",' in FRONTEND
    assert '"Pilot",' in FRONTEND
    assert '"HR",' not in FRONTEND


def test_phase23r_legacy_aion_department_aliases_to_pilot():
    assert 'if (key === "aion") return "pilot";' in FRONTEND
    assert '<div class="surface-eyebrow">Live Agents / Pilot</div>' in FRONTEND


def test_phase23r_removed_placeholder_departments_do_not_render_as_workspaces():
    body_start = FRONTEND.find("function renderLiveAgentsWorkspaceBody")
    assert body_start >= 0
    body_end = FRONTEND.find("\\nfunction ", body_start + 1)
    body = FRONTEND[body_start:body_end if body_end > 0 else len(FRONTEND)]

    assert 'departmentKey === "hr"' not in body
    assert 'departmentKey === "ceo"' not in body
    assert 'departmentKey === "coo"' not in body
    assert 'departmentKey === "aion"' not in body
    assert 'departmentKey === "pilot"' in body
    assert 'departmentKey === "builder"' in body


def test_phase23r_mission_preview_returns_department_and_tool_queues():
    assert '"department_route": department_route' in BACKEND
    assert '"department_queue": department_queue_with_blocked_live_actions' in BACKEND
    assert '"tool_execution_queue": tool_execution_queue' in BACKEND
    assert '"tool_execution_summary": summarize_tool_execution_queue(tool_execution_queue)' in BACKEND
    assert '"marketing_department_pack": marketing_department_pack' in BACKEND


def test_phase23r_backend_reuses_phase23_modules_in_route_not_frontend_mocking():
    assert "create_marketing_department_pack" in BACKEND
    assert "route_business_function" in BACKEND
    assert "build_department_execution_queue" in BACKEND
    assert "build_pilot_tool_execution_queue" in BACKEND
