"""Read-only Sage Business Cloud Accounting adapter for the accountant harness."""

from __future__ import annotations

from typing import Any

import httpx

from .accounting_provider_contract import AccountingProviderCapabilities, empty_collections, number, source_ref


class SageAccountingAdapter:
    provider_id = "sage_accounting"
    BASE_URL = "https://api.accounting.sage.com/v3.1"

    def capabilities(self) -> AccountingProviderCapabilities:
        return AccountingProviderCapabilities(
            provider_id=self.provider_id, label="Sage Business Cloud Accounting", oauth2=True,
            read_collections=("ledger_accounts", "sales_invoices", "purchase_invoices", "contact_payments", "bank_account_transactions", "ledger_entries"),
            draft_writes=("contact", "sales_invoice", "purchase_invoice"),
            approved_writes=("contact", "sales_invoice", "purchase_invoice", "contact_payment", "bank_transaction", "journal"),
            bank_reconciliation_api=False,
        )

    async def read_snapshot(self, *, access_token: str, company_id: str,
                            sandbox: bool = False) -> dict[str, Any]:
        if not access_token or not company_id:
            raise ValueError("sage_access_token_and_business_required")
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json", "X-Business": company_id}
        endpoints = {
            "ledger_accounts": "ledger_accounts", "sales_invoices": "sales_invoices",
            "purchase_invoices": "purchase_invoices", "contact_payments": "contact_payments",
            "bank_account_transactions": "bank_account_transactions", "ledger_entries": "ledger_entries",
        }
        result: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=45) as client:
            for key, path in endpoints.items():
                response = await client.get(f"{self.BASE_URL}/{path}", headers=headers, params={"items_per_page": 200})
                response.raise_for_status()
                payload = response.json()
                result[key] = list(payload.get("$items") or payload.get("items") or [])
        return result

    def normalize_snapshot(self, raw: dict[str, Any], *, sync_id: str,
                           company_id: str) -> dict[str, list[dict[str, Any]]]:
        records = empty_collections()
        for item in raw.get("ledger_accounts") or []:
            records["accounts"].append({
                "account_id": str(item.get("id") or ""), "code": item.get("nominal_code"),
                "name": item.get("displayed_as") or item.get("name"),
                "type": (item.get("ledger_account_type") or {}).get("displayed_as"),
                "subtype": None, "status": "active" if item.get("active", True) else "archived",
                "currency": None, "bank_account_type": None,
                "source_ref": source_ref(self.provider_id, sync_id, "ledger_accounts", item.get("id")),
            })
        for collection, invoice_type in (("sales_invoices", "sales_invoice"), ("purchase_invoices", "supplier_bill")):
            for item in raw.get(collection) or []:
                contact = item.get("contact") or {}; total = number(item.get("total_amount")); outstanding = number(item.get("outstanding_amount"))
                records["invoices"].append({
                    "invoice_id": str(item.get("id") or ""), "invoice_number": item.get("displayed_as") or item.get("reference"),
                    "invoice_type": invoice_type, "status": (item.get("status") or {}).get("displayed_as") or "recorded",
                    "contact": {"contact_id": contact.get("id"), "display_name": contact.get("displayed_as")},
                    "date": item.get("date"), "due_date": item.get("due_date"), "currency": (item.get("currency") or {}).get("id"),
                    "total": total, "amount_paid": round(max(0, total - outstanding), 4), "amount_due": outstanding,
                    "reference": item.get("reference"), "is_overdue": False, "line_items": [],
                    "source_ref": source_ref(self.provider_id, sync_id, collection, item.get("id")),
                })
        for item in raw.get("contact_payments") or []:
            transaction = item.get("transaction") or {}; account = item.get("bank_account") or {}
            records["payments"].append({
                "payment_id": str(item.get("id") or ""), "date": item.get("date"), "amount": number(item.get("total_amount")),
                "status": "recorded", "reference": item.get("reference"), "invoice_id": transaction.get("id"),
                "invoice_number": transaction.get("displayed_as"), "account_id": account.get("id"),
                "source_ref": source_ref(self.provider_id, sync_id, "contact_payments", item.get("id")),
            })
        for item in raw.get("bank_account_transactions") or []:
            contact = item.get("contact") or {}; txn_type = str((item.get("transaction_type") or {}).get("id") or "").lower()
            amount = number(item.get("total_amount")); signed = -abs(amount) if any(word in txn_type for word in ("payment", "purchase", "out")) else amount
            records["bank_transactions"].append({
                "bank_transaction_id": str(item.get("id") or ""), "transaction_type": txn_type or "bank_transaction",
                "status": "recorded", "contact": {"contact_id": contact.get("id"), "display_name": contact.get("displayed_as")},
                "date": item.get("date"), "reference": item.get("reference"), "total": signed,
                "bank_account_id": (item.get("bank_account") or {}).get("id"), "is_reconciled": bool(item.get("reconciled")),
                "source_ref": source_ref(self.provider_id, sync_id, "bank_account_transactions", item.get("id")),
            })
        for item in raw.get("ledger_entries") or []:
            records["manual_journals"].append({
                "manual_journal_id": str(item.get("id") or ""), "date": item.get("date"), "status": "posted",
                "narration": item.get("description"), "line_count": len(item.get("ledger_entry_lines") or []),
                "net_amount": number(item.get("total_amount")),
                "source_ref": source_ref(self.provider_id, sync_id, "ledger_entries", item.get("id")),
            })
        return records
