# /workspaces/COMDEX/backend/modules/aion_conversation/minimal_response_composer.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ==========================================================
# Data contracts
# ==========================================================

@dataclass
class AionKnowledgeState:
    intent: str = "answer"
    topic: str = "AION response"
    confidence: float = 0.5
    known_facts: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    fusion_snapshot: Dict[str, Any] = field(default_factory=dict)
    source_refs: List[str] = field(default_factory=list)


@dataclass
class ComposedResponse:
    text: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


# ==========================================================
# Helpers (deterministic + safe)
# ==========================================================

def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _clean_text(s: Any) -> str:
    return str(s or "").strip()


def _dedupe_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in items:
        v = _clean_text(x)
        if not v:
            continue
        k = v.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(v)
    return out


def _clip(items: List[str], n: int) -> List[str]:
    return list(items[: max(0, int(n))])


def _join_natural(items: List[str]) -> str:
    items = [i for i in items if _clean_text(i)]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _normalize_topic(topic: str) -> str:
    t = _clean_text(topic)
    return t if t else "AION response"


def _confidence_label(c: float) -> str:
    c = _safe_float(c, 0.0)
    if c >= 0.80:
        return "high"
    if c >= 0.60:
        return "moderate"
    if c >= 0.35:
        return "limited"
    return "low"


def _first_actionable_goal(goals: List[str]) -> Optional[str]:
    for g in goals:
        gl = g.lower()
        # prefer concrete implementation-style goals
        if any(k in gl for k in ["apply", "prove", "answer", "stay grounded", "preserve", "improve", "build", "route"]):
            return g
    return goals[0] if goals else None


def _render_answer_paragraphs(
    *,
    user_text: str,
    ks: AionKnowledgeState,
) -> str:
    """
    Phase 0.3 answer rendering:
    deterministic, grounded, paragraph-like, less list-template style.
    """
    topic = _normalize_topic(getattr(ks, "topic", "AION response"))
    confidence = round(max(0.0, min(0.99, _safe_float(getattr(ks, "confidence", 0.5), 0.5))), 2)

    known_facts = _dedupe_keep_order(list(getattr(ks, "known_facts", []) or []))
    goals = _dedupe_keep_order(list(getattr(ks, "goals", []) or []))
    unresolved = _dedupe_keep_order(list(getattr(ks, "unresolved", []) or []))
    source_refs = _dedupe_keep_order(list(getattr(ks, "source_refs", []) or []))

    # Keep deterministic clipping to avoid verbosity drift
    fact_view = _clip(known_facts, 3)
    goal_view = _clip(goals, 2)
    unresolved_view = _clip(unresolved, 2)

    # Opening sentence: topic + grounded stance
    opening = f"My current grounded view on {topic}:"

    # Facts sentence (naturalized)
    if fact_view:
        if len(fact_view) == 1:
            facts_sentence = f"Right now, {fact_view[0]}."
        else:
            facts_sentence = f"Right now, the key facts are that {_join_natural(fact_view)}."
    else:
        facts_sentence = "Right now, I have limited grounded facts loaded for this answer path."

    # Goal sentence (next step / focus)
    primary_goal = _first_actionable_goal(goal_view)
    if primary_goal and len(goal_view) > 1:
        secondary = [g for g in goal_view if g != primary_goal]
        goals_sentence = f"The immediate goal is to {primary_goal}, while also {secondary[0]}."
    elif primary_goal:
        goals_sentence = f"The immediate goal is to {primary_goal}."
    else:
        goals_sentence = "The immediate goal is to stay grounded and respond clearly."

    # Unresolved sentence (uncertainty kept explicit)
    if unresolved_view:
        unresolved_sentence = (
            f"The main unresolved point is {_join_natural(unresolved_view)}, "
            f"so this answer should be treated as a current-state summary rather than a final roadmap commitment."
        )
    else:
        unresolved_sentence = "There are no major unresolved blockers recorded in this response state."

    # Confidence sentence (explicit and stable)
    conf_sentence = (
        f"Current confidence is {confidence:.2f} ({_confidence_label(confidence)}), based on the available runtime/context signals."
    )

    # Optional grounding refs sentence (short; deterministic)
    if source_refs:
        refs_sentence = f"Grounding sources in this pass: {_join_natural(_clip(source_refs, 4))}."
    else:
        refs_sentence = "Grounding sources were not explicitly attached to this pass."

    # Build response as coherent paragraph(s), not a numbered list
    # Keep compact for Phase 0.3 but clearly better than Phase 0.2 template.
    return " ".join([
        opening,
        facts_sentence,
        goals_sentence,
        unresolved_sentence,
        conf_sentence,
        refs_sentence,
    ]).strip()


def _render_ask(
    *,
    user_text: str,
    ks: AionKnowledgeState,
) -> str:
    topic = _normalize_topic(getattr(ks, "topic", "AION response"))
    return (
        f"I can answer more precisely on {topic}, but I need one clarification first: "
        f"do you want the next build step, the implementation detail, or the roadmap priority?"
    )


def _render_clarify(
    *,
    user_text: str,
    ks: AionKnowledgeState,
) -> str:
    topic = _normalize_topic(getattr(ks, "topic", "AION response"))
    return (
        f"I can continue on {topic}, but your request is underspecified. "
        f"Tell me whether you want the next code task, the next roadmap phase, or a summary of what is already implemented."
    )


def _render_summarize(
    *,
    user_text: str,
    ks: AionKnowledgeState,
) -> str:
    topic = _normalize_topic(getattr(ks, "topic", "AION response"))
    facts = _clip(_dedupe_keep_order(list(getattr(ks, "known_facts", []) or [])), 3)
    goals = _clip(_dedupe_keep_order(list(getattr(ks, "goals", []) or [])), 2)
    unresolved = _clip(_dedupe_keep_order(list(getattr(ks, "unresolved", []) or [])), 2)

    parts: List[str] = [f"Summary for {topic}."]
    if facts:
        parts.append(f"Known facts: {_join_natural(facts)}.")
    if goals:
        parts.append(f"Current goals: {_join_natural(goals)}.")
    if unresolved:
        parts.append(f"Unresolved: {_join_natural(unresolved)}.")
    else:
        parts.append("No major unresolved items are currently recorded.")
    return " ".join(parts)


def _render_reflect(
    *,
    user_text: str,
    ks: AionKnowledgeState,
) -> str:
    topic = _normalize_topic(getattr(ks, "topic", "AION response"))
    confidence = round(max(0.0, min(0.99, _safe_float(getattr(ks, "confidence", 0.5), 0.5))), 2)
    sigma = _safe_float((getattr(ks, "fusion_snapshot", {}) or {}).get("sigma"), 0.0)
    psi = _safe_float((getattr(ks, "fusion_snapshot", {}) or {}).get("psi_tilde"), 0.0)

    return (
        f"AION reflection on {topic}: the response state is currently {_confidence_label(confidence)} confidence "
        f"(confidence={confidence:.2f}) with fusion snapshot sigma={sigma:.3f} and psi_tilde={psi:.3f}. "
        f"The next quality gain comes from stronger context-to-answer transformation, not just adding more facts."
    )


# ==========================================================
# Composer
# ==========================================================

class MinimalResponseComposer:
    """
    Phase 0.3: deterministic, grounded response composer with improved naturalness.

    Properties preserved:
    - deterministic text generation from KS
    - confidence passthrough (bounded)
    - metadata counts / topic / intent / timestamp
    """

    def compose(
        self,
        *,
        user_text: str,
        ks: AionKnowledgeState,
    ) -> ComposedResponse:
        intent = _clean_text(getattr(ks, "intent", "answer")).lower() or "answer"
        topic = _normalize_topic(getattr(ks, "topic", "AION response"))
        confidence = round(max(0.0, min(0.99, _safe_float(getattr(ks, "confidence", 0.5), 0.5))), 2)

        known_facts = _dedupe_keep_order(list(getattr(ks, "known_facts", []) or []))
        goals = _dedupe_keep_order(list(getattr(ks, "goals", []) or []))
        unresolved = _dedupe_keep_order(list(getattr(ks, "unresolved", []) or []))
        source_refs = _dedupe_keep_order(list(getattr(ks, "source_refs", []) or []))
        fusion_snapshot = dict(getattr(ks, "fusion_snapshot", {}) or {})

        # Deterministic mode mapping (still simple by design)
        if intent in {"clarify"}:
            text = _render_clarify(user_text=user_text, ks=ks)
        elif intent in {"ask"}:
            text = _render_ask(user_text=user_text, ks=ks)
        elif intent in {"summarize", "summary"}:
            text = _render_summarize(user_text=user_text, ks=ks)
        elif intent in {"reflect", "reflection"}:
            text = _render_reflect(user_text=user_text, ks=ks)
        else:
            text = _render_answer_paragraphs(user_text=user_text, ks=ks)

        metadata: Dict[str, Any] = {
            "topic": topic,
            "intent": intent,
            "fact_count": len(known_facts),
            "goal_count": len(goals),
            "unresolved_count": len(unresolved),
            "timestamp": time.time(),
            # extra grounding metadata for Phase 0.3 observability
            "composer_version": "phase0_3_natural_deterministic_v1",
            "grounding_ref_count": len(source_refs),
            "has_fusion_snapshot": bool(fusion_snapshot),
        }

        return ComposedResponse(
            text=text,
            confidence=confidence,
            metadata=metadata,
        )