from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class PrivateEntertainmentPersonalization:
    """Persona-isolated watchlists, deterministic recommendations, reminders and service health."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "entertainment_personalization"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"watchlists": [], "history": [], "reminders": [], "service_health": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"watchlists": [], "history": [], "reminders": [], "service_health": {}}
        except (OSError, json.JSONDecodeError):
            return {"watchlists": [], "history": [], "reminders": [], "service_health": {}}

    def _write(self, state: Dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def add_watchlist(self, *, persona_id: str, title: str, provider: str = "", visibility: str = "private") -> Dict[str, Any]:
        clean_visibility = str(visibility).strip().lower()
        if clean_visibility not in {"private", "household_shared"}:
            raise ValueError("Watchlist visibility must be private or household_shared")
        clean_title = " ".join(str(title).split())[:180]
        if not clean_title:
            raise ValueError("A title is required")
        state = self._read()
        state["watchlists"] = [item for item in state.get("watchlists", []) if not (item.get("persona_id") == persona_id and str(item.get("title") or "").casefold() == clean_title.casefold())]
        record = {
            "watchlist_id": f"watchlist_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "persona_id": str(persona_id)[:100],
            "title": clean_title,
            "provider": str(provider)[:100],
            "visibility": clean_visibility,
            "shared_by_explicit_choice": clean_visibility == "household_shared",
        }
        record["record_hash"] = canonical_hash(record)
        state["watchlists"].append(record)
        state["watchlists"] = state["watchlists"][-300:]
        self._write(state)
        return record

    def remember(self, *, persona_id: str, title: str, outcome: str, share_with_household: bool = False) -> Dict[str, Any]:
        if outcome not in {"watched", "liked", "disliked", "avoid"}:
            raise ValueError("Unsupported entertainment outcome")
        clean_title = " ".join(str(title).split())[:180]
        state = self._read()
        state["history"] = [item for item in state.get("history", []) if not (item.get("persona_id") == persona_id and str(item.get("title") or "").casefold() == clean_title.casefold())]
        record = {"history_id": f"history_{uuid4().hex}", "recorded_at": utc_now_iso(), "persona_id": str(persona_id)[:100], "title": clean_title, "outcome": outcome, "household_shared": bool(share_with_household)}
        record["record_hash"] = canonical_hash(record)
        state["history"].append(record)
        state["history"] = state["history"][-500:]
        self._write(state)
        return record

    def prepare_history(self, *, title: str, outcome: str) -> Dict[str, Any]:
        if outcome not in {"watched", "liked", "disliked", "avoid"}:
            raise ValueError("Unsupported entertainment outcome")
        clean_title = " ".join(str(title).split())[:180]
        if not clean_title:
            raise ValueError("A title is required")
        state = self._read()
        pending = {
            "pending_id": f"entertainment_memory_{uuid4().hex}", "created_at": utc_now_iso(),
            "title": clean_title, "outcome": outcome, "status": "awaiting_private_claim", "persona_id": None,
        }
        pending["record_hash"] = canonical_hash(pending)
        state.setdefault("pending_history", []).append(pending)
        state["pending_history"] = state["pending_history"][-100:]
        self._write(state)
        return pending

    def claim_history(self, pending_id: str, *, persona_id: str, share_with_household: bool = False) -> Dict[str, Any]:
        state = self._read()
        pending = next((item for item in state.get("pending_history", []) if item.get("pending_id") == pending_id and item.get("status") == "awaiting_private_claim"), None)
        if not pending:
            raise KeyError("No pending entertainment memory matches that identifier")
        pending["status"] = "claimed"
        pending["persona_id"] = str(persona_id)[:100]
        pending["claimed_at"] = utc_now_iso()
        self._write(state)
        return self.remember(persona_id=persona_id, title=str(pending["title"]), outcome=str(pending["outcome"]), share_with_household=share_with_household)

    def recommend(
        self,
        *,
        persona_id: str | None,
        candidates: list[Dict[str, Any]],
        mood: str = "",
        maximum_minutes: int | None = None,
        presence: str = "alone",
        hour: int | None = None,
    ) -> Dict[str, Any]:
        state = self._read()
        hour_value = datetime.now(timezone.utc).hour if hour is None else max(0, min(int(hour), 23))
        histories = []
        for item in state.get("history", []):
            if persona_id and item.get("persona_id") == persona_id:
                histories.append(item)
            elif presence != "alone" and item.get("household_shared"):
                histories.append(item)
        rejected = {str(item.get("title") or "").casefold() for item in histories if item.get("outcome") in {"watched", "disliked", "avoid"}}
        liked = {str(item.get("title") or "").casefold() for item in histories if item.get("outcome") == "liked"}
        scored = []
        for item in candidates[:100]:
            if not isinstance(item, dict) or not item.get("title") or str(item.get("title")).casefold() in rejected:
                continue
            runtime = item.get("minutes")
            if maximum_minutes and isinstance(runtime, int) and runtime > maximum_minutes:
                continue
            score = 0
            reasons = []
            moods = {str(value).casefold() for value in list(item.get("moods") or [])}
            if mood and mood.casefold() in moods:
                score += 3
                reasons.append(f"matches {mood}")
            if hour_value >= 21 and isinstance(runtime, int) and runtime <= 120:
                score += 1
                reasons.append("fits a late-evening duration")
            if presence in {"family", "children"} and item.get("family_safe") is True:
                score += 2
                reasons.append("labelled family-safe by the supplied catalogue")
            if str(item.get("title") or "").casefold() in liked:
                score += 1
            scored.append({**item, "pilot_score": score, "reasons": reasons, "entitlement": "unknown_until_authenticated_provider_confirms"})
        ranked = sorted(scored, key=lambda item: (-int(item.get("pilot_score") or 0), str(item.get("title") or "")))[:5]
        return {
            "recommendation_id": f"recommendation_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "persona_id": persona_id,
            "criteria": {"mood": mood, "maximum_minutes": maximum_minutes, "presence": presence, "hour": hour_value},
            "items": ranked,
            "private_history_used": bool(persona_id and histories),
            "unconsented_other_person_history_used": False,
            "paid_ai_used": False,
        }

    def add_episode_reminder(self, *, persona_id: str, programme: Dict[str, Any], notify_at: str) -> Dict[str, Any]:
        if not programme.get("provider") or not programme.get("provider_content_id") or not programme.get("episode_title"):
            raise ValueError("Episode reminders require exact provider metadata")
        when = datetime.fromisoformat(str(notify_at).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when <= datetime.now(timezone.utc):
            raise ValueError("Episode reminder must be in the future")
        state = self._read()
        record = {
            "reminder_id": f"episode_reminder_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "persona_id": str(persona_id)[:100],
            "programme": {"provider": str(programme["provider"])[:100], "provider_content_id": str(programme["provider_content_id"])[:160], "series_title": str(programme.get("series_title") or "")[:180], "episode_title": str(programme["episode_title"])[:180]},
            "notify_at": when.isoformat(timespec="seconds"),
            "status": "scheduled_local_private_inbox",
            "external_push_scheduled": False,
        }
        record["record_hash"] = canonical_hash(record)
        state["reminders"].append(record)
        state["reminders"] = state["reminders"][-300:]
        self._write(state)
        return record

    def record_service_health(self, *, provider: str, status: str, source: str, authenticated: bool = False, detail: str = "") -> Dict[str, Any]:
        clean_status = str(status).strip().lower()
        if clean_status not in {"available", "degraded", "outage", "sign_in_required", "unknown"}:
            raise ValueError("Unsupported provider health status")
        state = self._read()
        record = {
            "provider": str(provider)[:100], "status": clean_status, "source": str(source)[:160],
            "authenticated": bool(authenticated), "detail": " ".join(str(detail).split())[:300], "observed_at": utc_now_iso(),
            "credentials_inspected": False,
            "recovery": "Open the official provider sign-in surface for owner action." if clean_status == "sign_in_required" else "Retry later or choose another verified provider." if clean_status in {"degraded", "outage"} else "",
        }
        record["record_hash"] = canonical_hash(record)
        state.setdefault("service_health", {})[record["provider"]] = record
        self._write(state)
        return record

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        state = self._read()
        watchlists = [dict(item) for item in state.get("watchlists", []) if (persona_id and item.get("persona_id") == persona_id) or item.get("visibility") == "household_shared"]
        history = [dict(item) for item in state.get("history", []) if persona_id and item.get("persona_id") == persona_id]
        reminders = [dict(item) for item in state.get("reminders", []) if persona_id and item.get("persona_id") == persona_id]
        pending = [dict(item) for item in state.get("pending_history", []) if item.get("status") == "awaiting_private_claim"]
        return {"watchlists": watchlists[-50:], "private_history": history[-50:], "reminders": reminders[-50:], "service_health": dict(state.get("service_health") or {}), "pending_history": pending[-10:]}
