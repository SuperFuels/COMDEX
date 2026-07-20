from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PRODUCER = ROOT / "desktop" / "mac" / "src" / "aion_boardroom_department_pilot_producer.js"
INDEX = ROOT / "desktop" / "mac" / "src" / "index.html"


def test_real_boardroom_founder_delegation_routes_only_enabled_finance_pilot():
    source = PRODUCER.read_text(encoding="utf-8")

    assert "aion.department_task_build.live.v1" in source
    assert "tasks_ready_for_delegation_preview" in source
    assert "live_provider_fanout !== true" in source
    assert "simulated_responses === true" in source
    assert "data-aion-council-session-delegate-agents" in source
    assert "AionDepartmentPilotBackend.approveBoardroomAction" in source
    assert "finance.boardroom_analysis" in source
    assert "non-Finance task(s) remain design-gated" in source
    assert "aion:boardroom-finance-actions-routed" in source


def test_boardroom_producer_remains_modular_and_loads_after_legacy_app():
    index = INDEX.read_text(encoding="utf-8")
    app_position = index.index('<script src="./app.js"></script>')
    producer_position = index.index(
        '<script src="./aion_boardroom_department_pilot_producer.js"></script>'
    )

    assert producer_position > app_position
