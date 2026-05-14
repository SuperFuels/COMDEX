from __future__ import annotations

from backend.modules.aion_equities.company_trigger_map_store import (
    CompanyTriggerMapStore,
)
from backend.modules.aion_equities.feed_registry import FeedRegistry
from backend.modules.aion_equities.live_variable_tracker import LiveVariableTracker
from backend.modules.aion_equities.pilot_company_seed import PilotCompanySeedStore
from backend.modules.aion_equities.pilot_pre_earnings_runtime import (
    PilotPreEarningsRuntime,
)


def _setup_company_seed(seed_store: PilotCompanySeedStore) -> None:
    seed_store.save_company_seed(
        company_id="company/ULVR.L",
        ticker="ULVR.L",
        name="Unilever PLC",
        sector="consumer_staples",
        country="UK",
        generated_by="pytest",
        payload_patch={
            "predictability_profile": {
                "acs_band": "high",
                "sector_confidence_tier": "tier_1",
            },
            "sector_template_ref": "sector_template/consumer_staples",
            "fingerprint_ref": "company/ULVR.L/fingerprint/latest",
            "credit_profile_ref": "company/ULVR.L/credit_profile/latest",
            "pair_context_ref": "pair_context/ULVR.L/latest",
        },
        validate=False,
    )


def test_pilot_pre_earnings_runtime_builds_positive_long_candidate(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()
    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    _setup_company_seed(seed_store)

    feed_registry.register_feed(
        feed_id="EURUSD",
        source_type="fx",
        description="EUR/USD spot",
        frequency="daily",
    )

    trigger_store.save_trigger_map(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q1",
        generated_by="pytest",
        triggers=[
            {
                "trigger_id": "eurusd_tailwind",
                "variable_name": "EURUSD",
                "data_source": "EURUSD",
                "current_state": "confirmed",
                "threshold_rule": "manual",
                "lag_expectation": "0d",
                "impact_direction": "positive",
                "impact_weight": 0.8,
                "confidence": 78.0,
                "thesis_action": "refresh_pre_earnings",
                "latest_value": 1.07,
            },
            {
                "trigger_id": "fx_translation_support",
                "variable_name": "EURUSD support",
                "data_source": "EURUSD",
                "current_state": "building",
                "threshold_rule": "manual",
                "lag_expectation": "0d",
                "impact_direction": "positive",
                "impact_weight": 0.4,
                "confidence": 70.0,
                "thesis_action": "elevate_long_candidate",
                "latest_value": 1.07,
            },
        ],
        validate=False,
    )

    tracker.track_feed_value(feed_id="EURUSD", value=1.071)
    tracker.track_feed_value(feed_id="EURUSD", value=1.069)

    runtime = PilotPreEarningsRuntime(
        pilot_company_seed_store=seed_store,
        trigger_map_store=trigger_store,
        live_variable_tracker=tracker,
    )

    out = runtime.build_pre_earnings_estimate(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q1",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        assessment_ref="assessment/company/ULVR.L/2026-03-01",
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert out["company_ref"] == "company/ULVR.L"
    assert out["pre_earnings_estimate_id"] == "company/ULVR.L/pre_earnings/2026-Q1"
    assert out["trigger_summary"]["confirmed_trigger_count"] == 1
    assert out["trigger_summary"]["building_trigger_count"] == 1
    assert out["divergence"]["divergence_score"] > 0.0
    assert out["divergence"]["confidence"] >= 50.0
    assert out["signal"]["long_candidate"] is True
    assert out["signal"]["short_candidate"] is False


def test_pilot_pre_earnings_runtime_handles_broken_negative_setup(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()
    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    _setup_company_seed(seed_store)

    trigger_store.save_trigger_map(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q2",
        generated_by="pytest",
        triggers=[
            {
                "trigger_id": "margin_pressure",
                "variable_name": "Input cost pressure",
                "data_source": "PALM_OIL",
                "current_state": "broken",
                "threshold_rule": "manual",
                "lag_expectation": "1m",
                "impact_direction": "negative",
                "impact_weight": 0.9,
                "confidence": 73.0,
                "thesis_action": "reduce_conviction",
            }
        ],
        validate=False,
    )

    runtime = PilotPreEarningsRuntime(
        pilot_company_seed_store=seed_store,
        trigger_map_store=trigger_store,
        live_variable_tracker=tracker,
    )

    out = runtime.build_pre_earnings_estimate(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q2",
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert out["trigger_summary"]["broken_trigger_count"] == 1
    assert out["signal"]["long_candidate"] is False
    assert out["divergence"]["confidence"] < 50.0


def test_pilot_pre_earnings_runtime_mixed_signal_lowers_net_signal(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()
    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    _setup_company_seed(seed_store)

    trigger_store.save_trigger_map(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q3",
        generated_by="pytest",
        triggers=[
            {
                "trigger_id": "positive_fx",
                "variable_name": "FX tailwind",
                "data_source": "EURUSD",
                "current_state": "confirmed",
                "threshold_rule": "manual",
                "lag_expectation": "0d",
                "impact_direction": "positive",
                "impact_weight": 0.5,
                "confidence": 76.0,
                "thesis_action": "support_long",
            },
            {
                "trigger_id": "negative_cost",
                "variable_name": "Input costs",
                "data_source": "PALM_OIL",
                "current_state": "confirmed",
                "threshold_rule": "manual",
                "lag_expectation": "0d",
                "impact_direction": "negative",
                "impact_weight": 0.5,
                "confidence": 76.0,
                "thesis_action": "contradict_long",
            },
        ],
        validate=False,
    )

    runtime = PilotPreEarningsRuntime(
        pilot_company_seed_store=seed_store,
        trigger_map_store=trigger_store,
        live_variable_tracker=tracker,
    )

    out = runtime.build_pre_earnings_estimate(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q3",
        write_to_kg=False,
        write_to_sqi_container=False,
    )

    assert abs(out["trigger_summary"]["net_signal"]) < 1e-9
    assert out["divergence"]["divergence_score"] == 0.0
    assert out["signal"]["long_candidate"] is False
    assert out["signal"]["short_candidate"] is False


def test_pilot_pre_earnings_runtime_can_write_to_real_bridges(tmp_path):
    seed_store = PilotCompanySeedStore(tmp_path)
    trigger_store = CompanyTriggerMapStore(tmp_path)
    feed_registry = FeedRegistry()
    tracker = LiveVariableTracker(
        trigger_map_store=trigger_store,
        feed_registry=feed_registry,
    )

    _setup_company_seed(seed_store)

    trigger_store.save_trigger_map(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q4",
        generated_by="pytest",
        triggers=[
            {
                "trigger_id": "recovery_signal",
                "variable_name": "Recovery",
                "data_source": "RECOVERY_FEED",
                "current_state": "confirmed",
                "threshold_rule": "manual",
                "lag_expectation": "1m",
                "impact_direction": "positive",
                "impact_weight": 0.7,
                "confidence": 79.0,
                "thesis_action": "elevate_long_candidate",
            }
        ],
        validate=False,
    )

    runtime = PilotPreEarningsRuntime(
        pilot_company_seed_store=seed_store,
        trigger_map_store=trigger_store,
        live_variable_tracker=tracker,
    )

    out = runtime.run_first_pass_for_company(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026-Q4",
        thesis_ref="thesis/ULVR.L/long/medium_term",
        assessment_ref="assessment/company/ULVR.L/2026-03-01",
        write_to_kg=True,
        write_to_sqi_container=True,
    )

    assert out["linked_refs"]["company_ref"] == "company/ULVR.L"
    assert out["linked_refs"]["trigger_map_ref"] == "company/ULVR.L/trigger_map/2026-Q4"
    assert out["signal"]["long_candidate"] is True