"""Source-backed completion of Finance onboarding into usable business truth.

The discovery UI is allowed to collect approximate founder answers, but an
accepted accounting artifact must win whenever the two disagree.  This module
turns those accepted facts into an explicit statement package and a reviewable
first operating model without silently filling evidence gaps.
"""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any


FACT_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("net_sales", "revenue", "sales", "turnover"),
    "direct_costs": ("total_direct_costs", "direct_costs", "costs", "cost_of_sales", "cogs"),
    "gross_profit": ("gross_profit",),
    "overheads": ("operating_expenses", "overheads", "fixed_costs"),
    "operating_profit": ("operating_profit", "ebitda_profit"),
    "profit_before_tax": ("profit_before_tax",),
    "tax": ("tax", "corporation_tax", "income_tax"),
    "net_profit": ("net_profit", "profit_after_tax"),
    "cash_collections": ("cash_collections", "cash_receipts"),
    "cash_payments": ("cash_payments", "payments"),
    "ending_cash": ("ending_cash", "closing_cash", "cash_balance", "cash"),
    "accounts_receivable": ("accounts_receivable", "trade_debtors", "debtors", "receivables"),
    "accounts_payable": ("accounts_payable", "trade_creditors", "creditors", "payables"),
}

SERVICE_REVENUE_FIELDS: tuple[tuple[str, str], ...] = (
    ("handyman_sales", "Handyman services"),
    ("painting_sales", "Painting services"),
    ("roofing_sales", "Roofing services"),
    ("plumbing_electrical_sales", "Plumbing & electrical services"),
    ("emergency_sales", "Emergency services"),
)

ACCEPTED_STATES = {
    "accepted_from_source_document",
    "accepted",
    "verified",
    "provider_sourced",
}


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value", value.get("amount", value.get("actual")))
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == "":
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _accepted_rows(financial: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = ((financial.get("external_data") or {}).get("artifacts") or {})
    rows: list[dict[str, Any]] = []
    if not isinstance(artifacts, dict):
        return rows
    for artifact in artifacts.values():
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("verification_status") or "").lower() not in ACCEPTED_STATES:
            continue
        for fact in artifact.get("facts") or []:
            if not isinstance(fact, dict) or _number(fact.get("value")) is None:
                continue
            rows.append(
                {
                    **fact,
                    "artifact_id": artifact.get("artifact_id"),
                    "filename": artifact.get("filename"),
                    "verification_status": artifact.get("verification_status"),
                }
            )
    return rows


def _fact_name(row: dict[str, Any]) -> str:
    return str(row.get("source_column") or str(row.get("field") or "").split(".")[-1]).strip().lower()


def _select(rows: list[dict[str, Any]], aliases: tuple[str, ...]) -> tuple[float | None, list[dict[str, Any]], list[str]]:
    for alias in aliases:
        candidates = [row for row in rows if _fact_name(row) == alias]
        unique = sorted({_number(row.get("value")) for row in candidates if _number(row.get("value")) is not None})
        if len(unique) == 1:
            return unique[0], candidates, []
        if len(unique) > 1:
            return None, candidates, [
                f"Accepted evidence conflicts for {alias.replace('_', ' ')}: "
                + ", ".join(f"{value:,.2f}" for value in unique)
            ]
    return None, [], []


def _source_record(value: float | None, rows: list[dict[str, Any]], *, calculation: str | None = None) -> dict[str, Any] | None:
    if value is None:
        return None
    record: dict[str, Any] = {
        "value": round(value, 4),
        "verification": "calculated_from_source_backed_values" if calculation else "source_backed",
        "source": "accepted_accounting_evidence",
        "evidence_refs": sorted({str(row.get("artifact_id")) for row in rows if row.get("artifact_id")}),
    }
    if calculation:
        record["calculation"] = calculation
    return record


def _period(rows: list[dict[str, Any]]) -> dict[str, Any]:
    years: set[int] = set()
    for row in rows:
        for match in re.findall(r"(?<!\d)(20\d{2})(?!\d)", str(row.get("filename") or "")):
            years.add(int(match))
    if len(years) == 1:
        year = next(iter(years))
        return {
            "label": f"FY{year}",
            "from": f"{year}-01-01",
            "to": f"{year}-12-31",
            "basis": "annual",
            "verification": "period_inferred_from_accepted_source_filename",
        }
    return {
        "label": "Period requires confirmation",
        "from": None,
        "to": None,
        "basis": "annual",
        "verification": "unverified",
    }


def _line(key: str, label: str, record: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "value": None if record is None else record.get("value"),
        "verification": "missing" if record is None else record.get("verification"),
        "evidence_refs": [] if record is None else record.get("evidence_refs", []),
        "available": record is not None,
    }


def build_finance_completion(financial: dict[str, Any], operating: dict[str, Any] | None = None) -> dict[str, Any]:
    rows = _accepted_rows(financial)
    selected: dict[str, tuple[float | None, list[dict[str, Any]]]] = {}
    conflicts: list[str] = []
    for key, aliases in FACT_ALIASES.items():
        value, evidence, issues = _select(rows, aliases)
        selected[key] = (value, evidence)
        conflicts.extend(issues)

    def rec(key: str) -> dict[str, Any] | None:
        value, evidence = selected[key]
        return _source_record(value, evidence)

    revenue = selected["revenue"][0]
    direct = selected["direct_costs"][0]
    gross = selected["gross_profit"][0]
    overheads = selected["overheads"][0]
    operating_profit = selected["operating_profit"][0]
    pbt = selected["profit_before_tax"][0]
    tax = selected["tax"][0]
    net = selected["net_profit"][0]
    collections = selected["cash_collections"][0]
    payments = selected["cash_payments"][0]
    ending_cash = selected["ending_cash"][0]

    if gross is None and revenue is not None and direct is not None:
        gross = revenue - direct
    if operating_profit is None and gross is not None and overheads is not None:
        operating_profit = gross - overheads
    if pbt is None and net is not None and tax is not None:
        pbt = net + tax
    if net is None and pbt is not None and tax is not None:
        net = pbt - tax

    all_source_rows = [row for _value, evidence in selected.values() for row in evidence]
    gross_margin = None if not revenue or gross is None else gross / revenue * 100
    operating_margin = None if not revenue or operating_profit is None else operating_profit / revenue * 100
    opening_cash = None
    net_cash_change = None
    if collections is not None and payments is not None:
        net_cash_change = collections - payments
        if ending_cash is not None:
            opening_cash = ending_cash - net_cash_change

    metrics = {
        "revenue": _source_record(revenue, selected["revenue"][1]),
        "annualised_revenue": _source_record(revenue, selected["revenue"][1]),
        "average_monthly_revenue": _source_record(None if revenue is None else revenue / 12, selected["revenue"][1], calculation="annual revenue / 12"),
        "direct_costs": _source_record(direct, selected["direct_costs"][1]),
        "gross_profit": _source_record(gross, [*selected["gross_profit"][1], *all_source_rows], calculation="revenue - direct costs" if not selected["gross_profit"][1] else None),
        "gross_margin_percent": _source_record(gross_margin, all_source_rows, calculation="gross profit / revenue * 100"),
        "overheads": _source_record(overheads, selected["overheads"][1]),
        "operating_profit": _source_record(operating_profit, [*selected["operating_profit"][1], *all_source_rows], calculation="gross profit - overheads" if not selected["operating_profit"][1] else None),
        "operating_margin_percent": _source_record(operating_margin, all_source_rows, calculation="operating profit / revenue * 100"),
        "profit_before_tax": _source_record(pbt, selected["profit_before_tax"][1]),
        "tax": _source_record(tax, selected["tax"][1]),
        "net_profit": _source_record(net, selected["net_profit"][1]),
        "cash_collections": _source_record(collections, selected["cash_collections"][1]),
        "cash_payments": _source_record(payments, selected["cash_payments"][1]),
        "net_cash_change": _source_record(net_cash_change, all_source_rows, calculation="cash collections - cash payments"),
        "opening_cash": _source_record(opening_cash, all_source_rows, calculation="ending cash - net cash change"),
        "ending_cash": _source_record(ending_cash, selected["ending_cash"][1]),
        "accounts_receivable": rec("accounts_receivable"),
        "accounts_payable": rec("accounts_payable"),
    }
    metrics = {key: value for key, value in metrics.items() if value is not None}

    period = _period(rows)
    profit_and_loss = {
        "statement_type": "profit_and_loss",
        "period": period,
        "status": "source_backed" if all(value is not None for value in (revenue, direct, gross, overheads, operating_profit, net)) else "partial",
        "lines": [
            _line("revenue", "Revenue", metrics.get("revenue")),
            _line("direct_costs", "Direct costs", metrics.get("direct_costs")),
            _line("gross_profit", "Gross profit", metrics.get("gross_profit")),
            _line("overheads", "Operating expenses", metrics.get("overheads")),
            _line("operating_profit", "Operating profit", metrics.get("operating_profit")),
            _line("profit_before_tax", "Profit before tax", metrics.get("profit_before_tax")),
            _line("tax", "Tax", metrics.get("tax")),
            _line("net_profit", "Net profit", metrics.get("net_profit")),
        ],
    }

    inventory_value = _number(((operating or {}).get("inventory_metrics") or {}).get("total_stock_value"))
    debt_value = sum(_number(item.get("balance")) or 0 for item in (operating or {}).get("debt_commitments") or [] if isinstance(item, dict))
    receivables = selected["accounts_receivable"][0]
    payables = selected["accounts_payable"][0]
    balance_sheet = {
        "statement_type": "balance_sheet",
        "as_at": period.get("to"),
        "status": "partial",
        "assets": {
            "cash": ending_cash,
            "accounts_receivable": receivables,
            "inventory": inventory_value,
            "other_assets": None,
        },
        "liabilities": {
            "accounts_payable": payables,
            "debt_commitments": debt_value if debt_value else None,
            "tax_liabilities": None,
            "other_liabilities": None,
        },
        "equity": None,
        "balance_check": {
            "available": False,
            "difference": None,
            "reason": "A complete assets, liabilities and equity dataset is not yet available.",
        },
        "missing_information": [
            label
            for value, label in (
                (receivables, "trade receivables"),
                (payables, "trade payables"),
                (None, "fixed and other assets"),
                (None, "tax and other liabilities"),
                (None, "owner equity and retained earnings"),
            )
            if value is None
        ],
    }

    cash_flow = {
        "statement_type": "cash_flow",
        "period": period,
        "method": "direct_summary",
        "status": "source_backed_summary" if all(value is not None for value in (collections, payments, ending_cash)) else "partial",
        "opening_cash": opening_cash,
        "cash_collections": collections,
        "cash_payments": payments,
        "net_cash_change": net_cash_change,
        "ending_cash": ending_cash,
        "protected_cash_reserve": _cash_reserve(financial),
        "missing_information": [] if all(value is not None for value in (collections, payments, ending_cash)) else ["cash receipts, payments or closing cash"],
    }

    operating_model = operating or {}
    business_model = {
        "status": "needs_user_review" if not operating else str(operating.get("model_status") or "draft"),
        "offering_count": len(operating_model.get("offerings") or []),
        "offerings": operating_model.get("offerings") or [],
        "pricing_rules": operating_model.get("pricing_rules") or [],
        "payment_terms": operating_model.get("payment_terms") or [],
        "unit_economics": operating_model.get("unit_economics") or [],
        "overall_financial_metrics": {
            key: metrics.get(key)
            for key in ("revenue", "gross_profit", "gross_margin_percent", "operating_profit", "operating_margin_percent", "net_profit")
        },
    }

    quality = {
        "status": "review_required" if conflicts or balance_sheet["status"] != "complete" else "complete",
        "accepted_artifact_count": len(((financial.get("external_data") or {}).get("artifacts") or {})),
        "source_backed_metric_count": sum(1 for value in metrics.values() if value.get("verification") == "source_backed"),
        "calculated_metric_count": sum(1 for value in metrics.values() if str(value.get("verification")).startswith("calculated")),
        "conflicts": conflicts,
        "warnings": [
            "The balance sheet remains partial until assets, liabilities and equity are complete.",
            "Products, rates, volumes and unit costs require owner review in Products & Services.",
        ],
    }

    return {
        "schema_version": "aion.finance_completion.v1",
        "generated_at": _now(),
        "currency": "EUR" if str(financial.get("currency") or "").lower() in {"eur", "euro", "euros", "€"} else str(financial.get("currency") or "EUR").upper(),
        "period": period,
        "authoritative_metrics": metrics,
        "financial_statements": {
            "profit_and_loss": profit_and_loss,
            "balance_sheet": balance_sheet,
            "cash_flow": cash_flow,
        },
        "business_model": business_model,
        "quality": quality,
    }


def _cash_reserve(financial: dict[str, Any]) -> float | None:
    cashflow = financial.get("cashflow_model") or {}
    discovery = financial.get("discovery_state") or {}
    candidates = (
        cashflow.get("minimum_cash_reserve"),
        cashflow.get("minimum_cash_buffer"),
        cashflow.get("minimum_cash_buffer_policy"),
        (discovery.get("answers") or {}).get("cash_buffer_policy"),
    )
    for candidate in candidates:
        if isinstance(candidate, (int, float)):
            return float(candidate)
        values = re.findall(r"\d+(?:[,.]\d+)?", str(candidate or "").replace(",", ""))
        if values:
            return float(values[0])
    return None


def seed_operating_model(financial: dict[str, Any], completion: dict[str, Any]) -> dict[str, Any]:
    rows = _accepted_rows(financial)
    answers = (financial.get("discovery_state") or {}).get("answers") or {}
    offerings: list[dict[str, Any]] = []
    for source_field, label in SERVICE_REVENUE_FIELDS:
        value, evidence, _issues = _select(rows, (source_field,))
        if value is None:
            continue
        offerings.append(
            {
                "name": label,
                "offering_type": "service",
                "pricing_basis": "quote",
                "price": None,
                "unit": "job",
                "expected_monthly_volume": None,
                "historical_annual_revenue": value,
                "verification": "source_backed_historical_revenue",
                "evidence_refs": sorted({str(row.get("artifact_id")) for row in evidence if row.get("artifact_id")}),
                "requires_owner_review": True,
            }
        )

    revenue_model = str(answers.get("revenue_model") or financial.get("revenue_model", {}).get("charging_and_prices") or "")
    day_rate_match = re.search(r"(?:charge|rate|typically|about)?[^\d]{0,20}(\d+(?:\.\d+)?)\s*(?:euros?|eur|€)?\s*(?:per\s+day|day)", revenue_model, re.I)
    if day_rate_match:
        offerings.insert(
            0,
            {
                "name": "Standard labour day rate",
                "offering_type": "service",
                "pricing_basis": "day_rate",
                "price": float(day_rate_match.group(1)),
                "unit": "day",
                "expected_monthly_volume": None,
                "verification": "founder_supplied_unverified",
                "requires_owner_review": True,
            },
        )

    markup_match = re.search(r"(\d+(?:\.\d+)?)\s*%[^.]{0,30}(?:material|cost)", revenue_model, re.I)
    pricing_rules = []
    if markup_match:
        pricing_rules.append(
            {
                "name": "Materials markup",
                "rule_type": "cost_plus",
                "markup_percent": float(markup_match.group(1)),
                "verification": "founder_supplied_unverified",
                "requires_owner_review": True,
            }
        )

    payment_text = str(answers.get("payment_terms") or "")
    deposit_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*deposit", payment_text, re.I)
    payment_terms = []
    if payment_text:
        payment_terms.append(
            {
                "name": "Default customer terms",
                "deposit_percent": float(deposit_match.group(1)) if deposit_match else None,
                "balance_due_days": 0 if "completion" in payment_text.lower() else None,
                "notes": payment_text,
                "verification": "founder_supplied_unverified",
            }
        )

    metrics = completion.get("authoritative_metrics") or {}
    overhead = _number(metrics.get("overheads"))
    overheads = [] if overhead is None else [
        {
            "name": "Historical operating expenses",
            "monthly_amount": round(overhead / 12, 2),
            "category": "combined_historical_overheads",
            "source": "accepted_accounting_evidence",
            "requires_breakdown_review": True,
        }
    ]
    reserve = _cash_reserve(financial)
    targets = [] if reserve is None else [
        {
            "name": "Minimum protected cash reserve",
            "target_value": reserve,
            "unit": "EUR",
            "deadline": None,
            "source": "finance_discovery",
        }
    ]

    return {
        "model_status": "needs_user_review",
        "setup_mode": "simple",
        "currency": completion.get("currency") or "EUR",
        "offerings": offerings,
        "pricing_rules": pricing_rules,
        "payment_terms": payment_terms,
        "customer_terms": [],
        "labour_resources": [],
        "overheads": overheads,
        "debt_commitments": [],
        "financial_targets": targets,
        "production_lines": [],
        "bills_of_materials": [],
        "inventory_items": [],
        "suppliers": [],
        "procurement_queue": [],
        "unit_economics": [],
        "inventory_metrics": {},
        "capacity_model": {},
        "provenance": {
            "seeded_by": "aion.finance_completion.v1",
            "seeded_at": _now(),
            "owner_confirmation_required": True,
        },
        "source_refs": [
            {"artifact_id": artifact_id, "source": "accepted_accounting_evidence"}
            for artifact_id in sorted({str(row.get("artifact_id")) for row in rows if row.get("artifact_id")})
        ],
    }
