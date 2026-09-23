"""Reversible resource arbitration for latency-sensitive local inference."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


class InferencePriorityLease:
    """Temporarily yield one verified background AION service.

    A detached watchdog always resumes the service after ``timeout_seconds``.
    Normal release resumes it immediately.  The command check prevents a stale
    lock-file PID from stopping an unrelated process.
    """

    def __init__(
        self,
        process_lock: Path,
        *,
        expected_command: str,
        timeout_seconds: int = 1800,
    ) -> None:
        if timeout_seconds < 60:
            raise ValueError("resource lease timeout must be at least 60 seconds")
        self.process_lock = process_lock.resolve()
        self.expected_command = expected_command
        self.timeout_seconds = int(timeout_seconds)
        self.pid: int | None = None
        self.command: str | None = None
        self.acquired_at: float | None = None
        self.released_at: float | None = None
        self._watchdog: subprocess.Popen[bytes] | None = None
        self._active = False

    def _resolve_verified_pid(self) -> tuple[int, str]:
        try:
            value = self.process_lock.read_text(encoding="ascii").strip()
            pid = int(value)
        except (OSError, ValueError) as error:
            raise RuntimeError("background service lock has no valid PID") from error
        if pid <= 1 or pid == os.getpid():
            raise RuntimeError("background service PID is unsafe")
        try:
            command = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "command="], text=True
            ).strip()
        except subprocess.CalledProcessError as error:
            raise RuntimeError("background service PID is not running") from error
        if self.expected_command not in command:
            raise RuntimeError("background service PID command did not match")
        return pid, command

    def acquire(self) -> dict[str, Any]:
        if self._active:
            raise RuntimeError("resource lease is already active")
        pid, command = self._resolve_verified_pid()
        watchdog_program = (
            "import os,signal,sys,time;"
            "time.sleep(float(sys.argv[2]));"
            "\ntry: os.kill(int(sys.argv[1]), signal.SIGCONT)"
            "\nexcept ProcessLookupError: pass"
        )
        watchdog = subprocess.Popen(
            [sys.executable, "-c", watchdog_program, str(pid), str(self.timeout_seconds)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            os.kill(pid, signal.SIGSTOP)
        except BaseException:
            watchdog.terminate()
            raise
        self.pid = pid
        self.command = command
        self.acquired_at = time.time()
        self._watchdog = watchdog
        self._active = True
        return self.snapshot()

    def release(self) -> dict[str, Any]:
        if self._active and self.pid is not None:
            try:
                os.kill(self.pid, signal.SIGCONT)
            except ProcessLookupError:
                pass
            self.released_at = time.time()
            self._active = False
        if self._watchdog is not None:
            self._watchdog.terminate()
            try:
                self._watchdog.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._watchdog.kill()
                self._watchdog.wait(timeout=2)
            self._watchdog = None
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "aion.inference-priority-lease.v1",
            "process_lock": str(self.process_lock),
            "expected_command": self.expected_command,
            "pid": self.pid,
            "verified_command": self.command,
            "timeout_seconds": self.timeout_seconds,
            "acquired_at_epoch": self.acquired_at,
            "released_at_epoch": self.released_at,
            "active": self._active,
            "watchdog_pid": self._watchdog.pid if self._watchdog is not None else None,
        }

    def write_receipt(self, path: Path) -> None:
        path.write_text(json.dumps(self.snapshot(), indent=2, sort_keys=True) + "\n")

