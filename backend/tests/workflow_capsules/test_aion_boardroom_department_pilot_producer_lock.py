from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PRODUCER = ROOT / "desktop" / "mac" / "src" / "aion_boardroom_department_pilot_producer.js"
INDEX = ROOT / "desktop" / "mac" / "src" / "index.html"


def test_real_boardroom_founder_delegation_routes_every_enabled_department_pilot():
    source = PRODUCER.read_text(encoding="utf-8")

    assert "aion.department_task_build.live.v1" in source
    assert "tasks_ready_for_delegation_preview" in source
    assert "live_provider_fanout !== true" in source
    assert "simulated_responses === true" in source
    assert "data-aion-council-session-delegate-agents" in source
    assert "AionDepartmentPilotBackend.approveBoardroomAction" in source
    assert "finance.boardroom_analysis" in source
    assert "sales.boardroom_projection" in source
    assert "marketing.boardroom_projection" in source
    assert "operations.boardroom_projection" in source
    assert "support.boardroom_projection" in source
    assert "hr.boardroom_summary" in source
    assert "enabled_department_ids" in source
    assert "staged_departments" in source
    assert "aion:boardroom-department-actions-routed" in source
    assert "Signed Board brief" in source
    assert "do not redefine the enterprise strategy" in source
    assert "task.decision_refs" in source


def test_boardroom_producer_remains_modular_and_loads_after_legacy_app():
    index = INDEX.read_text(encoding="utf-8")
    app_position = index.index('<script src="./app.js"></script>')
    producer_position = index.index(
        '<script src="./aion_boardroom_department_pilot_producer.js"></script>'
    )

    assert producer_position > app_position
