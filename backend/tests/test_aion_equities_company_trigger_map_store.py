from __future__ import annotations

from backend.modules.aion_equities.company_trigger_map_store import (
    CompanyTriggerMapStore,
    build_company_trigger_map_payload,
)


def test_build_company_trigger_map_payload_normalizes_entries():
    payload = build_company_trigger_map_payload(
        company_ref="company/PAGE.L",
        fiscal_period_ref="2026Q1",
        generated_by="pytest",
        trigger_entries=[
            {
                "variable_name": "uk_perm_placements",
                "data_source": "REC_UK_PERM",
                "current_state": "building",
                "threshold_rule": "cross_above_50_for_two_months",
                "lag_expectation": "6_to_8_weeks",
                "impact_direction": "positive",
                "impact_weight": 0.7,
                "confidence": 82.0,
                "thesis_action": "elevate_long_candidate",
                "linked_report_ref": "company/PAGE.L/quarter/2025-Q4",
            },
            {
                "variable_name": "france_business_confidence",
                "data_source": "INSEE_BUSINESS_CLIMATE",
                "current_state": "confirmed",
                "threshold_rule": "two_consecutive_improvements",
                "lag_expectation": "4_to_8_weeks",
                "impact_direction": "positive",
                "impact_weight": 0.9,
                "confidence": 88.0,
                "thesis_action": "promote_deployment_readiness",
            },
        ],
        validate=False,
    )

    assert payload["company_trigger_map_id"] == "company/PAGE.L/trigger_map/2026Q1"
    assert payload["summary"]["active_trigger_count"] == 2
    assert payload["summary"]["confirmed_trigger_count"] == 1
    assert payload["summary"]["broken_trigger_count"] == 0
    assert len(payload["trigger_entries"]) == 2
    assert payload["trigger_entries"][0]["trigger_id"].startswith(
        "company/PAGE.L/trigger/2026Q1/"
    )


def test_save_and_load_company_trigger_map(tmp_path):
    store = CompanyTriggerMapStore(tmp_path)

    payload = store.save_company_trigger_map(
        company_ref="company/PAGE.L",
        fiscal_period_ref="2026Q1",
        generated_by="pytest",
        trigger_entries=[
            {
                "trigger_id": "company/PAGE.L/trigger/2026Q1/uk_recovery",
                "variable_name": "uk_perm_placements",
                "data_source": "REC_UK_PERM",
                "current_state": "early_watch",
                "threshold_rule": "cross_above_50_for_two_months",
                "lag_expectation": "6_to_8_weeks",
                "impact_direction": "positive",
                "impact_weight": 0.6,
                "confidence": 75.0,
                "thesis_action": "watch_for_long_upgrade",
            },
            {
                "trigger_id": "company/PAGE.L/trigger/2026Q1/france_recovery",
                "variable_name": "fr_consumer_confidence",
                "data_source": "GFK_FR_CONSUMER",
                "current_state": "inactive",
                "threshold_rule": "two_consecutive_improvements",
                "lag_expectation": "4_to_8_weeks",
                "impact_direction": "positive",
                "impact_weight": 0.8,
                "confidence": 79.0,
                "thesis_action": "upgrade_recovery_signal",
            },
        ],
        linked_refs_patch={
            "report_refs": ["company/PAGE.L/quarter/2025-Q4"],
        },
        validate=False,
    )

    assert payload["summary"]["active_trigger_count"] == 1
    assert store.trigger_map_exists("company/PAGE.L", "2026Q1")

    loaded = store.load_company_trigger_map("company/PAGE.L", "2026Q1", validate=False)
    assert loaded["company_trigger_map_id"] == payload["company_trigger_map_id"]
    assert loaded["linked_refs"]["report_refs"] == ["company/PAGE.L/quarter/2025-Q4"]
    assert loaded["trigger_entries"][0]["current_state"] == "early_watch"


def test_load_company_trigger_map_by_id(tmp_path):
    store = CompanyTriggerMapStore(tmp_path)

    payload = store.save_company_trigger_map(
        company_ref="company/ULVR.L",
        fiscal_period_ref="2026Q2",
        generated_by="pytest",
        trigger_entries=[
            {
                "variable_name": "eurusd_translation",
                "data_source": "FX_EURUSD",
                "current_state": "confirmed",
                "threshold_rule": "usd_strength_gt_3pct_qtd",
                "lag_expectation": "immediate_translation",
                "impact_direction": "positive",
                "impact_weight": 0.9,
                "confidence": 91.0,
                "thesis_action": "raise_pre_earnings_estimate",
            }
        ],
        validate=False,
    )

    loaded = store.load_company_trigger_map_by_id(
        payload["company_trigger_map_id"],
        validate=False,
    )
    assert loaded["company_ref"] == "company/ULVR.L"
    assert loaded["fiscal_period_ref"] == "2026Q2"
    assert loaded["summary"]["confirmed_trigger_count"] == 1


def test_list_trigger_maps(tmp_path):
    store = CompanyTriggerMapStore(tmp_path)

    store.save_company_trigger_map(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026Q1",
        generated_by="pytest",
        trigger_entries=[],
        validate=False,
    )
    store.save_company_trigger_map(
        company_ref="company/AHT.L",
        fiscal_period_ref="2026Q2",
        generated_by="pytest",
        trigger_entries=[],
        validate=False,
    )

    assert store.list_trigger_maps("company/AHT.L") == ["2026Q1", "2026Q2"]