"""Period-aware, evidence-labelled Finance management reporting.

The builder is deliberately deterministic.  It never invents a reporting period,
budget or comparative: unavailable evidence is represented as a visible gap.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable


METRICS: tuple[tuple[str, str, tuple[str, ...], str], ...] = (
    ("revenue", "Revenue", ("revenue", "net_sales", "sales", "turnover", "average_monthly_revenue", "annualised_revenue"), "money"),
    ("direct_costs", "Direct costs", ("direct_costs", "total_direct_costs", "monthly_direct_costs", "cost_of_sales", "cogs", "costs"), "money"),
    ("gross_profit", "Gross profit", ("gross_profit", "monthly_gross_profit"), "money"),
    ("gross_margin_percent", "Gross margin", ("gross_margin_percent", "gross_margin_pct"), "percent"),
    ("overheads", "Overheads", ("overheads", "operating_expenses", "monthly_fixed_costs", "fixed_costs", "expenses"), "money"),
    ("operating_profit", "Operating profit", ("operating_profit", "ebitda_profit", "monthly_operating_surplus"), "money"),
    ("operating_margin_percent", "Operating margin", ("operating_margin_percent", "operating_margin_pct"), "percent"),
    ("net_profit", "Net profit", ("net_profit", "profit_after_tax"), "money"),
    ("ending_cash", "Closing cash", ("ending_cash", "cash", "cash_balance", "closing_cash"), "money"),
    ("debtors", "Trade debtors", ("debtors", "accounts_receivable", "trade_debtors", "receivables"), "money"),
    ("creditors", "Trade creditors", ("creditors", "accounts_payable", "trade_creditors", "payables"), "money"),
    ("debtor_days", "Debtor days", ("debtor_days", "days_sales_outstanding"), "number"),
    ("creditor_days", "Creditor days", ("creditor_days", "days_payable_outstanding"), "number"),
)

CORE_KEYS = ("revenue", "gross_profit", "operating_profit", "ending_cash")


def _number(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get("value", value.get("amount", value.get("actual")))
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _first(mapping: dict[str, Any], aliases: Iterable[str]) -> tuple[float | None, Any]:
    for name in aliases:
        if name in mapping:
            raw = mapping.get(name)
            value = _number(raw)
            if value is not None:
                return value, raw
    return None, None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _period_metrics(value: Any) -> dict[str, Any]:
    record = _mapping(value)
    nested = record.get("metrics")
    return _mapping(nested) if isinstance(nested, dict) else record


def _period_sources(financial: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    current = _mapping(financial.get("metrics"))
    budget: dict[str, Any] = {}
    previous: dict[str, Any] = {}

    accounts = _mapping(financial.get("management_accounts"))
    reporting = financial.get("reporting_periods") or financial.get("periods")
    if isinstance(reporting, dict):
        current = _period_metrics(reporting.get("current") or reporting.get("actual") or current)
        budget = _period_metrics(reporting.get("budget") or reporting.get("current_budget"))
        previous = _period_metrics(reporting.get("previous") or reporting.get("comparative"))
    elif isinstance(reporting, list) and reporting:
        ordered = [item for item in reporting if isinstance(item, dict)]
        actuals = [item for item in ordered if str(item.get("type") or "actual").lower() == "actual"]
        budgets = [item for item in ordered if str(item.get("type") or "").lower() == "budget"]
        if actuals:
            current = _period_metrics(actuals[-1])
            if len(actuals) > 1:
                previous = _period_metrics(actuals[-2])
        if budgets:
            budget = _period_metrics(budgets[-1])

    current = _period_metrics(accounts.get("current") or accounts.get("actual") or current)
    budget = _period_metrics(accounts.get("budget") or financial.get("budget_metrics") or budget)
    previous = _period_metrics(
        accounts.get("previous")
        or accounts.get("comparative")
        or financial.get("previous_period_metrics")
        or previous
    )
    return current, budget, previous


def _period_descriptor(financial: dict[str, Any]) -> dict[str, Any]:
    descriptor = _mapping(financial.get("reporting_period") or financial.get("current_period"))
    integration = _mapping(financial.get("integration_evidence"))
    xero = _mapping(integration.get("xero"))
    if not descriptor:
        descriptor = _mapping(xero.get("period"))
    metrics = _mapping(financial.get("metrics"))
    monthly_evidence = any(str(key).startswith("monthly_") or key == "average_monthly_revenue" for key in metrics)
    label = str(
        descriptor.get("label")
        or descriptor.get("name")
        or financial.get("period_label")
        or ("Average month" if monthly_evidence else financial.get("period_basis"))
        or "Period not specified"
    )
    return {
        "label": label,
        "from": descriptor.get("from") or descriptor.get("start") or descriptor.get("start_date"),
        "to": descriptor.get("to") or descriptor.get("end") or descriptor.get("end_date"),
        "basis": "monthly" if monthly_evidence and not descriptor else financial.get("period_basis") or descriptor.get("basis") or "not_specified",
        "explicit": bool(descriptor),
    }


def _verification(raw: Any, has_source_evidence: bool, *, derived: bool = False) -> str:
    if derived:
        return (
            "calculated_from_source_backed_values"
            if has_source_evidence
            else "calculated_from_unverified_values"
        )
    record = _mapping(raw)
    value = str(
        record.get("verification_state")
        or record.get("verification_status")
        or record.get("verification")
        or ""
    ).strip()
    if value:
        return value
    return "source_backed" if has_source_evidence else "unverified"


def _variance(actual: float | None, comparison: float | None) -> tuple[float | None, float | None]:
    if actual is None or comparison is None:
        return None, None
    amount = actual - comparison
    percent = None if comparison == 0 else amount / abs(comparison) * 100
    return round(amount, 4), None if percent is None else round(percent, 4)


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _freshness(financial: dict[str, Any], generated_at: str) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    meta = _mapping(financial.get("meta"))
    if meta.get("updated_at"):
        candidates.append({"source": "Financial Model", "observed_at": meta.get("updated_at")})
    for ref in list(financial.get("evidence_refs") or []):
        if not isinstance(ref, dict):
            continue
        candidates.append(
            {
                "source": ref.get("provider") or ref.get("source") or ref.get("artifact_id") or "Finance evidence",
                "observed_at": ref.get("observed_at") or ref.get("accepted_at") or ref.get("updated_at"),
                "verification_state": ref.get("verification_status") or ref.get("verification_state"),
            }
        )
    xero = _mapping(_mapping(financial.get("integration_evidence")).get("xero"))
    if xero.get("last_sync_at"):
        candidates.append(
            {
                "source": "Xero",
                "observed_at": xero.get("last_sync_at"),
                "verification_state": "provider_sourced",
            }
        )

    now = _parse_time(generated_at) or datetime.now(UTC)
    dated: list[dict[str, Any]] = []
    for item in candidates:
        observed = _parse_time(item.get("observed_at"))
        age = None if observed is None else max(0, (now - observed).days)
        state = "undated" if age is None else "fresh" if age <= 45 else "aging" if age <= 90 else "stale"
        dated.append({**item, "age_days": age, "freshness_state": state})
    dated.sort(key=lambda item: item.get("observed_at") or "", reverse=True)
    states = {item["freshness_state"] for item in dated}
    overall = "no_dated_evidence" if not dated else "stale" if "stale" in states else "aging" if "aging" in states else "fresh"
    return {
        "overall_state": overall,
        "latest_observed_at": dated[0].get("observed_at") if dated else None,
        "sources": dated[:30],
    }


def _derive_values(values: dict[str, tuple[float | None, Any]]) -> dict[str, bool]:
    derived: dict[str, bool] = {}
    revenue = values["revenue"][0]
    direct = values["direct_costs"][0]
    gross = values["gross_profit"][0]
    overheads = values["overheads"][0]
    operating = values["operating_profit"][0]

    if direct is None and revenue is not None and gross is not None:
        values["direct_costs"] = (revenue - gross, None)
        direct = revenue - gross
        derived["direct_costs"] = True
    if gross is None and revenue is not None and direct is not None:
        values["gross_profit"] = (revenue - direct, None)
        gross = revenue - direct
        derived["gross_profit"] = True
    if values["gross_margin_percent"][0] is None and revenue not in (None, 0) and gross is not None:
        values["gross_margin_percent"] = (gross / revenue * 100, None)
        derived["gross_margin_percent"] = True
    if overheads is None and gross is not None and operating is not None:
        values["overheads"] = (gross - operating, None)
        derived["overheads"] = True
    if operating is None and gross is not None and overheads is not None:
        values["operating_profit"] = (gross - overheads, None)
        operating = gross - overheads
        derived["operating_profit"] = True
    if values["operating_margin_percent"][0] is None and revenue not in (None, 0) and operating is not None:
        values["operating_margin_percent"] = (operating / revenue * 100, None)
        derived["operating_margin_percent"] = True
    return derived


def _accepted_artifact_values(financial: dict[str, Any]) -> tuple[dict[str, tuple[float, Any]], list[str]]:
    artifacts = _mapping(_mapping(financial.get("external_data")).get("artifacts"))
    projected = list(financial.get("accepted_artifact_facts") or [])
    if projected:
        artifacts = {
            str(item.get("artifact_id") or f"accepted-artifact-{index}"): item
            for index, item in enumerate(projected)
            if isinstance(item, dict)
        }
    aliases_by_key = {key: set(aliases) for key, _label, aliases, _format in METRICS}
    found: dict[str, list[tuple[float, dict[str, Any]]]] = {key: [] for key in aliases_by_key}
    for artifact in artifacts.values():
        record = _mapping(artifact)
        if str(record.get("verification_status") or "").lower() not in {
            "accepted_from_source_document", "accepted", "verified", "provider_sourced"
        }:
            continue
        for fact in list(record.get("facts") or []):
            if not isinstance(fact, dict):
                continue
            value = _number(fact.get("value"))
            if value is None:
                continue
            names = {
                str(fact.get("source_column") or "").strip().lower(),
                str(fact.get("field") or "").split(".")[-1].strip().lower(),
            }
            for key, aliases in aliases_by_key.items():
                if names & aliases:
                    found[key].append((value, {**fact, "artifact_id": record.get("artifact_id")}))

    accepted: dict[str, tuple[float, Any]] = {}
    conflicts: list[str] = []
    for key, candidates in found.items():
        unique = {round(item[0], 4) for item in candidates}
        if len(unique) == 1 and candidates:
            accepted[key] = candidates[0]
        elif len(unique) > 1:
            conflicts.append(
                f"Accepted source documents contain conflicting values for {key.replace('_', ' ')}: "
                + ", ".join(f"{value:,.2f}" for value in sorted(unique))
                + "."
            )
    return accepted, conflicts


def build_finance_management_report(
    financial: dict[str, Any],
    *,
    generated_at: str,
    retrieval_issues: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a management-account projection from canonical Finance truth."""

    current, budget, previous = _period_sources(financial)
    has_source_evidence = bool(financial.get("evidence_refs") or financial.get("integration_evidence"))
    values = {key: _first(current, aliases) for key, _label, aliases, _format in METRICS}
    artifact_values, artifact_conflicts = _accepted_artifact_values(financial)
    for key, artifact_value in artifact_values.items():
        # Accepted accounting evidence outranks free-text discovery metrics.
        # Previously a parsed founder sentence could override the workbook that
        # the founder had explicitly reviewed and accepted.
        values[key] = artifact_value
    if "revenue" in artifact_values and "gross_profit" in artifact_values:
        values["gross_margin_percent"] = (None, None)
    if "revenue" in artifact_values and "operating_profit" in artifact_values:
        values["operating_margin_percent"] = (None, None)
    budget_pairs = {key: _first(budget, aliases) for key, _label, aliases, _format in METRICS}
    previous_pairs = {key: _first(previous, aliases) for key, _label, aliases, _format in METRICS}
    derived = _derive_values(values)
    # Calculated margin/cost relationships are safe for comparisons as well.
    _derive_values(budget_pairs)
    _derive_values(previous_pairs)
    budget_values = {key: value[0] for key, value in budget_pairs.items()}
    previous_values = {key: value[0] for key, value in previous_pairs.items()}

    rows: list[dict[str, Any]] = []
    for key, label, _aliases, value_format in METRICS:
        actual, raw = values[key]
        budget_amount, budget_percent = _variance(actual, budget_values[key])
        previous_amount, previous_percent = _variance(actual, previous_values[key])
        rows.append(
            {
                "key": key,
                "label": label,
                "format": value_format,
                "actual": None if actual is None else round(actual, 4),
                "budget": budget_values[key],
                "budget_variance": budget_amount,
                "budget_variance_percent": budget_percent,
                "previous": previous_values[key],
                "previous_variance": previous_amount,
                "previous_variance_percent": previous_percent,
                "verification_state": _verification(raw, has_source_evidence, derived=derived.get(key, False)),
                "available": actual is not None,
            }
        )

    row_by_key = {item["key"]: item for item in rows}
    period = _period_descriptor(financial)
    freshness = _freshness(financial, generated_at)
    missing_core = [key for key in CORE_KEYS if row_by_key[key]["actual"] is None]
    missing = [str(item) for item in list(financial.get("missing_information") or [])]
    warnings = [str(item) for item in retrieval_issues]
    warnings.extend(artifact_conflicts)
    if not period["explicit"]:
        warnings.append("The reporting period is not explicitly evidenced.")
    if not budget:
        warnings.append("No canonical budget is available for an actual-versus-budget comparison.")
    if not previous:
        warnings.append("No canonical previous period is available for a period-on-period comparison.")
    if freshness["overall_state"] in {"stale", "no_dated_evidence"}:
        warnings.append("Finance evidence is stale or has no reliable observation date.")
    for item in missing:
        if item not in warnings:
            warnings.append(item)

    return {
        "schema_version": "aion.finance_pilot.management_accounts.v2",
        "period": period,
        "currency": str(financial.get("currency") or "EUR"),
        "kpis": rows,
        "sections": {
            "profit_and_loss": [row_by_key[key] for key in (
                "revenue", "direct_costs", "gross_profit", "gross_margin_percent",
                "overheads", "operating_profit", "operating_margin_percent", "net_profit",
            )],
            "cash_and_working_capital": [row_by_key[key] for key in (
                "ending_cash", "debtors", "creditors", "debtor_days", "creditor_days",
            )],
        },
        "headline": {key: row_by_key[key]["actual"] for key in CORE_KEYS},
        "comparison_coverage": {
            "budget_available": bool(budget),
            "previous_period_available": bool(previous),
            "budget_metric_count": sum(value is not None for value in budget_values.values()),
            "previous_period_metric_count": sum(value is not None for value in previous_values.values()),
        },
        "evidence_freshness": freshness,
        "missing_core_metrics": missing_core,
        "warnings": list(dict.fromkeys(warnings))[:30],
        "verification_summary": {
            "source_backed_count": sum(
                item["verification_state"] not in {
                    "unverified", "calculated_from_unverified_input", "calculated_from_unverified_values"
                }
                for item in rows if item["available"]
            ),
            "available_metric_count": sum(item["available"] for item in rows),
        },
    }
