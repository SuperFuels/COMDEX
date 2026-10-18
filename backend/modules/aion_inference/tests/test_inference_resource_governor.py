from __future__ import annotations

import signal
import subprocess

import pytest

from backend.modules.aion_inference.inference_resource_governor import (
    InferencePriorityLease,
)


class _Watchdog:
    pid = 4321

    def __init__(self) -> None:
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int) -> int:
        assert timeout == 2
        return 0


def test_lease_stops_and_resumes_only_verified_service(tmp_path, monkeypatch) -> None:
    lock = tmp_path / "mastery.lock"
    lock.write_text("123\n", encoding="ascii")
    signals: list[tuple[int, signal.Signals]] = []
    watchdog = _Watchdog()
    monkeypatch.setattr(
        subprocess,
        "check_output",
        lambda *args, **kwargs: "python aion_mastery_curriculum_service.py\n",
    )
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: watchdog)
    monkeypatch.setattr("os.kill", lambda pid, value: signals.append((pid, value)))

    lease = InferencePriorityLease(
        lock, expected_command="aion_mastery_curriculum_service.py", timeout_seconds=60
    )
    acquired = lease.acquire()
    released = lease.release()

    assert acquired["active"] is True
    assert released["active"] is False
    assert signals == [(123, signal.SIGSTOP), (123, signal.SIGCONT)]
    assert watchdog.terminated is True


def test_lease_rejects_stale_pid_command_without_signalling(tmp_path, monkeypatch) -> None:
    lock = tmp_path / "mastery.lock"
    lock.write_text("123\n", encoding="ascii")
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "unrelated")
    monkeypatch.setattr("os.kill", lambda *args: pytest.fail("must not signal"))
    lease = InferencePriorityLease(
        lock, expected_command="aion_mastery_curriculum_service.py", timeout_seconds=60
    )
    with pytest.raises(RuntimeError, match="did not match"):
        lease.acquire()


@pytest.mark.parametrize("value", ["", "not-a-pid", "0", "1"])
def test_lease_rejects_unsafe_lock_values(tmp_path, value) -> None:
    lock = tmp_path / "mastery.lock"
    lock.write_text(value, encoding="ascii")
    lease = InferencePriorityLease(
        lock, expected_command="aion_mastery_curriculum_service.py", timeout_seconds=60
    )
    with pytest.raises(RuntimeError):
        lease.acquire()

