"""HTTP surface for provider-neutral sales invoicing and month-end readiness."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.finance_month_end_service import FinanceMonthEndService
from backend.modules.aion_business.runtime.finance_bank_activity_service import FinanceBankActivityService
from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService


router = APIRouter(prefix="/api/aion/finance-sales", tags=["aion-finance-sales"])
sales = FinanceSalesService()
month_end = FinanceMonthEndService()
bank_activity = FinanceBankActivityService()


class CustomerCreateRequest(BaseModel):
    name: str
    email: str | None = None
    tax_id: str | None = None
    billing_address: str | None = None
    payment_terms_days: int = Field(default=14, ge=0, le=365)
    created_by_person_id: str


class CustomerProviderLinkRequest(BaseModel):
    provider: str
    provider_contact_id: str
    linked_by_person_id: str


class InvoicePrepareRequest(BaseModel):
    customer_id: str
    issue_date: str
    due_date: str | None = None
    currency: str | None = None
    reference: str | None = None
    lines: list[dict[str, Any]]
    prepared_by_person_id: str


class InvoiceApprovalRequest(BaseModel):
    approved_by_person_id: str
    approved_invoice_hash: str


class InvoicePostRequest(BaseModel):
    posted_by_person_id: str


class ReminderPrepareRequest(BaseModel):
    tone: str = "friendly"
    prepared_by_person_id: str


class MonthEndRequest(BaseModel):
    period_end: str
    prepared_by_person_id: str


class BankActivityPrepareRequest(BaseModel):
    source_type: str
    transaction_type: str
    transaction_date: str
    amount: float
    currency: str = "EUR"
    reference: str
    counterparty: str
    bank_account_id: str | None = None
    source_document_id: str | None = None
    source_invoice_id: str | None = None
    test_purpose: str | None = None
    prepared_by_person_id: str


class BankActivityApprovalRequest(BaseModel):
    approved_by_person_id: str
    approved_record_hash: str


def _workspace(value: str) -> str:
    return canonical_business_id(value)


def _call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{workspace_id}")
def catalog(workspace_id: str) -> dict[str, Any]:
    return {"ok": True, **_call(sales.catalog, _workspace(workspace_id))}


@router.post("/{workspace_id}/customers")
def create_customer(workspace_id: str, request: CustomerCreateRequest) -> dict[str, Any]:
    record = _call(sales.create_customer, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, "customer": record, "external_write_performed": False}


@router.post("/{workspace_id}/customers/{customer_id}/provider-link")
def link_customer(workspace_id: str, customer_id: str,
                  request: CustomerProviderLinkRequest) -> dict[str, Any]:
    record = _call(sales.link_customer_provider, _workspace(workspace_id), customer_id,
                   **request.model_dump())
    return {"ok": True, "customer": record, "external_write_performed": False}


@router.post("/{workspace_id}/invoices/prepare")
def prepare_invoice(workspace_id: str, request: InvoicePrepareRequest) -> dict[str, Any]:
    record = _call(sales.prepare_invoice, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, "invoice": record, "external_write_performed": False}


@router.post("/{workspace_id}/invoices/{invoice_id}/approve")
def approve_invoice(workspace_id: str, invoice_id: str,
                    request: InvoiceApprovalRequest) -> dict[str, Any]:
    record = _call(sales.approve_invoice, _workspace(workspace_id), invoice_id,
                   **request.model_dump())
    return {"ok": True, "invoice": record, "external_write_performed": False}


@router.post("/{workspace_id}/invoices/{invoice_id}/post-internal")
def post_invoice(workspace_id: str, invoice_id: str,
                 request: InvoicePostRequest) -> dict[str, Any]:
    record = _call(sales.post_internal, _workspace(workspace_id), invoice_id,
                   **request.model_dump())
    return {"ok": True, "invoice": record, "external_write_performed": False}


@router.post("/{workspace_id}/invoices/{invoice_id}/reminders/prepare")
def prepare_reminder(workspace_id: str, invoice_id: str,
                     request: ReminderPrepareRequest) -> dict[str, Any]:
    record = _call(sales.prepare_reminder, _workspace(workspace_id), invoice_id,
                   **request.model_dump())
    return {"ok": True, "reminder": record, "external_message_sent": False}


@router.get("/{workspace_id}/month-end")
def latest_month_end(workspace_id: str) -> dict[str, Any]:
    return {"ok": True, "month_end": _call(month_end.latest, _workspace(workspace_id))}


@router.post("/{workspace_id}/month-end/evaluate")
def evaluate_month_end(workspace_id: str, request: MonthEndRequest) -> dict[str, Any]:
    record = _call(month_end.evaluate, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, "month_end": record, "external_write_performed": False,
            "period_closed": False}


@router.get("/{workspace_id}/bank-activity")
def list_bank_activity(workspace_id: str) -> dict[str, Any]:
    return {"ok": True, "records": _call(bank_activity.list, _workspace(workspace_id)),
            "external_write_performed": False}


@router.post("/{workspace_id}/bank-activity/prepare")
def prepare_bank_activity(workspace_id: str, request: BankActivityPrepareRequest) -> dict[str, Any]:
    record = _call(bank_activity.prepare, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, "record": record, "external_write_performed": False}


@router.post("/{workspace_id}/bank-activity/{record_id}/approve")
def approve_bank_activity(workspace_id: str, record_id: str,
                          request: BankActivityApprovalRequest) -> dict[str, Any]:
    record = _call(bank_activity.approve, _workspace(workspace_id), record_id, **request.model_dump())
    return {"ok": True, "record": record, "external_write_performed": False}
