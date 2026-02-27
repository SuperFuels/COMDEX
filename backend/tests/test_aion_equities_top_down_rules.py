from __future__ import annotations

from backend.modules.aion_equities.top_down_rules import derive_top_down_implications


def test_derive_top_down_implications_risk_off():
    macro = {
        "regime_name": "risk_off",
        "regime_confidence": 82,
    }

    snapshot = {
        "fx": {
            "usd_broad": {"direction": "up"},
            "usd_jpy": {"direction": "down"},  # yen strength / carry unwind
        },
        "rates": {
            "real_yields": {"direction": "up"},
        },
        "credit": {
            "spreads": {"direction": "widening"},
        },
        "commodities": {
            "gold": {"direction": "up"},
            "oil": {"direction": "up"},
        },
        "sector_flows": {
            "defensives": {"direction": "into"},
            "energy": {"direction": "into"},
            "ai_infrastructure": {"direction": "out_of"},
        },
    }

    out = derive_top_down_implications(
        macro_regime=macro,
        top_down_snapshot=snapshot,
    )

    assert out["regime_summary"]["regime_name"] == "risk_off"
    assert out["conviction_filter"]["contradiction_count"] >= 1
    assert out["sector_posture"]["defensives"] == "green"
    assert out["sector_posture"]["high_beta"] == "red"
    assert any(x["rule"] == "credit_spreads_widening" for x in out["cascade_implications"])