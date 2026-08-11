"""Restart-persistent, fail-closed background polling for Support channels."""

from __future__ import annotations

from threading import Event, Lock, Thread
from typing import Any

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.support_case_service import SupportCaseService


class SupportPollingService:
    def __init__(self, *, scan_seconds: int = 30) -> None:
        self.scan_seconds = max(10, scan_seconds)
        self._stop = Event(); self._lock = Lock(); self._thread: Thread | None = None
        self._last_results: dict[str, Any] = {}

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive(): return
            self._stop.clear()
            self._thread = Thread(target=self._loop, name="aion-support-poller", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive(): thread.join(timeout=5)

    def status(self) -> dict[str, Any]:
        return {"running": bool(self._thread and self._thread.is_alive()),
                "scan_seconds": self.scan_seconds, "last_results": self._last_results}

    def tick(self) -> dict[str, Any]:
        service = SupportCaseService(); results = {}
        root = AIONBusinessPaths.BUSINESS_CONTAINERS
        if not root.exists(): return results
        for workspace in sorted(path for path in root.iterdir() if path.is_dir()):
            if not (workspace / "support/case_management/polling.json").exists(): continue
            try: results[workspace.name] = service.poll_sources(workspace.name)
            except Exception as exc: results[workspace.name] = {"ok": False, "error": str(exc)[:500]}
        self._last_results = results
        return results

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.tick(); self._stop.wait(self.scan_seconds)


SUPPORT_POLLER = SupportPollingService()
