"""
AION Phase 23N — Department Execution Queue

Purpose:
- Converts a routed business mission into per-department execution queues.
- Preserves department context boundaries.
- Separates safe, staged, approval-blocked and unsupported work.
- Does not execute tools.
- Does not duplicate the External Tool Gateway.

Design rule:
Pilot coordinates.
Departments own functional work.
Builder handles random build-me-X requests.
"""

from __future__ import annotations

from typing import Any
import re

from backend.services.aion_mission_mode.business_function_router import route_business_function
from backend.services.aion_mission_mode.department_capability_map import (
    DEPARTMENT_DISPLAY_NAMES,
    SUPPORTED_DEPARTMENTS,
    get_department_capabilities,
    normalize_department_id,
    stable_hash,
)


SAFE_INTERNAL_CAPABILITIES = {
    "campaign.plan",
    "ad_budget.plan",
    "content_calendar.create",
    "landing_page.copy",
    "review_request.draft",
    "campaign_pack.pdf",
    "pipeline.plan",
    "upsell.plan",
    "upsell.outreach_draft",
    "lead.reply_draft",
    "quote.followup_sequence",
    "sales_script.create",
    "conversion_checklist.create",
    "forecast.create",
    "cashflow.model",
    "budget.plan",
    "roi.model",
    "invoice.draft",
    "iva_vat.breakdown",
    "kpi.dashboard",
    "pricing_calculator.create",
    "invoice.collection.prepare",
    "workflow.create",
    "job_card.create",
    "sop.create",
    "inspection_checklist.create",
    "evidence_checklist.create",
    "fulfilment_plan.create",
    "handoff_task_cards.create",
    "customer_reply.draft",
    "faq.create",
    "aftercare.create",
    "complaint_response.draft",
    "support_knowledge.create",
    "case.triage",
    "leave.coverage.plan",
    "capacity.summary",
    "people.task.coordinate",
    "product.cost.analyse",
    "product.margin.analyse",
    "pricing.scenario",
    "offering.performance.review",
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
    "mission.route",
    "mission.coordinate",
    "approval.coordinate",
    "risk.guardrail",
    "receipt.bind",
    "replay.prepare",
    "department.dispatch",
}

STAGED_EXTERNAL_CAPABILITIES = {
    "social.post_draft",
    "advert.copy_draft",
    "google_business_profile.post_draft",
    "whatsapp.lead_capture_script",
    "referral_card.copy",
    "crm_record.draft",
}

READ_ONLY_EXTERNAL_CAPABILITIES = {
    "seo.plan",
}

APPROVED_LIVE_CAPABILITIES = {
    "social.publish",
    "ads.launch",
    "gmail.send",
    "booking.create",
    "payment.create",
    "dns.update",
    "website.deploy",
    "crm.mutate_live",
    "provider_account.mutate",
    "invoice.reminder.send",
    "upsell.outreach.send",
    "ads.budget_change",
}

HUMAN_ONLY_CAPABILITIES = {
    "identity.verify",
    "phone.verify",
    "real_world_photo.capture",
    "legal_document.sign",
    "provider_access.provide",
}


ARTIFACT_TYPE_BY_CAPABILITY = {
    "campaign.plan": "markdown",
    "social.post_draft": "markdown",
    "advert.copy_draft": "markdown",
    "content_calendar.create": "spreadsheet",
    "landing_page.copy": "markdown",
    "review_request.draft": "markdown",
    "campaign_pack.pdf": "pdf",
    "pipeline.plan": "markdown",
    "lead.reply_draft": "markdown",
    "quote.followup_sequence": "markdown",
    "forecast.create": "spreadsheet",
    "cashflow.model": "spreadsheet",
    "budget.plan": "spreadsheet",
    "roi.model": "spreadsheet",
    "invoice.draft": "pdf",
    "workflow.create": "workflow_json",
    "job_card.create": "markdown",
    "sop.create": "markdown",
    "customer_reply.draft": "markdown",
    "faq.create": "markdown",
    "document.create": "document",
    "spreadsheet.create": "spreadsheet",
    "pdf.render": "pdf",
    "image.generate": "image",
    "file.write": "file",
    "code.edit": "code_patch",
    "webpage.create": "html",
    "calculator.create": "spreadsheet_or_code",
}


CONCRETE_TOOL_BY_CAPABILITY = {
    "document.create": "document.create",
    "spreadsheet.create": "spreadsheet.create",
    "pdf.render": "pdf.render",
    "image.generate": "image.generate",
    "file.write": "file.write",
    "code.edit": "code.edit",
    "webpage.create": "file.write",
    "calculator.create": "spreadsheet.create",
    "content_calendar.create": "spreadsheet.create",
    "campaign_pack.pdf": "pdf.render",
    "forecast.create": "spreadsheet.create",
    "cashflow.model": "spreadsheet.create",
    "budget.plan": "spreadsheet.create",
    "roi.model": "spreadsheet.create",
    "invoice.draft": "pdf.render",
    "social.post_draft": "document.create",
    "advert.copy_draft": "document.create",
    "google_business_profile.post_draft": "document.create",
    "whatsapp.lead_capture_script": "document.create",
    "crm_record.draft": "crm.create_draft_record",
}


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower().replace("-", "_")).strip("_")


def classify_capability_execution(capability: str) -> dict[str, Any]:
    capability = str(capability or "").strip()

    if capability in APPROVED_LIVE_CAPABILITIES:
        return {
            "tool_mode": "approved_live_external",
            "permission": "approval_required",
            "approval_required": True,
            "credential_required": True,
            "live_external_side_effect": True,
            "status": "waiting_approval",
            "blocked_reason": "live_external_side_effect_requires_exact_approval",
        }

    if capability in HUMAN_ONLY_CAPABILITIES:
        return {
            "tool_mode": "human_only",
            "permission": "human_required",
            "approval_required": True,
            "credential_required": False,
            "live_external_side_effect": False,
            "status": "blocked",
            "blocked_reason": "human_only_task",
        }

    if capability in STAGED_EXTERNAL_CAPABILITIES:
        return {
            "tool_mode": "staged_external",
            "permission": "staged_review",
            "approval_required": False,
            "credential_required": False,
            "live_external_side_effect": False,
            "status": "staged",
            "blocked_reason": None,
        }

    if capability in READ_ONLY_EXTERNAL_CAPABILITIES:
        return {
            "tool_mode": "read_only_external",
            "permission": "read_only",
            "approval_required": False,
            "credential_required": False,
            "live_external_side_effect": False,
            "status": "ready",
            "blocked_reason": None,
        }

    if capability in SAFE_INTERNAL_CAPABILITIES:
        return {
            "tool_mode": "safe_internal",
            "permission": "safe_internal",
            "approval_required": False,
            "credential_required": False,
            "live_external_side_effect": False,
            "status": "ready",
            "blocked_reason": None,
        }

    return {
        "tool_mode": "unsupported",
        "permission": "blocked",
        "approval_required": False,
        "credential_required": False,
        "live_external_side_effect": False,
        "status": "blocked",
        "blocked_reason": "unsupported_capability",
    }


def create_department_queue_item(
    *,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    department_id: str,
    capability: str,
    title: str,
    task_type: str,
    task_index: int = 0,
    objective: str = "",
) -> dict[str, Any]:
    department_id = normalize_department_id(department_id)
    capability = str(capability or "").strip()
    task_id = f"{department_id}_{_slug(capability)}_{task_index:02d}"

    execution = classify_capability_execution(capability)

    item = {
        "schema_version": "aion.department_execution_queue_item.v0",
        "business_id": str(business_id or ""),
        "mission_id": str(mission_id or ""),
        "mission_run_id": str(mission_run_id or ""),
        "department_id": department_id,
        "department_display_name": DEPARTMENT_DISPLAY_NAMES.get(department_id, department_id),
        "task_id": task_id,
        "title": str(title or capability),
        "objective": str(objective or title or capability)[:2_000],
        "task_type": str(task_type or "department_work"),
        "capability": capability,
        "concrete_tool_id": CONCRETE_TOOL_BY_CAPABILITY.get(capability),
        "tool_mode": execution["tool_mode"],
        "permission": execution["permission"],
        "approval_required": execution["approval_required"],
        "credential_required": execution["credential_required"],
        "live_external_side_effect": execution["live_external_side_effect"],
        "artifact_type": ARTIFACT_TYPE_BY_CAPABILITY.get(capability, "artifact"),
        "artifact_path": None,
        "observation_hash": None,
        "artifact_hash": None,
        "receipt_hash": None,
        "status": execution["status"],
        "blocked_reason": execution["blocked_reason"],
        "queue_item_hash": "",
    }
    item["queue_item_hash"] = stable_hash({k: v for k, v in item.items() if k != "queue_item_hash"})
    return item


def default_capabilities_for_department(department_id: str, *, primary: bool = False) -> list[str]:
    department_id = normalize_department_id(department_id)
    capabilities = get_department_capabilities(department_id)

    if department_id == "marketing" and primary:
        return [
            "campaign.plan",
            "social.post_draft",
            "google_business_profile.post_draft",
            "advert.copy_draft",
            "landing_page.copy",
            "whatsapp.lead_capture_script",
            "referral_card.copy",
            "review_request.draft",
            "content_calendar.create",
            "campaign_pack.pdf",
        ]

    if department_id == "finance":
        return ["budget.plan", "roi.model"]

    if department_id == "sales":
        return ["lead.reply_draft", "quote.followup_sequence", "pipeline.plan"]

    if department_id == "operations":
        return ["fulfilment_plan.create", "workflow.create", "evidence_checklist.create"]

    if department_id == "support":
        return ["customer_reply.draft", "faq.create"]

    if department_id == "builder":
        return ["document.create"]

    if department_id == "pilot":
        return ["mission.route", "department.dispatch", "approval.coordinate"]

    return capabilities[:1]


def build_department_execution_queue(
    *,
    user_goal: str,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    routed_plan: dict[str, Any] | None = None,
    business_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    route = routed_plan or route_business_function(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        business_context=business_context or {},
    )

    queue_items: list[dict[str, Any]] = []

    primary_department = normalize_department_id(route["primary_department"])
    primary_capabilities = default_capabilities_for_department(primary_department, primary=True)

    for index, capability in enumerate(primary_capabilities):
        queue_items.append(
            create_department_queue_item(
                business_id=business_id,
                mission_id=mission_id,
                mission_run_id=mission_run_id,
                department_id=primary_department,
                capability=capability,
                title=f"{DEPARTMENT_DISPLAY_NAMES[primary_department]}: {capability}",
                task_type=f"{primary_department}_primary_work",
                task_index=index,
            )
        )

    for department_id in route.get("supporting_departments") or []:
        normalized = normalize_department_id(department_id)
        for index, capability in enumerate(default_capabilities_for_department(normalized, primary=False)):
            queue_items.append(
                create_department_queue_item(
                    business_id=business_id,
                    mission_id=mission_id,
                    mission_run_id=mission_run_id,
                    department_id=normalized,
                    capability=capability,
                    title=f"{DEPARTMENT_DISPLAY_NAMES[normalized]}: {capability}",
                    task_type=f"{normalized}_support_work",
                    task_index=index,
                )
            )

    grouped: dict[str, list[dict[str, Any]]] = {department_id: [] for department_id in SUPPORTED_DEPARTMENTS}
    for item in queue_items:
        grouped[item["department_id"]].append(item)

    result = {
        "schema_version": "aion.department_execution_queue.v0",
        "business_id": str(business_id or ""),
        "mission_id": str(mission_id or ""),
        "mission_run_id": str(mission_run_id or ""),
        "user_goal": str(user_goal or ""),
        "primary_department": primary_department,
        "supporting_departments": list(route.get("supporting_departments") or []),
        "queue_items": queue_items,
        "department_queues": grouped,
        "ready_count": sum(1 for item in queue_items if item["status"] == "ready"),
        "staged_count": sum(1 for item in queue_items if item["status"] == "staged"),
        "waiting_approval_count": sum(1 for item in queue_items if item["status"] == "waiting_approval"),
        "blocked_count": sum(1 for item in queue_items if item["status"] == "blocked"),
        "department_queue_hash": "",
    }
    result["department_queue_hash"] = stable_hash(
        {k: v for k, v in result.items() if k != "department_queue_hash"}
    )
    return result


def add_blocked_live_action_cards(
    *,
    queue: dict[str, Any],
    live_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    live_capabilities = live_capabilities or [
        "social.publish",
        "ads.launch",
        "gmail.send",
        "booking.create",
        "payment.create",
        "provider_account.mutate",
    ]

    queue_items = list(queue.get("queue_items") or [])
    business_id = str(queue.get("business_id") or "")
    mission_id = str(queue.get("mission_id") or "")
    mission_run_id = str(queue.get("mission_run_id") or "")

    for index, capability in enumerate(live_capabilities):
        queue_items.append(
            create_department_queue_item(
                business_id=business_id,
                mission_id=mission_id,
                mission_run_id=mission_run_id,
                department_id="marketing",
                capability=capability,
                title=f"Blocked live action: {capability}",
                task_type="blocked_live_action",
                task_index=index,
            )
        )

    grouped: dict[str, list[dict[str, Any]]] = {department_id: [] for department_id in SUPPORTED_DEPARTMENTS}
    for item in queue_items:
        grouped[item["department_id"]].append(item)

    result = {
        **queue,
        "queue_items": queue_items,
        "department_queues": grouped,
        "ready_count": sum(1 for item in queue_items if item["status"] == "ready"),
        "staged_count": sum(1 for item in queue_items if item["status"] == "staged"),
        "waiting_approval_count": sum(1 for item in queue_items if item["status"] == "waiting_approval"),
        "blocked_count": sum(1 for item in queue_items if item["status"] == "blocked"),
        "department_queue_hash": "",
    }
    result["department_queue_hash"] = stable_hash(
        {k: v for k, v in result.items() if k != "department_queue_hash"}
    )
    return result
