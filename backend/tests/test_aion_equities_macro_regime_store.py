from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.macro_regime_store import MacroRegimeStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_macro_regime(tmp_path):
    store = MacroRegimeStore(tmp_path)

    payload = store.save_macro_regime(
        as_of_date=_dt(2026, 2, 27, 9, 0, 0),
        regime_state="rotation",
        summary="Capital rotating into energy and defensives while credit remains stable.",
        signals_patch={
            "usd_direction": "strengthening",
            "usd_jpy_signal": "risk_negative",
            "rates_direction": "rising",
            "real_yields_direction": "rising",
            "gold_direction": "rising",
            "credit_spread_regime": "stable",
        },
        sector_flows_patch={
            "leaders": ["energy", "utilities"],
            "laggards": ["consumer_discretionary", "small_caps"],
            "notes": "Leadership narrow but coherent.",
        },
        market_style_patch={
            "mag7_state": "diverging",
            "breadth_state": "narrowing",
            "ai_trade_state": "concentrated",
        },
        regime_multipliers_patch={
            "business_quality_multiplier": 0.95,
            "analytical_confidence_multiplier": 0.9,
            "thesis_coherence_multiplier": 0.88,
        },
        risk_flags=["real_yield_headwind", "mag7_concentration_risk"],
        validate=True,
    )

    loaded = store.load_macro_regime("2026-02-27")

    assert payload["macro_regime_id"] == "macro/regime/2026-02-27"
    assert loaded["regime_state"] == "rotation"
    assert loaded["signals"]["usd_jpy_signal"] == "risk_negative"
    assert loaded["sector_flows"]["leaders"] == ["energy", "utilities"]


def test_list_macro_regimes(tmp_path):
    store = MacroRegimeStore(tmp_path)

    store.save_macro_regime(
        as_of_date="2026-02-26",
        regime_state="risk_off",
        summary="Risk-off session.",
        validate=True,
    )
    store.save_macro_regime(
        as_of_date="2026-02-27",
        regime_state="transition",
        summary="Transition session.",
        validate=True,
    )

    ids = store.list_macro_regimes()
    assert ids == ["2026-02-26", "2026-02-27"]


def test_macro_regime_exists(tmp_path):
    store = MacroRegimeStore(tmp_path)

    assert store.macro_regime_exists("2026-02-27") is False

    store.save_macro_regime(
        as_of_date="2026-02-27",
        regime_state="risk_on",
        summary="Broad risk-on regime.",
        validate=True,
    )

    assert store.macro_regime_exists("2026-02-27") is True