from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, ClassVar, Literal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALLOWED_TURN_MODES = {"answer", "ask", "clarify", "summarize", "reflect"}


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _safe_bool(v: Any, default: bool = False) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        t = v.strip().lower()
        if t in {"1", "true", "yes", "y", "on"}:
            return True
        if t in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _norm_str(v: Any, default: str = "") -> str:
    if v is None:
        return default
    return str(v).strip()


def _list_str(values: Any) -> List[str]:
    if not isinstance(values, list):
        return []
    out: List[str] = []
    for x in values:
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _dict_any(v: Any) -> Dict[str, Any]:
    return dict(v) if isinstance(v, dict) else {}


def _list_dict(v: Any) -> List[Dict[str, Any]]:
    if not isinstance(v, list):
        return []
    return [dict(x) for x in v if isinstance(x, dict)]


def _sanitize_mode(mode: Any, default: str = "answer") -> str:
    m = _norm_str(mode, default).lower() or default
    return m if m in _ALLOWED_TURN_MODES else default


def _validate_required_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required and must be a non-empty string")


# ---------------------------------------------------------------------------
# Shared lightweight state snapshot (contract-safe view)
# NOTE:
# - This is NOT replacing dialogue_state_tracker.DialogueState.
# - It is a transport/schema contract that mirrors important fields.
# ---------------------------------------------------------------------------

@dataclass
class DialogueStateSnapshot:
    schema_version: str = "aion.dialogue_state_snapshot.v1"

    session_id: str = ""
    topic: Optional[str] = None
    intent: str = "answer"
    turn_count: int = 0
    unresolved: List[str] = field(default_factory=list)
    commitments: List[str] = field(default_factory=list)
    last_mode: Optional[str] = None
    last_user_text: Optional[str] = None
    last_response_text: Optional[str] = None
    recent_turns: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.schema_version = _norm_str(self.schema_version, "aion.dialogue_state_snapshot.v1") or "aion.dialogue_state_snapshot.v1"
        self.session_id = _norm_str(self.session_id)
        self.topic = _norm_str(self.topic) if self.topic is not None else None
        self.intent = _norm_str(self.intent, "answer") or "answer"
        self.turn_count = max(0, _safe_int(self.turn_count, 0))
        self.unresolved = _list_str(self.unresolved)
        self.commitments = _list_str(self.commitments)
        self.last_mode = _sanitize_mode(self.last_mode, default="answer") if self.last_mode is not None else None
        self.last_user_text = _norm_str(self.last_user_text) if self.last_user_text is not None else None
        self.last_response_text = _norm_str(self.last_response_text) if self.last_response_text is not None else None
        self.recent_turns = _list_dict(self.recent_turns)

        # snapshot can be partially populated, but session_id should normally exist
        if self.session_id:
            _validate_required_nonempty("session_id", self.session_id)

    def validate(self, *, require_session_id: bool = True) -> "DialogueStateSnapshot":
        if require_session_id:
            _validate_required_nonempty("session_id", self.session_id)
        if self.turn_count < 0:
            raise ValueError("turn_count must be >= 0")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "topic": self.topic,
            "intent": self.intent,
            "turn_count": int(self.turn_count),
            "unresolved": list(self.unresolved or []),
            "commitments": list(self.commitments or []),
            "last_mode": self.last_mode,
            "last_user_text": self.last_user_text,
            "last_response_text": self.last_response_text,
            "recent_turns": [dict(x) for x in (self.recent_turns or [])],
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "DialogueStateSnapshot":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.dialogue_state_snapshot.v1"),
            session_id=str(d.get("session_id") or ""),
            topic=(str(d.get("topic")).strip() if d.get("topic") is not None else None),
            intent=str(d.get("intent") or "answer"),
            turn_count=_safe_int(d.get("turn_count"), 0),
            unresolved=_list_str(d.get("unresolved")),
            commitments=_list_str(d.get("commitments")),
            last_mode=(str(d.get("last_mode")).strip() if d.get("last_mode") is not None else None),
            last_user_text=(str(d.get("last_user_text")) if d.get("last_user_text") is not None else None),
            last_response_text=(str(d.get("last_response_text")) if d.get("last_response_text") is not None else None),
            recent_turns=_list_dict(d.get("recent_turns")),
        )


# ---------------------------------------------------------------------------
# Turn contracts
# ---------------------------------------------------------------------------

@dataclass
class TurnPacket:
    """
    Input contract to the conversation orchestrator.
    """
    schema_version: str = "aion.turn_packet.v1"

    session_id: str = ""
    user_text: str = ""
    apply_teaching: Optional[bool] = None
    include_debug: bool = False
    include_metadata: bool = True
    request_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _norm_str(self.schema_version, "aion.turn_packet.v1") or "aion.turn_packet.v1"
        self.session_id = _norm_str(self.session_id)
        self.user_text = str(self.user_text or "").strip()
        if self.apply_teaching is not None:
            self.apply_teaching = bool(self.apply_teaching)
        self.include_debug = bool(self.include_debug)
        self.include_metadata = bool(self.include_metadata)
        self.request_metadata = _dict_any(self.request_metadata)

    def validate(self) -> "TurnPacket":
        _validate_required_nonempty("session_id", self.session_id)
        _validate_required_nonempty("user_text", self.user_text)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "user_text": self.user_text,
            "apply_teaching": self.apply_teaching,
            "include_debug": bool(self.include_debug),
            "include_metadata": bool(self.include_metadata),
            "request_metadata": dict(self.request_metadata or {}),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TurnPacket":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.turn_packet.v1"),
            session_id=str(d.get("session_id") or ""),
            user_text=str(d.get("user_text") or ""),
            apply_teaching=(None if d.get("apply_teaching") is None else bool(d.get("apply_teaching"))),
            include_debug=bool(d.get("include_debug", False)),
            include_metadata=bool(d.get("include_metadata", True)),
            request_metadata=_dict_any(d.get("request_metadata")),
        )


@dataclass
class TurnContext:
    """
    Normalized context packet produced by turn_context_assembler.
    Mirrors current build_turn_context() output shape.
    """
    schema_version: str = "aion.turn_context.v1"

    user_text: str = ""
    intent: str = "answer"
    topic: str = "AION response"
    response_mode: str = "answer"
    confidence_hint: float = 0.5

    phi_state: Dict[str, Any] = field(default_factory=dict)
    beliefs: Dict[str, Any] = field(default_factory=dict)
    runtime_context: Dict[str, Any] = field(default_factory=dict)

    dialogue_state: Dict[str, Any] = field(default_factory=dict)
    followup_context: Dict[str, Any] = field(default_factory=dict)

    context_hints: List[str] = field(default_factory=list)
    source_refs: List[str] = field(default_factory=list)

    # Optional planner packet emitted upstream by assembler (single source of truth path)
    planner: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _norm_str(self.schema_version, "aion.turn_context.v1") or "aion.turn_context.v1"
        self.user_text = str(self.user_text or "").strip()
        self.intent = _norm_str(self.intent, "answer") or "answer"
        self.topic = _norm_str(self.topic, "AION response") or "AION response"
        self.response_mode = _sanitize_mode(self.response_mode, "answer")
        self.confidence_hint = _safe_float(self.confidence_hint, 0.5)

        self.phi_state = _dict_any(self.phi_state)
        self.beliefs = _dict_any(self.beliefs)
        self.runtime_context = _dict_any(self.runtime_context)
        self.dialogue_state = _dict_any(self.dialogue_state)
        self.followup_context = _dict_any(self.followup_context)
        self.context_hints = _list_str(self.context_hints)
        self.source_refs = _list_str(self.source_refs)
        self.planner = _dict_any(self.planner)

    def validate(self, *, require_user_text: bool = False) -> "TurnContext":
        if require_user_text:
            _validate_required_nonempty("user_text", self.user_text)
        if self.response_mode not in _ALLOWED_TURN_MODES:
            raise ValueError(f"response_mode must be one of {sorted(_ALLOWED_TURN_MODES)}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "user_text": self.user_text,
            "intent": self.intent,
            "topic": self.topic,
            "response_mode": self.response_mode,
            "confidence_hint": float(self.confidence_hint),
            "phi_state": dict(self.phi_state or {}),
            "beliefs": dict(self.beliefs or {}),
            "runtime_context": dict(self.runtime_context or {}),
            "dialogue_state": dict(self.dialogue_state or {}),
            "followup_context": dict(self.followup_context or {}),
            "context_hints": list(self.context_hints or []),
            "source_refs": list(self.source_refs or []),
            "planner": dict(self.planner or {}),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TurnContext":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.turn_context.v1"),
            user_text=str(d.get("user_text") or ""),
            intent=str(d.get("intent") or "answer"),
            topic=str(d.get("topic") or "AION response"),
            response_mode=str(d.get("response_mode") or "answer"),
            confidence_hint=_safe_float(d.get("confidence_hint"), 0.5),
            phi_state=_dict_any(d.get("phi_state")),
            beliefs=_dict_any(d.get("beliefs")),
            runtime_context=_dict_any(d.get("runtime_context")),
            dialogue_state=_dict_any(d.get("dialogue_state")),
            followup_context=_dict_any(d.get("followup_context")),
            context_hints=_list_str(d.get("context_hints")),
            source_refs=_list_str(d.get("source_refs")),
            planner=_dict_any(d.get("planner")),
        )


@dataclass
class TurnPlan:
    """
    Planner decision contract (maps to PlannedMode.to_dict()).
    """
    schema_version: str = "aion.turn_plan.v1"

    mode: str = "answer"               # answer | ask | clarify | summarize | reflect
    reason: str = "default_answer_mode"
    confidence_hint: float = 0.5
    ask_prompt: Optional[str] = None
    flags: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _norm_str(self.schema_version, "aion.turn_plan.v1") or "aion.turn_plan.v1"
        self.mode = _sanitize_mode(self.mode, "answer")
        self.reason = _norm_str(self.reason, "default_answer_mode") or "default_answer_mode"
        self.confidence_hint = _safe_float(self.confidence_hint, 0.5)
        self.ask_prompt = _norm_str(self.ask_prompt) if self.ask_prompt is not None else None
        self.flags = _dict_any(self.flags)

    def validate(self) -> "TurnPlan":
        if self.mode not in _ALLOWED_TURN_MODES:
            raise ValueError(f"mode must be one of {sorted(_ALLOWED_TURN_MODES)}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "reason": self.reason,
            "confidence_hint": float(self.confidence_hint),
            "ask_prompt": self.ask_prompt,
            "flags": dict(self.flags or {}),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TurnPlan":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.turn_plan.v1"),
            mode=str(d.get("mode") or "answer"),
            reason=str(d.get("reason") or "default_answer_mode"),
            confidence_hint=_safe_float(d.get("confidence_hint"), 0.5),
            ask_prompt=(str(d.get("ask_prompt")) if d.get("ask_prompt") is not None else None),
            flags=_dict_any(d.get("flags")),
        )


@dataclass
class TurnResult:
    """
    Standardized orchestrator output contract.
    Mirrors current /api/aion/conversation/turn response shape.
    """
    schema_version: str = "aion.turn_result.v1"

    ok: bool = False
    origin: str = ""
    turn_id: str = ""
    session_id: str = ""

    response: str = ""
    confidence: float = 0.0
    mode: str = "answer"
    topic: str = "AION response"

    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    debug: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.schema_version = _norm_str(self.schema_version, "aion.turn_result.v1") or "aion.turn_result.v1"
        self.ok = bool(self.ok)
        self.origin = _norm_str(self.origin)
        self.turn_id = _norm_str(self.turn_id)
        self.session_id = _norm_str(self.session_id)
        self.response = str(self.response or "")
        self.confidence = _safe_float(self.confidence, 0.0)
        self.mode = _sanitize_mode(self.mode, "answer")
        self.topic = _norm_str(self.topic, "AION response") or "AION response"
        self.timestamp = _norm_str(self.timestamp) if self.timestamp is not None else None
        self.metadata = _dict_any(self.metadata)
        self.debug = _dict_any(self.debug)

    def validate(self) -> "TurnResult":
        _validate_required_nonempty("origin", self.origin)
        _validate_required_nonempty("turn_id", self.turn_id)
        _validate_required_nonempty("session_id", self.session_id)
        if self.mode not in _ALLOWED_TURN_MODES:
            raise ValueError(f"mode must be one of {sorted(_ALLOWED_TURN_MODES)}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "ok": bool(self.ok),
            "origin": self.origin,
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "response": self.response,
            "confidence": float(self.confidence),
            "mode": self.mode,
            "topic": self.topic,
        }
        if self.metadata:
            out["metadata"] = dict(self.metadata)
        if self.debug:
            out["debug"] = dict(self.debug)
        return out

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TurnResult":
        d = dict(data or {})
        return cls(
            schema_version=str(d.get("schema_version") or "aion.turn_result.v1"),
            ok=bool(d.get("ok", False)),
            origin=str(d.get("origin") or ""),
            turn_id=str(d.get("turn_id") or ""),
            session_id=str(d.get("session_id") or ""),
            timestamp=(str(d.get("timestamp")) if d.get("timestamp") is not None else None),
            response=str(d.get("response") or ""),
            confidence=_safe_float(d.get("confidence"), 0.0),
            mode=str(d.get("mode") or "answer"),
            topic=str(d.get("topic") or "AION response"),
            metadata=_dict_any(d.get("metadata")),
            debug=_dict_any(d.get("debug")),
        )


# ---------------------------------------------------------------------------
# Convenience helpers (optional usage in orchestrator/tests)
# ---------------------------------------------------------------------------

def make_turn_result_from_orchestrator_dict(payload: Dict[str, Any]) -> TurnResult:
    """
    Convenience adapter for wrapping existing orchestrator dict responses.
    """
    return TurnResult.from_dict(payload).validate()