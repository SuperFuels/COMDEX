"""
AION Phase 23O — Pilot Capability Adapter Into Existing Gateway

Purpose:
- Maps department execution queue items into the existing External Tool Gateway.
- Reuses the existing gateway capability registry.
- Preserves department context.
- Does not execute tools.
- Does not grant raw model tool access.

Design rule:
Pilot coordinates.
Departments own functional work.
The gateway permits or blocks.
The runtime records.
The receipt proves.
"""

from __future__ import annotations

from typing import Any

from backend.services.aion_mission_mode.department_capability_map import stable_hash
from backend.services.aion_mission_mode.department_execution_queue import (
    create_department_queue_item,
)
from backend.services.aion_mission_mode.external_tool_gateway import (
    create_capability_registry,
    create_tool_call_request,
    evaluate_tool_call,
    get_capability,
)


DEPARTMENT_CAPABILITY_TO_GATEWAY_CAPABILITY = {
    # Marketing / content / safe creation
    "campaign.plan": "generate_copy",
    "social.post_draft": "prepare_facebook_post",
    "advert.copy_draft": "prepare_facebook_post",
    "content_calendar.create": "generate_copy",
    "landing_page.copy": "generate_copy",
    "review_request.draft": "generate_copy",
    "campaign_pack.pdf": "generate_copy",
    "seo.plan": "browser_search",
    "google_business_profile.post_draft": "prepare_facebook_post",
    "whatsapp.lead_capture_script": "generate_copy",
    "referral_card.copy": "generate_copy",

    # Sales
    "pipeline.plan": "generate_copy",
    "lead.reply_draft": "generate_copy",
    "quote.followup_sequence": "generate_copy",
    "sales_script.create": "generate_copy",
    "crm_record.draft": "generate_copy",
    "conversion_checklist.create": "generate_copy",

    # Finance
    "forecast.create": "generate_copy",
    "cashflow.model": "generate_copy",
    "budget.plan": "generate_copy",
    "roi.model": "generate_copy",
    "invoice.draft": "generate_copy",
    "iva_vat.breakdown": "generate_copy",
    "kpi.dashboard": "generate_copy",
    "pricing_calculator.create": "generate_copy",
    "invoice.collection.prepare": "generate_copy",
    "invoice.reminder.send": "send_email",

    # Operations
    "workflow.create": "generate_copy",
    "job_card.create": "generate_copy",
    "sop.create": "generate_copy",
    "inspection_checklist.create": "generate_copy",
    "evidence_checklist.create": "generate_copy",
    "fulfilment_plan.create": "generate_copy",
    "handoff_task_cards.create": "generate_copy",

    # Support
    "customer_reply.draft": "generate_copy",
    "faq.create": "generate_copy",
    "aftercare.create": "generate_copy",
    "complaint_response.draft": "generate_copy",
    "support_knowledge.create": "generate_copy",
    "case.triage": "generate_copy",

    # People
    "leave.coverage.plan": "generate_copy",
    "capacity.summary": "generate_copy",
    "people.task.coordinate": "generate_copy",

    # Products and services
    "product.cost.analyse": "generate_copy",
    "product.margin.analyse": "generate_copy",
    "pricing.scenario": "generate_copy",
    "offering.performance.review": "generate_copy",

    # Sales actions
    "upsell.plan": "generate_copy",
    "upsell.outreach_draft": "generate_copy",
    "upsell.outreach.send": "send_email",

    # Marketing actions
    "ad_budget.plan": "generate_copy",
    "ads.budget_change": "start_ad_campaign",

    # Builder
    "document.create": "generate_copy",
    "spreadsheet.create": "generate_copy",
    "pdf.render": "generate_copy",
    "image.generate": "generate_copy",
    "file.write": "create_site_files",
    "code.edit": "create_site_files",
    "webpage.create": "create_site_files",
    "calculator.create": "generate_copy",
    "app_component.create": "create_site_files",
    "automation_script.create": "create_site_files",

    # Pilot / governance
    "mission.route": "generate_copy",
    "mission.coordinate": "generate_copy",
    "approval.coordinate": "generate_copy",
    "risk.guardrail": "generate_copy",
    "receipt.bind": "generate_copy",
    "replay.prepare": "generate_copy",
    "department.dispatch": "generate_copy",

    # Live or external actions
    "social.publish": "publish_facebook_post",
    "ads.launch": "start_ad_campaign",
    "gmail.send": "send_email",
    "booking.create": "create_booking",
    "payment.create": "take_payment",
    "website.deploy": "deploy_to_vercel",
    "dns.update": "buy_domain",
    "provider_account.mutate": "mutate_provider_account",
}


DEPARTMENT_CAPABILITY_TO_LOCAL_TOOL_ID = {
    "seo.plan": "tool.google.search.v1",
    "social.post_draft": "tool.gmail.draft_preview.v1",
    "advert.copy_draft": "tool.gmail.draft_preview.v1",
    "google_business_profile.post_draft": "tool.gmail.draft_preview.v1",
    "customer_reply.draft": "tool.gmail.draft_preview.v1",
    "lead.reply_draft": "tool.gmail.draft_preview.v1",
    "crm_record.draft": "tool.stackone.crm.contact_upsert.v1",
    "gmail.send": "tool.gmail.create_draft.v1",
    "invoice.reminder.send": "tool.gmail.create_draft.v1",
    "upsell.outreach.send": "tool.gmail.create_draft.v1",
    "social.publish": "tool.browser.computer_use.v1",
    "ads.launch": "tool.browser.computer_use.v1",
    "booking.create": "tool.browser.computer_use.v1",
    "payment.create": "tool.browser.computer_use.v1",
    "website.deploy": "tool.n8n.workflow_trigger.v1",
}


def gateway_capability_for_department_capability(capability: str) -> str | None:
    return DEPARTMENT_CAPABILITY_TO_GATEWAY_CAPABILITY.get(str(capability or "").strip())


def local_tool_id_for_department_capability(capability: str, fallback: str | None = None) -> str | None:
    return DEPARTMENT_CAPABILITY_TO_LOCAL_TOOL_ID.get(str(capability or "").strip()) or fallback


def adapt_department_queue_item_to_gateway_request(
    *,
    queue_item: dict[str, Any],
    requested_by: str = "aion_pilot",
    approved_payload_hash: str | None = None,
    approval_hash: str | None = None,
    approval_expires_at: int | None = None,
) -> dict[str, Any]:
    capability = str(queue_item.get("capability") or "").strip()
    gateway_tool_name = gateway_capability_for_department_capability(capability)
    local_tool_id = local_tool_id_for_department_capability(
        capability,
        fallback=queue_item.get("concrete_tool_id"),
    )

    adapter_payload = {
        "department_id": queue_item.get("department_id"),
        "department_display_name": queue_item.get("department_display_name"),
        "task_id": queue_item.get("task_id"),
        "task_type": queue_item.get("task_type"),
        "title": queue_item.get("title"),
        "department_capability": capability,
        "gateway_tool_name": gateway_tool_name,
        "local_tool_id": local_tool_id,
        "artifact_type": queue_item.get("artifact_type"),
        "live_external_side_effect": queue_item.get("live_external_side_effect"),
    }

    if gateway_tool_name is None:
        return {
            "schema_version": "aion.pilot_capability_adapter_result.v0",
            "adapted": False,
            "adapter_state": "unsupported_department_capability",
            "business_id": queue_item.get("business_id"),
            "mission_id": queue_item.get("mission_id"),
            "mission_run_id": queue_item.get("mission_run_id"),
            "department_id": queue_item.get("department_id"),
            "task_id": queue_item.get("task_id"),
            "department_capability": capability,
            "gateway_tool_name": None,
            "local_tool_id": local_tool_id,
            "payload": adapter_payload,
            "payload_hash": stable_hash(adapter_payload),
            "adapter_hash": "",
        }

    request = create_tool_call_request(
        mission_id=str(queue_item.get("mission_id") or ""),
        mission_run_id=str(queue_item.get("mission_run_id") or ""),
        step_id=str(queue_item.get("task_id") or ""),
        tool_name=gateway_tool_name,
        requested_by=requested_by,
        payload=adapter_payload,
        approved_payload_hash=approved_payload_hash,
        approval_hash=approval_hash,
        approval_expires_at=approval_expires_at,
    )

    result = {
        "schema_version": "aion.pilot_capability_adapter_result.v0",
        "adapted": True,
        "adapter_state": "gateway_request_created",
        "business_id": queue_item.get("business_id"),
        "mission_id": queue_item.get("mission_id"),
        "mission_run_id": queue_item.get("mission_run_id"),
        "department_id": queue_item.get("department_id"),
        "task_id": queue_item.get("task_id"),
        "department_capability": capability,
        "gateway_tool_name": gateway_tool_name,
        "local_tool_id": local_tool_id,
        "payload": adapter_payload,
        "payload_hash": stable_hash(adapter_payload),
        "gateway_request": request,
        "adapter_hash": "",
    }
    result["adapter_hash"] = stable_hash({k: v for k, v in result.items() if k != "adapter_hash"})
    return result


def evaluate_department_queue_item_gateway_access(
    *,
    queue_item: dict[str, Any],
    evaluation_time: int,
    caller: str = "aion_pilot",
    approved_payload_hash: str | None = None,
    approval_hash: str | None = None,
    approval_expires_at: int | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or create_capability_registry()

    adapted = adapt_department_queue_item_to_gateway_request(
        queue_item=queue_item,
        approved_payload_hash=approved_payload_hash,
        approval_hash=approval_hash,
        approval_expires_at=approval_expires_at,
    )

    if not adapted["adapted"]:
        result = {
            **adapted,
            "gateway_registry_hash": registry["registry_hash"],
            "gateway_evaluation": {
                "allowed": False,
                "gateway_state": "blocked",
                "reasons": ["unsupported_department_capability"],
            },
            "gateway_adapter_hash": "",
        }
        result["gateway_adapter_hash"] = stable_hash(
            {k: v for k, v in result.items() if k != "gateway_adapter_hash"}
        )
        return result

    evaluation = evaluate_tool_call(
        registry=registry,
        request=adapted["gateway_request"],
        evaluation_time=evaluation_time,
        caller=caller,
    )

    result = {
        **adapted,
        "gateway_registry_hash": registry["registry_hash"],
        "gateway_evaluation": evaluation,
        "gateway_adapter_hash": "",
    }
    result["gateway_adapter_hash"] = stable_hash(
        {k: v for k, v in result.items() if k != "gateway_adapter_hash"}
    )
    return result


def create_adapter_demo_item(
    *,
    department_id: str,
    capability: str,
    business_id: str = "home-fixed",
    mission_id: str = "mission_adapter_demo",
    mission_run_id: str = "run_001",
) -> dict[str, Any]:
    return create_department_queue_item(
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        department_id=department_id,
        capability=capability,
        title=f"{department_id}: {capability}",
        task_type=f"{department_id}_work",
        task_index=0,
    )
