"""Governed lead-to-revenue completion layer for Tessaris Sales.

This service closes the commercial loop after canonical lead intake: availability,
bookings, quotations, Operations/Finance handoffs, controlled communications,
campaign audiences, outcomes and evidence-based playbook experiments. External
messages and provider writes remain separate, exact-payload actions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService
from backend.modules.aion_business.runtime.telephony_credentials import (
    get_retell_agent_id,
    get_retell_api_key,
    get_retell_from_number,
)
from backend.modules.aion_business.runtime.twilio_credentials import (
    get_twilio_credential_readiness,
    get_twilio_account_sid,
    get_twilio_api_secret,
    get_twilio_api_username,
    get_twilio_caller_id,
    get_twilio_carrier_number,
    get_twilio_from_number,
    get_twilio_trunk,
)


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _money(value: Any) -> float:
    return round(float(value or 0), 2)


class SalesCompletionService:
    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = OrganizationAuthorityService(self.repository)
        self.sales = SalesRevenueService(self.repository, self.authority)
        self.finance = FinanceSalesService(self.repository, self.authority)

    def workspace(self, workspace_id: str) -> dict[str, Any]:
        bookings = self._list(workspace_id, "bookings", "booking_hash")
        quotes = self._list(workspace_id, "quotes", "quote_hash")
        handoffs = self._list(workspace_id, "handoffs", "handoff_hash")
        messages = self._list(workspace_id, "messages", "message_hash")
        campaigns = self._list(workspace_id, "campaigns", "campaign_hash")
        outcomes = self._list(workspace_id, "outcomes", "outcome_hash")
        experiments = self._list(workspace_id, "experiments", "experiment_hash")
        return {
            "schema_version": "aion.sales.completion_workspace.v1",
            "workspace_id": workspace_id,
            "availability": self.get_availability(workspace_id),
            "bookings": bookings, "quotes": quotes, "handoffs": handoffs,
            "messages": messages, "campaigns": campaigns, "outcomes": outcomes,
            "experiments": experiments,
            "summary": {
                "confirmed_bookings": sum(x.get("status") in {"confirmed_internal", "calendar_event_created"} for x in bookings),
                "quotes_awaiting_approval": sum(x.get("status") == "exact_approval_required" for x in quotes),
                "accepted_quotes": sum(x.get("status") == "accepted_by_customer" for x in quotes),
                "operations_handoffs": sum(x.get("destination") == "operations" for x in handoffs),
                "finance_handoffs": sum(x.get("destination") == "finance" for x in handoffs),
                "messages_awaiting_approval": sum(x.get("status") == "exact_approval_required" for x in messages),
                "campaigns_ready": sum(x.get("status") == "preflight_passed" for x in campaigns),
                "won_value": round(sum(_money(x.get("value")) for x in outcomes if x.get("disposition") == "won"), 2),
            },
            "external_readiness": self.external_readiness(workspace_id),
            "governance": {
                "canonical_crm": "tessaris", "exact_payload_approval": True,
                "quote_acceptance_requires_customer_evidence": True,
                "campaign_contacts_require_permission": True,
                "playbook_promotion_requires_outcomes": True,
            },
        }

    def list_bookings(self, workspace_id: str) -> list[dict[str, Any]]:
        """Return integrity-checked bookings without probing external providers."""
        return self._list(workspace_id, "bookings", "booking_hash")

    def list_handoffs(self, workspace_id: str) -> list[dict[str, Any]]:
        """Return integrity-checked delivery handoffs without readiness side effects."""
        return self._list(workspace_id, "handoffs", "handoff_hash")

    def set_availability(self, workspace_id: str, *, person_id: str, timezone: str,
                         weekly_hours: dict[str, list[list[str]]], buffer_minutes: int,
                         changed_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, changed_by_person_id, "sales.manage")
        if not timezone or buffer_minutes < 0 or buffer_minutes > 180:
            raise ValueError("invalid_sales_availability")
        allowed_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        clean: dict[str, list[list[str]]] = {}
        for day, ranges in (weekly_hours or {}).items():
            if day.lower() not in allowed_days:
                raise ValueError("invalid_availability_day")
            clean[day.lower()] = []
            for start, end in ranges:
                if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end) or start >= end:
                    raise ValueError("invalid_availability_range")
                clean[day.lower()].append([start, end])
        record = {"schema_version": "aion.sales.availability.v1", "workspace_id": workspace_id,
                  "person_id": person_id, "timezone": timezone, "weekly_hours": clean,
                  "buffer_minutes": int(buffer_minutes), "updated_at": _now(),
                  "changed_by_person_id": changed_by_person_id}
        self._rehash(record, "availability_hash")
        self._write(self._root(workspace_id) / "availability.json", record)
        return record

    def get_availability(self, workspace_id: str) -> dict[str, Any]:
        path = self._root(workspace_id) / "availability.json"
        if path.exists():
            return self._load(path, workspace_id, "availability_hash")
        return {"workspace_id": workspace_id, "status": "configuration_required", "weekly_hours": {}}

    def prepare_booking(self, workspace_id: str, opportunity_id: str, *, starts_at: str,
                        duration_minutes: int, assigned_person_id: str, channel: str,
                        prepared_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, prepared_by_person_id, "sales.manage")
        opportunity = self.sales.load_opportunity(workspace_id, opportunity_id)
        start = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
        if start.tzinfo is None or start <= datetime.now(UTC):
            raise ValueError("future_timezone_aware_booking_required")
        if duration_minutes < 10 or duration_minutes > 480:
            raise ValueError("invalid_booking_duration")
        end = start + timedelta(minutes=duration_minutes)
        for row in self._list(workspace_id, "bookings", "booking_hash"):
            if row.get("assigned_person_id") != assigned_person_id or row.get("status") != "confirmed_internal":
                continue
            existing_start = datetime.fromisoformat(row["starts_at"])
            existing_end = datetime.fromisoformat(row["ends_at"])
            if start < existing_end and end > existing_start:
                raise ValueError("sales_booking_conflict")
        booking = {"schema_version": "aion.sales.booking.v1", "booking_id": "booking-" + secrets.token_hex(8),
                   "workspace_id": workspace_id, "opportunity_id": opportunity_id,
                   "customer": opportunity.get("contact"), "starts_at": start.isoformat(), "ends_at": end.isoformat(),
                   "duration_minutes": duration_minutes, "assigned_person_id": assigned_person_id,
                   "channel": str(channel or "Phone"), "status": "exact_approval_required",
                   "prepared_at": _now(), "prepared_by_person_id": prepared_by_person_id,
                   "authority_decision": access, "external_calendar_write": False,
                   "customer_notification_sent": False}
        self._rehash(booking, "booking_hash"); self._save(workspace_id, "bookings", booking["booking_id"], booking)
        return booking

    def approve_booking(self, workspace_id: str, booking_id: str, *, expected_booking_hash: str,
                        approved_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, approved_by_person_id, "sales.approve_communication")
        booking = self._get(workspace_id, "bookings", booking_id, "booking_hash")
        self._exact(booking, "booking_hash", expected_booking_hash, "sales_booking_changed_since_review")
        booking.update({"status": "confirmed_internal", "approved_at": _now(),
                        "approved_by_person_id": approved_by_person_id, "approval_authority": access})
        self._rehash(booking, "booking_hash"); self._save(workspace_id, "bookings", booking_id, booking)
        opportunity = self.sales.load_opportunity(workspace_id, booking["opportunity_id"])
        if opportunity.get("stage") in {"qualified", "appointment_proposed", "human_handoff"}:
            self.sales.update_stage(workspace_id, booking["opportunity_id"], stage="appointment_booked",
                                    reason="Exact internal booking approved", changed_by_person_id=approved_by_person_id)
        return booking

    def execute_booking(self, workspace_id: str, booking_id: str, *, expected_booking_hash: str,
                        executed_by_person_id: str) -> dict[str, Any]:
        """Create an exact-approved internal booking in Google Calendar without notifying guests."""
        access = self._require(workspace_id, executed_by_person_id, "sales.approve_communication")
        booking = self._get(workspace_id, "bookings", booking_id, "booking_hash")
        self._exact(booking, "booking_hash", expected_booking_hash,
                    "sales_booking_changed_since_review")
        if booking.get("status") != "confirmed_internal":
            raise PermissionError("confirmed_internal_booking_required")
        try:
            from backend.api.local_node_router import get_runtime
            runtime = get_runtime()
            health = runtime.get_gmail_connector_health()
            if health.get("auth_status") != "connected":
                raise PermissionError("google_workspace_reauthorization_required")
            contact = booking.get("customer") or {}
            result = runtime._create_google_calendar_event(
                summary=f"Home Fixed enquiry · {contact.get('name') or 'Customer'}",
                description=(f"Tessaris Sales booking {booking_id}. Customer notification is handled "
                             "separately through an approved communication."),
                starts_at=str(booking.get("starts_at") or ""),
                ends_at=str(booking.get("ends_at") or ""),
                location=str(booking.get("channel") or ""),
            )
        except PermissionError:
            raise
        except Exception as exc:
            raise ValueError(f"google_calendar_event_creation_failed:{exc}") from exc
        if not result.get("created") or result.get("attendees_notified"):
            raise ValueError("google_calendar_result_not_safe")
        booking.update({
            "status": "calendar_event_created",
            "executed_at": _now(), "executed_by_person_id": executed_by_person_id,
            "execution_authority": access, "external_calendar_write": True,
            "customer_notification_sent": False,
            "provider_result": {"provider": "google_calendar", "event_id": result.get("event_id"),
                                "html_link": result.get("html_link"),
                                "attendees_notified": False},
        })
        self._rehash(booking, "booking_hash")
        self._save(workspace_id, "bookings", booking_id, booking)
        return booking

    def prepare_quote(self, workspace_id: str, opportunity_id: str, *, lines: list[dict[str, Any]],
                      valid_days: int, terms: str, prepared_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, prepared_by_person_id, "sales.manage")
        opportunity = self.sales.load_opportunity(workspace_id, opportunity_id)
        if not lines or valid_days < 1 or valid_days > 180:
            raise ValueError("valid_quote_lines_and_expiry_required")
        clean, subtotal, tax_total = [], 0.0, 0.0
        for index, line in enumerate(lines[:100], 1):
            quantity = _money(line.get("quantity") or 1); unit = _money(line.get("unit_amount")); rate = _money(line.get("tax_rate"))
            description = str(line.get("description") or "").strip()
            if not description or quantity <= 0 or unit < 0 or rate < 0:
                raise ValueError(f"invalid_quote_line:{index}")
            net = round(quantity * unit, 2); tax = round(net * rate / 100, 2)
            clean.append({"line_id": f"line-{index}", "description": description, "quantity": quantity,
                          "unit_amount": unit, "tax_rate": rate, "net_amount": net, "tax_amount": tax,
                          "offering_id": line.get("offering_id")})
            subtotal += net; tax_total += tax
        prepared = datetime.now(UTC).date(); total = round(subtotal + tax_total, 2)
        quote = {"schema_version": "aion.sales.quote.v1", "quote_id": "quote-" + secrets.token_hex(8),
                 "workspace_id": workspace_id, "opportunity_id": opportunity_id,
                 "customer": opportunity.get("contact"), "currency": "EUR", "lines": clean,
                 "subtotal": round(subtotal, 2), "tax_total": round(tax_total, 2), "total": total,
                 "terms": str(terms or "").strip(), "prepared_date": prepared.isoformat(),
                 "valid_until": (prepared + timedelta(days=valid_days)).isoformat(),
                 "status": "exact_approval_required", "prepared_at": _now(),
                 "prepared_by_person_id": prepared_by_person_id, "authority_decision": access,
                 "customer_acceptance": None, "external_message_sent": False}
        self._rehash(quote, "quote_hash"); self._save(workspace_id, "quotes", quote["quote_id"], quote)
        return quote

    def approve_quote(self, workspace_id: str, quote_id: str, *, expected_quote_hash: str,
                      approved_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, approved_by_person_id, "sales.approve_communication")
        quote = self._get(workspace_id, "quotes", quote_id, "quote_hash")
        self._exact(quote, "quote_hash", expected_quote_hash, "sales_quote_changed_since_review")
        quote.update({"status": "approved_not_sent", "approved_at": _now(),
                      "approved_by_person_id": approved_by_person_id, "approval_authority": access})
        self._rehash(quote, "quote_hash"); self._save(workspace_id, "quotes", quote_id, quote)
        opportunity = self.sales.load_opportunity(workspace_id, quote["opportunity_id"])
        if opportunity.get("stage") in {"qualified", "appointment_booked", "human_handoff"}:
            self.sales.update_stage(workspace_id, quote["opportunity_id"], stage="proposal",
                                    reason="Exact quote approved", changed_by_person_id=approved_by_person_id)
        return quote

    def record_quote_acceptance(self, workspace_id: str, quote_id: str, *, evidence_reference: str,
                                recorded_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, recorded_by_person_id, "sales.manage")
        quote = self._get(workspace_id, "quotes", quote_id, "quote_hash")
        if quote.get("status") != "approved_not_sent" or not str(evidence_reference or "").strip():
            raise PermissionError("approved_quote_and_customer_acceptance_evidence_required")
        quote.update({"status": "accepted_by_customer", "customer_acceptance": {
            "evidence_reference": str(evidence_reference).strip(), "recorded_at": _now(),
            "recorded_by_person_id": recorded_by_person_id}})
        self._rehash(quote, "quote_hash"); self._save(workspace_id, "quotes", quote_id, quote)
        self.sales.update_stage(workspace_id, quote["opportunity_id"], stage="won",
                                reason="Customer acceptance evidence recorded", changed_by_person_id=recorded_by_person_id)
        return quote

    def create_handoffs(self, workspace_id: str, quote_id: str, *, operations_owner_person_id: str,
                        created_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, created_by_person_id, "sales.manage")
        quote = self._get(workspace_id, "quotes", quote_id, "quote_hash")
        if quote.get("status") != "accepted_by_customer":
            raise PermissionError("accepted_quote_required_for_delivery_handoff")
        opportunity = self.sales.load_opportunity(workspace_id, quote["opportunity_id"])
        operations = {"schema_version": "aion.sales.handoff.v1", "handoff_id": "operations-" + quote_id,
                      "workspace_id": workspace_id, "destination": "operations", "quote_id": quote_id,
                      "opportunity_id": quote["opportunity_id"], "customer": quote.get("customer"),
                      "scope": quote.get("lines"), "value": quote.get("total"), "currency": quote.get("currency"),
                      "assigned_person_id": operations_owner_person_id, "status": "ready_for_delivery_planning",
                      "created_at": _now(), "created_by_person_id": created_by_person_id}
        self._rehash(operations, "handoff_hash"); self._save(workspace_id, "handoffs", operations["handoff_id"], operations)
        contact = opportunity.get("contact") or {}
        customer = self.finance.create_customer(workspace_id, name=contact.get("name") or "Customer",
                    email=contact.get("email"), created_by_person_id=created_by_person_id)
        invoice = self.finance.prepare_invoice(workspace_id, customer_id=customer["customer_id"],
                    issue_date=datetime.now(UTC).date().isoformat(), due_date=None, currency=quote.get("currency"),
                    reference=quote_id, lines=[{"description": x["description"], "quantity": x["quantity"],
                    "unit_amount": x["unit_amount"], "tax_rate": x["tax_rate"], "account_code": "200",
                    "account_name": "Sales"} for x in quote["lines"]], prepared_by_person_id=created_by_person_id)
        finance = {"schema_version": "aion.sales.handoff.v1", "handoff_id": "finance-" + quote_id,
                   "workspace_id": workspace_id, "destination": "finance", "quote_id": quote_id,
                   "opportunity_id": quote["opportunity_id"], "customer_id": customer["customer_id"],
                   "invoice_id": invoice["invoice_id"], "status": "invoice_exact_approval_required",
                   "created_at": _now(), "created_by_person_id": created_by_person_id}
        self._rehash(finance, "handoff_hash"); self._save(workspace_id, "handoffs", finance["handoff_id"], finance)
        return {"operations": operations, "finance": finance, "invoice": invoice}

    def prepare_message(self, workspace_id: str, opportunity_id: str, *, channel: str, purpose: str,
                        subject: str | None, body: str, prepared_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, prepared_by_person_id, "sales.manage")
        opportunity = self.sales.load_opportunity(workspace_id, opportunity_id); contact = opportunity.get("contact") or {}
        if channel not in {"email", "sms"} or not str(body or "").strip():
            raise ValueError("valid_sales_message_required")
        destination = contact.get("email") if channel == "email" else contact.get("phone")
        if not destination:
            raise ValueError(f"customer_{channel}_required")
        permission = (opportunity.get("consent") or {}).get("contact_permission")
        if permission not in {"inbound_response", "explicit_outbound", "agent_authorized_response"}:
            raise PermissionError("customer_contact_permission_required")
        payload = {"channel": channel, "to": destination, "subject": str(subject or "").strip() or None,
                   "body": str(body).strip(), "purpose": str(purpose or "follow_up").strip()}
        message = {"schema_version": "aion.sales.message.v1", "message_id": "message-" + secrets.token_hex(8),
                   "workspace_id": workspace_id, "opportunity_id": opportunity_id, "payload": payload,
                   "payload_hash": canonical_contract_hash(payload), "status": "exact_approval_required",
                   "prepared_at": _now(), "prepared_by_person_id": prepared_by_person_id,
                   "authority_decision": access, "external_message_sent": False}
        self._rehash(message, "message_hash"); self._save(workspace_id, "messages", message["message_id"], message)
        return message

    def prepare_post_call_confirmation(self, workspace_id: str, opportunity_id: str, *,
                                       call_draft_id: str, provider_call_id: str,
                                       captured_fields: dict[str, Any],
                                       missing_fields: list[str] | None,
                                       channel: str,
                                       prepared_by_person_id: str) -> dict[str, Any]:
        """Create a deterministic confirmation draft from an approved call contract.

        The template deliberately does not ask a voice model to compose operational
        instructions. It names only the route frozen into the approved call draft,
        and the existing message approval gate remains in force.
        """
        self._require(workspace_id, prepared_by_person_id, "sales.manage")
        opportunity = self.sales.load_opportunity(workspace_id, opportunity_id)
        draft = next((row for row in self.sales.list_call_drafts(workspace_id)
                      if row.get("draft_id") == call_draft_id), None)
        if not draft or draft.get("opportunity_id") != opportunity_id:
            raise FileNotFoundError(call_draft_id)
        contract = draft.get("call_goal_contract") or {}
        route = contract.get("evidence_route") or {}
        clean = {str(key): str(value or "").strip()[:240]
                 for key, value in (captured_fields or {}).items() if str(value or "").strip()}
        missing = [str(value) for value in (missing_fields or [])
                   if str(value) in set(contract.get("required_fields") or [])]
        name = str((opportunity.get("contact") or {}).get("name") or "there").split(" ", 1)[0]
        facts = []
        labels = {"work_required": "Work", "property_location": "Location",
                  "full_property_address": "Address", "urgency": "Timing",
                  "preferred_follow_up_time": "Preferred contact time"}
        for key in ("work_required", "property_location", "full_property_address", "urgency",
                    "preferred_follow_up_time"):
            if clean.get(key): facts.append(f"{labels[key]}: {clean[key]}")
        lines = [f"Thanks for speaking with AION, {name}."]
        if facts:
            lines.extend(["Please check these details:", *[f"- {value}" for value in facts]])
        if contract.get("written_contact_confirmation"):
            lines.append("Please reply with any correction and, if we do not already have it, your correctly spelled email address.")
        mode, destination = route.get("mode"), route.get("destination")
        if mode == "reply_to_approved_sms":
            lines.append("You may reply to this approved message with your photos or documents.")
        elif mode == "approved_email_address" and destination:
            lines.append(f"Please send photos or documents to {destination}.")
        else:
            lines.append("A person from the business will confirm the approved route for photos or documents.")
        if missing:
            lines.append("Still needed for review: " + ", ".join(value.replace("_", " ") for value in missing) + ".")
        lines.append("A person will review the enquiry. No price, appointment or work is confirmed by this message.")
        message = self.prepare_message(
            workspace_id, opportunity_id, channel=channel,
            purpose="post_call_fact_confirmation", subject="Please confirm your enquiry",
            body="\n".join(lines), prepared_by_person_id=prepared_by_person_id)
        message.update({"template": "deterministic_post_call_confirmation_v1",
                        "call_draft_id": call_draft_id,
                        "provider_call_id": str(provider_call_id or "").strip() or None,
                        "call_goal_contract_hash": draft.get("call_goal_contract_hash"),
                        "captured_fields": clean, "missing_fields": missing})
        self._rehash(message, "message_hash")
        self._save(workspace_id, "messages", message["message_id"], message)
        return message

    def prepare_contact_fallback(self, workspace_id: str, opportunity_id: str, *,
                                 call_draft_id: str, provider_call_id: str,
                                 provider_status: str, disconnection_reason: str | None,
                                 prepared_by_person_id: str) -> dict[str, Any]:
        """Plan the next bounded contact step after an unanswered call.

        The same frozen goal contract follows the customer across channels.
        This method can prepare a retry or an email/SMS draft, but never sends,
        books or changes a calendar automatically.
        """
        access = self._require(workspace_id, prepared_by_person_id, "sales.manage")
        opportunity = self.sales.load_opportunity(workspace_id, opportunity_id)
        draft = next((row for row in self.sales.list_call_drafts(workspace_id)
                      if row.get("draft_id") == call_draft_id), None)
        if not draft or draft.get("opportunity_id") != opportunity_id:
            raise FileNotFoundError(call_draft_id)
        if str(provider_status) not in {"not_connected", "ended", "error"}:
            raise ValueError("terminal_call_outcome_required_for_fallback")
        sequence = draft.get("contact_sequence") or {}
        attempt = int(draft.get("attempt_number") or 1)
        maximum = int(sequence.get("maximum_phone_attempts") or 2)
        plan = {
            "schema_version": "aion.sales.contact_sequence_step.v1",
            "sequence_step_id": "contact-step-" + secrets.token_hex(8),
            "workspace_id": workspace_id, "opportunity_id": opportunity_id,
            "call_draft_id": call_draft_id, "provider_call_id": str(provider_call_id or ""),
            "provider_status": str(provider_status),
            "disconnection_reason": str(disconnection_reason or "") or None,
            "attempt_number": attempt, "maximum_phone_attempts": maximum,
            "call_goal_contract_hash": draft.get("call_goal_contract_hash"),
            "automatic_send": False, "booking_created": False,
            "prepared_at": _now(), "prepared_by_person_id": prepared_by_person_id,
            "authority_decision": access,
        }
        if provider_status == "ended" and disconnection_reason not in {
                "dial_no_answer", "dial_busy", "dial_failed", "voicemail_reached"}:
            plan.update({"status": "conversation_completed_no_fallback", "next_channel": None})
        elif attempt < maximum:
            plan.update({"status": "telephone_retry_requires_approval", "next_channel": "telephone",
                         "next_attempt_number": attempt + 1})
        else:
            fallback = str(sequence.get("fallback_channel") or "email")
            contact = opportunity.get("contact") or {}
            destination = contact.get("email") if fallback == "email" else contact.get("phone")
            if fallback == "none":
                plan.update({"status": "human_review_required_no_fallback", "next_channel": None})
            elif fallback == "whatsapp":
                plan.update({"status": "blocked_whatsapp_business_connector_required",
                             "next_channel": "whatsapp", "destination": destination})
            elif not destination:
                plan.update({"status": f"blocked_{fallback}_destination_missing",
                             "next_channel": fallback, "destination": None})
            else:
                required = list((draft.get("call_goal_contract") or {}).get("required_fields") or [])
                confirmed = self._confirmed_goal_fields(opportunity)
                questions = int(sequence.get("questions_per_written_message") or 2)
                ask = [value for value in required if value not in confirmed][:max(1, min(3, questions))]
                first_name = str(contact.get("name") or "there").split(" ", 1)[0]
                prompts = "; ".join(value.replace("_", " ") for value in ask) or "any correction to the details already provided"
                body = (
                    f"Hi {first_name}, we tried to reach you about your enquiry. "
                    f"Please reply with: {prompts}. We will continue here without making you repeat "
                    "information already confirmed. A person reviews any appointment, price or work before "
                    "it is confirmed."
                )
                message = self.prepare_message(
                    workspace_id, opportunity_id, channel=fallback,
                    purpose="unanswered_call_goal_continuation",
                    subject="Your enquiry — a few details", body=body,
                    prepared_by_person_id=prepared_by_person_id)
                plan.update({"status": "fallback_message_exact_approval_required",
                             "next_channel": fallback, "destination": destination,
                             "message_id": message["message_id"],
                             "message_hash": message["message_hash"],
                             "questions_requested": ask})
        self._rehash(plan, "sequence_step_hash")
        self._save(workspace_id, "contact_sequences", plan["sequence_step_id"], plan)
        return plan

    def prepare_written_goal_continuation(self, workspace_id: str, opportunity_id: str, *,
                                          call_draft_id: str,
                                          confirmed_fields: dict[str, Any], channel: str,
                                          prepared_by_person_id: str) -> dict[str, Any]:
        """Continue the frozen call objectives after a governed written reply."""
        access = self._require(workspace_id, prepared_by_person_id, "sales.manage")
        opportunity = self.sales.load_opportunity(workspace_id, opportunity_id)
        draft = next((row for row in self.sales.list_call_drafts(workspace_id)
                      if row.get("draft_id") == call_draft_id), None)
        if not draft or draft.get("opportunity_id") != opportunity_id:
            raise FileNotFoundError(call_draft_id)
        if channel not in {"email", "sms"}:
            raise ValueError("written_goal_continuation_requires_email_or_sms")
        contract = draft.get("call_goal_contract") or {}
        required = list(contract.get("required_fields") or [])
        allowed = set(required)
        supplied = {str(key): str(value or "").strip()[:500]
                    for key, value in (confirmed_fields or {}).items()
                    if str(key) in allowed and str(value or "").strip()}
        previous = {}
        for row in self._list(workspace_id, "written_conversations", "continuation_hash"):
            if row.get("call_draft_id") == call_draft_id:
                previous.update(row.get("confirmed_fields") or {})
        confirmed = {**self._confirmed_goal_fields(opportunity), **previous, **supplied}
        missing = [field for field in required if field not in confirmed]
        sequence = draft.get("contact_sequence") or {}
        limit = max(1, min(3, int(sequence.get("questions_per_written_message") or 2)))
        next_questions = missing[:limit]
        record = {
            "schema_version": "aion.sales.written_goal_continuation.v1",
            "continuation_id": "written-continuation-" + secrets.token_hex(8),
            "workspace_id": workspace_id, "opportunity_id": opportunity_id,
            "call_draft_id": call_draft_id,
            "call_goal_contract_hash": draft.get("call_goal_contract_hash"),
            "channel": channel, "confirmed_fields": confirmed,
            "newly_confirmed_fields": supplied, "missing_fields": missing,
            "next_questions": next_questions, "automatic_send": False,
            "booking_created": False, "prepared_at": _now(),
            "prepared_by_person_id": prepared_by_person_id,
            "authority_decision": access,
        }
        if missing:
            first_name = str((opportunity.get("contact") or {}).get("name") or "there").split(" ", 1)[0]
            prompts = "; ".join(value.replace("_", " ") for value in next_questions)
            message = self.prepare_message(
                workspace_id, opportunity_id, channel=channel,
                purpose="written_goal_continuation", subject="Your enquiry — next details",
                body=(f"Thanks {first_name}. We have saved the details you confirmed. "
                      f"Please reply with: {prompts}. A person reviews any appointment, price "
                      "or work before it is confirmed."),
                prepared_by_person_id=prepared_by_person_id)
            record.update({"status": "next_message_exact_approval_required",
                           "message_id": message["message_id"],
                           "message_hash": message["message_hash"]})
        else:
            record.update({
                "status": "qualification_goals_complete_human_booking_review_required",
                "next_action": contract.get("desired_outcome") or "human_review_request",
            })
        self._rehash(record, "continuation_hash")
        self._save(workspace_id, "written_conversations", record["continuation_id"], record)
        return record

    @staticmethod
    def _confirmed_goal_fields(opportunity: dict[str, Any]) -> dict[str, str]:
        contact = opportunity.get("contact") or {}
        answers = (opportunity.get("qualification") or {}).get("answers") or {}
        candidates = {
            "customer_name": contact.get("name"),
            "customer_email": contact.get("email"),
            "work_required": answers.get("work_required") or answers.get("need") or opportunity.get("enquiry"),
            "property_location": answers.get("property_location") or answers.get("location"),
            "full_property_address": answers.get("full_property_address"),
            "urgency": answers.get("urgency"),
            "immediate_safety_risk": answers.get("immediate_safety_risk"),
            "photos_or_documents_available": answers.get("photos_or_documents_available"),
            "preferred_follow_up_channel": answers.get("preferred_follow_up_channel"),
            "preferred_follow_up_time": answers.get("preferred_follow_up_time"),
            "decision_authority": answers.get("decision_authority") or answers.get("decision_maker"),
            "budget_context": answers.get("budget_context"),
        }
        return {key: str(value).strip()[:500] for key, value in candidates.items()
                if value is not None and str(value).strip()}

    def approve_message(self, workspace_id: str, message_id: str, *, expected_message_hash: str,
                        approved_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, approved_by_person_id, "sales.approve_communication")
        message = self._get(workspace_id, "messages", message_id, "message_hash")
        self._exact(message, "message_hash", expected_message_hash, "sales_message_changed_since_review")
        message.update({"status": "approved_not_sent", "approved_at": _now(),
                        "approved_by_person_id": approved_by_person_id, "approval_authority": access})
        self._rehash(message, "message_hash"); self._save(workspace_id, "messages", message_id, message)
        return message

    def create_campaign(self, workspace_id: str, *, name: str, channel: str,
                        contacts: list[dict[str, Any]], variant: str,
                        created_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, created_by_person_id, "sales.manage")
        if channel not in {"email", "sms", "telephone"} or not contacts:
            raise ValueError("valid_campaign_channel_and_audience_required")
        eligible, excluded = [], []
        for row in contacts[:10000]:
            reasons = []
            if row.get("suppressed") or row.get("do_not_contact"): reasons.append("suppressed")
            if row.get("contact_permission") not in {"explicit_outbound", "inbound_response"}: reasons.append("permission_missing")
            destination = row.get("email") if channel == "email" else row.get("phone")
            if not destination: reasons.append("destination_missing")
            (excluded if reasons else eligible).append({**row, "exclusion_reasons": reasons})
        campaign = {"schema_version": "aion.sales.campaign.v1", "campaign_id": "campaign-" + secrets.token_hex(8),
                    "workspace_id": workspace_id, "name": str(name).strip(), "channel": channel,
                    "variant": str(variant or "control"), "eligible_contacts": eligible,
                    "excluded_contacts": excluded, "status": "preflight_passed" if eligible else "blocked_no_eligible_contacts",
                    "daily_cap": 25, "external_messages_sent": 0, "created_at": _now(),
                    "created_by_person_id": created_by_person_id}
        self._rehash(campaign, "campaign_hash"); self._save(workspace_id, "campaigns", campaign["campaign_id"], campaign)
        return campaign

    def record_outcome(self, workspace_id: str, opportunity_id: str, *, disposition: str, value: float,
                       reason: str, variant: str, authority_reference: str,
                       recorded_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, recorded_by_person_id, "sales.manage")
        if disposition not in {"appointment", "won", "lost", "no_response", "not_qualified"} or not authority_reference:
            raise ValueError("valid_independent_sales_outcome_required")
        self.sales.load_opportunity(workspace_id, opportunity_id)
        outcome = {"schema_version": "aion.sales.outcome.v1", "outcome_id": "outcome-" + secrets.token_hex(8),
                   "workspace_id": workspace_id, "opportunity_id": opportunity_id,
                   "disposition": disposition, "value": _money(value), "reason": str(reason).strip(),
                   "variant": str(variant or "control"), "authority_reference": authority_reference,
                   "recorded_at": _now(), "recorded_by_person_id": recorded_by_person_id}
        self._rehash(outcome, "outcome_hash"); self._save(workspace_id, "outcomes", outcome["outcome_id"], outcome)
        return outcome

    def evaluate_experiment(self, workspace_id: str, *, control_variant: str, challenger_variant: str,
                            minimum_samples: int, evaluated_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, evaluated_by_person_id, "sales.manage")
        outcomes = self._list(workspace_id, "outcomes", "outcome_hash")
        arms = {}
        for name in (control_variant, challenger_variant):
            rows = [x for x in outcomes if x.get("variant") == name]
            successes = sum(x.get("disposition") in {"appointment", "won"} for x in rows)
            arms[name] = {"samples": len(rows), "successes": successes,
                          "conversion_rate": round(successes / len(rows), 4) if rows else 0.0,
                          "won_value": round(sum(_money(x.get("value")) for x in rows if x.get("disposition") == "won"), 2)}
        enough = all(x["samples"] >= minimum_samples for x in arms.values())
        lift = arms[challenger_variant]["conversion_rate"] - arms[control_variant]["conversion_rate"]
        experiment = {"schema_version": "aion.sales.experiment.v1", "experiment_id": "experiment-" + secrets.token_hex(8),
                      "workspace_id": workspace_id, "control_variant": control_variant,
                      "challenger_variant": challenger_variant, "minimum_samples": minimum_samples,
                      "arms": arms, "absolute_conversion_lift": round(lift, 4),
                      "status": "challenger_eligible_for_human_promotion" if enough and lift > 0 else
                                "insufficient_independent_outcomes" if not enough else "challenger_rejected",
                      "automatic_promotion": False, "evaluated_at": _now(),
                      "evaluated_by_person_id": evaluated_by_person_id}
        self._rehash(experiment, "experiment_hash"); self._save(workspace_id, "experiments", experiment["experiment_id"], experiment)
        return experiment

    def external_readiness(self, workspace_id: str | None = None) -> dict[str, Any]:
        import os
        gmail = {"mode": "approved_draft_only", "requires_reauthorization": True,
                 "connector_health": "not_connected", "live_draft_ready": False,
                 "live_send_enabled": False}
        hubspot = {"mode": "dry_run", "connector_health": "not_connected",
                   "external_writes_enabled": False}
        try:
            from backend.api.local_node_router import get_runtime
            runtime = get_runtime()
            gmail_health = runtime.get_gmail_connector_health()
            gmail.update({
                "requires_reauthorization": gmail_health.get("auth_status") == "reauthorization_required",
                "connector_health": gmail_health.get("connector_health") or "unknown",
                "auth_status": gmail_health.get("auth_status") or "unknown",
                "live_draft_ready": gmail_health.get("auth_status") == "connected",
            })
            hubspot_health = runtime.get_hubspot_connector_health()
            hubspot.update({
                "connector_health": hubspot_health.get("connector_health") or "unknown",
                "auth_status": hubspot_health.get("auth_status") or "unknown",
                "mode": "connected_read_dry_write" if hubspot_health.get("auth_status") == "connected" else "dry_run",
            })
        except Exception:
            pass
        # Passive workspace rendering must never unlock a Keychain secret.
        # Credential values are read only inside the approved execution path.
        twilio = get_twilio_credential_readiness(workspace_id)
        twilio_ready = bool(twilio["configured"])
        return {
            "gmail": gmail,
            "hubspot": hubspot,
            "calendar": {"mode": "google_calendar_exact_approval",
                         "provider_write_enabled": gmail.get("live_draft_ready", False),
                         "guest_notifications_automatic": False},
            "sms": {"provider": "twilio", "configured": twilio_ready,
                    "credential_ready": twilio["credential_ready"],
                    "phone_number_configured": twilio["phone_number_configured"],
                    "carrier_number_configured": twilio["carrier_number_configured"],
                    "verified_caller_id_configured": twilio["verified_caller_id_configured"],
                    "sip_trunk_configured": twilio["sip_trunk_configured"],
                    "live_send_enabled": bool(twilio_ready and str(os.getenv("AION_SALES_LIVE_SMS_ENABLED") or "").lower() in {"1", "true", "yes"})},
            "telephone": {"provider": "retell", "configured": bool(get_retell_api_key() and get_retell_from_number() and get_retell_agent_id()),
                          "agent_configured": bool(get_retell_agent_id()),
                          "phone_number_configured": bool(get_retell_from_number()),
                          "provider_readback_ready": bool(get_retell_api_key() and get_retell_agent_id()),
                          "webhook_required": False},
        }

    def execute_message(self, workspace_id: str, message_id: str, *, expected_message_hash: str,
                        executed_by_person_id: str) -> dict[str, Any]:
        """Execute the bounded provider action attached to an approved Sales message.

        Email execution creates a Gmail draft and never sends it. SMS requires a
        configured Twilio account plus the explicit live-send environment guard.
        """
        access = self._require(workspace_id, executed_by_person_id, "sales.approve_communication")
        message = self._get(workspace_id, "messages", message_id, "message_hash")
        self._exact(message, "message_hash", expected_message_hash,
                    "sales_message_changed_since_review")
        if message.get("status") != "approved_not_sent":
            raise PermissionError("approved_sales_message_required")
        payload = message.get("payload") or {}
        channel = payload.get("channel")
        if channel == "email":
            try:
                from backend.api.local_node_router import get_runtime
                runtime = get_runtime()
                health = runtime.get_gmail_connector_health()
                if health.get("auth_status") != "connected":
                    raise PermissionError("gmail_reauthorization_required")
                result = runtime._create_gmail_draft(
                    to=str(payload.get("to") or ""),
                    subject=str(payload.get("subject") or "Sales follow-up"),
                    body=str(payload.get("body") or ""),
                )
            except PermissionError:
                raise
            except Exception as exc:
                raise ValueError(f"gmail_draft_creation_failed:{exc}") from exc
            if not result.get("created") or result.get("sent"):
                raise ValueError("gmail_draft_result_not_safe")
            execution = {"status": "gmail_draft_created", "external_draft_created": True,
                         "external_message_sent": False, "provider_result": {
                             "provider": "gmail", "draft_id": result.get("draft_id"),
                             "message_id": result.get("message_id"), "thread_id": result.get("thread_id"),
                             "gmail_url": result.get("gmail_url"), "sent": False}}
        elif channel == "sms":
            result = self._send_twilio_sms(workspace_id=workspace_id, to=str(payload.get("to") or ""),
                                           body=str(payload.get("body") or ""))
            execution = {"status": "sms_submitted", "external_draft_created": False,
                         "external_message_sent": True, "provider_result": {
                             "provider": "twilio", "message_sid": result.get("sid"),
                             "provider_status": result.get("status"), "sent": True}}
        else:
            raise ValueError("unsupported_sales_message_channel")
        message.update({
            **execution,
            "executed_at": _now(),
            "executed_by_person_id": executed_by_person_id,
            "execution_authority": access,
        })
        self._rehash(message, "message_hash")
        self._save(workspace_id, "messages", message_id, message)
        return message

    @staticmethod
    def _send_twilio_sms(workspace_id: str, *, to: str, body: str) -> dict[str, Any]:
        import base64
        import os
        import urllib.parse
        import urllib.request
        account_sid = get_twilio_account_sid(workspace_id)
        api_username = get_twilio_api_username(workspace_id)
        api_secret = get_twilio_api_secret(workspace_id)
        from_number = get_twilio_from_number(workspace_id)
        enabled = str(os.getenv("AION_SALES_LIVE_SMS_ENABLED") or "").lower() in {"1", "true", "yes"}
        if not (account_sid and api_username and api_secret and from_number):
            raise PermissionError("twilio_sms_provider_not_configured")
        if not enabled:
            raise PermissionError("sales_sms_live_send_not_enabled")
        if not str(to or "").startswith("+") or not str(body or "").strip():
            raise ValueError("valid_sms_destination_and_body_required")
        encoded = urllib.parse.urlencode({"To": to, "From": from_number,
                                         "Body": str(body).strip()[:1600]}).encode()
        basic = base64.b64encode(f"{api_username}:{api_secret}".encode()).decode()
        request = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{urllib.parse.quote(account_sid)}/Messages.json",
            data=encoded, headers={"Authorization": f"Basic {basic}",
                                   "Content-Type": "application/x-www-form-urlencoded",
                                   "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"twilio_sms_submission_failed:{exc}") from exc
        if not result.get("sid"):
            raise ValueError("twilio_sms_receipt_missing")
        return {"sid": result.get("sid"), "status": result.get("status") or "submitted"}

    def _require(self, workspace_id: str, person_id: str, capability: str) -> dict[str, Any]:
        decision = self.authority.access_decision(workspace_id, person_id=person_id, capability=capability)
        if not decision.get("allowed"):
            raise PermissionError(decision.get("reason") or f"{capability}_not_authorised")
        return decision

    def _root(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "sales/completion"
        path.mkdir(parents=True, exist_ok=True); return path

    def _path(self, workspace_id: str, kind: str, record_id: str) -> Path:
        path = self._root(workspace_id) / kind; path.mkdir(parents=True, exist_ok=True)
        return path / f"{_safe(record_id)}.json"

    def _save(self, workspace_id: str, kind: str, record_id: str, record: dict[str, Any]) -> None:
        self._write(self._path(workspace_id, kind, record_id), record)

    def _get(self, workspace_id: str, kind: str, record_id: str, hash_field: str) -> dict[str, Any]:
        return self._load(self._path(workspace_id, kind, record_id), workspace_id, hash_field)

    def _list(self, workspace_id: str, kind: str, hash_field: str) -> list[dict[str, Any]]:
        directory = self._root(workspace_id) / kind
        if not directory.exists(): return []
        return [self._load(path, workspace_id, hash_field) for path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]

    @staticmethod
    def _exact(record: dict[str, Any], field: str, expected: str, error: str) -> None:
        if not hmac.compare_digest(str(record.get(field) or ""), str(expected or "")): raise ValueError(error)

    @staticmethod
    def _rehash(record: dict[str, Any], field: str) -> None:
        record.pop(field, None); record[field] = canonical_contract_hash(record)

    @staticmethod
    def _write(path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _load(path: Path, workspace_id: str, hash_field: str) -> dict[str, Any]:
        if not path.exists(): raise FileNotFoundError(path.stem)
        record = json.loads(path.read_text(encoding="utf-8")); expected = record.get(hash_field)
        payload = dict(record); payload.pop(hash_field, None)
        if not expected or canonical_contract_hash(payload) != expected: raise ValueError(f"sales_completion_{hash_field}_mismatch")
        if record.get("workspace_id") != workspace_id: raise PermissionError("sales_completion_workspace_isolation_violation")
        return record
