"""Living Finance Director model, proactive signals and Boardroom proposals."""

from __future__ import annotations

from datetime import UTC, date, datetime
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_ledger_service import FinanceLedgerService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import WorkflowFileCabinetRepository


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _number(value: Any) -> float:
    if isinstance(value, dict):
        value = value.get("value", value.get("amount", value.get("actual")))
    try:
        return round(float(value or 0), 4)
    except (TypeError, ValueError):
        return 0.0


def _first(mapping: dict[str, Any], *keys: str) -> float:
    for key in keys:
        if key in mapping and mapping.get(key) not in (None, ""):
            return _number(mapping.get(key))
    return 0.0


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


class FinanceDirectorService:
    """Build a read-only, evidence-labelled operating view of Finance."""

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 ledger_service: FinanceLedgerService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.ledger_service = ledger_service or FinanceLedgerService(self.repository)

    def refresh(self, workspace_id: str, *, minimum_cash_reserve: float | None = None,
                created_by: str = "finance_pilot", created_at: str | None = None) -> dict[str, Any]:
        financial = self.repository.load_dict(workspace_id, "business_financial_model")
        operating = self.repository.load_optional_dict(workspace_id, "business_operating_model") or {}
        ledger = self.ledger_service.latest(workspace_id, include_records=True)
        metrics = financial.get("metrics") or {}
        ledger_summary = (ledger or {}).get("summaries") or {}
        records = (ledger or {}).get("records") or {}
        invoices = records.get("invoices") or []
        accounts = records.get("accounts") or []

        revenue = _first(metrics, "revenue", "net_sales", "sales", "turnover", "annualised_revenue")
        direct_costs = _first(metrics, "direct_costs", "total_direct_costs", "cost_of_sales", "cogs", "costs")
        gross_profit = _first(metrics, "gross_profit") or revenue - direct_costs
        overheads = _first(metrics, "overheads", "operating_expenses", "fixed_costs")
        operating_profit = _first(metrics, "operating_profit", "ebitda_profit", "monthly_operating_surplus") or gross_profit - overheads
        cash = _first(metrics, "ending_cash", "cash", "cash_balance", "closing_cash")
        receivables = _number(ledger_summary.get("accounts_receivable")) or _first(metrics, "debtors", "accounts_receivable")
        payables = _number(ledger_summary.get("accounts_payable")) or _first(metrics, "creditors", "accounts_payable")
        period_basis = str(financial.get("period_basis") or "annual").lower()
        monthly_revenue = revenue if "month" in period_basis else revenue / 12 if revenue else 0
        monthly_operating_profit = operating_profit if "month" in period_basis else operating_profit / 12 if operating_profit else 0
        monthly_cash_burn = max(0, -monthly_operating_profit)
        reserve = _number(minimum_cash_reserve if minimum_cash_reserve is not None else
                          ((financial.get("cashflow_model") or {}).get("minimum_cash_reserve") or
                           (financial.get("discovery_state") or {}).get("minimum_cash_reserve") or 0))
        runway_months = None if monthly_cash_burn <= 0 else round(max(0, cash - reserve) / monthly_cash_burn, 2)

        offerings = operating.get("offerings") or []
        unit_economics = operating.get("unit_economics") or []
        inventory = operating.get("inventory_metrics") or {}
        procurement = operating.get("procurement_queue") or []
        overdue_sales = [item for item in invoices if item.get("invoice_type") == "sales_invoice" and item.get("is_overdue")]
        overdue_bills = [item for item in invoices if item.get("invoice_type") == "supplier_bill" and item.get("is_overdue")]
        unverified = not bool(financial.get("evidence_refs") or financial.get("integration_evidence"))
        statement_package = financial.get("financial_statements") or {}
        source_balance_sheet = statement_package.get("balance_sheet") or {}
        source_cash_flow = statement_package.get("cash_flow") or {}
        balance_sheet = {
            "cash": cash, "accounts_receivable": receivables,
            "accounts_payable": payables, "inventory": _number(inventory.get("total_stock_value")),
            "net_working_capital": round(cash + receivables + _number(inventory.get("total_stock_value")) - payables, 2),
            "coverage": "partial_operating_balance_sheet",
        }
        cash_flow = {
            "opening_or_latest_cash": cash,
            "monthly_operating_cash_proxy": round(monthly_operating_profit, 2),
            "monthly_cash_burn_proxy": round(monthly_cash_burn, 2),
            "protected_reserve": reserve,
            "estimated_runway_months": runway_months,
            "accounts_receivable": receivables,
            "accounts_payable": payables,
            "warning": "Operating-profit proxy excludes financing, tax, capital and timing movements." if monthly_operating_profit else "Insufficient evidence for a monthly cash movement proxy.",
        }
        if source_cash_flow:
            cash_flow.update({
                "statement_status": source_cash_flow.get("status"),
                "statement_method": source_cash_flow.get("method"),
                "opening_cash": source_cash_flow.get("opening_cash"),
                "cash_collections": source_cash_flow.get("cash_collections"),
                "cash_payments": source_cash_flow.get("cash_payments"),
                "net_cash_change": source_cash_flow.get("net_cash_change"),
                "ending_cash": source_cash_flow.get("ending_cash"),
                "warning": None if source_cash_flow.get("status") == "source_backed_summary" else cash_flow["warning"],
            })
        if source_balance_sheet:
            balance_sheet.update({
                "statement_status": source_balance_sheet.get("status"),
                "assets": source_balance_sheet.get("assets") or {},
                "liabilities": source_balance_sheet.get("liabilities") or {},
                "equity": source_balance_sheet.get("equity"),
                "balance_check": source_balance_sheet.get("balance_check") or {},
                "missing_information": source_balance_sheet.get("missing_information") or [],
            })
        profitability = {
            "revenue": revenue, "direct_costs": direct_costs, "gross_profit": gross_profit,
            "gross_margin_percent": round(gross_profit / revenue * 100, 2) if revenue else None,
            "overheads": overheads, "operating_profit": operating_profit,
            "operating_margin_percent": round(operating_profit / revenue * 100, 2) if revenue else None,
        }
        working_capital = {
            "overdue_receivables": round(sum(_number(item.get("amount_due")) for item in overdue_sales), 2),
            "overdue_payables": round(sum(_number(item.get("amount_due")) for item in overdue_bills), 2),
            "overdue_sales_invoice_count": len(overdue_sales), "overdue_supplier_bill_count": len(overdue_bills),
            "procurement_cash_required": _number(inventory.get("suggested_procurement_cash_required")),
            "purchases_awaiting_review": len([item for item in procurement if str(item.get("status") or "draft") in {"draft", "review_required"}]),
        }
        commercial = {
            "offering_count": len(offerings), "unit_economics_count": len(unit_economics),
            "unit_economics": unit_economics[:100],
            "pipeline": (financial.get("commercial_context") or {}).get("pipeline") or {},
            "work_in_progress": (financial.get("commercial_context") or {}).get("work_in_progress") or {},
            "budgets": financial.get("budget_metrics") or (financial.get("management_accounts") or {}).get("budget") or {},
            "projects": records.get("projects") or [],
        }
        signals = self._signals(profitability, cash_flow, working_capital, commercial, unverified)
        proposals = self._proposals(workspace_id, signals, overdue_sales, unit_economics)
        occurred_at = created_at or _now(); director_id = f"finance-director-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
        record = {
            "schema_version": "aion.finance_director.model.v1", "director_model_id": director_id,
            "workspace_id": workspace_id, "created_at": occurred_at, "created_by": created_by,
            "currency": financial.get("currency") or operating.get("currency") or "EUR",
            "source_financial_model_revision": financial.get("revision"),
            "source_financial_model_hash": canonical_contract_hash(financial),
            "ledger_ref": None if not ledger else {"ledger_id": ledger["ledger_id"], "ledger_hash": ledger["ledger_hash"]},
            "profit_and_loss": profitability, "balance_sheet": balance_sheet, "cash_flow": cash_flow,
            "financial_statements": statement_package,
            "statement_quality": financial.get("statement_quality") or {},
            "working_capital": working_capital, "commercial_and_operating_context": commercial,
            "proactive_signals": signals, "boardroom_proposals": proposals,
            "verification_state": "unverified_founder_supplied" if unverified else "mixed_provider_and_accepted_evidence",
            "limitations": ["This is an operating Finance model, not a statutory set of accounts.",
                            "No accounting, communication or payment action was executed."],
            "external_write_performed": False,
        }
        record["director_model_hash"] = canonical_contract_hash(record)
        path = self._dir(workspace_id) / f"{director_id}.json"; path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self._index(workspace_id, record, path); self._project(workspace_id, financial, record, path)
        return record

    def latest(self, workspace_id: str) -> dict[str, Any] | None:
        paths = sorted(self._dir(workspace_id).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not paths: return None
        record = json.loads(paths[0].read_text(encoding="utf-8")); self._verify(record); return record

    def _dir(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "finance/director_models"; path.mkdir(parents=True, exist_ok=True); return path

    @staticmethod
    def _signals(profit: dict[str, Any], cash: dict[str, Any], working: dict[str, Any], commercial: dict[str, Any], unverified: bool) -> list[dict[str, Any]]:
        signals = []
        def add(code: str, severity: str, title: str, evidence: dict[str, Any], recommendation: str, departments: list[str]) -> None:
            signals.append({"signal_id": f"finance-signal-{code}", "code": code, "severity": severity, "title": title,
                            "evidence": evidence, "recommendation": recommendation, "target_departments": departments,
                            "status": "requires_review"})
        runway = cash.get("estimated_runway_months")
        if runway is not None and runway <= 1:
            add("cash_runway_critical", "critical", "Cash runway is one month or less", {"runway_months": runway, "cash": cash.get("opening_or_latest_cash"), "reserve": cash.get("protected_reserve")}, "Protect cash immediately and review debt collection, WIP completion and demand-generation options.", ["finance", "sales", "marketing", "operations"])
        elif runway is not None and runway <= 3:
            add("cash_runway_warning", "high", "Cash runway is below three months", {"runway_months": runway}, "Prepare a cash improvement plan before the protected reserve is reached.", ["finance", "sales", "operations"])
        if cash.get("opening_or_latest_cash", 0) < cash.get("protected_reserve", 0):
            add("cash_reserve_breach", "critical", "Cash is below the protected reserve", {"cash": cash.get("opening_or_latest_cash"), "reserve": cash.get("protected_reserve")}, "Escalate to the founder and Boardroom; stage only cash-preserving actions.", ["finance", "central_pilot"])
        margin = profit.get("gross_margin_percent")
        if margin is not None and margin < 25:
            add("gross_margin_low", "high", "Gross margin is below 25%", {"gross_margin_percent": margin}, "Review pricing, direct costs and customer acquisition cost before increasing volume.", ["finance", "sales", "marketing", "operations"])
        if working.get("overdue_receivables", 0) > 0:
            add("overdue_receivables", "high", "Customer invoices are overdue", {"amount": working["overdue_receivables"], "count": working["overdue_sales_invoice_count"]}, "Prepare an invoice chase list for exact approval.", ["finance", "sales"])
        pipeline = commercial.get("pipeline") or {}
        open_quotes = pipeline.get("open_quotes") or pipeline.get("outstanding_quotes") or []
        open_quote_count = len(open_quotes) if isinstance(open_quotes, list) else int(_number(pipeline.get("open_quote_count") or pipeline.get("outstanding_quote_count")))
        open_quote_value = _number(pipeline.get("open_quote_value") or pipeline.get("outstanding_quote_value"))
        if open_quote_count > 0:
            add("quote_leakage", "high", "Open quotes need commercial follow-up", {"count": open_quote_count, "value": open_quote_value}, "Ask Sales to review ageing, probability and the fastest appropriate follow-up for every open quote.", ["sales", "finance"])
        if pipeline and _number(pipeline.get("forecast_value") or pipeline.get("weighted_value")) <= 0:
            add("pipeline_weak", "high", "The recorded sales pipeline has no forecast value", {"pipeline": pipeline}, "Ask Sales to validate open opportunities and Marketing to prepare demand-generation options.", ["sales", "marketing"])
        if commercial.get("unit_economics_count", 0) == 0:
            add("unit_economics_missing", "medium", "Unit economics are not yet modelled", {}, "Complete price, volume, labour and direct-cost inputs before changing prices.", ["finance", "products_services"])
        wip = commercial.get("work_in_progress") or {}
        wip_value = _number(wip.get("value") or wip.get("amount") or wip.get("invoiceable_value"))
        if wip_value > 0:
            add("wip_cash_tied_up", "high", "Work in progress is tying up cash", {"wip_value": wip_value}, "Prioritise work closest to completion and confirm the invoice trigger and expected collection date.", ["operations", "finance"])
        if profit.get("operating_profit", 0) < 0:
            add("operating_loss", "high", "The operating model is loss-making", {"operating_profit": profit.get("operating_profit")}, "Review overheads, direct costs, pricing and loss-making work before approving additional discretionary spend.", ["finance", "operations"])
        if unverified:
            add("evidence_unverified", "medium", "The financial baseline is not provider or source backed", {}, "Connect accounting evidence or accept reviewed source documents before acting on the model.", ["finance"])
        return signals

    @staticmethod
    def _proposals(workspace_id: str, signals: list[dict[str, Any]], overdue_sales: list[dict[str, Any]], unit_economics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        proposals = []
        codes = {item["code"] for item in signals}
        def add(kind: str, title: str, department: str, payload: dict[str, Any], rationale: str) -> None:
            proposal = {"proposal_id": f"finance-proposal-{_safe(kind)}-{len(proposals) + 1}", "workspace_id": workspace_id,
                        "source_department": "finance", "target_department": department, "kind": kind, "title": title,
                        "payload": payload, "rationale": rationale, "status": "boardroom_review_required",
                        "approval_required": True, "external_action_performed": False}
            proposal["payload_hash"] = canonical_contract_hash(payload); proposals.append(proposal)
        if "overdue_receivables" in codes:
            add("invoice_chase", "Prepare overdue invoice follow-up", "finance", {"invoices": [{"invoice_id": item.get("invoice_id"), "invoice_number": item.get("invoice_number"), "contact": item.get("contact"), "amount_due": item.get("amount_due"), "due_date": item.get("due_date")} for item in overdue_sales]}, "Release cash from overdue customer balances; communication remains unsent until exact approval.")
        if "gross_margin_low" in codes and unit_economics:
            add("pricing_review", "Test price changes against unit economics", "finance", {"offerings": unit_economics[:25], "requested_scenarios_percent": [5, 10, 15]}, "Determine whether a price change can restore margin without confusing modelled results with actuals.")
        if "operating_loss" in codes:
            add("cost_review", "Identify controllable cost reductions", "finance", {"requested_outputs": ["avoidable_overheads", "supplier_savings", "loss_making_work", "cash_effect"]}, "The current operating model is loss-making; Finance should prepare options without changing contracts or payments.")
        if "quote_leakage" in codes:
            add("quote_follow_up", "Review and follow up outstanding quotes", "sales", {"requested_outputs": ["quote_ageing", "probability", "recommended_follow_up", "cash_timing"]}, "Open quotes may convert to cash faster than creating new demand; messages remain drafts until approved.")
        if {"cash_runway_critical", "cash_runway_warning", "pipeline_weak", "wip_cash_tied_up"} & codes:
            add("sales_pipeline_review", "Validate quotes and near-term pipeline", "sales", {"requested_outputs": ["open_quotes", "weighted_pipeline", "fastest_cash_opportunities"]}, "Finance needs evidence of near-term cash inflows.")
            add("demand_generation_options", "Prepare bounded demand-generation options", "marketing", {"constraint": "no_spend_or_publishing_without_approval", "requested_outputs": ["existing_customer_offer", "early_booking_campaign", "low_cost_lead_options"]}, "Finance forecasts a cash or pipeline risk; Marketing should propose options, not publish them.")
            add("wip_cash_release", "Prioritise WIP that releases cash", "operations", {"requested_outputs": ["work_in_progress", "completion_dates", "invoice_trigger", "cash_released"]}, "Completing near-finished work may release cash faster than acquiring new work.")
        return proposals

    def _index(self, workspace_id: str, record: dict[str, Any], path: Path) -> None:
        tree = WorkflowFileCabinetRepository.load(workspace_id); folders = tree.get("folders") or (tree.get("root") or {}).get("children") or []
        finance = next((item for item in folders if item.get("id") == "folder_finance"), None)
        if finance is None:
            finance = {"id": "folder_finance", "name": "Finance", "type": "department", "children": []}; folders.append(finance)
        children = finance.setdefault("children", []); folder = next((item for item in children if item.get("id") == "folder_finance_director_models"), None)
        if folder is None:
            folder = {"id": "folder_finance_director_models", "name": "Finance Director", "type": "folder", "children": []}; children.append(folder)
        folder.setdefault("children", []).append({"id": f"finance_director_pointer_{record['director_model_id']}", "name": record["director_model_id"], "type": "business_container_artifact", "document_type": "finance_director_model", "status": "current_operating_view", "target": {"storage_path": str(path), "director_model_hash": record["director_model_hash"]}})
        tree["folders"] = folders; tree["root"] = {**(tree.get("root") or {}), "id": "root", "type": "folder", "name": "Workflows", "children": folders}; WorkflowFileCabinetRepository.save(workspace_id, tree)

    def _project(self, workspace_id: str, financial: dict[str, Any], record: dict[str, Any], path: Path) -> None:
        compact = {"director_model_id": record["director_model_id"], "director_model_hash": record["director_model_hash"], "created_at": record["created_at"], "storage_path": str(path), "profit_and_loss": record["profit_and_loss"], "balance_sheet": record["balance_sheet"], "cash_flow": record["cash_flow"], "financial_statements": record.get("financial_statements") or {}, "statement_quality": record.get("statement_quality") or {}, "working_capital": record["working_capital"], "proactive_signals": record["proactive_signals"], "boardroom_proposals": record["boardroom_proposals"], "verification_state": record["verification_state"]}
        financial["finance_director"] = compact; financial["revision"] = int(financial.get("revision") or 0) + 1
        self.repository.save_dict(workspace_id, "business_financial_model", financial)
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            intelligence.setdefault("departments", {}).setdefault("finance", {})["finance_director"] = compact
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1; self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            runtime = boardroom.setdefault("boardroom", {}).setdefault("runtime", {}); runtime["finance_director"] = compact
            runtime["finance_boardroom_proposals"] = record["boardroom_proposals"]
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    @staticmethod
    def _verify(record: dict[str, Any]) -> None:
        expected = record.get("director_model_hash"); payload = dict(record); payload.pop("director_model_hash", None)
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError("finance_director_model_hash_mismatch")
