from __future__ import annotations

import threading

from backend.modules.aion_fabric.supervisor import AutonomousDiscoverySupervisor


class FakeRuntime:
    def __init__(self):
        self.called = threading.Event()

    def scan_devices(self, *, timeout_seconds):
        self.called.set()
        return {"run": {"observations": [{"id": "one"}]}}


def test_autonomous_supervisor_runs_bounded_discovery_and_stops():
    runtime = FakeRuntime()
    supervisor = AutonomousDiscoverySupervisor(runtime, interval_seconds=30, initial_delay_seconds=0)
    supervisor.start()
    assert runtime.called.wait(timeout=2)
    supervisor.stop()
    status = supervisor.status()
    assert status["last_observation_count"] == 1
    assert status["last_error"] is None
    assert status["enabled"] is False
