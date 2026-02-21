from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional


def _truthy(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def _data_root() -> Path:
    root = os.getenv("TESSARIS_DATA_ROOT") or os.getenv("DATA_ROOT") or "data"
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _state_dir() -> Path:
    p = _data_root() / "aion_conversation"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _safe_json_dump(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


@dataclass
class DialogueTurnRecord:
    turn_id: str
    ts: float
    role: str
    text: str
    mode: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogueState:
    session_id: str
    topic: Optional[str] = None
    intent: str = "answer"
    turn_count: int = 0
    unresolved: List[str] = field(default_factory=list)
    commitments: List[str] = field(default_factory=list)
    last_mode: Optional[str] = None
    last_user_text: Optional[str] = None
    last_response_text: Optional[str] = None
    updated_at: float = field(default_factory=lambda: time.time())
    recent_turns: List[DialogueTurnRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["recent_turns"] = [asdict(t) for t in self.recent_turns]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogueState":
        turns = []
        for t in (data.get("recent_turns") or []):
            try:
                turns.append(DialogueTurnRecord(**t))
            except Exception:
                continue
        return cls(
            session_id=str(data.get("session_id") or "default"),
            topic=data.get("topic"),
            intent=str(data.get("intent") or "answer"),
            turn_count=int(data.get("turn_count") or 0),
            unresolved=list(data.get("unresolved") or []),
            commitments=list(data.get("commitments") or []),
            last_mode=data.get("last_mode"),
            last_user_text=data.get("last_user_text"),
            last_response_text=data.get("last_response_text"),
            updated_at=float(data.get("updated_at") or time.time()),
            recent_turns=turns,
        )


class DialogueStateTracker:
    """
    Minimal persistent dialogue state tracker for Phase B Sprint 1.

    Persistence is JSON-file based by session_id so it survives process restarts in dev.
    """

    def __init__(self, max_recent_turns: int = 12) -> None:
        self.max_recent_turns = max(4, int(max_recent_turns))
        self._cache: Dict[str, DialogueState] = {}
        self._persist = _truthy(os.getenv("AION_DIALOGUE_STATE_PERSIST", "1"), True)

    def _path_for(self, session_id: str) -> Path:
        safe = "".join(ch for ch in session_id if ch.isalnum() or ch in {"-", "_", "."}) or "default"
        return _state_dir() / f"{safe}.json"

    def get_or_create(self, session_id: str) -> DialogueState:
        sid = (session_id or "default").strip() or "default"

        if sid in self._cache:
            return self._cache[sid]

        path = self._path_for(sid)
        if self._persist and path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                st = DialogueState.from_dict(data)
                self._cache[sid] = st
                return st
            except Exception:
                pass

        st = DialogueState(session_id=sid)
        self._cache[sid] = st
        return st

    def save(self, state: DialogueState) -> None:
        state.updated_at = time.time()
        self._cache[state.session_id] = state
        if not self._persist:
            return
        try:
            _safe_json_dump(self._path_for(state.session_id), state.to_dict())
        except Exception:
            # never fail request on state save
            pass

    def reset(self, session_id: str) -> Dict[str, Any]:
        sid = (session_id or "default").strip() or "default"
        self._cache.pop(sid, None)
        p = self._path_for(sid)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
        return {"ok": True, "session_id": sid, "reset": True}

    def append_turn(
        self,
        *,
        state: DialogueState,
        role: str,
        text: str,
        mode: str,
        confidence: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        turn_id: Optional[str] = None,
    ) -> None:
        rec = DialogueTurnRecord(
            turn_id=str(turn_id or f"{int(time.time()*1000)}"),
            ts=time.time(),
            role=role,
            text=text,
            mode=mode,
            confidence=float(confidence or 0.0),
            metadata=dict(metadata or {}),
        )
        state.recent_turns.append(rec)
        if len(state.recent_turns) > self.max_recent_turns:
            state.recent_turns = state.recent_turns[-self.max_recent_turns:]
        state.turn_count += 1
        state.updated_at = time.time()