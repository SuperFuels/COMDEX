from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
APP = (ROOT / "desktop/mac/src/app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "desktop/mac/src/index.html").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "desktop/mac/src/aion_project_management_workspace.js").read_text(encoding="utf-8")
ELECTRON_MAIN = (ROOT / "desktop/mac/electron/main.js").read_text(encoding="utf-8")


def test_project_management_is_a_connected_specialist_route():
    assert 'departmentKey === "projects"' in APP
    assert '["legal", "cybersecurity", "projects"]' in APP
    assert '"cybersecurity",\n    "projects",' in APP
    assert 'isProjectWorkspace ? "Project Pilot · goals, budgets and delivery control"' in APP
    assert "aion_project_management_workspace.js" in INDEX
    assert INDEX.index("aion_project_management_workspace.js") < INDEX.index('src="./app.js"')


def test_workspace_exposes_split_pilot_and_delivery_controls():
    for text in (
        "PROJECT DELIVERY COMMAND CENTRE", "Project Pilot", "Portfolio", "Timeline", "Budget",
        "Team & resources", "Risks & decisions", "Spent + committed", "People · Materials · Suppliers",
    ):
        assert text.upper() in WORKSPACE.upper()
    assert "data-pmw-resizer" in WORKSPACE
    assert 'holder.querySelector("[data-aion-project-management-root]")' in WORKSPACE
    assert "/api/aion/business/project-management" in WORKSPACE
    assert "signAionFlowRequest" in WORKSPACE
    assert '"/api/aion/business/project-management/"' in ELECTRON_MAIN


def test_project_mutations_remain_explicit_user_actions():
    for operation in ("add_task", "add_milestone", "record_cost", "add_resource", "add_risk", "add_decision"):
        assert f'"{operation}"' in WORKSPACE
    assert 'request("/agent-turn"' in WORKSPACE
    assert "approval-gated" in WORKSPACE.casefold()


def test_new_project_uses_visible_desktop_form_instead_of_native_prompts():
    assert "data-pmw-project-form" in WORKSPACE
    assert "Create a project" in WORKSPACE
    assert 'request("/projects", payload)' in WORKSPACE
    assert 'prompt("Project or job name")' not in WORKSPACE


def test_tasks_gantt_calendar_and_files_are_first_class_workspace_views():
    for text in ("data-pmw-task-form", "To-do", "Gantt", "Calendar", "Files &amp; links", "dependency_ids"):
        assert text in WORKSPACE
    assert 'prompt("Task or work item")' not in WORKSPACE
    assert 'operation: "add_file"' in WORKSPACE


def test_project_pilot_can_drive_the_plan_from_voice_or_plain_language():
    for text in ("/agent-turn", "data-pmw-voice", "Talk it through", "Controlled actions", "work_mode", "assigned_department"):
        assert text in WORKSPACE
    assert "Project Pilot changes records only through explicit project actions" not in WORKSPACE
    assert "Advanced details" in WORKSPACE


def test_project_pilot_history_scrolls_inside_the_fixed_left_pane():
    assert ".pmw-pilot{height:100%;min-height:0;overflow:hidden}" in WORKSPACE
    assert ".pmw-thread{min-height:0;overflow-y:auto;overflow-x:hidden" in WORKSPACE
    assert "thread.scrollTop = thread.scrollHeight" in WORKSPACE
    assert ".pmw-pilot-title,.pmw-chat{flex:none}" in WORKSPACE


def test_finance_keeps_the_developed_runtime_as_its_primary_workspace():
    finance_renderer = APP[APP.index("function renderFinanceWorkspaceSurface"):APP.index("function renderFinancePilotCommandCentre")]
    assert 'window.renderAionDepartmentPilotRuntime("finance")' in finance_renderer
    assert finance_renderer.index('window.renderAionDepartmentPilotRuntime("finance")') < finance_renderer.index("window.AionFinancePilot.render()")
