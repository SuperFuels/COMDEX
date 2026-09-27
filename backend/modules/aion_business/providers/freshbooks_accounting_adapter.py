"""Read-only FreshBooks adapter for the governed accountant harness."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .accounting_provider_contract import AccountingProviderCapabilities, empty_collections, number, source_ref


class FreshBooksAccountingAdapter:
    provider_id = "freshbooks"
    BASE_URL = "https://api.freshbooks.com/accounting"

    def capabilities(self) -> AccountingProviderCapabilities:
        return AccountingProviderCapabilities(
            provider_id=self.provider_id, label="FreshBooks", oauth2=True,
            read_collections=("chart_of_accounts", "invoices", "bills", "payments", "expenses"),
            draft_writes=("client", "invoice", "expense"),
            approved_writes=("client", "invoice", "payment", "expense", "journal_entry"),
            bank_reconciliation_api=False,
        )

    @staticmethod
    def _identifiers(company_id: str) -> tuple[str, str | None]:
        account_id, separator, business_uuid = str(company_id or "").partition("|")
        if not account_id:
            raise ValueError("freshbooks_account_id_required")
        return account_id, business_uuid if separator and business_uuid else None

    async def read_snapshot(self, *, access_token: str, company_id: str,
                            sandbox: bool = False) -> dict[str, Any]:
        if not access_token:
            raise ValueError("freshbooks_access_token_required")
        account_id, business_uuid = self._identifiers(company_id)
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        base = f"{self.BASE_URL}/account/{quote(account_id, safe='')}"
        endpoints = {
            "invoices": "invoices/invoices", "bills": "bills/bills",
            "payments": "payments/payments", "expenses": "expenses/expenses",
        }
        result: dict[str, Any] = {"chart_of_accounts": []}
        async with httpx.AsyncClient(timeout=45) as client:
            for key, path in endpoints.items():
                response = await client.get(f"{base}/{path}", headers=headers, params={"per_page": 100})
                response.raise_for_status()
                payload = ((response.json().get("response") or {}).get("result") or {})
                result[key] = list(payload.get(key) or [])
            if business_uuid:
                response = await client.get(
                    f"{self.BASE_URL}/businesses/{quote(business_uuid, safe='')}/reports/chart_of_accounts",
                    headers=headers, params={"use_ledger_entries": "true", "state": "active"},
                )
                response.raise_for_status()
                payload = ((response.json().get("response") or {}).get("result") or {})
                result["chart_of_accounts"] = list(payload.get("journal_entry_accounts") or [])
        return result

    def normalize_snapshot(self, raw: dict[str, Any], *, sync_id: str,
                           company_id: str) -> dict[str, list[dict[str, Any]]]:
        records = empty_collections()
        for item in raw.get("chart_of_accounts") or []:
            records["accounts"].append({
                "account_id": str(item.get("account_uuid") or item.get("uuid") or ""),
                "code": item.get("account_number") or item.get("number"),
                "name": item.get("account_name") or item.get("name"),
                "type": item.get("account_type") or item.get("type"),
                "subtype": item.get("account_sub_type") or item.get("sub_type"),
                "status": item.get("state") or "active", "currency": item.get("currency_code"),
                "bank_account_type": item.get("account_sub_type") if item.get("account_type") == "asset" else None,
                "source_ref": source_ref(self.provider_id, sync_id, "chart_of_accounts", item.get("account_uuid") or item.get("uuid")),
            })
        for item in raw.get("invoices") or []:
            amount = item.get("amount") or {}; outstanding = item.get("outstanding") or {}
            total = number(amount.get("amount") if isinstance(amount, dict) else amount)
            due = number(outstanding.get("amount") if isinstance(outstanding, dict) else outstanding)
            status = str(item.get("v3_status") or item.get("status") or "recorded").lower()
            records["invoices"].append({
                "invoice_id": str(item.get("invoiceid") or item.get("id") or ""),
                "invoice_number": item.get("invoice_number") or item.get("number"),
                "invoice_type": "sales_invoice", "status": status,
                "contact": {"contact_id": str(item.get("customerid") or item.get("clientid") or "") or None,
                            "display_name": item.get("organization") or item.get("customer_name")},
                "date": item.get("create_date") or item.get("date"), "due_date": item.get("due_date"),
                "currency": amount.get("code") if isinstance(amount, dict) else item.get("currency_code"),
                "total": total, "amount_paid": round(max(0, total - due), 4), "amount_due": due,
                "reference": item.get("po_number"), "is_overdue": "overdue" in status,
                "line_items": self._lines(item.get("lines")),
                "source_ref": source_ref(self.provider_id, sync_id, "invoices", item.get("invoiceid") or item.get("id")),
            })
        for item in raw.get("bills") or []:
            total_amount = item.get("total_amount") or item.get("amount") or {}
            outstanding = item.get("outstanding") or {}
            total = number(total_amount.get("amount") if isinstance(total_amount, dict) else total_amount)
            due = number(outstanding.get("amount") if isinstance(outstanding, dict) else outstanding)
            status = str(item.get("status") or "recorded").lower()
            bill_id = str(item.get("id") or "")
            records["invoices"].append({
                "invoice_id": bill_id, "invoice_number": item.get("bill_number"),
                "invoice_type": "supplier_bill", "status": status,
                "contact": {"contact_id": str(item.get("vendorid") or "") or None,
                            "display_name": (item.get("vendor") or {}).get("vendor_name") if isinstance(item.get("vendor"), dict) else item.get("vendor")},
                "date": item.get("issue_date"), "due_date": item.get("due_date"),
                "currency": total_amount.get("code") if isinstance(total_amount, dict) else item.get("currency_code"),
                "total": total, "amount_paid": round(max(0, total - due), 4), "amount_due": due,
                "reference": item.get("bill_number"), "is_overdue": status == "overdue",
                "line_items": self._lines(item.get("lines")),
                "source_ref": source_ref(self.provider_id, sync_id, "bills", item.get("id")),
            })
            for payment in item.get("bill_payments") or []:
                amount = payment.get("amount") or {}
                records["payments"].append({
                    "payment_id": str(payment.get("id") or ""), "date": payment.get("payment_date") or payment.get("date"),
                    "amount": number(amount.get("amount") if isinstance(amount, dict) else amount),
                    "status": "recorded", "reference": payment.get("note"), "invoice_id": bill_id,
                    "invoice_number": item.get("bill_number"), "account_id": payment.get("account_id"),
                    "source_ref": source_ref(self.provider_id, sync_id, "bill_payments", payment.get("id")),
                })
        for item in raw.get("payments") or []:
            amount = item.get("amount") or {}
            records["payments"].append({
                "payment_id": str(item.get("id") or item.get("logid") or ""), "date": item.get("date"),
                "amount": number(amount.get("amount") if isinstance(amount, dict) else amount),
                "status": "deleted" if item.get("vis_state") == 1 else "recorded", "reference": item.get("note"),
                "invoice_id": str(item.get("invoiceid") or "") or None, "invoice_number": None,
                "account_id": None,
                "source_ref": source_ref(self.provider_id, sync_id, "payments", item.get("id") or item.get("logid")),
            })
        for item in raw.get("expenses") or []:
            amount = item.get("amount") or {}; value = number(amount.get("amount") if isinstance(amount, dict) else amount)
            records["bank_transactions"].append({
                "bank_transaction_id": str(item.get("expenseid") or item.get("id") or ""),
                "transaction_type": "expense", "status": "deleted" if item.get("vis_state") == 1 else "recorded",
                "contact": {"contact_id": None, "display_name": item.get("vendor")}, "date": item.get("date"),
                "reference": item.get("notes"), "total": -abs(value), "bank_account_id": item.get("accountid"),
                "is_reconciled": False,
                "source_ref": source_ref(self.provider_id, sync_id, "expenses", item.get("expenseid") or item.get("id")),
            })
        return records

    @staticmethod
    def _lines(lines: Any) -> list[dict[str, Any]]:
        return [{
            "description": row.get("description") or row.get("name"), "quantity": number(row.get("qty")),
            "unit_amount": number((row.get("unit_cost") or {}).get("amount") if isinstance(row.get("unit_cost"), dict) else row.get("unit_cost")),
            "line_amount": number((row.get("amount") or {}).get("amount") if isinstance(row.get("amount"), dict) else row.get("amount")),
            "account_code": None, "tax_type": row.get("taxName1"), "tracking": [],
        } for row in lines or []]
