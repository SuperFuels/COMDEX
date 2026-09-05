from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from .canonical import canonical_bytes, utc_now_iso


class ConversationMemory:
    """Persistent, channel-separated conversational task context.

    Shared-TV state never contains the text of private-phone turns. The memory
    stores compact user-authored turns and task constraints, not microphone
    audio or model chain-of-thought.
    """

    _lock = threading.RLock()
    _correction_patterns = (
        r"^(?:make|keep|change) it\b",
        r"^(?:not|instead|actually|prefer|avoid|exclude|include)\b",
        r"^(?:the|that|this) (?:first|second|third|fourth|fifth|one|option|result|hotel|film|show|product)\b",
        r"^(?:open|choose|use|book|buy) (?:the|that|this|it)\b",
    )

    def __init__(self, runtime_dir: str | Path) -> None:
        self.path = Path(runtime_dir) / "conversation" / "memory.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _initial() -> Dict[str, Any]:
        return {
            "schema_version": "aion.conversation.v1",
            "conversation_id": f"conversation_{uuid4().hex}",
            "active_objective": None,
            "active_task_id": None,
            "constraints": [],
            "turns": [],
            "interrupted_tasks": [],
            "updated_at": utc_now_iso(),
        }

    def _load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._initial()
        try:
            state = json.loads(self.path.read_text(encoding="utf-8"))
            return state if isinstance(state, dict) else self._initial()
        except (OSError, json.JSONDecodeError):
            return self._initial()

    def _save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now_iso()
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(state))
        os.replace(temporary, self.path)

    @staticmethod
    def _clean(text: str, limit: int = 500) -> str:
        return " ".join(str(text).split()).strip()[:limit]

    @classmethod
    def is_contextual_follow_up(cls, text: str) -> bool:
        normalized = cls._clean(text).lower()
        return any(re.search(pattern, normalized) for pattern in cls._correction_patterns)

    def prepare_request(self, text: str, *, explicit_refinement: bool = False) -> Dict[str, Any]:
        clean = self._clean(text)
        if len(clean) < 2:
            raise ValueError("The conversational request is too short")
        with self._lock:
            state = self._load()
            objective = self._clean(state.get("active_objective") or "")
            had_objective = bool(objective)
            constraints = [self._clean(item, 200) for item in state.get("constraints", []) if self._clean(item, 200)]
            refinement = explicit_refinement or (bool(objective) and self.is_contextual_follow_up(clean))
            if refinement and objective:
                if clean.lower() not in {item.lower() for item in constraints}:
                    constraints.append(clean)
                constraints = constraints[-8:]
            else:
                if objective and objective.lower() != clean.lower():
                    interrupted = list(state.get("interrupted_tasks") or [])[-7:]
                    interrupted.append({"objective": objective, "task_id": state.get("active_task_id"), "interrupted_at": utc_now_iso()})
                    state["interrupted_tasks"] = interrupted
                objective = clean
                constraints = []
            state["active_objective"] = objective
            state["constraints"] = constraints
            self._save(state)
            composed = objective
            if constraints:
                composed += ". Current user constraints and corrections: " + "; ".join(constraints)
            return {
                "objective": objective,
                "constraints": constraints,
                "composed_request": composed,
                "is_refinement": refinement and had_objective,
                "conversation_id": state["conversation_id"],
            }

    def bind_task(self, task_id: str) -> None:
        with self._lock:
            state = self._load()
            state["active_task_id"] = self._clean(task_id, 100)
            self._save(state)

    def pause_active(self) -> Dict[str, Any] | None:
        with self._lock:
            state = self._load()
            objective = self._clean(state.get("active_objective") or "")
            if not objective:
                return None
            interrupted = list(state.get("interrupted_tasks") or [])[-7:]
            interrupted.append({
                "objective": objective,
                "constraints": list(state.get("constraints") or []),
                "task_id": state.get("active_task_id"),
                "interrupted_at": utc_now_iso(),
            })
            state["interrupted_tasks"] = interrupted
            state["active_objective"] = None
            state["active_task_id"] = None
            state["constraints"] = []
            self._save(state)
            return dict(interrupted[-1])

    def resume_previous(self) -> Dict[str, Any] | None:
        with self._lock:
            state = self._load()
            interrupted = list(state.get("interrupted_tasks") or [])
            if not interrupted:
                return None
            previous = dict(interrupted.pop())
            current = self._clean(state.get("active_objective") or "")
            if current:
                interrupted.append({
                    "objective": current,
                    "constraints": list(state.get("constraints") or []),
                    "task_id": state.get("active_task_id"),
                    "interrupted_at": utc_now_iso(),
                })
            state["interrupted_tasks"] = interrupted[-8:]
            state["active_objective"] = self._clean(previous.get("objective") or "")
            state["active_task_id"] = previous.get("task_id")
            state["constraints"] = [self._clean(item, 200) for item in previous.get("constraints", [])]
            self._save(state)
            composed = state["active_objective"]
            if state["constraints"]:
                composed += ". Current user constraints and corrections: " + "; ".join(state["constraints"])
            return {**previous, "composed_request": composed}

    def cancel_active(self) -> Dict[str, Any] | None:
        with self._lock:
            state = self._load()
            objective = self._clean(state.get("active_objective") or "")
            task_id = state.get("active_task_id")
            if not objective and not task_id:
                return None
            cancelled = {
                "objective": objective,
                "task_id": task_id,
                "cancelled_at": utc_now_iso(),
            }
            history = list(state.get("cancelled_tasks") or [])[-19:]
            history.append(cancelled)
            state["cancelled_tasks"] = history
            state["active_objective"] = None
            state["active_task_id"] = None
            state["constraints"] = []
            self._save(state)
            return cancelled

    def record_turn(
        self,
        role: str,
        text: str,
        *,
        channel: str,
        intent: str | None = None,
        task_id: str | None = None,
    ) -> None:
        if role not in {"user", "assistant"} or channel not in {"shared_tv", "private_phone"}:
            raise ValueError("Invalid conversation turn")
        clean = self._clean(text, 600)
        if not clean:
            return
        with self._lock:
            state = self._load()
            turns = list(state.get("turns") or [])[-79:]
            turns.append({
                "turn_id": f"turn_{uuid4().hex}",
                "role": role,
                "text": clean,
                "channel": channel,
                "private": channel == "private_phone",
                "intent": self._clean(intent or "", 80) or None,
                "task_id": self._clean(task_id or "", 100) or None,
                "created_at": utc_now_iso(),
            })
            state["turns"] = turns
            self._save(state)

    def snapshot(self, *, channel: str = "shared_tv") -> Dict[str, Any]:
        state = self._load()
        turns = list(state.get("turns") or [])
        visible = turns if channel == "private_phone" else [item for item in turns if not item.get("private")]
        return {
            "schema_version": state.get("schema_version"),
            "conversation_id": state.get("conversation_id"),
            "active_objective": state.get("active_objective"),
            "active_task_id": state.get("active_task_id"),
            "constraints": list(state.get("constraints") or []),
            "recent_turns": visible[-8:],
            "interrupted_task_count": len(state.get("interrupted_tasks") or []),
            "private_turns_hidden": channel == "shared_tv" and any(item.get("private") for item in turns),
            "updated_at": state.get("updated_at"),
        }
