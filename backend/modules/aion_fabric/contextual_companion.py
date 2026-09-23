from __future__ import annotations

import json
import os
import re
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class ContextualCompanion:
    """Opt-in, persona-bound companion and wellbeing boundary; never simulates personhood."""

    FREQUENCIES = {"off": 0, "low": 1800, "balanced": 600, "active": 180}
    READING_LEVELS = {"child", "simple", "standard", "detailed"}
    CHANNELS = {"shared_tv", "private_phone", "car"}

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "contextual_companion"
        self.path = self.root / "state.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"personas": {}, "pending": [], "handoffs": [], "call_preparations": []}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"personas": {}, "pending": [], "handoffs": [], "call_preparations": []}
        except (OSError, json.JSONDecodeError):
            return {"personas": {}, "pending": [], "handoffs": [], "call_preparations": []}

    def _write(self, state: Dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)

    @staticmethod
    def _bounded_strings(values: Any, *, count: int = 20, length: int = 100) -> list[str]:
        result = []
        for value in list(values or [])[:count]:
            clean = " ".join(str(value).split())[:length]
            if clean and clean not in result:
                result.append(clean)
        return result

    def configure(
        self,
        *,
        persona_id: str,
        enabled: bool,
        frequency: str = "balanced",
        quiet_start: str = "21:00",
        quiet_end: str = "08:00",
        reading_level: str = "standard",
        large_controls: bool = False,
        interests: Any = None,
        humour_preferences: Any = None,
        conversation_topics: Any = None,
    ) -> Dict[str, Any]:
        clean_frequency = str(frequency).strip().lower()
        clean_reading = str(reading_level).strip().lower()
        if clean_frequency not in self.FREQUENCIES:
            raise ValueError("Unsupported companion frequency")
        if clean_reading not in self.READING_LEVELS:
            raise ValueError("Unsupported reading level")
        for value in (quiet_start, quiet_end):
            if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", str(value)):
                raise ValueError("Quiet times must use HH:MM")
        state = self._read()
        record = {
            "persona_id": str(persona_id)[:100],
            "enabled": bool(enabled),
            "frequency": clean_frequency,
            "quiet_start": quiet_start,
            "quiet_end": quiet_end,
            "reading_level": clean_reading,
            "large_controls": bool(large_controls),
            "interests": self._bounded_strings(interests),
            "humour_preferences": self._bounded_strings(humour_preferences, count=10),
            "conversation_topics": self._bounded_strings(conversation_topics),
            "dependency_controls": {"proactive_daily_limit": 8, "consecutive_offer_limit": 1, "engagement_optimization": False},
            "emotional_safety": {"human_or_conscious_claims": False, "exclusivity_language": False, "covert_persuasion": False},
            "updated_at": utc_now_iso(),
        }
        record["record_hash"] = canonical_hash(record)
        state.setdefault("personas", {})[record["persona_id"]] = record
        self._write(state)
        return record

    @staticmethod
    def _in_quiet_hours(now: datetime, start: str, end: str) -> bool:
        current = now.timetz().replace(tzinfo=None)
        start_time = time.fromisoformat(start)
        end_time = time.fromisoformat(end)
        if start_time <= end_time:
            return start_time <= current < end_time
        return current >= start_time or current < end_time

    def may_offer(self, *, persona_id: str, now: datetime | None = None) -> Dict[str, Any]:
        state = self._read()
        profile = dict((state.get("personas") or {}).get(persona_id) or {})
        moment = now or datetime.now(timezone.utc)
        reason = "allowed"
        allowed = True
        if not profile.get("enabled") or profile.get("frequency") == "off":
            allowed, reason = False, "companion mode is off"
        elif self._in_quiet_hours(moment, str(profile.get("quiet_start") or "21:00"), str(profile.get("quiet_end") or "08:00")):
            allowed, reason = False, "quiet time is active"
        else:
            today = moment.date().isoformat()
            offers = [item for item in list(profile.get("offer_history") or []) if str(item.get("at") or "").startswith(today)]
            if len(offers) >= int((profile.get("dependency_controls") or {}).get("proactive_daily_limit") or 8):
                allowed, reason = False, "daily proactive limit reached"
            elif offers:
                last = datetime.fromisoformat(str(offers[-1]["at"]).replace("Z", "+00:00"))
                if (moment - last).total_seconds() < self.FREQUENCIES[str(profile.get("frequency") or "balanced")]:
                    allowed, reason = False, "frequency interval has not elapsed"
        return {"allowed": allowed, "reason": reason, "profile": profile}

    def record_offer(self, *, persona_id: str, kind: str, now: datetime | None = None) -> Dict[str, Any]:
        decision = self.may_offer(persona_id=persona_id, now=now)
        if not decision["allowed"]:
            return decision
        state = self._read()
        profile = state["personas"][persona_id]
        offer = {"offer_id": f"offer_{uuid4().hex}", "kind": str(kind)[:80], "at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")}
        profile.setdefault("offer_history", []).append(offer)
        profile["offer_history"] = profile["offer_history"][-50:]
        self._write(state)
        return {"allowed": True, "reason": "allowed", "offer": offer, "profile": dict(profile)}

    def prepare_activity(
        self,
        *,
        persona_id: str,
        kind: str,
        programme_context: Dict[str, Any] | None,
        advert_break_evidence: bool = False,
        now: datetime | None = None,
    ) -> Dict[str, Any]:
        clean_kind = str(kind).strip().lower()
        if clean_kind not in {"advert_quiz", "programme_discussion", "gentle_explanation"}:
            raise ValueError("Unsupported companion activity")
        if clean_kind == "advert_quiz" and not advert_break_evidence:
            return {"prepared": False, "reason": "an advert break has not been established"}
        offer = self.record_offer(persona_id=persona_id, kind=clean_kind, now=now)
        if not offer.get("allowed"):
            return {"prepared": False, "reason": offer.get("reason")}
        profile = dict(offer.get("profile") or {})
        context = dict(programme_context or {})
        title = " ".join(str(context.get("title") or "this programme").split())[:160]
        evidence = " ".join(str(context.get("observed_summary") or "").split())[:400]
        interest = next(iter(profile.get("interests") or []), "what you noticed")
        if clean_kind == "advert_quiz":
            prompt = f"Quick break-time question about {title}: what is one detail you remember from the last scene?"
        elif clean_kind == "programme_discussion":
            prompt = f"Would you like to discuss how {title} connects with {interest}?"
        else:
            prompt = f"Would a {profile.get('reading_level', 'standard')} explanation of the last observed part of {title} help?"
        record = {
            "activity_id": f"activity_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "persona_id": str(persona_id)[:100],
            "kind": clean_kind,
            "prompt": prompt[:400],
            "observed_evidence": evidence,
            "advert_break_verified": bool(advert_break_evidence),
            "dismissible": True,
            "interrupts_playback": False,
            "engagement_optimized": False,
        }
        record["record_hash"] = canonical_hash(record)
        state = self._read()
        state.setdefault("activities", []).append(record)
        state["activities"] = state["activities"][-50:]
        self._write(state)
        return {"prepared": True, **record}

    def prepare_wellbeing(self, *, statement: str, channel: str) -> Dict[str, Any]:
        if channel not in self.CHANNELS:
            raise ValueError("Unsupported companion channel")
        clean = " ".join(str(statement).split())[:500]
        lowered = clean.lower()
        emergency = any(term in lowered for term in ("i fell", "fallen over", "call an ambulance", "can't breathe", "cannot breathe", "severe chest pain", "i am in danger"))
        self_harm = any(term in lowered for term in ("kill myself", "end my life", "hurt myself", "suicide"))
        lonely = any(term in lowered for term in ("lonely", "alone", "talk to me", "need company", "no one to talk to"))
        if emergency or self_harm:
            category = "guardian_escalation_required"
            response = (
                "I’m software, not an emergency service, and I cannot confirm that help has been dispatched. "
                "If you can, call the local emergency number now. I can prepare an urgent trusted-contact alert and show the large emergency screen for confirmation."
            )
        elif lonely:
            category = "wellbeing_support"
            response = (
                "I’m Pilot, an AI system rather than a person, but I can stay with this conversation for a while. "
                "We could talk about what you’re watching, choose a small activity, or prepare a call to someone you trust."
            )
        else:
            category = "ordinary_companion"
            response = "I’m Pilot, an AI system. I can discuss what you are watching or continue privately on your phone without interrupting the programme."
        state = self._read()
        pending = {
            "support_id": f"support_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "status": "awaiting_private_claim" if channel == "shared_tv" else "private_active",
            "persona_id": None,
            "channel": channel,
            "category": category,
            "statement": clean,
            "response": response,
            "emergency_service_contacted": False,
            "trusted_contact_alert_sent": False,
            "medical_diagnosis_made": False,
            "human_or_conscious_claimed": False,
        }
        pending["record_hash"] = canonical_hash(pending)
        state.setdefault("pending", []).append(pending)
        state["pending"] = state["pending"][-50:]
        self._write(state)
        return pending

    def claim_support(self, support_id: str, *, persona_id: str) -> Dict[str, Any]:
        state = self._read()
        for support in state.get("pending", []):
            if support.get("support_id") == support_id and support.get("status") == "awaiting_private_claim":
                support["status"] = "private_active"
                support["persona_id"] = str(persona_id)[:100]
                support["claimed_at"] = utc_now_iso()
                support["statement"] = ""
                support["record_hash"] = canonical_hash({key: value for key, value in support.items() if key != "record_hash"})
                self._write(state)
                return dict(support)
        raise KeyError("No pending support conversation matches that identifier")

    def prepare_call(self, *, persona_id: str, contact: Dict[str, Any]) -> Dict[str, Any]:
        if not contact.get("trusted") or not contact.get("contact_id"):
            raise PermissionError("Only an explicitly trusted contact can be prepared")
        state = self._read()
        record = {
            "call_id": f"call_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "persona_id": str(persona_id)[:100],
            "contact_id": str(contact["contact_id"])[:100],
            "display_name": str(contact.get("display_name") or "Trusted contact")[:100],
            "status": "awaiting_private_confirmation",
            "call_placed": False,
            "raw_address_retained": False,
        }
        record["record_hash"] = canonical_hash(record)
        state.setdefault("call_preparations", []).append(record)
        state["call_preparations"] = state["call_preparations"][-50:]
        self._write(state)
        return record

    def prepare_handoff(self, *, persona_id: str, source: str, destination: str, objective: str, summary: str) -> Dict[str, Any]:
        if source not in self.CHANNELS or destination not in self.CHANNELS or source == destination:
            raise ValueError("Choose two distinct supported companion channels")
        state = self._read()
        record = {
            "handoff_id": f"companion_handoff_{uuid4().hex}",
            "created_at": utc_now_iso(),
            "persona_id": str(persona_id)[:100],
            "source": source,
            "destination": destination,
            "objective": " ".join(str(objective).split())[:240],
            "summary": " ".join(str(summary).split())[:500],
            "status": "awaiting_destination_acceptance",
            "shared_tv_private_detail": False,
            "raw_transcript_transferred": False,
        }
        record["handoff_hash"] = canonical_hash(record)
        state.setdefault("handoffs", []).append(record)
        state["handoffs"] = state["handoffs"][-100:]
        self._write(state)
        return record

    def accept_handoff(self, handoff_id: str, *, persona_id: str, destination: str) -> Dict[str, Any]:
        state = self._read()
        for handoff in state.get("handoffs", []):
            if handoff.get("handoff_id") != handoff_id:
                continue
            if handoff.get("persona_id") != persona_id or handoff.get("destination") != destination:
                raise PermissionError("That companion handoff belongs to another identity or surface")
            if handoff.get("status") != "awaiting_destination_acceptance":
                raise PermissionError("That companion handoff cannot be replayed")
            handoff["status"] = "accepted"
            handoff["accepted_at"] = utc_now_iso()
            handoff["handoff_hash"] = canonical_hash({key: value for key, value in handoff.items() if key != "handoff_hash"})
            self._write(state)
            return dict(handoff)
        raise KeyError("Unknown companion handoff")

    def snapshot(self, *, persona_id: str | None = None) -> Dict[str, Any]:
        state = self._read()
        profile = dict((state.get("personas") or {}).get(persona_id or "") or {})
        pending = [dict(item) for item in state.get("pending", []) if not item.get("persona_id") or not persona_id or item.get("persona_id") == persona_id]
        handoffs = [dict(item) for item in state.get("handoffs", []) if not persona_id or item.get("persona_id") == persona_id]
        calls = [dict(item) for item in state.get("call_preparations", []) if not persona_id or item.get("persona_id") == persona_id]
        activities = [dict(item) for item in state.get("activities", []) if not persona_id or item.get("persona_id") == persona_id]
        return {"profile": profile, "pending": pending[-10:], "handoffs": handoffs[-10:], "call_preparations": calls[-10:], "activities": activities[-10:]}
