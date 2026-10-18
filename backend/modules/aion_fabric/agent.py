from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, utc_now_iso


class AionTVAgent:
    """Persistent, fail-closed task planning for the room-scale AION surface.

    Plans are data, not executable model output. Only the small action classes in
    this module can be emitted, and consequential service work always stops at a
    private approval gate until a separately authorized adapter completes it.
    """

    _lock = threading.RLock()
    _service_routes = {
        "calendar": ("schedule", "calendar", "remind", "reminder"),
        "communication": ("email", "message", "text", "contact", "call"),
        "shopping": ("buy", "order", "purchase", "basket", "checkout"),
        "booking": ("book", "reserve", "reservation", "appointment"),
    }

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "agent" / "tv_tasks.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "aion.tv.agent.v1",
            "active_task_id": None,
            "tasks": [],
            "updated_at": utc_now_iso(),
        }

    def _load(self) -> Dict[str, Any]:
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

    @classmethod
    def classify(cls, request: str) -> str:
        normalized = re.sub(r"[^a-z0-9 ]+", " ", request.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        for route, words in cls._service_routes.items():
            if any(re.search(rf"\b{re.escape(word)}\b", normalized) for word in words):
                return route
        if any(
            re.search(rf"\b{term}\b", normalized)
            for term in ("find", "compare", "research", "recommend", "best", "where", "who", "what", "how")
        ):
            return "research"
        return "conversation"

    def create_plan(
        self,
        request: str,
        *,
        perception: Dict[str, Any] | None = None,
        companion_url: str | None = None,
    ) -> Dict[str, Any]:
        request = " ".join(request.split()).strip()[:500]
        if len(request) < 2:
            raise ValueError("The agent request is too short")
        route = self.classify(request)
        consequential = route in self._service_routes
        task_id = f"tv_task_{uuid4().hex}"
        approval_id = f"approval_{uuid4().hex}" if consequential else None
        steps = [
            {
                "step_id": "1",
                "kind": "observe_context",
                "label": "Observe the current governed TV state",
                "status": "verified" if perception else "unavailable",
                "evidence": (perception or {}).get("summary", "No fresh TV observation was available"),
            },
            {
                "step_id": "2",
                "kind": "research" if route != "conversation" else "reason",
                "label": "Research and prepare the requested outcome" if route != "conversation" else "Reason about the request",
                "status": "ready",
                "evidence": "Bounded mother-node intelligence; no external commitment",
            },
        ]
        if consequential:
            steps.extend([
                {
                    "step_id": "3",
                    "kind": "private_approval",
                    "label": "Confirm the proposed real-world action privately",
                    "status": "waiting",
                    "evidence": "Money, messages, bookings and calendar changes require owner approval",
                },
                {
                    "step_id": "4",
                    "kind": f"service_{route}",
                    "label": f"Complete the approved {route} action",
                    "status": "blocked",
                    "evidence": "No service adapter may run before approval",
                },
            ])
        task = {
            "task_id": task_id,
            "request": request,
            "route": route,
            "status": "waiting_for_approval" if consequential else "planned",
            "risk": "medium" if consequential else "low",
            "approval": (
                {
                    "approval_id": approval_id,
                    "state": "pending",
                    "scope": f"Authorize only this prepared {route} action",
                    "companion_url": companion_url,
                    "decided_at": None,
                }
                if consequential
                else None
            ),
            "perception": perception or {},
            "steps": steps,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        with self._lock:
            state = self._load()
            tasks = list(state.get("tasks") or [])[-24:]
            tasks.append(task)
            state["tasks"] = tasks
            state["active_task_id"] = task_id
            self._save(state)
        return task

    def decide(self, approval_id: str, *, approved: bool) -> Dict[str, Any]:
        if not re.fullmatch(r"approval_[0-9a-f]{32}", approval_id):
            raise ValueError("Invalid approval identifier")
        with self._lock:
            state = self._load()
            task = next(
                (
                    item for item in state.get("tasks", [])
                    if isinstance(item, dict)
                    and isinstance(item.get("approval"), dict)
                    and item["approval"].get("approval_id") == approval_id
                ),
                None,
            )
            if task is None:
                raise KeyError("Approval request was not found")
            approval = task["approval"]
            if approval.get("state") != "pending":
                return dict(task)
            approval["state"] = "approved" if approved else "rejected"
            approval["decided_at"] = utc_now_iso()
            task["status"] = "approved_pending_adapter" if approved else "cancelled"
            task["updated_at"] = utc_now_iso()
            for step in task.get("steps", []):
                if step.get("kind") == "private_approval":
                    step["status"] = "verified" if approved else "failed"
                    step["evidence"] = "Owner approved on private companion" if approved else "Owner rejected on private companion"
                elif step.get("kind", "").startswith("service_"):
                    step["status"] = "ready" if approved else "skipped"
                    step["evidence"] = (
                        "Approved; awaiting a separately authorized service adapter"
                        if approved else "Cancelled before any external action"
                    )
            self._save(state)
            return dict(task)

    def mark_prepared(self, task_id: str, *, evidence: str, result: Dict[str, Any] | None = None) -> Dict[str, Any]:
        with self._lock:
            state = self._load()
            task = next((item for item in state.get("tasks", []) if item.get("task_id") == task_id), None)
            if task is None:
                raise KeyError("Agent task was not found")
            for step in task.get("steps", []):
                if step.get("kind") in {"research", "reason"}:
                    step["status"] = "verified"
                    step["evidence"] = evidence[:300]
            task["prepared_result"] = result or {}
            task["updated_at"] = utc_now_iso()
            if not task.get("approval"):
                task["status"] = "completed"
            self._save(state)
            return dict(task)

    def cancel_active(self, *, reason: str = "owner_cancelled") -> Dict[str, Any] | None:
        with self._lock:
            state = self._load()
            active_id = state.get("active_task_id")
            task = next((item for item in state.get("tasks", []) if item.get("task_id") == active_id), None)
            if task is None or task.get("status") in {"completed", "cancelled", "executed"}:
                return None
            task["status"] = "cancelled"
            task["cancelled_at"] = utc_now_iso()
            task["cancellation_reason"] = str(reason)[:100]
            approval = task.get("approval")
            if isinstance(approval, dict) and approval.get("state") == "pending":
                approval["state"] = "cancelled"
                approval["decided_at"] = utc_now_iso()
            for step in task.get("steps", []):
                if step.get("status") in {"ready", "waiting", "pending"}:
                    step["status"] = "skipped"
                    step["evidence"] = "Cancelled by the owner before further execution"
            state["active_task_id"] = None
            self._save(state)
            return dict(task)

    def latest(self) -> Dict[str, Any] | None:
        state = self._load()
        active_id = state.get("active_task_id")
        tasks = list(state.get("tasks") or [])
        return next((dict(item) for item in reversed(tasks) if item.get("task_id") == active_id), None)

    def snapshot(self) -> Dict[str, Any]:
        state = self._load()
        tasks = list(state.get("tasks") or [])
        pending = [
            item for item in tasks
            if isinstance(item.get("approval"), dict) and item["approval"].get("state") == "pending"
        ]
        return {
            "active_task": self.latest(),
            "recent_tasks": [dict(item) for item in tasks[-5:]],
            "pending_approvals": len(pending),
            "updated_at": state.get("updated_at"),
            "policy": {
                "model_output_executes_directly": False,
                "private_approval_required_for": ["booking", "shopping", "communication", "calendar"],
                "approved_without_adapter_executes": False,
            },
        }
