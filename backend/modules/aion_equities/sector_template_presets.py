from __future__ import annotations

from typing import Any, Dict, List

# Minimal v0 presets. Keep them lightweight and extensible.
# The intent is: sector template provides variable map + reporting focus + fingerprint defaults
# that downstream fingerprint calibration can start from.

def get_sector_template_presets_v0() -> List[Dict[str, Any]]:
    return [
        {
            "sector_ref": "sector/staffing",
            "sector_name": "Staffing / Recruitment",
            "variable_map_patch": {
                "primary_variables": [
                    {"name": "net_fee_growth", "feed_id": "feed/company/net_fee_growth", "importance": "primary"},
                    {"name": "perm_fees_share", "feed_id": "feed/company/perm_fees_share", "importance": "primary"},
                    {"name": "temp_fees_share", "feed_id": "feed/company/temp_fees_share", "importance": "secondary"},
                    {"name": "headcount", "feed_id": "feed/company/headcount", "importance": "secondary"},
                ],
                "secondary_variables": [
                    {"name": "wage_inflation", "feed_id": "feed/macro/wage_inflation", "importance": "secondary"},
                    {"name": "unemployment_rate", "feed_id": "feed/macro/unemployment", "importance": "secondary"},
                    {"name": "job_openings", "feed_id": "feed/macro/job_openings", "importance": "secondary"},
                ],
            },
            "reporting_template_patch": {
                "core_metrics": ["net_fees", "gross_profit", "operating_profit", "cash_conversion"],
                "margin_focus": ["operating_margin", "gross_profit_margin"],
                "cash_flow_focus": ["free_cash_flow", "working_capital_movement"],
                "balance_sheet_focus": ["net_cash_net_debt", "lease_liabilities"],
                "management_signals": ["consultant_productivity", "hiring_freeze_or_acceleration", "regional_mix_shifts"],
            },
            "fingerprint_defaults_patch": {
                "expected_report_count_for_calibration": 20,
                "base_predictability": "high",
                "seasonality_strength": "medium",
                "macro_sensitivity": "high",
            },
        },
        {
            "sector_ref": "sector/plant_hire",
            "sector_name": "Plant Hire / Equipment Rental",
            "variable_map_patch": {
                "primary_variables": [
                    {"name": "fleet_utilisation", "feed_id": "feed/company/fleet_utilisation", "importance": "primary"},
                    {"name": "rental_rate_growth", "feed_id": "feed/company/rental_rate_growth", "importance": "primary"},
                    {"name": "capex", "feed_id": "feed/company/capex", "importance": "secondary"},
                    {"name": "used_equipment_sale_prices", "feed_id": "feed/sector/used_equipment_prices", "importance": "secondary"},
                ],
                "secondary_variables": [
                    {"name": "construction_activity", "feed_id": "feed/macro/construction_activity", "importance": "secondary"},
                    {"name": "industrial_production", "feed_id": "feed/macro/industrial_production", "importance": "secondary"},
                    {"name": "credit_spreads", "feed_id": "feed/macro/credit_spreads", "importance": "secondary"},
                ],
            },
            "reporting_template_patch": {
                "core_metrics": ["rental_revenue", "utilisation", "rate", "ebitda", "free_cash_flow"],
                "margin_focus": ["ebitda_margin", "operating_margin"],
                "cash_flow_focus": ["free_cash_flow", "capex_intensity"],
                "balance_sheet_focus": ["net_debt", "debt_maturity_profile", "interest_coverage"],
                "management_signals": ["fleet_age", "discipline_on_capex", "demand_commentary"],
            },
            "fingerprint_defaults_patch": {
                "expected_report_count_for_calibration": 20,
                "base_predictability": "high",
                "seasonality_strength": "low",
                "macro_sensitivity": "medium",
            },
        },
        {
            "sector_ref": "sector/consumer_staples",
            "sector_name": "Consumer Staples",
            "variable_map_patch": {
                "primary_variables": [
                    {"name": "like_for_like_sales", "feed_id": "feed/company/like_for_like_sales", "importance": "primary"},
                    {"name": "pricing_vs_volume_mix", "feed_id": "feed/company/pricing_volume_mix", "importance": "primary"},
                    {"name": "gross_margin", "feed_id": "feed/company/gross_margin", "importance": "primary"},
                ],
                "secondary_variables": [
                    {"name": "input_cost_inflation", "feed_id": "feed/macro/input_cost_inflation", "importance": "secondary"},
                    {"name": "consumer_confidence", "feed_id": "feed/macro/consumer_confidence", "importance": "secondary"},
                    {"name": "fx_index", "feed_id": "feed/macro/fx_trade_weighted", "importance": "secondary"},
                ],
            },
            "reporting_template_patch": {
                "core_metrics": ["sales", "like_for_like_sales", "gross_margin", "operating_profit", "cash_conversion"],
                "margin_focus": ["gross_margin", "operating_margin"],
                "cash_flow_focus": ["free_cash_flow", "working_capital"],
                "balance_sheet_focus": ["net_debt", "pension_liabilities"],
                "management_signals": ["pricing_power", "promotion_intensity", "cost_savings_programs"],
            },
            "fingerprint_defaults_patch": {
                "expected_report_count_for_calibration": 20,
                "base_predictability": "high",
                "seasonality_strength": "medium",
                "macro_sensitivity": "low",
            },
        },
        {
            "sector_ref": "sector/utilities",
            "sector_name": "Utilities",
            "variable_map_patch": {
                "primary_variables": [
                    {"name": "regulated_asset_base", "feed_id": "feed/company/rab", "importance": "primary"},
                    {"name": "allowed_return", "feed_id": "feed/macro/allowed_return", "importance": "primary"},
                    {"name": "net_debt", "feed_id": "feed/company/net_debt", "importance": "secondary"},
                ],
                "secondary_variables": [
                    {"name": "real_yields", "feed_id": "feed/macro/real_yields", "importance": "secondary"},
                    {"name": "inflation", "feed_id": "feed/macro/inflation", "importance": "secondary"},
                    {"name": "regulatory_headlines", "feed_id": "feed/news/regulatory", "importance": "secondary"},
                ],
            },
            "reporting_template_patch": {
                "core_metrics": ["rab", "allowed_return", "capex", "operating_profit", "dividend_cover"],
                "margin_focus": ["operating_margin"],
                "cash_flow_focus": ["capex", "free_cash_flow_after_dividends"],
                "balance_sheet_focus": ["net_debt", "interest_coverage", "maturity_profile"],
                "management_signals": ["regulatory_engagement", "customer_outcomes", "performance_penalties"],
            },
            "fingerprint_defaults_patch": {
                "expected_report_count_for_calibration": 20,
                "base_predictability": "medium_high",
                "seasonality_strength": "low",
                "macro_sensitivity": "medium",
            },
        },
        {
            "sector_ref": "sector/housebuilders",
            "sector_name": "Housebuilders",
            "variable_map_patch": {
                "primary_variables": [
                    {"name": "reservation_rate", "feed_id": "feed/company/reservation_rate", "importance": "primary"},
                    {"name": "completion_volume", "feed_id": "feed/company/completions", "importance": "primary"},
                    {"name": "asp", "feed_id": "feed/company/average_selling_price", "importance": "secondary"},
                ],
                "secondary_variables": [
                    {"name": "mortgage_rates", "feed_id": "feed/macro/mortgage_rates", "importance": "secondary"},
                    {"name": "housing_affordability", "feed_id": "feed/macro/housing_affordability", "importance": "secondary"},
                    {"name": "consumer_confidence", "feed_id": "feed/macro/consumer_confidence", "importance": "secondary"},
                ],
            },
            "reporting_template_patch": {
                "core_metrics": ["reservations", "completions", "asp", "gross_margin", "net_cash_net_debt"],
                "margin_focus": ["gross_margin", "operating_margin"],
                "cash_flow_focus": ["land_spend", "working_capital"],
                "balance_sheet_focus": ["net_cash_net_debt", "land_bank"],
                "management_signals": ["build_cost_inflation", "incentive_intensity", "cancellation_rate"],
            },
            "fingerprint_defaults_patch": {
                "expected_report_count_for_calibration": 20,
                "base_predictability": "medium",
                "seasonality_strength": "medium",
                "macro_sensitivity": "high",
            },
        },
    ]


__all__ = ["get_sector_template_presets_v0"]