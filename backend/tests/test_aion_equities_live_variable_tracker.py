from __future__ import annotations

from backend.modules.aion_equities.company_trigger_map_store import (
    CompanyTriggerMapStore,
)
from backend.modules.aion_equities.feed_registry import FeedRegistry
from backend.modules.aion_equities.live_variable_tracker import LiveVariableTracker


def test_live_variable_tracker_updates_cross_above_trigger(tmp_path):
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()

    feed_registry.register_feed(
        feed_id="REC_UK_PLACEMENTS",
        source_type="macro_print",
        description="KPMG REC UK permanent placements index",
        frequency="monthly",
    )

    trigger_store.save_trigger_map(
        company_ref="company/PAGE.L",
        fiscal_period_ref="2026Q1",
        as_of_date="2026-02-01",
        generated_by="pytest",
        triggers=[
            {
                "trigger_id": "uk_recovery",
                "variable_name": "UK permanent placements",
                "data_source": "REC_UK_PLACEMENTS",
                "current_state": "inactive",
                "threshold_rule": "cross_above:50",
                "lag_expectation": "1m",
                "impact_direction": "positive",
                "impact_weight": 0.8,
                "confidence": 72.0,
                "thesis_action": "elevate_long_candidate",
            }
        ],
        validate=False,
    )

    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    out = tracker.track_feed_value(
        feed_id="REC_UK_PLACEMENTS",
        value=51.2,
        as_of="2026-02-10T08:00:00Z",
    )

    assert out["feed_id"] == "REC_UK_PLACEMENTS"
    assert len(out["updates"]) == 1
    assert out["updates"][0]["state"] == "confirmed"

    loaded = trigger_store.load_latest_trigger_map("company/PAGE.L")
    trig = loaded["triggers"][0]
    assert trig["latest_value"] == 51.2
    assert trig["current_state"] == "confirmed"


def test_live_variable_tracker_updates_two_consecutive_improvements(tmp_path):
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()

    feed_registry.register_feed(
        feed_id="FR_CONFIDENCE",
        source_type="macro_print",
        description="France confidence index",
        frequency="monthly",
    )

    trigger_store.save_trigger_map(
        company_ref="company/PAGE.L",
        fiscal_period_ref="2026Q1",
        as_of_date="2026-02-01",
        generated_by="pytest",
        triggers=[
            {
                "trigger_id": "france_recovery",
                "variable_name": "France confidence",
                "data_source": "FR_CONFIDENCE",
                "current_state": "inactive",
                "threshold_rule": "two_consecutive_improvements",
                "lag_expectation": "2m",
                "impact_direction": "positive",
                "impact_weight": 0.9,
                "confidence": 74.0,
                "thesis_action": "elevate_long_candidate",
                "latest_value": 95.0,
            }
        ],
        validate=False,
    )

    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    tracker.track_feed_value(
        feed_id="FR_CONFIDENCE",
        value=96.0,
        as_of="2026-02-20T08:00:00Z",
    )
    loaded_1 = trigger_store.load_latest_trigger_map("company/PAGE.L")
    assert loaded_1["triggers"][0]["current_state"] == "building"

    tracker.track_feed_value(
        feed_id="FR_CONFIDENCE",
        value=97.0,
        as_of="2026-03-20T08:00:00Z",
    )
    loaded_2 = trigger_store.load_latest_trigger_map("company/PAGE.L")
    assert loaded_2["triggers"][0]["current_state"] == "confirmed"


def test_live_variable_tracker_keeps_company_variable_history(tmp_path):
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()

    feed_registry.register_feed(
        feed_id="EURUSD",
        source_type="fx",
        description="EUR/USD spot",
        frequency="daily",
    )

    trigger_store.save_trigger_map(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026Q1",
        as_of_date="2026-02-01",
        generated_by="pytest",
        triggers=[
            {
                "trigger_id": "eurusd_fx",
                "variable_name": "EURUSD",
                "data_source": "EURUSD",
                "current_state": "inactive",
                "threshold_rule": "manual",
                "lag_expectation": "0d",
                "impact_direction": "positive",
                "impact_weight": 0.6,
                "confidence": 80.0,
                "thesis_action": "refresh_pre_earnings",
            }
        ],
        validate=False,
    )

    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    tracker.track_feed_value(feed_id="EURUSD", value=1.081)
    tracker.track_feed_value(feed_id="EURUSD", value=1.076)

    hist = tracker.get_company_variable_history("company/ULVR.L")
    assert len(hist) == 2
    assert hist[0]["feed_id"] == "EURUSD"
    assert hist[1]["value"] == 1.076


def test_live_variable_tracker_rejects_unknown_feed(tmp_path):
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()

    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    try:
        tracker.track_feed_value(feed_id="UNKNOWN_FEED", value=1.0)
        assert False, "Expected KeyError"
    except KeyError:
        assert True