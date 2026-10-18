from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class ExplicitObserverSessions:
    """Short-lived owner-started frame leases; tokens and frames are never persisted."""

    _lock = threading.RLock()
    PROFILES = {
        "detail": {"interval_seconds": 3, "max_frame_dimension": 1280, "jpeg_quality": 0.78},
        "balanced": {"interval_seconds": 5, "max_frame_dimension": 1280, "jpeg_quality": 0.72},
        "battery_saver": {"interval_seconds": 15, "max_frame_dimension": 960, "jpeg_quality": 0.60},
    }

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "perception" / "observer_session.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"active": False}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"active": False}
        except (OSError, json.JSONDecodeError):
            return {"active": False}

    def _save(self, state: Dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.path)

    def start(self, *, persona_id: str, duration_seconds: int = 600, interval_seconds: int = 5, capture_profile: str = "balanced") -> Dict[str, Any]:
        duration = max(30, min(int(duration_seconds), 600))
        profile_name = str(capture_profile or "balanced").strip().lower()
        if profile_name not in self.PROFILES:
            raise ValueError("Unknown Observer capture profile")
        profile = dict(self.PROFILES[profile_name])
        interval = max(3, min(int(interval_seconds or profile["interval_seconds"]), 30))
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        state = {
            "schema_version": "pilot.explicit-observer.v1",
            "session_id": f"observer_{uuid4().hex}",
            "active": True,
            "persona_id": persona_id,
            "started_at": now.isoformat(timespec="seconds"),
            "expires_at": (now + timedelta(seconds=duration)).isoformat(timespec="seconds"),
            "interval_seconds": interval,
            "requested_interval_seconds": interval,
            "effective_interval_seconds": interval,
            "capture_profile": profile_name,
            "max_frame_dimension": profile["max_frame_dimension"],
            "jpeg_quality": profile["jpeg_quality"],
            "last_frame_at": None,
            "frames_accepted": 0,
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "raw_frames_retained": False,
            "requires_visible_owner_start": True,
            "persistent_camera_indicator_required": True,
            "countdown_visible": True,
            "paused": False,
            "pause_reason": None,
            "resource_state": {
                "battery_band": "unknown",
                "charging": None,
                "thermal_state": "nominal",
                "visibility": "visible",
            },
        }
        with self._lock:
            self._save(state)
        return {**self.snapshot(), "frame_token": token}

    def accept_frame(self, token: str | None) -> Dict[str, Any] | None:
        if not token:
            return None
        with self._lock:
            state = self._load()
            now = datetime.now(timezone.utc)
            try:
                expires = datetime.fromisoformat(str(state.get("expires_at")))
            except ValueError as exc:
                raise PermissionError("Observer session is invalid") from exc
            if not state.get("active") or now >= expires:
                state["active"] = False
                self._save(state)
                raise PermissionError("Observer session has expired")
            if state.get("paused"):
                raise PermissionError(f"Observer session is paused: {state.get('pause_reason') or 'owner policy'}")
            if not secrets.compare_digest(hashlib.sha256(token.encode()).hexdigest(), str(state.get("token_hash") or "")):
                raise PermissionError("Observer frame token is invalid")
            last = state.get("last_frame_at")
            if last:
                elapsed = (now - datetime.fromisoformat(str(last))).total_seconds()
                if elapsed < int(state.get("effective_interval_seconds") or state.get("interval_seconds") or 5):
                    raise ValueError("Observer frame arrived before the permitted interval")
            state["last_frame_at"] = now.isoformat(timespec="seconds")
            state["frames_accepted"] = int(state.get("frames_accepted") or 0) + 1
            self._save(state)
            return self.snapshot()

    def configure(self, *, persona_id: str, capture_profile: str, interval_seconds: int | None = None) -> Dict[str, Any]:
        profile_name = str(capture_profile or "").strip().lower()
        if profile_name not in self.PROFILES:
            raise ValueError("Unknown Observer capture profile")
        profile = dict(self.PROFILES[profile_name])
        requested = max(3, min(int(interval_seconds or profile["interval_seconds"]), 30))
        with self._lock:
            state = self._load()
            self._require_persona(state, persona_id)
            state.update({
                "capture_profile": profile_name,
                "requested_interval_seconds": requested,
                "effective_interval_seconds": requested,
                "interval_seconds": requested,
                "max_frame_dimension": profile["max_frame_dimension"],
                "jpeg_quality": profile["jpeg_quality"],
            })
            self._apply_resource_policy(state)
            self._save(state)
            return self.snapshot()

    @staticmethod
    def _require_persona(state: Dict[str, Any], persona_id: str) -> None:
        if state.get("persona_id") not in {None, persona_id}:
            raise PermissionError("Observer session belongs to another private identity")

    @staticmethod
    def _battery_band(level: float | None) -> str:
        if level is None:
            return "unknown"
        if level < 0.10:
            return "critical"
        if level < 0.20:
            return "low"
        if level < 0.50:
            return "moderate"
        return "healthy"

    def _apply_resource_policy(self, state: Dict[str, Any]) -> None:
        resources = dict(state.get("resource_state") or {})
        requested = int(state.get("requested_interval_seconds") or 5)
        effective = requested
        automatic_reason = None
        if resources.get("visibility") != "visible":
            automatic_reason = "resource_page_not_visible"
        elif resources.get("thermal_state") == "critical":
            automatic_reason = "resource_thermal_critical"
        elif resources.get("battery_band") == "critical" and resources.get("charging") is False:
            automatic_reason = "resource_battery_critical"
        elif resources.get("thermal_state") == "serious":
            effective = max(effective, 30)
        elif resources.get("thermal_state") == "fair":
            effective = max(effective, 10)
        if resources.get("battery_band") == "low" and resources.get("charging") is False:
            effective = max(effective, 15)
        state["effective_interval_seconds"] = min(effective, 30)
        state["interval_seconds"] = state["effective_interval_seconds"]
        if str(state.get("pause_reason") or "").startswith("resource_"):
            state["paused"] = bool(automatic_reason)
            state["pause_reason"] = automatic_reason
        elif automatic_reason:
            state["paused"] = True
            state["pause_reason"] = automatic_reason

    def report_client_state(
        self,
        *,
        persona_id: str,
        battery_level: float | None = None,
        charging: bool | None = None,
        thermal_state: str = "nominal",
        visibility: str = "visible",
    ) -> Dict[str, Any]:
        thermal = str(thermal_state or "nominal").strip().lower()
        visible = str(visibility or "visible").strip().lower()
        if thermal not in {"nominal", "fair", "serious", "critical"}:
            raise ValueError("Invalid thermal state")
        if visible not in {"visible", "hidden", "suspended"}:
            raise ValueError("Invalid Observer visibility")
        level = None if battery_level is None else max(0.0, min(float(battery_level), 1.0))
        with self._lock:
            state = self._load()
            self._require_persona(state, persona_id)
            state["resource_state"] = {
                "battery_band": self._battery_band(level),
                "charging": bool(charging) if charging is not None else None,
                "thermal_state": thermal,
                "visibility": visible,
            }
            self._apply_resource_policy(state)
            self._save(state)
            return self.snapshot()

    def pause(self, *, persona_id: str, reason: str = "owner_paused") -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            self._require_persona(state, persona_id)
            state.update({"paused": True, "pause_reason": str(reason or "owner_paused")[:80]})
            self._save(state)
            return self.snapshot()

    def resume(self, *, persona_id: str) -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            self._require_persona(state, persona_id)
            state.update({"paused": False, "pause_reason": None})
            self._apply_resource_policy(state)
            self._save(state)
            if state.get("paused"):
                raise PermissionError("Observer cannot resume until the resource condition clears")
            return self.snapshot()

    def stop(self, *, persona_id: str) -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            self._require_persona(state, persona_id)
            receipt = {
                "session_id": state.get("session_id"),
                "frames_accepted": int(state.get("frames_accepted") or 0),
                "capture_profile": state.get("capture_profile"),
                "raw_frames_retained": False,
                "stopped_at": utc_now_iso(),
            }
            receipt["receipt_hash"] = canonical_hash(receipt)
            state.update({
                "active": False,
                "paused": False,
                "pause_reason": None,
                "stopped_at": receipt["stopped_at"],
                "token_hash": None,
                "session_receipt": receipt,
            })
            self._save(state)
            return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        state = self._load()
        try:
            expired = datetime.now(timezone.utc) >= datetime.fromisoformat(str(state.get("expires_at")))
        except ValueError:
            expired = True
        return {
            key: value for key, value in {**state, "active": bool(state.get("active")) and not expired}.items()
            if key != "token_hash"
        }
