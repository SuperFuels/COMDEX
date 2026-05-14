# /workspaces/COMDEX/backend/modules/aion_trading/dmip_llm_synthesis.py
from __future__ import annotations

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------
# Small safe coercion helpers
# ---------------------------------------------------------------------


def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


_ALLOWED_BIASES = {"BULLISH", "BEARISH", "NEUTRAL", "AVOID"}
_ALLOWED_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}


# ---------------------------------------------------------------------
# Weight extraction helpers (fail-open)
# ---------------------------------------------------------------------


def _extract_llm_trust_weights(weights_snapshot: Optional[Dict[str, Any]]) -> Dict[str, float]:
    """
    Tolerate multiple runtime shapes. Returns normalized weights with defaults.
    """
    ws = _safe_dict(weights_snapshot)

    # Common shape: {"llm_trust_weights": {"claude": 1.0, "gpt4": 1.0}}
    llm_trust = _safe_dict(ws.get("llm_trust_weights"))

    # Some runtimes may nest under "weights"
    if not llm_trust:
        nested_weights = _safe_dict(ws.get("weights"))
        llm_trust = _safe_dict(nested_weights.get("llm_trust_weights"))

    # Some runtimes may use alternate keys
    claude_w = _safe_float(
        llm_trust.get("claude")
        or llm_trust.get("claude_bias")
        or llm_trust.get("anthropic")
        or llm_trust.get("claude_trust"),
        1.0,
    )
    gpt4_w = _safe_float(
        llm_trust.get("gpt4")
        or llm_trust.get("gpt4_bias")
        or llm_trust.get("openai")
        or llm_trust.get("gpt4_trust"),
        1.0,
    )

    return {
        "claude": max(0.0, claude_w),
        "gpt4": max(0.0, gpt4_w),
    }


def _weights_meta(weights_snapshot: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    ws = _safe_dict(weights_snapshot)
    nested_weights = _safe_dict(ws.get("weights"))

    version = (
        ws.get("weights_version")
        or ws.get("version")
        or nested_weights.get("weights_version")
        or nested_weights.get("version")
    )
    snap_hash = (
        ws.get("snapshot_hash")
        or nested_weights.get("snapshot_hash")
    )

    return {
        "weights_version": version,
        "snapshot_hash": snap_hash,
    }


# ---------------------------------------------------------------------
# Core synthesis functions (P3D / reusable)
# ---------------------------------------------------------------------


def get_llm_weighted_bias(
    *,
    pair: str,
    llm_pair: Dict[str, Any],
    weights_snapshot: Optional[Dict[str, Any]] = None,
    base_selected_bias: Optional[str] = None,
    base_confidence: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reusable weighted synthesis result for one pair.

    Contract goals:
    - fail-open structured response
    - preserve disagreement as signal (AVOID/LOW)
    - bounded confidence refinement only
    - no risk invariant mutation (metadata signal only)
    """
    pair_s = _safe_str(pair)
    llm_pair = _safe_dict(llm_pair)

    a = _safe_str(llm_pair.get("claude_bias")).upper()
    b = _safe_str(llm_pair.get("gpt4_bias")).upper()

    input_conf = _safe_str(
        llm_pair.get("confidence"),
        _safe_str(base_confidence, "MEDIUM") or "MEDIUM",
    ).upper()
    if input_conf not in _ALLOWED_CONFIDENCE:
        input_conf = "MEDIUM"

    base_bias_norm = _safe_str(base_selected_bias).upper()
    if base_bias_norm and base_bias_norm not in _ALLOWED_BIASES:
        base_bias_norm = ""

    meta = _weights_meta(weights_snapshot)
    has_weights_snapshot = isinstance(weights_snapshot, dict)
    llm_weights_used = _extract_llm_trust_weights(weights_snapshot if has_weights_snapshot else None)

    # If no usable snapshot provided, return structured fail-open result
    if not has_weights_snapshot:
        return {
            "ok": False,
            "pair": pair_s,
            "weighted_bias": None,
            "weighted_confidence": None,
            "agreement": "unavailable",
            "reason": "weights_snapshot_unavailable",
            "weights_version": None,
            "snapshot_hash": None,
            "llm_weights_used": llm_weights_used,
            "base_selected_bias": base_bias_norm or None,
            "base_confidence": input_conf,
            "non_blocking": True,
            "risk_invariants_mutated": False,
        }

    # Disagreement preserved as signal (P3E)
    if a in _ALLOWED_BIASES and b in _ALLOWED_BIASES and a and b and a != b:
        return {
            "ok": True,
            "pair": pair_s,
            "weighted_bias": "AVOID",
            "weighted_confidence": "LOW",
            "agreement": "disagree",
            "reason": "llm_disagreement_preserved",
            "weights_version": meta["weights_version"],
            "snapshot_hash": meta["snapshot_hash"],
            "llm_weights_used": llm_weights_used,
            "base_selected_bias": base_bias_norm or None,
            "base_confidence": input_conf,
            "non_blocking": True,
            "risk_invariants_mutated": False,
        }

    # Agreement path
    if a in _ALLOWED_BIASES and b in _ALLOWED_BIASES and a and b and a == b:
        avg_w = (llm_weights_used["claude"] + llm_weights_used["gpt4"]) / 2.0
        weighted_conf = input_conf

        # Bounded uplift only (never jump LOW -> HIGH directly)
        if input_conf == "LOW" and avg_w >= 1.25:
            weighted_conf = "MEDIUM"
        elif input_conf == "MEDIUM" and avg_w >= 1.50:
            weighted_conf = "HIGH"

        # Optional gentle downshift if weights are very low (still bounded)
        if input_conf == "HIGH" and avg_w <= 0.60:
            weighted_conf = "MEDIUM"
        elif input_conf == "MEDIUM" and avg_w <= 0.50:
            weighted_conf = "LOW"

        return {
            "ok": True,
            "pair": pair_s,
            "weighted_bias": a,
            "weighted_confidence": weighted_conf,
            "agreement": "agree",
            "reason": "llm_agreement_weighted_hint",
            "weights_version": meta["weights_version"],
            "snapshot_hash": meta["snapshot_hash"],
            "llm_weights_used": llm_weights_used,
            "base_selected_bias": base_bias_norm or None,
            "base_confidence": input_conf,
            "non_blocking": True,
            "risk_invariants_mutated": False,
        }

    # Partial/incomplete path
    return {
        "ok": True,
        "pair": pair_s,
        "weighted_bias": None,
        "weighted_confidence": None,
        "agreement": "partial",
        "reason": "insufficient_llm_pair_data",
        "weights_version": meta["weights_version"],
        "snapshot_hash": meta["snapshot_hash"],
        "llm_weights_used": llm_weights_used,
        "base_selected_bias": base_bias_norm or None,
        "base_confidence": input_conf,
        "non_blocking": True,
        "risk_invariants_mutated": False,
    }


def synthesise_llm_consultation(
    *,
    llm_consultation: Optional[Dict[str, Any]],
    weights_snapshot: Optional[Dict[str, Any]] = None,
    base_pair_outputs: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Batch synthesis across consultation pairs.

    Inputs:
      llm_consultation:
        {
          "pairs": {
            "EUR/USD": {"claude_bias": "...", "gpt4_bias": "...", "confidence": "..."},
            ...
          }
        }

      base_pair_outputs (optional):
        {
          "EUR/USD": {"bias": "BULLISH", "confidence": "MEDIUM"},
          ...
        }

    Returns:
      structured summary + per-pair weighted hints
    """
    consultation = _safe_dict(llm_consultation)
    pairs_payload = _safe_dict(consultation.get("pairs"))
    base_map = _safe_dict(base_pair_outputs)

    per_pair: Dict[str, Dict[str, Any]] = {}
    counts = {
        "total_pairs_seen": 0,
        "pairs_with_llm_payload": 0,
        "agree": 0,
        "disagree": 0,
        "partial": 0,
        "unavailable": 0,
        "ok_results": 0,
        "not_ok_results": 0,
    }

    for pair, raw in pairs_payload.items():
        counts["total_pairs_seen"] += 1

        llm_pair = _safe_dict(raw)
        if llm_pair:
            counts["pairs_with_llm_payload"] += 1

        base_info = _safe_dict(base_map.get(pair))
        result = get_llm_weighted_bias(
            pair=_safe_str(pair),
            llm_pair=llm_pair,
            weights_snapshot=weights_snapshot,
            base_selected_bias=_safe_str(base_info.get("bias")),
            base_confidence=_safe_str(base_info.get("confidence")),
        )
        per_pair[_safe_str(pair)] = result

        if _safe_bool(result.get("ok")):
            counts["ok_results"] += 1
        else:
            counts["not_ok_results"] += 1

        ag = _safe_str(result.get("agreement")).lower()
        if ag in {"agree", "disagree", "partial", "unavailable"}:
            counts[ag] += 1

    meta = _weights_meta(weights_snapshot)

    return {
        "ok": True,
        "schema_version": "aion.dmip_llm_synthesis_result.v1",
        "non_blocking": True,
        "risk_invariants_mutated": False,
        "weights_snapshot_loaded": isinstance(weights_snapshot, dict),
        "weights_version": meta["weights_version"],
        "snapshot_hash": meta["snapshot_hash"],
        "counts": counts,
        "per_pair": per_pair,
        "notes": [
            "phase3d_reusable_llm_synthesis",
            "disagreement_preserved_as_signal",
            "bounded_confidence_refinement_only",
            "fail_open_structured_results",
        ],
    }