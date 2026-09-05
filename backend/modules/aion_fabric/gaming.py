from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class GovernedGamingExperience:
    """Local gaming state that never confuses opening a provider with playing a game."""

    PROVIDERS = {
        "geforce_now": {
            "name": "GeForce NOW",
            "origin": "https://play.geforcenow.com/",
            "sign_in_owner": "provider",
        }
    }
    CONTROLLER_PROFILES = {
        "standard_gamepad": {"required": {"axes", "buttons"}, "input_mode": "gamepad"},
        "lg_mobile_gamepad": {"required": {"buttons"}, "input_mode": "tv_mobile_gamepad"},
        "keyboard_mouse": {"required": {"keyboard", "pointer"}, "input_mode": "keyboard_mouse"},
        "tv_remote": {"required": {"directional", "select"}, "input_mode": "navigation_only"},
    }

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "gaming"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"controllers": {}, "sessions": [], "shortcuts": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"controllers": {}, "sessions": [], "shortcuts": []}
        except (OSError, json.JSONDecodeError):
            return {"controllers": {}, "sessions": [], "shortcuts": []}

    def _write(self, state: Dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    def prepare_provider_handoff(
        self, *, provider: str = "geforce_now", query: str = "", persona_id: str = "",
    ) -> Dict[str, Any]:
        if provider not in self.PROVIDERS:
            raise ValueError("Unsupported gaming provider")
        clean_query = " ".join(str(query).split())[:160]
        session = {
            "session_id": f"game_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "provider": provider,
            "provider_name": self.PROVIDERS[provider]["name"],
            "official_origin": self.PROVIDERS[provider]["origin"],
            "query": clean_query,
            "persona_id": str(persona_id)[:100] or None,
            "state": "provider_surface_prepared",
            "provider_surface_open": False,
            "search_verified": False,
            "title_verified": False,
            "stream_ready_verified": False,
            "playing_verified": False,
            "sign_in": {
                "owner": "provider",
                "status": "owner_action_may_be_required",
                "credentials_retained": False,
                "credentials_exposed_to_tv_node": False,
            },
        }
        session["record_hash"] = canonical_hash(session)
        state = self._read()
        state.setdefault("sessions", []).append(session)
        state["sessions"] = state["sessions"][-100:]
        self._write(state)
        return session

    def record_provider_observation(
        self,
        session_id: str,
        *,
        observation: str,
        evidence_source: str,
        title: str = "",
        provider_content_id: str = "",
        signed: bool = False,
    ) -> Dict[str, Any]:
        allowed = {"surface_open", "search_results", "title_selected", "stream_ready", "playing", "sign_in_required"}
        if observation not in allowed:
            raise ValueError("Unsupported gaming observation")
        state = self._read()
        session = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
        if session is None:
            raise KeyError("Unknown gaming session")
        source = " ".join(str(evidence_source).split())[:160]
        if not source:
            raise ValueError("Gaming observations require an evidence source")
        clean_title = " ".join(str(title).split())[:180]
        if observation == "surface_open":
            session["provider_surface_open"] = True
            session["state"] = "provider_surface_observed"
        elif observation == "sign_in_required":
            session["sign_in"]["status"] = "owner_action_required"
            session["state"] = "provider_sign_in_required"
        elif observation == "search_results":
            session["search_verified"] = True
            session["state"] = "search_results_observed"
        elif observation == "title_selected":
            if not clean_title:
                raise ValueError("A verified game title is required")
            session["title"] = clean_title
            session["provider_content_id"] = str(provider_content_id)[:180]
            session["title_verified"] = True
            session["state"] = "title_observed"
        elif observation == "stream_ready":
            if not session.get("title_verified"):
                raise ValueError("Stream readiness cannot precede verified game identity")
            session["stream_ready_verified"] = True
            session["state"] = "stream_ready_observed"
        elif observation == "playing":
            if not signed or not session.get("stream_ready_verified"):
                raise PermissionError("Playing requires signed provider/device evidence after stream readiness")
            session["playing_verified"] = True
            session["state"] = "playing_verified"
        session.setdefault("evidence", []).append({
            "observation": observation,
            "source": source,
            "signed": bool(signed),
            "observed_at": utc_now_iso(),
        })
        session["record_hash"] = canonical_hash({key: value for key, value in session.items() if key != "record_hash"})
        self._write(state)
        return dict(session)

    def observe_controller(
        self,
        *,
        controller_id: str,
        capabilities: list[str],
        input_events_seen: list[str] | None = None,
        name: str = "",
    ) -> Dict[str, Any]:
        clean_id = " ".join(str(controller_id).split())[:120]
        if not clean_id:
            raise ValueError("Controller identifier is required")
        available = {str(item).strip().lower() for item in capabilities if str(item).strip()}
        events = {str(item).strip().lower() for item in (input_events_seen or []) if str(item).strip()}
        candidates = []
        for profile_id, profile in self.CONTROLLER_PROFILES.items():
            required = set(profile["required"])
            if required.issubset(available):
                candidates.append((profile_id, profile))
        profile_id, profile = candidates[0] if candidates else ("unknown", {"input_mode": "unknown"})
        verified = bool(events and profile_id != "unknown")
        record = {
            "controller_id": clean_id,
            "name": " ".join(str(name).split())[:120],
            "capabilities": sorted(available),
            "input_events_seen": sorted(events),
            "profile": profile_id,
            "input_mode": profile["input_mode"],
            "compatibility": "verified" if verified else "advertised_not_field_verified" if profile_id != "unknown" else "unknown",
            "gameplay_ready": verified and profile["input_mode"] != "navigation_only",
            "observed_at": utc_now_iso(),
        }
        record["record_hash"] = canonical_hash(record)
        state = self._read()
        state.setdefault("controllers", {})[clean_id] = record
        self._write(state)
        return record

    def save_shortcut(self, session_id: str, *, persona_id: str) -> Dict[str, Any]:
        state = self._read()
        session = next((item for item in state.get("sessions", []) if item.get("session_id") == session_id), None)
        if not session or not session.get("title_verified"):
            raise PermissionError("A game shortcut requires verified provider title evidence")
        shortcut = {
            "shortcut_id": f"game_shortcut_{uuid4().hex}",
            "persona_id": str(persona_id)[:100],
            "provider": session["provider"],
            "title": session["title"],
            "provider_content_id": str(session.get("provider_content_id") or "")[:180],
            "created_at": utc_now_iso(),
            "launch_authority": "prepare_only_until_provider_and_device_verify",
        }
        shortcut["record_hash"] = canonical_hash(shortcut)
        state["shortcuts"] = [item for item in state.get("shortcuts", []) if not (
            item.get("persona_id") == shortcut["persona_id"] and
            str(item.get("title") or "").casefold() == shortcut["title"].casefold()
        )]
        state["shortcuts"].append(shortcut)
        state["shortcuts"] = state["shortcuts"][-100:]
        self._write(state)
        return shortcut

    def continue_last(self, *, persona_id: str) -> Dict[str, Any]:
        state = self._read()
        shortcuts = [item for item in state.get("shortcuts", []) if item.get("persona_id") == persona_id]
        if not shortcuts:
            raise KeyError("No verified saved game exists for this private identity")
        latest = shortcuts[-1]
        prepared = self.prepare_provider_handoff(
            provider=str(latest["provider"]), query=str(latest["title"]), persona_id=persona_id,
        )
        return {**prepared, "shortcut_id": latest["shortcut_id"], "continuation": "prepared_not_playing"}

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        state = self._read()
        shortcuts = [dict(item) for item in state.get("shortcuts", []) if persona_id and item.get("persona_id") == persona_id]
        sessions = [
            item for item in state.get("sessions", []) if isinstance(item, dict)
            and (persona_id is None or item.get("persona_id") == persona_id)
        ]
        latest = dict(sessions[-1]) if sessions else None
        return {
            "latest_session": latest,
            "controllers": list(dict(state.get("controllers") or {}).values()),
            "shortcuts": shortcuts,
            "claims": {
                "provider_open_is_playing": False,
                "search_is_launch": False,
                "controller_advertisement_is_compatibility": False,
            },
        }
