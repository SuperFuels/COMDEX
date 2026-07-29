"""Department activation profiles.

Only Finance is activated until the founder has designed the purpose, workflows,
capabilities, permissions and presentation of each remaining function.
"""

from __future__ import annotations

from typing import Any


DEPARTMENT_PILOT_PROFILES: dict[str, dict[str, Any]] = {
    "finance": {
        "pilot_id": "finance_pilot",
        "display_name": "Finance Pilot",
        "activation_state": "enabled",
        "implementation_order": 1,
        "design_topics": [],
        "allowed_capabilities": [
            "finance.boardroom_analysis",
            "finance.management_report",
            "finance.explain",
            "finance.reconciliation",
            "finance.transaction_reconciliation",
            "finance.ledger",
            "finance.director_signals",
            "finance.scenario",
            "cashflow.model",
        ],
        "tool_permissions": {
            "safe_internal": ["finance_report_writer", "finance_calculator", "finance_ledger_builder", "finance_transaction_matcher", "finance_counterparty_classifier", "finance_director_model"],
            "read_only_external": ["xero.read", "xero.transactions.read", "finance_artifact.read"],
            "staged_external": [
                "xero.invoice.draft",
                "finance.payment.draft",
                "finance.journal.draft",
                "finance.credit_control.draft",
                "xero.reconciliation.manual_handoff",
            ],
            "approved_live_external": [],
        },
    },
    "sales": {
        "pilot_id": "sales_pilot",
        "display_name": "Sales Pilot",
        "activation_state": "design_required",
        "implementation_order": 2,
        "design_topics": [
            "sales operating model and pipeline stages",
            "inbound and outbound phone-agent qualification",
            "email sales, follow-up and funnel workflows",
            "CRM ownership, permissions and human handoff",
        ],
    },
    "marketing": {
        "pilot_id": "marketing_pilot",
        "display_name": "Marketing Pilot",
        "activation_state": "design_required",
        "implementation_order": 3,
        "design_topics": [
            "campaign planning and day-to-day operating view",
            "channel, content, attribution and budget capabilities",
            "publishing and advertising approval boundaries",
            "relationship to Sales funnels and recognised outcomes",
        ],
    },
    "support": {
        "pilot_id": "support_pilot",
        "display_name": "Support Pilot",
        "activation_state": "design_required",
        "implementation_order": 4,
        "design_topics": [
            "support channels, queues, service levels and escalation",
            "phone support agent and communication plugins",
            "knowledge, drafted responses and human handoff",
            "outbound communication permissions",
        ],
    },
    "hr": {
        "pilot_id": "hr_pilot",
        "display_name": "HR & People Pilot",
        "activation_state": "design_required",
        "implementation_order": 5,
        "design_topics": [
            "visual organisation chart and accountability canvas",
            "people, roles, reporting lines, skills and capacity",
            "application permissions separated from job titles",
            "sensitive-data visibility and retrieval boundaries",
        ],
    },
    "operations": {
        "pilot_id": "operations_pilot",
        "display_name": "Operations Pilot",
        "activation_state": "design_required",
        "implementation_order": 6,
        "design_topics": [
            "full operating-system scope before implementation",
            "delivery, production, capacity and work orchestration",
            "stock, procurement, suppliers and service execution",
            "cross-functional dependencies and exception management",
        ],
        "implementation_note": "Design and implement after the other specialist functions.",
    },
}


def get_department_pilot_profile(department_id: str) -> dict[str, Any] | None:
    profile = DEPARTMENT_PILOT_PROFILES.get(str(department_id or "").strip().lower())
    return dict(profile) if profile else None


def list_department_pilot_profiles() -> list[dict[str, Any]]:
    return [
        {"department_id": department_id, **dict(profile)}
        for department_id, profile in sorted(
            DEPARTMENT_PILOT_PROFILES.items(),
            key=lambda item: int(item[1].get("implementation_order") or 999),
        )
    ]
