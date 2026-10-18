from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, utc_now_iso


class TVAutopilot:
    """Persistent belief state and explainable plans for the governed TV node."""

    _lock = threading.RLock()

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "autopilot" / "tv_state.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "aion.tv.autopilot.v1",
            "belief": {
                "surface": "unknown",
                "view": None,
                "confidence": 0.0,
                "evidence": "No governed TV action observed yet",
                "observed_at": None,
                "pixel_vision": False,
            },
            "active_plan": None,
            "last_plan": None,
            "recent_events": [],
            "navigation_memory": {},
            "updated_at": utc_now_iso(),
        }

    def load(self) -> Dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return self._initial()
            try:
                value = json.loads(self.path.read_text(encoding="utf-8"))
                return value if isinstance(value, dict) else self._initial()
            except (OSError, json.JSONDecodeError):
                return self._initial()

    def _save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.path)

    def observe(self, *, surface: str, confidence: float, evidence: str, view: str | None = None) -> None:
        if surface not in {"unknown", "aion_canvas", "netflix", "youtube", "games", "hdmi", "media_app", "web_browser"}:
            raise ValueError("Unknown TV surface belief")
        with self._lock:
            state = self.load()
            state["belief"] = {
                "surface": surface,
                "view": view,
                "confidence": max(0.0, min(1.0, float(confidence))),
                "evidence": evidence[:240],
                "observed_at": utc_now_iso(),
                "pixel_vision": False,
            }
            self._event(state, "belief_updated", {"surface": surface, "view": view, "confidence": confidence})
            self._save(state)

    def start_plan(self, *, name: str, goal: str, steps: list[Dict[str, Any]]) -> str:
        plan_id = f"tv_plan_{uuid4().hex}"
        with self._lock:
            state = self.load()
            state["active_plan"] = {
                "plan_id": plan_id,
                "name": name,
                "goal": goal,
                "status": "running",
                "steps": [
                    {
                        "step_id": str(index + 1),
                        "name": str(step["name"]),
                        "status": "pending",
                        "verification": str(step.get("verification") or "receipt"),
                        "evidence": None,
                    }
                    for index, step in enumerate(steps)
                ],
                "started_at": utc_now_iso(),
                "completed_at": None,
            }
            self._event(state, "plan_started", {"plan_id": plan_id, "name": name})
            self._save(state)
        return plan_id

    def mark_step(self, plan_id: str, index: int, *, status: str, evidence: str) -> None:
        if status not in {"running", "verified", "failed", "skipped"}:
            raise ValueError("Unknown plan step status")
        with self._lock:
            state = self.load()
            plan = state.get("active_plan")
            if not plan or plan.get("plan_id") != plan_id:
                return
            steps = plan.get("steps", [])
            if 0 <= index < len(steps):
                steps[index]["status"] = status
                steps[index]["evidence"] = evidence[:300]
            self._save(state)

    def finish_plan(self, plan_id: str, *, status: str, summary: str) -> None:
        if status not in {"completed", "failed", "cancelled"}:
            raise ValueError("Unknown plan result")
        with self._lock:
            state = self.load()
            plan = state.get("active_plan")
            if not plan or plan.get("plan_id") != plan_id:
                return
            plan["status"] = status
            plan["summary"] = summary[:400]
            plan["completed_at"] = utc_now_iso()
            state["last_plan"] = plan
            state["active_plan"] = None
            self._event(state, "plan_finished", {"plan_id": plan_id, "status": status, "summary": summary[:180]})
            self._save(state)

    def cancel_active(self, *, summary: str = "Cancelled by the owner") -> Dict[str, Any] | None:
        with self._lock:
            state = self.load()
            plan = state.get("active_plan")
            if not isinstance(plan, dict):
                return None
            for step in plan.get("steps", []):
                if step.get("status") in {"pending", "running"}:
                    step["status"] = "skipped"
                    step["evidence"] = summary[:300]
            plan["status"] = "cancelled"
            plan["summary"] = summary[:400]
            plan["completed_at"] = utc_now_iso()
            state["last_plan"] = plan
            state["active_plan"] = None
            self._event(state, "plan_finished", {"plan_id": plan.get("plan_id"), "status": "cancelled"})
            self._save(state)
            return dict(plan)

    def record_navigation_attempt(
        self,
        *,
        action: str,
        expected: str,
        observed: str,
        success: bool,
    ) -> None:
        key = re.sub(r"[^a-z0-9_.-]+", "_", action.lower())[:80]
        with self._lock:
            state = self.load()
            memory = dict(state.get("navigation_memory") or {})
            entry = dict(memory.get(key) or {"successes": 0, "failures": 0})
            field = "successes" if success else "failures"
            entry[field] = int(entry.get(field, 0)) + 1
            entry.update({
                "expected": expected[:160],
                "last_observed": observed[:160],
                "last_success": bool(success),
                "updated_at": utc_now_iso(),
            })
            memory[key] = entry
            state["navigation_memory"] = dict(list(memory.items())[-40:])
            self._event(state, "navigation_verified" if success else "navigation_failed", {
                "action": action[:80], "expected": expected[:120], "observed": observed[:120]
            })
            self._save(state)

    @staticmethod
    def _event(state: Dict[str, Any], kind: str, payload: Dict[str, Any]) -> None:
        events = list(state.get("recent_events", []))[-19:]
        events.append({"kind": kind, "payload": payload, "at": utc_now_iso()})
        state["recent_events"] = events

    def snapshot(self) -> Dict[str, Any]:
        state = self.load()
        return {
            "belief": dict(state.get("belief") or {}),
            "active_plan": state.get("active_plan"),
            "last_plan": state.get("last_plan"),
            "recent_events": list(state.get("recent_events") or [])[-8:],
            "navigation_memory": dict(state.get("navigation_memory") or {}),
            "updated_at": state.get("updated_at"),
        }
