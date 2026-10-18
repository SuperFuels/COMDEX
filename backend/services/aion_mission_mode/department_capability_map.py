"""
AION Phase 23M — Department Capability Map

Purpose:
- Defines the first-class business execution departments.
- Keeps business-function context separate from generic tool execution.
- Provides deterministic capability envelopes for department-routed work.

Departments:
- Marketing
- Pilot
- Sales
- Finance
- Operations
- Support
- Builder

Design rule:
Pilot coordinates and governs.
Departments own functional business work.
Builder handles random "build me X" requests.
"""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any


SUPPORTED_DEPARTMENTS = (
    "marketing",
    "pilot",
    "sales",
    "finance",
    "operations",
    "support",
    "people",
    "products_services",
    "builder",
)

DEPARTMENT_DISPLAY_NAMES = {
    "marketing": "Marketing",
    "pilot": "Pilot",
    "sales": "Sales",
    "finance": "Finance",
    "operations": "Operations",
    "support": "Support",
    "people": "People",
    "products_services": "Products & Services",
    "builder": "Builder",
}

REMOVED_PLACEHOLDER_DEPARTMENTS = (
    "ceo",
    "coo",
    "core",
    "hr",
    "aion",
)

DEPARTMENT_CAPABILITIES = {
    "marketing": (
        "campaign.plan",
        "ad_budget.plan",
        "ads.budget_change",
        "social.post_draft",
        "advert.copy_draft",
        "content_calendar.create",
        "landing_page.copy",
        "review_request.draft",
        "campaign_pack.pdf",
        "seo.plan",
        "google_business_profile.post_draft",
        "whatsapp.lead_capture_script",
        "referral_card.copy",
    ),
    "pilot": (
        "mission.route",
        "mission.coordinate",
        "approval.coordinate",
        "risk.guardrail",
        "receipt.bind",
        "replay.prepare",
        "department.dispatch",
    ),
    "sales": (
        "pipeline.plan",
        "upsell.plan",
        "upsell.outreach_draft",
        "upsell.outreach.send",
        "lead.reply_draft",
        "quote.followup_sequence",
        "sales_script.create",
        "crm_record.draft",
        "conversion_checklist.create",
    ),
    "finance": (
        "forecast.create",
        "cashflow.model",
        "budget.plan",
        "roi.model",
        "invoice.draft",
        "iva_vat.breakdown",
        "kpi.dashboard",
        "pricing_calculator.create",
        "invoice.collection.prepare",
        "invoice.reminder.send",
    ),
    "operations": (
        "workflow.create",
        "job_card.create",
        "sop.create",
        "inspection_checklist.create",
        "evidence_checklist.create",
        "fulfilment_plan.create",
        "handoff_task_cards.create",
    ),
    "support": (
        "case.triage",
        "customer_reply.draft",
        "faq.create",
        "aftercare.create",
        "complaint_response.draft",
        "review_request.draft",
        "support_knowledge.create",
    ),
    "people": (
        "leave.coverage.plan",
        "capacity.summary",
        "people.task.coordinate",
    ),
    "products_services": (
        "product.cost.analyse",
        "product.margin.analyse",
        "pricing.scenario",
        "offering.performance.review",
    ),
    "builder": (
        "document.create",
        "spreadsheet.create",
        "pdf.render",
        "image.generate",
        "file.write",
        "code.edit",
        "webpage.create",
        "calculator.create",
        "app_component.create",
        "automation_script.create",
    ),
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def normalize_department_id(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower().replace("-", "_")).strip("_")


def is_supported_department(department_id: Any) -> bool:
    return normalize_department_id(department_id) in SUPPORTED_DEPARTMENTS


def is_removed_placeholder_department(department_id: Any) -> bool:
    return normalize_department_id(department_id) in REMOVED_PLACEHOLDER_DEPARTMENTS


def get_supported_departments() -> list[dict[str, Any]]:
    departments = []
    for department_id in SUPPORTED_DEPARTMENTS:
        departments.append(
            {
                "department_id": department_id,
                "display_name": DEPARTMENT_DISPLAY_NAMES[department_id],
                "capability_count": len(DEPARTMENT_CAPABILITIES[department_id]),
                "capabilities": list(DEPARTMENT_CAPABILITIES[department_id]),
            }
        )
    return departments


def get_department_capabilities(department_id: Any) -> list[str]:
    normalized = normalize_department_id(department_id)
    if normalized not in SUPPORTED_DEPARTMENTS:
        return []
    return list(DEPARTMENT_CAPABILITIES[normalized])


def create_department_capability_map() -> dict[str, Any]:
    result = {
        "schema_version": "aion.department_capability_map.v0",
        "supported_departments": get_supported_departments(),
        "supported_department_ids": list(SUPPORTED_DEPARTMENTS),
        "removed_placeholder_department_ids": list(REMOVED_PLACEHOLDER_DEPARTMENTS),
        "map_hash": "",
    }
    result["map_hash"] = stable_hash({k: v for k, v in result.items() if k != "map_hash"})
    return result


def create_department_capability_envelope(
    *,
    department_id: str,
    capability: str,
    task_id: str,
    task_type: str,
    title: str,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
) -> dict[str, Any]:
    normalized_department = normalize_department_id(department_id)

    supported = normalized_department in SUPPORTED_DEPARTMENTS
    known_capabilities = get_department_capabilities(normalized_department)
    capability_supported = capability in known_capabilities

    status = "ready" if supported and capability_supported else "unsupported"

    envelope = {
        "schema_version": "aion.department_capability_envelope.v0",
        "business_id": str(business_id or ""),
        "mission_id": str(mission_id or ""),
        "mission_run_id": str(mission_run_id or ""),
        "department_id": normalized_department,
        "department_display_name": DEPARTMENT_DISPLAY_NAMES.get(normalized_department, normalized_department),
        "task_id": str(task_id or ""),
        "task_type": str(task_type or ""),
        "title": str(title or ""),
        "capability": str(capability or ""),
        "department_supported": supported,
        "capability_supported": capability_supported,
        "status": status,
        "capability_task_hash": "",
    }
    envelope["capability_task_hash"] = stable_hash(
        {k: v for k, v in envelope.items() if k != "capability_task_hash"}
    )
    return envelope
