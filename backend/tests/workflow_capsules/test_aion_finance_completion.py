from backend.modules.aion_business.runtime.finance_completion_service import (
    build_finance_completion,
    seed_operating_model,
)
from pathlib import Path


def _financial():
    facts = [
        ("external_data.revenue.net_sales", "net_sales", 378750),
        ("external_data.costs.total_direct_costs", "total_direct_costs", 143734),
        ("external_data.profit.gross_profit", "gross_profit", 235016),
        ("external_data.costs.operating_expenses", "operating_expenses", 82670),
        ("external_data.profit.operating_profit", "operating_profit", 152346),
        ("external_data.tax.profit_before_tax", "profit_before_tax", 146586),
        ("external_data.tax.tax", "tax", 36648),
        ("external_data.profit.net_profit", "net_profit", 109938),
        ("external_data.cash.cash_collections", "cash_collections", 454840),
        ("external_data.cash.cash_payments", "cash_payments", 308329),
        ("external_data.cash.ending_cash", "ending_cash", 159011),
        ("external_data.revenue.handyman_sales", "handyman_sales", 109839),
    ]
    return {
        "currency": "euros",
        "metrics": {"average_monthly_revenue": {"value": 205156.5}},
        "discovery_state": {
            "answers": {
                "revenue_model": "I typically charge 200 euros per day and add 20% on materials",
                "payment_terms": "I take a 50% deposit and the rest on completion",
                "cash_buffer_policy": "Keep a minimum 3500 euros",
            }
        },
        "external_data": {
            "artifacts": {
                "artifact-1": {
                    "artifact_id": "artifact-1",
                    "filename": "Management_Accounts_2025.xlsx",
                    "verification_status": "accepted_from_source_document",
                    "facts": [
                        {"field": field, "source_column": column, "value": value}
                        for field, column, value in facts
                    ],
                }
            }
        },
    }


def test_source_backed_completion_overrides_bad_discovery_metric():
    result = build_finance_completion(_financial())
    assert result["currency"] == "EUR"
    assert result["period"]["label"] == "FY2025"
    assert result["authoritative_metrics"]["revenue"]["value"] == 378750
    assert result["authoritative_metrics"]["average_monthly_revenue"]["value"] == 31562.5
    assert result["financial_statements"]["profit_and_loss"]["status"] == "source_backed"
    assert result["financial_statements"]["profit_and_loss"]["lines"][-1]["value"] == 109938


def test_cash_flow_is_source_backed_but_balance_sheet_stays_honestly_partial():
    result = build_finance_completion(_financial())
    cash = result["financial_statements"]["cash_flow"]
    assert cash["opening_cash"] == 12500
    assert cash["net_cash_change"] == 146511
    assert cash["ending_cash"] == 159011
    assert cash["status"] == "source_backed_summary"
    balance = result["financial_statements"]["balance_sheet"]
    assert balance["status"] == "partial"
    assert balance["balance_check"]["available"] is False
    assert "owner equity and retained earnings" in balance["missing_information"]


def test_operating_model_seed_is_reviewable_and_never_claims_unknown_unit_margin():
    financial = _financial()
    completion = build_finance_completion(financial)
    model = seed_operating_model(financial, completion)
    assert model["model_status"] == "needs_user_review"
    assert model["offerings"][0]["name"] == "Standard labour day rate"
    assert model["offerings"][0]["price"] == 200
    assert model["offerings"][1]["historical_annual_revenue"] == 109839
    assert model["pricing_rules"][0]["markup_percent"] == 20
    assert model["payment_terms"][0]["deposit_percent"] == 50
    assert model["unit_economics"] == []


def test_desktop_completion_and_light_statement_workspace_are_wired():
    client = Path("desktop/mac/src/aion_business_container_client.js").read_text()
    pilot = Path("desktop/mac/src/aion_finance_pilot.js").read_text()
    runtime = Path("desktop/mac/src/aion_department_pilot_backend.js").read_text()
    assert "/api/aion/business/data/finance-completion/" in client
    assert "completeFinanceFoundation" in pilot
    assert "CANONICAL FINANCIAL VIEW" in runtime
    assert "Business model · P&amp;L · Balance sheet · Cash flow" in runtime
    assert "--fin-ink:#102a43" in runtime
    assert 'background:#fff !important;color:var(--fin-ink)' in runtime


def test_desktop_recovery_cache_cannot_embed_previous_raw_payload():
    contracts = Path("desktop/mac/src/lib/desktop-state-contracts.js").read_text()
    assert 'key === "raw"' in contracts
    assert 'key === "recoveryPayload"' in contracts
    assert "raw: clone(rawSource)" in contracts
    assert "raw: clone(next)" not in contracts


def test_legacy_boardroom_package_bridge_is_idempotent_and_not_self_triggering():
    app = Path("desktop/mac/src/app.js").read_text()
    assert "if (!changed) return result;" in app
    assert "if (!existingPackage && typeof window.aionStageBoardroomPackagesToDepartmentPilotsO14A" in app
    assert "if (syncScheduledO14A3 || syncRunningO14A3) return;" in app
