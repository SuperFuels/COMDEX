from __future__ import annotations

from typing import Any, Dict, List


def evaluate_macro_cascade_rules(*, levers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Minimal v1 rules engine for top-down cascade implications.

    Input:
      levers = [
        {"lever": "yen", "direction": "up", "materiality": 82, "note": "..."},
        ...
      ]

    Output:
      list of cascade implication dicts suitable for storage in
      top_down_levers_snapshot.cascade_implications
    """
    out: List[Dict[str, Any]] = []

    lever_map = {str(x.get("lever")): x for x in levers if isinstance(x, dict)}

    def materiality(name: str) -> float:
        try:
            return float(lever_map.get(name, {}).get("materiality", 0.0))
        except Exception:
            return 0.0

    def direction(name: str) -> str:
        return str(lever_map.get(name, {}).get("direction", ""))

    # Yen carry unwind -> risk off
    if direction("yen") == "up" and materiality("yen") >= 60:
        out.append({
            "rule_id": "yen_up_risk_off",
            "summary": "Yen strength suggests carry unwind / risk-off pressure.",
            "affected_scope": "macro",
            "effect_direction": "de_risk",
            "confidence": min(95.0, materiality("yen")),
            "target_refs": [],
        })

    # Dollar up -> pressure on EM / commodities / multinationals
    if direction("dollar") == "up" and materiality("dollar") >= 60:
        out.append({
            "rule_id": "dollar_up_headwind",
            "summary": "Dollar strength likely creates headwinds for EM exposure and dollar-sensitive risk assets.",
            "affected_scope": "cross_asset",
            "effect_direction": "headwind",
            "confidence": min(95.0, materiality("dollar")),
            "target_refs": [],
        })

    # Credit spreads widening -> debt stress
    if direction("credit_spreads") == "up" and materiality("credit_spreads") >= 60:
        out.append({
            "rule_id": "credit_spreads_up_debt_stress",
            "summary": "Widening credit spreads increase pressure on high-debt / refinancing-risk businesses.",
            "affected_scope": "thesis",
            "effect_direction": "increase_conviction",
            "confidence": min(95.0, materiality("credit_spreads")),
            "target_refs": ["pattern/debt_wall_stress"],
        })

    # Oil up -> energy tailwind / input-cost headwind elsewhere
    if direction("oil") == "up" and materiality("oil") >= 60:
        out.append({
            "rule_id": "oil_up_sector_rotation",
            "summary": "Oil strength supports energy while creating input-cost headwinds for energy-sensitive sectors.",
            "affected_scope": "sector",
            "effect_direction": "mixed",
            "confidence": min(95.0, materiality("oil")),
            "target_refs": ["sector/energy"],
        })

    # Gold up + risk_off = defensive signal
    if direction("gold") == "up" and materiality("gold") >= 60:
        out.append({
            "rule_id": "gold_up_defensive_signal",
            "summary": "Gold strength suggests defensive preference / stress sensitivity in capital allocation.",
            "affected_scope": "macro",
            "effect_direction": "de_risk",
            "confidence": min(95.0, materiality("gold")),
            "target_refs": [],
        })

    # Sector rotation explicit
    if direction("sector_rotation") in {"risk_on", "risk_off", "mixed"} and materiality("sector_rotation") >= 50:
        effect = "tailwind" if direction("sector_rotation") == "risk_on" else "headwind"
        if direction("sector_rotation") == "mixed":
            effect = "uncertain"
        out.append({
            "rule_id": "sector_rotation_signal",
            "summary": "Sector rotation is material and should be applied as a sector-level conviction modifier.",
            "affected_scope": "sector",
            "effect_direction": effect,
            "confidence": min(90.0, materiality("sector_rotation")),
            "target_refs": [],
        })

    return out