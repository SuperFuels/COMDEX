from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class AionKnowledgeState:
    intent: str = "unknown"
    topic: Optional[str] = None
    confidence: float = 0.2
    known_facts: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    fusion_snapshot: Dict[str, Any] = field(default_factory=dict)
    source_refs: List[str] = field(default_factory=list)


@dataclass
class ComposedResponse:
    text: str
    mode: str  # answer | ask | reflect | summarize | fallback
    confidence: float
    metadata: Dict[str, Any]


class MinimalResponseComposer:
    """
    Phase 0 composer:
    - template-driven
    - intentionally limited / child-like / structured output
    - honest about unknowns
    """

    def __init__(self, max_facts: int = 3, low_confidence_threshold: float = 0.45):
        self.max_facts = max_facts
        self.low_confidence_threshold = low_confidence_threshold

    def compose(self, user_text: str, ks: AionKnowledgeState) -> ComposedResponse:
        # Normalize confidence
        c = max(0.0, min(1.0, float(ks.confidence)))

        if c < self.low_confidence_threshold:
            text = self._compose_low_confidence(user_text, ks, c)
            mode = "ask"
        elif ks.intent in {"summarize", "summary"}:
            text = self._compose_summary(ks, c)
            mode = "summarize"
        elif ks.intent in {"reflect", "reflection"}:
            text = self._compose_reflection(ks, c)
            mode = "reflect"
        else:
            text = self._compose_answer(ks, c)
            mode = "answer"

        return ComposedResponse(
            text=text,
            mode=mode,
            confidence=c,
            metadata={
                "topic": ks.topic,
                "intent": ks.intent,
                "fact_count": len(ks.known_facts),
                "goal_count": len(ks.goals),
                "unresolved_count": len(ks.unresolved),
                "timestamp": time.time(),
                "phase": "phase0_minimal_composer",
            },
        )

    def _compose_low_confidence(self, user_text: str, ks: AionKnowledgeState, c: float) -> str:
        topic = ks.topic or "this topic"
        known = self._bulletish_facts(ks.known_facts)
        unresolved = ks.unresolved[:2]

        parts = [
            f"I am still learning about {topic}.",
            f"My confidence is {c:.2f}.",
        ]

        if known:
            parts.append(f"What I think I know: {known}.")
        else:
            parts.append("I do not have enough verified knowledge yet.")

        if unresolved:
            parts.append(f"I need help with: {', '.join(unresolved)}.")
        else:
            parts.append("Please teach me one step at a time.")

        parts.append("Can you correct me or give one example?")
        return " ".join(parts)

    def _compose_answer(self, ks: AionKnowledgeState, c: float) -> str:
        topic = ks.topic or "the question"
        known = ks.known_facts[: self.max_facts]
        goals = ks.goals[:2]

        parts = [f"My current answer about {topic}:"]

        if known:
            for i, fact in enumerate(known, start=1):
                parts.append(f"{i}) {fact}")
        else:
            parts.append("1) I have limited stored facts right now.")

        if goals:
            parts.append(f"Next goal: {goals[0]}.")

        parts.append(f"(confidence: {c:.2f})")
        return " ".join(parts)

    def _compose_summary(self, ks: AionKnowledgeState, c: float) -> str:
        topic = ks.topic or "current topic"
        facts = ks.known_facts[: self.max_facts]
        if not facts:
            return f"Summary for {topic}: I do not have enough facts yet. (confidence: {c:.2f})"
        return f"Summary for {topic}: " + " | ".join(facts) + f" (confidence: {c:.2f})"

    def _compose_reflection(self, ks: AionKnowledgeState, c: float) -> str:
        topic = ks.topic or "current work"
        unresolved = ks.unresolved[:3]
        if unresolved:
            return (
                f"Reflection on {topic}: I am stable but incomplete. "
                f"I need to improve: {', '.join(unresolved)}. "
                f"(confidence: {c:.2f})"
            )
        return f"Reflection on {topic}: no major unresolved items detected. (confidence: {c:.2f})"

    def _bulletish_facts(self, facts: List[str]) -> str:
        if not facts:
            return ""
        return "; ".join(facts[: self.max_facts])