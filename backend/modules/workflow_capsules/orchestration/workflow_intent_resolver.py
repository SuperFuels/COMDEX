from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)
from backend.modules.workflow_capsules.habits.habit_capsule_registry import (
    HabitCapsuleRegistry,
)


@dataclass
class WorkflowIntentResolution:
    ok: bool
    matched: bool = False
    canonical_key: Optional[str] = None
    display_name: Optional[str] = None
    display_glyph: Optional[str] = None
    score: float = 0.0
    reason: str = ""
    query: str = ""
    candidates: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _norm(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


class WorkflowIntentResolver:
    """
    Safe deterministic intent resolver for workflow capsules.

    This is intentionally narrow for the first lock:
      - exact canonical key
      - display glyph WG-001
      - obvious Gmail enquiry workflow language

    It does not execute workflows. It only resolves intent to a capsule key.
    """

    def __init__(
        self,
        registry: Optional[WorkflowGlyphRegistry] = None,
        habit_registry: Optional[HabitCapsuleRegistry] = None,
    ) -> None:
        self.registry = registry or WorkflowGlyphRegistry()
        self.habit_registry = habit_registry or HabitCapsuleRegistry()

    def resolve(self, user_text: str, *, rebuild_registry: bool = True) -> WorkflowIntentResolution:
        raw = str(user_text or "").strip()
        t = _norm(raw)

        if not raw:
            return WorkflowIntentResolution(ok=True, matched=False, reason="empty_input", query=raw)

        if rebuild_registry:
            self.registry.rebuild_and_save()

        # Advisory habit resolution.
        # Habits never execute directly. They resolve back to a source workflow key,
        # then execution still goes through WorkflowGlyphRegistry/WorkflowCapsuleRunner.
        try:
            self.habit_registry.rebuild_and_save()
            habit_matches = self.habit_registry.find(raw)
            if habit_matches:
                top_habit = habit_matches[0]
                return self._resolve_query(
                    top_habit.source_workflow_key,
                    reason=f"habit_advisory_match:{top_habit.reason}",
                )
        except Exception:
            pass

        # Explicit workflow identity paths.
        if "workflow:gmail.enquiry_reply.v1" in t:
            return self._resolve_query("workflow:gmail.enquiry_reply.v1", reason="exact_canonical_key_in_text")

        if "wg-001" in t or "wg001" in t:
            return self._resolve_query("WG-001", reason="display_glyph_in_text")

        # Narrow Gmail enquiry intent route.
        gmail_terms = ["gmail", "email", "mail"]
        enquiry_terms = ["enquiry", "inquiry", "customer message", "customer email", "lead"]
        action_terms = ["draft", "reply", "respond", "handle", "run", "prepare"]

        has_gmail = any(x in t for x in gmail_terms)
        has_enquiry = any(x in t for x in enquiry_terms)
        has_action = any(x in t for x in action_terms)

        if has_gmail and has_enquiry and has_action:
            return self._resolve_query("workflow:gmail.enquiry_reply.v1", reason="gmail_enquiry_action_intent")

        return WorkflowIntentResolution(ok=True, matched=False, reason="no_workflow_intent_match", query=raw)

    def _resolve_query(self, query: str, *, reason: str) -> WorkflowIntentResolution:
        try:
            matches = self.registry.find(query)
            candidates = [m.to_dict() for m in matches[:5]]

            if not matches:
                return WorkflowIntentResolution(
                    ok=False,
                    matched=False,
                    reason="registry_no_match",
                    query=query,
                    candidates=candidates,
                    errors=[f"workflow_not_found:{query}"],
                )

            top = matches[0]
            capsule = self.registry.require(top.canonical_key)

            return WorkflowIntentResolution(
                ok=True,
                matched=True,
                canonical_key=capsule.canonical_key,
                display_name=capsule.display_name,
                display_glyph=capsule.display_glyph,
                score=float(top.score),
                reason=reason or top.reason,
                query=query,
                candidates=candidates,
            )
        except Exception as exc:
            return WorkflowIntentResolution(
                ok=False,
                matched=False,
                reason="resolver_exception",
                query=query,
                errors=[f"{type(exc).__name__}: {exc}"],
            )
