from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_finance_pilot_exposes_structured_scenarios_without_touching_app_js():
    source = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text(encoding="utf-8")
    assert "data-aion-finance-scenario-form" in source
    assert "data-aion-finance-run-scenario" in source
    assert "runFinanceScenario" in source
    assert "/finance/scenarios/run" in source
    assert "Planning model · not actuals" in source
    assert "never overwrite accounting evidence or accepted historical facts" in source
    for field in (
        "forecast_months",
        "revenue_change_percent",
        "price_change_percent",
        "volume_change_percent",
        "direct_cost_change_percent",
        "overhead_change_percent",
        "monthly_hiring_cost",
        "one_off_stock_purchase",
        "minimum_cash_reserve",
        "sensitivity_percent",
    ):
        assert f'name="{field}"' in source


def test_finance_pilot_exposes_read_only_reconciliation_and_review_controls():
    source = (ROOT / "desktop/mac/src/aion_department_pilot_backend.js").read_text(encoding="utf-8")
    assert "data-aion-finance-reconciliation-form" in source
    assert "Compare accepted files with Xero" in source
    assert "data-aion-reconciliation-review" in source
    assert "keep_spreadsheet" in source
    assert "prefer_xero" in source
    assert "needs_investigation" in source
    assert "No accepted fact is replaced by this check" in source
