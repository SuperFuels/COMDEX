from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.pair_context_store import (
    PairContextStore,
)


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_pair_context(tmp_path):
    store = PairContextStore(tmp_path)

    payload = store.save_pair_context(
        pair="USDJPY",
        base_country_ref="country/US",
        quote_country_ref="country/JP",
        as_of_date=_dt(2026, 5, 1, 8, 0, 0),
        generated_by="pytest",
        macro_coherence_patch={
            "score": 74.0,
            "regime_alignment": "mixed",
            "notes": "Dollar strong but carry unwind risk elevated.",
        },
        carry_signal_patch={
            "state": "unwind_risk",
            "strength": 81.0,
        },
        risk_appetite_signal_patch={
            "state": "risk_off",
            "confidence": 77.0,
        },
        pair_score_patch={
            "direction_bias": "quote_outperform",
            "conviction": 69.0,
            "summary": "Yen support likely if carry stress accelerates.",
        },
        linked_refs_patch={
            "country_ambassador_refs": ["country/US", "country/JP"],
            "country_relationship_refs": ["relationship/US-JP"],
            "global_capital_markets_refs": ["macro/global_capital_markets/2026-05-01"],
        },
        validate=True,
    )

    assert payload["pair"] == "USDJPY"
    assert payload["as_of_date"] == "2026-05-01"

    loaded = store.load_pair_context("USDJPY", as_of_date="2026-05-01")

    assert loaded["pair_context_id"] == payload["pair_context_id"]
    assert loaded["carry_signal"]["state"] == "unwind_risk"
    assert loaded["pair_score"]["direction_bias"] == "quote_outperform"


def test_list_pair_contexts(tmp_path):
    store = PairContextStore(tmp_path)

    store.save_pair_context(
        pair="EURUSD",
        base_country_ref="country/EU",
        quote_country_ref="country/US",
        as_of_date="2026-02-22",
        generated_by="pytest",
        validate=True,
    )

    store.save_pair_context(
        pair="EURUSD",
        base_country_ref="country/EU",
        quote_country_ref="country/US",
        as_of_date="2026-03-31",
        generated_by="pytest",
        validate=True,
    )

    ids = store.list_pair_contexts("EURUSD")
    assert ids == ["2026-02-22", "2026-03-31"]


def test_pair_context_exists(tmp_path):
    store = PairContextStore(tmp_path)

    assert not store.context_exists("GBPUSD", as_of_date="2026-04-15")

    store.save_context(
        pair="GBPUSD",
        base_country_ref="country/GB",
        quote_country_ref="country/US",
        as_of_date="2026-04-15",
        generated_by="pytest",
        validate=True,
    )

    assert store.context_exists("GBPUSD", as_of_date="2026-04-15")