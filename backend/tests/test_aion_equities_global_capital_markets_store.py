from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.global_capital_markets_store import GlobalCapitalMarketsStore


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_global_capital_markets(tmp_path):
    store = GlobalCapitalMarketsStore(tmp_path)

    payload = store.save_global_capital_markets(
        as_of_date=_dt(2026, 2, 22, 8, 0, 0),
        generated_by="pytest",
        liquidity_regime_patch={
            "state": "tight",
            "confidence": 81.0,
            "summary": "Liquidity tightening across developed markets",
        },
        dollar_funding_patch={
            "regime": "tight",
            "dxy_direction": "up",
            "cross_currency_basis_regime": "watch",
        },
        yield_curves=[
            {
                "country_code": "US",
                "yield_2y": 4.8,
                "yield_10y": 4.3,
                "yield_30y": 4.4,
                "curve_regime": "inverted",
            },
            {
                "country_code": "JP",
                "yield_2y": 0.4,
                "yield_10y": 1.2,
                "yield_30y": 1.8,
                "curve_regime": "normal",
            },
        ],
        real_yields=[
            {
                "country_code": "US",
                "real_yield_10y": 1.9,
                "real_yield_2y": 2.1,
                "real_rate_regime": "positive_rising",
            }
        ],
        credit_spreads=[
            {
                "country_code": "US",
                "ig_oas_bps": 115.0,
                "hy_oas_bps": 410.0,
                "spread_regime": "wide",
                "direction": "widening",
            }
        ],
        yield_differential_matrix=[
            {
                "base_country": "US",
                "quote_country": "JP",
                "diff_2y_bps": 440.0,
                "diff_10y_bps": 310.0,
                "regime": "base_favored",
            }
        ],
        foreign_ownership_vulnerability=[
            {
                "country_code": "GB",
                "foreign_ownership_pct": 29.0,
                "vulnerability_regime": "medium",
            }
        ],
        cross_market_signals_patch={
            "risk_appetite_regime": "risk_off",
            "carry_regime": "unwinding",
            "equity_bond_correlation_regime": "inflationary",
            "stress_notes": ["yen_carry_watch", "credit_stress_rising"],
        },
        validate=True,
    )

    loaded = store.load_global_capital_markets("2026-02-22")

    assert payload["global_capital_markets_id"] == "global_capital_markets/2026-02-22"
    assert loaded["liquidity_regime"]["state"] == "tight"
    assert loaded["dollar_funding"]["regime"] == "tight"
    assert loaded["yield_curves"][0]["country_code"] == "US"


def test_list_global_capital_markets_snapshots(tmp_path):
    store = GlobalCapitalMarketsStore(tmp_path)

    store.save_global_capital_markets(
        as_of_date="2026-02-22",
        generated_by="pytest",
        validate=True,
    )
    store.save_global_capital_markets(
        as_of_date="2026-02-23",
        generated_by="pytest",
        validate=True,
    )

    ids = store.list_snapshots()
    assert ids == ["2026-02-22", "2026-02-23"]


def test_global_capital_markets_exists(tmp_path):
    store = GlobalCapitalMarketsStore(tmp_path)

    assert store.global_capital_markets_exists("2026-02-22") is False

    store.save_global_capital_markets(
        as_of_date="2026-02-22",
        generated_by="pytest",
        validate=True,
    )

    assert store.global_capital_markets_exists("2026-02-22") is True
    assert store.snapshot_exists("2026-02-22") is True