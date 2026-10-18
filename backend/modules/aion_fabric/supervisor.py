from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict

from .canonical import utc_now_iso
from .runtime import AionFabricRuntime


@dataclass(slots=True)
class AutonomousDiscoverySupervisor:
    runtime: AionFabricRuntime
    interval_seconds: float = 300.0
    initial_delay_seconds: float = 2.0
    _stop: threading.Event = field(default_factory=threading.Event, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)
    last_started_at: str | None = None
    last_completed_at: str | None = None
    last_observation_count: int = 0
    last_error: str | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="aion-fabric-discovery", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def _run(self) -> None:
        if self._stop.wait(max(0.0, self.initial_delay_seconds)):
            return
        while not self._stop.is_set():
            self.last_started_at = utc_now_iso()
            try:
                result = self.runtime.scan_devices(timeout_seconds=2.5)
                self.last_observation_count = len(result["run"]["observations"])
                self.last_error = None
                self.last_completed_at = utc_now_iso()
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                self.last_completed_at = utc_now_iso()
            if self._stop.wait(max(30.0, self.interval_seconds)):
                return

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self._thread and self._thread.is_alive()),
            "interval_seconds": self.interval_seconds,
            "last_started_at": self.last_started_at,
            "last_completed_at": self.last_completed_at,
            "last_observation_count": self.last_observation_count,
            "last_error": self.last_error,
        }
