from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

from backend.modules.aion_resonance.resonance_state import load_phi_state
from backend.modules.aion_resonance.phi_reinforce import get_reinforce_state

try:
    from backend.modules.consciousness.state_manager import STATE as UCS_STATE
except Exception:  # pragma: no cover
    UCS_STATE = None  # type: ignore


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def infer_intent(user_text: str) -> str:
    t = (user_text or "").lower()
    if any(x in t for x in ["summarize", "summary", "recap"]):
        return "summarize"
    if any(x in t for x in ["why", "how", "explain", "what"]):
        return "answer"
    if any(x in t for x in ["do ", "run ", "execute ", "create ", "build "]):
        return "act"
    if any(x in t for x in ["think", "reflect"]):
        return "reflect"
    if "?" in t:
        return "answer"
    return "answer"


def infer_topic(user_text: str, prior_topic: Optional[str] = None) -> str:
    t = (user_text or "").lower()
    if "aion" in t and ("build" in t or "roadmap" in t or "next" in t):
        return "AION roadmap"
    if "aion" in t and "teaching" in t:
        return "AION teaching pipeline"
    if "aion" in t and "conversation" in t:
        return "AION conversation intelligence"
    if "weather" in t:
        return "weather"
    if prior_topic:
        return prior_topic
    return "AION response"


def choose_response_mode(
    *,
    user_text: str,
    intent: str,
    unresolved: List[str],
    confidence_hint: float,
) -> str:
    t = (user_text or "").lower()

    if intent == "summarize":
        return "summarize"
    if intent == "reflect":
        return "reflect"

    if any(x in t for x in ["clarify", "what do you mean", "not sure"]):
        return "ask"

    if confidence_hint < 0.35 and intent == "answer":
        return "ask"

    if unresolved and any(x in t for x in ["continue", "next", "proceed"]):
        return "answer"

    if intent == "act":
        return "act"

    return "answer"


def _runtime_context() -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        if UCS_STATE is None:
            return out

        paused = None
        current_container = None
        context = None

        try:
            paused = bool(UCS_STATE.is_paused())
        except Exception:
            pass
        try:
            current_container = UCS_STATE.get_current_container()
        except Exception:
            pass
        try:
            context = UCS_STATE.get_context()
        except Exception:
            pass

        out = {
            "paused": paused,
            "current_container": current_container if isinstance(current_container, dict) else None,
            "context": context if isinstance(context, dict) else None,
        }
    except Exception:
        return {}
    return out


def build_turn_context(
    *,
    user_text: str,
    dialogue_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Assemble a compact turn packet for the orchestrator.
    """
    phi = load_phi_state() or {}
    reinforce = get_reinforce_state() or {}
    beliefs = (reinforce.get("beliefs", {}) if isinstance(reinforce, dict) else {}) or {}

    prior_topic = dialogue_state.get("topic")
    unresolved = list(dialogue_state.get("unresolved") or [])

    intent = infer_intent(user_text)
    topic = infer_topic(user_text, prior_topic=prior_topic)

    phi_coh = _safe_float(phi.get("Φ_coherence"), 0.4)
    trust = _safe_float(beliefs.get("trust"), 0.4)
    clarity = _safe_float(beliefs.get("clarity"), 0.4)
    confidence_hint = round(max(0.15, min(0.95, 0.45 * phi_coh + 0.30 * trust + 0.25 * clarity)), 2)

    response_mode = choose_response_mode(
        user_text=user_text,
        intent=intent,
        unresolved=unresolved,
        confidence_hint=confidence_hint,
    )

    recent_turns = dialogue_state.get("recent_turns") or []
    recent_summary = [
        {
            "role": t.get("role"),
            "text": t.get("text", "")[:240],
            "mode": t.get("mode"),
            "confidence": t.get("confidence"),
        }
        for t in recent_turns[-6:]
        if isinstance(t, dict)
    ]

    return {
        "user_text": user_text,
        "intent": intent,
        "topic": topic,
        "response_mode": response_mode,
        "confidence_hint": confidence_hint,
        "phi_state": phi,
        "beliefs": beliefs,
        "runtime_context": _runtime_context(),
        "dialogue_state": {
            "session_id": dialogue_state.get("session_id"),
            "turn_count": dialogue_state.get("turn_count", 0),
            "unresolved": unresolved,
            "commitments": list(dialogue_state.get("commitments") or []),
            "last_mode": dialogue_state.get("last_mode"),
            "recent_turns": recent_summary,
        },
        "source_refs": [
            "turn_context_assembler",
            "resonance_state",
            "phi_reinforce",
            "dialogue_state_tracker",
        ],
    }