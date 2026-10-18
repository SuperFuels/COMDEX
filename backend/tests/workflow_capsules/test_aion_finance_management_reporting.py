from __future__ import annotations

from backend.modules.aion_business.runtime.finance_management_report_builder import (
    build_finance_management_report,
)


def _row(report: dict, key: str) -> dict:
    return next(item for item in report["kpis"] if item["key"] == key)


def test_management_report_calculates_kpis_and_period_comparisons_from_canonical_values():
    report = build_finance_management_report(
        {
            "currency": "EUR",
            "period_basis": "annual",
            "reporting_period": {
                "label": "Year ended 31 December 2025",
                "from": "2025-01-01",
                "to": "2025-12-31",
            },
            "reporting_periods": {
                "current": {
                    "metrics": {
                        "revenue": {"value": 120000, "verification": "accepted_from_source_document"},
                        "direct_costs": 45000,
                        "overheads": 25000,
                        "ending_cash": 30000,
                        "debtors": 14000,
                        "creditors": 9000,
                    }
                },
                "budget": {
                    "metrics": {
                        "revenue": 100000,
                        "direct_costs": 40000,
                        "overheads": 24000,
                        "ending_cash": 25000,
                    }
                },
                "previous": {
                    "metrics": {
                        "revenue": 90000,
                        "direct_costs": 36000,
                        "overheads": 22000,
                        "ending_cash": 20000,
                    }
                },
            },
            "evidence_refs": [
                {
                    "source": "management_accounts",
                    "accepted_at": "2026-07-10T12:00:00+00:00",
                    "verification_status": "accepted_from_source_document",
                }
            ],
        },
        generated_at="2026-07-20T12:00:00+00:00",
    )

    assert report["schema_version"] == "aion.finance_pilot.management_accounts.v2"
    assert report["period"]["label"] == "Year ended 31 December 2025"
    assert report["comparison_coverage"] == {
        "budget_available": True,
        "previous_period_available": True,
        "budget_metric_count": 8,
        "previous_period_metric_count": 8,
    }
    assert _row(report, "gross_profit")["actual"] == 75000
    assert _row(report, "gross_margin_percent")["actual"] == 62.5
    assert _row(report, "operating_profit")["actual"] == 50000
    assert _row(report, "operating_margin_percent")["actual"] == 41.6667
    assert _row(report, "revenue")["budget_variance"] == 20000
    assert _row(report, "revenue")["budget_variance_percent"] == 20
    assert _row(report, "revenue")["previous_variance"] == 30000
    assert _row(report, "revenue")["previous_variance_percent"] == 33.3333
    assert report["evidence_freshness"]["overall_state"] == "fresh"
    assert report["warnings"] == []


def test_management_report_exposes_missing_comparisons_period_and_stale_evidence():
    report = build_finance_management_report(
        {
            "currency": "EUR",
            "metrics": {
                "revenue": 378750,
                "gross_profit": 235016,
                "operating_profit": 152346,
                "ending_cash": 159011,
            },
            "evidence_refs": [
                {
                    "source": "uploaded_workbook",
                    "accepted_at": "2025-12-31T12:00:00+00:00",
                    "verification_status": "accepted_from_source_document",
                }
            ],
        },
        generated_at="2026-07-20T12:00:00+00:00",
    )

    assert report["headline"] == {
        "revenue": 378750.0,
        "gross_profit": 235016.0,
        "operating_profit": 152346.0,
        "ending_cash": 159011.0,
    }
    assert report["period"]["explicit"] is False
    assert report["comparison_coverage"]["budget_available"] is False
    assert report["comparison_coverage"]["previous_period_available"] is False
    assert report["evidence_freshness"]["overall_state"] == "stale"
    assert any("reporting period" in item for item in report["warnings"])
    assert any("budget" in item for item in report["warnings"])
    assert any("previous period" in item for item in report["warnings"])
    assert any("stale" in item for item in report["warnings"])


def test_management_report_uses_accepted_artifact_facts_and_refuses_conflicts():
    report = build_finance_management_report(
        {
            "currency": "EUR",
            "external_data": {
                "artifacts": {
                    "management-accounts": {
                        "artifact_id": "management-accounts",
                        "verification_status": "accepted_from_source_document",
                        "facts": [
                            {"source_column": "revenue", "value": 378750},
                            {"source_column": "total_direct_costs", "value": 143734},
                            {"source_column": "gross_profit", "value": 235016},
                            {"source_column": "operating_profit", "value": 152346},
                            {"source_column": "ending_cash", "value": 159011},
                        ],
                    },
                    "conflicting-cash-report": {
                        "artifact_id": "conflicting-cash-report",
                        "verification_status": "accepted_from_source_document",
                        "facts": [{"source_column": "ending_cash", "value": 125000}],
                    },
                }
            },
            "evidence_refs": [
                {
                    "source": "user_uploaded_finance_artifact",
                    "accepted_at": "2026-07-20T10:00:00+00:00",
                    "verification_status": "accepted_from_source_document",
                }
            ],
        },
        generated_at="2026-07-20T12:00:00+00:00",
    )

    assert report["headline"]["revenue"] == 378750
    assert report["headline"]["gross_profit"] == 235016
    assert report["headline"]["operating_profit"] == 152346
    assert report["headline"]["ending_cash"] is None
    assert _row(report, "gross_margin_percent")["actual"] == 62.0504
    assert any("conflicting values for ending cash" in item for item in report["warnings"])
