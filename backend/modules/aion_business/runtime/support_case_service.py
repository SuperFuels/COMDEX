"""Canonical, authority-bound customer Support case engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import base64
from pathlib import Path
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from email.utils import parseaddr

from backend.modules.aion_business.contracts.department_pilot import canonical_contract_hash
from backend.modules.aion_business.runtime.business_container_repository import BusinessContainerRepository
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService
from backend.modules.aion_business.runtime.finance_sales_service import FinanceSalesService
from backend.modules.aion_business.runtime.sales_completion_service import SalesCompletionService


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _safe(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or "")).strip("-")


CATEGORIES = {
    "information", "status", "billing_refund", "cancel_return", "quality_fault",
    "technical_help", "complaint", "account_data", "safety_legal_emergency",
    "feedback", "unknown",
}

DEFAULT_SUPPORT_SETUP = {
    "supported_channels": ["email", "website", "telephone", "manual"],
    "primary_goal": "safe_verified_resolution",
    "tone": "calm_clear_human",
    "languages": ["en"],
    "first_response_minutes": 240,
    "resolution_target_hours": 48,
    "required_identity_checks": ["contact_route", "case_reference_or_customer_detail"],
    "knowledge_sources": ["business_terms", "approved_faq", "product_service_model", "case_history"],
    "action_policy": {
        "explain_verified_information": "allowed",
        "collect_information_and_evidence": "allowed",
        "prepare_reply": "allowed",
        "prepare_callback_or_revisit": "allowed",
        "recommend_refund_or_compensation": "prepare_only",
        "send_reply": "exact_approval_required",
        "cancel_service": "exact_approval_required",
        "issue_refund": "exact_approval_required",
        "admit_legal_liability": "never",
        "promise_unverified_date_or_outcome": "never",
    },
    "remedy_policy": {
        "automatic_refund_enabled": False,
        "automatic_refund_limit": 0.0,
        "exact_approval_refund_limit": 250.0,
        "larger_refund_route": "finance_and_human_review",
        "replacement": "exact_approval_required",
        "revisit": "exact_approval_required",
        "goodwill_credit_limit": 0.0,
    },
    "mandatory_escalations": [
        "customer_requests_human", "immediate_safety_risk", "vulnerable_customer",
        "legal_threat", "regulatory_or_consumer_rights_uncertainty", "fraud_or_chargeback",
        "data_rights_request", "discrimination_or_abuse", "repeat_failure", "unknown_authority",
    ],
    "legal_policy": {
        "default_jurisdiction": None,
        "consumer_law_sources_required": True,
        "terms_source_required": True,
        "legal_conclusion_without_authority": "human_escalation",
        "protect_customer_and_business_rights": True,
    },
}


class SupportCaseService:
    def __init__(self, repository: BusinessContainerRepository | None = None) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.authority = OrganizationAuthorityService(self.repository)
        self.sales = SalesRevenueService(self.repository, self.authority)
        self.finance = FinanceSalesService(self.repository, self.authority)
        self.completion = SalesCompletionService(self.repository)

    def workspace(self, workspace_id: str) -> dict[str, Any]:
        setup = self.ensure_setup(workspace_id)
        cases = self.list_cases(workspace_id)
        responses = self._list(workspace_id, "responses", "response_hash")
        now = datetime.now(UTC)
        open_cases = [row for row in cases if row.get("status") not in {"resolved", "closed"}]
        return {
            "schema_version": "aion.support.workspace.v1", "workspace_id": workspace_id,
            "setup": setup, "cases": cases, "responses": responses,
            "intake_endpoints": self.list_intake_endpoints(workspace_id),
            "actors": self._actors(workspace_id),
            "polling": self.polling_config(workspace_id),
            "whatsapp": self._public_whatsapp(self.whatsapp_config(workspace_id)),
            "summary": {
                "open": len(open_cases),
                "urgent": sum(row.get("priority") in {"urgent", "critical"} for row in open_cases),
                "awaiting_human": sum(row.get("status") == "human_intervention_required" for row in open_cases),
                "awaiting_customer": sum(row.get("status") == "awaiting_customer" for row in open_cases),
                "overdue": sum(self._is_overdue(row, now) for row in open_cases),
                "resolved": sum(row.get("status") == "resolved" for row in cases),
            },
            "governance": {
                "canonical_case_ledger": True, "external_send_enabled": False,
                "automatic_refund_enabled": False, "legal_self_authority": False,
                "customer_or_owner_resolution_evidence_required": True,
            },
        }

    def polling_config(self, workspace_id: str) -> dict[str, Any]:
        path = self._root(workspace_id) / "polling.json"
        if path.exists():
            return self._load(path, workspace_id, "polling_hash")
        record = {
            "schema_version": "aion.support.polling.v1", "workspace_id": workspace_id,
            "enabled": False, "interval_seconds": 300,
            "sources": {"gmail": True, "website_queue": workspace_id == "home-fixed"},
            "gmail_query": "in:inbox newer_than:30d (subject:support OR subject:help OR subject:complaint OR subject:refund OR subject:problem)",
            "actor_person_id": None, "last_poll_at": None, "next_poll_at": None,
            "last_result": None, "consecutive_failures": 0, "updated_at": _now(),
        }
        self._rehash(record, "polling_hash"); self._write(path, record)
        return record

    def configure_polling(self, workspace_id: str, *, expected_polling_hash: str,
                          enabled: bool, interval_seconds: int, sources: dict[str, Any],
                          gmail_query: str, configured_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, configured_by_person_id, "support.manage")
        current = self.polling_config(workspace_id)
        self._exact(current, "polling_hash", expected_polling_hash,
                    "support_polling_changed_since_review")
        query = str(gmail_query or "").strip()
        if "in:inbox" not in query or len(query) < 15:
            raise ValueError("support_gmail_query_must_be_narrow_and_inbox_scoped")
        configured = {
            **current, "enabled": bool(enabled),
            "interval_seconds": max(120, min(86400, int(interval_seconds or 300))),
            "sources": {"gmail": bool((sources or {}).get("gmail")),
                        "website_queue": bool((sources or {}).get("website_queue"))},
            "gmail_query": query[:1000], "actor_person_id": configured_by_person_id,
            "configured_by_person_id": configured_by_person_id,
            "configuration_authority": access, "updated_at": _now(),
            "next_poll_at": _now() if enabled else None,
        }
        self._rehash(configured, "polling_hash")
        self._write(self._root(workspace_id) / "polling.json", configured)
        return configured

    def poll_sources(self, workspace_id: str, *, force: bool = False) -> dict[str, Any]:
        config = self.polling_config(workspace_id)
        if not config.get("enabled") and not force:
            return {"ok": True, "status": "disabled", "did_work": False}
        actor = str(config.get("actor_person_id") or "").strip()
        if not actor:
            raise PermissionError("support_polling_actor_required")
        if not force and config.get("next_poll_at"):
            try:
                if datetime.fromisoformat(str(config["next_poll_at"])) > datetime.now(UTC):
                    return {"ok": True, "status": "not_due", "did_work": False,
                            "next_poll_at": config["next_poll_at"]}
            except ValueError:
                pass
        results: dict[str, Any] = {}; errors: dict[str, str] = {}
        if (config.get("sources") or {}).get("gmail"):
            try:
                from backend.api.local_node_router import get_runtime
                messages = get_runtime().fetch_gmail_messages_readonly(
                    query=str(config.get("gmail_query") or ""), max_results=25)
                results["gmail"] = self.import_gmail_messages(
                    workspace_id, messages=messages, imported_by_person_id=actor)
                results["gmail"]["messages_read"] = len(messages)
            except Exception as exc:
                errors["gmail"] = str(exc)[:500]
        if (config.get("sources") or {}).get("website_queue"):
            try:
                results["website_queue"] = self.poll_homefixed_support_queue(
                    workspace_id, imported_by_person_id=actor)
            except Exception as exc:
                errors["website_queue"] = str(exc)[:500]
        now = datetime.now(UTC)
        config.update({"last_poll_at": now.replace(microsecond=0).isoformat(),
                       "next_poll_at": (now + timedelta(seconds=int(config["interval_seconds"]))).replace(microsecond=0).isoformat(),
                       "last_result": {"sources": results, "errors": errors},
                       "consecutive_failures": int(config.get("consecutive_failures") or 0) + 1 if errors and not results else 0,
                       "updated_at": _now()})
        self._rehash(config, "polling_hash")
        self._write(self._root(workspace_id) / "polling.json", config)
        imported = sum(int(row.get("imported") or row.get("accepted") or 0)
                       for row in results.values() if isinstance(row, dict))
        return {"ok": not bool(errors), "status": "completed_with_errors" if errors else "completed",
                "did_work": imported > 0, "imported": imported, "results": results,
                "errors": errors, "next_poll_at": config["next_poll_at"]}

    def poll_homefixed_support_queue(self, workspace_id: str, *,
                                     imported_by_person_id: str) -> dict[str, Any]:
        import os
        self._require(workspace_id, imported_by_person_id, "support.manage")
        base = str(os.getenv("HOMEFIXED_SUPPORT_QUEUE_URL") or
                   "https://www.homefixed.com/api/support/queue").rstrip("/")
        key = str(os.getenv("HOMEFIXED_PUBLIC_QUEUE_KEY") or "").strip()
        if not key: raise ValueError("homefixed_support_queue_key_missing")
        request = urllib.request.Request(
            f"{base}/pull", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                queue = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ValueError("homefixed_support_queue_read_failed") from exc
        accepted = 0; deduplicated = 0; skipped = []; acknowledgements = []
        for item in queue.get("items") or []:
            pathname = str(item.get("pathname") or "")
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            try:
                result = self.create_case(
                    workspace_id, channel="website",
                    subject=str(payload.get("subject") or "Home Fixed website support"),
                    message=str(payload.get("message") or ""), customer_name=payload.get("name"),
                    email=payload.get("email"), phone=payload.get("phone"),
                    provider_thread_id=payload.get("thread_id"),
                    provider_message_id=payload.get("event_id"),
                    source_reference=f"homefixed-support:{payload.get('event_id')}",
                    evidence_references=[f"homefixed-private-queue:{pathname}"],
                    created_by_person_id=imported_by_person_id)
                acknowledgements.append(pathname)
                if result.get("deduplicated"): deduplicated += 1
                else: accepted += 1
            except (PermissionError, ValueError) as exc:
                skipped.append({"pathname": pathname, "reason": str(exc)})
        if acknowledgements:
            ack = urllib.request.Request(
                f"{base}/ack", data=json.dumps({"pathnames": acknowledgements}).encode(),
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                method="POST")
            try:
                with urllib.request.urlopen(ack, timeout=12) as response:
                    if response.status >= 300: raise ValueError("acknowledgement_failed")
            except (urllib.error.URLError, TimeoutError) as exc:
                raise ValueError("homefixed_support_queue_ack_failed") from exc
        return {"accepted": accepted, "deduplicated": deduplicated,
                "skipped": skipped, "acknowledged": len(acknowledgements),
                "external_message_sent": False}

    def create_intake_endpoint(self, workspace_id: str, *, name: str,
                               created_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, created_by_person_id, "support.manage")
        endpoint_id = "support-intake-" + secrets.token_hex(8)
        token = secrets.token_urlsafe(32)
        record = {
            "schema_version": "aion.support.intake_endpoint.v1",
            "endpoint_id": endpoint_id, "workspace_id": workspace_id,
            "name": str(name or "Website support").strip()[:120], "status": "active",
            "token_sha256": hashlib.sha256(token.encode()).hexdigest(),
            "accepted": 0, "rejected": 0, "last_received_at": None,
            "recent_accepts": [], "created_at": _now(),
            "created_by_person_id": created_by_person_id, "authority_decision": access,
            "security": {"token_returned_once": True, "honeypot": True,
                         "idempotency": True, "max_payload_characters": 12000,
                         "accepted_per_minute": 20},
        }
        self._rehash(record, "endpoint_hash")
        self._save(workspace_id, "intake_endpoints", endpoint_id, record)
        return {**self._public_endpoint(record), "token": token,
                "token_notice": "Copy now. Tessaris stores only its SHA-256 digest."}

    def whatsapp_config(self, workspace_id: str) -> dict[str, Any]:
        path = self._root(workspace_id) / "whatsapp.json"
        if path.exists(): return self._load(path, workspace_id, "whatsapp_hash")
        record = {"schema_version": "aion.support.whatsapp.v1", "workspace_id": workspace_id,
                  "status": "configuration_required", "provider": "twilio_whatsapp",
                  "sender": None, "sender_verified": False, "live_send_enabled": False,
                  "endpoint_id": None, "token_sha256": None, "created_at": _now()}
        self._rehash(record, "whatsapp_hash"); self._write(path, record); return record

    def configure_whatsapp(self, workspace_id: str, *, expected_whatsapp_hash: str,
                           sender: str | None, sender_verified: bool,
                           live_send_enabled: bool, configured_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, configured_by_person_id, "support.manage")
        current = self.whatsapp_config(workspace_id)
        self._exact(current, "whatsapp_hash", expected_whatsapp_hash,
                    "support_whatsapp_changed_since_review")
        token = secrets.token_urlsafe(32) if not current.get("token_sha256") else None
        clean_sender = re.sub(r"[^+0-9]", "", str(sender or "")) or None
        verified = bool(sender_verified and clean_sender)
        configured = {**current, "status": "configured" if verified else "sender_verification_required",
                      "sender": clean_sender, "sender_verified": verified,
                      "live_send_enabled": bool(live_send_enabled and verified),
                      "endpoint_id": current.get("endpoint_id") or "whatsapp-" + secrets.token_hex(8),
                      "token_sha256": current.get("token_sha256") or hashlib.sha256(str(token).encode()).hexdigest(),
                      "configured_at": _now(), "configured_by_person_id": configured_by_person_id,
                      "configuration_authority": access}
        self._rehash(configured, "whatsapp_hash"); self._write(self._root(workspace_id) / "whatsapp.json", configured)
        setup = self.ensure_setup(workspace_id)
        if "whatsapp" not in (setup.get("supported_channels") or []):
            setup["supported_channels"] = [*(setup.get("supported_channels") or []), "whatsapp"]
            setup["version"] = int(setup.get("version") or 0) + 1
            setup["configured_at"] = _now(); setup["configured_by_person_id"] = configured_by_person_id
            self._rehash(setup, "setup_hash"); self._write(self._root(workspace_id) / "agent_setup.json", setup)
        public = self._public_whatsapp(configured)
        if token:
            public.update({"webhook_token": token,
                           "token_notice": "Copy now. Tessaris stores only its SHA-256 digest."})
        return public

    def ingest_whatsapp_webhook(self, workspace_id: str, endpoint_id: str, *, token: str,
                                payload: dict[str, Any]) -> dict[str, Any]:
        config = self.whatsapp_config(workspace_id)
        if endpoint_id != config.get("endpoint_id"):
            raise FileNotFoundError("support_whatsapp_endpoint")
        supplied = hashlib.sha256(str(token or "").encode()).hexdigest()
        if not hmac.compare_digest(supplied, str(config.get("token_sha256") or "")):
            raise PermissionError("support_whatsapp_token_invalid")
        message_id = str(payload.get("MessageSid") or payload.get("SmsMessageSid") or "").strip()
        from_number = re.sub(r"^whatsapp:", "", str(payload.get("From") or ""), flags=re.I)
        body = str(payload.get("Body") or "").strip()
        media_count = min(10, max(0, int(payload.get("NumMedia") or 0)))
        if not message_id or not from_number or (not body and not media_count):
            raise ValueError("support_whatsapp_identity_and_content_required")
        if self._provider_message_exists(workspace_id, message_id):
            existing = self._open_case_for_contact(workspace_id, from_number)
            return {"deduplicated": True, "case": existing, "external_message_sent": False}
        attachments = []
        for index in range(media_count):
            url = str(payload.get(f"MediaUrl{index}") or "").strip()
            content_type = str(payload.get(f"MediaContentType{index}") or "application/octet-stream")
            attachments.append(self._capture_twilio_media(
                workspace_id, message_id=message_id, index=index, url=url,
                content_type=content_type))
        content = body or "Customer supplied WhatsApp media evidence."
        evidence = [f"whatsapp-media:{row['attachment_id']}" for row in attachments]
        case = self._open_case_for_contact(workspace_id, from_number)
        actor = str(config.get("configured_by_person_id") or "").strip()
        if not actor: raise PermissionError("support_whatsapp_actor_missing")
        if case:
            updated = self.append_conversation(
                workspace_id, case["case_id"], channel="whatsapp", direction="inbound",
                content=content, provider_thread_id=from_number,
                provider_message_id=message_id, evidence_references=evidence,
                recorded_by_person_id=actor)
            return {"case": updated, "continued": True, "deduplicated": False,
                    "attachments": attachments, "external_message_sent": False}
        result = self.create_case(
            workspace_id, channel="whatsapp", subject="WhatsApp customer support",
            message=content, customer_name=None, email=None, phone=from_number,
            provider_thread_id=from_number, provider_message_id=message_id,
            source_reference=f"twilio-whatsapp:{message_id}", evidence_references=evidence,
            created_by_person_id=actor)
        return {**result, "continued": False, "attachments": attachments,
                "external_message_sent": False}

    def list_intake_endpoints(self, workspace_id: str) -> list[dict[str, Any]]:
        return [self._public_endpoint(row) for row in
                self._list(workspace_id, "intake_endpoints", "endpoint_hash")]

    def ingest_website_case(self, workspace_id: str, endpoint_id: str, *, token: str,
                            payload: dict[str, Any], remote_reference: str | None = None) -> dict[str, Any]:
        endpoint = self._get(workspace_id, "intake_endpoints", endpoint_id, "endpoint_hash")
        if endpoint.get("status") != "active":
            raise PermissionError("support_website_intake_inactive")
        supplied = hashlib.sha256(str(token or "").encode()).hexdigest()
        if not hmac.compare_digest(supplied, str(endpoint.get("token_sha256") or "")):
            raise PermissionError("support_website_intake_token_invalid")
        if len(json.dumps(payload or {}, ensure_ascii=False)) > 12000:
            raise ValueError("support_website_payload_too_large")
        if str(payload.get("website") or "").strip():
            endpoint["rejected"] = int(endpoint.get("rejected") or 0) + 1
            self._rehash(endpoint, "endpoint_hash")
            self._save(workspace_id, "intake_endpoints", endpoint_id, endpoint)
            return {"accepted": False, "reason": "honeypot_triggered"}
        event_id = str(payload.get("event_id") or payload.get("idempotency_key") or "").strip()
        if not event_id:
            raise ValueError("support_website_idempotency_key_required")
        recent = []
        cutoff = datetime.now(UTC) - timedelta(minutes=1)
        for value in endpoint.get("recent_accepts") or []:
            try:
                if datetime.fromisoformat(str(value)) >= cutoff: recent.append(value)
            except ValueError:
                continue
        if len(recent) >= 20:
            raise PermissionError("support_website_rate_limit_reached")
        result = self.create_case(
            workspace_id, channel="website",
            subject=str(payload.get("subject") or "Website support request"),
            message=str(payload.get("message") or payload.get("issue") or ""),
            customer_name=payload.get("name"), email=payload.get("email"),
            phone=payload.get("phone"), provider_thread_id=payload.get("thread_id"),
            provider_message_id=event_id,
            source_reference=f"{endpoint_id}:{event_id}",
            evidence_references=[f"secured_website:{event_id}"],
            created_by_person_id=str(endpoint["created_by_person_id"]),
        )
        if not result.get("deduplicated"):
            recent.append(_now())
            endpoint["accepted"] = int(endpoint.get("accepted") or 0) + 1
        endpoint["recent_accepts"] = recent[-20:]
        endpoint["last_received_at"] = _now()
        endpoint["last_remote_reference_hash"] = hashlib.sha256(
            str(remote_reference or "unknown").encode()).hexdigest()
        self._rehash(endpoint, "endpoint_hash")
        self._save(workspace_id, "intake_endpoints", endpoint_id, endpoint)
        return {**result, "accepted": True, "external_action_performed": False,
                "intake_evidence": {"authenticated": True, "endpoint_id": endpoint_id,
                                    "raw_payload_retained": False}}

    def import_gmail_messages(self, workspace_id: str, *, messages: list[dict[str, Any]],
                              imported_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, imported_by_person_id, "support.manage")
        imported = 0; continued = 0; deduplicated = 0; skipped = []
        for message in messages or []:
            message_id = str(message.get("id") or message.get("message_id") or "").strip()
            thread_id = str(message.get("threadId") or message.get("thread_id") or "").strip()
            sender_name, sender_email = parseaddr(str(message.get("from") or message.get("sender") or ""))
            subject = str(message.get("subject") or "Support request").strip()[:300]
            body = self._plain_email_text(str(message.get("body") or message.get("snippet") or ""))
            if not message_id or not sender_email or not body:
                skipped.append({"message_id": message_id or None, "reason": "identity_or_message_missing"})
                continue
            if self._provider_message_exists(workspace_id, message_id):
                deduplicated += 1; continue
            existing = self._case_for_thread(workspace_id, thread_id) if thread_id else None
            if existing:
                self.append_conversation(
                    workspace_id, existing["case_id"], channel="email", direction="inbound",
                    content=body, provider_thread_id=thread_id, provider_message_id=message_id,
                    evidence_references=[f"gmail:{message_id}"],
                    recorded_by_person_id=imported_by_person_id)
                continued += 1
            else:
                result = self.create_case(
                    workspace_id, channel="email", subject=subject, message=body,
                    customer_name=sender_name or sender_email.split("@", 1)[0],
                    email=sender_email, phone=None, provider_thread_id=thread_id or None,
                    provider_message_id=message_id, source_reference=f"gmail:{message_id}",
                    evidence_references=[f"gmail:{message_id}"],
                    created_by_person_id=imported_by_person_id)
                if result.get("deduplicated"): deduplicated += 1
                else: imported += 1
        return {"imported": imported, "continued": continued,
                "deduplicated": deduplicated, "skipped": skipped,
                "gmail_mutated": False, "reply_sent": False}

    def ensure_setup(self, workspace_id: str) -> dict[str, Any]:
        path = self._root(workspace_id) / "agent_setup.json"
        if path.exists():
            return self._load(path, workspace_id, "setup_hash")
        setup = {
            "schema_version": "aion.support.agent_setup.v1", "workspace_id": workspace_id,
            "version": 1, "status": "draft_configuration_required",
            **json.loads(json.dumps(DEFAULT_SUPPORT_SETUP)), "created_at": _now(),
        }
        self._rehash(setup, "setup_hash"); self._write(path, setup)
        return setup

    def configure_agent(self, workspace_id: str, *, setup: dict[str, Any],
                        expected_setup_hash: str, configured_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, configured_by_person_id, "support.manage")
        current = self.ensure_setup(workspace_id)
        self._exact(current, "setup_hash", expected_setup_hash, "support_setup_changed_since_review")
        raw = setup if isinstance(setup, dict) else {}
        actions = {**DEFAULT_SUPPORT_SETUP["action_policy"], **(raw.get("action_policy") or {})}
        valid_actions = {"allowed", "prepare_only", "exact_approval_required", "never"}
        if any(value not in valid_actions for value in actions.values()):
            raise ValueError("invalid_support_action_policy")
        remedies = {**DEFAULT_SUPPORT_SETUP["remedy_policy"], **(raw.get("remedy_policy") or {})}
        # Refund execution stays approval-gated in v1 regardless of submitted configuration.
        remedies["automatic_refund_enabled"] = False
        remedies["automatic_refund_limit"] = 0.0
        legal = {**DEFAULT_SUPPORT_SETUP["legal_policy"], **(raw.get("legal_policy") or {})}
        legal["consumer_law_sources_required"] = True
        legal["terms_source_required"] = True
        legal["legal_conclusion_without_authority"] = "human_escalation"
        configured = {
            "schema_version": "aion.support.agent_setup.v1", "workspace_id": workspace_id,
            "version": int(current.get("version") or 0) + 1,
            "status": "configured_controlled_use",
            "supported_channels": self._list_values(raw.get("supported_channels"), {"email", "website", "telephone", "sms", "whatsapp", "manual"}) or list(DEFAULT_SUPPORT_SETUP["supported_channels"]),
            "primary_goal": str(raw.get("primary_goal") or "safe_verified_resolution")[:120],
            "tone": str(raw.get("tone") or "calm_clear_human")[:120],
            "languages": self._list_values(raw.get("languages"), None) or ["en"],
            "first_response_minutes": max(5, min(10080, int(raw.get("first_response_minutes") or 240))),
            "resolution_target_hours": max(1, min(2160, int(raw.get("resolution_target_hours") or 48))),
            "required_identity_checks": self._text_list(raw.get("required_identity_checks"), 20),
            "knowledge_sources": self._text_list(raw.get("knowledge_sources"), 30),
            "action_policy": actions, "remedy_policy": remedies,
            "mandatory_escalations": self._text_list(raw.get("mandatory_escalations"), 30) or list(DEFAULT_SUPPORT_SETUP["mandatory_escalations"]),
            "legal_policy": legal, "configured_at": _now(),
            "configured_by_person_id": configured_by_person_id, "configuration_authority": access,
        }
        self._rehash(configured, "setup_hash"); self._write(self._root(workspace_id) / "agent_setup.json", configured)
        return configured

    def add_knowledge(self, workspace_id: str, *, title: str, source_type: str,
                      content: str, source_reference: str, jurisdiction: str | None,
                      effective_from: str | None, approved_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, approved_by_person_id, "support.manage")
        if source_type not in {"terms", "consumer_law", "refund_policy", "warranty", "approved_faq", "product_service", "operating_policy"}:
            raise ValueError("unsupported_support_knowledge_source")
        if not str(title).strip() or len(str(content).strip()) < 20 or not str(source_reference).strip():
            raise ValueError("support_knowledge_title_content_and_source_required")
        record = {
            "schema_version": "aion.support.knowledge.v1",
            "knowledge_id": "support-knowledge-" + secrets.token_hex(8),
            "workspace_id": workspace_id, "title": str(title).strip()[:240],
            "source_type": source_type, "content": str(content).strip()[:50000],
            "source_reference": str(source_reference).strip()[:1000],
            "jurisdiction": str(jurisdiction or "").strip() or None,
            "effective_from": str(effective_from or "").strip() or None,
            "status": "approved_business_knowledge", "approved_at": _now(),
            "approved_by_person_id": approved_by_person_id, "approval_authority": access,
        }
        self._rehash(record, "knowledge_hash")
        self._save(workspace_id, "knowledge", record["knowledge_id"], record)
        return record

    def create_case(self, workspace_id: str, *, channel: str, subject: str, message: str,
                    customer_name: str | None, email: str | None, phone: str | None,
                    provider_thread_id: str | None, provider_message_id: str | None,
                    source_reference: str, evidence_references: list[str] | None,
                    created_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, created_by_person_id, "support.manage")
        setup = self.ensure_setup(workspace_id)
        if channel not in set(setup.get("supported_channels") or []):
            raise ValueError("support_channel_not_enabled")
        if not str(message).strip() or not str(source_reference).strip():
            raise ValueError("support_message_and_source_reference_required")
        duplicate = next((row for row in self.list_cases(workspace_id)
                          if row.get("source_reference") == source_reference), None)
        if duplicate:
            return {"case": duplicate, "deduplicated": True}
        match = self._match_customer(workspace_id, email=email, phone=phone)
        classification = self._classify(subject + "\n" + message)
        previous_similar = [row for row in self.list_cases(workspace_id)
                            if row.get("category") == classification["category"] and
                            ((email and str(row.get("customer", {}).get("email") or "").lower() == str(email).lower()) or
                             (phone and re.sub(r"\D", "", str(row.get("customer", {}).get("phone") or "")) == re.sub(r"\D", "", str(phone))))]
        if len(previous_similar) >= 2:
            classification["risk_flags"] = sorted(set(classification["risk_flags"]) | {"repeat_failure"})
            classification["priority"] = "urgent"
        now = datetime.now(UTC)
        case_id = "support-case-" + secrets.token_hex(8)
        conversation = self._conversation_event(
            case_id=case_id, channel=channel, direction="inbound", content=message,
            provider_thread_id=provider_thread_id, provider_message_id=provider_message_id,
            evidence_references=evidence_references, actor="customer")
        escalation = self._escalation(classification, setup, customer_requested_human=False)
        case = {
            "schema_version": "aion.support.case.v1", "case_id": case_id,
            "workspace_id": workspace_id, "case_number": self._next_case_number(workspace_id),
            "subject": str(subject or "Customer support request").strip()[:300],
            "source_reference": str(source_reference).strip()[:500], "source_channel": channel,
            "customer": {"name": str(customer_name or "").strip() or match.get("name") or "Customer",
                         "email": str(email or "").strip() or match.get("email"),
                         "phone": str(phone or "").strip() or match.get("phone"),
                         "contact_id": match.get("contact_id")},
            "linked_records": match.get("linked_records") or [],
            "category": classification["category"], "priority": classification["priority"],
            "sentiment": classification["sentiment"], "risk_flags": classification["risk_flags"],
            "status": "human_intervention_required" if escalation["required"] else "open",
            "escalation": escalation, "conversation": [conversation],
            "first_response_due_at": (now + timedelta(minutes=int(setup["first_response_minutes"]))).isoformat(),
            "resolution_due_at": (now + timedelta(hours=int(setup["resolution_target_hours"]))).isoformat(),
            "created_at": now.isoformat(), "updated_at": now.isoformat(),
            "created_by_person_id": created_by_person_id, "creation_authority": access,
            "resolution": None, "external_action_performed": False,
        }
        self._rehash(case, "case_hash"); self._save(workspace_id, "cases", case_id, case)
        return {"case": case, "deduplicated": False}

    def append_conversation(self, workspace_id: str, case_id: str, *, channel: str,
                            direction: str, content: str, provider_thread_id: str | None,
                            provider_message_id: str | None, evidence_references: list[str] | None,
                            recorded_by_person_id: str) -> dict[str, Any]:
        self._require(workspace_id, recorded_by_person_id, "support.manage")
        case = self.load_case(workspace_id, case_id)
        if direction not in {"inbound", "outbound_draft", "outbound_verified", "internal_note"}:
            raise ValueError("unsupported_support_conversation_direction")
        event = self._conversation_event(case_id=case_id, channel=channel, direction=direction,
            content=content, provider_thread_id=provider_thread_id,
            provider_message_id=provider_message_id, evidence_references=evidence_references,
            actor=recorded_by_person_id)
        case["conversation"].append(event); case["updated_at"] = _now()
        if direction == "inbound":
            classification = self._classify(content)
            case["risk_flags"] = sorted(set(case.get("risk_flags") or []) | set(classification["risk_flags"]))
            if classification["priority"] in {"urgent", "critical"}:
                case["priority"] = classification["priority"]
            escalation = self._escalation({"risk_flags": case["risk_flags"]}, self.ensure_setup(workspace_id),
                                          customer_requested_human="customer_requests_human" in case["risk_flags"])
            if escalation["required"]:
                case["status"] = "human_intervention_required"; case["escalation"] = escalation
        self._rehash(case, "case_hash"); self._save(workspace_id, "cases", case_id, case)
        return case

    def prepare_response(self, workspace_id: str, case_id: str, *, proposed_body: str,
                         requested_action: str, remedy_amount: float | None,
                         prepared_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, prepared_by_person_id, "support.manage")
        case = self.load_case(workspace_id, case_id); setup = self.ensure_setup(workspace_id)
        policy = setup.get("action_policy") or {}
        action_state = policy.get(requested_action, "never")
        if action_state == "never":
            raise PermissionError("support_action_prohibited_by_business_policy")
        knowledge = self._relevant_knowledge(workspace_id, case, proposed_body)
        legal_risk = bool(set(case.get("risk_flags") or []) & {"legal_threat", "consumer_rights", "data_rights", "safety"})
        rights_relevant = (
            legal_risk
            or case.get("category") in {"billing_refund", "cancel_return", "quality_fault", "account_data"}
            or requested_action in {"issue_refund", "recommend_refund_or_compensation", "cancel_service"}
        )
        required_sources = {row.get("source_type") for row in knowledge}
        missing_authority = []
        if rights_relevant and "consumer_law" not in required_sources:
            missing_authority.append("applicable_consumer_law_source")
        if rights_relevant and "terms" not in required_sources:
            missing_authority.append("approved_business_terms")
        jurisdiction = str((setup.get("legal_policy") or {}).get("default_jurisdiction") or "").lower()
        consumer_sources = [row for row in knowledge if row.get("source_type") == "consumer_law"]
        if rights_relevant and consumer_sources and jurisdiction and not any(
                str(row.get("jurisdiction") or "").lower() in jurisdiction
                or jurisdiction in str(row.get("jurisdiction") or "").lower()
                for row in consumer_sources):
            missing_authority.append("consumer_law_jurisdiction_mismatch")
        amount = round(float(remedy_amount or 0), 2)
        remedy = setup.get("remedy_policy") or {}
        if requested_action in {"issue_refund", "recommend_refund_or_compensation"}:
            if amount <= 0: missing_authority.append("positive_remedy_amount")
            if amount > float(remedy.get("exact_approval_refund_limit") or 0):
                missing_authority.append("finance_and_human_refund_authority")
        escalation = self._escalation({"risk_flags": case.get("risk_flags") or []}, setup,
                                      customer_requested_human="customer_requests_human" in (case.get("risk_flags") or []))
        status = "human_intervention_required" if (missing_authority or escalation["required"]) else "exact_approval_required"
        draft = {
            "schema_version": "aion.support.response_draft.v1",
            "response_id": "support-response-" + secrets.token_hex(8),
            "workspace_id": workspace_id, "case_id": case_id,
            "channel": case.get("source_channel"), "to": case.get("customer", {}).get("email") or case.get("customer", {}).get("phone"),
            "body": str(proposed_body or "").strip()[:10000],
            "requested_action": requested_action, "configured_action_state": action_state,
            "remedy_amount": amount, "knowledge_citations": [self._citation(row) for row in knowledge],
            "evidence_quality": "candidate_sources_attached_for_human_verification" if knowledge else "insufficient_business_evidence",
            "missing_authority": missing_authority, "escalation": escalation,
            "status": status, "prepared_at": _now(), "prepared_by_person_id": prepared_by_person_id,
            "preparation_authority": access, "external_message_sent": False,
            "refund_executed": False, "liability_admitted": False,
        }
        if not draft["body"]: raise ValueError("support_response_body_required")
        self._rehash(draft, "response_hash"); self._save(workspace_id, "responses", draft["response_id"], draft)
        if status == "human_intervention_required":
            case["status"] = status; case["escalation"] = escalation; case["updated_at"] = _now()
            self._rehash(case, "case_hash"); self._save(workspace_id, "cases", case_id, case)
        return draft

    def approve_response(self, workspace_id: str, response_id: str, *, expected_response_hash: str,
                         approved_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, approved_by_person_id, "support.approve_communication")
        response = self._get(workspace_id, "responses", response_id, "response_hash")
        self._exact(response, "response_hash", expected_response_hash, "support_response_changed_since_review")
        if response.get("status") != "exact_approval_required":
            raise PermissionError("support_response_not_approvable")
        response.update({"status": "approved_not_sent", "approved_at": _now(),
                         "approved_by_person_id": approved_by_person_id,
                         "approval_authority": access, "external_message_sent": False})
        self._rehash(response, "response_hash"); self._save(workspace_id, "responses", response_id, response)
        return response

    def execute_response_draft(self, workspace_id: str, response_id: str, *,
                               expected_response_hash: str,
                               executed_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, executed_by_person_id, "support.approve_communication")
        response = self._get(workspace_id, "responses", response_id, "response_hash")
        self._exact(response, "response_hash", expected_response_hash,
                    "support_response_changed_since_approval")
        if response.get("status") != "approved_not_sent":
            raise PermissionError("support_response_not_approved_for_draft")
        case = self.load_case(workspace_id, str(response["case_id"]))
        if response.get("channel") != "email" or "@" not in str(response.get("to") or ""):
            raise PermissionError("support_gmail_draft_requires_customer_email")
        thread_id = next((str(row.get("provider_thread_id")) for row in reversed(case.get("conversation") or [])
                          if row.get("provider_thread_id")), "")
        try:
            from backend.api.local_node_router import get_runtime
            result = get_runtime()._create_gmail_draft(
                to=str(response["to"]), subject=f"Re: {case.get('subject') or 'Support request'}",
                body=str(response["body"]), thread_id=thread_id)
        except Exception as exc:
            raise ValueError(f"support_gmail_draft_failed:{exc}") from exc
        response.update({"status": "provider_draft_created", "provider": "gmail",
                         "provider_draft_id": result.get("draft_id"),
                         "provider_message_id": result.get("message_id"),
                         "provider_thread_id": result.get("thread_id") or thread_id or None,
                         "draft_created_at": _now(), "executed_by_person_id": executed_by_person_id,
                         "execution_authority": access, "external_message_sent": False})
        self._rehash(response, "response_hash")
        self._save(workspace_id, "responses", response_id, response)
        self.append_conversation(
            workspace_id, str(response["case_id"]), channel="email", direction="outbound_draft",
            content=str(response["body"]), provider_thread_id=response.get("provider_thread_id"),
            provider_message_id=response.get("provider_message_id"),
            evidence_references=[f"gmail-draft:{result.get('draft_id') or 'created'}"],
            recorded_by_person_id=executed_by_person_id)
        return response

    def execute_whatsapp_response(self, workspace_id: str, response_id: str, *,
                                  expected_response_hash: str,
                                  executed_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, executed_by_person_id, "support.approve_communication")
        response = self._get(workspace_id, "responses", response_id, "response_hash")
        self._exact(response, "response_hash", expected_response_hash,
                    "support_response_changed_since_approval")
        if response.get("status") != "approved_not_sent" or response.get("channel") != "whatsapp":
            raise PermissionError("approved_whatsapp_response_required")
        config = self.whatsapp_config(workspace_id)
        if not config.get("live_send_enabled") or not config.get("sender_verified"):
            raise PermissionError("support_whatsapp_live_send_not_enabled")
        case = self.load_case(workspace_id, str(response["case_id"]))
        inbound = next((row for row in reversed(case.get("conversation") or [])
                        if row.get("channel") == "whatsapp" and row.get("direction") == "inbound"), None)
        if not inbound:
            raise PermissionError("support_whatsapp_customer_session_missing")
        if datetime.fromisoformat(str(inbound["recorded_at"])) < datetime.now(UTC) - timedelta(hours=24):
            raise PermissionError("support_whatsapp_template_required_outside_24_hour_window")
        from backend.modules.aion_business.runtime.twilio_credentials import (
            get_twilio_account_sid, get_twilio_api_secret, get_twilio_api_username)
        account = get_twilio_account_sid(workspace_id); username = get_twilio_api_username(workspace_id)
        secret = get_twilio_api_secret(workspace_id)
        if not all((account, username, secret)): raise PermissionError("twilio_credentials_missing")
        data = urllib.parse.urlencode({"From": f"whatsapp:{config['sender']}",
                                      "To": f"whatsapp:{response['to']}",
                                      "Body": str(response["body"])}).encode()
        request = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{account}/Messages.json",
            data=data, headers={"Authorization": "Basic " + base64.b64encode(f"{username}:{secret}".encode()).decode(),
                                "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(request, timeout=20) as result:
                receipt = json.loads(result.read().decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"support_whatsapp_send_failed:{exc}") from exc
        if not receipt.get("sid"): raise ValueError("support_whatsapp_provider_receipt_missing")
        response.update({"status": "submitted_to_provider", "provider": "twilio_whatsapp",
                         "provider_message_id": receipt["sid"], "provider_status": receipt.get("status"),
                         "external_message_sent": True, "sent_at": _now(),
                         "executed_by_person_id": executed_by_person_id, "execution_authority": access})
        self._rehash(response, "response_hash"); self._save(workspace_id, "responses", response_id, response)
        self.append_conversation(
            workspace_id, str(response["case_id"]), channel="whatsapp", direction="outbound_verified",
            content=str(response["body"]), provider_thread_id=str(response["to"]),
            provider_message_id=receipt["sid"], evidence_references=[f"twilio-message:{receipt['sid']}"],
            recorded_by_person_id=executed_by_person_id)
        return response

    def escalate(self, workspace_id: str, case_id: str, *, destination: str, reason: str,
                 assigned_person_id: str | None, escalated_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, escalated_by_person_id, "support.manage")
        if destination not in {"human", "finance", "operations", "sales", "legal_privacy"}:
            raise ValueError("unsupported_support_escalation_destination")
        case = self.load_case(workspace_id, case_id)
        handoff = {"schema_version": "aion.support.handoff.v1",
                   "handoff_id": "support-handoff-" + secrets.token_hex(8),
                   "workspace_id": workspace_id, "case_id": case_id,
                   "destination": destination, "reason": str(reason).strip()[:2000],
                   "assigned_person_id": assigned_person_id, "status": "open",
                   "created_at": _now(), "created_by_person_id": escalated_by_person_id,
                   "authority_decision": access, "external_action_performed": False}
        self._rehash(handoff, "handoff_hash"); self._save(workspace_id, "handoffs", handoff["handoff_id"], handoff)
        case.update({"status": "human_intervention_required", "updated_at": _now(),
                     "escalation": {"required": True, "destination": destination,
                                    "reasons": [str(reason).strip()]}})
        self._rehash(case, "case_hash"); self._save(workspace_id, "cases", case_id, case)
        return {"case": case, "handoff": handoff}

    def resolve(self, workspace_id: str, case_id: str, *, outcome: str,
                evidence_reference: str, authority_type: str,
                resolved_by_person_id: str) -> dict[str, Any]:
        access = self._require(workspace_id, resolved_by_person_id, "support.manage")
        if authority_type not in {"customer_confirmation", "owner_confirmation", "provider_verified_outcome"}:
            raise ValueError("independent_support_resolution_authority_required")
        if not str(evidence_reference).strip(): raise ValueError("support_resolution_evidence_required")
        case = self.load_case(workspace_id, case_id)
        case["resolution"] = {"outcome": str(outcome).strip()[:1000],
                              "authority_type": authority_type,
                              "evidence_reference": str(evidence_reference).strip()[:1000],
                              "resolved_at": _now(), "resolved_by_person_id": resolved_by_person_id,
                              "authority_decision": access}
        case["status"] = "resolved"; case["updated_at"] = _now()
        self._rehash(case, "case_hash"); self._save(workspace_id, "cases", case_id, case)
        return case

    def load_case(self, workspace_id: str, case_id: str) -> dict[str, Any]:
        return self._get(workspace_id, "cases", case_id, "case_hash")

    def list_cases(self, workspace_id: str) -> list[dict[str, Any]]:
        return self._list(workspace_id, "cases", "case_hash")

    def _classify(self, text: str) -> dict[str, Any]:
        lower = text.lower(); flags = []
        rules = [
            ("safety_legal_emergency", ["emergency", "danger", "unsafe", "injury", "fire", "gas leak", "legal action", "solicitor", "lawyer", "court"]),
            ("billing_refund", ["refund", "invoice", "charged", "payment", "money back", "overcharged"]),
            ("cancel_return", ["cancel", "return", "replacement"]),
            ("quality_fault", ["broken", "fault", "poor quality", "damaged", "not working", "bad service"]),
            ("technical_help", ["how do i", "error", "login", "technical", "setup"]),
            ("complaint", ["complaint", "unacceptable", "angry", "furious", "disappointed"]),
            ("status", ["where is", "when will", "status", "update", "arrive"]),
            ("account_data", ["my data", "delete my", "privacy", "subject access", "account"]),
            ("feedback", ["thank you", "great service", "feedback", "review"]),
            ("information", ["question", "information", "do you", "can you", "what is"]),
        ]
        category = next((name for name, words in rules if any(word in lower for word in words)), "unknown")
        if any(x in lower for x in ["legal action", "solicitor", "lawyer", "court"]): flags += ["legal_threat", "consumer_rights"]
        if any(x in lower for x in ["unsafe", "danger", "injury", "fire", "gas leak", "emergency"]): flags.append("safety")
        if any(x in lower for x in ["vulnerable", "elderly", "disabled", "child"]): flags.append("vulnerable_customer")
        if any(x in lower for x in ["chargeback", "fraud", "stolen card"]): flags.append("fraud_or_chargeback")
        if any(x in lower for x in ["delete my data", "subject access", "data breach"]): flags.append("data_rights")
        if any(x in lower for x in ["human", "manager", "supervisor", "real person"]): flags.append("customer_requests_human")
        heated = any(x in lower for x in ["furious", "disgusting", "unacceptable", "scam", "terrible"])
        priority = "critical" if "safety" in flags else "urgent" if flags or heated else "normal"
        return {"category": category, "priority": priority,
                "sentiment": "heated" if heated else "negative" if category in {"complaint", "quality_fault", "billing_refund"} else "neutral",
                "risk_flags": sorted(set(flags))}

    def _escalation(self, classification: dict[str, Any], setup: dict[str, Any], *, customer_requested_human: bool) -> dict[str, Any]:
        flags = set(classification.get("risk_flags") or [])
        mapping = {
            "customer_requests_human": "human", "safety": "human",
            "vulnerable_customer": "human", "legal_threat": "legal_privacy",
            "consumer_rights": "legal_privacy", "fraud_or_chargeback": "finance",
            "data_rights": "legal_privacy", "repeat_failure": "operations",
        }
        if customer_requested_human: flags.add("customer_requests_human")
        reasons = sorted(flags & set(mapping))
        return {"required": bool(reasons), "reasons": reasons,
                "destination": mapping.get(reasons[0], "human") if reasons else None,
                "automatic_external_action": False}

    def _match_customer(self, workspace_id: str, *, email: str | None, phone: str | None) -> dict[str, Any]:
        email_key = str(email or "").strip().lower(); phone_key = re.sub(r"\D", "", str(phone or ""))
        try: contacts = self.sales.list_contacts(workspace_id)
        except Exception: contacts = []
        row = next((item for item in contacts if
                    (email_key and str(item.get("email") or "").lower() == email_key) or
                    (phone_key and re.sub(r"\D", "", str(item.get("phone") or "")) == phone_key)), None)
        if not row: return {"linked_records": []}
        linked = [{"record_type": "sales_contact", "record_id": row.get("contact_id"), "match_authority": "normalised_contact_route"}]
        for opportunity in self.sales.list_opportunities(workspace_id):
            if opportunity.get("contact_id") == row.get("contact_id"):
                linked.append({"record_type": "sales_opportunity", "record_id": opportunity.get("opportunity_id"), "match_authority": "canonical_contact_id"})
        try:
            for booking in self.completion.list_bookings(workspace_id):
                customer = booking.get("customer") or {}
                if customer.get("contact_id") == row.get("contact_id"):
                    linked.append({"record_type": "customer_booking", "record_id": booking.get("booking_id"),
                                   "match_authority": "canonical_contact_id", "status": booking.get("status")})
            for handoff in self.completion.list_handoffs(workspace_id):
                customer = handoff.get("customer") or {}
                if customer.get("contact_id") == row.get("contact_id"):
                    linked.append({"record_type": "operations_handoff", "record_id": handoff.get("handoff_id"),
                                   "match_authority": "canonical_contact_id", "status": handoff.get("status")})
        except Exception:
            pass
        try:
            finance_customers = [customer for customer in self.finance.list_customers(workspace_id)
                                 if email_key and str(customer.get("email") or "").lower() == email_key]
            for customer in finance_customers:
                linked.append({"record_type": "finance_customer", "record_id": customer.get("customer_id"),
                               "match_authority": "normalised_email"})
                for invoice in self.finance.list_invoices(workspace_id):
                    if invoice.get("customer_id") == customer.get("customer_id"):
                        linked.append({"record_type": "sales_invoice", "record_id": invoice.get("invoice_id"),
                                       "reference": invoice.get("invoice_number"), "status": invoice.get("status"),
                                       "amount_due": invoice.get("amount_due"), "match_authority": "canonical_finance_customer_id"})
        except Exception:
            pass
        return {**row, "linked_records": linked}

    def _relevant_knowledge(self, workspace_id: str, case: dict[str, Any], body: str) -> list[dict[str, Any]]:
        terms = set(re.findall(r"[a-z0-9]{4,}", (case.get("subject", "") + " " + body).lower()))
        rows = self._list(workspace_id, "knowledge", "knowledge_hash")
        scored = []
        for row in rows:
            haystack = (str(row.get("title") or "") + " " + str(row.get("content") or "")).lower()
            score = sum(term in haystack for term in terms)
            if score or row.get("source_type") in {"terms", "consumer_law"}: scored.append((score, row))
        return [row for _, row in sorted(scored, key=lambda item: (-item[0], item[1].get("title", "")))[:8]]

    @staticmethod
    def _citation(row: dict[str, Any]) -> dict[str, Any]:
        return {key: row.get(key) for key in ("knowledge_id", "title", "source_type", "source_reference", "jurisdiction", "effective_from", "knowledge_hash")}

    @staticmethod
    def _conversation_event(*, case_id: str, channel: str, direction: str, content: str,
                            provider_thread_id: str | None, provider_message_id: str | None,
                            evidence_references: list[str] | None, actor: str) -> dict[str, Any]:
        payload = {"case_id": case_id, "channel": channel, "direction": direction,
                   "content": str(content).strip()[:50000],
                   "provider_thread_id": str(provider_thread_id or "").strip() or None,
                   "provider_message_id": str(provider_message_id or "").strip() or None,
                   "evidence_references": [str(x)[:1000] for x in (evidence_references or []) if str(x).strip()],
                   "actor": actor, "recorded_at": _now()}
        payload["event_id"] = "support-event-" + secrets.token_hex(8)
        payload["content_hash"] = canonical_contract_hash({"content": payload["content"]})
        payload["event_hash"] = canonical_contract_hash(payload)
        return payload

    def _next_case_number(self, workspace_id: str) -> str:
        return f"SUP-{datetime.now(UTC).year}-{len(self.list_cases(workspace_id)) + 1:05d}"

    def _case_for_thread(self, workspace_id: str, thread_id: str) -> dict[str, Any] | None:
        return next((case for case in self.list_cases(workspace_id)
                     if any(str(row.get("provider_thread_id") or "") == thread_id
                            for row in case.get("conversation") or [])), None)

    def _provider_message_exists(self, workspace_id: str, message_id: str) -> bool:
        return any(str(row.get("provider_message_id") or "") == message_id
                   for case in self.list_cases(workspace_id)
                   for row in case.get("conversation") or [])

    def _open_case_for_contact(self, workspace_id: str, phone: str) -> dict[str, Any] | None:
        key = re.sub(r"\D", "", phone)
        return next((case for case in self.list_cases(workspace_id)
                     if case.get("status") not in {"resolved", "closed"} and
                     re.sub(r"\D", "", str(case.get("customer", {}).get("phone") or "")) == key), None)

    def _capture_twilio_media(self, workspace_id: str, *, message_id: str, index: int,
                              url: str, content_type: str) -> dict[str, Any]:
        from urllib.parse import urlparse
        attachment_id = "support-attachment-" + secrets.token_hex(8)
        allowed = {"image/jpeg", "image/png", "application/pdf", "audio/mpeg", "audio/ogg", "audio/mp4"}
        parsed = urlparse(url)
        record = {"schema_version": "aion.support.attachment.v1", "workspace_id": workspace_id,
                  "attachment_id": attachment_id, "provider": "twilio_whatsapp",
                  "provider_message_id": message_id, "index": index,
                  "content_type": content_type, "source_url_hash": hashlib.sha256(url.encode()).hexdigest(),
                  "captured_at": _now(), "status": "capture_failed", "size_bytes": 0}
        if content_type not in allowed or parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith("twilio.com"):
            record["failure_reason"] = "unsupported_or_untrusted_media"
        else:
            try:
                from backend.modules.aion_business.runtime.twilio_credentials import (
                    get_twilio_api_secret, get_twilio_api_username)
                username = get_twilio_api_username(workspace_id); secret = get_twilio_api_secret(workspace_id)
                request = urllib.request.Request(url, headers={"Authorization": "Basic " + base64.b64encode(f"{username}:{secret}".encode()).decode()})
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = response.read(16 * 1024 * 1024 + 1)
                if len(payload) > 16 * 1024 * 1024: raise ValueError("media_too_large")
                media_dir = self._dir(workspace_id, "attachments")
                blob_path = media_dir / f"{attachment_id}.bin"
                blob_path.write_bytes(payload)
                record.update({"status": "captured_protected", "size_bytes": len(payload),
                               "sha256": hashlib.sha256(payload).hexdigest(),
                               "protected_path": str(blob_path)})
            except Exception as exc:
                record["failure_reason"] = str(exc)[:300]
        self._rehash(record, "attachment_hash")
        self._save(workspace_id, "attachment_metadata", attachment_id, record)
        return {key: record.get(key) for key in ("attachment_id", "content_type", "status", "size_bytes", "sha256", "attachment_hash")}

    @staticmethod
    def _plain_email_text(value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", str(value or ""))
        text = re.sub(r"\s+", " ", text).strip()
        return text[:10000]

    @staticmethod
    def _public_endpoint(record: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items()
                if key not in {"token_sha256", "authority_decision", "recent_accepts"}}

    @staticmethod
    def _public_whatsapp(record: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items()
                if key not in {"token_sha256", "configuration_authority"}}

    @staticmethod
    def _is_overdue(case: dict[str, Any], now: datetime) -> bool:
        try: return datetime.fromisoformat(str(case.get("resolution_due_at"))) < now
        except (TypeError, ValueError): return False

    def _actors(self, workspace_id: str) -> list[dict[str, Any]]:
        model = self.authority.get(workspace_id)
        return [{"person_id": row.get("id"), "name": row.get("name"), "position_title": row.get("position_title")}
                for row in model.get("people") or [] if row.get("status") == "active"]

    def _require(self, workspace_id: str, person_id: str, capability: str) -> dict[str, Any]:
        decision = self.authority.access_decision(workspace_id, person_id=person_id,
                                                  capability=capability,
                                                  department_id="department.support")
        if not decision.get("allowed"): raise PermissionError(decision.get("reason") or "support_authority_required")
        return decision

    def _root(self, workspace_id: str) -> Path:
        path = AIONBusinessPaths.business_container_dir(workspace_id) / "support" / "case_management"
        path.mkdir(parents=True, exist_ok=True); return path

    def _dir(self, workspace_id: str, collection: str) -> Path:
        path = self._root(workspace_id) / _safe(collection); path.mkdir(parents=True, exist_ok=True); return path

    def _save(self, workspace_id: str, collection: str, record_id: str, record: dict[str, Any]) -> None:
        self._write(self._dir(workspace_id, collection) / f"{_safe(record_id)}.json", record)

    def _get(self, workspace_id: str, collection: str, record_id: str, hash_key: str) -> dict[str, Any]:
        return self._load(self._dir(workspace_id, collection) / f"{_safe(record_id)}.json", workspace_id, hash_key)

    def _list(self, workspace_id: str, collection: str, hash_key: str) -> list[dict[str, Any]]:
        rows=[]
        for path in sorted(self._dir(workspace_id, collection).glob("*.json"), reverse=True):
            try: rows.append(self._load(path, workspace_id, hash_key))
            except (ValueError, json.JSONDecodeError): continue
        return rows

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(path)

    def _load(self, path: Path, workspace_id: str, hash_key: str) -> dict[str, Any]:
        if not path.exists(): raise FileNotFoundError(path.stem)
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("workspace_id") != workspace_id: raise PermissionError("cross_workspace_support_record")
        expected = row.get(hash_key); copy = dict(row); copy.pop(hash_key, None)
        if not hmac.compare_digest(str(expected or ""), canonical_contract_hash(copy)):
            raise ValueError("support_record_integrity_failed")
        return row

    @staticmethod
    def _rehash(record: dict[str, Any], key: str) -> None:
        record.pop(key, None); record[key] = canonical_contract_hash(record)

    @staticmethod
    def _exact(record: dict[str, Any], key: str, expected: str, error: str) -> None:
        if not hmac.compare_digest(str(record.get(key) or ""), str(expected or "")): raise ValueError(error)

    @staticmethod
    def _list_values(value: Any, allowed: set[str] | None) -> list[str]:
        result=[]
        for item in value or []:
            clean=str(item).strip().lower()
            if clean and (allowed is None or clean in allowed) and clean not in result: result.append(clean)
        return result[:30]

    @staticmethod
    def _text_list(value: Any, limit: int) -> list[str]:
        return [str(item).strip()[:240] for item in (value or []) if str(item).strip()][:limit]
