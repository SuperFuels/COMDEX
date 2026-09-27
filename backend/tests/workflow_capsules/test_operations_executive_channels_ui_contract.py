from pathlib import Path


APP = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")
ROUTER = Path("backend/api/workflow_capsule_router.py").read_text(encoding="utf-8")
DESKTOP_BACKEND = Path("backend/desktop_app.py").read_text(encoding="utf-8")


def test_operations_command_centre_has_live_department_channel_controls():
    for marker in (
        'data-aion-operations-run-briefing',
        'data-aion-operations-channel-thread',
        'data-aion-operations-channel-form',
        'data-aion-operations-channel-input',
        'data-aion-operations-briefing-mode',
    ):
        assert marker in APP


def test_operations_frontend_calls_protected_executive_routes():
    for route in ("executive-status", "channel-history", "channel-turn", "morning-briefing"):
        assert f'"{route}"' in APP
        assert f'operations-conversation/{route}' in ROUTER


def test_department_channels_do_not_render_the_old_placeholder():
    command = APP[APP.index("function renderOperationsCommandCentre"):]
    assert "Once the Mission bridge is connected" not in command[:18_000]


def test_desktop_scheduler_runs_due_morning_briefing_without_operations_page_open():
    assert "executive_briefings.status(workspace.name)" in DESKTOP_BACKEND
    assert 'if briefing_status.get("briefing_due")' in DESKTOP_BACKEND
    assert "executive_briefings.run_morning_briefing" in DESKTOP_BACKEND
