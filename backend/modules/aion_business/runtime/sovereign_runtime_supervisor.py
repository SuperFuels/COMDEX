from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict

from backend.modules.aion_fabric.canonical import canonical_bytes, utc_now_iso
from backend.modules.pilot_unified.ownership import MotherOwnershipAuthority


SUPERVISOR_VERSION = "aion.sovereign_supervisor.v1"


class SovereignRuntimeSupervisor:
    """Bounded health/recovery state machine; the OS-specific service invokes it."""

    _lock = threading.RLock()

    def __init__(self, state_path: str | Path, *, max_attempts: int = 3, cooldown_seconds: int = 10) -> None:
        if not 1 <= max_attempts <= 10:
            raise ValueError("Recovery attempts must be between 1 and 10")
        if not 1 <= cooldown_seconds <= 3600:
            raise ValueError("Recovery cooldown must be between 1 and 3600 seconds")
        self.state_path = Path(state_path).resolve()
        self.max_attempts = max_attempts
        self.cooldown_seconds = cooldown_seconds

    def initialize(self) -> Dict[str, Any]:
        with self._lock:
            if not self.state_path.exists():
                self._write({
                    "schema_version": SUPERVISOR_VERSION,
                    "status": "starting",
                    "consecutive_failures": 0,
                    "recovery_attempts": 0,
                    "last_checked_at": None,
                    "last_recovered_at": None,
                    "next_recovery_at": None,
                })
            return self.status()

    def status(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": SUPERVISOR_VERSION, "status": "not_initialized"}
        return self._read()

    def check_and_recover(
        self,
        *,
        health_check: Callable[[], bool],
        restart: Callable[[], bool],
        now: datetime | None = None,
    ) -> Dict[str, Any]:
        instant = now or datetime.now(timezone.utc)
        with self._lock:
            state = self._read() if self.state_path.exists() else self.initialize()
            state["last_checked_at"] = instant.isoformat()
            if self._safe_call(health_check):
                state.update({"status": "healthy", "consecutive_failures": 0, "recovery_attempts": 0, "next_recovery_at": None})
                self._write(state)
                return {**state, "action": "none"}

            state["consecutive_failures"] = int(state.get("consecutive_failures") or 0) + 1
            allowed_at = self._parse_time(state.get("next_recovery_at"))
            if allowed_at and instant < allowed_at:
                state["status"] = "cooldown"
                self._write(state)
                return {**state, "action": "wait"}
            if int(state.get("recovery_attempts") or 0) >= self.max_attempts:
                state["status"] = "manual_recovery_required"
                self._write(state)
                return {**state, "action": "stop"}

            state["recovery_attempts"] = int(state.get("recovery_attempts") or 0) + 1
            restarted = self._safe_call(restart)
            recovered = restarted and self._safe_call(health_check)
            if recovered:
                state.update({
                    "status": "recovered",
                    "consecutive_failures": 0,
                    "recovery_attempts": 0,
                    "last_recovered_at": instant.isoformat(),
                    "next_recovery_at": None,
                })
                action = "restarted"
            else:
                state["status"] = "recovering" if state["recovery_attempts"] < self.max_attempts else "manual_recovery_required"
                state["next_recovery_at"] = (instant + timedelta(seconds=self.cooldown_seconds)).isoformat()
                action = "restart_failed"
            self._write(state)
            return {**state, "action": action}

    def verify_update(
        self,
        *,
        authority: MotherOwnershipAuthority,
        version: str,
        health_check: Callable[[], bool],
        restart_previous: Callable[[], bool],
    ) -> Dict[str, Any]:
        healthy = self._safe_call(health_check)
        update = authority.verify_or_rollback_update(version=version, health_check=lambda: healthy)
        previous_restarted = False
        if not healthy:
            previous_restarted = self._safe_call(restart_previous)
        return {
            **update,
            "previous_runtime_restart_attempted": not healthy,
            "previous_runtime_restarted": previous_restarted,
            "manual_recovery_required": not healthy and not previous_restarted,
        }

    @staticmethod
    def _safe_call(callback: Callable[[], bool]) -> bool:
        try:
            return bool(callback())
        except Exception:
            return False

    @staticmethod
    def _parse_time(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def _read(self) -> Dict[str, Any]:
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("schema_version") != SUPERVISOR_VERSION:
            raise RuntimeError("Runtime supervisor state has an unsupported format")
        return state

    def _write(self, state: Dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = utc_now_iso()
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_bytes(canonical_bytes(state))
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, self.state_path)
