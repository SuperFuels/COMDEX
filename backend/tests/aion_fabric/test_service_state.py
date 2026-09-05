from __future__ import annotations

import os
import threading
import time

from backend.modules.aion_fabric.service_state import ConnectionHealthMonitor, PrivateServiceState


def test_private_service_credentials_survive_restart(tmp_path) -> None:
    first = PrivateServiceState(tmp_path).load()
    second = PrivateServiceState(tmp_path).load()

    assert first == second
    assert len(first["companion_pair_code"]) == 6
    assert oct(os.stat(tmp_path / "private_service_state.json").st_mode & 0o777) == "0o600"


def test_connection_monitor_recovers_without_restarting() -> None:
    attempts = 0
    recovered = threading.Event()

    def check():
        nonlocal attempts
        attempts += 1
        connected = attempts >= 2
        if connected:
            recovered.set()
        return {"connected": connected, "host": "192.0.2.5"}

    monitor = ConnectionHealthMonitor(check, interval_seconds=0.01)
    monitor.start()
    try:
        monitor.retry_now()
        assert recovered.wait(2)
        limit = time.monotonic() + 1
        while monitor.snapshot()["status"] != "connected" and time.monotonic() < limit:
            time.sleep(0.01)
        state = monitor.snapshot()
        assert state["status"] == "connected"
        assert state["consecutive_failures"] == 0
    finally:
        monitor.stop()
