"""Canonical Finance permission and sensitive-data policy."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


FINANCE_SECURITY_POLICY: dict[str, Any] = {
    "schema_version": "aion.finance.security_policy.v1",
    "department_id": "finance",
    "default_posture": "deny_external_write",
    "business_isolation_required": True,
    "exact_payload_approval_required": True,
    "authority_source": "organization_authority.v1",
    "viewer_projection_required": True,
    "credential_storage": "macos_keychain_only",
    "credential_material_allowed_in_business_container": False,
    "data_classes": {
        "financial_summary": {
            "examples": ["management KPIs", "cash runway", "margin", "budget variance"],
            "read": ["founder", "finance_pilot", "boardroom"],
            "boardroom_projection": "summary_and_evidence_refs",
            "external_model_prompt": "minimum_necessary",
        },
        "transaction_detail": {
            "examples": ["bank transactions", "invoices", "bills", "payments", "journals"],
            "read": ["founder", "finance_pilot"],
            "boardroom_projection": "aggregates_and_exceptions_only",
            "external_model_prompt": "retrieval_only_when_required",
        },
        "counterparty_personal_data": {
            "examples": ["customer address", "supplier contact", "bank reference"],
            "read": ["founder", "finance_pilot"],
            "boardroom_projection": "redacted_unless_decision_requires_identity",
            "external_model_prompt": "redacted_by_default",
        },
        "credentials_and_tokens": {
            "examples": ["oauth access token", "refresh token", "client secret"],
            "read": ["connector_runtime"],
            "boardroom_projection": "never",
            "external_model_prompt": "never",
        },
        "payroll_and_tax_sensitive": {
            "examples": ["individual pay", "tax identifiers", "filing credentials"],
            "read": ["founder", "authorised_finance_role"],
            "boardroom_projection": "aggregates_only",
            "external_model_prompt": "aggregates_only",
        },
    },
    "capability_matrix": {
        "read_accounting_data": {"mode": "read_only_external", "approval": "connection_consent", "enabled": True},
        "analyse_and_forecast": {"mode": "safe_internal", "approval": "none", "enabled": True},
        "reconcile_summary_evidence": {"mode": "safe_internal", "approval": "review_before_canonical_change", "enabled": True},
        "build_canonical_ledger": {"mode": "safe_internal", "approval": "none", "enabled": True},
        "match_individual_transactions": {"mode": "safe_internal", "approval": "review_exceptions", "enabled": True},
        "classify_unknown_counterparties": {"mode": "safe_internal", "approval": "human_confirmation_for_new_mapping", "enabled": True},
        "reuse_confirmed_counterparty_mapping": {"mode": "safe_internal", "approval": "review_suggestion", "enabled": True},
        "accept_transaction_match_draft": {"mode": "safe_internal", "approval": "founder_or_authorised_finance_review", "enabled": True},
        "finance_director_signals": {"mode": "safe_internal", "approval": "boardroom_review_for_proposed_action", "enabled": True},
        "create_cross_department_proposal": {"mode": "safe_internal", "approval": "boardroom_approval_before_routing", "enabled": True},
        "draft_invoice_or_credit_control": {"mode": "staged_external", "approval": "exact_payload", "enabled": True},
        "create_xero_sales_invoice": {"mode": "approved_live_external", "approval": "exact_payload_and_readback", "enabled": True},
        "post_reconciliation_or_journal": {"mode": "approved_live_external", "approval": "individual_capability_enablement_and_exact_payload", "enabled": False},
        "reconcile_xero_bank_statement_line": {"mode": "provider_unsupported", "approval": "not_available", "enabled": False,
                                                   "reason": "xero_bank_statement_reconciliation_api_not_supported"},
        "create_xero_payment": {"mode": "approved_live_external", "approval": "individual_capability_enablement_and_exact_payload", "enabled": False},
        "send_invoice_or_customer_message": {"mode": "approved_live_external", "approval": "exact_payload", "enabled": False},
        "create_payment_or_transfer_funds": {"mode": "prohibited", "approval": "not_available", "enabled": False},
        "file_tax_return": {"mode": "prohibited", "approval": "not_available", "enabled": False},
    },
}


def get_finance_security_policy() -> dict[str, Any]:
    return deepcopy(FINANCE_SECURITY_POLICY)
