from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_trading.contracts import DailyBiasSheet, PairBias

# ---------------------------------------------------------------------
# Optional Phase 3 DMIP learning capture imports (fail-open)
# ---------------------------------------------------------------------
try:
    from backend.modules.aion_trading.dmip_learning_capture import (
        log_llm_accuracy_stub,
        log_task_tracking_stub,
    )
except Exception:  # pragma: no cover - fail-open import
    # Local non-blocking fallbacks so dmip_runtime stays importable/testable
    def log_llm_accuracy_stub(**kwargs: Any) -> Dict[str, Any]:
        return {
            "ok": True,
            "non_blocking": True,
            "stub": True,
            "capture_type": "llm_accuracy_stub_fallback",
            "source": "dmip_runtime_local_fallback",
            "payload": dict(kwargs or {}),
            "timestamp_unix": time.time(),
        }

    def log_task_tracking_stub(**kwargs: Any) -> Dict[str, Any]:
        return {
            "ok": True,
            "non_blocking": True,
            "stub": True,
            "capture_type": "task_tracking_stub_fallback",
            "source": "dmip_runtime_local_fallback",
            "payload": dict(kwargs or {}),
            "timestamp_unix": time.time(),
        }


# Optional governed weighting runtime (Phase D / learning)
try:
    from backend.modules.aion_learning.decision_influence_runtime import (
        get_decision_influence_runtime,
    )
except Exception:  # pragma: no cover - fail-open import
    get_decision_influence_runtime = None  # type: ignore[assignment]


CHECKPOINT_SPECS = {
    "pre_market": {"label": "Pre-Market Global Briefing", "hhmm_gmt": "06:00"},
    "london": {"label": "London Open Analysis", "hhmm_gmt": "07:45"},
    "mid_london": {"label": "Mid-London Review", "hhmm_gmt": "10:00"},
    "new_york": {"label": "New York Open Analysis", "hhmm_gmt": "13:30"},
    "asia": {"label": "Asia Open Preparation", "hhmm_gmt": "22:30"},
    "eod": {"label": "End of Day Learning Debrief", "hhmm_gmt": "22:00"},
}


def _default_pairs() -> List[str]:
    return ["EUR/USD", "GBP/USD", "USD/JPY"]


# ---------------------------------------------------------------------
# Small safe coercion helpers
# ---------------------------------------------------------------------


def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


# ---------------------------------------------------------------------
# Phase 3D / 3E: weighting runtime integration (fail-open)
# ---------------------------------------------------------------------


def _get_weighting_runtime() -> Tuple[Optional[Any], Optional[str]]:
    if get_decision_influence_runtime is None:
        return None, "decision_influence_runtime_import_unavailable"
    try:
        return get_decision_influence_runtime(), None
    except Exception as e:
        return None, f"decision_influence_runtime_init_error:{e}"


def _build_weighting_scope(
    *,
    checkpoint: str,
    market_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Scope used for governed weighting lookup. Keep paper-safe.
    """
    profile_id = _safe_str(market_snapshot.get("profile_id"), "default") or "default"
    environment = _safe_str(market_snapshot.get("environment"), "paper") or "paper"
    return {
        "profile_id": profile_id,
        "environment": environment,
        "checkpoint": checkpoint,
    }


def _try_read_weights_snapshot(
    runtime: Any,
    *,
    scope: Dict[str, Any],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Try multiple runtime API shapes, fail-open.
    """
    payload = {
        "action": "show",
        "dry_run": True,
        "scope": scope,
        "source": "dmip_runtime",
        "reason": "DMIP read decision influence weights for weighted synthesis",
    }

    try:
        raw = None
        if hasattr(runtime, "get_weights"):
            raw = runtime.get_weights(payload)
        elif hasattr(runtime, "read_weights"):
            raw = runtime.read_weights(payload)
        elif hasattr(runtime, "show_weights"):
            raw = runtime.show_weights(payload)
        elif hasattr(runtime, "get_snapshot"):
            raw = runtime.get_snapshot(payload)
        else:
            return None, "decision_influence_runtime_read_api_unavailable"

        if hasattr(raw, "to_dict"):
            raw = raw.to_dict()

        d = _safe_dict(raw)
        # Some runtimes wrap payload under "output"
        out = _safe_dict(d.get("output")) if isinstance(d.get("output"), dict) else d

        weights = out.get("weights")
        if isinstance(weights, dict) and weights:
            return out, None

        # tolerate alternate shapes but mark unusable
        return out, "decision_influence_weights_missing"
    except Exception as e:
        return None, f"decision_influence_weights_read_error:{e}"


def _extract_weighted_bias_hint(
    *,
    pair: str,
    llm_pair: Dict[str, Any],
    weights_snapshot: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Lightweight synthesis hook (P3D) without changing risk invariants.
    Produces metadata only + confidence hinting (capped).
    """
    a = _safe_str(llm_pair.get("claude_bias")).upper()
    b = _safe_str(llm_pair.get("gpt4_bias")).upper()
    conf = _safe_str(llm_pair.get("confidence"), "MEDIUM").upper()
    conf = conf if conf in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"

    if not isinstance(weights_snapshot, dict):
        return {
            "ok": False,
            "pair": pair,
            "weighted_bias": None,
            "weighted_confidence": None,
            "agreement": "unavailable",
            "reason": "weights_snapshot_unavailable",
        }

    # We don't assume specific keys yet; just read likely LLM trust signal if present
    llm_trust_weights = _safe_dict(weights_snapshot.get("llm_trust_weights"))

    # Some runtimes may flatten trust weights elsewhere; fail softly
    claude_w = _safe_float(
        llm_trust_weights.get("claude") or llm_trust_weights.get("claude_bias"),
        1.0,
    )
    gpt_w = _safe_float(
        llm_trust_weights.get("gpt4") or llm_trust_weights.get("gpt4_bias"),
        1.0,
    )

    allowed = {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}

    # Preserve disagreement as first-class signal (P3E)
    if a and b and a in allowed and b in allowed and a != b:
        return {
            "ok": True,
            "pair": pair,
            "weighted_bias": "AVOID",
            "weighted_confidence": "LOW",
            "agreement": "disagree",
            "reason": "llm_disagreement_preserved",
            "weights_version": weights_snapshot.get("weights_version") or weights_snapshot.get("version"),
            "snapshot_hash": weights_snapshot.get("snapshot_hash"),
            "llm_weights_used": {"claude": claude_w, "gpt4": gpt_w},
        }

    # Agreement path
    if a and b and a == b and a in allowed:
        base_conf = conf
        # Simple capped uplift hint only (never overrides to HIGH from LOW unless both weights strong)
        avg_w = (max(0.0, claude_w) + max(0.0, gpt_w)) / 2.0
        if base_conf == "LOW" and avg_w >= 1.25:
            weighted_conf = "MEDIUM"
        elif base_conf == "MEDIUM" and avg_w >= 1.5:
            weighted_conf = "HIGH"
        else:
            weighted_conf = base_conf

        return {
            "ok": True,
            "pair": pair,
            "weighted_bias": a,
            "weighted_confidence": weighted_conf,
            "agreement": "agree",
            "reason": "llm_agreement_weighted_hint",
            "weights_version": weights_snapshot.get("weights_version") or weights_snapshot.get("version"),
            "snapshot_hash": weights_snapshot.get("snapshot_hash"),
            "llm_weights_used": {"claude": claude_w, "gpt4": gpt_w},
        }

    # Partial / incomplete path
    return {
        "ok": True,
        "pair": pair,
        "weighted_bias": None,
        "weighted_confidence": None,
        "agreement": "partial",
        "reason": "insufficient_llm_pair_data",
        "weights_version": weights_snapshot.get("weights_version") or weights_snapshot.get("version"),
        "snapshot_hash": weights_snapshot.get("snapshot_hash"),
        "llm_weights_used": {"claude": claude_w, "gpt4": gpt_w},
    }


def run_dmip_checkpoint(
    *,
    checkpoint: str,
    market_snapshot: Optional[Dict[str, Any]] = None,
    llm_consultation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Phase T Sprint 1 + Phase 3 promotion (non-breaking):
    - deterministic DMIP scaffold remains primary behavior
    - optional governed weighting runtime read used for weighted synthesis hints
    - disagreement remains a preserved signal (AVOID)
    - no risk invariants are mutated here (paper-safe / read-only synthesis)
    """
    cp = str(checkpoint or "").strip()
    if cp not in CHECKPOINT_SPECS:
        raise ValueError(f"checkpoint must be one of {sorted(CHECKPOINT_SPECS)}")

    market_snapshot = dict(market_snapshot or {})
    llm_consultation = dict(llm_consultation or {})

    pairs = list(market_snapshot.get("pairs") or _default_pairs())
    pair_biases: List[PairBias] = []
    agreement_flags: Dict[str, str] = {}

    # Phase 3 runtime lookup (read-only, fail-open)
    weighting_runtime, weighting_runtime_error = _get_weighting_runtime()
    weighting_scope = _build_weighting_scope(checkpoint=cp, market_snapshot=market_snapshot)

    weights_snapshot: Optional[Dict[str, Any]] = None
    weights_runtime_notes: List[str] = []
    if weighting_runtime is not None:
        weights_snapshot, read_err = _try_read_weights_snapshot(weighting_runtime, scope=weighting_scope)
        if read_err:
            weights_runtime_notes.append(read_err)
        else:
            weights_runtime_notes.append("decision_influence_weights_loaded")
    else:
        if weighting_runtime_error:
            weights_runtime_notes.append(weighting_runtime_error)

    weighted_llm_hints: Dict[str, Dict[str, Any]] = {}

    # P3A/P3B unified learning events container (non-breaking, fail-open)
    learning_events: Dict[str, List[Dict[str, Any]]] = {
        "llm_accuracy": [],
        "task_tracking": [],
    }

    # Deterministic defaults (placeholder until real data+LLM consultation skills land)
    for pair in pairs:
        bias = "NEUTRAL"
        conf = "LOW"
        notes = ["phase_t_sprint1_placeholder_bias"]
        key_levels: List[float] = []

        llm_pair = dict((llm_consultation.get("pairs") or {}).get(pair, {}) or {})
        if llm_pair:
            # if both present and disagree -> AVOID (your rule)
            a = _safe_str(llm_pair.get("claude_bias")).upper()
            b = _safe_str(llm_pair.get("gpt4_bias")).upper()
            if a and b:
                if a != b:
                    bias = "AVOID"
                    conf = "LOW"
                    agreement_flags[pair] = "disagree"
                    notes.append("llm_disagreement_pair_avoid")
                else:
                    if a in {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}:
                        bias = a
                    conf = _safe_str(llm_pair.get("confidence"), "MEDIUM").upper()
                    conf = conf if conf in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"
                    agreement_flags[pair] = "agree"
                    notes.append("llm_agreement")
            else:
                agreement_flags[pair] = "partial"
                notes.append("llm_partial_signal")

            kls = llm_pair.get("key_levels")
            if isinstance(kls, list):
                for x in kls:
                    try:
                        key_levels.append(float(x))
                    except Exception:
                        pass

            # ----------------------------------------------------------
            # Phase 3D weighted synthesis hint (metadata / confidence hint)
            # ----------------------------------------------------------
            weighted_hint = _extract_weighted_bias_hint(
                pair=pair,
                llm_pair=llm_pair,
                weights_snapshot=weights_snapshot,
            )
            weighted_llm_hints[pair] = weighted_hint

            if weighted_hint.get("ok"):
                if weighted_hint.get("agreement") == "disagree":
                    # Preserve disagreement / AVOID (P3E)
                    notes.append("weighted_llm_disagreement_preserved")
                    bias = "AVOID"
                    conf = "LOW"
                elif weighted_hint.get("agreement") == "agree":
                    # Non-destructive hinting only: can confirm direction and optionally refine confidence
                    wb = _safe_str(weighted_hint.get("weighted_bias")).upper()
                    wc = _safe_str(weighted_hint.get("weighted_confidence")).upper()
                    if wb in {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"} and bias != "AVOID":
                        # Only align if current pair bias came from LLM agreement path
                        if agreement_flags.get(pair) == "agree":
                            bias = wb
                            notes.append("weighted_llm_bias_confirmed")
                    if wc in {"HIGH", "MEDIUM", "LOW"} and agreement_flags.get(pair) == "agree":
                        # Confidence refinement only (still bounded/categorical)
                        conf = wc
                        notes.append("weighted_llm_confidence_hint")
                elif weighted_hint.get("agreement") == "partial":
                    notes.append("weighted_llm_partial_hint")

            # ----------------------------------------------------------
            # P3A / P3B append-only learning capture stubs (non-blocking)
            # ----------------------------------------------------------
            try:
                agreement = agreement_flags.get(pair, "partial")
                cap1 = log_llm_accuracy_stub(
                    checkpoint=cp,
                    pair=pair,
                    llm_pair=llm_pair,
                    agreement=agreement,
                    selected_bias=bias,
                    confidence=conf,
                    source="dmip_runtime",
                )
                learning_events["llm_accuracy"].append(cap1)
            except Exception as e:
                learning_events["llm_accuracy"].append(
                    {
                        "ok": False,
                        "non_blocking": True,
                        "error": "llm_accuracy_capture_wrapper_exception",
                        "message": str(e),
                    }
                )

            try:
                cap2 = log_task_tracking_stub(
                    checkpoint=cp,
                    pair=pair,
                    stage="dmip_llm_consultation",
                    status="processed",
                    details={
                        "agreement": agreement_flags.get(pair, "partial"),
                        "bias": bias,
                        "confidence": conf,
                        "weighted_hint": weighted_llm_hints.get(pair, {}),
                    },
                    source="dmip_runtime",
                )
                learning_events["task_tracking"].append(cap2)
            except Exception as e:
                learning_events["task_tracking"].append(
                    {
                        "ok": False,
                        "non_blocking": True,
                        "error": "task_tracking_capture_wrapper_exception",
                        "message": str(e),
                    }
                )

        pair_biases.append(
            PairBias(
                pair=pair,
                bias=bias,
                confidence=conf,
                key_levels=key_levels[:8],
                notes=notes,
            ).validate()
        )

    # Conservative default environment
    risk_environment = _safe_str(market_snapshot.get("risk_environment"), "UNKNOWN").upper()
    if risk_environment not in {"RISK_ON", "RISK_OFF", "MIXED", "UNKNOWN"}:
        risk_environment = "UNKNOWN"

    trading_conf = "LOW"
    if any(v == "disagree" for v in agreement_flags.values()):
        trading_conf = "LOW"
    elif all(v == "agree" for v in agreement_flags.values()) and agreement_flags:
        trading_conf = "MEDIUM"

    sheet = DailyBiasSheet(
        checkpoint_id=f"dmip_{uuid.uuid4().hex[:16]}",
        session=cp,
        risk_environment=risk_environment,
        trading_confidence=trading_conf,
        pair_biases=pair_biases,
        avoid_events=list(market_snapshot.get("avoid_events") or []),
        llm_agreement_flags=agreement_flags,
        metadata={
            "phase": "phase_t_sprint1_dmip_scaffold_plus_phase3_weighted_hints",
            "generated_at_unix": time.time(),
            "checkpoint_label": CHECKPOINT_SPECS[cp]["label"],
            "checkpoint_time_gmt": CHECKPOINT_SPECS[cp]["hhmm_gmt"],
            # Phase 3 metadata (read-only / non-blocking)
            "decision_influence_weighting_scope": weighting_scope,
            "decision_influence_weighting_loaded": bool(weights_snapshot),
            "decision_influence_weighting_notes": weights_runtime_notes,
            "decision_influence_weights_version": (
                (weights_snapshot or {}).get("weights_version")
                or (weights_snapshot or {}).get("version")
            ),
            "decision_influence_snapshot_hash": (weights_snapshot or {}).get("snapshot_hash"),
            "risk_invariants_mutated": False,  # explicit P3F guardrail signal
        },
    ).validate()

    return {
        "ok": True,
        "schema_version": "aion.dmip_checkpoint_result.v1",
        "checkpoint": cp,
        "bias_sheet": sheet.to_dict(),
        "notes": [
            "read_only_scaffold",
            "real_data_feeds_not_connected_yet",
            "llm_consultation_optional_input_supported",
            "phase3_weighted_synthesis_hints_enabled_fail_open",
            "disagreement_preserved_as_signal",
            "risk_invariants_not_mutated",
            "p3a_p3b_learning_capture_stubs_non_blocking",
        ],
        # Phase 3 additive outputs (non-breaking)
        "llm_weighted_hints": weighted_llm_hints,
        "learning_events": learning_events,
        "decision_influence_weighting": {
            "scope": weighting_scope,
            "loaded": bool(weights_snapshot),
            "notes": weights_runtime_notes,
            "weights_version": (
                (weights_snapshot or {}).get("weights_version")
                or (weights_snapshot or {}).get("version")
            ),
            "snapshot_hash": (weights_snapshot or {}).get("snapshot_hash"),
        },
    }