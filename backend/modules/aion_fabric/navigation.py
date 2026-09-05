from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, utc_now_iso


class PhoneVerifiedNavigation:
    """Pairs a governed TV action with the next explicit phone observation."""

    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "perception" / "navigation_verification.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "aion.phone.navigation-verification.v1", "pending": None, "last_result": None}

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _save(self, state: Dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.path)

    def begin(self, action: str, *, expected: str, before_image_sha256: str | None) -> Dict[str, Any]:
        pending = {
            "verification_id": f"nav_verify_{uuid4().hex}",
            "action": action[:80],
            "expected": expected,
            "before_image_sha256": before_image_sha256,
            "status": "waiting_for_owner_capture",
            "started_at": utc_now_iso(),
        }
        with self._lock:
            state = self._load()
            state["pending"] = pending
            self._save(state)
        return pending

    def verify(self, perception: Dict[str, Any]) -> Dict[str, Any] | None:
        with self._lock:
            state = self._load()
            pending = state.get("pending")
            if not isinstance(pending, dict):
                return None
            inference = dict(perception.get("inference") or {})
            expected = str(pending.get("expected") or "")
            surface = str(inference.get("surface") or "unknown")
            view = str(inference.get("view") or "")
            before_hash = str(pending.get("before_image_sha256") or "")
            after_hash = str(perception.get("image_sha256") or "")
            changed = bool(before_hash and after_hash and before_hash != after_hash)
            if expected.startswith("surface:"):
                target = expected.split(":", 1)[1]
                success = surface == target
                evidence = f"phone vision observed surface={surface}; expected={target}"
            elif expected == "profile_selected":
                success = surface == "netflix" and view != "profile_chooser"
                evidence = f"phone vision observed surface={surface}, view={view}"
            elif expected == "google_consent_dismissed":
                success = not (surface == "web_browser" and view == "google_consent")
                evidence = f"phone vision observed surface={surface}, view={view}"
            else:
                success = changed
                evidence = "owner capture changed after the remote action" if changed else "owner capture did not establish a screen change"
            result = {
                **pending,
                "status": "verified" if success else "not_verified",
                "success": success,
                "evidence": evidence,
                "after_image_sha256": after_hash,
                "completed_at": utc_now_iso(),
            }
            state["last_result"] = result
            state["pending"] = None
            self._save(state)
            return result

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            return {"pending": state.get("pending"), "last_result": state.get("last_result")}
