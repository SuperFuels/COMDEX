from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable

from backend.modules.connectors.tool_manifest import SCHEMA_VERSION, validate_tool_manifest


READINESS_STAGES = (
    "catalogued",
    "contract_ready",
    "knowledge_ready",
    "adapter_ready",
    "credential_ready",
    "sandbox_verified",
    "live_verified",
)


def get_provider_training_syllabus(tool_id: str) -> Dict[str, Any]:
    definition = _PROVIDERS[tool_id]
    return {
        "tool_id": tool_id,
        "provider": definition["label"],
        "lessons": [
            "Provider objects, identifiers and state transitions",
            "Least-privilege authentication and local Vault handling",
            "Atomic read, draft and write action contracts",
            "Business policy, authority limits and approval escalation",
            "Provider errors, retries, idempotency and rate limits",
            "Receipt creation and independent provider reconciliation",
            "Credential revocation, kill switch and incident response",
        ],
        "assessments": ["closed_book_provider_model", "safe_dry_run", "adversarial_permission_test", "sandbox_execution_and_readback", "retention_and_unfamiliar_transfer"],
        "claim_boundary": "Passing the knowledge syllabus does not grant credentials or live authority.",
    }


def _action(
    tool_id: str,
    skill_id: str,
    action: str,
    label: str,
    kind: str,
    *,
    write: bool = False,
    financial: bool = False,
    reversible: bool = True,
    data_classes: Iterable[str] = ("business_records",),
) -> Dict[str, Any]:
    tier = "high" if financial else "medium" if write else "low"
    constraints: Dict[str, Any] = {"workspace_scoped": True}
    if financial:
        constraints.update({"amount_limit_required": True, "currency": "workspace_policy"})
    return {
        "action_id": f"{tool_id}.{action}",
        "label": label,
        "description": f"Perform the bounded {label.lower()} operation through {tool_id}.",
        "kind": kind,
        "skill_ids": [skill_id],
        "input_contract": {"required": ["workspace_id", "payload"], "properties": {"workspace_id": {"type": "string"}, "payload": {"type": "object"}}},
        "output_contract": {"required": ["provider_request_id", "status", "completed_at"]},
        "risk": {
            "tier": tier,
            "external_write": write,
            "financial": financial,
            "reversible": reversible,
            "data_classes": list(data_classes),
        },
        "authority": {
            "policy_key": f"{tool_id}.{action}",
            "default_mode": "ask_each_time" if write else "auto_within_limits",
            "allowed_modes": ["ask_each_time", "auto_within_limits", "full_access", "blocked"],
            "constraints": constraints,
        },
        "execution": {
            "adapter_method": action,
            "dry_run_supported": True,
            "idempotency": "required" if write else "not_applicable",
            "timeout_seconds": 45,
        },
        "receipt": {
            "required": True,
            "success_fields": ["provider_request_id", "payload_sha256", "status", "completed_at"],
            "reconciliation": "Read provider state after execution and bind the result to the approved payload hash.",
        },
        "failure": {
            "fail_closed": True,
            "retryable_errors": ["rate_limited", "temporary_unavailable", "provider_timeout"],
            "user_message": f"{label} was not independently verified and is treated as not completed.",
        },
    }


_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "gmail": {
        "label": "Gmail",
        "category": "email",
        "connection": "oauth2",
        "scopes": ["gmail.readonly", "gmail.compose", "gmail.modify"],
        "skill": "gmail.business_email",
        "knowledge": ["email_etiquette", "business_identity", "recipient_policy", "approved_company_knowledge"],
        "actions": [
            ("search_email", "Search email", "read", False, False),
            ("create_draft", "Create email draft", "draft", False, False),
            ("send_email", "Send email", "write", True, False),
            ("reply_email", "Reply to email", "write", True, False),
        ],
    },
    "microsoft_outlook": {
        "label": "Microsoft Outlook",
        "category": "email",
        "connection": "oauth2",
        "scopes": ["Mail.Read", "Mail.ReadWrite", "Mail.Send"],
        "skill": "microsoft_outlook.business_email",
        "knowledge": ["microsoft_graph_mail", "email_etiquette", "business_identity", "recipient_policy"],
        "actions": [
            ("search_email", "Search Outlook email", "read", False, False),
            ("create_draft", "Create Outlook draft", "draft", False, False),
            ("send_email", "Send Outlook email", "write", True, False),
            ("reply_email", "Reply through Outlook", "write", True, False),
        ],
    },
    "mailchimp_marketing": {
        "label": "Mailchimp Marketing",
        "category": "marketing",
        "connection": "oauth2",
        "scopes": ["audiences.read", "audiences.write", "campaigns.read", "campaigns.write"],
        "skill": "mailchimp_marketing.campaigns",
        "knowledge": ["consent_and_suppression", "audience_identity", "campaign_policy", "marketing_attribution"],
        "actions": [
            ("read_audiences", "Read Mailchimp audiences", "read", False, False),
            ("upsert_contact", "Add or update audience contact", "write", True, False),
            ("create_campaign_draft", "Create campaign draft", "draft", False, False),
            ("send_campaign", "Send approved campaign", "write", True, False),
        ],
    },
    "resend": {
        "label": "Resend",
        "category": "transactional_email",
        "connection": "api_key",
        "scopes": ["emails.send", "emails.read", "domains.read"],
        "skill": "resend.transactional_email",
        "knowledge": ["recipient_consent", "verified_sending_domain", "message_template_policy", "delivery_events"],
        "actions": [
            ("check_domain", "Check sending domain", "read", False, False),
            ("send_notification", "Send customer notification", "write", True, False),
            ("read_delivery", "Read message delivery", "read", False, False),
            ("cancel_scheduled_email", "Cancel scheduled email", "write", True, False),
        ],
    },
    "twilio_messaging": {
        "label": "Twilio Messaging",
        "category": "sms",
        "connection": "api_key",
        "scopes": ["messages.read", "messages.create"],
        "skill": "twilio_messaging.customer_notifications",
        "knowledge": ["recipient_consent", "sender_identity", "message_policy", "delivery_status"],
        "actions": [
            ("prepare_message", "Prepare SMS message", "draft", False, False),
            ("send_message", "Send approved SMS message", "write", True, False),
            ("read_delivery", "Read SMS delivery", "read", False, False),
            ("record_opt_out", "Record messaging opt-out", "write", True, False),
        ],
    },
    "google_routes": {
        "label": "Google Maps Routes",
        "category": "routing",
        "connection": "api_key",
        "scopes": ["routes.compute", "route_matrix.compute"],
        "skill": "google_routes.field_schedule",
        "knowledge": ["address_quality", "travel_modes", "traffic_assumptions", "route_capacity"],
        "actions": [
            ("compute_route", "Compute field route", "read", False, False),
            ("compute_route_matrix", "Compute travel-time matrix", "read", False, False),
            ("propose_schedule", "Propose multi-stop schedule", "draft", False, False),
            ("read_route_conditions", "Read route conditions", "read", False, False),
        ],
    },
    "xero": {
        "label": "Xero",
        "category": "accounting",
        "connection": "oauth2",
        "scopes": ["accounting.transactions", "accounting.contacts", "accounting.settings", "offline_access"],
        "skill": "xero.bookkeeping",
        "knowledge": ["double_entry_accounting", "invoice_policy", "tax_context", "customer_and_supplier_identity"],
        "actions": [
            ("read_cash_position", "Read cash position", "read", False, False),
            ("read_invoices", "Read invoices", "read", False, False),
            ("create_draft_invoice", "Create draft invoice", "draft", False, False),
            ("issue_invoice", "Issue invoice", "write", True, False),
            ("reconcile_transaction", "Reconcile transaction", "write", True, False),
        ],
    },
    "quickbooks_online": {
        "label": "QuickBooks Online",
        "category": "accounting",
        "connection": "oauth2",
        "scopes": ["com.intuit.quickbooks.accounting", "offline_access"],
        "skill": "quickbooks_online.bookkeeping",
        "knowledge": ["double_entry_accounting", "quickbooks_entities", "tax_context", "customer_and_supplier_identity"],
        "actions": [
            ("read_ledger", "Read QuickBooks ledger", "read", False, False),
            ("run_reconciliation", "Prepare reconciliation review", "draft", False, False),
            ("create_draft_invoice", "Create QuickBooks draft invoice", "draft", False, False),
            ("post_approved_transaction", "Post approved QuickBooks transaction", "write", True, True),
        ],
    },
    "sage_accounting": {
        "label": "Sage Business Cloud Accounting",
        "category": "accounting",
        "connection": "oauth2",
        "scopes": ["full_access", "offline_access"],
        "skill": "sage_accounting.bookkeeping",
        "knowledge": ["double_entry_accounting", "sage_accounting_entities", "tax_context", "contact_allocations"],
        "actions": [
            ("read_ledger", "Read Sage ledger", "read", False, False),
            ("run_reconciliation", "Prepare reconciliation review", "draft", False, False),
            ("create_draft_invoice", "Create Sage draft invoice", "draft", False, False),
            ("post_approved_transaction", "Post approved Sage transaction", "write", True, True),
        ],
    },
    "freeagent": {
        "label": "FreeAgent",
        "category": "accounting",
        "connection": "oauth2",
        "scopes": ["accounting_read", "banking_read", "invoices_read", "bills_read"],
        "skill": "freeagent.bookkeeping",
        "knowledge": ["double_entry_accounting", "freeagent_categories", "tax_context", "bank_transaction_explanations"],
        "actions": [
            ("read_ledger", "Read FreeAgent ledger", "read", False, False),
            ("run_reconciliation", "Prepare reconciliation review", "draft", False, False),
            ("create_draft_invoice", "Create FreeAgent draft invoice", "draft", False, False),
            ("post_approved_transaction", "Post approved FreeAgent transaction", "write", True, True),
        ],
    },
    "freshbooks": {
        "label": "FreshBooks",
        "category": "accounting",
        "connection": "oauth2",
        "scopes": ["user:invoices:read", "user:bills:read", "user:payments:read", "user:expenses:read", "user:reports:read"],
        "skill": "freshbooks.bookkeeping",
        "knowledge": ["double_entry_accounting", "freshbooks_entities", "service_business_invoicing", "tax_context"],
        "actions": [
            ("read_ledger", "Read FreshBooks records", "read", False, False),
            ("run_reconciliation", "Prepare reconciliation review", "draft", False, False),
            ("create_draft_invoice", "Create FreshBooks draft invoice", "draft", False, False),
            ("post_approved_transaction", "Post approved FreshBooks transaction", "write", True, True),
        ],
    },
    "zoho_books": {
        "label": "Zoho Books",
        "category": "accounting",
        "connection": "oauth2",
        "scopes": ["ZohoBooks.settings.READ", "ZohoBooks.invoices.READ", "ZohoBooks.bills.READ", "ZohoBooks.customerpayments.READ", "ZohoBooks.vendorpayments.READ", "ZohoBooks.banking.READ", "ZohoBooks.accountants.READ"],
        "skill": "zoho_books.bookkeeping",
        "knowledge": ["double_entry_accounting", "zoho_books_entities", "organization_context", "tax_context"],
        "actions": [
            ("read_ledger", "Read Zoho Books ledger", "read", False, False),
            ("run_reconciliation", "Prepare reconciliation review", "draft", False, False),
            ("create_draft_invoice", "Create Zoho Books draft invoice", "draft", False, False),
            ("post_approved_transaction", "Post approved Zoho Books transaction", "write", True, True),
        ],
    },
    "hubspot": {
        "label": "HubSpot",
        "category": "crm",
        "connection": "oauth2",
        "scopes": ["crm.objects.contacts.read", "crm.objects.contacts.write", "crm.objects.deals.read", "crm.objects.deals.write"],
        "skill": "hubspot.sales_crm",
        "knowledge": ["crm_data_model", "sales_pipeline", "contact_identity", "deal_stage_policy"],
        "actions": [
            ("read_pipeline", "Read sales pipeline", "read", False, False),
            ("create_contact", "Create contact", "write", True, False),
            ("update_deal_stage", "Update deal stage", "write", True, False),
            ("add_activity_note", "Add CRM activity note", "write", True, False),
        ],
    },
    "pipedrive": {
        "label": "Pipedrive",
        "category": "crm",
        "connection": "oauth2",
        "scopes": ["persons:read", "persons:write", "deals:read", "deals:write", "activities:write"],
        "skill": "pipedrive.sales_crm",
        "knowledge": ["crm_data_model", "sales_pipeline", "contact_identity", "activity_policy"],
        "actions": [
            ("read_pipeline", "Read Pipedrive pipeline", "read", False, False),
            ("create_person", "Create Pipedrive person", "write", True, False),
            ("update_deal_stage", "Update Pipedrive deal", "write", True, False),
            ("add_activity", "Add Pipedrive activity", "write", True, False),
        ],
    },
    "twilio_voice": {
        "label": "Twilio Voice",
        "category": "calling",
        "connection": "api_key",
        "scopes": ["calls.read", "calls.create", "recordings.read"],
        "skill": "twilio_voice.business_calling",
        "knowledge": ["call_purpose", "contact_consent", "approved_script", "recording_and_disclosure_policy"],
        "actions": [
            ("prepare_call", "Prepare phone call", "draft", False, False),
            ("place_call", "Place phone call", "write", True, False),
            ("read_call_outcome", "Read call outcome", "read", False, False),
            ("record_call_outcome", "Record call outcome", "write", True, False),
        ],
    },
    "stripe": {
        "label": "Stripe",
        "category": "payments",
        "connection": "api_key",
        "scopes": ["payment_intents.read", "payment_intents.write", "refunds.write"],
        "skill": "stripe.customer_payments",
        "knowledge": ["payment_identity", "amount_and_currency", "refund_policy", "fraud_and_dispute_controls"],
        "actions": [
            ("read_payment_status", "Read payment status", "read", False, False),
            ("create_payment_intent", "Create customer payment intent", "financial", True, True),
            ("capture_payment", "Capture authorised customer payment", "financial", True, True),
            ("refund_payment", "Refund customer payment", "financial", True, True),
        ],
    },
}


CURRENT_READINESS: Dict[str, Dict[str, Any]] = {
    "gmail": {"stage": "adapter_ready", "evidence": ["oauth_routes", "draft_adapter", "send_adapter", "approval_tests"], "blockers": ["workspace_credential_health", "approved_live_send_and_readback"]},
    "microsoft_outlook": {"stage": "adapter_ready", "evidence": ["manifest_contract", "graph_draft_and_send_adapter"], "blockers": ["oauth_connection", "sandbox_and_live_receipts"]},
    "mailchimp_marketing": {"stage": "adapter_ready", "evidence": ["contact_upsert_adapter", "campaign_draft_adapter"], "blockers": ["vault_connection", "approved_campaign_send_and_readback"]},
    "resend": {"stage": "adapter_ready", "evidence": ["transactional_send_adapter", "business_action_wrapper"], "blockers": ["vault_connection", "verified_sending_domain", "approved_send_and_delivery_readback"]},
    "twilio_messaging": {"stage": "adapter_ready", "evidence": ["sms_send_paths", "delivery_record_contract"], "blockers": ["vault_connection", "consent_evidence", "approved_send_and_status_readback"]},
    "google_routes": {"stage": "contract_ready", "evidence": ["provider_contract"], "blockers": ["routes_adapter", "vault_connection", "route_matrix_acceptance"]},
    "xero": {"stage": "adapter_ready", "evidence": ["invoice_export", "reconciliation_handoff", "supplier_contact_service"], "blockers": ["live_write_adapter", "oauth_connection", "approved_provider_readback"]},
    "quickbooks_online": {"stage": "adapter_ready", "evidence": ["read_adapter", "canonical_normalizer", "shared_reconciliation_harness"], "blockers": ["oauth_connection", "sandbox_read_acceptance", "approved_write_and_readback"]},
    "sage_accounting": {"stage": "adapter_ready", "evidence": ["read_adapter", "canonical_normalizer", "shared_reconciliation_harness"], "blockers": ["oauth_connection", "sandbox_read_acceptance", "approved_write_and_readback"]},
    "freeagent": {"stage": "adapter_ready", "evidence": ["read_adapter", "canonical_normalizer", "shared_reconciliation_harness"], "blockers": ["oauth_connection", "sandbox_read_acceptance", "approved_write_and_readback"]},
    "freshbooks": {"stage": "adapter_ready", "evidence": ["read_adapter", "canonical_normalizer", "shared_reconciliation_harness"], "blockers": ["oauth_connection", "sandbox_read_acceptance", "approved_write_and_readback"]},
    "zoho_books": {"stage": "adapter_ready", "evidence": ["read_adapter", "canonical_normalizer", "shared_reconciliation_harness"], "blockers": ["oauth_connection", "sandbox_read_acceptance", "approved_write_and_readback"]},
    "hubspot": {"stage": "adapter_ready", "evidence": ["oauth_routes", "mcp_tools", "dry_run_and_write_paths"], "blockers": ["workspace_credential_health", "approved_live_write_and_readback"]},
    "pipedrive": {"stage": "contract_ready", "evidence": ["provider_contract"], "blockers": ["crm_adapter", "oauth_connection", "sandbox_and_live_receipts"]},
    "twilio_voice": {"stage": "adapter_ready", "evidence": ["credential_contract", "signed_webhook_routes", "retell_call_history"], "blockers": ["approved_outbound_call", "provider_call_status_readback", "consent_evidence"]},
    "stripe": {"stage": "contract_ready", "evidence": ["signed_webhook_verification", "manifest_contract"], "blockers": ["payment_execution_adapter", "sandbox_payment_and_refund", "approved_live_receipt"]},
}


def build_provider_manifest(tool_id: str) -> Dict[str, Any]:
    definition = _PROVIDERS[tool_id]
    skill_id = definition["skill"]
    actions = [
        _action(
            tool_id,
            skill_id,
            action_id,
            label,
            kind,
            write=write,
            financial=financial,
            reversible=action_id not in {"send_email", "reply_email", "send_campaign", "send_notification", "send_message", "place_call", "capture_payment"},
            data_classes=("financial_records",) if definition["category"] in {"accounting", "payments"} else ("business_records", "personal_data"),
        )
        for action_id, label, kind, write, financial in definition["actions"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {"tool_id": tool_id, "label": definition["label"], "category": definition["category"], "owner": "Tessaris Connectors", "description": f"Governed {definition['label']} integration."},
        "connection": {
            "type": definition["connection"],
            "vault_reference": f"vault.{tool_id}.credentials",
            "least_privilege_scopes": list(definition["scopes"]),
            "health_check": f"{tool_id}.health_check",
            "revocation_method": "Revoke the provider grant/key and remove the local Vault entry.",
            "secrets_visible_to_model": False,
        },
        "skills": [{"skill_id": skill_id, "description": f"Use {definition['label']} safely for bounded business work.", "required_knowledge": list(definition["knowledge"])}],
        "actions": actions,
        "governance": {
            "data_retention": "Retain minimum local evidence and provider identifiers needed for reconciliation.",
            "audit_log": "Record intent, policy, payload hash, attempt, provider result and reconciliation.",
            "kill_switch": f"Disable {tool_id}, revoke its credential and stop queued actions.",
            "promotion_evidence": ["contract_tests_pass", "credential_health_verified", "dry_run_verified", "sandbox_write_verified", "live_write_and_readback_verified", "failure_and_revocation_verified"],
            "claim_boundary": "The manifest and skill syllabus do not prove a credential exists or that live execution has been verified.",
        },
    }


def get_priority_provider_catalog() -> Dict[str, Dict[str, Any]]:
    return {tool_id: build_provider_manifest(tool_id) for tool_id in _PROVIDERS}


def validate_priority_provider_catalog() -> Dict[str, Any]:
    providers: Dict[str, Any] = {}
    for tool_id, manifest in get_priority_provider_catalog().items():
        providers[tool_id] = {**validate_tool_manifest(manifest), **deepcopy(CURRENT_READINESS[tool_id])}
    return {"valid": all(item["valid"] for item in providers.values()), "provider_count": len(providers), "providers": providers}


def can_claim_live_verified(tool_id: str, evidence: Dict[str, Any]) -> bool:
    required = {
        "contract_sha256",
        "credential_health_receipt",
        "dry_run_receipt",
        "approved_live_action_receipt",
        "provider_readback_receipt",
        "failure_test_receipt",
        "revocation_test_receipt",
    }
    return tool_id in _PROVIDERS and all(bool(evidence.get(key)) for key in required)
