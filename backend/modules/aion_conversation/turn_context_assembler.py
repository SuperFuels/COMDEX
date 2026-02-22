from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.modules.aion_conversation.response_mode_planner import ResponseModePlanner


_MODE_PLANNER = ResponseModePlanner()


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _topic_norm(topic: Optional[str]) -> str:
    return _norm(topic or "")


def _is_generic_topic(topic: Optional[str]) -> bool:
    t = _topic_norm(topic)
    return t in {"", "aion response", "response", "general", "unknown"}


def _is_short_followup(text: str) -> bool:
    t = _norm(text)
    return t in {
        "and then what",
        "then what",
        "what next",
        "next",
        "go on",
        "continue",
        "and then",
        "what should we do next",
    }


def _is_summary_request(text: str) -> bool:
    t = _norm(text)
    phrases = [
        "summarize",
        "sum up",
        "recap",
        "where are we at",
        "what have we done",
    ]
    return any(p in t for p in phrases)


def _is_reflection_request(text: str) -> bool:
    t = _norm(text)
    phrases = [
        "reflect",
        "how are we doing",
        "what does this mean",
        "status of aion thinking",
    ]
    return any(p in t for p in phrases)


def _is_status_progress_request(text: str) -> bool:
    t = _norm(text)
    phrases = [
        "status",
        "progress",
        "where we are",
        "where are we",
        "where we at",
    ]
    return any(p in t for p in phrases)


def _infer_topic_from_text(user_text: str, dialogue_state: Dict[str, Any]) -> str:
    """
    Lightweight deterministic topic inference.
    Prefer existing state topic when available and non-generic.
    """
    state_topic = str((dialogue_state or {}).get("topic") or "").strip()
    if state_topic and not _is_generic_topic(state_topic):
        return state_topic

    t = _norm(user_text)

    if "roadmap" in t or "building next" in t or "what is aion building" in t:
        return "AION roadmap"
    if "teach" in t or "teaching" in t:
        return "AION teaching pipeline"
    if "composer" in t or "respond" in t:
        return "AION response pipeline"
    if "conversation" in t or "orchestrator" in t:
        return "AION conversation runtime"
    if "skill" in t or "skills" in t:
        return "AION skill runtime"
    if "learn" in t or "learning" in t:
        return "AION learning loop"

    return "AION response"


def _infer_intent(user_text: str) -> str:
    """
    Deterministic intent label for the LLMRespondRequest path.
    Keep coarse-grained for now.
    """
    t = _norm(user_text)

    if _is_summary_request(t):
        return "summarize"
    if _is_reflection_request(t):
        return "reflect"

    if "?" in (user_text or ""):
        return "answer"

    if _is_short_followup(t):
        return "answer"

    if any(p in t for p in ["what should", "how do", "how should", "which", "why", "explain"]):
        return "answer"

    return "answer"


def _infer_response_mode_hint(user_text: str) -> str:
    t = _norm(user_text)
    if _is_summary_request(t):
        return "summarize"
    if _is_reflection_request(t):
        return "reflect"
    return "answer"


def _recent_turns(dialogue_state: Dict[str, Any], limit: int = 8) -> List[Dict[str, Any]]:
    recent = list((dialogue_state or {}).get("recent_turns", []) or [])
    clean = [r for r in recent if isinstance(r, dict)]
    if limit <= 0:
        return clean
    return clean[-limit:]


def _extract_recent_user_prompts(recent_turns: List[Dict[str, Any]], limit: int = 4) -> List[str]:
    msgs: List[str] = []
    for item in recent_turns:
        if item.get("role") == "user":
            txt = str(item.get("text") or "").strip()
            if txt:
                msgs.append(txt)
    return msgs[-limit:]


def _extract_last_assistant_response(recent_turns: List[Dict[str, Any]]) -> Optional[str]:
    for item in reversed(recent_turns):
        if item.get("role") == "assistant":
            txt = str(item.get("text") or "").strip()
            if txt:
                return txt
    return None


def _extract_recent_assistant_modes(recent_turns: List[Dict[str, Any]], limit: int = 4) -> List[str]:
    modes: List[str] = []
    for item in recent_turns:
        if item.get("role") == "assistant":
            m = str(item.get("mode") or "").strip()
            if m:
                modes.append(m)
    return modes[-limit:]


def _followup_features(user_text: str, dialogue_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Richer follow-up extraction for Phase B Sprint 2.
    Produces deterministic hints that the orchestrator/composer can use.
    """
    state = dialogue_state or {}
    recent = _recent_turns(state, limit=10)
    state_topic = str(state.get("topic") or "")
    state_topic_n = _topic_norm(state_topic)
    generic_topics = {"", "aion response", "response", "general", "unknown"}

    has_recent_context = len(recent) > 0
    has_topic_context = state_topic_n not in generic_topics

    user_text_n = _norm(user_text)
    short_followup = _is_short_followup(user_text_n)

    recent_user_prompts = _extract_recent_user_prompts(recent, limit=4)
    last_assistant_response = _extract_last_assistant_response(recent)
    recent_assistant_modes = _extract_recent_assistant_modes(recent, limit=4)

    continuity_from_topic = bool(has_topic_context and short_followup)
    continuity_from_recent = bool(has_recent_context and short_followup)

    has_prior_summary = "summarize" in recent_assistant_modes
    has_prior_clarify = "clarify" in recent_assistant_modes

    return {
        "is_short_followup": short_followup,
        "has_recent_context": has_recent_context,
        "has_topic_context": has_topic_context,
        "state_topic": state_topic,
        "recent_user_prompts": recent_user_prompts,
        "last_assistant_response": last_assistant_response,
        "recent_assistant_modes": recent_assistant_modes,
        "continuity_signals": {
            "topic_continuity": continuity_from_topic,
            "recent_turn_continuity": continuity_from_recent,
            "has_prior_summary": has_prior_summary,
            "has_prior_clarify": has_prior_clarify,
        },
        "turn_count": int(state.get("turn_count") or 0),
    }


def _confidence_hint(
    *,
    user_text: str,
    topic: str,
    intent: str,
    dialogue_state: Dict[str, Any],
    followup: Dict[str, Any],
) -> float:
    """
    Deterministic confidence hint for downstream composer request.
    This is a hint, not a final truth score.
    """
    t = _norm(user_text)
    base = 0.58

    if intent in {"summarize", "reflect"}:
        base = 0.68

    if not _is_generic_topic(topic):
        base += 0.04

    if followup.get("is_short_followup"):
        if followup.get("has_topic_context") or followup.get("has_recent_context"):
            base += 0.04
        else:
            base -= 0.18

    if "explain" in t or "what should" in t or "how do" in t:
        base += 0.02

    if _is_status_progress_request(t):
        base += 0.01

    unresolved = list((dialogue_state or {}).get("unresolved", []) or [])
    if unresolved:
        base -= min(0.08, 0.02 * len(unresolved))

    return max(0.20, min(0.90, round(base, 2)))


def _build_context_hints(
    *,
    user_text: str,
    topic: str,
    ds_view: Dict[str, Any],
    followup: Dict[str, Any],
) -> List[str]:
    hints: List[str] = []

    if followup.get("is_short_followup"):
        if followup.get("has_topic_context") or followup.get("has_recent_context"):
            hints.append("interpret_as_followup_to_active_context")
        else:
            hints.append("likely_requires_clarification_without_context")

    if not _is_generic_topic(topic):
        hints.append("topic_is_non_generic")

    if ds_view.get("unresolved"):
        hints.append("carry_forward_unresolved_items")

    if ds_view.get("commitments"):
        hints.append("consider_prior_commitments")

    if _is_summary_request(user_text):
        hints.append("prefer_state_summarization")

    if _is_reflection_request(user_text):
        hints.append("prefer_meta_reflection")

    if _is_status_progress_request(user_text):
        hints.append("prefer_status_progress_answer")

    if followup.get("continuity_signals", {}).get("has_prior_clarify"):
        hints.append("may_resolve_after_prior_clarification")

    return hints


def build_turn_context(
    *,
    user_text: str,
    dialogue_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase B Sprint 2 (richer turn-context assembly)
    -----------------------------------------------
    Deterministically assembles a turn packet for the orchestrator/composer.
    This intentionally remains lightweight and safe:
      - no side effects
      - no external calls
      - no mutation of tracker state
      - stable shape for downstream consumers
      - includes prebuilt planner output for orchestrator reuse

    Inputs:
      - user_text
      - dialogue_state (snapshot from DialogueStateTracker)

    Output:
      dict with:
        user_text, intent, topic, response_mode, confidence_hint,
        phi_state, beliefs, runtime_context (best-effort placeholders),
        dialogue_state (shallow relevant view),
        followup_context, context_hints, source_refs, planner
    """
    state = dict(dialogue_state or {})
    topic = _infer_topic_from_text(user_text, state)
    intent = _infer_intent(user_text)
    response_mode = _infer_response_mode_hint(user_text)

    followup = _followup_features(user_text=user_text, dialogue_state=state)
    confidence_hint = _confidence_hint(
        user_text=user_text,
        topic=topic,
        intent=intent,
        dialogue_state=state,
        followup=followup,
    )

    # These are placeholders at assembler layer; orchestrator can enrich
    # using runtime modules and actual phi/beliefs sources downstream.
    phi_state: Dict[str, Any] = {}
    beliefs: Dict[str, Any] = {}
    runtime_context: Dict[str, Any] = {}

    # Dialogue state subset to keep packet compact + predictable
    ds_view = {
        "session_id": state.get("session_id"),
        "topic": state.get("topic"),
        "intent": state.get("intent"),
        "turn_count": int(state.get("turn_count") or 0),
        "unresolved": list(state.get("unresolved", []) or []),
        "commitments": list(state.get("commitments", []) or []),
        "last_mode": state.get("last_mode"),
        "recent_turns": _recent_turns(state, limit=6),
    }

    context_hints = _build_context_hints(
        user_text=user_text,
        topic=topic,
        ds_view=ds_view,
        followup=followup,
    )

    # Prebuild planner output so orchestrator and debug views use one deterministic plan source
    planner_obj = _MODE_PLANNER.plan(
        user_text=user_text,
        dialogue_state=state,
        topic=topic,
        intent=intent,
    )
    planner = planner_obj.to_dict()

    # Keep top-level response_mode aligned with planner mode
    response_mode = str(planner.get("mode") or response_mode or "answer")

    source_refs = [
        "turn_context_assembler",
        "dialogue_state_tracker",
        "response_mode_planner",
    ]

    if followup.get("has_topic_context") or followup.get("has_recent_context"):
        source_refs.append("followup_context_extractor")

    return {
        "user_text": user_text,
        "intent": intent,
        "topic": topic,
        "response_mode": response_mode,
        "confidence_hint": _safe_float(confidence_hint, 0.58),
        "phi_state": phi_state,
        "beliefs": beliefs,
        "runtime_context": runtime_context,
        "dialogue_state": ds_view,
        "followup_context": followup,
        "context_hints": context_hints,
        "source_refs": source_refs,
        "planner": planner,
    }