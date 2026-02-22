from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SkillTelemetryEvent:
    telemetry_id: str
    ts_unix: float
    skill_run_id: str
    skill_id: str
    ok: bool
    latency_ms: int
    session_id: Optional[str] = None
    turn_id: Optional[str] = None
    safety_class: Optional[str] = None
    status: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "telemetry_id": self.telemetry_id,
            "ts_unix": self.ts_unix,
            "skill_run_id": self.skill_run_id,
            "skill_id": self.skill_id,
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "safety_class": self.safety_class,
            "status": self.status,
            "error_code": self.error_code,
            "metadata": dict(self.metadata or {}),
        }


class SkillTelemetryStore:
    """
    In-memory telemetry store (Phase C Sprint 1).
    Replace/augment later with persistent store.
    """

    def __init__(self, max_events: int = 5000) -> None:
        self.max_events = int(max_events)
        self._events: List[SkillTelemetryEvent] = []

    def record(self, event: SkillTelemetryEvent) -> SkillTelemetryEvent:
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events :]
        return event

    def emit(
        self,
        *,
        skill_run_id: str,
        skill_id: str,
        ok: bool,
        latency_ms: int,
        session_id: Optional[str] = None,
        turn_id: Optional[str] = None,
        safety_class: Optional[str] = None,
        status: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SkillTelemetryEvent:
        ev = SkillTelemetryEvent(
            telemetry_id=f"telemetry_{uuid.uuid4().hex[:12]}",
            ts_unix=time.time(),
            skill_run_id=skill_run_id,
            skill_id=skill_id,
            ok=bool(ok),
            latency_ms=int(latency_ms),
            session_id=session_id,
            turn_id=turn_id,
            safety_class=safety_class,
            status=status,
            error_code=error_code,
            metadata=dict(metadata or {}),
        )
        return self.record(ev)

    def list_events(self, skill_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self._events
        if skill_id:
            rows = [e for e in rows if e.skill_id == skill_id]
        return [e.to_dict() for e in rows[-int(limit) :]]

    def summary(self) -> Dict[str, Any]:
        total = len(self._events)
        ok_count = sum(1 for e in self._events if e.ok)
        fail_count = total - ok_count
        avg_latency = int(sum(e.latency_ms for e in self._events) / total) if total else 0
        by_skill: Dict[str, Dict[str, Any]] = {}
        for e in self._events:
            bucket = by_skill.setdefault(e.skill_id, {"count": 0, "ok": 0, "fail": 0})
            bucket["count"] += 1
            if e.ok:
                bucket["ok"] += 1
            else:
                bucket["fail"] += 1
        return {
            "total_events": total,
            "ok_count": ok_count,
            "fail_count": fail_count,
            "avg_latency_ms": avg_latency,
            "by_skill": by_skill,
        }


_GLOBAL_TELEMETRY: Optional[SkillTelemetryStore] = None


def get_global_skill_telemetry() -> SkillTelemetryStore:
    global _GLOBAL_TELEMETRY
    if _GLOBAL_TELEMETRY is None:
        _GLOBAL_TELEMETRY = SkillTelemetryStore()
    return _GLOBAL_TELEMETRY