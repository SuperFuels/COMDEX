import json

from backend.AION.system import aion_heartbeat
from backend.AION.system.aion_heartbeat import HeartbeatSupervisor, unhealthy_services


def test_running_process_services_are_live() -> None:
    state = {
        "general_apprentice": {"status": "running"},
        "mastery_curriculum": {"status": "running"},
        "receiver": {"status": "healthy"},
    }

    assert unhealthy_services(state) == []


def test_stopped_and_missing_services_are_unhealthy() -> None:
    state = {
        "general_apprentice": {"status": "running"},
        "stopped_service": {"status": "stopped"},
        "unknown_service": {},
    }

    assert unhealthy_services(state) == ["stopped_service", "unknown_service"]


def test_state_file_is_replaced_with_complete_json(tmp_path, monkeypatch) -> None:
    state_path = tmp_path / "heartbeat.json"
    state_path.write_text('{"old": true}', encoding="utf-8")
    monkeypatch.setattr(aion_heartbeat, "STATE_FILE", str(state_path))

    supervisor = HeartbeatSupervisor()
    supervisor.state = {
        "open_mission_executor": {"status": "running", "pid": 42, "restarts": 0}
    }
    supervisor.update_state_file()

    assert json.loads(state_path.read_text(encoding="utf-8")) == supervisor.state
    assert list(tmp_path.glob(".aion_heartbeat_state.*.tmp")) == []
