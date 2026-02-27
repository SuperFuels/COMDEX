from __future__ import annotations

from typing import Any, Dict, List


def _materiality(value: Any, default: float = 50.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def derive_top_down_implications(
    *,
    macro_regime: Dict[str, Any],
    top_down_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Normalize macro regime + top-down snapshot into a lightweight derived
    helicopter view used by runtime/tests.

    This version is aligned to the current v0_1 schema shapes:

      macro_regime:
        - macro_regime_id
        - regime_state
        - summary
        - signals
        - risk_flags

      top_down_snapshot:
        - snapshot_id
        - active_levers[]
        - cascade_implications[]
        - sector_posture[]
        - conviction_state{}
    """

    regime_name = (
        macro_regime.get("summary")
        or macro_regime.get("regime_name")
        or macro_regime.get("regime_state")
        or "unknown"
    )

    regime_confidence = float(
        macro_regime.get("regime_confidence", 0.0) or 0.0
    )

    active_levers: List[Dict[str, Any]] = list(top_down_snapshot.get("active_levers") or [])
    input_cascades: List[Dict[str, Any]] = list(top_down_snapshot.get("cascade_implications") or [])
    input_sector_posture: List[Dict[str, Any]] = list(top_down_snapshot.get("sector_posture") or [])
    conviction_state: Dict[str, Any] = dict(top_down_snapshot.get("conviction_state") or {})

    derived_sector_posture: Dict[str, str] = {}
    derived_cascades: List[Dict[str, Any]] = list(input_cascades)
    contradictions = 0

    # ------------------------------------------------------------------
    # Start with explicit sector posture already present in snapshot
    # ------------------------------------------------------------------
    for row in input_sector_posture:
        sector_ref = row.get("sector_ref")
        posture = row.get("posture")
        if isinstance(sector_ref, str) and sector_ref.startswith("sector/") and isinstance(posture, str):
            short_name = sector_ref.split("/", 1)[1]
            derived_sector_posture[short_name] = posture

    # ------------------------------------------------------------------
    # Read active levers into a map
    # ------------------------------------------------------------------
    lever_map: Dict[str, Dict[str, Any]] = {}
    for lever in active_levers:
        name = lever.get("lever")
        if isinstance(name, str):
            lever_map[name] = lever

    def has(lever_name: str, direction: str | None = None) -> bool:
        row = lever_map.get(lever_name)
        if not row:
            return False
        if direction is None:
            return True
        return row.get("direction") == direction

    # ------------------------------------------------------------------
    # Add derived cascades / posture from active levers
    # ------------------------------------------------------------------
    if has("dollar", "up"):
        derived_cascades.append(
            {
                "rule_id": "stronger_dollar",
                "summary": "Dollar strength creates headwinds for risk assets and foreign earnings translation.",
                "affected_scope": "cross_asset",
                "effect_direction": "decrease_conviction",
                "confidence": _materiality(lever_map["dollar"].get("materiality"), 70.0),
                "target_refs": [],
            }
        )

    if has("yen", "up") or has("yen", "risk_off"):
        derived_cascades.append(
            {
                "rule_id": "yen_carry_unwind",
                "summary": "Yen strength signals carry unwind / risk-off conditions.",
                "affected_scope": "macro",
                "effect_direction": "de_risk",
                "confidence": _materiality(lever_map["yen"].get("materiality"), 85.0),
                "target_refs": [],
            }
        )
        derived_sector_posture.setdefault("defensives", "green")
        derived_sector_posture.setdefault("high_beta", "red")

    if has("gold", "up"):
        derived_cascades.append(
            {
                "rule_id": "gold_rising",
                "summary": "Gold strength suggests stress, defensive demand, or declining confidence in risk assets.",
                "affected_scope": "cross_asset",
                "effect_direction": "de_risk",
                "confidence": _materiality(lever_map["gold"].get("materiality"), 68.0),
                "target_refs": [],
            }
        )

    if has("credit_spreads", "up") or has("credit_spreads", "risk_off"):
        derived_cascades.append(
            {
                "rule_id": "credit_spreads_widening",
                "summary": "Widening credit spreads increase stress for cyclicals and high-debt names.",
                "affected_scope": "sector",
                "effect_direction": "headwind",
                "confidence": _materiality(lever_map["credit_spreads"].get("materiality"), 88.0),
                "target_refs": [],
            }
        )
        derived_sector_posture.setdefault("high_debt", "red")

    if has("real_yields", "up") or has("real_yields", "tightening"):
        derived_cascades.append(
            {
                "rule_id": "real_yields_up",
                "summary": "Rising real yields pressure long-duration growth valuations.",
                "affected_scope": "sector",
                "effect_direction": "headwind",
                "confidence": _materiality(lever_map["real_yields"].get("materiality"), 78.0),
                "target_refs": [],
            }
        )
        derived_sector_posture.setdefault("long_duration_growth", "red")

    if has("oil", "up"):
        derived_cascades.append(
            {
                "rule_id": "oil_rising",
                "summary": "Oil strength supports energy and pressures fuel/input-cost sensitive sectors.",
                "affected_scope": "sector",
                "effect_direction": "tailwind",
                "confidence": _materiality(lever_map["oil"].get("materiality"), 72.0),
                "target_refs": [],
            }
        )
        derived_sector_posture.setdefault("energy", "green")

    if has("sector_rotation", "risk_off"):
        derived_sector_posture.setdefault("defensives", "green")
        derived_sector_posture.setdefault("cyclicals", "red")

    if has("ai_leadership", "down"):
        derived_sector_posture.setdefault("ai_infrastructure", "red")
    elif has("ai_leadership", "up"):
        derived_sector_posture.setdefault("ai_infrastructure", "green")

    # ------------------------------------------------------------------
    # Contradiction detection
    # ------------------------------------------------------------------
    if has("dollar", "up") and has("gold", "up"):
        contradictions += 1
    if (has("real_yields", "up") or has("real_yields", "tightening")) and has("ai_leadership", "up"):
        contradictions += 1
    if (has("credit_spreads", "up") or has("credit_spreads", "risk_off")) and has("ai_leadership", "up"):
        contradictions += 1

    # Also respect snapshot conviction_state if present
    signal_coherence = conviction_state.get("signal_coherence")
    uncertainty_score = conviction_state.get("uncertainty_score")

    if signal_coherence is None:
        if contradictions >= 2:
            signal_coherence = 25.0
        elif contradictions == 1:
            signal_coherence = 55.0
        else:
            signal_coherence = 80.0

    if uncertainty_score is None:
        if contradictions >= 2:
            uncertainty_score = 80.0
        elif contradictions == 1:
            uncertainty_score = 50.0
        else:
            uncertainty_score = 25.0

    if contradictions >= 2:
        coherence_label = "low"
    elif contradictions == 1:
        coherence_label = "medium"
    else:
        coherence_label = "high"

    return {
        "regime_summary": {
            "regime_name": regime_name,
            "regime_confidence": regime_confidence,
        },
        "active_levers": active_levers,
        "cascade_implications": derived_cascades,
        "sector_posture": derived_sector_posture,
        "conviction_filter": {
            "macro_signal_coherence": coherence_label,
            "contradiction_count": contradictions,
            "signal_coherence": float(signal_coherence),
            "uncertainty_score": float(uncertainty_score),
        },
    }