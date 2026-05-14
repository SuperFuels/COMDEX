from __future__ import annotations

from datetime import datetime, timezone

from backend.modules.aion_equities.post_report_calibration_store import (
    PostReportCalibrationStore,
)


def _dt(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc)


def test_save_and_load_post_report_calibration(tmp_path):
    store = PostReportCalibrationStore(tmp_path)

    payload = store.save_post_report_calibration(
        company_ref="company/ULVR.L",
        as_of_date=_dt(2026, 4, 30, 9, 0, 0),
        report_ref="company/ULVR.L/quarter/2026-Q1",
        prediction_ref="company/ULVR.L/pre_earnings/2026-04-29",
        generated_by="pytest",
        actuals_patch={
            "reported_revenue": 12650.0,
            "reported_operating_margin": 19.8,
            "reported_eps": 1.24,
        },
        prediction_comparison_patch={
            "revenue_error_pct": 1.8,
            "margin_error_bps": -25.0,
            "prediction_quality": "acceptable",
            "summary": "Revenue close, margin slightly missed.",
        },
        calibration_actions_patch={
            "sensitivity_update_required": True,
            "lag_update_required": False,
            "guidance_bias_update_required": True,
        },
        confidence_drift_patch={
            "previous_confidence": 78.0,
            "new_confidence": 74.0,
            "drift_reason": "Margin sensitivity slightly overstated.",
        },
        linked_refs_patch={
            "fingerprint_refs": ["company/ULVR.L/fingerprint/2026-02-28"],
            "pre_earnings_refs": ["company/ULVR.L/pre_earnings/2026-04-29"],
            "quarter_event_refs": ["company/ULVR.L/quarter/2026-Q1"],
        },
        validate=True,
    )

    assert payload["company_ref"] == "company/ULVR.L"
    assert payload["as_of_date"] == "2026-04-30"

    loaded = store.load_post_report_calibration(
        "company/ULVR.L",
        as_of_date="2026-04-30",
    )

    assert loaded["post_report_calibration_id"] == payload["post_report_calibration_id"]
    assert loaded["actuals"]["reported_revenue"] == 12650.0
    assert loaded["prediction_comparison"]["prediction_quality"] == "acceptable"
    assert loaded["confidence_drift"]["new_confidence"] == 74.0


def test_list_calibrations(tmp_path):
    store = PostReportCalibrationStore(tmp_path)

    store.save_post_report_calibration(
        company_ref="company/AHT.L",
        as_of_date="2026-02-22",
        report_ref="company/AHT.L/quarter/2025-Q4",
        prediction_ref="company/AHT.L/pre_earnings/2026-02-21",
        generated_by="pytest",
        validate=True,
    )

    store.save_post_report_calibration(
        company_ref="company/AHT.L",
        as_of_date="2026-03-31",
        report_ref="company/AHT.L/quarter/2026-Q1",
        prediction_ref="company/AHT.L/pre_earnings/2026-03-30",
        generated_by="pytest",
        validate=True,
    )

    ids = store.list_calibrations("company/AHT.L")
    assert ids == ["2026-02-22", "2026-03-31"]


def test_calibration_exists(tmp_path):
    store = PostReportCalibrationStore(tmp_path)

    assert not store.calibration_exists(
        "company/ULVR.L",
        as_of_date="2026-04-30",
    )

    store.save_calibration(
        company_ref="company/ULVR.L",
        as_of_date="2026-04-30",
        report_ref="company/ULVR.L/quarter/2026-Q1",
        prediction_ref="company/ULVR.L/pre_earnings/2026-04-29",
        generated_by="pytest",
        validate=True,
    )

    assert store.calibration_exists(
        "company/ULVR.L",
        as_of_date="2026-04-30",
    )