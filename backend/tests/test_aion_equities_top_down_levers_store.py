from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.macro_cascade_rules import evaluate_macro_cascade_rules
from backend.modules.aion_equities.top_down_levers_store import TopDownLeversStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_top_down_snapshot(tmp_path):
    store = TopDownLeversStore(tmp_path)

    levers = [
        {"lever": "yen", "direction": "up", "materiality": 82, "note": "carry unwind risk"},
        {"lever": "credit_spreads", "direction": "up", "materiality": 71, "note": "stress building"},
    ]
    cascades = evaluate_macro_cascade_rules(levers=levers)

    payload = store.save_snapshot(
        snapshot_id="topdown/2026-02-27_morning",
        timestamp=_dt(2026, 2, 27, 8, 0, 0),
        regime_ref="macro/global_transitioning",
        regime_state="transitioning",
        active_levers=levers,
        cascade_implications=cascades,
        sector_posture=[
            {"sector_ref": "sector/energy", "posture": "green", "tailwind_score": 72, "headwind_score": 20},
            {"sector_ref": "sector/consumer_discretionary", "posture": "red", "tailwind_score": 18, "headwind_score": 81},
        ],
        conviction_state={
            "signal_coherence": 64,
            "uncertainty_score": 41,
            "summary": "Signals moderately aligned but not fully clean."
        },
        created_by="pytest",
        validate=True,
    )

    loaded = store.load_snapshot("topdown/2026-02-27_morning")
    assert loaded["snapshot_id"] == payload["snapshot_id"]
    assert loaded["regime_state"] == "transitioning"
    assert len(loaded["cascade_implications"]) >= 1


def test_list_snapshots(tmp_path):
    store = TopDownLeversStore(tmp_path)

    store.save_snapshot(
        snapshot_id="topdown/2026-02-27_morning",
        timestamp=_dt(2026, 2, 27, 8, 0, 0),
        regime_ref="macro/global_transitioning",
        regime_state="transitioning",
        active_levers=[{"lever": "dollar", "direction": "up", "materiality": 60}],
        cascade_implications=[],
        sector_posture=[],
        conviction_state={"signal_coherence": 50, "uncertainty_score": 50},
        created_by="pytest",
        validate=True,
    )

    assert "topdown_2026-02-27_morning" in store.list_snapshots()


def test_macro_cascade_rules_emit_implications():
    cascades = evaluate_macro_cascade_rules(
        levers=[
            {"lever": "yen", "direction": "up", "materiality": 90},
            {"lever": "credit_spreads", "direction": "up", "materiality": 75},
        ]
    )
    rule_ids = {x["rule_id"] for x in cascades}
    assert "yen_up_risk_off" in rule_ids
    assert "credit_spreads_up_debt_stress" in rule_ids