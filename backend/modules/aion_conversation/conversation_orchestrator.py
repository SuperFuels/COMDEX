from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.modules.aion_conversation.dialogue_state_tracker import DialogueStateTracker
from backend.modules.aion_conversation.turn_context_assembler import build_turn_context
from backend.modules.aion_conversation.response_mode_planner import ResponseModePlanner

# Reuse your working composer backend path (Phase 0.2)
from backend.modules.aion_resonance.aion_llm_bridge import LLMRespondRequest, _run_composer_response


@dataclass
class OrchestratorConfig:
    enable_teaching_default: bool = False
    max_unresolved: int = 10


_MODE_PLANNER = ResponseModePlanner()


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _extract_commitments(text: str) -> List[str]:
    t = (text or "").lower()
    hits: List[str] = []
    patterns = [
        ("i will", "assistant_promised_action"),
        ("next step", "next_step_offered"),
        ("we should", "suggested_plan"),
        ("i can", "assistant_capability_offer"),
    ]
    for phrase, label in patterns:
        if phrase in t and label not in hits:
            hits.append(label)
    return hits


def _extract_new_unresolved(user_text: str, response_text: str) -> List[str]:
    out: List[str] = []
    u = (user_text or "").lower()
    r = (response_text or "").lower()

    if "?" in user_text and ("not sure" in r or "clarify" in r):
        out.append("clarification_pending")

    if any(x in u for x in ["next", "roadmap", "plan"]) and "specific user intent refinement" in r:
        out.append("specific user intent refinement")

    return out


def _topic_norm(topic: Optional[str]) -> str:
    return _norm(topic or "")


def _is_roadmap_topic(topic: Optional[str]) -> bool:
    t = _topic_norm(topic)
    return ("roadmap" in t) or ("aion roadmap" in t) or ("building next" in t)


def _is_short_next_followup(text: str) -> bool:
    t = _norm(text)
    return t in {
        "and then what",
        "then what",
        "what next",
        "next",
        "go on",
        "continue",
        "and then",
    }


def _build_roadmap_followup_response(
    *,
    dialogue_state: Dict[str, Any],
    apply_teaching: bool,
) -> Dict[str, Any]:
    """
    Local deterministic answer for roadmap follow-ups like:
      - and then what
      - what next
      - continue
    This gives a visible jump in usefulness before deeper planner/composer upgrades.
    """
    turn_count = int((dialogue_state or {}).get("turn_count") or 0)
    topic = (dialogue_state or {}).get("topic") or "AION roadmap"

    steps: List[str] = [
        "Phase 0.3: improve composer naturalness so it uses KS (facts/goals/unresolved) as a coherent answer, not just a listed template",
        "Phase B Sprint 1.5: add more local follow-up handlers (roadmap/next-step/prioritization) for high-value conversational continuity",
        "Phase B Sprint 2: route richer turn context into response planning so follow-up answers become topic-specific by default",
        "Phase C (next major layer): unified skill registry + execution adapter so AION can reliably do things, not just describe them",
    ]

    if apply_teaching:
        lead = (
            "Next, use the working teaching-apply path to improve the roadmap response style itself "
            "(teach a cleaner roadmap explanation pattern), then expand follow-up handlers."
        )
    else:
        lead = (
            "Next, improve the answer behavior for roadmap follow-ups before deepening the stack, "
            "so AION feels more intelligent in multi-turn use immediately."
        )

    msg = (
        f"Next step for {topic}: {lead} "
        f"Priority order: 1) {steps[0]} 2) {steps[1]} 3) {steps[2]} 4) {steps[3]}. "
        f"(session_turn_events={turn_count})"
    )

    return {
        "ok": True,
        "origin": "aion_conversation_orchestrator",
        "response": msg,
        "confidence": 0.74,
        "mode": "answer",
        "metadata": {
            "phase": "phase_b_sprint1_5_local_handlers",
            "planner_reason": "short_followup_with_context",
            "local_mode_handler": True,
            "local_handler": "roadmap_followup_next_step",
        },
        "debug": {},
    }


def _build_prioritization_response(
    *,
    dialogue_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Local deterministic answer for:
      'what should we build first to make it feel more intelligent?'
    """
    topic = (dialogue_state or {}).get("topic") or "AION roadmap"
    msg = (
        f"To make AION feel more intelligent fastest (within {topic}), build in this order: "
        "1) Conversation Orchestrator + Turn Context Assembler + Dialogue State Tracker (done scaffold), "
        "2) stronger response planning + local follow-up handlers, "
        "3) composer naturalness improvements (KS-aware phrasing), "
        "4) skill runtime registry/execution adapter (Phase C), "
        "5) learning loop integration (Phase D)."
    )
    return {
        "ok": True,
        "origin": "aion_conversation_orchestrator",
        "response": msg,
        "confidence": 0.78,
        "mode": "answer",
        "metadata": {
            "phase": "phase_b_sprint1_5_local_handlers",
            "planner_reason": "roadmap_priority_question",
            "local_mode_handler": True,
            "local_handler": "roadmap_prioritization",
        },
        "debug": {},
    }


def _local_mode_response(
    *,
    user_text: str,
    mode: str,
    plan: Dict[str, Any],
    dialogue_state: Dict[str, Any],
    topic: Optional[str],
    apply_teaching: bool,
) -> Optional[Dict[str, Any]]:
    """
    Local deterministic responses for clarify/summarize/reflect,
    plus selective answer-path handlers for roadmap follow-ups.
    Return None for paths that should go through composer.
    """
    text_n = _norm(user_text)

    # ------------------------------------------------------------------
    # Local ANSWER handlers (high-leverage, topic-specific follow-ups)
    # ------------------------------------------------------------------
    if mode == "answer":
        # Roadmap short follow-up: "and then what" / "what next" etc.
        if plan.get("reason") == "short_followup_with_context" and _is_roadmap_topic(topic) and _is_short_next_followup(user_text):
            return _build_roadmap_followup_response(
                dialogue_state=dialogue_state,
                apply_teaching=bool(apply_teaching),
            )

        # Roadmap prioritization prompt
        if _is_roadmap_topic(topic) and (
            "what should we build first" in text_n
            or ("feel more intelligent" in text_n and "build first" in text_n)
        ):
            return _build_prioritization_response(dialogue_state=dialogue_state)

    # ------------------------------------------------------------------
    # Local CLARIFY handler
    # ------------------------------------------------------------------
    if mode == "clarify":
        ask_prompt = plan.get("ask_prompt") or "Can you clarify what you want me to do next?"
        return {
            "ok": True,
            "origin": "aion_conversation_orchestrator",
            "response": ask_prompt,
            "confidence": 0.45,
            "mode": "clarify",
            "metadata": {
                "phase": "phase_b_sprint1_mode_planner",
                "planner_reason": plan.get("reason"),
                "local_mode_handler": True,
            },
            "debug": {
                "planner": plan,
            },
        }

    # ------------------------------------------------------------------
    # Local SUMMARIZE handler
    # ------------------------------------------------------------------
    if mode == "summarize":
        recent = list((dialogue_state or {}).get("recent_turns", []) or [])
        if not recent:
            summary = "No conversation history is stored yet for this session."
        else:
            last_items = recent[-8:]
            user_msgs = [str(x.get("text", "")) for x in last_items if x.get("role") == "user"]
            topic_s = (dialogue_state or {}).get("topic") or "current topic"
            recent_prompt_preview = " | ".join([m[:120] for m in user_msgs[-3:]]) if user_msgs else "none"
            summary = (
                f"Session summary ({topic_s}): "
                f"{len(recent)} stored turn events. "
                f"Recent user prompts: {recent_prompt_preview}"
            )

        return {
            "ok": True,
            "origin": "aion_conversation_orchestrator",
            "response": summary,
            "confidence": 0.70,
            "mode": "summarize",
            "metadata": {
                "phase": "phase_b_sprint1_mode_planner",
                "planner_reason": plan.get("reason"),
                "local_mode_handler": True,
            },
            "debug": {
                "planner": plan,
            },
        }

    # ------------------------------------------------------------------
    # Local REFLECT handler
    # ------------------------------------------------------------------
    if mode == "reflect":
        topic_s = (dialogue_state or {}).get("topic") or "unknown"
        turn_count = int((dialogue_state or {}).get("turn_count") or 0)
        unresolved = list((dialogue_state or {}).get("unresolved", []) or [])
        msg = (
            f"AION reflection: current dialogue topic is {topic_s}; "
            f"stored turn count={turn_count}; unresolved items={len(unresolved)}. "
            f"Next improvement target is stronger context-aware response planning and topic-specific follow-up answers."
        )
        return {
            "ok": True,
            "origin": "aion_conversation_orchestrator",
            "response": msg,
            "confidence": 0.68,
            "mode": "reflect",
            "metadata": {
                "phase": "phase_b_sprint1_mode_planner",
                "planner_reason": plan.get("reason"),
                "local_mode_handler": True,
            },
            "debug": {
                "planner": plan,
            },
        }

    return None


class ConversationOrchestrator:
    """
    Phase B Sprint 1 + Sprint 1.5 orchestrator:
    - loads dialogue state
    - assembles turn context
    - plans response mode (answer/clarify/summarize/reflect)
    - local deterministic handlers for high-value follow-ups (roadmap next-step, summarize, clarify, reflect)
    - calls existing /llm/respond backend logic (default answer path)
    - updates state
    """

    def __init__(
        self,
        tracker: Optional[DialogueStateTracker] = None,
        config: Optional[OrchestratorConfig] = None,
    ) -> None:
        self.tracker = tracker or DialogueStateTracker()
        self.config = config or OrchestratorConfig()

    def handle_turn(
        self,
        *,
        session_id: str,
        user_text: str,
        apply_teaching: Optional[bool] = None,
        include_debug: bool = False,
        include_metadata: bool = True,
    ) -> Dict[str, Any]:
        started = time.time()
        turn_id = str(uuid.uuid4())

        if apply_teaching is None:
            apply_teaching = self.config.enable_teaching_default

        state = self.tracker.get_or_create(session_id)
        state_dict = state.to_dict()

        # Assemble from current state BEFORE appending the new user turn
        turn_ctx = build_turn_context(user_text=user_text, dialogue_state=state_dict)

        # Plan response mode from current dialogue state + current user input
        plan_obj = _MODE_PLANNER.plan(
            user_text=user_text,
            dialogue_state=state_dict,
            topic=str(turn_ctx.get("topic") or state.topic or ""),
            intent=str(turn_ctx.get("intent") or "answer"),
        )
        plan = plan_obj.to_dict()
        planned_mode = str(plan.get("mode") or "answer")

        # Override context mode with planner output for downstream consistency
        turn_ctx["response_mode"] = planned_mode
        turn_ctx["planner"] = plan

        # Track user turn first
        self.tracker.append_turn(
            state=state,
            role="user",
            text=user_text,
            mode="input",
            confidence=0.0,
            metadata={"turn_id": turn_id},
            turn_id=turn_id + ":u",
        )

        # Use state AFTER user append for local handlers (summary/roadmap follow-up can see latest turn)
        state_after_user = state.to_dict()

        # Local short-circuit paths (clarify / summarize / reflect / selective answer handlers)
        local_out = _local_mode_response(
            user_text=user_text,
            mode=planned_mode,
            plan=plan,
            dialogue_state=state_after_user,
            topic=str(turn_ctx.get("topic") or state.topic or ""),
            apply_teaching=bool(apply_teaching),
        )

        if local_out is not None:
            composer_out = {
                "ok": True,
                "origin": local_out.get("origin", "aion_conversation_orchestrator"),
                "timestamp": None,
                "user_text": user_text,
                "response": str(local_out.get("response") or ""),
                "confidence": float(local_out.get("confidence") or 0.0),
                "metadata": dict(local_out.get("metadata") or {}),
            }
            if include_debug:
                composer_out["debug"] = dict(local_out.get("debug") or {})
        else:
            # Default answer path -> composer backend
            req = LLMRespondRequest(
                user_text=user_text,
                intent=str(turn_ctx.get("intent") or "answer"),
                topic=str(turn_ctx.get("topic") or "AION response"),
                confidence=float(turn_ctx.get("confidence_hint") or 0.0),
                known_facts=[
                    (
                        f"AION runtime paused state is {bool((turn_ctx.get('runtime_context') or {}).get('paused'))}"
                        if (turn_ctx.get("runtime_context") or {}).get("paused") is not None
                        else "AION runtime paused state is unknown"
                    ),
                    "AION response path is using MinimalResponseComposer",
                ],
                goals=[
                    "answer the user clearly",
                    "stay grounded in current runtime state",
                    "preserve multi-turn continuity",
                ],
                unresolved=list((turn_ctx.get("dialogue_state") or {}).get("unresolved") or []),
                fusion_snapshot={
                    "sigma": float((turn_ctx.get("beliefs") or {}).get("stability", 0.5) or 0.5),
                    "psi_tilde": float((turn_ctx.get("phi_state") or {}).get("Φ_coherence", 0.5) or 0.5),
                },
                source_refs=list(turn_ctx.get("source_refs") or []),
                apply_teaching=apply_teaching,
                include_debug=include_debug,
                include_metadata=include_metadata,
            )
            composer_out = _run_composer_response(req)

        response_text = str(composer_out.get("response") or "")
        confidence = float(composer_out.get("confidence") or 0.0)
        metadata = dict(composer_out.get("metadata") or {})

        # Update dialogue state
        state.topic = str(turn_ctx.get("topic") or state.topic or "AION response")
        state.intent = str(turn_ctx.get("intent") or state.intent or "answer")
        state.last_mode = planned_mode
        state.last_user_text = user_text
        state.last_response_text = response_text

        # commitments
        for c in _extract_commitments(response_text):
            if c not in state.commitments:
                state.commitments.append(c)

        # unresolved merge (bounded)
        merged_unresolved = list(state.unresolved or [])
        for u in _extract_new_unresolved(user_text, response_text):
            if u not in merged_unresolved:
                merged_unresolved.append(u)
        state.unresolved = merged_unresolved[-self.config.max_unresolved :]

        self.tracker.append_turn(
            state=state,
            role="assistant",
            text=response_text,
            mode=planned_mode,
            confidence=confidence,
            metadata={"turn_id": turn_id, "metadata": metadata},
            turn_id=turn_id + ":a",
        )

        self.tracker.save(state)

        out: Dict[str, Any] = {
            "ok": True,
            "origin": "aion_conversation_orchestrator",
            "turn_id": turn_id,
            "session_id": state.session_id,
            "timestamp": composer_out.get("timestamp"),
            "response": response_text,
            "confidence": confidence,
            "mode": planned_mode,
            "topic": state.topic,
        }

        if include_metadata:
            out["metadata"] = {
                **metadata,
                "orchestrator": {
                    "turn_count": state.turn_count,
                    "state_topic": state.topic,
                    "state_intent": state.intent,
                    "unresolved_count": len(state.unresolved),
                    "commitment_count": len(state.commitments),
                    "latency_ms": int((time.time() - started) * 1000),
                    "planned_mode": planned_mode,
                    "planner_reason": plan.get("reason"),
                    "local_mode_handler": bool(local_out is not None),
                },
            }

        if include_debug:
            out["debug"] = {
                "turn_context": turn_ctx,
                "dialogue_state": state.to_dict(),
                "composer_out": composer_out,
                "planner": plan,
            }

        return out

    def get_state(self, session_id: str) -> Dict[str, Any]:
        return self.tracker.get_or_create(session_id).to_dict()

    def reset_state(self, session_id: str) -> Dict[str, Any]:
        return self.tracker.reset(session_id)