"""HTTP API for the shared Work & Schedule workspace."""

from __future__ import annotations

from typing import Any
import base64
from datetime import UTC, datetime
import html
import os
import re

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from urllib.parse import quote
import json
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService
from backend.modules.aion_business.runtime.work_notification_delivery import WorkNotificationDeliveryService
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService


router = APIRouter(prefix="/api/aion/business/work-schedule", tags=["aion-business-work-schedule"])


class SaveRequest(BaseModel):
    model: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = None
    changed_by: str = "desktop_user"


class ActionRequest(BaseModel):
    operation: str
    fields: dict[str, Any] = Field(default_factory=dict)
    actor_id: str = "desktop_user"


class IntakeRequest(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    channel: str = "website"
    sales_endpoint_id: str | None = None


class UploadRequest(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    data_base64: str
    actor_id: str = "desktop_user"


class DocumentRequest(BaseModel):
    kind: str
    actor_id: str = "desktop_user"
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    tax_rate: str = "0"
    document_profile: dict[str, Any] = Field(default_factory=dict)


class QuoteEmailDraftRequest(BaseModel):
    document_id: str
    to: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=20000)
    actor_id: str = "desktop_user"


class InterpretRequest(BaseModel):
    text: str


class RewriteDescriptionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=6000)


class PortalAccessRequest(BaseModel):
    actor_id: str = "desktop_user"
    expires_days: int = 30


class PortalActionRequest(BaseModel):
    operation: str
    fields: dict[str, Any] = Field(default_factory=dict)


class PaymentDeliveryRetryRequest(BaseModel):
    acceptance_url: str = Field(min_length=1, max_length=2000)
    payment_method: str = Field(default="bank_transfer", max_length=40)
    business: dict[str, Any] = Field(default_factory=dict)
    actor_id: str = "desktop_user"


def _business_display_name(business: dict[str, Any], workspace_id: str) -> str:
    """Return a customer-safe name, repairing legacy placeholder profiles."""
    name = str(business.get("name") or "").strip()
    if name.casefold() not in {"", "your business", "the business", "business status pending verification"}:
        return name
    words = re.sub(r"[^a-zA-Z0-9]+", " ", str(workspace_id or "")).strip()
    return words.title() or "The business"


class ReminderDeliveryRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=160)


def _workspace(value: str) -> str:
    try:
        return canonical_business_id(value)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _error(error: Exception) -> HTTPException:
    code = str(error)
    if isinstance(error, LookupError):
        return HTTPException(status_code=404, detail=code)
    if code == "work_schedule_revision_conflict":
        return HTTPException(status_code=409, detail=code)
    return HTTPException(status_code=422, detail=code)


@router.get("/{workspace_id}")
def get_schedule(workspace_id: str) -> dict[str, Any]:
    key = _workspace(workspace_id)
    return {"ok": True, "workspace_id": key, "model": WorkScheduleService().get(key)}


@router.put("/{workspace_id}")
def save_schedule(workspace_id: str, request: SaveRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        model = WorkScheduleService().save(
            key, request.model, expected_revision=request.expected_revision, changed_by=request.changed_by,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/actions")
def schedule_action(workspace_id: str, request: ActionRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        model = WorkScheduleService().action(key, request.operation, request.fields, actor_id=request.actor_id)
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/intake")
def create_intake(workspace_id: str, request: IntakeRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        model = WorkScheduleService().create_intake(key, request.fields, channel=request.channel)
    except ValueError as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/items/{item_id}/files")
def upload_file(workspace_id: str, item_id: str, request: UploadRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkScheduleService().upload(
            key, item_id, filename=request.filename, content_type=request.content_type,
            data_base64=request.data_base64, actor_id=request.actor_id,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}


@router.post("/{workspace_id}/items/{item_id}/documents")
def generate_document(workspace_id: str, item_id: str, request: DocumentRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkScheduleService().generate_document(
            key, item_id, request.kind, actor_id=request.actor_id,
            line_items=request.line_items, tax_rate=request.tax_rate,
            document_profile=request.document_profile,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}


@router.get("/{workspace_id}/items/{item_id}/files/{document_id}")
def download_file(workspace_id: str, item_id: str, document_id: str, inline: bool = False) -> Response:
    key = _workspace(workspace_id)
    try:
        data, document = WorkScheduleService().file_bytes(key, item_id, document_id)
    except LookupError as error:
        raise _error(error) from error
    filename = str(document.get("name") or "document")
    return Response(
        content=data,
        media_type=str(document.get("content_type") or "application/octet-stream"),
        headers={"Content-Disposition": f"{'inline' if inline else 'attachment'}; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/{workspace_id}/items/{item_id}/quote-email-draft")
def create_quote_email_draft(
    workspace_id: str, item_id: str, request: QuoteEmailDraftRequest, http_request: Request,
) -> dict[str, Any]:
    """Create an editable Gmail draft with the generated quote PDF attached.

    This is an explicit user-triggered draft action. It never sends the message.
    """
    key = _workspace(workspace_id)
    if "@" not in request.to:
        raise HTTPException(status_code=422, detail="Add a valid customer email address")
    service = WorkScheduleService()
    try:
        file_data, document = service.file_bytes(key, item_id, request.document_id)
    except LookupError as error:
        raise _error(error) from error
    if document.get("kind") != "quote" or document.get("content_type") != "application/pdf":
        raise HTTPException(status_code=422, detail="Generate the quotation PDF before preparing the email")
    try:
        portal = service.issue_portal_access(key, item_id, actor_id=request.actor_id, expires_days=30)
        item = next(row for row in portal["schedule"].get("items", []) if row.get("id") == item_id)
    except (ValueError, LookupError, StopIteration) as error:
        raise _error(error) from error
    public_base = str(os.environ.get("TESSARIS_CUSTOMER_PORTAL_BASE_URL") or http_request.base_url).rstrip("/")
    acceptance_url = f"{public_base}/api/aion/business/work-schedule/portal/{portal['token']}/accept"
    quote = item.get("quote") or {}
    profile = quote.get("document_profile") or {}
    business = profile.get("business") or {}
    quote_number = str(quote.get("number") or "Quotation")
    message_html = "<br>".join(html.escape(request.body).splitlines())
    html_body = f"""<!doctype html><html><body style="margin:0;background:#fff;font-family:Arial,sans-serif;color:#172033">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:22px 8px">
<table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;width:100%">
<tr><td style="font-size:16px;line-height:1.55">{message_html}</td></tr>
<tr><td style="padding:24px 0 10px"><a href="{html.escape(acceptance_url, quote=True)}" style="display:inline-block;background:#2f66e8;color:#fff;text-decoration:none;font-weight:bold;padding:14px 24px;border-radius:7px">Accept quotation</a></td></tr>
<tr><td style="color:#60708a;font-size:12px">The complete branded quotation {html.escape(quote_number)} is attached as a PDF. Acceptance records the agreed quotation, Terms &amp; Conditions and payment schedule.</td></tr>
</table></td></tr></table></body></html>"""
    from backend.api.local_node_router import get_runtime
    # Gmail OAuth is connected through the shared local Vault. The dashboard,
    # OAuth callback and quote drafts must all read the same connector store.
    # Using the business workspace runtime here made the dashboard report
    # "connected" while quote drafting incorrectly saw a different empty store.
    runtime = get_runtime()
    health = runtime.get_gmail_connector_health()
    if str(health.get("auth_status") or "").lower() != "connected":
        raise HTTPException(status_code=409, detail="No connected Gmail account is available. Save or share the PDF instead.")
    try:
        result = runtime._create_gmail_draft(
            to=request.to,
            subject=request.subject,
            body=request.body,
            html_body=html_body,
            attachments=[{
                "filename": document.get("name") or "quotation.pdf",
                "content_type": "application/pdf",
                "data_base64": base64.b64encode(file_data).decode("ascii"),
            }],
        )
    except (ValueError, RuntimeError) as error:
        raise _error(error) from error
    schedule = portal["schedule"]
    scheduled_item = next((row for row in schedule.get("items", []) if row.get("id") == item_id), None)
    if scheduled_item is not None:
        scheduled_item["quote_email_draft"] = {
            "status": "created",
            "to": request.to,
            "subject": request.subject,
            "body": request.body,
            "document_id": request.document_id,
            "draft_id": result.get("draft_id") or "",
            "gmail_url": result.get("gmail_url") or "",
            "gmail_account": result.get("account_email") or "",
            "acceptance_url": acceptance_url,
            "created_at": result.get("created_at") or datetime.now(UTC).replace(microsecond=0).isoformat(),
            "error": "",
        }
        scheduled_item.setdefault("updates", []).append({
            "id": f"update_quote_email_{request.document_id}",
            "text": f"Gmail quotation draft prepared for {request.to} with {document.get('name') or 'quotation.pdf'} attached. Nothing was sent.",
            "at": scheduled_item["quote_email_draft"]["created_at"],
            "by": request.actor_id,
        })
        schedule = service.save(
            key, schedule, expected_revision=schedule["revision"], changed_by=request.actor_id,
        )
    return {
        "ok": True,
        "created": bool(result.get("created")),
        "sent": False,
        "draft_id": result.get("draft_id"),
        "gmail_url": result.get("gmail_url"),
        "gmail_account": result.get("account_email"),
        "acceptance_url": acceptance_url,
        "attachment": document.get("name") or "quotation.pdf",
        "schedule": schedule,
    }


@router.post("/{workspace_id}/items/{item_id}/quote-email-send")
def send_quote_email(
    workspace_id: str, item_id: str, request: QuoteEmailDraftRequest, http_request: Request,
) -> dict[str, Any]:
    """Send the approved quotation immediately after the user presses Send."""
    key = _workspace(workspace_id)
    if "@" not in request.to:
        raise HTTPException(status_code=422, detail="Add a valid customer email address")
    service = WorkScheduleService()
    try:
        file_data, document = service.file_bytes(key, item_id, request.document_id)
    except LookupError as error:
        raise _error(error) from error
    if document.get("kind") != "quote" or document.get("content_type") != "application/pdf":
        raise HTTPException(status_code=422, detail="Generate the quotation PDF before sending the email")
    try:
        portal = service.issue_portal_access(key, item_id, actor_id=request.actor_id, expires_days=30)
        item = next(row for row in portal["schedule"].get("items", []) if row.get("id") == item_id)
    except (ValueError, LookupError, StopIteration) as error:
        raise _error(error) from error

    public_base = str(os.environ.get("TESSARIS_CUSTOMER_PORTAL_BASE_URL") or http_request.base_url).rstrip("/")
    acceptance_url = f"{public_base}/api/aion/business/work-schedule/portal/{portal['token']}/accept"
    quote = item.get("quote") or {}
    quote_number = str(quote.get("number") or "Quotation")
    message_html = "<br>".join(html.escape(request.body).splitlines())
    html_body = f"""<!doctype html><html><body style="margin:0;background:#fff;font-family:Arial,sans-serif;color:#172033">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="padding:22px 8px">
<table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;width:100%">
<tr><td style="font-size:16px;line-height:1.55">{message_html}</td></tr>
<tr><td style="padding:24px 0 10px"><a href="{html.escape(acceptance_url, quote=True)}" style="display:inline-block;background:#2f66e8;color:#fff;text-decoration:none;font-weight:bold;padding:14px 24px;border-radius:7px">Accept quotation</a></td></tr>
<tr><td style="color:#60708a;font-size:12px">The complete branded quotation {html.escape(quote_number)} is attached as a PDF. Acceptance records the agreed quotation, Terms &amp; Conditions and payment schedule.</td></tr>
</table></td></tr></table></body></html>"""
    from backend.api.local_node_router import get_runtime
    runtime = get_runtime()
    health = runtime.get_gmail_connector_health()
    if str(health.get("auth_status") or "").lower() != "connected":
        raise HTTPException(status_code=409, detail="No connected Gmail account is available. Save or share the PDF instead.")
    try:
        result = runtime._send_gmail_message(
            to=request.to,
            subject=request.subject,
            body=request.body,
            html_body=html_body,
            attachments=[{
                "filename": document.get("name") or "quotation.pdf",
                "content_type": "application/pdf",
                "data_base64": base64.b64encode(file_data).decode("ascii"),
            }],
        )
    except (ValueError, RuntimeError) as error:
        raise _error(error) from error

    schedule = portal["schedule"]
    scheduled_item = next((row for row in schedule.get("items", []) if row.get("id") == item_id), None)
    sent_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    if scheduled_item is not None:
        quote_state = dict(scheduled_item.get("quote") or {})
        if str(quote_state.get("status") or "") != "customer_approved":
            quote_state.update({"status": "sent", "sent_at": sent_at})
            scheduled_item["quote"] = quote_state
            scheduled_item["status"] = "awaiting_approval"
        scheduled_item["quote_email_delivery"] = {
            "status": "sent", "to": request.to, "subject": request.subject, "body": request.body,
            "document_id": request.document_id, "message_id": result.get("message_id") or "",
            "acceptance_url": acceptance_url, "sent_at": sent_at, "error": "",
        }
        scheduled_item.setdefault("updates", []).append({
            "id": f"update_quote_sent_{request.document_id}",
            "text": f"Quotation {quote_number} sent to {request.to}; awaiting customer acceptance.",
            "at": sent_at, "by": request.actor_id,
        })
        schedule = service.save(key, schedule, expected_revision=schedule["revision"], changed_by=request.actor_id)
    return {
        "ok": True, "sent": True, "message_id": result.get("message_id"),
        "acceptance_url": acceptance_url, "attachment": document.get("name") or "quotation.pdf",
        "sent_at": sent_at, "schedule": schedule,
    }


@router.post("/{workspace_id}/interpret")
def interpret_instruction(workspace_id: str, request: InterpretRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    return {"ok": True, "workspace_id": key, "interpretation": WorkScheduleService().interpret(request.text)}


@router.post("/{workspace_id}/rewrite-description")
def rewrite_quote_description(workspace_id: str, request: RewriteDescriptionRequest) -> dict[str, Any]:
    """Rewrite a rough scope into an editable customer-facing draft using only the local model."""
    key = _workspace(workspace_id)
    source = request.text.strip()
    if not source:
        raise HTTPException(status_code=422, detail="Write a rough description before asking SI to rewrite it")
    try:
        from backend.services.aion_mission_mode.pilot_local_model_runtime import (
            run_selected_local_chat,
            selected_local_runtime_profile_for_workspace,
        )

        profile = selected_local_runtime_profile_for_workspace(key)
        profile = {**profile, "max_output_tokens": min(700, int(profile.get("max_output_tokens") or 700))}
        result = run_selected_local_chat(
            prompt=(
                "Rewrite the following rough scope of work into concise, professional, customer-facing English. "
                "Correct spelling and grammar. Preserve every factual detail and do not invent materials, tasks, "
                "prices, dates, promises, warranties or exclusions. Use a short opening sentence and bullet points "
                "when there is more than one distinct task. Return only the finished description, with no heading, "
                "commentary, quotation marks or markdown code fence.\n\nROUGH DESCRIPTION:\n" + source
            ),
            system_prompt=(
                "You edit quotation descriptions. Keep the wording clear and plain, preserve the supplied facts, "
                "and never add commitments. Return only the editable rewritten text."
            ),
            runtime_profile=profile,
            timeout_seconds=180.0,
        )
    except Exception as error:
        code = str(error) or type(error).__name__
        raise HTTPException(status_code=503, detail=f"Local rewrite is unavailable: {code}") from error
    description = str(result.get("content") or "").strip()
    if description.startswith("```") and description.endswith("```"):
        description = description.strip("`").strip()
    if len(description) < 3:
        raise HTTPException(status_code=503, detail="The local model did not return a usable description")
    return {
        "ok": True,
        "workspace_id": key,
        "description": description,
        "provider": "local_model",
        "editable": True,
        "saved": False,
    }


@router.post("/{workspace_id}/rewrite-quote-email-template")
def rewrite_quote_email_template(workspace_id: str, request: RewriteDescriptionRequest) -> dict[str, Any]:
    """Turn a rough quote-email template into an editable local-model draft."""
    key = _workspace(workspace_id)
    source = request.text.strip()
    if not source:
        raise HTTPException(status_code=422, detail="Write a rough quote email before asking SI to rewrite it")
    placeholders = set(re.findall(r"\{(?:customer_name|quote_number|business_name)\}", source))
    try:
        from backend.services.aion_mission_mode.pilot_local_model_runtime import (
            run_selected_local_chat,
            selected_local_runtime_profile_for_workspace,
        )

        profile = selected_local_runtime_profile_for_workspace(key)
        profile = {**profile, "max_output_tokens": min(600, int(profile.get("max_output_tokens") or 600))}
        result = run_selected_local_chat(
            prompt=(
                "Rewrite this rough reusable quotation email as a concise, warm and professional customer email. "
                "Correct spelling and grammar, keep it in plain English, and do not invent facts, prices, dates, "
                "attachments or promises. Preserve every placeholder exactly as written, including {customer_name}, "
                "{quote_number} and {business_name} when present. Return only the finished email template as plain "
                "text, with no subject line, heading, commentary, quotation marks or markdown.\n\nROUGH EMAIL TEMPLATE:\n" + source
            ),
            system_prompt=(
                "You edit reusable customer email templates. Preserve all brace placeholders exactly. "
                "Return only the editable email body and never send or save anything."
            ),
            runtime_profile=profile,
            timeout_seconds=180.0,
        )
    except Exception as error:
        code = str(error) or type(error).__name__
        raise HTTPException(status_code=503, detail=f"Local rewrite is unavailable: {code}") from error
    email_body = str(result.get("content") or "").strip()
    if email_body.startswith("```") and email_body.endswith("```"):
        email_body = email_body.strip("`").strip()
    bold_wrapper = re.fullmatch(r"\*\*([\s\S]*)\*\*", email_body)
    if bold_wrapper:
        email_body = bold_wrapper.group(1).strip()
    email_body = re.sub(r"[ \t]{2,}\n", "\n", email_body)
    missing = sorted(token for token in placeholders if token not in email_body)
    if missing:
        raise HTTPException(status_code=503, detail="The local rewrite did not preserve: " + ", ".join(missing))
    if len(email_body) < 3:
        raise HTTPException(status_code=503, detail="The local model did not return a usable email template")
    return {
        "ok": True,
        "workspace_id": key,
        "email_body": email_body,
        "provider": "local_model",
        "editable": True,
        "saved": False,
    }


@router.post("/{workspace_id}/items/{item_id}/portal-access")
def issue_portal_access(workspace_id: str, item_id: str, request: PortalAccessRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkScheduleService().issue_portal_access(
            key, item_id, actor_id=request.actor_id, expires_days=request.expires_days,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}


@router.post("/{workspace_id}/reminders/{reminder_id}/approve-and-send")
def approve_and_send_reminder(
    workspace_id: str,
    reminder_id: str,
    request: ReminderDeliveryRequest,
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkNotificationDeliveryService().send_approved(
            key,
            reminder_id,
            approved_by=request.approved_by,
        )
    except (ValueError, LookupError, PermissionError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}



@router.get("/portal/{token}")
def customer_portal_view(token: str) -> dict[str, Any]:
    try:
        return {"ok": True, **WorkScheduleService().portal_view(token)}
    except (ValueError, LookupError) as error:
        raise _error(error) from error


@router.post("/portal/{token}/actions")
def customer_portal_action(token: str, request: PortalActionRequest) -> dict[str, Any]:
    service = WorkScheduleService()
    try:
        result = service.portal_action(token, request.operation, request.fields)
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    result_schedule = result.get("schedule") or {}
    result_item_id = str((result.get("item") or {}).get("id") or "")
    result_item = next((row for row in result_schedule.get("items", []) if row.get("id") == result_item_id), {})
    retryable_payment = str((result_item.get("payment_request") or {}).get("status") or "") in {
        "payment_configuration_required", "delivery_failed", "preparing_delivery",
    }
    if request.operation != "approve_quote" or (not result.get("newly_accepted") and not retryable_payment):
        return {"ok": True, **result}

    workspace_id = str(result.get("workspace_id") or "")
    schedule = result.get("schedule") or {}
    public_item = result.get("item") or {}
    item_id = str(public_item.get("id") or "")
    item = next((row for row in schedule.get("items", []) if row.get("id") == item_id), {})
    payment = dict(item.get("payment_request") or {})
    quote = item.get("quote") or {}
    profile = quote.get("document_profile") or {}
    business = profile.get("business") or {}
    customer = profile.get("customer") or {}
    method = str(payment.get("method") or "bank_transfer")
    bank = business.get("bank") or {}
    bank_ready = bool(bank.get("accountNumber") or bank.get("iban"))
    payment_links = business.get("paymentLinks") if isinstance(business.get("paymentLinks"), dict) else {}
    provider_links = {
        "stripe": str(payment_links.get("stripe") or business.get("stripePaymentLink") or business.get("stripe_payment_link") or "").strip(),
        "paypal": str(payment_links.get("paypal") or business.get("paypalPaymentLink") or business.get("paypal_payment_link") or "").strip(),
        "square": str(payment_links.get("square") or business.get("squarePaymentLink") or business.get("square_payment_link") or "").strip(),
        "gocardless": str(payment_links.get("gocardless") or business.get("gocardlessPaymentLink") or business.get("gocardless_payment_link") or "").strip(),
        "revolut": str(payment_links.get("revolut") or business.get("revolutPaymentLink") or business.get("revolut_payment_link") or "").strip(),
        "sumup": str(payment_links.get("sumup") or business.get("sumupPaymentLink") or business.get("sumup_payment_link") or "").strip(),
        "mollie": str(payment_links.get("mollie") or business.get("molliePaymentLink") or business.get("mollie_payment_link") or "").strip(),
        "braintree": str(payment_links.get("braintree") or business.get("braintreePaymentLink") or business.get("braintree_payment_link") or "").strip(),
        "worldpay": str(payment_links.get("worldpay") or business.get("worldpayPaymentLink") or business.get("worldpay_payment_link") or "").strip(),
        "adyen": str(payment_links.get("adyen") or business.get("adyenPaymentLink") or business.get("adyen_payment_link") or "").strip(),
        "checkout_com": str(payment_links.get("checkout_com") or business.get("checkoutComPaymentLink") or business.get("checkout_com_payment_link") or "").strip(),
    }
    online_methods = set(provider_links)
    provider_link = provider_links.get(method, "")
    customer_email = str(item.get("customer_email") or customer.get("email") or "").strip()
    business_email = str(business.get("email") or "").strip()
    business_name = _business_display_name(business, workspace_id)

    blocker = ""
    if "@" not in customer_email:
        blocker = "customer_email_required"
    elif method == "bank_transfer" and not bank_ready:
        blocker = "bank_details_required"
    elif method in online_methods and not provider_link:
        blocker = f"{method}_payment_link_required"
    elif method == "customer_choice" and not (bank_ready or any(provider_links.values())):
        blocker = "bank_or_online_payment_details_required"
    if blocker:
        saved = service.record_payment_delivery(
            workspace_id, item_id, status="payment_configuration_required",
            details={"delivery_error": blocker, "update_text": f"Automatic payment email paused: {blocker.replace('_', ' ')}."},
        )
        result.update({"schedule": saved, "payment_request": next(row for row in saved["items"] if row.get("id") == item_id).get("payment_request"), "payment_delivery": {"sent": False, "status": "payment_configuration_required", "reason": blocker}})
        return {"ok": True, **result}

    invoice = item.get("invoice") or result.get("invoice") or {}
    if invoice.get("number"):
        invoice_profile = dict(invoice.get("document_profile") or profile)
        invoice_business = dict(business)
        invoice_business["name"] = business_name
        invoice_profile["business"] = invoice_business
        invoice_profile["payment_method"] = method
        invoice_profile["payment_reference"] = payment.get("reference") or quote.get("number")
        invoice_profile["source_quote_number"] = quote.get("number")
        invoice_profile["payment_stage"] = payment
        refreshed = service.refresh_invoice_document(
            workspace_id, item_id, actor_id="automatic_payment_delivery", document_profile=invoice_profile,
        )
        result["schedule"] = refreshed["schedule"]
        result["invoice_document"] = refreshed["document"]
        result["invoice"] = refreshed["commercial"]
        item = next(row for row in refreshed["schedule"].get("items", []) if row.get("id") == item_id)
        invoice = item.get("invoice") or refreshed.get("commercial") or invoice

    invoice_document = result.get("invoice_document") or next(
        (row for row in reversed(item.get("documents") or []) if isinstance(row, dict) and row.get("kind") == "invoice"), None,
    )
    if not invoice_document:
        saved = service.record_payment_delivery(workspace_id, item_id, status="delivery_failed", details={"delivery_error": "invoice_document_missing", "update_text": "Automatic payment email failed because the invoice PDF was not available."})
        result.update({"schedule": saved, "payment_delivery": {"sent": False, "status": "delivery_failed", "reason": "invoice_document_missing"}})
        return {"ok": True, **result}

    try:
        invoice_data, invoice_document = service.file_bytes(workspace_id, item_id, str(invoice_document.get("id") or ""))
        currency = str(payment.get("currency") or "EUR")
        amount = str(payment.get("amount") or invoice.get("total") or "0.00")
        reference = str(payment.get("reference") or quote.get("number") or "")
        customer_name = str(item.get("customer") or customer.get("name") or "Customer")
        bank_lines = [
            value for value in (
                f"Account name: {bank.get('accountName')}" if bank.get("accountName") else "",
                f"Bank: {bank.get('bankName')}" if bank.get("bankName") else "",
                f"Sort code / routing number: {bank.get('sortCode')}" if bank.get("sortCode") else "",
                f"Account number: {bank.get('accountNumber')}" if bank.get("accountNumber") else "",
                f"IBAN: {bank.get('iban')}" if bank.get("iban") else "",
                f"BIC / SWIFT: {bank.get('bic')}" if bank.get("bic") else "",
            ) if value
        ]
        payment_lines = []
        if method in {"bank_transfer", "customer_choice"}:
            payment_lines.extend(["Pay by bank transfer:", *bank_lines, f"Payment reference: {reference}"])
        chosen_online = provider_link or next((link for link in provider_links.values() if link), "")
        provider_label = {"stripe": "Stripe", "paypal": "PayPal", "square": "Square", "gocardless": "GoCardless", "revolut": "Revolut Business", "sumup": "SumUp", "mollie": "Mollie", "braintree": "Braintree", "worldpay": "Worldpay", "adyen": "Adyen", "checkout_com": "Checkout.com"}.get(method, "online")
        if method in online_methods and chosen_online:
            payment_lines.extend(["", f"Pay securely with {provider_label}: {chosen_online}"])
        elif method == "customer_choice" and chosen_online:
            payment_lines.extend(["", f"Pay securely online: {chosen_online}"])
        body = "\n".join([
            f"Hi {customer_name},", "",
            f"Thank you for accepting quotation {quote.get('number') or ''}.",
            f"Your payment invoice {invoice.get('number') or ''} for {currency} {amount} is attached.", "",
            *payment_lines, "", "Kind regards,", business_name,
        ])
        escaped_payment = "<br>".join(html.escape(line) for line in payment_lines)
        card_button = f'<p><a href="{html.escape(chosen_online, quote=True)}" style="display:inline-block;background:#2f66e8;color:#fff;text-decoration:none;font-weight:bold;padding:14px 24px;border-radius:7px">Pay securely online</a></p>' if chosen_online and (method in online_methods or method == "customer_choice") else ""
        html_body = f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#172033;line-height:1.55"><p>Hi {html.escape(customer_name)},</p><p>Thank you for accepting quotation <strong>{html.escape(str(quote.get('number') or ''))}</strong>.</p><p>Your payment invoice <strong>{html.escape(str(invoice.get('number') or ''))}</strong> for <strong>{html.escape(currency)} {html.escape(amount)}</strong> is attached.</p><p>{escaped_payment}</p>{card_button}<p>Kind regards,<br>{html.escape(business_name)}</p></body></html>"""
        from backend.api.local_node_router import get_runtime
        runtime = get_runtime()
        health = runtime.get_gmail_connector_health()
        if str(health.get("auth_status") or "").lower() != "connected":
            raise RuntimeError("gmail_not_connected")
        delivery = runtime._send_gmail_message(
            to=customer_email,
            subject=f"Payment invoice {invoice.get('number') or ''} for accepted quotation {quote.get('number') or ''}",
            body=body, html_body=html_body,
            attachments=[{"filename": invoice_document.get("name") or "invoice.pdf", "content_type": "application/pdf", "data_base64": base64.b64encode(invoice_data).decode("ascii")}],
        )
        internal_notice = None
        internal_notice_error = ""
        if "@" in business_email and business_email.casefold() != customer_email.casefold():
            try:
                internal_notice = runtime._send_gmail_message(
                    to=business_email,
                    subject=f"Quotation {quote.get('number') or ''} accepted",
                    body=f"{customer_name} accepted quotation {quote.get('number') or ''}. Invoice {invoice.get('number') or ''} for {currency} {amount} has been sent. Payment reference: {reference}.",
                )
            except Exception as notice_error:
                # The customer delivery has already succeeded. A secondary inbox
                # notification must never incorrectly relabel it as failed.
                internal_notice_error = str(notice_error)
        awaiting_status = "awaiting_bank_payment" if method == "bank_transfer" else "awaiting_card_payment" if method in online_methods else "awaiting_customer_payment"
        saved = service.record_payment_delivery(
            workspace_id, item_id, status=awaiting_status,
            details={"gmail_message_id": delivery.get("message_id"), "recipient": customer_email, "business_notification_sent": bool(internal_notice and internal_notice.get("sent")), "business_notification_error": internal_notice_error, "update_text": f"Payment invoice {invoice.get('number') or ''} sent automatically to {customer_email}; awaiting payment."},
        )
        result.update({"schedule": saved, "payment_request": next(row for row in saved["items"] if row.get("id") == item_id).get("payment_request"), "payment_delivery": {"sent": True, "status": awaiting_status, "recipient": customer_email, "message_id": delivery.get("message_id")}})
    except Exception as error:
        saved = service.record_payment_delivery(
            workspace_id, item_id, status="delivery_failed",
            details={"delivery_error": str(error), "update_text": f"Automatic payment email failed: {error}."},
        )
        result.update({"schedule": saved, "payment_request": next(row for row in saved["items"] if row.get("id") == item_id).get("payment_request"), "payment_delivery": {"sent": False, "status": "delivery_failed", "reason": str(error)}})
    return {"ok": True, **result}


@router.post("/{workspace_id}/items/{item_id}/retry-payment-delivery")
def retry_payment_delivery(
    workspace_id: str, item_id: str, request: PaymentDeliveryRetryRequest,
) -> dict[str, Any]:
    """Retry an accepted quote's invoice after the business fixes payment setup."""
    key = _workspace(workspace_id)
    token_match = re.search(r"/portal/([^/]+)/accept(?:[?#].*)?$", request.acceptance_url)
    if not token_match:
        raise HTTPException(status_code=422, detail="The quotation acceptance link is unavailable")
    service = WorkScheduleService()
    schedule = service.get(key)
    item = next((row for row in schedule.get("items", []) if row.get("id") == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="work_item_not_found")
    if str((item.get("quote") or {}).get("status") or "") != "customer_approved":
        raise HTTPException(status_code=409, detail="The quotation has not been accepted")
    quote = dict(item.get("quote") or {})
    profile = dict(quote.get("document_profile") or {})
    existing_business = dict(profile.get("business") or {})
    supplied_business = dict(request.business or {})
    for field in ("name", "email", "currency", "stripePaymentLink", "stripe_payment_link"):
        if supplied_business.get(field):
            existing_business[field] = supplied_business[field]
    if isinstance(supplied_business.get("bank"), dict):
        existing_business["bank"] = dict(supplied_business["bank"])
    profile["business"] = existing_business
    profile["payment_method"] = request.payment_method
    quote["document_profile"] = profile
    quote["payment_method"] = request.payment_method
    item["quote"] = quote
    payment_request = dict(item.get("payment_request") or {})
    payment_request["method"] = request.payment_method
    if existing_business.get("currency"):
        payment_request["currency"] = existing_business["currency"]
    item["payment_request"] = payment_request
    schedule = service.save(key, schedule, expected_revision=schedule["revision"], changed_by=request.actor_id)
    return customer_portal_action(
        token_match.group(1), PortalActionRequest(operation="approve_quote", fields={}),
    )


@router.get("/portal/{token}/accept", response_class=HTMLResponse)
def customer_quote_acceptance_page(token: str) -> HTMLResponse:
    """Show a minimal confirmation page; never accept a quote from a GET request.

    Mail security scanners routinely follow links, so the customer must press the
    confirmation button before Tessaris records contractual acceptance.
    """
    try:
        payload = WorkScheduleService().portal_view(token)
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    item = payload.get("item") or {}
    quote = item.get("quote") or {}
    profile = quote.get("document_profile") or {}
    business = profile.get("business") or {}
    business_name = _business_display_name(business, str(payload.get("workspace_id") or ""))
    currency = str(business.get("currency") or "EUR")
    safe_token = json.dumps(token)
    already_accepted = json.dumps(str(quote.get("status") or "") == "customer_approved")
    initial_delivery = json.dumps(str((item.get("payment_request") or {}).get("status") or ""))
    return HTMLResponse(f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Accept quotation</title><style>
body{{margin:0;background:#f3f6fb;color:#172033;font:16px system-ui}}main{{max-width:620px;margin:48px auto;padding:0 18px}}article{{background:#fff;border:1px solid #d7e0ee;border-top:6px solid #2f66e8;padding:30px}}small{{color:#2f66e8;font-weight:800;letter-spacing:.14em}}h1{{margin:8px 0}}.summary{{margin:24px 0;padding:18px;background:#f6f8fc;display:flex;justify-content:space-between;gap:16px}}button{{width:100%;border:0;border-radius:7px;padding:15px;background:#2f66e8;color:#fff;font:inherit;font-weight:800;cursor:pointer}}button:disabled{{opacity:.65;cursor:wait}}#message{{font-weight:700;color:#a52a21}}#confirmation{{text-align:center;padding:18px 0 4px}}#confirmation .check{{display:grid;place-items:center;width:64px;height:64px;margin:0 auto 18px;border-radius:50%;background:#e8f7ee;color:#17643a;font-size:34px;font-weight:900}}#confirmation h2{{margin:0 0 16px;color:#17643a;font-size:27px}}#confirmation p{{line-height:1.55;margin:10px 0}}#confirmation .close-note{{margin-top:22px;padding:14px;background:#f6f8fc;color:#52647d;font-weight:700}}@media(max-width:520px){{main{{margin:18px auto}}article{{padding:22px}}.summary{{display:block}}}}
</style></head><body><main><article><small>{html.escape(business_name)}</small><div id="acceptance-form"><h1>Accept quotation</h1><p>Please confirm that you accept quotation <strong>{html.escape(str(quote.get('number') or ''))}</strong>, including its Terms &amp; Conditions and payment schedule.</p><div class="summary"><strong>{html.escape(str(item.get('title') or 'Quotation'))}</strong><strong>{html.escape(currency)} {html.escape(str(quote.get('total') or quote.get('amount') or '0.00'))}</strong></div><button id="accept" type="button">Accept quotation</button><p id="message" role="alert"></p></div><div id="confirmation" hidden><div class="check">✓</div><h2>Quotation accepted</h2><p>Your acceptance has been sent to <strong>{html.escape(business_name)}</strong>.</p><p id="payment-confirmation">We will send your invoice and payment details shortly, followed by confirmation of your appointment or schedule of works.</p><p class="close-note">You can now close this window.</p></div></article></main><script>
const token={safe_token},button=document.getElementById('accept'),message=document.getElementById('message'),form=document.getElementById('acceptance-form'),confirmation=document.getElementById('confirmation'),paymentConfirmation=document.getElementById('payment-confirmation');function showAccepted(delivery=''){{form.hidden=true;confirmation.hidden=false;document.title='Quotation accepted';if(['awaiting_bank_payment','awaiting_card_payment','awaiting_customer_payment'].includes(delivery))paymentConfirmation.textContent='Your payment invoice has been emailed to you. Once payment is confirmed, we will confirm your appointment or schedule of works.';else paymentConfirmation.textContent='We will send your invoice and payment details shortly, followed by confirmation of your appointment or schedule of works.';}}if({already_accepted})showAccepted({initial_delivery});button.addEventListener('click',async()=>{{button.disabled=true;button.textContent='Recording acceptance and preparing payment…';message.textContent='';try{{const response=await fetch(`/api/aion/business/work-schedule/portal/${{encodeURIComponent(token)}}/actions`,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{operation:'approve_quote',fields:{{}}}})}});const result=await response.json();if(!response.ok)throw new Error(result.detail||'Acceptance could not be recorded');showAccepted(result.payment_delivery?.status||result.payment_request?.status||'');}}catch(error){{message.textContent=error.message;button.disabled=false;button.textContent='Accept quotation';}}}});
</script></body></html>""")


@router.get("/portal/{token}/page", response_class=HTMLResponse)
def customer_portal_page(token: str) -> HTMLResponse:
    try:
        payload = WorkScheduleService().portal_view(token)
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    data = json.dumps(payload.get("item") or {}).replace("</", "<\\/")
    safe_token = json.dumps(token)
    page = f"""<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Your booking</title><style>
body{{margin:0;background:#f4f8fb;color:#102a43;font:16px system-ui}}main{{max-width:720px;margin:40px auto;padding:0 18px}}header,section{{background:#fff;border:1px solid #ccd8e4;padding:24px;margin-bottom:14px}}header{{border-top:5px solid #0f766e}}small{{color:#0f766e;font-weight:800;letter-spacing:.14em}}h1{{margin:8px 0}}dl{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}dl div{{background:#f7fafc;padding:12px}}dt{{font-size:11px;color:#64748b}}dd{{margin:4px 0 0;font-weight:700}}button,input,textarea{{font:inherit;padding:11px;border:1px solid #9eb0bf}}button{{font-weight:800;background:#fff;cursor:pointer}}button.primary{{background:#0f766e;color:#fff;border-color:#0f766e}}form{{display:grid;gap:10px}}.actions{{display:flex;flex-wrap:wrap;gap:8px}}#message{{color:#0f766e;font-weight:700}}@media(max-width:520px){{dl{{grid-template-columns:1fr}}main{{margin:14px auto}}}}
</style></head><body><main><header><small>CUSTOMER PORTAL</small><h1 id=\"title\"></h1><p id=\"customer\"></p></header><section><dl><div><dt>Status</dt><dd id=\"status\"></dd></div><div><dt>Date and time</dt><dd id=\"date\"></dd></div><div><dt>Assigned to</dt><dd id=\"assignee\"></dd></div><div><dt>Location</dt><dd id=\"location\"></dd></div></dl></section><section><h2>Quotation</h2><p id=\"quote\"></p><div id=\"payment\"></div><p id=\"payment-method\"></p><p><strong>Payment reference:</strong> <span id=\"reference\"></span></p><p>By accepting, you confirm the quotation and its included Terms &amp; Conditions.</p><div class=\"actions\"><button class=\"primary\" data-action=\"approve_quote\">Accept quotation &amp; T&amp;Cs</button><button data-action=\"decline_quote\">Decline quotation</button></div></section><section><h2>Need to change the booking?</h2><form id=\"change\"><input name=\"date\" type=\"date\"><input name=\"time\" type=\"time\"><textarea name=\"note\" placeholder=\"Tell us what you need\"></textarea><div class=\"actions\"><button class=\"primary\" type=\"submit\">Request another time</button><button type=\"button\" data-action=\"request_cancellation\">Request cancellation</button></div></form><p id=\"message\"></p></section></main><script>
const item={data},token={safe_token};const text=(id,value)=>document.getElementById(id).textContent=value||'Not recorded';text('title',item.title);text('customer',item.customer);text('status',String(item.status||'').replaceAll('_',' '));text('date',[item.date,item.time].filter(Boolean).join(' · '));text('assignee',item.assignee);text('location',item.location);const profile=item.quote?.document_profile||{{}};const currency=profile.business?.currency||'EUR';text('quote',item.quote?.number?`${{item.quote.number}} · ${{currency}} ${{item.quote.total||item.quote.amount||'0.00'}} · ${{String(item.quote.status||'draft').replaceAll('_',' ')}}`:'No quote is ready yet.');text('reference',profile.payment_reference||item.quote?.number||'Shown on the numbered quote');const method=item.quote?.payment_method||profile.payment_method||'bank_transfer',bank=profile.business?.bank||{{}},providerNames={{stripe:'Stripe',paypal:'PayPal',square:'Square',gocardless:'GoCardless'}};text('payment-method',method==='bank_transfer'?[bank.accountName&&`Account: ${{bank.accountName}}`,bank.bankName,bank.sortCode&&`Sort / routing: ${{bank.sortCode}}`,bank.accountNumber&&`Account no: ${{bank.accountNumber}}`,bank.iban&&`IBAN: ${{bank.iban}}`,bank.bic&&`BIC / SWIFT: ${{bank.bic}}`].filter(Boolean).join(' · ')||'Bank details will be supplied before payment is due.':providerNames[method]?`A secure ${{providerNames[method]}} payment link will be supplied with the payment request.`:'Pay by bank transfer or the secure online link supplied with the payment request.');const stages=item.quote?.payment_schedule||profile.payment_schedule||[];const payment=document.getElementById('payment');if(stages.length){{const heading=document.createElement('h3');heading.textContent='Payment schedule';payment.append(heading);stages.forEach(stage=>{{const row=document.createElement('p'),name=document.createElement('strong');name.textContent=stage.label||'Payment';const due=stage.due_type==='acceptance'?'When accepted':stage.due_type==='completion'?'On completion':stage.due_type==='days'?`${{stage.due_value||0}} days after acceptance`:stage.due_value||'Date to be agreed';row.append(name,document.createTextNode(` · ${{currency}} ${{Number(stage.calculated_amount||0).toFixed(2)}} · ${{due}}`));payment.append(row);}});}}async function act(operation,fields={{}}){{const response=await fetch(`/api/aion/business/work-schedule/portal/${{encodeURIComponent(token)}}/actions`,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{operation,fields}})}});const result=await response.json();if(!response.ok)throw new Error(result.detail||'Request failed');const delivery=result.payment_delivery?.status||result.payment_request?.status||'';const acceptedMessage=['awaiting_bank_payment','awaiting_card_payment','awaiting_customer_payment'].includes(delivery)?'Quotation accepted. Your payment invoice has been emailed to you.':delivery==='payment_configuration_required'?'Quotation accepted. The business has been notified and will send your payment details shortly.':'Quotation accepted. Your invoice and payment details are being prepared.';text('message',operation==='approve_quote'?acceptedMessage:'Your request has been recorded. The business can now review it.');}}document.addEventListener('click',event=>{{const button=event.target.closest('[data-action]');if(button)act(button.dataset.action).catch(error=>text('message',error.message));}});document.getElementById('change').addEventListener('submit',event=>{{event.preventDefault();act('request_reschedule',Object.fromEntries(new FormData(event.target))).catch(error=>text('message',error.message));}});
</script></body></html>"""
    page = page.replace(
        "providerNames={stripe:'Stripe',paypal:'PayPal',square:'Square',gocardless:'GoCardless'}",
        "providerNames={stripe:'Stripe',paypal:'PayPal',square:'Square',gocardless:'GoCardless',revolut:'Revolut Business',sumup:'SumUp',mollie:'Mollie',braintree:'Braintree',worldpay:'Worldpay',adyen:'Adyen',checkout_com:'Checkout.com'}",
    )
    return HTMLResponse(page)


# A website can post a booking request without gaining access to the schedule.
# A deployment should place its usual CSRF/rate-limit layer in front of this route.
@router.post("/public/{workspace_id}/booking")
def public_booking(
    workspace_id: str,
    request: IntakeRequest,
    x_tessaris_intake_key: str = Header(default=""),
    x_forwarded_for: str = Header(default=""),
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    fields = dict(request.fields)
    if request.sales_endpoint_id:
        if not x_tessaris_intake_key:
            raise HTTPException(status_code=403, detail="website_intake_token_required")
        event_id = str(fields.get("event_id") or fields.get("idempotency_key") or "").strip()
        if not event_id:
            raise HTTPException(status_code=409, detail="website_intake_idempotency_key_required")
        sales_payload = {
            **fields,
            "event_id": event_id,
            "name": fields.get("customer") or fields.get("name"),
            "email": fields.get("customer_email") or fields.get("email"),
            "phone": fields.get("customer_phone") or fields.get("phone"),
            "address": fields.get("customer_address") or fields.get("address"),
            "enquiry": fields.get("message") or fields.get("enquiry") or fields.get("title"),
        }
        try:
            sales_result = SalesRevenueService().ingest_website_enquiry(
                key,
                request.sales_endpoint_id,
                token=x_tessaris_intake_key,
                payload=sales_payload,
                remote_reference=x_forwarded_for,
            )
        except PermissionError as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        contact = dict(sales_result.get("contact") or {})
        opportunity = dict(sales_result.get("opportunity") or {})
        fields.update({
            "customer_id": contact.get("contact_id") or fields.get("customer_id"),
            "customer": contact.get("name") or fields.get("customer") or fields.get("name"),
            "customer_email": contact.get("email") or fields.get("customer_email") or fields.get("email"),
            "customer_phone": contact.get("phone") or fields.get("customer_phone") or fields.get("phone"),
            "customer_address": contact.get("address") or fields.get("customer_address") or fields.get("address"),
            "sales_opportunity_id": opportunity.get("opportunity_id"),
            "source_reference": opportunity.get("source_reference"),
        })
    model = WorkScheduleService().create_intake(key, fields, channel=request.channel or "website")
    created = model.get("intake", [])[-1]
    return {
        "ok": True,
        "booking_reference": created.get("id"),
        "state": created.get("state"),
        "customer_id": created.get("customer_id"),
        "sales_opportunity_id": created.get("sales_opportunity_id"),
    }
