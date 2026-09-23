from __future__ import annotations

import json
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict


class PrivateServiceState:
    """Private, process-independent credentials for household-facing surfaces."""

    def __init__(self, base_dir: str | Path) -> None:
        self.path = Path(base_dir) / "private_service_state.json"

    def load(self) -> Dict[str, str]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state: Dict[str, str] = {}
        if self.path.exists():
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    state = {str(key): str(item) for key, item in value.items() if isinstance(item, str)}
            except (OSError, ValueError, json.JSONDecodeError):
                state = {}
        changed = False
        defaults = {
            "companion_token": lambda: secrets.token_urlsafe(24),
            "companion_csrf": lambda: secrets.token_urlsafe(24),
            "companion_pair_code": lambda: f"{secrets.randbelow(1_000_000):06d}",
            "canvas_token": lambda: secrets.token_urlsafe(24),
            "education_token": lambda: secrets.token_urlsafe(24),
        }
        for key, factory in defaults.items():
            if not state.get(key):
                state[key] = factory()
                changed = True
        if changed or not self.path.exists():
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
            os.chmod(temporary, 0o600)
            temporary.replace(self.path)
        else:
            os.chmod(self.path, 0o600)
        return state


class ConnectionHealthMonitor:
    """Small local watchdog that recovers changing TV addresses without taking over playback."""

    def __init__(
        self,
        check: Callable[[], Dict[str, Any]],
        *,
        interval_seconds: float = 12.0,
    ) -> None:
        self.check = check
        self.interval_seconds = max(2.0, interval_seconds)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._state: Dict[str, Any] = {
            "status": "starting",
            "message": "Checking the television connection…",
            "last_checked_at": None,
            "last_connected_at": None,
            "host": None,
            "consecutive_failures": 0,
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pilot-connection-health", daemon=True)
        self._thread.start()

    def retry_now(self) -> Dict[str, Any]:
        # A button press should provide a fresh result immediately.  Waking the
        # background loop alone made the dashboard appear unresponsive for up
        # to one polling interval.
        self._refresh_once()
        self._wake.set()
        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._refresh_once()
            self._wake.wait(self.interval_seconds)
            self._wake.clear()

    def _refresh_once(self) -> None:
        try:
            result = dict(self.check())
            connected = bool(result.get("connected"))
            with self._lock:
                failures = 0 if connected else int(self._state.get("consecutive_failures", 0)) + 1
                self._state.update(
                    {
                        "status": "connected" if connected else "recovering",
                        "message": (
                            "TV connected and ready."
                            if connected
                            else "Pilot is looking for the TV. Keep it on and on the same Wi-Fi."
                        ),
                        "host": result.get("host"),
                        "last_checked_at": time.time(),
                        "last_connected_at": time.time() if connected else self._state.get("last_connected_at"),
                        "consecutive_failures": failures,
                        "detail": str(result.get("detail") or ""),
                    }
                )
        except Exception as exc:
            with self._lock:
                self._state.update(
                    {
                        "status": "recovering",
                        "message": "Pilot is reconnecting to the TV automatically.",
                        "last_checked_at": time.time(),
                        "consecutive_failures": int(self._state.get("consecutive_failures", 0)) + 1,
                        "detail": f"{type(exc).__name__}: {exc}"[:240],
                    }
                )

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=3)
