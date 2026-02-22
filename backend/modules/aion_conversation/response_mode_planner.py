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


def _is_generic_topic(topic: Optional[str]) -> bool:
    return _norm(topic or "") in {"", "aion response", "response", "general", "unknown"}


def _looks_like_contextual_why_followup(text: str) -> bool:
    """
    Handle high-value multi-turn follow-ups like:
      - why that order
      - why this order
      - why that?
      - why first?
      - how so?
      - why though
    These should answer directly when strong context exists.
    """
    t = _norm(text)
    if t in {
        "why that order",
        "why this order",
        "why that",
        "why this",
        "why first",
        "why that first",
        "why this first",
        "how so",
        "why though",
        "why",
        "how",
    }:
        return True

    # Slightly broader phrase checks (still deterministic / conservative)
    why_phrases = [
        "why that order",
        "why this order",
        "why first",
        "why that first",
        "why this first",
    ]
    return any(p in t for p in why_phrases)


def _has_recent_answer_turn(recent_turns: List[Dict[str, Any]]) -> bool:
    for item in reversed(recent_turns or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "") != "assistant":
            continue
        mode = _norm(str(item.get("mode") or ""))
        txt = str(item.get("text") or "").strip()
        if txt and (mode == "answer" or mode == ""):
            return True
    return False


def _has_recent_clarify_turn(recent_turns: List[Dict[str, Any]]) -> bool:
    for item in reversed(recent_turns or []):
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "") != "assistant":
            continue
        mode = _norm(str(item.get("mode") or ""))
        if mode == "clarify":
            return True
    return False


def _is_contextual_elaboration_followup(text: str) -> bool:
    """
    Contextual expansion / elaboration follow-ups that should answer
    directly when context continuity is strong.
    """
    t = _norm(text)

    exacts = {
        "explain that",
        "explain that in more detail",
        "explain in more detail",
        "more detail",
        "more details",
        "go into more detail",
        "expand on that",
        "expand that",
        "elaborate",
        "elaborate on that",
        "tell me more",
        "explain more",
        "more info",
        "more information",
    }
    if t in exacts:
        return True

    phrases = [
        "explain that",
        "in more detail",
        "go into more detail",
        "expand on that",
        "elaborate on that",
        "tell me more",
    ]
    return any(p in t for p in phrases)


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
    Phase B Sprint 1 / 1.5 / 2 refinement:
    Deterministic response mode planner + repair/clarify heuristics.

    Goals:
    - predictable/testable behavior
    - better short follow-up handling
    - explicit summary/reflect routing
    - clear planner reasons for observability
    - contextual 'why/how' follow-ups can answer directly when continuity is strong
    - contextual elaboration follow-ups ('explain that in more detail') answer when continuity is strong
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
        toks = _tokens(text)  # kept for future heuristics / observability

        state = dialogue_state or {}
        unresolved = list(state.get("unresolved", []) or [])
        recent_turns = list(state.get("recent_turns", []) or [])
        turn_count = _safe_int(state.get("turn_count"), 0)

        state_topic = _state_topic(state, topic)
        has_topic_context = not _is_generic_topic(state_topic)
        has_recent_context = _has_meaningful_recent_context(recent_turns)
        has_context = bool(has_topic_context or has_recent_context or turn_count > 0)

        has_recent_answer = _has_recent_answer_turn(recent_turns)
        has_recent_clarify = _has_recent_clarify_turn(recent_turns)
        strong_continuity = bool(
            (has_topic_context and has_recent_context)
            or (has_topic_context and has_recent_answer)
        )

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
                    "has_topic_context": has_topic_context,
                    "has_recent_context": has_recent_context,
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
                    "has_topic_context": has_topic_context,
                    "has_recent_context": has_recent_context,
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
            # Refine "why/how" when continuity is weak: clarify
            if text_l in {"why", "how", "which one"} and not strong_continuity:
                if has_context:
                    return PlannedMode(
                        mode="clarify",
                        reason="underspecified_why_how_with_weak_continuity",
                        confidence_hint=0.40,
                        ask_prompt=(
                            "Do you want me to explain the reasoning, the implementation details, "
                            "or the next step?"
                        ),
                        flags={
                            "uses_dialogue_context": True,
                            "has_topic_context": has_topic_context,
                            "has_recent_context": has_recent_context,
                            "strong_continuity": strong_continuity,
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

            if has_context:
                return PlannedMode(
                    mode="answer",
                    reason="short_followup_with_context",
                    confidence_hint=0.62 if not strong_continuity else 0.66,
                    flags={
                        "uses_dialogue_context": True,
                        "has_topic_context": has_topic_context,
                        "has_recent_context": has_recent_context,
                        "strong_continuity": strong_continuity,
                        "has_recent_answer": has_recent_answer,
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
        # 3.5) Contextual "why/how" follow-ups with strong continuity
        #      (high-leverage refinement)
        # ==========================================================
        if _looks_like_contextual_why_followup(text_l):
            if strong_continuity:
                return PlannedMode(
                    mode="answer",
                    reason="contextual_why_followup_with_continuity",
                    confidence_hint=0.68,
                    flags={
                        "uses_dialogue_context": True,
                        "has_topic_context": has_topic_context,
                        "has_recent_context": has_recent_context,
                        "strong_continuity": strong_continuity,
                        "has_recent_answer": has_recent_answer,
                        "turn_count": turn_count,
                    },
                )

            # If there is some context but not strong continuity, prefer clarify
            if has_context:
                return PlannedMode(
                    mode="clarify",
                    reason="contextual_why_followup_weak_continuity",
                    confidence_hint=0.42,
                    ask_prompt=(
                        "Do you want the reasoning for the roadmap order, the implementation details, "
                        "or the next step?"
                    ),
                    flags={
                        "uses_dialogue_context": True,
                        "has_topic_context": has_topic_context,
                        "has_recent_context": has_recent_context,
                        "strong_continuity": strong_continuity,
                        "turn_count": turn_count,
                    },
                )

        # ==========================================================
        # 3.6) Contextual elaboration follow-up
        #      (e.g. "Explain that in more detail", "Tell me more")
        # ==========================================================
        if _is_contextual_elaboration_followup(text_l):
            if strong_continuity:
                return PlannedMode(
                    mode="answer",
                    reason="contextual_elaboration_followup",
                    confidence_hint=0.68 if has_topic_context else 0.62,
                    flags={
                        "uses_dialogue_context": True,
                        "has_topic_context": has_topic_context,
                        "has_recent_context": has_recent_context,
                        "strong_continuity": strong_continuity,
                        "has_recent_answer": has_recent_answer,
                        "turn_count": turn_count,
                        "elaboration_followup": True,
                    },
                )

            if has_context:
                return PlannedMode(
                    mode="clarify",
                    reason="contextual_elaboration_followup_weak_continuity",
                    confidence_hint=0.42,
                    ask_prompt=(
                        "Do you want more detail on the roadmap order, the implementation, "
                        "or the next step?"
                    ),
                    flags={
                        "uses_dialogue_context": True,
                        "has_topic_context": has_topic_context,
                        "has_recent_context": has_recent_context,
                        "strong_continuity": strong_continuity,
                        "turn_count": turn_count,
                        "elaboration_followup": True,
                    },
                )

            return PlannedMode(
                mode="clarify",
                reason="elaboration_followup_without_context",
                confidence_hint=0.34,
                ask_prompt="What would you like me to explain in more detail?",
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
        #    Do NOT force clarify if strong continuity exists for a
        #    contextual why/how OR elaboration follow-up.
        # ==========================================================
        if unresolved and _contains_any(
            text_l,
            ["why", "how", "which one", "what do you mean", "explain that", "clarify"],
        ):
            if _looks_like_contextual_why_followup(text_l) and strong_continuity:
                return PlannedMode(
                    mode="answer",
                    reason="contextual_why_followup_overrides_unresolved_clarify",
                    confidence_hint=0.66,
                    flags={
                        "uses_dialogue_context": True,
                        "unresolved_count": len(unresolved),
                        "has_context": has_context,
                        "strong_continuity": strong_continuity,
                    },
                )

            if _is_contextual_elaboration_followup(text_l) and strong_continuity:
                return PlannedMode(
                    mode="answer",
                    reason="contextual_elaboration_overrides_unresolved_clarify",
                    confidence_hint=0.66,
                    flags={
                        "uses_dialogue_context": True,
                        "unresolved_count": len(unresolved),
                        "has_context": has_context,
                        "strong_continuity": strong_continuity,
                        "elaboration_followup": True,
                    },
                )

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
                    "has_topic_context": has_topic_context,
                    "has_recent_context": has_recent_context,
                    "has_recent_clarify": has_recent_clarify,
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
            return PlannedMode(
                mode="answer",
                reason="decision_request_answer_mode",
                confidence_hint=0.66 if has_context else 0.58,
                flags={
                    "decision_request": True,
                    "has_context": has_context,
                    "has_topic_context": has_topic_context,
                    "has_recent_context": has_recent_context,
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
                flags={
                    "has_context": has_context,
                    "has_topic_context": has_topic_context,
                    "has_recent_context": has_recent_context,
                    "strong_continuity": strong_continuity,
                    "token_count": len(toks),
                },
            )

        # ==========================================================
        # 8) Intent-driven default (current pipeline mostly uses answer)
        # ==========================================================
        if (intent or "answer").strip().lower() == "answer":
            return PlannedMode(
                mode="answer",
                reason="default_answer_mode",
                confidence_hint=0.64,
                flags={
                    "has_context": has_context,
                    "has_topic_context": has_topic_context,
                    "has_recent_context": has_recent_context,
                    "strong_continuity": strong_continuity,
                },
            )

        # ==========================================================
        # 9) Fallback
        # ==========================================================
        return PlannedMode(
            mode="answer",
            reason="fallback_answer_mode",
            confidence_hint=0.55,
            flags={
                "has_context": has_context,
                "has_topic_context": has_topic_context,
                "has_recent_context": has_recent_context,
            },
        )