from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


RE_QUESTION = re.compile(r"\?\s*$")
RE_WHITESPACE = re.compile(r"\s+")
RE_TOKEN = re.compile(r"[a-z0-9']+")


def _norm(text: str) -> str:
    return RE_WHITESPACE.sub(" ", (text or "").strip()).lower()


def _tokens(text: str) -> List[str]:
    return RE_TOKEN.findall(_norm(text))


def _contains_any(text: str, phrases: List[str]) -> bool:
    t = _norm(text)
    return any(p in t for p in phrases)


def _exact_any(text: str, phrases: List[str]) -> bool:
    t = _norm(text)
    return t in {_norm(p) for p in phrases}


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _has_meaningful_recent_context(recent_turns: List[Dict[str, Any]]) -> bool:
    """
    True if there is at least one prior assistant or user turn with non-empty text.
    This is intentionally lightweight and deterministic.
    """
    if not recent_turns:
        return False
    for t in recent_turns:
        if not isinstance(t, dict):
            continue
        txt = str(t.get("text") or "").strip()
        role = str(t.get("role") or "")
        if txt and role in {"user", "assistant"}:
            return True
    return False


def _state_topic(dialogue_state: Dict[str, Any], topic: Optional[str]) -> str:
    t = (topic or "").strip()
    if t:
        return t
    return str(dialogue_state.get("topic") or "").strip()


@dataclass
class PlannedMode:
    mode: str  # answer | ask | clarify | summarize | reflect
    reason: str
    confidence_hint: float = 0.5
    ask_prompt: Optional[str] = None
    flags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "reason": self.reason,
            "confidence_hint": float(self.confidence_hint),
            "ask_prompt": self.ask_prompt,
            "flags": dict(self.flags or {}),
        }


class ResponseModePlanner:
    """
    Phase B Sprint 1:
    Deterministic response mode planner + repair/clarify heuristics.

    Goals:
    - predictable/testable behavior
    - better short follow-up handling
    - explicit summary/reflect routing
    - clear planner reasons for observability
    """

    def plan(
        self,
        *,
        user_text: str,
        dialogue_state: Optional[Dict[str, Any]] = None,
        topic: Optional[str] = None,
        intent: str = "answer",
    ) -> PlannedMode:
        text = (user_text or "").strip()
        text_l = _norm(text)
        toks = _tokens(text)

        state = dialogue_state or {}
        unresolved = list(state.get("unresolved", []) or [])
        recent_turns = list(state.get("recent_turns", []) or [])
        turn_count = _safe_int(state.get("turn_count"), 0)

        state_topic = _state_topic(state, topic)
        generic_topics = {"", "aion response", "response", "general", "unknown"}
        has_topic_context = _norm(state_topic) not in generic_topics
        has_recent_context = _has_meaningful_recent_context(recent_turns)
        has_context = bool(has_topic_context or has_recent_context or turn_count > 0)

        # ==========================================================
        # 1) Explicit summarize requests
        # ==========================================================
        if _contains_any(
            text_l,
            [
                "summarize",
                "sum up",
                "recap",
                "summary",
                "what have we done",
                "where are we at",
                "where are we now",
                "catch me up",
            ],
        ):
            return PlannedMode(
                mode="summarize",
                reason="explicit_summary_request",
                confidence_hint=0.80,
                flags={
                    "requires_state_context": True,
                    "has_context": has_context,
                    "turn_count": turn_count,
                },
            )

        # ==========================================================
        # 2) Explicit reflection/meta requests
        # ==========================================================
        if _contains_any(
            text_l,
            [
                "reflect",
                "what does this mean",
                "how are we doing",
                "how are we progressing",
                "status of aion thinking",
                "how intelligent is aion",
                "is this working",
            ],
        ):
            return PlannedMode(
                mode="reflect",
                reason="explicit_reflection_request",
                confidence_hint=0.72,
                flags={
                    "meta": True,
                    "has_context": has_context,
                    "turn_count": turn_count,
                },
            )

        # ==========================================================
        # 3) Very short follow-ups / repair path
        #    Fresh session => clarify
        #    Existing context => answer using context
        # ==========================================================
        short_followups = {
            "and then what",
            "then what",
            "what next",
            "next",
            "go on",
            "continue",
            "and then",
            "so then",
            "after that",
            "what after that",
            "why",
            "how",
            "which one",
            "what first",
        }

        if _exact_any(text_l, list(short_followups)):
            if has_context:
                return PlannedMode(
                    mode="answer",
                    reason="short_followup_with_context",
                    confidence_hint=0.62,
                    flags={
                        "uses_dialogue_context": True,
                        "has_topic_context": has_topic_context,
                        "has_recent_context": has_recent_context,
                        "turn_count": turn_count,
                    },
                )
            return PlannedMode(
                mode="clarify",
                reason="short_followup_without_context",
                confidence_hint=0.30,
                ask_prompt=(
                    "Do you mean the next AION build step, the next code task, "
                    "or the next roadmap phase?"
                ),
                flags={"uses_dialogue_context": False, "turn_count": turn_count},
            )

        # ==========================================================
        # 4) Vague implementation/debug requests with no context
        # ==========================================================
        vague_prompts = [
            "help me fix it",
            "fix this",
            "is this correct",
            "what file",
            "what do i run",
            "what am i running",
            "why is this happening",
            "what's wrong",
            "what is wrong",
        ]
        if _contains_any(text_l, vague_prompts) and not has_context:
            return PlannedMode(
                mode="clarify",
                reason="vague_request_no_context",
                confidence_hint=0.35,
                ask_prompt="Share the exact file path or error output and I’ll give the precise patch/command.",
                flags={"has_context": False},
            )

        # ==========================================================
        # 5) Unresolved-state disambiguation
        # ==========================================================
        if unresolved and _contains_any(
            text_l,
            ["why", "how", "which one", "what do you mean", "explain that", "clarify"],
        ):
            return PlannedMode(
                mode="clarify",
                reason="unresolved_state_needs_disambiguation",
                confidence_hint=0.48,
                ask_prompt=(
                    "Do you want me to explain the current implementation, "
                    "the failure cause, or the next implementation step?"
                ),
                flags={
                    "unresolved_count": len(unresolved),
                    "has_context": has_context,
                },
            )

        # ==========================================================
        # 6) Explicit ask-mode triggers (optional early scaffold)
        #    Use when the user is clearly requesting a decision from AION
        # ==========================================================
        if _contains_any(
            text_l,
            [
                "what should i do",
                "which should we do first",
                "help me choose",
                "pick one",
                "decide between",
            ],
        ):
            # We still route to "answer" for now unless you implement a dedicated ask handler.
            # Keeping reason explicit makes this easy to promote later.
            return PlannedMode(
                mode="answer",
                reason="decision_request_answer_mode",
                confidence_hint=0.66 if has_context else 0.58,
                flags={
                    "decision_request": True,
                    "has_context": has_context,
                },
            )

        # ==========================================================
        # 7) Question-like inputs -> answer
        # ==========================================================
        if RE_QUESTION.search(text) or ("?" in text):
            return PlannedMode(
                mode="answer",
                reason="question_detected_answer_mode",
                confidence_hint=0.64 if has_context else 0.60,
                flags={"has_context": has_context},
            )

        # ==========================================================
        # 8) Intent-driven default (current pipeline mostly uses answer)
        # ==========================================================
        if (intent or "answer").strip().lower() == "answer":
            return PlannedMode(
                mode="answer",
                reason="default_answer_mode",
                confidence_hint=0.64,
                flags={"has_context": has_context},
            )

        # ==========================================================
        # 9) Fallback
        # ==========================================================
        return PlannedMode(
            mode="answer",
            reason="fallback_answer_mode",
            confidence_hint=0.55,
            flags={"has_context": has_context},
        )