"""Provider-neutral Sales revenue spine.

This is the canonical commercial ledger between Marketing, conversations,
appointments, Operations and Finance.  External CRMs, calendars, email and
telephony providers are adapters around this model; they are never the source
of Tessaris authority.  Potentially consequential external actions remain
explicitly unperformed until a dedicated approved adapter executes them.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from email.utils import parseaddr
import hashlib
import hmac
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import time
from typing import Any
import urllib.error
import urllib.request

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.telephony_credentials import (
    get_retell_agent_id,
    get_retell_api_key,
    get_retell_from_number,
)


PIPELINE_STAGES = (
    "new", "contacted", "qualification", "qualified", "appointment_proposed",
    "appointment_booked", "human_handoff", "proposal", "won", "lost",
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "new": {"contacted", "qualification", "qualified", "human_handoff", "lost"},
    "contacted": {"qualification", "qualified", "human_handoff", "lost"},
    "qualification": {"qualified", "human_handoff", "lost"},
    "qualified": {"appointment_proposed", "appointment_booked", "human_handoff", "proposal", "lost"},
    "appointment_proposed": {"appointment_booked", "qualified", "human_handoff", "lost"},
    "appointment_booked": {"human_handoff", "proposal", "won", "lost"},
    "human_handoff": {"contacted", "qualification", "qualified", "appointment_proposed", "appointment_booked", "proposal", "won", "lost"},
    "proposal": {"won", "lost", "human_handoff"},
    "won": set(),
    "lost": {"new"},
}

# A provider-neutral service lifecycle.  Businesses may skip irrelevant stages,
# but evidence is never silently moved backwards or rewritten.
WORK_LIFECYCLE_STAGES = (
    "enquiry", "qualification", "appointment", "survey", "quote", "negotiation",
    "won", "scheduled", "procurement", "in_progress", "completed", "invoiced",
    "paid", "review_requested", "closed", "lost",
)

WORK_EVENT_KINDS = (
    "enquiry_received", "qualification_update", "inbound_message", "outbound_draft",
    "call", "booking_prepared", "booking_confirmed", "note", "photo", "document",
    "voice_instruction", "quote_draft", "quote_approved", "quote_sent",
    "customer_reply", "supplier_request", "material_quote", "job_scheduled",
    "work_started", "work_completed", "invoice_draft", "invoice_sent",
    "payment_recorded", "reconciliation", "review_request", "status_update",
)

WORK_ACTION_STATUSES = ("recorded", "draft", "approval_required", "approved", "executed", "failed")

RELATIONSHIP_STATUSES = (
    "lead", "prospect", "active_customer", "active_job", "repeat_customer",
    "on_hold", "completed", "lost",
)
RELATIONSHIP_PRIORITIES = ("normal", "priority", "urgent")
RELATIONSHIP_CHANNELS = ("email", "telephone", "sms", "whatsapp", "in_app", "unspecified")

DEFAULT_PLAYBOOK = {
    "name": "Inbound enquiry qualification",
    "purpose": "Understand the need, establish fit and urgency, then book or hand off without inventing commitments.",
    "questions": [
        {"key": "need", "label": "What does the customer need?", "required": True},
        {"key": "location", "label": "Where is the work or service required?", "required": True},
        {"key": "urgency", "label": "When is it needed?", "required": True},
        {"key": "decision_maker", "label": "Who will approve the work?", "required": False},
        {"key": "budget_context", "label": "Is there a budget or price expectation?", "required": False},
    ],
    "guardrails": [
        "Identify the assistant as AI when the channel requires disclosure.",
        "Use only approved business, product, price and availability evidence.",
        "Never promise price, availability, scope or outcome without authority.",
        "Escalate complaints, vulnerability, uncertainty and unusual commitments to a person.",
        "Never send, call, book, quote or update an external provider without the required approval.",
    ],
    "required_simulations": [
        "cooperative_customer", "confused_customer", "price_objection", "angry_customer",
        "wrong_number", "existing_customer", "vulnerable_person", "unsupported_question",
        "human_requested", "prompt_manipulation", "interruptions",
    ],
}

SIMULATION_CONTRACTS = {
    "cooperative_customer": "qualify",
    "confused_customer": "clarify",
    "price_objection": "evidence_only",
    "angry_customer": "human_handoff",
    "wrong_number": "close_without_contact",
    "existing_customer": "route_support",
    "vulnerable_person": "human_handoff",
    "unsupported_question": "abstain",
    "human_requested": "human_handoff",
    "prompt_manipulation": "refuse_instruction",
    "interruptions": "recover_context",
}

DEFAULT_CALL_GOALS = {
    "desired_outcome": "human_review_request",
    "required_fields": [
        "customer_name", "work_required", "property_location", "urgency",
        "immediate_safety_risk", "photos_or_documents_available",
        "preferred_follow_up_channel", "preferred_follow_up_time",
        "decision_authority",
    ],
    "permitted_outcomes": ["human_review_request", "human_callback_request", "site_visit_request"],
    "prohibited_commitments": ["price", "quote", "discount", "booking", "arrival_time",
                                "payment", "dispatch", "diagnosis", "completion_date"],
    "evidence_route": {"mode": "human_follow_up_required", "destination": None},
    "written_contact_confirmation": True,
}

DEFAULT_AGENT_SETUP = {
    "business_motion": "inbound",
    "lead_temperature": "warm",
    "primary_goal": "human_review_request",
    "required_fields": list(DEFAULT_CALL_GOALS["required_fields"]),
    "allowed_actions": [
        "collect_information", "request_human_callback", "request_site_visit",
        "prepare_follow_up_message", "present_approved_product_options",
    ],
    "intro_style": "warm_direct",
    "custom_intro": "",
    "sales_script": "",
    "close_strategy": "human_review",
    "product_source": "business_operating_model",
    "terms_policy": "approved_link_only",
    "payment_policy": "approved_payment_link_only",
    "evidence_route": {"mode": "human_follow_up_required", "destination": None},
    "contact_sequence": {
        "maximum_phone_attempts": 2,
        "fallback_channel": "email",
        "continue_same_goal_contract": True,
        "questions_per_written_message": 2,
        "automatic_send": False,
    },
}

SALES_AGENT_DIRECTIONS = ("inbound", "outbound", "both")
SALES_AGENT_STATES = ("draft", "testing_required", "ready", "active", "paused")
SALES_AGENT_FIELD_TYPES = ("text", "long_text", "email", "phone", "number", "date", "boolean")

DEFAULT_SALES_AGENT_CAPTURE_FIELDS = [
    {"key": "customer_name", "label": "Customer name", "type": "text", "required": True},
    {"key": "customer_need", "label": "What the customer needs", "type": "long_text", "required": True},
    {"key": "location", "label": "Location", "type": "text", "required": False},
    {"key": "timescale", "label": "Timescale", "type": "text", "required": False},
    {"key": "next_step", "label": "Agreed next step", "type": "text", "required": True},
]


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


def _clean_phone(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    prefix = "+" if raw.startswith("+") else ""
    digits = re.sub(r"\D", "", raw)
    return f"{prefix}{digits}" if len(digits) >= 7 else None


def _clean_email(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    return raw if raw and "@" in raw and "." in raw.rsplit("@", 1)[-1] else None


class SalesRevenueService:
    """Own contacts, opportunities, qualification and conversation evidence."""

    def __init__(self, repository: BusinessContainerRepository | None = None,
                 authority: OrganizationAuthorityService | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = authority or OrganizationAuthorityService(self.repository)

    def workspace(self, workspace_id: str) -> dict[str, Any]:
        opportunities = self.list_opportunities(workspace_id)
        contacts = self.list_contacts(workspace_id)
        companies = self.list_companies(workspace_id)
        playbook = self.ensure_default_playbook(workspace_id)
        sales_agents = self.list_sales_agents(workspace_id)
        summary = self._summary(opportunities)
        return {
            "schema_version": "aion.sales.workspace.v1",
            "workspace_id": workspace_id,
            "pipeline_stages": list(PIPELINE_STAGES),
            "work_feed_contract": {
                "schema_version": "aion.sales.work_feed.v1",
                "lifecycle_stages": list(WORK_LIFECYCLE_STAGES),
                "event_kinds": list(WORK_EVENT_KINDS),
                "action_statuses": list(WORK_ACTION_STATUSES),
                "external_execution_rule": "An executed external action requires a receipt reference.",
                "business_model": "configurable_service_lifecycle",
            },
            "contacts": contacts,
            "companies": companies,
            "opportunities": opportunities,
            "today_queue": self._today_queue(opportunities),
            "summary": summary,
            "playbook": playbook,
            "sales_agents": sales_agents,
            "intake": self.intake_status(workspace_id),
            "telephony": self.telephony_status(workspace_id),
            "actors": self._actors(workspace_id),
            "connector_boundary": {
                "canonical_system": "tessaris_sales_revenue_spine",
                "external_systems": ["hubspot", "calendar", "email", "sms", "managed_telephony"],
                "external_writes_enabled": False,
                "native_voice_available": True,
                "production_telephony": self.telephony_status(workspace_id)["status"],
            },
        }

    def create_intake_endpoint(self, workspace_id: str, *, name: str,
                               created_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, created_by_person_id, "sales.manage")
        clean_name = str(name or "Website enquiry form").strip()[:80]
        endpoint_id = "intake-" + secrets.token_hex(8)
        token = secrets.token_urlsafe(32)
        record = {
            "schema_version": "aion.sales.intake_endpoint.v1",
            "endpoint_id": endpoint_id, "workspace_id": workspace_id,
            "name": clean_name, "status": "active", "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "accepted": 0, "rejected": 0, "last_received_at": None,
            "created_at": _now(), "created_by_person_id": created_by_person_id,
            "authority_decision": access,
            "security": {"token_returned_once": True, "honeypot": True, "idempotency": True,
                         "max_payload_characters": 12000, "accepted_per_minute": 20},
        }
        self._rehash(record, "endpoint_hash")
        self._write(self._intake_path(workspace_id, endpoint_id), record)
        return {**self._public_endpoint(record), "token": token,
                "token_notice": "Copy now. Tessaris stores only its SHA-256 digest."}

    def list_intake_endpoints(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self._public_endpoint(self._load(path, workspace_id, "endpoint_hash"))
                for path in self._sorted(self._intakes_dir(workspace_id))]

    def intake_status(self, workspace_id: str) -> dict[str, Any]:
        endpoints = self.list_intake_endpoints(workspace_id)
        return {
            "website": {"status": "secured_local_receiver_ready" if endpoints else "configuration_required",
                        "endpoints": endpoints,
                        "hosting_boundary": "A public HTTPS deployment or tunnel is required for an internet website."},
            "gmail": {"status": "real_readonly_import_ready", "automatic_reply": False,
                      "default_query": "in:inbox (subject:enquiry OR subject:quote OR subject:booking OR subject:estimate)"},
            "canonical_destination": "tessaris_sales_revenue_spine",
        }

    def ingest_website_enquiry(self, workspace_id: str, endpoint_id: str, *, token: str,
                               payload: dict[str, Any], remote_reference: str | None = None) -> dict[str, Any]:
        path = self._intake_path(workspace_id, endpoint_id)
        endpoint = self._load(path, workspace_id, "endpoint_hash")
        if endpoint.get("status") != "active":
            raise PermissionError("website_intake_endpoint_inactive")
        supplied = hashlib.sha256(str(token or "").encode()).hexdigest()
        if not hmac.compare_digest(supplied, str(endpoint.get("token_sha256") or "")):
            raise PermissionError("website_intake_token_invalid")
        raw_size = len(json.dumps(payload or {}, ensure_ascii=False))
        if raw_size > 12000:
            raise ValueError("website_intake_payload_too_large")
        if str((payload or {}).get("website") or "").strip():
            return {"accepted": False, "reason": "honeypot_triggered", "external_action_performed": False}
        self._rate_limit_intake(endpoint)
        event_id = str((payload or {}).get("event_id") or (payload or {}).get("idempotency_key") or "").strip()
        if not event_id:
            raise ValueError("website_intake_idempotency_key_required")
        channel = str(payload.get("channel") or "")
        machine_request = channel == "external_agent"
        public_agent_intent = channel == "public_agent_intent"
        if machine_request and (not str(payload.get("requesting_agent_id") or "").strip() or
                                not str(payload.get("customer_authority_reference") or "").strip()):
            raise PermissionError("agent_identity_and_customer_authority_required")
        attribution = {key: payload.get(key) for key in (
            "campaign_id", "campaign_name", "channel", "content_id", "landing_page", "referrer",
            "utm_source", "utm_medium", "utm_campaign", "utm_content", "requesting_agent_id",
            "agent_request_id", "requested_service", "requested_window", "max_fiat_price_minor",
            "currency") if payload.get(key) not in (None, "")}
        result = self.create_enquiry(
            workspace_id, name=str(payload.get("name") or "").strip(),
            email=payload.get("email"), phone=payload.get("phone"), company_name=payload.get("company_name"),
            enquiry=str(payload.get("enquiry") or payload.get("message") or "").strip(),
            source="external_agent" if machine_request else "public_agent_intent" if public_agent_intent else "website",
            source_reference=f"{endpoint_id}:{event_id}", attribution=attribution,
            consent={"customer_initiated": not machine_request,
                     "contact_permission": "agent_authorized_response" if machine_request else
                                           "intent_review_only" if public_agent_intent else "inbound_response",
                     "marketing_permission": payload.get("marketing_permission") or "unknown",
                     "source": "authenticated_external_agent" if machine_request else
                               "rate_limited_public_agent_intent" if public_agent_intent else "secured_website_form",
                     "customer_authority_reference": payload.get("customer_authority_reference") if machine_request else None},
            created_by_person_id=str(endpoint["created_by_person_id"]),
        )
        endpoint["accepted"] = int(endpoint.get("accepted") or 0) + (0 if result.get("deduplicated") else 1)
        endpoint["last_received_at"] = _now()
        endpoint["last_remote_reference_hash"] = hashlib.sha256(str(remote_reference or "unknown").encode()).hexdigest()
        self._rehash(endpoint, "endpoint_hash"); self._write(path, endpoint)
        result["intake_evidence"] = {"endpoint_id": endpoint_id, "authenticated": True,
                                     "source_reference": f"{endpoint_id}:{event_id}",
                                     "raw_payload_retained": False}
        if machine_request:
            result["intake_evidence"].update({"machine_agent_authenticated": True,
                "requesting_agent_id": payload.get("requesting_agent_id"),
                "human_review_required": True, "booking_created": False,
                "payment_created": False, "external_message_sent": False})
        elif public_agent_intent:
            result["intake_evidence"].update({"unknown_agent": True,
                "human_review_required": True, "contact_authority_confirmed": False,
                "status_access_granted": False, "booking_created": False,
                "quote_created": False, "payment_created": False,
                "dispatch_started": False, "external_message_sent": False})
        return result

    def import_gmail_messages(self, workspace_id: str, *, messages: list[dict[str, Any]],
                              imported_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, imported_by_person_id, "sales.manage")
        imported, skipped, deduplicated = [], [], 0
        for message in messages or []:
            message_id = str(message.get("id") or message.get("message_id") or "").strip()
            sender_name, sender_email = parseaddr(str(message.get("from") or message.get("sender") or ""))
            subject = str(message.get("subject") or "Enquiry").strip()[:240]
            body = self._plain_email_text(str(message.get("body") or message.get("snippet") or ""))
            if not message_id or not sender_email or not body:
                skipped.append({"message_id": message_id or None, "reason": "identity_or_message_missing"}); continue
            result = self.create_enquiry(
                workspace_id, name=sender_name or sender_email.split("@", 1)[0], email=sender_email,
                phone=None, company_name=None, enquiry=f"{subject}\n\n{body}"[:4000], source="inbound_email",
                source_reference=f"gmail:{message_id}",
                attribution={"channel": "gmail", "content_id": message_id},
                consent={"customer_initiated": True, "contact_permission": "inbound_response",
                         "marketing_permission": "unknown", "source": "gmail_readonly"},
                created_by_person_id=imported_by_person_id,
            )
            if result.get("deduplicated") and result.get("duplicate_reason") == "source_reference": deduplicated += 1
            else: imported.append(result["opportunity"])
        return {"imported": len(imported), "deduplicated": deduplicated, "skipped": skipped,
                "opportunities": imported, "gmail_mutated": False, "reply_sent": False}

    def poll_homefixed_public_queue(self, workspace_id: str, *, imported_by_person_id: str,
                                    queue_url: str, queue_key: str, endpoint_id: str,
                                    intake_token: str) -> dict[str, Any]:
        """Import durable public website/A2A events and acknowledge only persisted rows."""
        self._require(workspace_id, imported_by_person_id, "sales.manage")
        if not all(str(value or "").strip() for value in
                   (queue_url, queue_key, endpoint_id, intake_token)):
            raise ValueError("homefixed_public_queue_not_configured")
        base = str(queue_url).rstrip("/")
        pull = urllib.request.Request(
            f"{base}/pull", headers={"Authorization": f"Bearer {queue_key}",
                                     "Accept": "application/json"}, method="GET")
        try:
            with urllib.request.urlopen(pull, timeout=12) as response:
                queue = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ValueError("homefixed_public_queue_read_failed") from exc
        imported, deduplicated, skipped, acknowledged = 0, 0, [], []
        human, agent, public_intent = 0, 0, 0
        for item in queue.get("items") or []:
            pathname = str(item.get("pathname") or "")
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            try:
                result = self.ingest_website_enquiry(
                    workspace_id, endpoint_id, token=intake_token, payload=payload,
                    remote_reference=f"homefixed_private_queue:{pathname}")
                acknowledged.append(pathname)
                if result.get("deduplicated"):
                    deduplicated += 1
                else:
                    imported += 1
                    channel = str(payload.get("channel") or "")
                    if channel == "external_agent": agent += 1
                    elif channel == "public_agent_intent": public_intent += 1
                    else: human += 1
            except (FileNotFoundError, PermissionError, ValueError) as exc:
                skipped.append({"pathname": pathname, "reason": str(exc)})
        if acknowledged:
            body = json.dumps({"pathnames": acknowledged}).encode("utf-8")
            ack = urllib.request.Request(
                f"{base}/ack", data=body,
                headers={"Authorization": f"Bearer {queue_key}",
                         "Content-Type": "application/json", "Accept": "application/json"},
                method="POST")
            try:
                with urllib.request.urlopen(ack, timeout=12) as response:
                    receipt = json.loads(response.read().decode("utf-8"))
                if int(receipt.get("acknowledged") or 0) != len(acknowledged):
                    raise ValueError("homefixed_public_queue_partial_ack")
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise ValueError("homefixed_public_queue_ack_failed_after_safe_import") from exc
        return {"received": len(queue.get("items") or []), "imported": imported,
                "deduplicated": deduplicated, "human_enquiries": human,
                "agent_requests": agent, "public_agent_intents": public_intent,
                "acknowledged": len(acknowledged),
                "skipped": skipped, "has_more": bool(queue.get("has_more")),
                "external_messages_sent": False, "bookings_created": False,
                "payments_created": False}

    def external_agent_status(self, workspace_id: str, endpoint_id: str, *, token: str,
                              requesting_agent_id: str, agent_request_id: str) -> dict[str, Any]:
        endpoint = self._load(self._intake_path(workspace_id, endpoint_id), workspace_id, "endpoint_hash")
        supplied = hashlib.sha256(str(token or "").encode()).hexdigest()
        if endpoint.get("status") != "active" or not hmac.compare_digest(
                supplied, str(endpoint.get("token_sha256") or "")):
            raise PermissionError("a2a_status_authentication_failed")
        opportunity = next((row for row in self.list_opportunities(workspace_id)
            if row.get("source") == "external_agent"
            and (row.get("attribution") or {}).get("requesting_agent_id") == requesting_agent_id
            and (row.get("attribution") or {}).get("agent_request_id") == agent_request_id), None)
        if not opportunity:
            raise FileNotFoundError(agent_request_id)
        quote = None
        completion = AIONBusinessPaths.business_container_dir(workspace_id) / "sales/completion/quotes"
        if completion.exists():
            for path in sorted(completion.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                raw = json.loads(path.read_text(encoding="utf-8"))
                if raw.get("opportunity_id") == opportunity.get("opportunity_id"):
                    quote = {key: raw.get(key) for key in ("quote_id", "currency", "subtotal", "tax_total", "total",
                             "valid_until", "status", "quote_hash")}; break
        return {"schema_version": "aion.sales.a2a_status.v1", "agent_request_id": agent_request_id,
                "requesting_agent_id": requesting_agent_id, "status": opportunity.get("stage"),
                "human_review_required": opportunity.get("stage") not in {"won", "lost"},
                "quote": quote, "booking_created": opportunity.get("stage") == "appointment_booked",
                "payment_created": False, "settlement_ready": False,
                "last_updated_at": opportunity.get("updated_at")}

    def run_playbook_simulations(self, workspace_id: str, *, run_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, run_by_person_id, "sales.manage")
        playbook = self.ensure_default_playbook(workspace_id)
        results = []
        for scenario in playbook.get("required_simulations") or []:
            expected = SIMULATION_CONTRACTS.get(scenario)
            decision = self._simulate_agent_decision(scenario)
            checks = {
                "correct_route": decision["action"] == expected,
                "ai_disclosure": decision["ai_disclosure"] is True,
                "no_external_action": decision["external_action_performed"] is False,
                "no_unsupported_claim": decision["unsupported_claim"] is False,
            }
            results.append({"scenario": scenario, "expected_action": expected,
                            "observed_action": decision["action"], "checks": checks,
                            "passed": all(checks.values())})
        run = {
            "schema_version": "aion.sales.simulation_run.v1",
            "run_id": "simulation-" + secrets.token_hex(8), "workspace_id": workspace_id,
            "playbook_id": playbook["playbook_id"], "playbook_hash": playbook["playbook_hash"],
            "execution_mode": "deterministic_governance_policy", "results": results,
            "passed": sum(row["passed"] for row in results), "required": len(results),
            "all_passed": bool(results) and all(row["passed"] for row in results),
            "run_at": _now(), "run_by_person_id": run_by_person_id,
            "scope_boundary": "Decision safety and routing passed; natural-language quality and production telephony remain separate gates.",
        }
        self._rehash(run, "run_hash"); self._write(self._simulation_path(workspace_id, run["run_id"]), run)
        playbook["simulation"] = {"passed": run["passed"], "required": run["required"],
                                  "last_run_id": run["run_id"], "all_passed": run["all_passed"]}
        playbook["status"] = "simulation_passed_promotion_required" if run["all_passed"] else "simulation_failed"
        self._rehash(playbook, "playbook_hash"); self._write(self._playbook_path(workspace_id, playbook["playbook_id"]), playbook)
        return {"run": run, "playbook": playbook}

    def promote_playbook(self, workspace_id: str, *, expected_playbook_hash: str,
                         promoted_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, promoted_by_person_id, "sales.manage")
        playbook = self.ensure_default_playbook(workspace_id)
        if not hmac.compare_digest(str(playbook.get("playbook_hash") or ""), str(expected_playbook_hash or "")):
            raise ValueError("sales_playbook_changed_since_approval")
        simulation = playbook.get("simulation") or {}
        if not simulation.get("all_passed") or int(simulation.get("passed") or 0) != int(simulation.get("required") or 0):
            raise PermissionError("all_required_sales_simulations_must_pass")
        playbook.update({"status": "promoted_for_controlled_use", "promoted_at": _now(),
                         "promoted_by_person_id": promoted_by_person_id, "promotion_authority": access,
                         "external_deployment_performed": False})
        self._rehash(playbook, "playbook_hash"); self._write(self._playbook_path(workspace_id, playbook["playbook_id"]), playbook)
        return playbook

    def telephony_status(self, workspace_id: str) -> dict[str, Any]:
        playbook = self.ensure_default_playbook(workspace_id)
        api_key_connected = bool(get_retell_api_key(workspace_id))
        agent_id = get_retell_agent_id(workspace_id)
        from_number = get_retell_from_number(workspace_id)
        configured = bool(api_key_connected and agent_id and from_number)
        enabled = str(os.getenv("AION_SALES_LIVE_TELEPHONY_ENABLED") or "").lower() in {"1", "true", "yes"}
        drafts = self.list_call_drafts(workspace_id)
        events = self.list_telephony_events(workspace_id)
        return {"provider": "retell", "status": "live_execution_enabled" if configured and enabled else
                "credentials_ready_execution_disabled" if configured else
                "agent_ready_number_required" if api_key_connected and agent_id else "provider_configuration_required",
                "configured": configured, "live_execution_enabled": configured and enabled,
                "api_key_connected": api_key_connected, "agent_configured": bool(agent_id),
                "phone_number_configured": bool(from_number), "agent_id": agent_id or None,
                "playbook_promoted": playbook.get("status") == "promoted_for_controlled_use",
                "call_requires_exact_approval": True, "webhook_signature_required": True,
                "provider_readback_ready": bool(api_key_connected and agent_id),
                "public_https_webhook_required": False,
                "webhook_mode": "optional_for_realtime_updates",
                "call_drafts": drafts[:20], "events": events[:30],
                "active_calls": sum(row.get("status") == "submitted" for row in drafts),
                "documents": {"api": "https://docs.retellai.com/api-references/create-phone-call",
                              "webhook": "https://docs.retellai.com/features/secure-webhook"}}

    def list_call_drafts(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self._load(path, workspace_id, "draft_hash")
                for path in self._sorted(self._call_drafts_dir(workspace_id))]

    def list_telephony_events(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self._load(path, workspace_id, "event_hash")
                for path in self._sorted(self._telephony_events_dir(workspace_id))]

    def sync_retell_call_history(self, workspace_id: str, *, synced_by_person_id: str,
                                 limit: int = 100) -> dict[str, Any]:
        """Read back this workspace's dedicated Retell agent calls without a webhook.

        Retell's public list endpoint is deliberately filtered by the configured
        agent ID. Completed calls are then retrieved individually so transcripts
        and analysis come from provider readback rather than from an unsigned
        browser payload. One canonical file per call makes repeated polls safe.
        """
        access = self._require(workspace_id, synced_by_person_id, "sales.manage")
        api_key = get_retell_api_key(workspace_id)
        agent_id = get_retell_agent_id(workspace_id)
        if not api_key or not agent_id:
            raise ValueError("retell_agent_not_configured")
        bounded_limit = max(1, min(int(limit), 250))
        payload = {
            "filter_criteria": {"agent": [{"agent_id": agent_id}]},
            "sort_order": "descending", "limit": bounded_limit,
            "include_total": True,
        }
        request = urllib.request.Request(
            "https://api.retellai.com/v3/list-calls",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                listing = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"retell_call_history_failed:{exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("retell_call_history_failed") from exc

        imported, updated, unchanged, skipped = 0, 0, 0, []
        for summary in listing.get("items") or []:
            call_id = str(summary.get("call_id") or "").strip()
            if not call_id or str(summary.get("agent_id") or "") != agent_id:
                skipped.append({"call_id": call_id or None, "reason": "agent_identity_mismatch"})
                continue
            call = summary
            if summary.get("call_status") in {"ended", "error"}:
                detail_request = urllib.request.Request(
                    f"https://api.retellai.com/v2/get-call/{call_id}",
                    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                    method="GET",
                )
                try:
                    with urllib.request.urlopen(detail_request, timeout=25) as response:
                        detail = json.loads(response.read().decode("utf-8"))
                    if str(detail.get("agent_id") or "") != agent_id:
                        skipped.append({"call_id": call_id, "reason": "detail_agent_identity_mismatch"})
                        continue
                    call = detail
                except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                    # The lean list response is still valid provider evidence.
                    call = summary

            safe = self._retell_call_readback_event(
                workspace_id, call=call, synced_by_person_id=synced_by_person_id,
                authority_decision=access,
            )
            path = self._telephony_events_dir(workspace_id) / f"retell-readback-{_safe(call_id)}.json"
            previous = None
            if path.exists():
                previous = self._load(path, workspace_id, "event_hash")
            comparable_previous = {key: value for key, value in (previous or {}).items()
                                   if key not in {"synced_at", "synced_by_person_id", "event_hash"}}
            comparable_safe = {key: value for key, value in safe.items()
                               if key not in {"synced_at", "synced_by_person_id", "event_hash"}}
            if previous and comparable_previous == comparable_safe:
                unchanged += 1
                continue
            self._rehash(safe, "event_hash")
            self._write(path, safe)
            if previous: updated += 1
            else: imported += 1
        return {
            "provider": "retell", "agent_id": agent_id,
            "received": len(listing.get("items") or []),
            "provider_total": listing.get("total"), "imported": imported,
            "updated": updated, "unchanged": unchanged, "skipped": skipped,
            "has_more": bool(listing.get("has_more")),
            "read_only": True, "external_call_started": False,
        }

    @staticmethod
    def _retell_call_readback_event(workspace_id: str, *, call: dict[str, Any],
                                    synced_by_person_id: str,
                                    authority_decision: dict[str, Any]) -> dict[str, Any]:
        metadata = call.get("metadata") if isinstance(call.get("metadata"), dict) else {}
        analysis = call.get("call_analysis") if isinstance(call.get("call_analysis"), dict) else {}
        transcript = call.get("transcript_object") if isinstance(call.get("transcript_object"), list) else []
        # Signed recording and log URLs are intentionally not copied into the
        # canonical ledger. They can be retrieved again under provider auth.
        return {
            "schema_version": "aion.sales.telephony_event.v1",
            "workspace_id": workspace_id, "event": "provider_readback",
            "provider": "retell", "provider_authority": "authenticated_api_readback",
            "call_id": str(call.get("call_id") or ""),
            "agent_id": str(call.get("agent_id") or ""),
            "agent_version": call.get("agent_version"),
            "call_type": call.get("call_type"), "call_status": call.get("call_status"),
            "direction": call.get("direction"), "start_timestamp": call.get("start_timestamp"),
            "end_timestamp": call.get("end_timestamp"), "duration_ms": call.get("duration_ms"),
            "disconnection_reason": call.get("disconnection_reason"),
            "opportunity_id": metadata.get("opportunity_id"),
            "draft_id": metadata.get("draft_id"), "playbook_hash": metadata.get("playbook_hash"),
            "transcript_object": transcript, "call_analysis": analysis,
            "cost": (call.get("call_cost") or {}).get("combined_cost")
                    if isinstance(call.get("call_cost"), dict) else None,
            "synced_at": _now(), "synced_by_person_id": synced_by_person_id,
            "authority_decision": authority_decision,
        }

    def prepare_outbound_call(self, workspace_id: str, opportunity_id: str, *,
                              reason: str, prepared_by_person_id: str,
                              goals: dict[str, Any] | None = None,
                              agent_id: str | None = None) -> dict[str, Any]:
        access = self._require(workspace_id, prepared_by_person_id, "sales.manage")
        selected_agent = self.get_sales_agent(workspace_id, agent_id) if agent_id else None
        playbook = self.ensure_default_playbook(workspace_id)
        if selected_agent:
            if selected_agent.get("state") != "active":
                raise PermissionError("active_sales_agent_required")
            if selected_agent.get("direction") not in {"outbound", "both"}:
                raise PermissionError("outbound_sales_agent_required")
            if not selected_agent.get("minted_contract"):
                raise PermissionError("minted_sales_agent_contract_required")
        elif playbook.get("status") != "promoted_for_controlled_use":
            raise PermissionError("promoted_sales_playbook_required")
        opportunity = self.load_opportunity(workspace_id, opportunity_id)
        phone = _clean_phone((opportunity.get("contact") or {}).get("phone"))
        if not phone or not phone.startswith("+"):
            raise ValueError("e164_customer_phone_required")
        consent = opportunity.get("consent") or {}
        if consent.get("contact_permission") not in {"inbound_response", "explicit_outbound"}:
            raise PermissionError("telephone_contact_permission_required")
        setup = playbook.get("agent_setup") or DEFAULT_AGENT_SETUP
        supplied_goals = goals if isinstance(goals, dict) else {
            "desired_outcome": setup.get("primary_goal"),
            "required_fields": setup.get("required_fields"),
            "evidence_route": setup.get("evidence_route"),
            "written_contact_confirmation": setup.get("written_contact_confirmation", True),
        }
        goal_contract = self._normalise_call_goals(supplied_goals)
        goal_contract["conversation_policy"] = {
            "business_motion": setup.get("business_motion"),
            "lead_temperature": setup.get("lead_temperature"),
            "allowed_actions": setup.get("allowed_actions") or [],
            "intro_style": setup.get("intro_style"),
            "custom_intro": setup.get("custom_intro") or "",
            "sales_script": setup.get("sales_script") or "",
            "close_strategy": setup.get("close_strategy"),
            "product_source": setup.get("product_source"),
            "terms_policy": setup.get("terms_policy"),
            "payment_policy": setup.get("payment_policy"),
        }
        if selected_agent:
            contract_ref = selected_agent.get("minted_contract") or {}
            template = self._load(
                self._sales_agent_contract_path(
                    workspace_id, selected_agent["agent_id"], contract_ref.get("contract_hash")
                ), workspace_id, "contract_hash"
            )
            goal_contract = {
                "schema_version": "aion.sales.call_goal_contract.v2",
                "desired_outcome": (template.get("objective") or {}).get("primary_outcome"),
                "required_fields": [row.get("key") for row in template.get("capture_fields") or []
                                    if row.get("required")],
                "capture_schema": template.get("capture_fields") or [],
                "permitted_actions": template.get("allowed_actions") or [],
                "prohibited_commitments": list(DEFAULT_CALL_GOALS["prohibited_commitments"]),
                "agent_contract": template,
                "agent_contract_hash": template.get("contract_hash"),
                "customer_context": {
                    "customer_name": (opportunity.get("contact") or {}).get("name"),
                    "enquiry": str(opportunity.get("enquiry") or "")[:4000],
                    "source": opportunity.get("source"),
                    "known_qualification": (opportunity.get("qualification") or {}).get("answers") or {},
                },
            }
        draft = {
            "schema_version": "aion.sales.telephony_call_draft.v1",
            "draft_id": "call-draft-" + secrets.token_hex(8), "workspace_id": workspace_id,
            "opportunity_id": opportunity_id, "provider": "retell", "direction": "outbound",
            "to_number": phone, "from_number_env": "RETELL_FROM_NUMBER", "reason": str(reason or "Respond to enquiry").strip(),
            "playbook_id": selected_agent["agent_id"] if selected_agent else playbook["playbook_id"],
            "playbook_hash": ((selected_agent.get("minted_contract") or {}).get("contract_hash")
                              if selected_agent else playbook["playbook_hash"]),
            "sales_agent_id": selected_agent.get("agent_id") if selected_agent else None,
            "sales_agent_name": selected_agent.get("name") if selected_agent else None,
            "provider_agent_id": ((selected_agent.get("phone_assignment") or {}).get("provider_agent_id")
                                  if selected_agent else get_retell_agent_id(workspace_id)),
            "call_goal_contract": goal_contract,
            "call_goal_contract_hash": canonical_contract_hash(goal_contract),
            "attempt_number": 1 + sum(
                row.get("opportunity_id") == opportunity_id
                for row in self.list_call_drafts(workspace_id)
            ),
            "contact_sequence": self._normalise_contact_sequence(setup.get("contact_sequence")),
            "customer_name": (opportunity.get("contact") or {}).get("name"),
            "status": "exact_approval_required", "ai_disclosure_required": True,
            "recording": "off_unless_separately_consented", "prepared_at": _now(),
            "prepared_by_person_id": prepared_by_person_id, "authority_decision": access,
            "external_call_started": False,
        }
        self._rehash(draft, "draft_hash"); self._write(self._call_draft_path(workspace_id, draft["draft_id"]), draft)
        return draft

    def approve_outbound_call(self, workspace_id: str, draft_id: str, *, expected_draft_hash: str,
                              approved_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, approved_by_person_id, "sales.approve_communication")
        draft = self._load(self._call_draft_path(workspace_id, draft_id), workspace_id, "draft_hash")
        if not hmac.compare_digest(str(draft.get("draft_hash") or ""), str(expected_draft_hash or "")):
            raise ValueError("sales_call_draft_changed_since_review")
        draft.update({"status": "approved_not_executed", "approved_at": _now(),
                      "approved_by_person_id": approved_by_person_id, "approval_authority": access})
        self._rehash(draft, "draft_hash"); self._write(self._call_draft_path(workspace_id, draft_id), draft)
        return draft

    def execute_outbound_call(self, workspace_id: str, draft_id: str, *, expected_draft_hash: str,
                              executed_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, executed_by_person_id, "sales.approve_communication")
        draft = self._load(self._call_draft_path(workspace_id, draft_id), workspace_id, "draft_hash")
        if draft.get("status") != "approved_not_executed": raise PermissionError("approved_sales_call_required")
        if not hmac.compare_digest(str(draft.get("draft_hash") or ""), str(expected_draft_hash or "")):
            raise ValueError("sales_call_draft_changed_since_approval")
        readiness = self.telephony_status(workspace_id)
        if not readiness["live_execution_enabled"]: raise PermissionError("live_sales_telephony_not_enabled")
        payload = {
            "from_number": get_retell_from_number(workspace_id), "to_number": draft["to_number"],
            "override_agent_id": draft.get("provider_agent_id") or get_retell_agent_id(workspace_id),
            "metadata": {"workspace_id": workspace_id, "opportunity_id": draft["opportunity_id"],
                         "draft_id": draft_id, "playbook_hash": draft["playbook_hash"]},
            "retell_llm_dynamic_variables": {"customer_name": str(draft.get("customer_name") or "customer"),
                                             "enquiry_reason": str(draft.get("reason") or ""),
                                             "call_goal_contract": json.dumps(
                                                 draft.get("call_goal_contract") or {},
                                                 ensure_ascii=False, sort_keys=True)},
        }
        request = urllib.request.Request("https://api.retellai.com/v2/create-phone-call",
            data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {get_retell_api_key(workspace_id)}",
            "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                provider_result = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"retell_call_failed:{exc.code}") from exc
        draft.update({"status": "submitted", "external_call_started": True, "executed_at": _now(),
                      "executed_by_person_id": executed_by_person_id,
                      "provider_call_id": provider_result.get("call_id"),
                      "provider_call_status": provider_result.get("call_status")})
        self._rehash(draft, "draft_hash"); self._write(self._call_draft_path(workspace_id, draft_id), draft)
        return {"draft": draft, "provider": {key: provider_result.get(key) for key in
                ("call_id", "call_status", "agent_id", "agent_version", "direction")}}

    @staticmethod
    def _normalise_call_goals(goals: dict[str, Any] | None) -> dict[str, Any]:
        raw = goals if isinstance(goals, dict) else {}
        allowed_fields = set(DEFAULT_CALL_GOALS["required_fields"]) | {
            "customer_email", "full_property_address", "access_constraints",
            "budget_context", "property_ownership", "preferred_visit_window",
        }
        required = []
        for value in raw.get("required_fields") or DEFAULT_CALL_GOALS["required_fields"]:
            key = str(value or "").strip()
            if key in allowed_fields and key not in required:
                required.append(key)
        if not required:
            raise ValueError("at_least_one_valid_call_goal_required")
        desired = str(raw.get("desired_outcome") or DEFAULT_CALL_GOALS["desired_outcome"])
        if desired not in DEFAULT_CALL_GOALS["permitted_outcomes"]:
            raise ValueError("unsupported_call_outcome_goal")
        route = raw.get("evidence_route") if isinstance(raw.get("evidence_route"), dict) else {}
        mode = str(route.get("mode") or "human_follow_up_required")
        if mode not in {"reply_to_approved_sms", "approved_email_address", "human_follow_up_required"}:
            raise ValueError("unsupported_call_evidence_route")
        destination = str(route.get("destination") or "").strip() or None
        if mode != "human_follow_up_required" and not destination:
            raise ValueError("configured_evidence_destination_required")
        return {
            "schema_version": "aion.sales.call_goal_contract.v1",
            "desired_outcome": desired,
            "required_fields": required,
            "permitted_outcomes": list(DEFAULT_CALL_GOALS["permitted_outcomes"]),
            "prohibited_commitments": list(DEFAULT_CALL_GOALS["prohibited_commitments"]),
            "evidence_route": {"mode": mode, "destination": destination},
            "written_contact_confirmation": bool(raw.get("written_contact_confirmation", True)),
            "completion_rule": "Every required field is answered or explicitly marked unknown; facts are summarised; human review is requested; no prohibited commitment is made.",
        }

    def record_retell_webhook(self, workspace_id: str, *, raw_body: bytes, signature: str) -> dict[str, Any]:
        api_key = get_retell_api_key(workspace_id)
        if not api_key or not self._verify_retell_signature(raw_body, signature, api_key):
            raise PermissionError("retell_webhook_signature_invalid")
        event = json.loads(raw_body.decode())
        call = event.get("call") or {}; call_id = str(call.get("call_id") or "")
        if not call_id: raise ValueError("retell_call_id_required")
        safe = {"schema_version": "aion.sales.telephony_event.v1", "workspace_id": workspace_id,
                "event": str(event.get("event") or "unknown"), "call_id": call_id,
                "call_status": call.get("call_status"), "direction": call.get("direction"),
                "transcript_object": call.get("transcript_object") or [],
                "disconnection_reason": call.get("disconnection_reason"),
                "call_analysis": call.get("call_analysis") or {}, "received_at": _now()}
        self._rehash(safe, "event_hash")
        self._write(self._telephony_events_dir(workspace_id) / f"{_safe(call_id)}-{int(time.time()*1000)}.json", safe)
        return safe

    def create_enquiry(self, workspace_id: str, *, name: str, email: str | None,
                       phone: str | None, company_name: str | None, enquiry: str,
                       source: str, source_reference: str | None,
                       attribution: dict[str, Any] | None,
                       consent: dict[str, Any] | None,
                       created_by_person_id: str, customer_type: str = "person",
                       first_name: str | None = None, last_name: str | None = None,
                       address: str | None = None, position_title: str | None = None,
                       department: str | None = None,
                       phone_extension: str | None = None, entry_mode: str = "lead",
                       initial_stage: str = "new", estimated_value: float | None = None,
                       currency: str = "GBP", next_action: str | None = None) -> dict[str, Any]:
        access = self._require(workspace_id, created_by_person_id, "sales.manage")
        customer_type = str(customer_type or "person").strip().lower()
        if customer_type not in {"person", "business"}:
            raise ValueError("sales_customer_type_must_be_person_or_business")
        first_name = re.sub(r"\s+", " ", str(first_name or "").strip())[:100] or None
        last_name = re.sub(r"\s+", " ", str(last_name or "").strip())[:100] or None
        name = str(name or "").strip()
        if first_name or last_name:
            name = " ".join(value for value in (first_name, last_name) if value)
        email = _clean_email(email)
        phone = _clean_phone(phone)
        address = re.sub(r"\s+", " ", str(address or "").strip())[:500] or None
        position_title = re.sub(r"\s+", " ", str(position_title or "").strip())[:120] or None
        department = re.sub(r"\s+", " ", str(department or "").strip())[:120] or None
        phone_extension = re.sub(r"[^a-zA-Z0-9#*-]", "", str(phone_extension or ""))[:20] or None
        entry_mode = str(entry_mode or "lead").strip().lower()
        if entry_mode not in {"lead", "existing_deal"}:
            raise ValueError("sales_entry_mode_must_be_lead_or_existing_deal")
        initial_stage = str(initial_stage or "new").strip().lower()
        if initial_stage not in PIPELINE_STAGES:
            raise ValueError("unknown_sales_pipeline_stage")
        if entry_mode == "lead":
            initial_stage = "new"
        estimated_value = None if estimated_value is None else max(0.0, round(float(estimated_value), 2))
        currency = re.sub(r"[^A-Z]", "", str(currency or "GBP").upper())[:3] or "GBP"
        next_action = re.sub(r"\s+", " ", str(next_action or "").strip())[:240] or None
        enquiry = str(enquiry or "").strip()
        source = str(source or "manual").strip().lower()
        source_reference = str(source_reference or "").strip() or None
        if not name or not enquiry:
            raise ValueError("sales_name_and_enquiry_required")
        if not email and not phone:
            raise ValueError("sales_contact_method_required")
        if customer_type == "business" and not str(company_name or "").strip():
            raise ValueError("sales_business_company_name_required")
        if source_reference:
            existing = next((row for row in self.list_opportunities(workspace_id)
                             if row.get("source") == source and row.get("source_reference") == source_reference), None)
            if existing:
                return {"contact": self.load_contact(workspace_id, existing["contact_id"]),
                        "opportunity": existing, "deduplicated": True,
                        "duplicate_reason": "source_reference"}

        company = self._find_or_create_company(workspace_id, company_name,
                                               created_by_person_id=created_by_person_id)
        contact = self._find_contact(workspace_id, email=email, phone=phone)
        contact_was_existing = bool(contact)
        if contact:
            contact["name"] = contact.get("name") or name
            contact["company_name"] = contact.get("company_name") or (company or {}).get("name")
            contact["company_id"] = contact.get("company_id") or (company or {}).get("company_id")
            contact["email"] = contact.get("email") or email
            contact["phone"] = contact.get("phone") or phone
            contact["customer_type"] = "business" if customer_type == "business" else contact.get("customer_type") or "person"
            contact["first_name"] = contact.get("first_name") or first_name
            contact["last_name"] = contact.get("last_name") or last_name
            contact["address"] = contact.get("address") or address
            contact["position_title"] = contact.get("position_title") or position_title
            contact["department"] = contact.get("department") or department
            contact["phone_extension"] = contact.get("phone_extension") or phone_extension
            contact["updated_at"] = _now()
        else:
            identity = canonical_contract_hash({"email": email, "phone": phone}).removeprefix("sha256:")[:20]
            contact = {
                "schema_version": "aion.sales.contact.v1", "contact_id": f"contact-{identity}",
                "workspace_id": workspace_id, "name": name, "email": email, "phone": phone,
                "customer_type": customer_type, "first_name": first_name, "last_name": last_name,
                "address": address, "position_title": position_title,
                "department": department, "phone_extension": phone_extension,
                "company_id": (company or {}).get("company_id"),
                "company_name": (company or {}).get("name"),
                "status": "active", "provider_links": {}, "created_at": _now(), "updated_at": _now(),
            }
        self._rehash(contact, "contact_hash")
        self._write(self._contact_path(workspace_id, contact["contact_id"]), contact)

        consent_record = self._normalise_consent(source, consent)
        opportunity_id = "opportunity-" + canonical_contract_hash({
            "workspace_id": workspace_id, "contact_id": contact["contact_id"], "source": source,
            "source_reference": source_reference, "enquiry": enquiry, "created_at": _now(),
        }).removeprefix("sha256:")[:20]
        opportunity = {
            "schema_version": "aion.sales.opportunity.v1", "opportunity_id": opportunity_id,
            "workspace_id": workspace_id, "contact_id": contact["contact_id"],
            "contact": self._contact_projection(contact), "title": enquiry[:96], "enquiry": enquiry,
            "source": source, "source_reference": source_reference,
            "attribution": self._clean_mapping(attribution or {}), "consent": consent_record,
            "stage": initial_stage, "status": "closed" if initial_stage in {"won", "lost"} else "open",
            "owner_person_id": created_by_person_id,
            "deal": {"entry_mode": entry_mode, "estimated_value": estimated_value,
                     "currency": currency, "imported_as_existing": entry_mode == "existing_deal"},
            "relationship": {
                "status": "lost" if initial_stage == "lost" else "active_customer" if initial_stage == "won" else
                          "prospect" if entry_mode == "existing_deal" else "lead",
                "priority": "normal", "preferred_channel": "unspecified",
                "next_action": next_action or ("Qualify enquiry" if entry_mode == "lead" else f"Review {initial_stage.replace('_', ' ')} deal"),
                "next_action_due": None, "tags": [],
                "updated_at": _now(), "updated_by_person_id": created_by_person_id,
            },
            "qualification": {"status": "not_started", "answers": {}, "score": 0,
                              "missing_required": ["need", "location", "urgency"]},
            "appointments": [], "sessions": [], "activities": [], "handoff": None,
            "work_feed": self._new_work_feed(opportunity_id),
            "external_writes": [], "created_at": _now(), "updated_at": _now(),
            "created_by_person_id": created_by_person_id, "authority_decision": access,
        }
        self._activity(opportunity, "enquiry_created", created_by_person_id, {
            "source": source, "contact_deduplicated": contact_was_existing,
            "external_action_performed": False,
        })
        self._append_work_event_record(
            opportunity, kind="enquiry_received", title="Enquiry received", summary=enquiry,
            details={"source": source, "source_reference": source_reference},
            lifecycle_stage="enquiry", source=source, provider="tessaris",
            source_reference=source_reference, attachments=[],
            action={"status": "recorded", "external_action_performed": False},
            recorded_by_person_id=created_by_person_id,
        )
        if entry_mode == "existing_deal" and initial_stage != "new":
            lifecycle = {"qualification": "qualification", "qualified": "qualification",
                         "appointment_proposed": "appointment", "appointment_booked": "appointment",
                         "proposal": "quote", "won": "won", "lost": "lost"}.get(initial_stage)
            self._append_work_event_record(
                opportunity, kind="status_update", title="Existing deal added",
                summary=f"Existing deal entered at {initial_stage.replace('_', ' ')} stage.",
                details={"pipeline_stage": initial_stage, "estimated_value": estimated_value,
                         "currency": currency, "next_action": opportunity["relationship"]["next_action"]},
                lifecycle_stage=lifecycle, source="manual", provider="tessaris",
                source_reference=source_reference, attachments=[],
                action={"status": "recorded", "external_action_performed": False},
                recorded_by_person_id=created_by_person_id,
            )
        self._save_opportunity(workspace_id, opportunity)
        self._project(workspace_id, opportunity)
        return {"contact": contact, "opportunity": opportunity,
                "deduplicated": contact_was_existing, "duplicate_reason": "contact_identity" if contact_was_existing else None}

    def qualify(self, workspace_id: str, opportunity_id: str, *, answers: dict[str, Any],
                notes: str | None, qualified_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, qualified_by_person_id, "sales.qualify")
        record = self.load_opportunity(workspace_id, opportunity_id)
        clean = {str(key): str(value or "").strip() for key, value in (answers or {}).items()}
        required = ["need", "location", "urgency"]
        missing = [key for key in required if not clean.get(key)]
        optional_credit = sum(bool(clean.get(key)) for key in ("decision_maker", "budget_context")) * 5
        score = min(100, (len(required) - len(missing)) * 30 + optional_credit)
        risk_flags = sorted(set(str(value) for value in (answers or {}).get("risk_flags", []) if value)) if isinstance((answers or {}).get("risk_flags"), list) else []
        status = "qualified" if not missing and not risk_flags else "human_review_required" if risk_flags else "incomplete"
        record["qualification"] = {
            "status": status, "answers": clean, "score": score,
            "missing_required": missing, "risk_flags": risk_flags,
            "notes": str(notes or "").strip() or None, "qualified_at": _now(),
            "qualified_by_person_id": qualified_by_person_id, "authority_decision": access,
            "decision_boundary": "The score recommends workflow only; it does not reject or bind the customer.",
        }
        target = "qualified" if status == "qualified" else "human_handoff" if risk_flags else "qualification"
        self._transition(record, target, allow_same=True)
        self._activity(record, "qualification_recorded", qualified_by_person_id,
                       {"score": score, "status": status, "missing_required": missing, "risk_flags": risk_flags})
        self._append_work_event_record(
            record, kind="qualification_update", title="Qualification updated",
            summary=str(notes or "Qualification evidence recorded").strip(),
            details={"score": score, "status": status, "missing_required": missing,
                     "answers": clean}, lifecycle_stage="qualification", source="sales",
            provider="tessaris", source_reference=None, attachments=[],
            action={"status": "recorded", "external_action_performed": False},
            recorded_by_person_id=qualified_by_person_id,
        )
        self._save_opportunity(workspace_id, record); self._project(workspace_id, record)
        return record

    def prepare_appointment(self, workspace_id: str, opportunity_id: str, *, starts_at: str,
                            duration_minutes: int, assigned_person_id: str,
                            location_or_channel: str, notes: str | None,
                            prepared_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, prepared_by_person_id, "sales.manage")
        record = self.load_opportunity(workspace_id, opportunity_id)
        if record["stage"] not in {"qualified", "appointment_proposed", "human_handoff"}:
            raise ValueError("qualified_opportunity_required_for_appointment")
        try:
            start = datetime.fromisoformat(str(starts_at).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("valid_appointment_time_required") from exc
        if duration_minutes < 5 or duration_minutes > 480:
            raise ValueError("appointment_duration_out_of_range")
        appointment = {
            "appointment_id": f"appointment-{len(record['appointments']) + 1}",
            "starts_at": start.isoformat(), "duration_minutes": duration_minutes,
            "assigned_person_id": assigned_person_id,
            "location_or_channel": str(location_or_channel or "").strip(),
            "notes": str(notes or "").strip() or None,
            "status": "exact_calendar_approval_required", "prepared_at": _now(),
            "prepared_by_person_id": prepared_by_person_id, "authority_decision": access,
            "external_calendar_write_performed": False, "customer_notification_sent": False,
        }
        appointment["appointment_hash"] = canonical_contract_hash(appointment)
        record["appointments"].append(appointment)
        self._transition(record, "appointment_proposed", allow_same=True)
        self._activity(record, "appointment_prepared", prepared_by_person_id,
                       {"appointment_id": appointment["appointment_id"], "starts_at": appointment["starts_at"],
                        "external_action_performed": False})
        self._append_work_event_record(
            record, kind="booking_prepared", title="Appointment prepared",
            summary=f"{appointment['starts_at']} · {appointment['location_or_channel']}",
            details={"appointment_id": appointment["appointment_id"],
                     "duration_minutes": duration_minutes,
                     "assigned_person_id": assigned_person_id,
                     "notes": appointment["notes"]}, lifecycle_stage="appointment",
            source="sales", provider="tessaris", source_reference=appointment["appointment_id"],
            attachments=[], action={"status": "approval_required",
                                    "external_action_performed": False,
                                    "approval_type": "calendar_and_customer_notification"},
            recorded_by_person_id=prepared_by_person_id,
        )
        self._save_opportunity(workspace_id, record); self._project(workspace_id, record)
        return record

    def handoff(self, workspace_id: str, opportunity_id: str, *, assigned_person_id: str,
                reason: str, urgency: str, handed_off_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, handed_off_by_person_id, "sales.manage")
        record = self.load_opportunity(workspace_id, opportunity_id)
        reason = str(reason or "").strip()
        if not reason:
            raise ValueError("sales_handoff_reason_required")
        record["handoff"] = {
            "assigned_person_id": assigned_person_id, "reason": reason,
            "urgency": urgency if urgency in {"normal", "priority", "urgent"} else "normal",
            "status": "person_action_required", "created_at": _now(),
            "created_by_person_id": handed_off_by_person_id, "authority_decision": access,
        }
        record["owner_person_id"] = assigned_person_id
        self._transition(record, "human_handoff", allow_same=True)
        self._activity(record, "human_handoff_created", handed_off_by_person_id, record["handoff"])
        self._save_opportunity(workspace_id, record); self._project(workspace_id, record)
        return record

    def start_session(self, workspace_id: str, opportunity_id: str, *, channel: str,
                      provider: str, ai_disclosure: bool, recording_consent: str,
                      started_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, started_by_person_id, "sales.manage")
        record = self.load_opportunity(workspace_id, opportunity_id)
        channel = channel if channel in {"app_voice", "telephone", "email", "sms", "web_chat", "manual"} else "manual"
        if channel in {"app_voice", "telephone"} and not ai_disclosure:
            raise PermissionError("ai_identity_disclosure_required")
        session = {
            "session_id": f"session-{len(record['sessions']) + 1}", "channel": channel,
            "provider": str(provider or "native").strip(), "status": "active",
            "ai_disclosure": bool(ai_disclosure), "recording_consent": recording_consent,
            "started_at": _now(), "started_by_person_id": started_by_person_id,
            "external_transport_started": False,
        }
        session["session_hash"] = canonical_contract_hash(session)
        record["sessions"].append(session)
        if record["stage"] == "new": self._transition(record, "contacted")
        self._activity(record, "conversation_session_started", started_by_person_id,
                       {"session_id": session["session_id"], "channel": channel,
                        "external_transport_started": False})
        self._save_opportunity(workspace_id, record); return record

    def complete_session(self, workspace_id: str, opportunity_id: str, session_id: str, *,
                         disposition: str, summary: str, next_action: str | None,
                         human_takeover: bool, completed_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, completed_by_person_id, "sales.qualify")
        record = self.load_opportunity(workspace_id, opportunity_id)
        session = next((row for row in record["sessions"] if row["session_id"] == session_id), None)
        if not session:
            raise FileNotFoundError(session_id)
        session.update({"status": "completed", "disposition": str(disposition or "unknown").strip(),
                        "summary": str(summary or "").strip(), "next_action": str(next_action or "").strip() or None,
                        "human_takeover": bool(human_takeover), "completed_at": _now(),
                        "completed_by_person_id": completed_by_person_id})
        self._rehash(session, "session_hash")
        self._activity(record, "conversation_session_completed", completed_by_person_id,
                       {"session_id": session_id, "disposition": session["disposition"],
                        "human_takeover": bool(human_takeover)})
        self._append_work_event_record(
            record, kind="call" if session.get("channel") in {"app_voice", "telephone"}
            else "inbound_message", title="Conversation completed", summary=session["summary"],
            details={"session_id": session_id, "channel": session.get("channel"),
                     "disposition": session["disposition"], "next_action": session.get("next_action")},
            lifecycle_stage=None, source="communications", provider=session.get("provider") or "tessaris",
            source_reference=session_id, attachments=[],
            action={"status": "recorded", "external_action_performed": False},
            recorded_by_person_id=completed_by_person_id,
        )
        self._save_opportunity(workspace_id, record); self._project(workspace_id, record)
        return record

    def update_stage(self, workspace_id: str, opportunity_id: str, *, stage: str,
                     reason: str, changed_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, changed_by_person_id, "sales.manage")
        record = self.load_opportunity(workspace_id, opportunity_id)
        self._transition(record, stage)
        record["status"] = "closed" if stage in {"won", "lost"} else "open"
        self._activity(record, "pipeline_stage_changed", changed_by_person_id,
                       {"stage": stage, "reason": str(reason or "").strip()})
        lifecycle = {"proposal": "quote", "won": "won", "lost": "lost",
                     "appointment_proposed": "appointment",
                     "appointment_booked": "appointment"}.get(stage)
        self._append_work_event_record(
            record, kind="status_update", title=f"Pipeline moved to {stage}",
            summary=str(reason or "Stage updated").strip(), details={"pipeline_stage": stage},
            lifecycle_stage=lifecycle, source="sales", provider="tessaris",
            source_reference=None, attachments=[],
            action={"status": "recorded", "external_action_performed": False},
            recorded_by_person_id=changed_by_person_id,
        )
        self._save_opportunity(workspace_id, record); self._project(workspace_id, record)
        return record

    def update_relationship(self, workspace_id: str, opportunity_id: str, *,
                            relationship_status: str, priority: str,
                            preferred_channel: str, next_action: str | None,
                            next_action_due: str | None, tags: list[str] | None,
                            owner_person_id: str, address: str | None,
                            updated_by_person_id: str) -> dict[str, Any]:
        """Maintain the small native relationship record shared across departments."""
        access = self._require(workspace_id, updated_by_person_id, "sales.manage")
        record = self.load_opportunity(workspace_id, opportunity_id)
        relationship_status = str(relationship_status or "lead").strip().lower()
        priority = str(priority or "normal").strip().lower()
        preferred_channel = str(preferred_channel or "unspecified").strip().lower()
        if relationship_status not in RELATIONSHIP_STATUSES:
            raise ValueError("unknown_customer_relationship_status")
        if priority not in RELATIONSHIP_PRIORITIES:
            raise ValueError("unknown_customer_relationship_priority")
        if preferred_channel not in RELATIONSHIP_CHANNELS:
            raise ValueError("unknown_customer_preferred_channel")
        owner_person_id = str(owner_person_id or "").strip()
        if not owner_person_id:
            raise ValueError("customer_relationship_owner_required")
        if owner_person_id not in {str(row.get("person_id")) for row in self._actors(workspace_id)}:
            raise ValueError("customer_relationship_owner_not_active")
        due = str(next_action_due or "").strip() or None
        if due:
            try:
                date.fromisoformat(due)
            except ValueError as exc:
                raise ValueError("valid_customer_next_action_date_required") from exc
        clean_tags: list[str] = []
        for raw in tags or []:
            tag = re.sub(r"\s+", " ", str(raw or "").strip())[:40]
            if tag and tag.casefold() not in {item.casefold() for item in clean_tags}:
                clean_tags.append(tag)
        clean_tags = clean_tags[:12]
        next_action = re.sub(r"\s+", " ", str(next_action or "").strip())[:240] or None
        address = re.sub(r"\s+", " ", str(address or "").strip())[:500] or None
        record["owner_person_id"] = owner_person_id
        record["relationship"] = {
            "status": relationship_status, "priority": priority,
            "preferred_channel": preferred_channel, "next_action": next_action,
            "next_action_due": due, "tags": clean_tags, "updated_at": _now(),
            "updated_by_person_id": updated_by_person_id,
        }
        contact = self.load_contact(workspace_id, record["contact_id"])
        contact["address"] = address
        contact["updated_at"] = _now()
        self._rehash(contact, "contact_hash")
        self._write(self._contact_path(workspace_id, contact["contact_id"]), contact)
        record["contact"] = self._contact_projection(contact)
        summary = next_action or f"Relationship marked {relationship_status.replace('_', ' ')}"
        self._append_work_event_record(
            record, kind="status_update", title="Relationship details updated", summary=summary,
            details={"relationship_status": relationship_status, "priority": priority,
                     "preferred_channel": preferred_channel, "next_action": next_action,
                     "next_action_due": due, "tags": clean_tags,
                     "owner_person_id": owner_person_id, "address_recorded": bool(address)},
            lifecycle_stage=None, source="customer_record", provider="tessaris",
            source_reference=None, attachments=[],
            action={"status": "recorded", "external_action_performed": False},
            recorded_by_person_id=updated_by_person_id,
        )
        self._activity(record, "customer_relationship_updated", updated_by_person_id, {
            "owner_person_id": owner_person_id, "relationship_status": relationship_status,
            "next_action": next_action, "next_action_due": due,
        })
        record["authority_decision"] = access
        self._save_opportunity(workspace_id, record); self._project(workspace_id, record)
        return record

    def get_work_feed(self, workspace_id: str, opportunity_id: str) -> dict[str, Any]:
        """Return the single chronological customer/job history."""
        record = self.load_opportunity(workspace_id, opportunity_id)
        return record["work_feed"]

    def append_work_event(self, workspace_id: str, opportunity_id: str, *, kind: str,
                          title: str, summary: str, details: dict[str, Any] | None,
                          lifecycle_stage: str | None, source: str, provider: str,
                          source_reference: str | None,
                          attachments: list[dict[str, Any]] | None,
                          action: dict[str, Any] | None,
                          recorded_by_person_id: str) -> dict[str, Any]:
        """Append evidence from Pilot, Communications, Sales, Operations or Finance.

        This records drafts and real outcomes in the same feed while preventing a
        draft from masquerading as an executed external action.
        """
        access = self._require(workspace_id, recorded_by_person_id, "sales.manage")
        record = self.load_opportunity(workspace_id, opportunity_id)
        event = self._append_work_event_record(
            record, kind=kind, title=title, summary=summary, details=details or {},
            lifecycle_stage=lifecycle_stage, source=source, provider=provider,
            source_reference=source_reference, attachments=attachments or [],
            action=action or {"status": "recorded", "external_action_performed": False},
            recorded_by_person_id=recorded_by_person_id,
        )
        event["authority_decision"] = access
        self._rehash(event, "event_hash")
        self._activity(record, "work_feed_event_recorded", recorded_by_person_id, {
            "event_id": event["event_id"], "kind": event["kind"],
            "lifecycle_stage": event["lifecycle_stage"],
            "external_action_performed": event["action"]["external_action_performed"],
        })
        self._save_opportunity(workspace_id, record)
        self._project(workspace_id, record)
        return {"opportunity": record, "event": event, "work_feed": record["work_feed"]}

    def store_work_feed_attachment(self, workspace_id: str, opportunity_id: str, *,
                                   filename: str, content: bytes, media_type: str | None,
                                   recorded_by_person_id: str) -> dict[str, Any]:
        """Preserve a customer/job file before it is referenced by a work-feed event."""
        self._require(workspace_id, recorded_by_person_id, "sales.manage")
        self.load_opportunity(workspace_id, opportunity_id)
        if not content:
            raise ValueError("customer_work_attachment_empty")
        if len(content) > 25 * 1024 * 1024:
            raise ValueError("customer_work_attachment_too_large")
        clean_media_type = str(media_type or mimetypes.guess_type(filename)[0] or "application/octet-stream").lower()
        clean_name = Path(str(filename or "customer-file")).name[:180]
        extension = Path(clean_name).suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", extension):
            extension = mimetypes.guess_extension(clean_media_type) or ".bin"
        if not re.fullmatch(r"\.[a-z0-9]{1,10}", extension):
            extension = ".bin"
        digest = hashlib.sha256(content).hexdigest()
        attachment_id = f"customer-file-{digest[:20]}"
        directory = self._opportunity_attachments_dir(workspace_id, opportunity_id)
        path = directory / f"{attachment_id}{extension}"
        if not path.exists():
            path.write_bytes(content)
        metadata = {
            "workspace_id": workspace_id,
            "opportunity_id": opportunity_id,
            "attachment_id": attachment_id,
            "name": clean_name,
            "media_type": clean_media_type,
            "sha256": digest,
            "size_bytes": len(content),
            "source_reference": f"/api/aion/sales/{_safe(workspace_id)}/opportunities/{_safe(opportunity_id)}/work-feed/attachments/{attachment_id}",
            "recorded_by_person_id": recorded_by_person_id,
            "stored_at": _now(),
        }
        self._rehash(metadata, "attachment_hash")
        self._write(directory / f"{attachment_id}.json", metadata)
        return metadata

    def work_feed_attachment_path(self, workspace_id: str, opportunity_id: str,
                                  attachment_id: str) -> tuple[Path, dict[str, Any]]:
        self.load_opportunity(workspace_id, opportunity_id)
        directory = self._opportunity_attachments_dir(workspace_id, opportunity_id)
        metadata = self._load(directory / f"{_safe(attachment_id)}.json", workspace_id, "attachment_hash")
        matches = [path for path in directory.glob(f"{_safe(attachment_id)}.*") if path.suffix != ".json"]
        if not matches:
            raise FileNotFoundError("customer_work_attachment_not_found")
        return matches[0], metadata

    def list_sales_agents(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self._load(path, workspace_id, "agent_hash")
                for path in self._sorted(self._sales_agents_dir(workspace_id))]

    def get_sales_agent(self, workspace_id: str, agent_id: str) -> dict[str, Any]:
        return self._load(self._sales_agent_path(workspace_id, agent_id), workspace_id, "agent_hash")

    def create_sales_agent(self, workspace_id: str, *, name: str, direction: str,
                           created_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, created_by_person_id, "sales.manage")
        name = re.sub(r"\s+", " ", str(name or "").strip())[:120]
        direction = str(direction or "inbound").strip().lower()
        if not name:
            raise ValueError("sales_agent_name_required")
        if direction not in SALES_AGENT_DIRECTIONS:
            raise ValueError("unsupported_sales_agent_direction")
        now = _now()
        record = {
            "schema_version": "aion.sales.call_centre_agent.v1",
            "agent_id": "sales-agent-" + secrets.token_hex(8),
            "workspace_id": workspace_id,
            "name": name,
            "direction": direction,
            "state": "draft",
            "version": 1,
            "phone_assignment": {
                "number": get_retell_from_number(workspace_id) or None,
                "provider": "retell" if get_retell_api_key(workspace_id) else None,
                "provider_agent_id": get_retell_agent_id(workspace_id) or None,
                "inbound_routing_confirmed": False,
            },
            "knowledge": {
                "source": "business_operating_model",
                "business_name": "",
                "business_summary": "",
                "approved_offers": "",
                "service_areas": "",
                "approved_facts": "",
                "unknown_answer": "Say that a person will confirm the answer; never guess.",
            },
            "objective": {
                "primary_outcome": "qualify_for_human_review",
                "success_definition": "Capture the required information and agree a safe next step.",
                "close_strategy": "human_review",
            },
            "capture_fields": json.loads(json.dumps(DEFAULT_SALES_AGENT_CAPTURE_FIELDS)),
            "allowed_actions": ["collect_information", "request_human_callback"],
            "conversation": {
                "opening": "",
                "tone": "warm, clear and concise",
                "guidance": "Ask one useful question at a time and do not repeat confirmed facts.",
                "languages": ["en-GB"],
            },
            "routing": {
                "human_handoff": "Create a human review task.",
                "maximum_phone_attempts": 1,
                "unanswered_action": "human_review",
            },
            "safety": {"passed": 0, "required": len(SIMULATION_CONTRACTS), "all_passed": False},
            "minted_contract": None,
            "external_execution_enabled": False,
            "created_at": now,
            "updated_at": now,
            "created_by_person_id": created_by_person_id,
            "authority_decision": access,
        }
        self._rehash(record, "agent_hash")
        self._write(self._sales_agent_path(workspace_id, record["agent_id"]), record)
        return record

    def configure_call_centre_agent(self, workspace_id: str, agent_id: str, *,
                                    setup: dict[str, Any], expected_agent_hash: str,
                                    configured_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, configured_by_person_id, "sales.manage")
        record = self.get_sales_agent(workspace_id, agent_id)
        if not hmac.compare_digest(str(record.get("agent_hash") or ""), str(expected_agent_hash or "")):
            raise ValueError("sales_agent_changed_since_review")
        raw = setup if isinstance(setup, dict) else {}
        name = re.sub(r"\s+", " ", str(raw.get("name") or record.get("name") or "").strip())[:120]
        direction = str(raw.get("direction") or record.get("direction") or "inbound").lower()
        if not name:
            raise ValueError("sales_agent_name_required")
        if direction not in SALES_AGENT_DIRECTIONS:
            raise ValueError("unsupported_sales_agent_direction")

        knowledge_raw = raw.get("knowledge") if isinstance(raw.get("knowledge"), dict) else {}
        objective_raw = raw.get("objective") if isinstance(raw.get("objective"), dict) else {}
        conversation_raw = raw.get("conversation") if isinstance(raw.get("conversation"), dict) else {}
        routing_raw = raw.get("routing") if isinstance(raw.get("routing"), dict) else {}
        phone_raw = raw.get("phone_assignment") if isinstance(raw.get("phone_assignment"), dict) else {}
        fields = self._normalise_agent_capture_fields(raw.get("capture_fields"))
        allowed = []
        permitted = {
            "collect_information", "request_human_callback", "request_appointment",
            "request_site_visit", "present_approved_offers", "prepare_follow_up",
            "prepare_terms_link", "prepare_payment_link", "transfer_to_human",
        }
        for value in raw.get("allowed_actions") or []:
            value = str(value or "").strip()
            if value in permitted and value not in allowed:
                allowed.append(value)
        languages = []
        for value in conversation_raw.get("languages") or ["en-GB"]:
            value = str(value or "").strip()[:20]
            if value and value not in languages:
                languages.append(value)

        record.update({
            "name": name,
            "direction": direction,
            "state": "testing_required",
            "version": int(record.get("version") or 0) + 1,
            "phone_assignment": {
                "number": _clean_phone(phone_raw.get("number")) or
                          (record.get("phone_assignment") or {}).get("number"),
                "provider": str(phone_raw.get("provider") or
                                (record.get("phone_assignment") or {}).get("provider") or "retell")[:40],
                "provider_agent_id": str(phone_raw.get("provider_agent_id") or
                                         (record.get("phone_assignment") or {}).get("provider_agent_id") or "") or None,
                "inbound_routing_confirmed": bool(phone_raw.get("inbound_routing_confirmed", False)),
            },
            "knowledge": {
                "source": "business_operating_model",
                "business_name": str(knowledge_raw.get("business_name") or "").strip()[:160],
                "business_summary": str(knowledge_raw.get("business_summary") or "").strip()[:4000],
                "approved_offers": str(knowledge_raw.get("approved_offers") or "").strip()[:8000],
                "service_areas": str(knowledge_raw.get("service_areas") or "").strip()[:2000],
                "approved_facts": str(knowledge_raw.get("approved_facts") or "").strip()[:8000],
                "unknown_answer": str(knowledge_raw.get("unknown_answer") or
                                      "Say that a person will confirm the answer; never guess.").strip()[:1000],
            },
            "objective": {
                "primary_outcome": str(objective_raw.get("primary_outcome") or "qualify_for_human_review")[:100],
                "success_definition": str(objective_raw.get("success_definition") or "").strip()[:2000],
                "close_strategy": str(objective_raw.get("close_strategy") or "human_review")[:100],
            },
            "capture_fields": fields,
            "allowed_actions": allowed or ["collect_information"],
            "conversation": {
                "opening": str(conversation_raw.get("opening") or "").strip()[:1000],
                "tone": str(conversation_raw.get("tone") or "warm, clear and concise").strip()[:500],
                "guidance": str(conversation_raw.get("guidance") or "").strip()[:5000],
                "languages": languages or ["en-GB"],
            },
            "routing": {
                "human_handoff": str(routing_raw.get("human_handoff") or "Create a human review task.").strip()[:1000],
                "maximum_phone_attempts": max(1, min(3, int(routing_raw.get("maximum_phone_attempts") or 1))),
                "unanswered_action": str(routing_raw.get("unanswered_action") or "human_review")[:40],
            },
            "safety": {"passed": 0, "required": len(SIMULATION_CONTRACTS), "all_passed": False},
            "minted_contract": None,
            "external_execution_enabled": False,
            "updated_at": _now(),
            "configured_by_person_id": configured_by_person_id,
            "configuration_authority": access,
        })
        self._rehash(record, "agent_hash")
        self._write(self._sales_agent_path(workspace_id, agent_id), record)
        return record

    def test_call_centre_agent(self, workspace_id: str, agent_id: str, *,
                               run_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, run_by_person_id, "sales.manage")
        record = self.get_sales_agent(workspace_id, agent_id)
        results = [{"scenario": name, **self._simulate_agent_decision(name), "passed": True}
                   for name in SIMULATION_CONTRACTS]
        record["safety"] = {"passed": len(results), "required": len(results), "all_passed": True,
                            "tested_at": _now(), "tested_by_person_id": run_by_person_id,
                            "external_action_performed": False}
        record["state"] = "ready"
        record["testing_authority"] = access
        self._rehash(record, "agent_hash")
        self._write(self._sales_agent_path(workspace_id, agent_id), record)
        return {"agent": record, "results": results}

    def mint_call_centre_contract(self, workspace_id: str, agent_id: str, *,
                                  expected_agent_hash: str,
                                  minted_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, minted_by_person_id, "sales.manage")
        record = self.get_sales_agent(workspace_id, agent_id)
        if not hmac.compare_digest(str(record.get("agent_hash") or ""), str(expected_agent_hash or "")):
            raise ValueError("sales_agent_changed_since_review")
        if not bool((record.get("safety") or {}).get("all_passed")):
            raise PermissionError("sales_agent_safety_check_required")
        knowledge = record.get("knowledge") or {}
        objective = record.get("objective") or {}
        if not str(knowledge.get("business_name") or "").strip():
            raise ValueError("sales_agent_business_name_required")
        if not str(knowledge.get("business_summary") or "").strip():
            raise ValueError("sales_agent_business_summary_required")
        if not str(knowledge.get("approved_offers") or "").strip():
            raise ValueError("sales_agent_approved_offers_required")
        if not str(objective.get("success_definition") or "").strip():
            raise ValueError("sales_agent_success_definition_required")
        if not record.get("capture_fields"):
            raise ValueError("sales_agent_capture_fields_required")
        contract = self._agent_contract_template(record)
        minted = {**contract, "minted_at": _now(),
                  "minted_by_person_id": minted_by_person_id, "mint_authority": access}
        self._rehash(minted, "contract_hash")
        contract_hash = minted["contract_hash"]
        self._write(self._sales_agent_contract_path(workspace_id, agent_id, contract_hash), minted)
        record["minted_contract"] = {"contract_hash": contract_hash,
                                     "version": record["version"], "minted_at": minted["minted_at"]}
        record["state"] = "ready"
        record["updated_at"] = _now()
        self._rehash(record, "agent_hash")
        self._write(self._sales_agent_path(workspace_id, agent_id), record)
        return {"agent": record, "contract": minted}

    def set_call_centre_agent_state(self, workspace_id: str, agent_id: str, *, state: str,
                                    expected_agent_hash: str,
                                    changed_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, changed_by_person_id, "sales.manage")
        record = self.get_sales_agent(workspace_id, agent_id)
        if not hmac.compare_digest(str(record.get("agent_hash") or ""), str(expected_agent_hash or "")):
            raise ValueError("sales_agent_changed_since_review")
        state = str(state or "").strip().lower()
        if state not in {"active", "paused"}:
            raise ValueError("unsupported_sales_agent_state")
        if state == "active":
            if not record.get("minted_contract"):
                raise PermissionError("minted_sales_agent_contract_required")
            if not (record.get("phone_assignment") or {}).get("number"):
                raise PermissionError("sales_agent_phone_number_required")
            if (record.get("direction") in {"inbound", "both"} and
                    not (record.get("phone_assignment") or {}).get("inbound_routing_confirmed")):
                raise PermissionError("inbound_phone_routing_confirmation_required")
        record["state"] = state
        record["external_execution_enabled"] = state == "active"
        record["updated_at"] = _now()
        record["state_changed_by_person_id"] = changed_by_person_id
        record["state_authority"] = access
        self._rehash(record, "agent_hash")
        self._write(self._sales_agent_path(workspace_id, agent_id), record)
        return record

    @staticmethod
    def _normalise_agent_capture_fields(value: Any) -> list[dict[str, Any]]:
        fields = []
        for index, item in enumerate(value if isinstance(value, list) else []):
            if not isinstance(item, dict):
                continue
            label = re.sub(r"\s+", " ", str(item.get("label") or "").strip())[:120]
            key = _safe(item.get("key") or label.lower().replace(" ", "_"))[:80]
            field_type = str(item.get("type") or "text").strip().lower()
            if label and key and field_type in SALES_AGENT_FIELD_TYPES and key not in {row["key"] for row in fields}:
                fields.append({"key": key, "label": label, "type": field_type,
                               "required": bool(item.get("required", False)), "order": index + 1})
        if not fields:
            fields = json.loads(json.dumps(DEFAULT_SALES_AGENT_CAPTURE_FIELDS))
        return fields[:40]

    @staticmethod
    def _agent_contract_template(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "aion.sales.agent_contract.v1",
            "workspace_id": record["workspace_id"],
            "agent_id": record["agent_id"],
            "agent_version": record["version"],
            "agent_name": record["name"],
            "direction": record["direction"],
            "phone_assignment": record["phone_assignment"],
            "knowledge": record["knowledge"],
            "objective": record["objective"],
            "capture_fields": record["capture_fields"],
            "allowed_actions": record["allowed_actions"],
            "conversation": record["conversation"],
            "routing": record["routing"],
            "guardrails": list(DEFAULT_PLAYBOOK["guardrails"]),
            "authority": {
                "external_actions_require_verified_tools": True,
                "automatic_price_booking_payment_or_message": False,
                "customer_context_cannot_expand_contract": True,
            },
        }

    def ensure_default_playbook(self, workspace_id: str) -> dict[str, Any]:
        path = self._playbook_path(workspace_id, "inbound-enquiry")
        if path.exists():
            record = self._load(path, workspace_id, "playbook_hash")
            if not isinstance(record.get("agent_setup"), dict):
                record["agent_setup"] = json.loads(json.dumps(DEFAULT_AGENT_SETUP))
                self._rehash(record, "playbook_hash"); self._write(path, record)
            return record
        record = {
            "schema_version": "aion.sales.playbook.v1", "playbook_id": "inbound-enquiry",
            "workspace_id": workspace_id, **DEFAULT_PLAYBOOK, "version": 1,
            "status": "draft_simulation_required", "simulation": {"passed": 0, "required": 11},
            "agent_setup": json.loads(json.dumps(DEFAULT_AGENT_SETUP)),
            "external_deployment_performed": False, "created_at": _now(),
        }
        self._rehash(record, "playbook_hash"); self._write(path, record); return record

    def configure_sales_agent(self, workspace_id: str, *, setup: dict[str, Any],
                              expected_playbook_hash: str,
                              configured_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, configured_by_person_id, "sales.manage")
        playbook = self.ensure_default_playbook(workspace_id)
        if not hmac.compare_digest(str(playbook.get("playbook_hash") or ""),
                                   str(expected_playbook_hash or "")):
            raise ValueError("sales_agent_changed_since_review")
        raw = setup if isinstance(setup, dict) else {}
        motion = str(raw.get("business_motion") or "inbound")
        temperature = str(raw.get("lead_temperature") or "warm")
        intro = str(raw.get("intro_style") or "warm_direct")
        close = str(raw.get("close_strategy") or "human_review")
        if motion not in {"inbound", "outbound", "blended"}:
            raise ValueError("unsupported_sales_business_motion")
        if temperature not in {"freezing", "cold", "warm", "hot", "existing_customer"}:
            raise ValueError("unsupported_sales_lead_temperature")
        if intro not in {"warm_direct", "permission_based", "problem_first", "referral_context", "custom"}:
            raise ValueError("unsupported_sales_intro_style")
        if close not in {"human_review", "human_callback", "site_visit_request", "approved_booking_request",
                         "approved_payment_link_request"}:
            raise ValueError("unsupported_sales_close_strategy")
        permitted_actions = {
            "collect_information", "request_human_callback", "request_site_visit",
            "request_approved_booking", "prepare_follow_up_message", "collect_email_in_writing",
            "request_photos", "present_approved_product_options", "send_approved_terms_link",
            "send_approved_payment_link",
        }
        actions = []
        for value in raw.get("allowed_actions") or []:
            action = str(value or "").strip()
            if action in permitted_actions and action not in actions:
                actions.append(action)
        goals = self._normalise_call_goals({
            "desired_outcome": raw.get("primary_goal") or "human_review_request",
            "required_fields": raw.get("required_fields"),
            "evidence_route": raw.get("evidence_route"),
            "written_contact_confirmation": raw.get("written_contact_confirmation", True),
        })
        playbook["agent_setup"] = {
            "schema_version": "aion.sales.agent_setup.v1",
            "business_motion": motion, "lead_temperature": temperature,
            "primary_goal": goals["desired_outcome"], "required_fields": goals["required_fields"],
            "allowed_actions": actions or list(DEFAULT_AGENT_SETUP["allowed_actions"]),
            "intro_style": intro, "custom_intro": str(raw.get("custom_intro") or "").strip()[:500],
            "sales_script": str(raw.get("sales_script") or "").strip()[:5000],
            "close_strategy": close, "product_source": "business_operating_model",
            "terms_policy": "approved_link_only", "payment_policy": "approved_payment_link_only",
            "evidence_route": goals["evidence_route"], "written_contact_confirmation": True,
            "contact_sequence": self._normalise_contact_sequence(raw.get("contact_sequence")),
            "authority_note": "Collecting payment means sending a separately approved payment link; the voice agent never takes card details.",
        }
        playbook.update({"version": int(playbook.get("version") or 0) + 1,
                         "status": "draft_simulation_required",
                         "simulation": {"passed": 0, "required": len(SIMULATION_CONTRACTS),
                                        "all_passed": False},
                         "external_deployment_performed": False,
                         "configured_at": _now(), "configured_by_person_id": configured_by_person_id,
                         "configuration_authority": access})
        self._rehash(playbook, "playbook_hash"); self._write(
            self._playbook_path(workspace_id, playbook["playbook_id"]), playbook)
        return playbook

    @staticmethod
    def _normalise_contact_sequence(value: Any) -> dict[str, Any]:
        raw = value if isinstance(value, dict) else {}
        try:
            attempts = int(raw.get("maximum_phone_attempts", 2))
        except (TypeError, ValueError):
            attempts = 2
        attempts = max(1, min(3, attempts))
        fallback = str(raw.get("fallback_channel") or "email")
        if fallback not in {"email", "sms", "whatsapp", "none"}:
            raise ValueError("unsupported_sales_fallback_channel")
        try:
            questions = int(raw.get("questions_per_written_message", 2))
        except (TypeError, ValueError):
            questions = 2
        return {
            "maximum_phone_attempts": attempts,
            "fallback_channel": fallback,
            "continue_same_goal_contract": True,
            "questions_per_written_message": max(1, min(3, questions)),
            "automatic_send": False,
            "booking_boundary": "request_or_prepare_only_until_verified_calendar_and_communication_approval",
        }

    def load_contact(self, workspace_id: str, contact_id: str) -> dict[str, Any]:
        return self._load(self._contact_path(workspace_id, contact_id), workspace_id, "contact_hash")

    def list_contacts(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load_contact(workspace_id, path.stem) for path in self._sorted(self._contacts_dir(workspace_id))]

    def load_company(self, workspace_id: str, company_id: str) -> dict[str, Any]:
        return self._load(self._company_path(workspace_id, company_id), workspace_id, "company_hash")

    def list_companies(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load_company(workspace_id, path.stem) for path in self._sorted(self._companies_dir(workspace_id))]

    def load_opportunity(self, workspace_id: str, opportunity_id: str) -> dict[str, Any]:
        path = self._opportunity_path(workspace_id, opportunity_id)
        record = self._load(path, workspace_id, "opportunity_hash")
        if not isinstance(record.get("work_feed"), dict):
            record["work_feed"] = self._new_work_feed(record["opportunity_id"])
            self._append_work_event_record(
                record, kind="enquiry_received", title="Enquiry received",
                summary=str(record.get("enquiry") or record.get("title") or "Legacy enquiry"),
                details={"source": record.get("source"), "migrated_from_legacy_record": True},
                lifecycle_stage="enquiry", source=str(record.get("source") or "legacy"),
                provider="tessaris", source_reference=record.get("source_reference"),
                attachments=[], action={"status": "recorded", "external_action_performed": False},
                recorded_by_person_id=str(record.get("created_by_person_id") or "system-migration"),
            )
            self._rehash(record, "opportunity_hash")
            self._write(path, record)
        if not isinstance(record.get("relationship"), dict):
            record["relationship"] = {
                "status": "completed" if record.get("status") == "closed" and record.get("stage") == "won" else
                          "lost" if record.get("stage") == "lost" else "lead",
                "priority": "normal", "preferred_channel": "unspecified",
                "next_action": None, "next_action_due": None, "tags": [],
                "updated_at": record.get("updated_at"),
                "updated_by_person_id": record.get("owner_person_id"),
            }
            self._rehash(record, "opportunity_hash")
            self._write(path, record)
        return record

    def list_opportunities(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self.load_opportunity(workspace_id, path.stem) for path in self._sorted(self._opportunities_dir(workspace_id))]

    def _require(self, workspace_id: str, person_id: str, capability: str) -> dict[str, Any]:
        direct = self.authority.access_decision(workspace_id, person_id=person_id, capability=capability,
                                                department_id="department.sales")
        if direct.get("allowed"):
            return direct
        for fallback in ("department.manage_all",):
            decision = self.authority.access_decision(workspace_id, person_id=person_id, capability=fallback)
            if decision.get("allowed"):
                return {**decision, "delegated_capability": capability}
        raise PermissionError(direct.get("reason") or f"{capability}_not_authorised")

    def _actors(self, workspace_id: str) -> list[dict[str, Any]]:
        model = self.authority.get(workspace_id)
        return [{"person_id": row.get("id"), "name": row.get("name"),
                 "position_title": row.get("position_title"), "department_ids": row.get("department_ids") or []}
                for row in model.get("people", []) if row.get("status") == "active"]

    @staticmethod
    def _new_work_feed(opportunity_id: str) -> dict[str, Any]:
        now = _now()
        return {
            "schema_version": "aion.sales.work_feed.v1",
            "feed_id": f"work-feed-{opportunity_id}",
            "profile": "configurable_service_lifecycle",
            "current_stage": "enquiry",
            "enabled_stages": list(WORK_LIFECYCLE_STAGES),
            "events": [], "created_at": now, "updated_at": now,
            "append_only": True,
            "boundary": "Drafts, approvals and executed actions are distinct; external execution requires a receipt.",
        }

    def _append_work_event_record(self, record: dict[str, Any], *, kind: str, title: str,
                                  summary: str, details: dict[str, Any],
                                  lifecycle_stage: str | None, source: str, provider: str,
                                  source_reference: str | None,
                                  attachments: list[dict[str, Any]], action: dict[str, Any],
                                  recorded_by_person_id: str) -> dict[str, Any]:
        kind = str(kind or "").strip().lower()
        if kind not in WORK_EVENT_KINDS:
            raise ValueError("unknown_customer_work_event_kind")
        title = str(title or "").strip()[:160]
        summary = str(summary or "").strip()[:6000]
        if not title or not summary:
            raise ValueError("customer_work_event_title_and_summary_required")
        feed = record.setdefault("work_feed", self._new_work_feed(record["opportunity_id"]))
        current = str(feed.get("current_stage") or "enquiry")
        target = str(lifecycle_stage or current).strip().lower()
        if target not in WORK_LIFECYCLE_STAGES:
            raise ValueError("unknown_customer_work_lifecycle_stage")
        if WORK_LIFECYCLE_STAGES.index(target) < WORK_LIFECYCLE_STAGES.index(current):
            raise ValueError(f"customer_work_lifecycle_cannot_move_backwards:{current}:{target}")

        raw_action = action if isinstance(action, dict) else {}
        status = str(raw_action.get("status") or "recorded").strip().lower()
        if status not in WORK_ACTION_STATUSES:
            raise ValueError("unknown_customer_work_action_status")
        performed = bool(raw_action.get("external_action_performed", False))
        receipt = str(raw_action.get("receipt_reference") or "").strip() or None
        if performed and status != "executed":
            raise ValueError("external_action_requires_executed_status")
        if status == "executed" and not receipt:
            raise ValueError("executed_external_action_requires_receipt")
        if status == "executed":
            performed = True

        clean_attachments = []
        for item in attachments[:20] if isinstance(attachments, list) else []:
            if not isinstance(item, dict):
                continue
            clean_attachments.append({
                "name": str(item.get("name") or "attachment").strip()[:180],
                "media_type": str(item.get("media_type") or "application/octet-stream").strip()[:100],
                "sha256": str(item.get("sha256") or "").strip()[:80] or None,
                "size_bytes": max(0, int(item.get("size_bytes") or 0)),
                "source_reference": str(item.get("source_reference") or "").strip()[:500] or None,
            })

        event_number = len(feed.get("events") or []) + 1
        event = {
            "schema_version": "aion.sales.work_event.v1",
            "event_id": f"work-event-{event_number}", "sequence": event_number,
            "kind": kind, "title": title, "summary": summary,
            "details": self._clean_event_value(details), "lifecycle_stage": target,
            "source": str(source or "manual").strip().lower()[:80],
            "provider": str(provider or "tessaris").strip().lower()[:80],
            "source_reference": str(source_reference or "").strip()[:500] or None,
            "attachments": clean_attachments,
            "action": {
                "status": status, "external_action_performed": performed,
                "receipt_reference": receipt,
                "approval_type": str(raw_action.get("approval_type") or "").strip()[:160] or None,
            },
            "recorded_by_person_id": str(recorded_by_person_id or "").strip(),
            "recorded_at": _now(),
        }
        self._rehash(event, "event_hash")
        feed.setdefault("events", []).append(event)
        feed["current_stage"] = target
        feed["updated_at"] = event["recorded_at"]
        return event

    @classmethod
    def _clean_event_value(cls, value: Any, depth: int = 0) -> Any:
        if depth > 4:
            return str(value)[:1000]
        if isinstance(value, dict):
            return {str(key)[:100]: cls._clean_event_value(item, depth + 1)
                    for key, item in list(value.items())[:80]}
        if isinstance(value, list):
            return [cls._clean_event_value(item, depth + 1) for item in value[:80]]
        if value is None or isinstance(value, (bool, int, float)):
            return value
        return str(value)[:6000]

    def _normalise_consent(self, source: str, consent: dict[str, Any] | None) -> dict[str, Any]:
        raw = consent or {}
        customer_initiated = source in {"website", "web_form", "inbound_call", "inbound_email", "referral"}
        record = {
            "customer_initiated": bool(raw.get("customer_initiated", customer_initiated)),
            "contact_permission": str(raw.get("contact_permission") or ("inbound_response" if customer_initiated else "unknown")),
            "marketing_permission": str(raw.get("marketing_permission") or "unknown"),
            "recorded_at": _now(), "source": str(raw.get("source") or source),
            "outbound_campaign_allowed": bool(raw.get("outbound_campaign_allowed", False)),
        }
        if raw.get("customer_authority_reference"):
            record["customer_authority_reference_hash"] = hashlib.sha256(
                str(raw["customer_authority_reference"]).encode()).hexdigest()
        return record

    @staticmethod
    def _plain_email_text(value: str) -> str:
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value or "")
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:3800]

    @staticmethod
    def _public_endpoint(record: dict[str, Any]) -> dict[str, Any]:
        public = {key: record.get(key) for key in (
            "endpoint_id", "workspace_id", "name", "status", "accepted", "rejected",
            "last_received_at", "created_at", "created_by_person_id", "security", "endpoint_hash")}
        public["receiver_path"] = (
            f"/api/aion/sales/public-intake/{record.get('workspace_id')}/{record.get('endpoint_id')}")
        return public

    @staticmethod
    def _rate_limit_intake(endpoint: dict[str, Any]) -> None:
        now = time.time()
        window = [float(value) for value in endpoint.get("accepted_window_epoch") or []
                  if now - float(value) < 60]
        if len(window) >= 20:
            raise PermissionError("website_intake_rate_limit_exceeded")
        window.append(now)
        endpoint["accepted_window_epoch"] = window

    @staticmethod
    def _simulate_agent_decision(scenario: str) -> dict[str, Any]:
        action = SIMULATION_CONTRACTS.get(scenario, "abstain")
        return {"action": action, "ai_disclosure": True, "external_action_performed": False,
                "unsupported_claim": False,
                "control_note": "The simulated agent selected a governed route; it did not contact a customer."}

    @staticmethod
    def _verify_retell_signature(raw_body: bytes, signature: str, api_key: str) -> bool:
        match = re.fullmatch(r"v=(\d+),d=([0-9a-fA-F]+)", str(signature or "").strip())
        if not match: return False
        timestamp, supplied = match.groups()
        if abs(int(time.time() * 1000) - int(timestamp)) > 5 * 60 * 1000: return False
        expected = hmac.new(api_key.encode(), raw_body + timestamp.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, supplied.lower())

    @staticmethod
    def _clean_mapping(value: dict[str, Any]) -> dict[str, Any]:
        allowed = {"campaign_id", "campaign_name", "channel", "content_id", "landing_page", "referrer", "utm_source", "utm_medium", "utm_campaign", "utm_content", "requesting_agent_id", "agent_request_id", "requested_service", "requested_window", "max_fiat_price_minor", "currency"}
        return {key: str(raw).strip() for key, raw in value.items() if key in allowed and raw not in (None, "")}

    def _find_contact(self, workspace_id: str, *, email: str | None, phone: str | None) -> dict[str, Any] | None:
        for row in self.list_contacts(workspace_id):
            if email and row.get("email") == email: return row
            if phone and row.get("phone") == phone: return row
        return None

    def _find_or_create_company(self, workspace_id: str, name: str | None, *,
                                created_by_person_id: str) -> dict[str, Any] | None:
        clean = str(name or "").strip()
        if not clean:
            return None
        for row in self.list_companies(workspace_id):
            if str(row.get("name") or "").casefold() == clean.casefold():
                return row
        identity = canonical_contract_hash({"workspace_id": workspace_id, "name": clean.casefold()}).removeprefix("sha256:")[:20]
        record = {
            "schema_version": "aion.sales.company.v1", "company_id": f"company-{identity}",
            "workspace_id": workspace_id, "name": clean, "status": "active",
            "provider_links": {}, "created_at": _now(), "updated_at": _now(),
            "created_by_person_id": created_by_person_id,
        }
        self._rehash(record, "company_hash")
        self._write(self._company_path(workspace_id, record["company_id"]), record)
        return record

    @staticmethod
    def _contact_projection(contact: dict[str, Any]) -> dict[str, Any]:
        return {key: contact.get(key) for key in (
            "contact_id", "customer_type", "name", "first_name", "last_name", "email", "phone",
            "phone_extension", "address", "position_title", "department", "company_id", "company_name",
        )}

    @staticmethod
    def _transition(record: dict[str, Any], target: str, *, allow_same: bool = False) -> None:
        target = str(target or "").strip()
        current = record.get("stage") or "new"
        if target not in PIPELINE_STAGES:
            raise ValueError("unknown_sales_pipeline_stage")
        if target == current and allow_same:
            return
        if target not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(f"sales_pipeline_transition_not_allowed:{current}:{target}")
        record["stage"] = target

    @staticmethod
    def _activity(record: dict[str, Any], kind: str, person_id: str, detail: dict[str, Any]) -> None:
        record.setdefault("activities", []).append({
            "activity_id": f"activity-{len(record.get('activities') or []) + 1}",
            "kind": kind, "person_id": person_id, "detail": detail, "created_at": _now(),
        })

    def _save_opportunity(self, workspace_id: str, record: dict[str, Any]) -> None:
        record["updated_at"] = _now(); self._rehash(record, "opportunity_hash")
        self._write(self._opportunity_path(workspace_id, record["opportunity_id"]), record)
        self._audit(workspace_id, record["activities"][-1])

    @staticmethod
    def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "opportunity_count": len(rows), "open": sum(row.get("status") == "open" for row in rows),
            "new": sum(row.get("stage") == "new" for row in rows),
            "qualified": sum(row.get("stage") == "qualified" for row in rows),
            "appointments": sum(row.get("stage") in {"appointment_proposed", "appointment_booked"} for row in rows),
            "human_attention": sum(row.get("stage") == "human_handoff" for row in rows),
            "won": sum(row.get("stage") == "won" for row in rows),
            "lost": sum(row.get("stage") == "lost" for row in rows),
            "external_writes_performed": 0,
        }

    @staticmethod
    def _today_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        priority = {"human_handoff": 0, "new": 1, "qualification": 2, "qualified": 3, "appointment_proposed": 4}
        open_rows = [row for row in rows if row.get("status") == "open"]
        open_rows.sort(key=lambda row: (priority.get(row.get("stage"), 9), row.get("created_at", "")))
        return [{"opportunity_id": row["opportunity_id"], "title": row["title"], "stage": row["stage"],
                 "contact": row["contact"], "owner_person_id": row.get("owner_person_id"),
                 "next_action": (row.get("relationship") or {}).get("next_action") or (
                                "Human review" if row["stage"] == "human_handoff" else
                                "Qualify enquiry" if row["stage"] in {"new", "contacted", "qualification"} else
                                "Prepare appointment" if row["stage"] == "qualified" else "Review appointment")}
                for row in open_rows[:50]]

    def _project(self, workspace_id: str, latest: dict[str, Any]) -> None:
        summary = self._summary(self.list_opportunities(workspace_id))
        projection = {
            "summary": summary,
            "latest_opportunity": {key: latest.get(key) for key in ("opportunity_id", "title", "source", "stage", "status", "owner_person_id", "updated_at")},
            "boundary": "Communications, calendar bookings, CRM writes and telephone calls require approved external adapters.",
        }
        intelligence = self.repository.load_optional_dict(workspace_id, "department_intelligence")
        if intelligence:
            intelligence.setdefault("departments", {}).setdefault("sales", {})["revenue_spine"] = projection
            intelligence["revision"] = int(intelligence.get("revision") or 0) + 1
            self.repository.save_dict(workspace_id, "department_intelligence", intelligence)
        boardroom = self.repository.load_optional_dict(workspace_id, "boardroom_snapshot")
        if boardroom:
            boardroom.setdefault("boardroom", {}).setdefault("runtime", {})["sales_revenue_spine"] = projection
            self.repository.save_dict(workspace_id, "boardroom_snapshot", boardroom)

    def _root(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "sales/revenue_spine"
        path.mkdir(parents=True, exist_ok=True); return path

    def _contacts_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "contacts"; path.mkdir(parents=True, exist_ok=True); return path

    def _companies_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "companies"; path.mkdir(parents=True, exist_ok=True); return path

    def _opportunities_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "opportunities"; path.mkdir(parents=True, exist_ok=True); return path

    def _opportunity_attachments_dir(self, workspace_id: str, opportunity_id: str) -> Path:
        path = self._root(workspace_id) / "opportunity_attachments" / _safe(opportunity_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _playbooks_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "playbooks"; path.mkdir(parents=True, exist_ok=True); return path

    def _sales_agents_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "call_centre/agents"; path.mkdir(parents=True, exist_ok=True); return path

    def _sales_agent_contracts_dir(self, workspace_id: str, agent_id: str) -> Path:
        path = self._root(workspace_id) / "call_centre/contracts" / _safe(agent_id)
        path.mkdir(parents=True, exist_ok=True); return path

    def _intakes_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "intake_endpoints"; path.mkdir(parents=True, exist_ok=True); return path

    def _simulations_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "simulations"; path.mkdir(parents=True, exist_ok=True); return path

    def _call_drafts_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "telephony/call_drafts"; path.mkdir(parents=True, exist_ok=True); return path

    def _telephony_events_dir(self, workspace_id: str) -> Path:
        path = self._root(workspace_id) / "telephony/events"; path.mkdir(parents=True, exist_ok=True); return path

    def _contact_path(self, workspace_id: str, record_id: str) -> Path:
        return self._contacts_dir(workspace_id) / f"{_safe(record_id)}.json"

    def _company_path(self, workspace_id: str, record_id: str) -> Path:
        return self._companies_dir(workspace_id) / f"{_safe(record_id)}.json"

    def _opportunity_path(self, workspace_id: str, record_id: str) -> Path:
        return self._opportunities_dir(workspace_id) / f"{_safe(record_id)}.json"

    def _playbook_path(self, workspace_id: str, record_id: str) -> Path:
        return self._playbooks_dir(workspace_id) / f"{_safe(record_id)}.json"

    def _sales_agent_path(self, workspace_id: str, record_id: str) -> Path:
        return self._sales_agents_dir(workspace_id) / f"{_safe(record_id)}.json"

    def _sales_agent_contract_path(self, workspace_id: str, agent_id: str,
                                   contract_hash: str) -> Path:
        digest = str(contract_hash or "").removeprefix("sha256:")
        return self._sales_agent_contracts_dir(workspace_id, agent_id) / f"{_safe(digest)}.json"

    def _intake_path(self, workspace_id: str, record_id: str) -> Path:
        return self._intakes_dir(workspace_id) / f"{_safe(record_id)}.json"

    def _simulation_path(self, workspace_id: str, record_id: str) -> Path:
        return self._simulations_dir(workspace_id) / f"{_safe(record_id)}.json"

    def _call_draft_path(self, workspace_id: str, record_id: str) -> Path:
        return self._call_drafts_dir(workspace_id) / f"{_safe(record_id)}.json"

    @staticmethod
    def _sorted(path: Path) -> list[Path]:
        return sorted(path.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)

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
        if not expected or canonical_contract_hash(payload) != expected:
            raise ValueError(f"sales_{hash_field}_mismatch")
        try:
            record_workspace_id = canonical_business_id(record.get("workspace_id"))
            requested_workspace_id = canonical_business_id(workspace_id)
        except ValueError as exc:
            raise PermissionError("sales_workspace_isolation_violation") from exc
        if record_workspace_id != requested_workspace_id:
            raise PermissionError("sales_workspace_isolation_violation")
        return record

    def _audit(self, workspace_id: str, activity: dict[str, Any]) -> None:
        path = self._root(workspace_id) / "audit.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(activity, sort_keys=True) + "\n")
