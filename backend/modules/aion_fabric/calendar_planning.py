from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .private_identity import ProductionPrivateIdentity


class GovernedCalendarPlanning:
    """Private calendar proposals, conflict checks and verified modifications."""

    _lock = threading.RLock()
    ACTIONS = {"create", "reschedule", "cancel"}

    def __init__(self, runtime_dir: str | Path, *, identities: ProductionPrivateIdentity | None = None) -> None:
        self.root = Path(runtime_dir) / "calendar_planning"; self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)
        self.identities = identities or ProductionPrivateIdentity(runtime_dir)
        self.adapters: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {"schema_version": "pilot.calendar-planning.v2", "events": [], "proposals": [], "receipts": [], "idempotency": []}

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists(): return self._initial()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8")); return value if isinstance(value, dict) else self._initial()
        except (OSError, json.JSONDecodeError): return self._initial()

    def _write(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso(); temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state)); os.chmod(temporary, 0o600); os.replace(temporary, self.path)

    def _profile(self, persona_id: str) -> Dict[str, Any]:
        profile = next((item for item in self.identities.snapshot().get("profiles", []) if item.get("persona_id") == persona_id and item.get("status") == "active"), None)
        if profile is None: raise PermissionError("A production private identity is required")
        return dict(profile)

    @staticmethod
    def _time(value: str) -> datetime:
        try: parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc: raise ValueError("Calendar times must be ISO-8601") from exc
        if parsed.tzinfo is None: raise ValueError("Calendar times require a time zone")
        return parsed

    def register_adapter(self, action: str, adapter: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        if action not in self.ACTIONS: raise ValueError("Unsupported calendar action adapter")
        self.adapters[action] = adapter

    def ingest_busy_event(
        self, *, persona_id: str, provider_event_id: str, start: str, end: str,
        title: str = "", location: str = "", source: str = "google_calendar",
    ) -> Dict[str, Any]:
        self._profile(persona_id); begins, finishes = self._time(start), self._time(end)
        if finishes <= begins: raise ValueError("Calendar end must be after start")
        event = {
            "event_id": f"calendar_event_{uuid4().hex}", "persona_id": persona_id,
            "provider_event_id": str(provider_event_id)[:240], "start": begins.isoformat(), "end": finishes.isoformat(),
            "title": " ".join(str(title).split())[:240], "location": " ".join(str(location).split())[:300],
            "source": str(source)[:80], "status": "confirmed", "provider_payload_retained": False,
            "ingested_at": utc_now_iso(),
        }
        with self._lock:
            state = self._read(); state["events"] = [item for item in state["events"] if not (item.get("persona_id") == persona_id and item.get("provider_event_id") == provider_event_id)] + [event]; self._write(state)
        return dict(event)

    def _conflicts(self, state: Dict[str, Any], persona_id: str, start: datetime, end: datetime, exclude_provider_id: str = "") -> list[Dict[str, Any]]:
        conflicts = []
        for event in state.get("events", []):
            if event.get("persona_id") != persona_id or event.get("status") == "cancelled" or event.get("provider_event_id") == exclude_provider_id: continue
            if self._time(str(event["start"])) < end and self._time(str(event["end"])) > start:
                conflicts.append({"event_id": event["event_id"], "start": event["start"], "end": event["end"]})
        return conflicts

    def prepare(
        self, *, persona_id: str, action: str, title: str, start: str = "", end: str = "",
        provider_event_id: str = "", location: str = "", travel_minutes: int = 0,
        reminder_minutes: int = 0, calendar_id: str = "primary", time_zone: str = "Europe/Madrid",
        attendees: list[str] | None = None, description: str = "", notify_attendees: bool = False,
        idempotency_key: str = "",
    ) -> Dict[str, Any]:
        self._profile(persona_id); action = str(action).lower()
        if action not in self.ACTIONS: raise ValueError("Unsupported calendar action")
        if action in {"reschedule", "cancel"} and not provider_event_id: raise ValueError("An exact provider event is required")
        clean_title = " ".join(str(title).split())[:240]
        if action != "cancel" and not clean_title: raise ValueError("Calendar event title is required")
        if action != "cancel":
            begins, finishes = self._time(start), self._time(end)
            if finishes <= begins: raise ValueError("Calendar end must be after start")
        else: begins = finishes = datetime.now(timezone.utc)
        travel_minutes = max(0, min(int(travel_minutes), 1440)); reminder_minutes = max(0, min(int(reminder_minutes), 10080))
        clean_attendees = []
        for address in list(attendees or [])[:20]:
            address = str(address).strip().lower()
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", address):
                raise ValueError("Calendar attendees require valid email addresses")
            if address not in clean_attendees: clean_attendees.append(address)
        clean_time_zone = str(time_zone or "Europe/Madrid")[:80]
        try: ZoneInfo(clean_time_zone)
        except ZoneInfoNotFoundError as exc: raise ValueError("Calendar time zone is invalid") from exc
        scope = {
            "title": clean_title, "start": start, "end": end,
            "provider_event_id": str(provider_event_id)[:240], "location": " ".join(str(location).split())[:300],
            "travel_minutes": travel_minutes, "reminder_minutes": reminder_minutes,
            "calendar_id": str(calendar_id or "primary")[:240], "time_zone": clean_time_zone,
            "attendees": clean_attendees, "description": str(description).strip()[:1500],
            "notify_attendees": bool(notify_attendees),
        }
        request_hash = canonical_hash({"persona_id": persona_id, "action": action, "scope": scope})
        state = self._read()
        if idempotency_key:
            previous = next((item for item in state.get("idempotency", []) if item.get("persona_id") == persona_id and item.get("key") == idempotency_key), None)
            if previous:
                if previous.get("request_hash") != request_hash: raise PermissionError("Calendar retry changed its exact scope")
                existing = next((item for item in state.get("proposals", []) if item.get("proposal_id") == previous.get("proposal_id")), None)
                if existing: return dict(existing)
        conflicts = [] if action == "cancel" else self._conflicts(state, persona_id, begins - timedelta(minutes=travel_minutes), finishes, provider_event_id)
        proposal = {
            "proposal_id": f"calendar_proposal_{uuid4().hex}", "persona_id": persona_id,
            "action": action, "scope": scope, "scope_hash": canonical_hash(scope),
            "conflict_count": len(conflicts), "conflicts": conflicts, "private_event_titles_disclosed": False,
            "status": "awaiting_conflict_confirmation" if conflicts else "awaiting_private_approval",
            "external_effect": False, "created_at": utc_now_iso(),
        }
        with self._lock:
            state = self._read()
            if idempotency_key:
                previous = next((item for item in state.get("idempotency", []) if item.get("persona_id") == persona_id and item.get("key") == idempotency_key), None)
                if previous:
                    if previous.get("request_hash") != request_hash: raise PermissionError("Calendar retry changed its exact scope")
                    existing = next((item for item in state.get("proposals", []) if item.get("proposal_id") == previous.get("proposal_id")), None)
                    if existing: return dict(existing)
            state["proposals"] = list(state["proposals"])[-199:] + [proposal]
            if idempotency_key:
                state["idempotency"] = list(state.get("idempotency", []))[-399:] + [{"persona_id": persona_id, "key": idempotency_key[:160], "request_hash": request_hash, "proposal_id": proposal["proposal_id"]}]
            self._write(state)
        return dict(proposal)

    def decide(self, *, proposal_id: str, persona_id: str, scope_hash: str, approved: bool, accept_conflicts: bool = False) -> Dict[str, Any]:
        with self._lock:
            state = self._read(); proposal = next((item for item in state["proposals"] if item.get("proposal_id") == proposal_id), None)
            if proposal is None: raise KeyError("Calendar proposal was not found")
            if proposal.get("persona_id") != persona_id: raise PermissionError("Only the calendar owner can approve this change")
            if proposal.get("scope_hash") != scope_hash: raise PermissionError("The calendar scope changed; review it again")
            if proposal.get("conflict_count") and not accept_conflicts: raise PermissionError("Confirm the detected time conflict explicitly")
            if proposal.get("status") not in {"awaiting_conflict_confirmation", "awaiting_private_approval"}: return dict(proposal)
            proposal["status"] = "approved_pending_adapter" if approved else "rejected"; proposal["approved_by_persona"] = persona_id if approved else None; proposal["decided_at"] = utc_now_iso(); self._write(state); return dict(proposal)

    def execute(self, *, proposal_id: str, persona_id: str) -> Dict[str, Any]:
        with self._lock:
            state = self._read(); proposal = next((item for item in state["proposals"] if item.get("proposal_id") == proposal_id), None)
            if proposal is None: raise KeyError("Calendar proposal was not found")
            if proposal.get("persona_id") != persona_id or proposal.get("approved_by_persona") != persona_id: raise PermissionError("Exact private approval is required")
            if proposal.get("status") == "executed": return dict(next(item for item in state["receipts"] if item.get("proposal_id") == proposal_id))
            if proposal.get("status") != "approved_pending_adapter": raise PermissionError("This calendar action is not approved")
            adapter = self.adapters.get(str(proposal.get("action")))
            if adapter is None: raise RuntimeError("An authorized persona-specific calendar adapter is not connected")
            proposal["status"] = "executing"; proposal["attempt_id"] = f"calendar_attempt_{uuid4().hex}"; self._write(state)
            try: result = adapter(dict(proposal))
            except Exception:
                proposal["status"] = "execution_unknown_reconcile_required"; self._write(state); raise
            if not isinstance(result, dict) or not result.get("verified") or not result.get("provider_event_id"):
                proposal["status"] = "execution_unknown_reconcile_required"; self._write(state); raise RuntimeError("The calendar provider did not verify the modification")
            receipt = {
                "receipt_id": f"calendar_receipt_{uuid4().hex}", "proposal_id": proposal_id,
                "persona_id": persona_id, "action": proposal["action"], "provider_event_id": str(result["provider_event_id"])[:240],
                "provider_status": str(result.get("provider_status") or "verified")[:80], "verified": True,
                "normalized_scope_hash": proposal["scope_hash"], "provider_payload_retained": False, "created_at": utc_now_iso(),
            }
            proposal["status"] = "executed"; proposal["external_effect"] = True; state["receipts"] = list(state["receipts"])[-399:] + [receipt]
            event = next((item for item in state["events"] if item.get("persona_id") == persona_id and item.get("provider_event_id") == receipt["provider_event_id"]), None)
            if proposal["action"] == "cancel" and event: event["status"] = "cancelled"
            elif proposal["action"] in {"create", "reschedule"}:
                scope = proposal["scope"]
                values = {"persona_id": persona_id, "provider_event_id": receipt["provider_event_id"], "start": scope["start"], "end": scope["end"], "title": scope["title"], "location": scope["location"], "calendar_id": scope.get("calendar_id", "primary"), "time_zone": scope.get("time_zone", "Europe/Madrid"), "attendees": list(scope.get("attendees") or []), "status": "confirmed", "source": "verified_adapter", "provider_payload_retained": False}
                if event: event.update(values)
                else: state["events"].append({"event_id": f"calendar_event_{uuid4().hex}", **values})
            self._write(state); return dict(receipt)

    def availability(self, *, persona_id: str, start: str, end: str, slot_minutes: int = 30) -> Dict[str, Any]:
        self._profile(persona_id); begins, finishes = self._time(start), self._time(end)
        slot_minutes = max(15, min(int(slot_minutes), 240)); state = self._read(); free = []
        cursor = begins
        while cursor + timedelta(minutes=slot_minutes) <= finishes and len(free) < 96:
            end_cursor = cursor + timedelta(minutes=slot_minutes)
            if not self._conflicts(state, persona_id, cursor, end_cursor): free.append({"start": cursor.isoformat(), "end": end_cursor.isoformat()})
            cursor = end_cursor
        return {"persona_id": persona_id, "free_slots": free, "private_event_details_disclosed": False, "source": "normalized_private_calendar", "generated_at": utc_now_iso()}

    def snapshot(self, *, persona_id: str) -> Dict[str, Any]:
        self._profile(persona_id); state = self._read()
        return {key: [dict(item) for item in state.get(key, []) if item.get("persona_id") == persona_id] for key in ("events", "proposals", "receipts")}
