from __future__ import annotations

import time
import uuid
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from backend.modules.aion_conversation.dialogue_state_tracker import DialogueStateTracker
from backend.modules.aion_conversation.turn_context_assembler import build_turn_context
from backend.modules.aion_conversation.response_mode_planner import ResponseModePlanner
from backend.modules.aion_skills.registry import get_global_skill_registry, register_builtin_demo_skills
from backend.modules.aion_skills.execution_adapter import SkillExecutionAdapter
from backend.modules.aion_trading.learning_capture import get_trading_learning_capture_runtime
from backend.modules.aion_skills.contracts import SkillRunRequest
# Reuse your working composer backend path (Phase 0.2+)
from backend.modules.aion_resonance.aion_llm_bridge import LLMRespondRequest, _run_composer_response
# Trading Sprint 3 (paper-only learning capture / journal)
from backend.modules.aion_conversation.contracts import (
    TurnPacket,
    TurnResult,
    TurnContext,
    TurnPlan,
    DialogueStateSnapshot,
)

# Phase D Sprint 2 (read-only learning context for orchestrator debug/trace)
from backend.modules.aion_learning.runtime import get_aion_learning_runtime


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

    if "?" in (user_text or "") and ("not sure" in r or "clarify" in r):
        out.append("clarification_pending")

    # keep compatibility with both old list-style and newer natural composer phrasing
    if any(x in u for x in ["next", "roadmap", "plan"]) and (
        "specific user intent refinement" in r or "main unresolved point is specific user intent refinement" in r
    ):
        out.append("specific user intent refinement")

    return out


def _topic_norm(topic: Optional[str]) -> str:
    return _norm(topic or "")


def _is_generic_topic(topic: Optional[str]) -> bool:
    t = _topic_norm(topic)
    return t in {"", "aion response", "response", "general", "unknown"}


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


def _is_contextual_elaboration_followup(text: str) -> bool:
    t = _norm(text)
    phrases = [
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
    ]
    return any(p in t for p in phrases)


def _is_contextual_why_followup(text: str) -> bool:
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
    return any(
        p in t
        for p in [
            "why that order",
            "why this order",
            "why first",
            "why that first",
            "why this first",
        ]
    )


def _truncate_text(text: Optional[str], n: int = 180) -> str:
    s = str(text or "").strip()
    if len(s) <= n:
        return s
    return s[: max(0, n - 3)].rstrip() + "..."


def _composer_known_facts_from_turn_ctx(turn_ctx: Dict[str, Any]) -> List[str]:
    """
    Build deterministic known_facts for the composer from turn context.
    Keeps facts short and grounded.
    """
    facts: List[str] = []

    runtime_ctx = dict(turn_ctx.get("runtime_context") or {})
    paused_val = runtime_ctx.get("paused")

    if paused_val is None:
        facts.append("AION runtime paused state is unknown")
    else:
        facts.append(f"AION runtime paused state is {bool(paused_val)}")

    facts.append("AION response path is using MinimalResponseComposer")

    # Follow-up continuity facts
    followup = dict(turn_ctx.get("followup_context") or {})
    if followup.get("is_short_followup"):
        facts.append("Current user message is a short follow-up")
    if followup.get("has_topic_context"):
        facts.append(f"Active dialogue topic is {str(followup.get('state_topic') or 'unknown')}")
    if followup.get("has_recent_context"):
        recent_prompts = list(followup.get("recent_user_prompts") or [])
        if recent_prompts:
            facts.append(f"Recent user prompt: {_truncate_text(recent_prompts[-1], 140)}")

    # Optional last assistant response breadcrumb (shortened)
    last_assistant = followup.get("last_assistant_response")
    if last_assistant:
        facts.append(f"Last assistant response summary: {_truncate_text(last_assistant, 140)}")

    # planner breadcrumb (useful when composer is used on follow-ups)
    planner = dict(turn_ctx.get("planner") or {})
    planner_reason = str(planner.get("reason") or "").strip()
    if planner_reason:
        facts.append(f"Planner routed this turn as {planner_reason}")

    # dedupe preserve order
    out: List[str] = []
    for f in facts:
        if f not in out:
            out.append(f)
    return out


def _composer_goals_from_turn_ctx(turn_ctx: Dict[str, Any]) -> List[str]:
    """
    Build deterministic goals for the composer.
    """
    goals: List[str] = [
        "answer the user clearly",
        "stay grounded in current runtime state",
        "preserve multi-turn continuity",
    ]

    followup = dict(turn_ctx.get("followup_context") or {})
    hints = list(turn_ctx.get("context_hints") or [])
    planner = dict(turn_ctx.get("planner") or {})
    planner_reason = str(planner.get("reason") or "")

    if followup.get("is_short_followup"):
        if followup.get("has_topic_context") or followup.get("has_recent_context"):
            goals.append("interpret short follow-up using active conversation context")
        else:
            goals.append("avoid overcommitting when short follow-up lacks context")

    if planner_reason == "contextual_elaboration_followup":
        goals.append("expand the prior answer in more detail without changing the topic")
    elif planner_reason in {
        "contextual_why_followup_with_continuity",
        "contextual_why_followup_overrides_unresolved_clarify",
    }:
        goals.append("explain the reasoning behind the prior answer using active context")

    if "carry_forward_unresolved_items" in hints:
        goals.append("acknowledge unresolved items when relevant")

    if "consider_prior_commitments" in hints:
        goals.append("respect prior commitments in dialogue state")

    if "prefer_state_summarization" in hints:
        goals.append("summarize stored state succinctly")

    if "prefer_meta_reflection" in hints:
        goals.append("provide concise meta reflection grounded in state")

    # Deduplicate while preserving order
    out: List[str] = []
    for g in goals:
        if g not in out:
            out.append(g)
    return out


def _composer_source_refs(turn_ctx: Dict[str, Any]) -> List[str]:
    refs: List[str] = list(turn_ctx.get("source_refs") or [])
    followup = dict(turn_ctx.get("followup_context") or {})

    if followup.get("has_topic_context") or followup.get("has_recent_context"):
        if "followup_context_extractor" not in refs:
            refs.append("followup_context_extractor")

    planner = dict(turn_ctx.get("planner") or {})
    if planner.get("reason") and "response_mode_planner" not in refs:
        refs.append("response_mode_planner")

    return refs


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default

def _extract_first_float(text: str, patterns: List[str]) -> Optional[float]:
    s = str(text or "")
    for pat in patterns:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if not m:
            continue
        try:
            return float(m.group(1))
        except Exception:
            continue
    return None


def _extract_pair_from_text(text: str) -> Optional[str]:
    t = _norm(text)
    # support slash and compact forms
    pair_map = {
        "eur/usd": "EUR/USD",
        "gbp/usd": "GBP/USD",
        "usd/jpy": "USD/JPY",
        "aud/usd": "AUD/USD",
        "usd/cad": "USD/CAD",
        "nzd/usd": "NZD/USD",
        "usd/chf": "USD/CHF",
        "eurusd": "EUR/USD",
        "gbpusd": "GBP/USD",
        "usdjpy": "USD/JPY",
        "audusd": "AUD/USD",
        "usdcad": "USD/CAD",
        "nzdusd": "NZD/USD",
        "usdchf": "USD/CHF",
    }
    for k, v in pair_map.items():
        if k in t:
            return v
    return None


def _extract_direction_from_text(text: str) -> Optional[str]:
    t = f" {_norm(text)} "
    if any(x in t for x in [" sell ", " short ", " bearish "]):
        return "SELL"
    if any(x in t for x in [" buy ", " long ", " bullish "]):
        return "BUY"
    return None


def _parse_trade_risk_request_from_text(user_text: str) -> Dict[str, Any]:
    """
    Deterministic parser for natural-language risk validation prompts.
    Returns a partial dict with parsed values only.
    Fallbacks are handled by caller.
    """
    raw = str(user_text or "")
    t = _norm(raw)

    out: Dict[str, Any] = {}

    pair = _extract_pair_from_text(raw)
    if pair:
        out["pair"] = pair

    direction = _extract_direction_from_text(raw)
    if direction:
        out["direction"] = direction

    # Price fields: flexible forms:
    # entry 1.1025 / entry=1.1025 / at 1.1025
    entry = _extract_first_float(raw, [
        r"\bentry\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\b",
        r"\bat\s+([0-9]+(?:\.[0-9]+)?)\b",
    ])
    if entry is not None:
        out["entry"] = entry

    stop_loss = _extract_first_float(raw, [
        r"\b(?:sl|stop(?:\s*loss)?)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\b",
    ])
    if stop_loss is not None:
        out["stop_loss"] = stop_loss

    take_profit = _extract_first_float(raw, [
        r"\b(?:tp|target|take\s*profit)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\b",
    ])
    if take_profit is not None:
        out["take_profit"] = take_profit

    # Risk/account values
    account_equity = _extract_first_float(raw, [
        r"\b(?:equity|account(?:\s*equity)?|balance)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\b",
    ])
    if account_equity is not None:
        out["account_equity"] = account_equity

    risk_pct = _extract_first_float(raw, [
        r"\brisk\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"\brisk_pct\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\b",
    ])
    if risk_pct is not None:
        out["risk_pct"] = risk_pct

    stop_pips = _extract_first_float(raw, [
        r"\b(?:stop_pips|sl\s*pips|stop\s*pips)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\b",
        r"\b([0-9]+(?:\.[0-9]+)?)\s*pips?\b",
    ])
    if stop_pips is not None:
        out["stop_pips"] = stop_pips

    pip_value = _extract_first_float(raw, [
        r"\b(?:pip_value|pip\s*value)\s*[:=]?\s*([0-9]+(?:\.[0-9]+)?)\b",
    ])
    if pip_value is not None:
        out["pip_value"] = pip_value

    # Optional strategy tier inference
    if "tier 1" in t or "tier1" in t or "order flow" in t:
        out["strategy_tier"] = "tier1_order_flow_sniping"
    elif "tier 2" in t or "tier2" in t or "momentum" in t or "opening range" in t:
        out["strategy_tier"] = "tier2_momentum_orb"
    elif "tier 3" in t or "tier3" in t or "smc" in t:
        out["strategy_tier"] = "tier3_smc_intraday"
    elif "tier 4" in t or "tier4" in t or "swing" in t:
        out["strategy_tier"] = "tier4_swing"
    elif "tier 5" in t or "tier5" in t or "macro" in t:
        out["strategy_tier"] = "tier5_macro_positioning"

    return out

def _normalize_influence_key(raw_key: str) -> str:
    """
    Maps natural-language keys to canonical decision influence keys.
    Keep aliases here so parser stays simple.
    """
    k = _norm(raw_key).replace("-", " ").replace("_", " ")
    aliases = {
        "liquidity sweep": "liquidity_sweep",
        "liquidity sweeps": "liquidity_sweep",
        "sweep": "liquidity_sweep",
        "news risk filter": "news_risk_filter",
        "news filter": "news_risk_filter",
        "news risk": "news_risk_filter",
        "session bias": "session_bias",
        "market structure": "market_structure",
        "order flow": "order_flow",
        "volatility regime": "volatility_regime",
        "trend alignment": "trend_alignment",
    }
    if k in aliases:
        return aliases[k]
    return k.replace(" ", "_")


# ------------------------------------------------------------------
# Trading Sprint 3 parser helpers: decision influence weights patch
# ------------------------------------------------------------------

def _extract_decision_influence_key_from_text(text: str) -> Optional[str]:
    t = _norm(text)

    # Canonical key aliases (expand over time)
    key_aliases = [
        (["liquidity sweep", "liquidity_sweep", "sweep influence"], "liquidity_sweep"),
        (["news risk filter", "news_risk_filter", "news filter", "news risk"], "news_risk_filter"),
        (["session bias", "session_bias"], "session_bias"),
        (["market structure", "market_structure"], "market_structure"),
        (["order flow", "order_flow"], "order_flow"),
        (["volatility regime", "volatility_regime", "volatility influence"], "volatility_regime"),
        (["trend alignment", "trend_alignment"], "trend_alignment"),
    ]

    for aliases, canonical in key_aliases:
        if any(a in t for a in aliases):
            return canonical
    return None


def _extract_decision_influence_scope_from_text(text: str) -> Dict[str, Any]:
    """
    Optional scope parsing (safe, partial). Keep empty when not present.
    """
    t = _norm(text)
    scope: Dict[str, Any] = {}

    pair = _extract_pair_from_text(text)
    if pair:
        scope["pair"] = pair

    # simple timeframe parsing
    for tf in ["m1", "m5", "m15", "m30", "h1", "h4", "d1"]:
        if f" {tf} " in f" {t} ":
            scope["timeframe"] = tf.upper()
            break

    # optional checkpoint/session tags
    if "london" in t:
        scope["session"] = "london"
    elif "new york" in t or "ny" in t:
        scope["session"] = "new_york"
    elif "asia" in t:
        scope["session"] = "asia"

    return scope


def _parse_decision_influence_request_from_text(user_text: str) -> Dict[str, Any]:
    """
    Deterministic parser for decision influence weights commands.

    Returns:
      {
        "intent": "show" | "update",
        "dry_run": bool,
        "patch": {"ops":[...]},
        "scope": {...},
        "warnings": [...],
        "reason": str,
      }
    """
    raw = str(user_text or "")
    t = _norm(raw)

    warnings: List[str] = []

    # Safety default
    dry_run = True
    if any(x in t for x in ["apply live", "live apply", "commit", "write now", "not dry run"]):
        dry_run = False
    if "dry run" in t or "dry-run" in t:
        dry_run = True

    # "show" / read intent
    show_phrases = [
        "show decision influence weights",
        "show influence weights",
        "display decision influence weights",
        "view decision influence weights",
        "get decision influence weights",
    ]
    if any(p in t for p in show_phrases):
        return {
            "intent": "show",
            "dry_run": True,          # read path stays safe
            "patch": {},
            "scope": _extract_decision_influence_scope_from_text(raw),
            "warnings": [],
            "reason": "User requested current decision influence weights snapshot.",
        }

    # Update intent (delta/set)
    key = _extract_decision_influence_key_from_text(raw)
    scope = _extract_decision_influence_scope_from_text(raw)

    # Delta patterns: "increase X by 0.05", "decrease X by 0.02"
    inc_m = re.search(
        r"\b(?:increase|raise|up)\b.*?\bby\s*([-+]?[0-9]+(?:\.[0-9]+)?)\b",
        raw,
        flags=re.IGNORECASE,
    )
    dec_m = re.search(
        r"\b(?:decrease|lower|reduce|down)\b.*?\bby\s*([-+]?[0-9]+(?:\.[0-9]+)?)\b",
        raw,
        flags=re.IGNORECASE,
    )

    # Set patterns: "set X to 0.08", "set X = 0.08"
    set_m = re.search(
        r"\bset\b.*?\b(?:to|=)\s*([-+]?[0-9]+(?:\.[0-9]+)?)\b",
        raw,
        flags=re.IGNORECASE,
    )

    patch_ops: List[Dict[str, Any]] = []

    if key is None:
        # if user clearly asks update but no key parsed
        if any(x in t for x in ["decision influence", "influence weights", "update influence", "increase", "decrease", "set "]):
            warnings.append("No recognized decision influence key found in request.")

    if inc_m and key:
        try:
            v = float(inc_m.group(1))
            patch_ops.append({"op": "delta", "key": key, "value": abs(v)})
        except Exception:
            warnings.append("Could not parse increase delta value.")
    elif dec_m and key:
        try:
            v = float(dec_m.group(1))
            patch_ops.append({"op": "delta", "key": key, "value": -abs(v)})
        except Exception:
            warnings.append("Could not parse decrease delta value.")
    elif set_m and key:
        try:
            v = float(set_m.group(1))
            patch_ops.append({"op": "set", "key": key, "value": v})
        except Exception:
            warnings.append("Could not parse set value.")

    # Fallback intent if generic phrase but no op parsed
    if not patch_ops:
        if any(p in t for p in ["decision influence weights", "update influence weights", "decision influence dry run"]):
            warnings.append("No patch operation parsed; returning empty patch for validation/display path.")
            return {
                "intent": "update",
                "dry_run": dry_run,
                "patch": {},
                "scope": scope,
                "warnings": warnings,
                "reason": "User requested decision influence update, but parser could not extract a patch op.",
            }

    return {
        "intent": "update",
        "dry_run": dry_run,
        "patch": {"ops": patch_ops} if patch_ops else {},
        "scope": scope,
        "warnings": warnings,
        "reason": "User-requested decision influence weights update via orchestrator route.",
    }

def _turn_ctx_as_dict(turn_ctx: Any) -> Dict[str, Any]:
    """
    Accept either dict (current assembler output) or TurnContext contract.
    """
    if isinstance(turn_ctx, TurnContext):
        return turn_ctx.to_dict()
    if isinstance(turn_ctx, dict):
        return dict(turn_ctx)
    return {}


def _plan_as_dict(plan_obj: Any) -> Dict[str, Any]:
    """
    Accept planner outputs as dict / PlannedMode / TurnPlan.
    """
    if isinstance(plan_obj, TurnPlan):
        return plan_obj.to_dict()
    if isinstance(plan_obj, dict):
        return dict(plan_obj)
    if hasattr(plan_obj, "to_dict"):
        try:
            return dict(plan_obj.to_dict())
        except Exception:
            return {}
    return {}


def _safe_recent_list(dialogue_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    recent = list((dialogue_state or {}).get("recent_turns", []) or [])
    return [x for x in recent if isinstance(x, dict)]


def _select_recent_user_prompts(dialogue_state: Dict[str, Any], limit: int = 3) -> List[str]:
    recent = _safe_recent_list(dialogue_state)
    out: List[str] = []
    for row in reversed(recent):
        if row.get("role") == "user":
            txt = str(row.get("text") or "").strip()
            if txt:
                out.append(txt)
            if len(out) >= limit:
                break
    out.reverse()
    return out


def _last_assistant_response(dialogue_state: Dict[str, Any]) -> Optional[str]:
    recent = _safe_recent_list(dialogue_state)
    for row in reversed(recent):
        if row.get("role") == "assistant":
            txt = str(row.get("text") or "").strip()
            return txt or None
    return None


# ------------------------------------------------------------------
# Phase D Sprint 2 helpers (read-only learning context)
# ------------------------------------------------------------------

def _normalize_learning_view_dict(view: Any) -> Optional[Dict[str, Any]]:
    """
    Normalize learning context view objects to dict safely.
    Supports dict / contract object with to_dict().
    """
    if view is None:
        return None
    if isinstance(view, dict):
        return dict(view)
    if hasattr(view, "to_dict"):
        try:
            return dict(view.to_dict())
        except Exception:
            return None
    return None


def _fallback_learning_context_view_from_runtime(
    learning_runtime: Any,
    *,
    include_debug: bool,
) -> Optional[Dict[str, Any]]:
    """
    Backward-compatible fallback when Sprint 2 typed get_learning_context_view()
    is not available yet. Uses Sprint 1 summary/weakness APIs if present.
    """
    if learning_runtime is None:
        return None

    summary: Dict[str, Any] = {}
    weaknesses: List[Dict[str, Any]] = []

    try:
        if hasattr(learning_runtime, "build_summary"):
            raw_summary = learning_runtime.build_summary()
            if isinstance(raw_summary, dict):
                summary = dict(raw_summary)
    except Exception:
        summary = {}

    try:
        if hasattr(learning_runtime, "get_top_weakness_signals"):
            raw_w = learning_runtime.get_top_weakness_signals(limit=3)
            if isinstance(raw_w, list):
                weaknesses = [w for w in raw_w if isinstance(w, dict)]
        elif hasattr(learning_runtime, "load_weakness_signals"):
            raw_w = learning_runtime.load_weakness_signals()
            if isinstance(raw_w, list):
                weaknesses = [w for w in raw_w if isinstance(w, dict)][:3]
    except Exception:
        weaknesses = []

    if not summary and not weaknesses and not include_debug:
        return None

    return {
        "schema_version": "aion.learning_context_view.v1",
        "writable": False,
        "summary": summary,
        "weakness_hints": weaknesses,
        "cautions": [
            {
                "kind": "read_only_context",
                "message": "Learning context is advisory only in Phase D Sprint 2.",
            }
        ],
    }


def _compact_learning_context_summary(view: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Compact summary for metadata/debug to avoid bloating payloads.
    """
    if not isinstance(view, dict):
        return None

    summary = dict(view.get("summary") or {})
    weakness_hints = list(view.get("weakness_hints") or [])
    cautions = list(view.get("cautions") or [])

    return {
        "schema_version": str(view.get("schema_version") or "aion.learning_context_view.v1"),
        "writable": bool(view.get("writable", False)),
        "summary": {
            "total_events": _safe_int(summary.get("total_events"), 0),
            "ok_count": _safe_int(summary.get("ok_count"), 0),
            "fail_count": _safe_int(summary.get("fail_count"), 0),
            "avg_reward_score": _safe_float(summary.get("avg_reward_score"), 0.0),
            "avg_process_score": _safe_float(summary.get("avg_process_score"), 0.0),
            "avg_outcome_score": _safe_float(summary.get("avg_outcome_score"), 0.0),
        },
        "weakness_hints_count": len(weakness_hints),
        "cautions_count": len(cautions),
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
    """
    turn_count = int((dialogue_state or {}).get("turn_count") or 0)
    topic = str((dialogue_state or {}).get("topic") or "AION roadmap")

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
    topic = str((dialogue_state or {}).get("topic") or "AION roadmap")
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


def _build_status_response(*, dialogue_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Local deterministic answer for broad status/progress questions.
    """
    topic = str((dialogue_state or {}).get("topic") or "current topic")
    turn_count = int((dialogue_state or {}).get("turn_count") or 0)
    commitments = list((dialogue_state or {}).get("commitments", []) or [])
    unresolved = list((dialogue_state or {}).get("unresolved", []) or [])

    msg = (
        f"Current AION conversation status ({topic}): "
        f"stateful orchestration is active with {turn_count} stored turn events. "
        "Mode planning (answer/clarify/summarize/reflect) is integrated, and topic-specific local handlers are active for roadmap follow-ups. "
        "The default composer path remains grounded and deterministic, with optional teaching-apply enrichment. "
        f"Tracked commitments={len(commitments)}; unresolved items={len(unresolved)}."
    )
    return {
        "ok": True,
        "origin": "aion_conversation_orchestrator",
        "response": msg,
        "confidence": 0.76,
        "mode": "answer",
        "metadata": {
            "phase": "phase_b_sprint1_5_local_handlers",
            "planner_reason": "status_progress_question",
            "local_mode_handler": True,
            "local_handler": "status_progress",
        },
        "debug": {},
    }


def _build_roadmap_why_order_response(
    *,
    dialogue_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Local deterministic answer for contextual why/order follow-ups after roadmap answers.
    """
    topic = str((dialogue_state or {}).get("topic") or "AION roadmap")
    msg = (
        f"The order in {topic} is chosen for fastest perceived intelligence gain with lowest integration risk: "
        "first improve the response behavior users feel immediately (composer naturalness and follow-up handling), "
        "then strengthen response planning/context routing so follow-ups become reliably topic-specific, "
        "and only then add heavier execution infrastructure (skill registry/adapter), which is high leverage but adds more surface area and integration complexity. "
        "This sequence improves conversational quality first, preserves determinism, and reduces regression risk while the stack is still stabilizing."
    )
    return {
        "ok": True,
        "origin": "aion_conversation_orchestrator",
        "response": msg,
        "confidence": 0.77,
        "mode": "answer",
        "metadata": {
            "phase": "phase_b_sprint1_5_local_handlers",
            "planner_reason": "contextual_why_followup_with_continuity",
            "local_mode_handler": True,
            "local_handler": "roadmap_why_order_reasoning",
        },
        "debug": {},
    }


def _build_contextual_elaboration_response(
    *,
    dialogue_state: Dict[str, Any],
    topic: Optional[str],
) -> Dict[str, Any]:
    """
    Local deterministic elaboration for prompts like:
      - explain that in more detail
      - expand on that
      - tell me more
    Focused on roadmap topic for now (high-value path).
    """
    topic_s = str(topic or (dialogue_state or {}).get("topic") or "AION roadmap")

    if _is_roadmap_topic(topic_s):
        msg = (
            f"More detail on {topic_s}: the near-term focus is improving answer quality before adding deeper capabilities. "
            "That means (1) composer naturalness so KS facts/goals/unresolved are expressed as coherent grounded prose, "
            "(2) stronger follow-up handling so short/contextual prompts continue the active topic instead of falling into generic clarifications, "
            "(3) richer turn-context routing so planner/composer receive continuity signals (topic context, recent prompts, last assistant response), "
            "and then (4) skill execution infrastructure so AION can perform actions reliably after the conversational layer is stable. "
            "This ordering prioritizes user-visible intelligence gains while keeping the system deterministic and easier to regression-test."
        )
        local_handler = "roadmap_contextual_elaboration"
    else:
        msg = (
            f"More detail on {topic_s}: the immediate goal is to expand the current answer using the active session context, "
            "preserve grounding/determinism, and avoid resetting the topic. The next step is to deepen planner + context routing so "
            "follow-up elaboration requests are handled consistently across topics."
        )
        local_handler = "generic_contextual_elaboration"

    return {
        "ok": True,
        "origin": "aion_conversation_orchestrator",
        "response": msg,
        "confidence": 0.73,
        "mode": "answer",
        "metadata": {
            "phase": "phase_b_sprint1_5_local_handlers",
            "planner_reason": "contextual_elaboration_followup",
            "local_mode_handler": True,
            "local_handler": local_handler,
        },
        "debug": {},
    }


def _should_try_skill_mode(user_text: str, topic: Optional[str], plan: Dict[str, Any]) -> bool:
    """
    Phase C / Trading Sprint 2 deterministic skill trigger.
    Keep planner contract unchanged; opportunistically run skills for obvious prompts.
    """
    t = _norm(user_text)

    # Existing explicit triggers
    if any(p in t for p in ["run skill", "use skill", "execute skill", "call skill"]):
        return True

    # Existing roadmap route
    if "priorit" in t and _is_roadmap_topic(topic):
        return True

    # Trading Sprint 2/2.1/3 triggers (kept intentionally specific to avoid false positives)
    trading_triggers = [
        "forex curriculum",
        "trading curriculum",
        "show curriculum",
        "list trading strategies",
        "trading strategies",
        "strategy list",
        "list strategies",
        "dmip",
        "market briefing",
        "daily market intelligence",
        "validate trade risk",
        "check trade risk",
        "risk check trade",
        "validate risk",
        "risk validation",
        "update decision influence weights",
        "decision influence weights",
        "decision influence dry run",
        "update influence weights",
        "show decision influence weights",
        "show influence weights",
        # NOTE: intentionally NOT adding broad "show weights"
    ]
    if any(p in t for p in trading_triggers):
        return True

    # Decision influence command verbs + qualifiers (more precise than broad trigger strings)
    # Supports:
    # - increase liquidity sweep influence by 0.05 dry run
    # - set news risk filter to 0.08
    # - decrease trend alignment by 0.02 apply live
    if (
        any(v in t for v in ["increase ", "raise ", "decrease ", "lower ", "reduce ", "set "])
        and (
            "influence" in t
            or "decision influence" in t
            or "influence weights" in t
            or any(
                k in t
                for k in [
                    "liquidity sweep",
                    "news risk filter",
                    "session bias",
                    "market structure",
                    "order flow",
                    "volatility regime",
                    "trend alignment",
                ]
            )
        )
    ):
        return True

    # Also allow common direct strategy lookups even without "list"
    if "strategy" in t and any(
        k in t
        for k in [
            "tier 1", "tier1",
            "tier 2", "tier2",
            "tier 3", "tier3",
            "tier 4", "tier4",
            "tier 5", "tier5",
            "smc", "macro", "swing",
        ]
    ):
        return True

    return False


def _build_skill_request_for_turn(
    *,
    user_text: str,
    topic: Optional[str],
    session_id: str,
    turn_id: str,
) -> Optional[SkillRunRequest]:
    t = _norm(user_text)

    # ------------------------------------------------------------
    # Existing explicit skill call: "run skill echo hello there"
    # ------------------------------------------------------------
    if t.startswith("run skill echo ") or t.startswith("use skill echo "):
        raw = user_text.strip()
        parts = raw.split()
        try:
            i = [p.lower() for p in parts].index("echo")
            echo_text = " ".join(parts[i + 1 :]).strip()
        except Exception:
            echo_text = ""
        return SkillRunRequest(
            skill_id="skill.echo_text",
            inputs={"text": echo_text},
            session_id=session_id,
            turn_id=turn_id,
            metadata={"route": "explicit_echo_skill"},
        ).validate()

    # ------------------------------------------------------------
    # Existing roadmap prioritization route
    # ------------------------------------------------------------
    if "priorit" in t and _is_roadmap_topic(topic):
        return SkillRunRequest(
            skill_id="skill.aion_roadmap_priority",
            inputs={"topic": str(topic or "AION roadmap")},
            session_id=session_id,
            turn_id=turn_id,
            metadata={"route": "roadmap_priority_skill"},
        ).validate()

    # ------------------------------------------------------------
    # Trading Sprint 2 / 2.1 / 3 routes (read-only + safe transform)
    # ------------------------------------------------------------

    # 1) Curriculum
    if any(p in t for p in ["forex curriculum", "trading curriculum", "show curriculum"]):
        return SkillRunRequest(
            skill_id="skill.trading_get_curriculum",
            inputs={},
            session_id=session_id,
            turn_id=turn_id,
            metadata={"route": "trading_curriculum_skill"},
        ).validate()

    # 2) Strategy list
    # Keep stricter so "show strategy tier 3" does NOT get swallowed by list route.
    if any(
        p in t
        for p in [
            "list trading strategies",
            "strategy list",
            "list strategies",
            "show all strategies",
            "all trading strategies",
        ]
    ):
        return SkillRunRequest(
            skill_id="skill.trading_list_strategies",
            inputs={},
            session_id=session_id,
            turn_id=turn_id,
            metadata={"route": "trading_list_strategies_skill"},
        ).validate()

    # 3) Single strategy spec (simple keyword parsing)
    # Supported examples:
    # - "show strategy tier 3"
    # - "get strategy tier3"
    # - "smc intraday strategy"
    strategy_tier = None
    if "tier 1" in t or "tier1" in t or "order flow sniping" in t or "orderflow sniping" in t:
        strategy_tier = "tier1_order_flow_sniping"
    elif "tier 2" in t or "tier2" in t or "opening range" in t or "momentum" in t:
        strategy_tier = "tier2_momentum_orb"
    elif "tier 3" in t or "tier3" in t or "smc" in t:
        strategy_tier = "tier3_smc_intraday"
    elif "tier 4" in t or "tier4" in t or "swing" in t:
        strategy_tier = "tier4_swing"
    elif "tier 5" in t or "tier5" in t or "macro" in t:
        strategy_tier = "tier5_macro_positioning"

    if strategy_tier and ("strategy" in t or "tier" in t or "smc" in t or "macro" in t):
        return SkillRunRequest(
            skill_id="skill.trading_get_strategy",
            inputs={"strategy_tier": strategy_tier},
            session_id=session_id,
            turn_id=turn_id,
            metadata={"route": "trading_get_strategy_skill", "strategy_tier": strategy_tier},
        ).validate()

    # 4) DMIP checkpoint (default pre_market)
    if "dmip" in t or "market briefing" in t or "daily market intelligence" in t:
        checkpoint = "pre_market"
        if "london" in t and ("open" in t or "pre-london" in t):
            checkpoint = "london_open"
        elif "mid london" in t or "mid-london" in t:
            checkpoint = "mid_london"
        elif "new york" in t or "ny open" in t or "us open" in t:
            checkpoint = "new_york_open"
        elif "asia" in t or "tokyo" in t:
            checkpoint = "asia_open"
        elif "end of day" in t or "eod" in t or "debrief" in t:
            # keep aligned to current dmip runtime checkpoint names
            checkpoint = "eod_debrief"

        return SkillRunRequest(
            skill_id="skill.trading_run_dmip_checkpoint",
            inputs={
                "checkpoint": checkpoint,
                "market_snapshot": {},
                "llm_consultation": {},
            },
            session_id=session_id,
            turn_id=turn_id,
            metadata={"route": "trading_dmip_checkpoint_skill", "checkpoint": checkpoint},
        ).validate()

    # 5) Risk validation (parser + safe defaults; hard-locked paper mode)
    if any(
        p in t
        for p in [
            "validate trade risk",
            "check trade risk",
            "risk check trade",
            "validate risk",
            "risk validation",
        ]
    ):
        parsed = _parse_trade_risk_request_from_text(user_text)

        direction = str(parsed.get("direction") or "BUY").upper()
        if direction not in {"BUY", "SELL"}:
            direction = "BUY"

        pair = str(parsed.get("pair") or "EUR/USD")

        # Defaults remain paper-first and safe
        entry = float(parsed.get("entry") if parsed.get("entry") is not None else 1.1000)

        # Direction-aware fallbacks if explicit SL/TP not supplied
        stop_loss_default = 1.0950 if direction == "BUY" else 1.1050
        take_profit_default = 1.1100 if direction == "BUY" else 1.0900

        stop_loss = float(parsed.get("stop_loss") if parsed.get("stop_loss") is not None else stop_loss_default)
        take_profit = float(parsed.get("take_profit") if parsed.get("take_profit") is not None else take_profit_default)

        account_equity = float(parsed.get("account_equity") if parsed.get("account_equity") is not None else 10000.0)
        risk_pct = float(parsed.get("risk_pct") if parsed.get("risk_pct") is not None else 1.0)
        pip_value = float(parsed.get("pip_value") if parsed.get("pip_value") is not None else 10.0)
        stop_pips = float(parsed.get("stop_pips") if parsed.get("stop_pips") is not None else 50.0)

        strategy_tier = str(parsed.get("strategy_tier") or "tier3_smc_intraday")

        parsed_fields = sorted(list(parsed.keys()))

        return SkillRunRequest(
            skill_id="skill.trading_validate_risk",
            inputs={
                "pair": pair,
                "strategy_tier": strategy_tier,
                "direction": direction,
                "account_mode": "paper",  # hard-locked in Sprint 2.1
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "account_equity": account_equity,
                "risk_pct": risk_pct,
                "pip_value": pip_value,
                "stop_pips": stop_pips,
                "thesis": "User-requested risk validation (parsed values + safe defaults).",
                "setup_tags": ["orchestrator_sprint2_1_parser"],
                "metadata": {
                    "source": "conversation_orchestrator",
                    "parser_mode": "regex_partial_with_defaults",
                    "parsed_fields": parsed_fields,
                },
                "session_stats": {
                    "losing_trades_today": 0,
                    "daily_risk_used_pct": 0.0,
                },
                "account_stats": {
                    "weekly_risk_used_pct": 0.0,
                    "drawdown_pct": 0.0,
                },
            },
            session_id=session_id,
            turn_id=turn_id,
            metadata={
                "route": "trading_validate_risk_skill",
                "parser_mode": "regex_partial_with_defaults",
                "parsed_fields": parsed_fields,
            },
        ).validate()

    # 6) Sprint 3 governed decision influence read/update (parser -> structured patch)
    if any(
        p in t
        for p in [
            "update decision influence weights",
            "decision influence weights",
            "decision influence dry run",
            "update influence weights",
            "show decision influence weights",
            "show influence weights",
            "show weights",
            "increase ",
            "decrease ",
            "set ",
        ]
    ):
        parsed = _parse_decision_influence_request_from_text(user_text)

        intent = str(parsed.get("intent") or "update").strip().lower()   # "show" | "update"
        dry_run = bool(parsed.get("dry_run", True))                      # hard-safe default
        patch = dict(parsed.get("patch") or {})
        scope = dict(parsed.get("scope") or {})
        warnings = list(parsed.get("warnings") or [])
        reason = str(parsed.get("reason") or "").strip() or (
            "User-requested decision influence weights read/update via orchestrator route."
        )

        return SkillRunRequest(
            skill_id="skill.trading_update_decision_influence_weights",
            inputs={
                "action": intent,     # <-- skill expects action, not intent
                "dry_run": dry_run,
                "patch": patch,       # {} for show, {"ops":[...]} for update
                "scope": scope,
                "reason": reason,
                "source": "conversation_orchestrator",
            },
            session_id=session_id,
            turn_id=turn_id,
            metadata={
                "route": "trading_update_decision_influence_weights_skill",
                "action": intent,
                "dry_run": dry_run,
                "parsed_ops_count": len(list((patch or {}).get("ops") or [])),
                "parsed_ops": list((patch or {}).get("ops") or []),
                "parser_warnings": warnings,
                "parser_mode": "regex_v2_decision_influence_request",
            },
        ).validate()

    return None


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
    planner_reason = str(plan.get("reason") or "")

    # ------------------------------------------------------------------
    # Local ANSWER handlers (high-leverage, topic-specific follow-ups)
    # ------------------------------------------------------------------
    if mode == "answer":
        # Roadmap short follow-up: "and then what" / "what next" etc.
        if (
            planner_reason == "short_followup_with_context"
            and _is_roadmap_topic(topic)
            and _is_short_next_followup(user_text)
        ):
            return _build_roadmap_followup_response(
                dialogue_state=dialogue_state,
                apply_teaching=bool(apply_teaching),
            )

        # Contextual elaboration follow-up (new)
        if planner_reason == "contextual_elaboration_followup" or _is_contextual_elaboration_followup(user_text):
            return _build_contextual_elaboration_response(
                dialogue_state=dialogue_state,
                topic=topic,
            )

        # Contextual why/order follow-up with continuity (new)
        if planner_reason in {
            "contextual_why_followup_with_continuity",
            "contextual_why_followup_overrides_unresolved_clarify",
        } and (_is_roadmap_topic(topic) or _is_contextual_why_followup(user_text)):
            return _build_roadmap_why_order_response(dialogue_state=dialogue_state)

        # Roadmap prioritization prompt
        if _is_roadmap_topic(topic) and (
            "what should we build first" in text_n
            or ("feel more intelligent" in text_n and "build first" in text_n)
        ):
            return _build_prioritization_response(dialogue_state=dialogue_state)

        # Broad status/progress question (context aware)
        if any(p in text_n for p in ["where are we at", "status", "progress", "where we are"]):
            return _build_status_response(dialogue_state=dialogue_state)

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
            "debug": {"planner": plan},
        }

    # ------------------------------------------------------------------
    # Local SUMMARIZE handler
    # ------------------------------------------------------------------
    if mode == "summarize":
        recent = _safe_recent_list(dialogue_state)
        if not recent:
            summary = "No conversation history is stored yet for this session."
        else:
            last_items = recent[-8:]
            user_msgs = [str(x.get("text", "")) for x in last_items if x.get("role") == "user"]
            topic_s = str((dialogue_state or {}).get("topic") or "current topic")
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
            "debug": {"planner": plan},
        }

    # ------------------------------------------------------------------
    # Local REFLECT handler
    # ------------------------------------------------------------------
    if mode == "reflect":
        topic_s = str((dialogue_state or {}).get("topic") or "unknown")
        turn_count = int((dialogue_state or {}).get("turn_count") or 0)
        unresolved = list((dialogue_state or {}).get("unresolved", []) or [])
        msg = (
            f"AION reflection: current dialogue topic is {topic_s}; "
            f"stored turn count={turn_count}; unresolved items={len(unresolved)}. "
            "Next improvement target is stronger context-aware response planning and topic-specific follow-up answers."
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
            "debug": {"planner": plan},
        }


    return None

def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _extract_top_violations_from_trading_capture_summary(summary: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Accepts multiple possible summary shapes and returns a normalized top-violations list.
    Keeps this non-breaking while learning_capture runtime evolves.
    """
    s = _safe_dict(summary)

    # Preferred explicit key
    top = s.get("top_violations")
    if isinstance(top, list):
        out: List[Dict[str, Any]] = []
        for row in top[:limit]:
            if isinstance(row, dict):
                out.append(
                    {
                        "violation": str(row.get("violation") or row.get("name") or "unknown"),
                        "count": _safe_int(row.get("count"), 0),
                    }
                )
        return out

    # Alternate shape: violations_count map / by_violation map
    for key in ["violations_count", "by_violation", "violation_counts"]:
        raw = s.get(key)
        if isinstance(raw, dict):
            rows = [{"violation": str(k), "count": _safe_int(v, 0)} for k, v in raw.items()]
            rows.sort(key=lambda x: (-x["count"], x["violation"]))
            return rows[:limit]

    return []


def _compact_trading_journal_summary(summary: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Compact journal summary for orchestrator metadata/debug.
    Supports evolving learning_capture runtime summary shapes.
    """
    if not isinstance(summary, dict):
        return None

    s = dict(summary)

    total_dmip = _safe_int(
        s.get("total_dmip_captures", s.get("dmip_count", s.get("trading_dmip_checkpoint_count", 0))),
        0,
    )
    total_risk = _safe_int(
        s.get("total_risk_validations", s.get("risk_validation_count", s.get("trading_risk_validation_count", 0))),
        0,
    )

    total_events = _safe_int(
        s.get("total_events", total_dmip + total_risk),
        total_dmip + total_risk,
    )

    risk_fail_count = _safe_int(
        s.get("risk_fail_count", s.get("risk_validation_fail_count", 0)),
        0,
    )

    # If runtime already gives a fail rate, respect it; else infer from risk validations only.
    fail_rate = s.get("fail_rate")
    if fail_rate is None:
        fail_rate = (risk_fail_count / total_risk) if total_risk > 0 else 0.0
    fail_rate = _safe_float(fail_rate, 0.0)

    return {
        "schema_version": str(s.get("schema_version") or "aion.trading_learning_journal_summary.v1"),
        "total_events": total_events,
        "total_dmip_captures": total_dmip,
        "total_risk_validations": total_risk,
        "risk_fail_count": risk_fail_count,
        "fail_rate": fail_rate,
        "top_violations": _extract_top_violations_from_trading_capture_summary(s, limit=5),
    }


class ConversationOrchestrator:
    """
    Phase B Sprint 1 + Sprint 1.5 + Phase D Sprint 2 orchestrator:
    - loads dialogue state
    - assembles turn context
    - plans response mode (answer/clarify/summarize/reflect)
    - local deterministic handlers for high-value follow-ups
      (roadmap next-step, prioritization, status, contextual elaboration/why, summarize, clarify, reflect)
    - optional skill runtime path (Phase C)
    - read-only learning context injection into debug/trace + metadata summary (Phase D Sprint 2)
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

        # Phase C Sprint 1 skill runtime (safe, in-memory)
        register_builtin_demo_skills(get_global_skill_registry())
        self.skill_adapter = SkillExecutionAdapter()

        # Phase D Sprint 2 learning runtime (read-only advisory context)
        self.learning_runtime = get_aion_learning_runtime()

        # Trading Sprint 3.1: paper-only trading learning/journal capture runtime (non-breaking)
        try:
            self.trading_learning_capture = get_trading_learning_capture_runtime()
        except Exception:
            self.trading_learning_capture = None

    def _build_learning_context_view(self, *, include_debug: bool) -> Optional[Dict[str, Any]]:
        """
        Phase D Sprint 2 read-only learning context for orchestrator visibility.
        Forward-compatible with Sprint 3 writable influence (same contract shape).
        """
        # Preferred Sprint 2 runtime API
        try:
            if hasattr(self.learning_runtime, "get_learning_context_view"):
                view_obj = self.learning_runtime.get_learning_context_view()
                view = _normalize_learning_view_dict(view_obj)
                if view is not None:
                    # Enforce Sprint 2 read-only semantics
                    view["writable"] = False
                    return view
        except Exception:
            pass

        # Backward-compatible fallback (Sprint 1 style summary/weakness APIs)
        return _fallback_learning_context_view_from_runtime(self.learning_runtime, include_debug=include_debug)

    def _capture_trading_dmip_event(
        self,
        *,
        session_id: str,
        turn_id: str,
        user_text: str,
        skill_req: Optional[Any],
        skill_out: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Sprint 3.1 journal capture for DMIP checkpoint skill results (paper-only).
        Non-breaking: supports multiple runtime method names / signatures.
        """
        runtime = getattr(self, "trading_learning_capture", None)
        if runtime is None or skill_out is None:
            return None

        outp = _safe_dict(getattr(skill_out, "output", None))
        req_dict = skill_req.to_dict() if (skill_req is not None and hasattr(skill_req, "to_dict")) else {}
        req_inputs = _safe_dict(req_dict.get("inputs"))

        checkpoint = str(outp.get("checkpoint") or req_inputs.get("checkpoint") or "unknown")

        # Bias extraction (support multiple output shapes)
        biases = {}
        for k in ["biases", "pair_biases", "market_biases"]:
            if isinstance(outp.get(k), dict):
                biases = dict(outp.get(k))
                break

        # Avoid/disagreement extraction
        avoid_flags: List[str] = []
        if isinstance(outp.get("avoid_flags"), list):
            avoid_flags = [str(x) for x in outp.get("avoid_flags") if x is not None]
        elif isinstance(outp.get("biases"), dict):
            # infer "AVOID" labels from bias map
            for pair, bias in dict(outp.get("biases") or {}).items():
                if str(bias).upper() == "AVOID":
                    avoid_flags.append(str(pair))

        # Record payload (journal event)
        event = {
            "event_type": "trading_dmip_checkpoint",
            "session_id": str(session_id),
            "turn_id": str(turn_id),
            "ok": bool(getattr(skill_out, "ok", False)),
            "skill_id": str(getattr(skill_out, "skill_id", "skill.trading_run_dmip_checkpoint")),
            "checkpoint": checkpoint,
            "biases": biases,
            "avoid_flags": avoid_flags,
            "user_text": str(user_text or ""),
            "metadata": {
                "route_metadata": _safe_dict(req_dict.get("metadata")),
                "skill_metadata": _safe_dict(getattr(skill_out, "metadata", None)),
            },
        }

        # Try common runtime APIs (non-breaking / introspective)
        try:
            if hasattr(runtime, "capture_dmip_event"):
                res = runtime.capture_dmip_event(event)
            elif hasattr(runtime, "record_dmip_event"):
                res = runtime.record_dmip_event(event)
            elif hasattr(runtime, "capture_event"):
                res = runtime.capture_event(event)
            elif hasattr(runtime, "record_event"):
                res = runtime.record_event(event)
            else:
                return {"ok": False, "reason": "no_supported_capture_method", "event_type": "trading_dmip_checkpoint"}
        except TypeError:
            # fallback signature variants
            try:
                if hasattr(runtime, "capture_dmip_event"):
                    res = runtime.capture_dmip_event(
                        checkpoint=checkpoint,
                        session_id=str(session_id),
                        turn_id=str(turn_id),
                        ok=bool(getattr(skill_out, "ok", False)),
                        biases=biases,
                        avoid_flags=avoid_flags,
                        metadata=event["metadata"],
                    )
                elif hasattr(runtime, "record_dmip_event"):
                    res = runtime.record_dmip_event(
                        checkpoint=checkpoint,
                        session_id=str(session_id),
                        turn_id=str(turn_id),
                        ok=bool(getattr(skill_out, "ok", False)),
                        biases=biases,
                        avoid_flags=avoid_flags,
                        metadata=event["metadata"],
                    )
                else:
                    return {"ok": False, "reason": "unsupported_dmip_signature", "event_type": "trading_dmip_checkpoint"}
            except Exception as e:
                return {"ok": False, "reason": "capture_exception", "error": str(e), "event_type": "trading_dmip_checkpoint"}
        except Exception as e:
            return {"ok": False, "reason": "capture_exception", "error": str(e), "event_type": "trading_dmip_checkpoint"}

        if isinstance(res, dict):
            return res
        if hasattr(res, "to_dict"):
            try:
                return dict(res.to_dict())
            except Exception:
                pass
        return {"ok": True, "event_type": "trading_dmip_checkpoint"}


    def _capture_trading_risk_validation_event(
        self,
        *,
        session_id: str,
        turn_id: str,
        user_text: str,
        skill_req: Optional[Any],
        skill_out: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Sprint 3.1 journal capture for trade risk validation results (paper-only).
        Non-breaking: supports multiple runtime method names / signatures.
        """
        runtime = getattr(self, "trading_learning_capture", None)
        if runtime is None or skill_out is None:
            return None

        outp = _safe_dict(getattr(skill_out, "output", None))
        result = _safe_dict(outp.get("result"))
        proposal = _safe_dict(outp.get("proposal"))

        req_dict = skill_req.to_dict() if (skill_req is not None and hasattr(skill_req, "to_dict")) else {}
        req_meta = _safe_dict(req_dict.get("metadata"))
        req_inputs = _safe_dict(req_dict.get("inputs"))

        violations = [str(v) for v in _safe_list(result.get("violations")) if v is not None]

        # Basic RR inference if not explicitly present
        rr_value = result.get("rr")
        if rr_value is None:
            try:
                entry = float(proposal.get("entry"))
                sl = float(proposal.get("stop_loss"))
                tp = float(proposal.get("take_profit"))
                risk_dist = abs(entry - sl)
                reward_dist = abs(tp - entry)
                rr_value = (reward_dist / risk_dist) if risk_dist > 0 else None
            except Exception:
                rr_value = None

        event = {
            "event_type": "trading_risk_validation",
            "session_id": str(session_id),
            "turn_id": str(turn_id),
            "ok": bool(result.get("ok", outp.get("ok", getattr(skill_out, "ok", False)))),
            "skill_id": str(getattr(skill_out, "skill_id", "skill.trading_validate_risk")),
            "pair": str(proposal.get("pair") or req_inputs.get("pair") or ""),
            "direction": str(proposal.get("direction") or req_inputs.get("direction") or ""),
            "strategy_tier": str(proposal.get("strategy_tier") or req_inputs.get("strategy_tier") or ""),
            "account_mode": str(proposal.get("account_mode") or req_inputs.get("account_mode") or "paper"),
            "risk_pct": proposal.get("risk_pct", req_inputs.get("risk_pct")),
            "rr": rr_value,
            "violations": violations,
            "user_text": str(user_text or ""),
            "metadata": {
                "route_metadata": req_meta,
                "skill_metadata": _safe_dict(getattr(skill_out, "metadata", None)),
                "parsed_fields": _safe_list(req_meta.get("parsed_fields")),
            },
        }

        try:
            if hasattr(runtime, "capture_risk_validation_event"):
                res = runtime.capture_risk_validation_event(event)
            elif hasattr(runtime, "record_risk_validation_event"):
                res = runtime.record_risk_validation_event(event)
            elif hasattr(runtime, "capture_event"):
                res = runtime.capture_event(event)
            elif hasattr(runtime, "record_event"):
                res = runtime.record_event(event)
            else:
                return {"ok": False, "reason": "no_supported_capture_method", "event_type": "trading_risk_validation"}
        except TypeError:
            try:
                if hasattr(runtime, "capture_risk_validation_event"):
                    res = runtime.capture_risk_validation_event(
                        session_id=str(session_id),
                        turn_id=str(turn_id),
                        ok=bool(event["ok"]),
                        pair=event["pair"],
                        direction=event["direction"],
                        strategy_tier=event["strategy_tier"],
                        account_mode=event["account_mode"],
                        risk_pct=event["risk_pct"],
                        rr=event["rr"],
                        violations=violations,
                        metadata=event["metadata"],
                    )
                elif hasattr(runtime, "record_risk_validation_event"):
                    res = runtime.record_risk_validation_event(
                        session_id=str(session_id),
                        turn_id=str(turn_id),
                        ok=bool(event["ok"]),
                        pair=event["pair"],
                        direction=event["direction"],
                        strategy_tier=event["strategy_tier"],
                        account_mode=event["account_mode"],
                        risk_pct=event["risk_pct"],
                        rr=event["rr"],
                        violations=violations,
                        metadata=event["metadata"],
                    )
                else:
                    return {"ok": False, "reason": "unsupported_risk_signature", "event_type": "trading_risk_validation"}
            except Exception as e:
                return {"ok": False, "reason": "capture_exception", "error": str(e), "event_type": "trading_risk_validation"}
        except Exception as e:
            return {"ok": False, "reason": "capture_exception", "error": str(e), "event_type": "trading_risk_validation"}

        if isinstance(res, dict):
            return res
        if hasattr(res, "to_dict"):
            try:
                return dict(res.to_dict())
            except Exception:
                pass
        return {"ok": True, "event_type": "trading_risk_validation"}


    def _capture_trading_skill_event_if_applicable(
        self,
        *,
        session_id: str,
        turn_id: str,
        user_text: str,
        skill_req: Optional[Any],
        skill_out: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatches Sprint 3.1 journal capture hooks for supported trading skills.
        Non-breaking and observational only.
        """
        if skill_out is None or not bool(getattr(skill_out, "ok", False)):
            return None

        sid = str(getattr(skill_out, "skill_id", "") or "")

        if sid == "skill.trading_run_dmip_checkpoint":
            return self._capture_trading_dmip_event(
                session_id=session_id,
                turn_id=turn_id,
                user_text=user_text,
                skill_req=skill_req,
                skill_out=skill_out,
            )

        if sid == "skill.trading_validate_risk":
            return self._capture_trading_risk_validation_event(
                session_id=session_id,
                turn_id=turn_id,
                user_text=user_text,
                skill_req=skill_req,
                skill_out=skill_out,
            )

        return None


    def _get_trading_journal_summary(self) -> Optional[Dict[str, Any]]:
        """
        Returns a compact trading learning/journal summary for debug metadata and meetings.
        Non-breaking against evolving runtime API names.
        """
        runtime = getattr(self, "trading_learning_capture", None)
        if runtime is None:
            return None

        raw = None
        try:
            if hasattr(runtime, "build_summary"):
                raw = runtime.build_summary()
            elif hasattr(runtime, "get_summary"):
                raw = runtime.get_summary()
            elif hasattr(runtime, "summary"):
                raw = runtime.summary()
        except Exception:
            raw = None

        if raw is None:
            return None
        if isinstance(raw, dict):
            return _compact_trading_journal_summary(raw)
        if hasattr(raw, "to_dict"):
            try:
                return _compact_trading_journal_summary(dict(raw.to_dict()))
            except Exception:
                return None
        return None

    def _capture_trading_skill_learning_event(
        self,
        *,
        session_id: str,
        turn_id: str,
        skill_out: Any,
    ) -> Optional[Dict[str, Any]]:
        """
        Sprint 3: capture paper-only trading skill outcomes as learning events.
        Non-breaking: swallow errors and return None on failure.
        """
        try:
            if skill_out is None or not getattr(skill_out, "skill_id", None):
                return None

            skill_id = str(getattr(skill_out, "skill_id") or "")
            output = dict(getattr(skill_out, "output", {}) or {})

            # DMIP checkpoint capture
            if skill_id == "skill.trading_run_dmip_checkpoint":
                return self.trading_learning_capture.log_dmip_checkpoint_event(
                    session_id=session_id,
                    turn_id=turn_id,
                    skill_id=skill_id,
                    skill_output=output,
                )

            # Risk validation capture
            if skill_id == "skill.trading_validate_risk":
                return self.trading_learning_capture.log_risk_validation_event(
                    session_id=session_id,
                    turn_id=turn_id,
                    skill_id=skill_id,
                    skill_output=output,
                )

            return None
        except Exception:
            return None

    def handle_turn_packet(self, packet: "TurnPacket") -> "TurnResult":
        """
        Contract-based wrapper around handle_turn().
        Keeps the existing dict response path intact while enabling typed tests/scripts.
        """
        # local import avoids hard dependency/circular issues at module import time
        from backend.modules.aion_conversation.contracts import TurnPacket, TurnResult

        if not isinstance(packet, TurnPacket):
            # tolerate dict input for convenience in tests
            packet = TurnPacket.from_dict(packet)
        packet.validate()

        out = self.handle_turn(
            session_id=packet.session_id,
            user_text=packet.user_text,
            apply_teaching=packet.apply_teaching,
            include_debug=packet.include_debug,
            include_metadata=packet.include_metadata,
        )
        return TurnResult.from_dict(out).validate()


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
        state_before = state.to_dict()

        # Assemble from current state BEFORE appending the new user turn
        turn_ctx_raw = build_turn_context(user_text=user_text, dialogue_state=state_before)
        turn_ctx = _turn_ctx_as_dict(turn_ctx_raw)

        # Prefer planner emitted by turn_context_assembler if present (keeps one source of truth),
        # otherwise compute locally as fallback.
        prebuilt_planner = turn_ctx.get("planner")
        prebuilt_plan_dict = _plan_as_dict(prebuilt_planner)

        if prebuilt_plan_dict.get("mode"):
            plan = prebuilt_plan_dict
            planned_mode = str(plan.get("mode") or "answer")
        else:
            plan_obj = _MODE_PLANNER.plan(
                user_text=user_text,
                dialogue_state=state_before,
                topic=str(turn_ctx.get("topic") or state.topic or ""),
                intent=str(turn_ctx.get("intent") or "answer"),
            )
            plan = _plan_as_dict(plan_obj)
            planned_mode = str(plan.get("mode") or "answer")

        # Override/normalize context mode with planner output for downstream consistency
        turn_ctx["response_mode"] = planned_mode
        turn_ctx["planner"] = plan

        # Phase D Sprint 2: read-only learning context (debug/trace + compact metadata summary)
        learning_context_view = self._build_learning_context_view(include_debug=include_debug)
        learning_context_summary = _compact_learning_context_summary(learning_context_view)

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

        # Use state AFTER user append for local handlers (summary/follow-up can see latest turn)
        state_after_user = state.to_dict()

        # ------------------------------------------------------------------
        # Phase C Sprint 1 / Trading Sprint 2+: optional skill route (non-breaking)
        # We do not replace planner mode yet; this is a deterministic side path.
        # ------------------------------------------------------------------
        topic_for_skill = str(turn_ctx.get("topic") or state.topic or "")
        skill_req = None
        skill_out = None

        # Trading Sprint 3 / 3.1 capture and journal summary (observational only)
        trading_capture_result = None
        trading_learning_event = None
        trading_journal_summary_before = None
        trading_journal_summary_after = None

        # Best-effort pre-capture journal summary (safe if helpers/runtime absent)
        try:
            if hasattr(self, "_get_trading_journal_summary"):
                trading_journal_summary_before = self._get_trading_journal_summary()
        except Exception:
            trading_journal_summary_before = None

        if _should_try_skill_mode(user_text=user_text, topic=topic_for_skill, plan=plan):
            skill_req = _build_skill_request_for_turn(
                user_text=user_text,
                topic=topic_for_skill,
                session_id=session_id,
                turn_id=turn_id,
            )
            if skill_req is not None:
                skill_out = self.skill_adapter.run(skill_req)

                # Sprint 3.1 trading journal capture (paper-only, non-breaking)
                try:
                    if hasattr(self, "_capture_trading_skill_event_if_applicable"):
                        trading_capture_result = self._capture_trading_skill_event_if_applicable(
                            session_id=session_id,
                            turn_id=turn_id,
                            user_text=user_text,
                            skill_req=skill_req,
                            skill_out=skill_out,
                        )
                except Exception:
                    trading_capture_result = None

                # Best-effort post-capture journal summary for debug / metadata / meetings
                try:
                    if hasattr(self, "_get_trading_journal_summary"):
                        trading_journal_summary_after = self._get_trading_journal_summary()
                except Exception:
                    trading_journal_summary_after = None

                # Sprint 3 paper-only learning capture (non-breaking)
                if skill_out is not None and bool(getattr(skill_out, "ok", False)):
                    try:
                        if hasattr(self, "_capture_trading_skill_learning_event"):
                            trading_learning_event = self._capture_trading_skill_learning_event(
                                session_id=session_id,
                                turn_id=turn_id,
                                skill_out=skill_out,
                            )
                    except Exception:
                        trading_learning_event = None

        # Skill-first local routing, then existing local handlers
        if skill_out is not None and bool(skill_out.ok):
            if skill_out.skill_id == "skill.trading_get_curriculum":
                outp = dict(skill_out.output or {})
                modules = list(outp.get("modules") or [])
                skill_summary = f"Forex curriculum loaded successfully. Modules: {len(modules)}."

            elif skill_out.skill_id == "skill.trading_list_strategies":
                outp = dict(skill_out.output or {})
                strategies = list(outp.get("strategies") or [])
                tiers = [
                    str(s.get("strategy_tier") or s.get("tier") or "?")
                    for s in strategies
                    if isinstance(s, dict)
                ]
                skill_summary = (
                    f"Trading strategies available ({len(strategies)}): "
                    f"{', '.join(tiers) if tiers else 'none'}."
                )

            elif skill_out.skill_id == "skill.trading_get_strategy":
                outp = dict(skill_out.output or {})
                if outp.get("ok"):
                    s = dict(outp.get("strategy") or {})
                    tier = str(s.get("strategy_tier") or s.get("tier") or "unknown")
                    title = str(s.get("title") or s.get("name") or "Strategy")
                    skill_summary = f"{title} ({tier}) loaded."
                else:
                    skill_summary = f"Trading strategy lookup failed: {outp.get('error') or 'unknown_error'}."

            elif skill_out.skill_id == "skill.trading_run_dmip_checkpoint":
                outp = dict(skill_out.output or {})
                checkpoint = str(outp.get("checkpoint") or "unknown")

                # Optional richer summary if bias_sheet exists
                bias_sheet = dict(outp.get("bias_sheet") or {})
                pair_bias = dict(bias_sheet.get("pair_bias") or outp.get("pair_bias") or {})
                avoid_pairs = [str(k) for k, v in pair_bias.items() if str(v).upper() == "AVOID"]
                if avoid_pairs:
                    skill_summary = (
                        f"DMIP checkpoint executed: {checkpoint}. "
                        f"AVOID bias on: {', '.join(sorted(avoid_pairs))}."
                    )
                else:
                    skill_summary = f"DMIP checkpoint executed: {checkpoint}."

            elif skill_out.skill_id == "skill.trading_validate_risk":
                outp = dict(skill_out.output or {})
                result = dict(outp.get("result") or {})
                # prefer top-level ok if present, fallback to nested result.ok
                ok_risk = bool(outp.get("ok", result.get("ok", False)))
                violations = list(result.get("violations") or [])
                skill_summary = (
                    f"Trade risk validation {'PASSED' if ok_risk else 'FAILED'}."
                    + (f" Violations: {', '.join(violations)}." if violations else "")
                )
            elif skill_out.skill_id == "skill.trading_update_decision_influence_weights":
                outp = dict(skill_out.output or {})
                dry_run = bool(outp.get("dry_run", True))
                applied = bool(outp.get("applied", False))
                action = str(outp.get("action") or "update")
                warnings = list(outp.get("warnings") or [])
                diff = list(outp.get("validated_diff") or [])
                snapshot_hash = str(outp.get("snapshot_hash") or outp.get("resulting_snapshot_hash") or "")

                if action == "show":
                    weight_count = len(dict(outp.get("weights") or {}))
                    skill_summary = (
                        f"Decision influence weights snapshot loaded ({weight_count} weights). "
                        f"Snapshot hash: {snapshot_hash or 'n/a'}."
                    )
                else:
                    skill_summary = (
                        f"Decision influence weights update {'DRY-RUN' if dry_run else 'EXECUTED'}; "
                        f"applied={applied}; diff_items={len(diff)}; warnings={len(warnings)}"
                        + (f"; snapshot_hash={snapshot_hash}." if snapshot_hash else ".")
                    )

            else:
                skill_summary = f"Skill execution completed ({skill_out.skill_id}) with output: {skill_out.output}"

            local_out = {
                "ok": True,
                "origin": "aion_conversation_orchestrator",
                "response": skill_summary,
                "confidence": 0.79,
                "mode": "answer",
                "metadata": {
                    "phase": "phase_c_sprint1_skill_runtime",
                    "planner_reason": plan.get("reason"),
                    "local_mode_handler": True,
                    "local_handler": "skill_execution_adapter",
                    "skill_run": skill_out.to_dict(),
                    # Trading Sprint 3 / 3.1 capture metadata
                    "trading_capture_result": trading_capture_result,
                    "trading_journal_summary_before": trading_journal_summary_before,
                    "trading_journal_summary": trading_journal_summary_after,
                    "trading_journal": trading_journal_summary_after or trading_journal_summary_before,
                    "trading_learning_event": trading_learning_event,
                },
                "debug": {
                    "planner": plan,
                    "skill_request": (skill_req.to_dict() if skill_req else None),
                    "skill_result": skill_out.to_dict(),
                    "trading_capture_result": trading_capture_result,
                    "trading_journal_summary_before": trading_journal_summary_before,
                    "trading_journal_summary_after": trading_journal_summary_after,
                    "trading_journal": trading_journal_summary_after or trading_journal_summary_before,
                    "trading_learning_event": trading_learning_event,
                },
            }
        else:
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
            composer_out: Dict[str, Any] = {
                "ok": True,
                "origin": local_out.get("origin", "aion_conversation_orchestrator"),
                "timestamp": None,
                "user_text": user_text,
                "response": str(local_out.get("response") or ""),
                "confidence": _safe_float(local_out.get("confidence"), 0.0),
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
                confidence=_safe_float(turn_ctx.get("confidence_hint"), 0.0),
                known_facts=_composer_known_facts_from_turn_ctx(turn_ctx),
                goals=_composer_goals_from_turn_ctx(turn_ctx),
                unresolved=list((turn_ctx.get("dialogue_state") or {}).get("unresolved") or []),
                fusion_snapshot={
                    "sigma": _safe_float((turn_ctx.get("beliefs") or {}).get("stability"), 0.5),
                    "psi_tilde": _safe_float((turn_ctx.get("phi_state") or {}).get("Φ_coherence"), 0.5),
                },
                source_refs=_composer_source_refs(turn_ctx),
                apply_teaching=bool(apply_teaching),
                include_debug=include_debug,
                include_metadata=include_metadata,
            )
            composer_out = _run_composer_response(req)

        response_text = str(composer_out.get("response") or "")
        confidence = _safe_float(composer_out.get("confidence"), 0.0)
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

        # Derived follow-up visibility flags (kept in orchestrator metadata/debug for now)
        followup_ctx = dict(turn_ctx.get("followup_context") or {})
        has_followup_context = bool(followup_ctx.get("has_recent_context")) or bool(followup_ctx.get("has_topic_context"))
        context_hints = list(turn_ctx.get("context_hints") or [])

        # Sprint 3 summaries (guarded)
        trading_learning_summary = None
        trading_weakness_signals: List[Dict[str, Any]] = []
        try:
            if getattr(self, "trading_learning_capture", None) is not None:
                if hasattr(self.trading_learning_capture, "build_summary"):
                    trading_learning_summary = self.trading_learning_capture.build_summary()
                if include_debug and hasattr(self.trading_learning_capture, "build_weakness_signals"):
                    raw_ws = self.trading_learning_capture.build_weakness_signals()
                    if isinstance(raw_ws, list):
                        trading_weakness_signals = [w for w in raw_ws if isinstance(w, dict)]
        except Exception:
            trading_learning_summary = None
            trading_weakness_signals = []

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
                    "turn_count": int(getattr(state, "turn_count", 0)),
                    "state_topic": state.topic,
                    "state_intent": state.intent,
                    "unresolved_count": len(state.unresolved),
                    "commitment_count": len(state.commitments),
                    "latency_ms": int((time.time() - started) * 1000),
                    "planned_mode": planned_mode,
                    "planner_reason": plan.get("reason"),
                    "local_mode_handler": bool(local_out is not None),
                    "used_prebuilt_planner": bool(prebuilt_plan_dict.get("mode")),
                    "has_followup_context": has_followup_context,
                    "context_hints": context_hints,
                    "skill_attempted": bool(skill_req is not None),
                    "skill_executed_ok": bool(skill_out is not None and bool(skill_out.ok)),
                    "skill_id": (
                        skill_out.skill_id
                        if skill_out is not None and getattr(skill_out, "skill_id", None)
                        else None
                    ),
                    # Trading Sprint 3 / 3.1 (paper-only capture)
                    "trading_learning_event_captured": bool(trading_learning_event is not None),
                    "trading_capture_recorded": bool(trading_capture_result is not None),
                    "trading_learning_summary": trading_learning_summary,
                    "trading_journal_summary": trading_journal_summary_after,
                    "trading_journal": trading_journal_summary_after or trading_journal_summary_before,
                    # Phase D Sprint 2 (compact, read-only advisory summary)
                    "learning_context": learning_context_summary,
                },
            }

        if include_debug:
            state_after_save = state.to_dict()
            out["debug"] = {
                "turn_context": turn_ctx,
                "dialogue_state": state_after_save,
                "composer_out": composer_out,
                "planner": plan,
                "orchestrator_trace": {
                    "used_local_handler": bool(local_out is not None),
                    "local_handler_name": (metadata.get("local_handler") if isinstance(metadata, dict) else None),
                    "apply_teaching": bool(apply_teaching),
                    "state_before_turn_count": int(state_before.get("turn_count") or 0),
                    "state_after_turn_count": int(state_after_save.get("turn_count") or 0),
                    "recent_user_prompts": _select_recent_user_prompts(state_after_save, limit=3),
                    "last_assistant_response": _last_assistant_response(state_after_save),
                    "has_followup_context": has_followup_context,
                    "context_hints": context_hints,
                    "skill_request": (skill_req.to_dict() if skill_req else None),
                    "skill_result": (skill_out.to_dict() if skill_out else None),
                    # Trading Sprint 3 / 3.1
                    "trading_capture_result": trading_capture_result,
                    "trading_journal_summary_before": trading_journal_summary_before,
                    "trading_journal_summary_after": trading_journal_summary_after,
                    "trading_journal": trading_journal_summary_after or trading_journal_summary_before,
                    "trading_learning_event": trading_learning_event,
                    "trading_weakness_signals": trading_weakness_signals,
                    # Phase D Sprint 2 (full read-only context view for diagnostics)
                    "learning_context_view": learning_context_view,
                },
            }

        return out

    def get_state_snapshot(self, session_id: str) -> DialogueStateSnapshot:
        """
        Typed state snapshot contract for debugging/tests/API compatibility.
        """
        state_dict = self.get_state(session_id)
        return DialogueStateSnapshot.from_dict(state_dict)

    def get_state(self, session_id: str) -> Dict[str, Any]:
        return self.tracker.get_or_create(session_id).to_dict()

    def reset_state(self, session_id: str) -> Dict[str, Any]:
        return self.tracker.reset(session_id)