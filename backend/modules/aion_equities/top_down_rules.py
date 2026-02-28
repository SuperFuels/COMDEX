from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _get(d: Dict[str, Any], *path: str, default=None):
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def _sector_posture_map(snapshot: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in snapshot.get("sector_posture", []) or []:
        if not isinstance(item, dict):
            continue
        sector_ref = item.get("sector_ref")
        posture = item.get("posture")
        if isinstance(sector_ref, str) and isinstance(posture, str):
            out[sector_ref.removeprefix("sector/")] = posture
    return out


def _active_lever_map(snapshot: Dict[str, Any]) -> Dict[str, Tuple[str, float]]:
    out: Dict[str, Tuple[str, float]] = {}
    for item in snapshot.get("active_levers", []) or []:
        if not isinstance(item, dict):
            continue
        lever = item.get("lever")
        direction = item.get("direction")
        materiality = item.get("materiality", 50.0)
        if isinstance(lever, str) and isinstance(direction, str):
            try:
                mat = float(materiality)
            except Exception:
                mat = 50.0
            out[lever] = (direction, mat)
    return out


def _mk_implication(
    *,
    rule: str,
    summary: str,
    affected_scope: str,
    effect_direction: str,
    confidence: float,
    target_refs: List[str] | None = None,
) -> Dict[str, Any]:
    """
    Emit both legacy and schema-oriented keys so old tests and newer runtime
    consumers can coexist.
    """
    return {
        "rule": rule,
        "rule_id": rule,
        "summary": summary,
        "impact": summary,  # legacy-friendly alias
        "affected_scope": affected_scope,
        "effect_direction": effect_direction,
        "confidence": confidence,
        "target_refs": target_refs or [],
    }


def derive_top_down_implications(
    *,
    macro_regime: Dict[str, Any],
    top_down_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    regime_name = (
        macro_regime.get("regime_name")
        or macro_regime.get("summary")
        or macro_regime.get("regime_state")
        or "unknown"
    )
    regime_conf = float(macro_regime.get("regime_confidence", 0.0) or 0.0)

    lever_map = _active_lever_map(top_down_snapshot)
    sector_posture = _sector_posture_map(top_down_snapshot)

    active_levers: List[Dict[str, Any]] = list(top_down_snapshot.get("active_levers", []) or [])
    cascade_implications: List[Dict[str, Any]] = list(top_down_snapshot.get("cascade_implications", []) or [])

    contradictions = 0

    def lever_dir(name: str) -> str | None:
        item = lever_map.get(name)
        return item[0] if item else None

    dollar_dir = lever_dir("dollar")
    yen_dir = lever_dir("yen")
    gold_dir = lever_dir("gold")
    oil_dir = lever_dir("oil")
    real_yields_dir = lever_dir("real_yields")
    credit_dir = lever_dir("credit_spreads")
    ai_dir = lever_dir("ai_leadership")
    mag7_dir = lever_dir("mag7_breadth")

    # Fallback support for older nested snapshot shapes
    if dollar_dir is None:
        fx_usd = _get(top_down_snapshot, "fx", "usd_broad", "direction")
        if fx_usd == "up":
            dollar_dir = "up"
        elif fx_usd == "down":
            dollar_dir = "down"

    if yen_dir is None:
        fx_jpy = _get(top_down_snapshot, "fx", "usd_jpy", "direction")
        if fx_jpy == "down":
            yen_dir = "risk_off"
        elif fx_jpy == "up":
            yen_dir = "risk_on"

    if real_yields_dir is None:
        ry = _get(top_down_snapshot, "rates", "real_yields", "direction")
        if ry == "up":
            real_yields_dir = "up"
        elif ry == "down":
            real_yields_dir = "down"

    if credit_dir is None:
        cs = _get(top_down_snapshot, "credit", "spreads", "direction")
        if cs in {"widening", "tightening"}:
            credit_dir = cs

    if gold_dir is None:
        gd = _get(top_down_snapshot, "commodities", "gold", "direction")
        if gd in {"up", "down"}:
            gold_dir = gd

    if oil_dir is None:
        od = _get(top_down_snapshot, "commodities", "oil", "direction")
        if od in {"up", "down"}:
            oil_dir = od

    if not sector_posture:
        defensives = _get(top_down_snapshot, "sector_flows", "defensives", "direction")
        energy = _get(top_down_snapshot, "sector_flows", "energy", "direction")
        ai_infra = _get(top_down_snapshot, "sector_flows", "ai_infrastructure", "direction")

        if defensives == "into":
            sector_posture["defensives"] = "green"
            sector_posture["cyclicals"] = "red"
        elif defensives == "out_of":
            sector_posture["defensives"] = "red"
            sector_posture["cyclicals"] = "green"

        if energy == "into":
            sector_posture["energy"] = "green"
        elif energy == "out_of":
            sector_posture["energy"] = "red"

        if ai_infra == "into":
            sector_posture["ai_infrastructure"] = "green"
        elif ai_infra == "out_of":
            sector_posture["ai_infrastructure"] = "red"

    # Only derive if not already supplied
    if not cascade_implications:
        if dollar_dir == "up":
            cascade_implications.append(
                _mk_implication(
                    rule="stronger_usd",
                    summary="headwind_for_em_and_dollar_sensitive_risk_assets",
                    affected_scope="cross_asset",
                    effect_direction="headwind",
                    confidence=70.0,
                )
            )
        elif dollar_dir == "down":
            cascade_implications.append(
                _mk_implication(
                    rule="weaker_usd",
                    summary="supportive_for_risk_assets_and_commodities",
                    affected_scope="cross_asset",
                    effect_direction="tailwind",
                    confidence=65.0,
                )
            )

        if yen_dir == "risk_off":
            cascade_implications.append(
                _mk_implication(
                    rule="yen_strength",
                    summary="risk_off_carry_unwind_signal",
                    affected_scope="macro",
                    effect_direction="de_risk",
                    confidence=85.0,
                )
            )
            sector_posture.setdefault("defensives", "green")
            sector_posture.setdefault("high_beta", "red")

        if gold_dir == "up":
            cascade_implications.append(
                _mk_implication(
                    rule="gold_rising",
                    summary="stress_or_defensive_bid_signal",
                    affected_scope="cross_asset",
                    effect_direction="uncertain",
                    confidence=68.0,
                )
            )

        if credit_dir == "widening":
            cascade_implications.append(
                _mk_implication(
                    rule="credit_spreads_widening",
                    summary="pressure_on_high_debt_and_cyclical_names",
                    affected_scope="macro",
                    effect_direction="headwind",
                    confidence=88.0,
                )
            )
            sector_posture.setdefault("high_debt", "red")
        elif credit_dir == "tightening":
            sector_posture.setdefault("credit_sensitive", "green")

        if real_yields_dir == "up":
            cascade_implications.append(
                _mk_implication(
                    rule="real_yields_up",
                    summary="multiple_pressure_on_long_duration_growth",
                    affected_scope="sector",
                    effect_direction="headwind",
                    confidence=78.0,
                )
            )
            sector_posture.setdefault("long_duration_growth", "red")
        elif real_yields_dir == "down":
            sector_posture.setdefault("long_duration_growth", "green")

    regime_state = top_down_snapshot.get("regime_state") or macro_regime.get("regime_state") or ""

    if dollar_dir == "up" and gold_dir == "up":
        contradictions += 1
    if real_yields_dir == "up" and ai_dir in {"up", "risk_on"}:
        contradictions += 1
    if credit_dir == "widening" and ai_dir in {"up", "risk_on"}:
        contradictions += 1
    if yen_dir == "risk_off" and oil_dir == "up":
        contradictions += 1

    if regime_state == "risk_off":
        if sector_posture.get("cyclicals") == "green":
            contradictions += 1
        if sector_posture.get("long_duration_growth") == "green":
            contradictions += 1
        if credit_dir == "widening" and sector_posture.get("defensives") not in {"green", "amber"}:
            contradictions += 1

    if contradictions >= 2:
        coherence = "low"
    elif contradictions == 1:
        coherence = "medium"
    else:
        coherence = "high"

    return {
        "regime_summary": {
            "regime_name": regime_name,
            "regime_confidence": regime_conf,
        },
        "active_levers": active_levers,
        "cascade_implications": cascade_implications,
        "sector_posture": sector_posture,
        "conviction_filter": {
            "macro_signal_coherence": coherence,
            "contradiction_count": contradictions,
        },
    }