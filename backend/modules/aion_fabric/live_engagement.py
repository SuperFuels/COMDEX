from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class HouseholdLiveEngagement:
    """Private, opt-in event watches and family predictions without betting or silent delivery."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "live_engagement"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"watches": [], "predictions": [], "commentary_preferences": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"watches": [], "predictions": [], "commentary_preferences": {}}
        except (OSError, json.JSONDecodeError):
            return {"watches": [], "predictions": [], "commentary_preferences": {}}

    def _write(self, value: Dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(value))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def _event_identity(live_event: Dict[str, Any] | None) -> Dict[str, Any]:
        event = dict((live_event or {}).get("authenticated_provider_fact") or {})
        if not event.get("provider_match_id"):
            raise ValueError("An authenticated current match is required")
        return {
            "provider_match_id": str(event["provider_match_id"])[:100],
            "home": str(event.get("home") or "")[:160],
            "away": str(event.get("away") or "")[:160],
            "competition": str(event.get("competition") or "")[:160],
        }

    def prepare_close_watch(self, *, live_event: Dict[str, Any] | None, margin: int = 1) -> Dict[str, Any]:
        event = self._event_identity(live_event)
        threshold = max(0, min(int(margin), 10))
        state = self._read()
        watch = {
            "watch_id": f"watch_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "status": "awaiting_private_claim",
            "persona_id": None,
            "event": event,
            "threshold": {"kind": "absolute_score_margin_at_most", "value": threshold},
            "delivery": "private_phone_only",
            "last_condition": False,
            "last_provider_update": "",
        }
        watch["record_hash"] = canonical_hash(watch)
        state.setdefault("watches", []).append(watch)
        state["watches"] = state["watches"][-100:]
        self._write(state)
        return watch

    def claim_watch(self, watch_id: str, *, persona_id: str) -> Dict[str, Any]:
        state = self._read()
        for watch in state.get("watches", []):
            if watch.get("watch_id") == watch_id and watch.get("status") == "awaiting_private_claim":
                watch["status"] = "active"
                watch["persona_id"] = str(persona_id)[:100]
                watch["activated_at"] = utc_now_iso()
                watch["record_hash"] = canonical_hash({key: value for key, value in watch.items() if key != "record_hash"})
                self._write(state)
                return dict(watch)
        raise KeyError("No pending live-event watch matches that identifier")

    def evaluate(self, live_event: Dict[str, Any] | None) -> list[Dict[str, Any]]:
        event = dict((live_event or {}).get("authenticated_provider_fact") or {})
        provider = dict((live_event or {}).get("provider") or {})
        if not provider.get("authenticated") or not event.get("provider_match_id"):
            return []
        home_score, away_score = event.get("home_score"), event.get("away_score")
        if not isinstance(home_score, int) or not isinstance(away_score, int):
            return []
        state = self._read()
        notifications = []
        changed = False
        for watch in state.get("watches", []):
            if watch.get("status") != "active" or (watch.get("event") or {}).get("provider_match_id") != str(event.get("provider_match_id")):
                continue
            condition = abs(home_score - away_score) <= int((watch.get("threshold") or {}).get("value") or 0)
            previous = bool(watch.get("last_condition"))
            watch["last_condition"] = condition
            watch["last_provider_update"] = str(event.get("last_updated") or "")[:80]
            changed = True
            if condition and not previous:
                notification = {
                    "notification_id": f"notice_{uuid4().hex}",
                    "watch_id": watch["watch_id"],
                    "persona_id": watch["persona_id"],
                    "created_at": utc_now_iso(),
                    "message": f"{event.get('home')} {home_score}, {event.get('away')} {away_score} is now within your selected threshold.",
                    "delivery": "private_phone_inbox",
                    "external_push_sent": False,
                }
                notification["record_hash"] = canonical_hash(notification)
                notifications.append(notification)
        if changed:
            state.setdefault("notifications", []).extend(notifications)
            state["notifications"] = state["notifications"][-100:]
            self._write(state)
        return notifications

    def add_prediction(self, *, live_event: Dict[str, Any] | None, persona_id: str, prediction: str) -> Dict[str, Any]:
        event = self._event_identity(live_event)
        clean = " ".join(str(prediction).split())[:160]
        if not clean:
            raise ValueError("A prediction is required")
        state = self._read()
        record = {
            "prediction_id": f"prediction_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "persona_id": str(persona_id)[:100],
            "event": event,
            "prediction": clean,
            "money_or_betting_enabled": False,
            "household_visibility": "opt_in",
        }
        record["record_hash"] = canonical_hash(record)
        state.setdefault("predictions", []).append(record)
        state["predictions"] = state["predictions"][-200:]
        self._write(state)
        return record

    def set_commentary(self, *, persona_id: str, style: str) -> Dict[str, Any]:
        clean = str(style).strip().lower()
        allowed = {"standard", "child_friendly", "tactical", "quiet", "accessibility"}
        if clean not in allowed:
            raise ValueError("Unsupported commentary style")
        state = self._read()
        state.setdefault("commentary_preferences", {})[str(persona_id)[:100]] = clean
        self._write(state)
        return {"persona_id": str(persona_id)[:100], "style": clean, "audio_replaced": False, "local_explanations_only": True}

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        state = self._read()
        watches = [dict(item) for item in state.get("watches", []) if not item.get("persona_id") or not persona_id or item.get("persona_id") == persona_id]
        predictions = [dict(item) for item in state.get("predictions", []) if not persona_id or item.get("persona_id") == persona_id]
        notifications = [dict(item) for item in state.get("notifications", []) if not persona_id or item.get("persona_id") == persona_id]
        return {
            "pending": next((item for item in reversed(watches) if item.get("status") == "awaiting_private_claim"), None),
            "watches": watches[-20:],
            "predictions": predictions[-20:],
            "notifications": notifications[-20:],
            "commentary_style": (state.get("commentary_preferences") or {}).get(persona_id or "", "standard"),
        }
