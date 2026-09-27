"""Read-only FreeAgent adapter for the governed accountant harness."""

from __future__ import annotations

from typing import Any

import httpx

from .accounting_provider_contract import AccountingProviderCapabilities, empty_collections, number, source_ref


def _identifier(value: Any) -> str:
    return str(value or "").rstrip("/").rsplit("/", 1)[-1]


class FreeAgentAccountingAdapter:
    provider_id = "freeagent"
    PRODUCTION_BASE = "https://api.freeagent.com/v2"
    SANDBOX_BASE = "https://api.sandbox.freeagent.com/v2"

    def capabilities(self) -> AccountingProviderCapabilities:
        return AccountingProviderCapabilities(
            provider_id=self.provider_id,
            label="FreeAgent",
            oauth2=True,
            read_collections=("categories", "contacts", "invoices", "bills", "bank_accounts", "bank_transactions", "journal_sets"),
            draft_writes=("contact", "invoice", "bill", "journal_set"),
            approved_writes=("contact", "invoice", "bill", "bank_transaction_explanation", "journal_set"),
            bank_reconciliation_api=False,
        )

    async def read_snapshot(self, *, access_token: str, company_id: str,
                            sandbox: bool = False) -> dict[str, Any]:
        if not access_token:
            raise ValueError("freeagent_access_token_required")
        base = self.SANDBOX_BASE if sandbox else self.PRODUCTION_BASE
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        result: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=45) as client:
            for key in ("categories", "contacts", "invoices", "bills", "bank_accounts", "journal_sets"):
                response = await client.get(f"{base}/{key}", headers=headers, params={"per_page": 100})
                response.raise_for_status()
                result[key] = list(response.json().get(key) or [])
            transactions: list[dict[str, Any]] = []
            for account in result["bank_accounts"]:
                account_url = account.get("url")
                if not account_url:
                    continue
                response = await client.get(
                    f"{base}/bank_transactions", headers=headers,
                    params={"bank_account": account_url, "view": "all", "per_page": 100},
                )
                response.raise_for_status()
                transactions.extend(response.json().get("bank_transactions") or [])
            result["bank_transactions"] = transactions
        return result

    def normalize_snapshot(self, raw: dict[str, Any], *, sync_id: str,
                           company_id: str) -> dict[str, list[dict[str, Any]]]:
        records = empty_collections()
        contacts = {_identifier(row.get("url")): row for row in raw.get("contacts") or []}
        for item in raw.get("categories") or []:
            records["accounts"].append({
                "account_id": _identifier(item.get("url") or item.get("nominal_code")),
                "code": item.get("nominal_code"), "name": item.get("description") or item.get("name"),
                "type": item.get("group_description") or item.get("group"), "subtype": item.get("type"),
                "status": "active" if item.get("active", True) else "archived", "currency": None,
                "bank_account_type": None,
                "source_ref": source_ref(self.provider_id, sync_id, "categories", item.get("url") or item.get("nominal_code")),
            })
        for collection, invoice_type in (("invoices", "sales_invoice"), ("bills", "supplier_bill")):
            for item in raw.get(collection) or []:
                contact_id = _identifier(item.get("contact")); contact = contacts.get(contact_id, {})
                total = number(item.get("total_value") or item.get("total"))
                due = number(item.get("due_value") if item.get("due_value") is not None else item.get("outstanding_value"))
                status = str(item.get("status") or "recorded").lower()
                if due == 0 and status == "paid":
                    due = 0.0
                elif due == 0 and status not in ("paid", "zero value", "refunded"):
                    due = total
                records["invoices"].append({
                    "invoice_id": _identifier(item.get("url")),
                    "invoice_number": item.get("reference") or item.get("invoice_number"),
                    "invoice_type": invoice_type, "status": status,
                    "contact": {"contact_id": contact_id or None, "display_name": contact.get("organisation_name") or contact.get("contact_name")},
                    "date": item.get("dated_on"), "due_date": item.get("due_on"), "currency": item.get("currency"),
                    "total": total, "amount_paid": round(max(0, total - due), 4), "amount_due": due,
                    "reference": item.get("reference"), "is_overdue": status == "overdue",
                    "line_items": self._items(item.get("invoice_items") or item.get("bill_items")),
                    "source_ref": source_ref(self.provider_id, sync_id, collection, item.get("url")),
                })
        for item in raw.get("bank_transactions") or []:
            amount = number(item.get("amount")); unexplained = number(item.get("unexplained_amount"))
            records["bank_transactions"].append({
                "bank_transaction_id": _identifier(item.get("url") or item.get("transaction_id")),
                "transaction_type": "receive" if amount >= 0 else "spend", "status": "recorded",
                "contact": {"contact_id": None, "display_name": None}, "date": item.get("dated_on"),
                "reference": item.get("description"), "total": amount,
                "bank_account_id": _identifier(item.get("bank_account")),
                "is_reconciled": unexplained == 0,
                "source_ref": source_ref(self.provider_id, sync_id, "bank_transactions", item.get("url") or item.get("transaction_id")),
            })
        for item in raw.get("journal_sets") or []:
            entries = item.get("journal_entries") or []
            records["manual_journals"].append({
                "manual_journal_id": _identifier(item.get("url")), "date": item.get("dated_on"),
                "status": "posted", "narration": item.get("description"), "line_count": len(entries),
                "net_amount": round(sum(number(row.get("debit_value")) for row in entries), 4),
                "source_ref": source_ref(self.provider_id, sync_id, "journal_sets", item.get("url")),
            })
        return records

    @staticmethod
    def _items(items: Any) -> list[dict[str, Any]]:
        return [{
            "description": row.get("description"), "quantity": number(row.get("quantity")),
            "unit_amount": number(row.get("price") or row.get("unit_price")),
            "line_amount": number(row.get("value") or row.get("total_value")),
            "account_code": _identifier(row.get("category")), "tax_type": row.get("sales_tax_status"),
            "tracking": [],
        } for row in items or []]
