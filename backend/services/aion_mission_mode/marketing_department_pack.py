"""
AION Phase 23Q — Marketing Department Pack

Purpose:
- Expands a marketing mission into department-owned work.
- Keeps Home Fixed as a fixture/test vertical, not a hardcoded universal limit.
- Produces safe/staged artifact tasks before any blocked live actions.
- Routes supporting tasks to Finance, Sales and Operations where relevant.

Design rule:
Marketing owns campaign execution.
Pilot coordinates.
Finance/Sales/Operations support when needed.
Live marketing actions remain approval-blocked.
"""

from __future__ import annotations

from typing import Any

from backend.services.aion_mission_mode.business_function_router import route_business_function
from backend.services.aion_mission_mode.department_capability_map import stable_hash
from backend.services.aion_mission_mode.department_execution_queue import (
    add_blocked_live_action_cards,
    build_department_execution_queue,
)
from backend.services.aion_mission_mode.pilot_tool_execution_queue import (
    build_pilot_tool_execution_queue,
    summarize_tool_execution_queue,
)


MARKETING_SAFE_ARTIFACTS = [
    {
        "department_id": "marketing",
        "capability": "campaign.plan",
        "artifact_label": "Campaign objective and strategy",
    },
    {
        "department_id": "marketing",
        "capability": "social.post_draft",
        "artifact_label": "Facebook post pack",
    },
    {
        "department_id": "marketing",
        "capability": "google_business_profile.post_draft",
        "artifact_label": "Google Business Profile post drafts",
    },
    {
        "department_id": "marketing",
        "capability": "advert.copy_draft",
        "artifact_label": "Advert copy variants",
    },
    {
        "department_id": "marketing",
        "capability": "landing_page.copy",
        "artifact_label": "Landing page copy",
    },
    {
        "department_id": "marketing",
        "capability": "whatsapp.lead_capture_script",
        "artifact_label": "WhatsApp lead-capture script",
    },
    {
        "department_id": "marketing",
        "capability": "referral_card.copy",
        "artifact_label": "Referral card copy",
    },
    {
        "department_id": "marketing",
        "capability": "review_request.draft",
        "artifact_label": "Review request message",
    },
    {
        "department_id": "marketing",
        "capability": "content_calendar.create",
        "artifact_label": "30/60/90 content calendar",
    },
    {
        "department_id": "marketing",
        "capability": "campaign_pack.pdf",
        "artifact_label": "Campaign approval PDF pack",
    },
]

MARKETING_SUPPORTING_ARTIFACTS = [
    {
        "department_id": "finance",
        "capability": "budget.plan",
        "artifact_label": "Campaign budget",
    },
    {
        "department_id": "finance",
        "capability": "roi.model",
        "artifact_label": "ROI assumptions",
    },
    {
        "department_id": "sales",
        "capability": "lead.reply_draft",
        "artifact_label": "Lead response script",
    },
    {
        "department_id": "sales",
        "capability": "quote.followup_sequence",
        "artifact_label": "Quote follow-up sequence",
    },
    {
        "department_id": "operations",
        "capability": "fulfilment_plan.create",
        "artifact_label": "Fulfilment readiness checklist",
    },
    {
        "department_id": "operations",
        "capability": "evidence_checklist.create",
        "artifact_label": "Evidence checklist",
    },
]

MARKETING_BLOCKED_LIVE_ACTIONS = [
    "social.publish",
    "ads.launch",
    "gmail.send",
    "booking.create",
    "payment.create",
    "provider_account.mutate",
]


def create_marketing_department_pack(
    *,
    user_goal: str,
    business_id: str,
    mission_id: str,
    mission_run_id: str,
    business_context: dict[str, Any] | None = None,
    include_blocked_live_actions: bool = True,
    evaluation_time: int = 0,
) -> dict[str, Any]:
    route = route_business_function(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        business_context=business_context or {},
    )

    department_queue = build_department_execution_queue(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        routed_plan=route,
        business_context=business_context or {},
    )

    if include_blocked_live_actions:
        department_queue = add_blocked_live_action_cards(
            queue=department_queue,
            live_capabilities=MARKETING_BLOCKED_LIVE_ACTIONS,
        )

    tool_queue = build_pilot_tool_execution_queue(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        department_queue=department_queue,
        include_blocked_live_actions=False,
        evaluation_time=evaluation_time,
    )

    marketing_items = [
        item for item in tool_queue["tool_execution_items"]
        if item.get("department_id") == "marketing"
    ]
    supporting_items = [
        item for item in tool_queue["tool_execution_items"]
        if item.get("department_id") in {"finance", "sales", "operations"}
    ]
    blocked_live_items = [
        item for item in tool_queue["tool_execution_items"]
        if item.get("status") == "waiting_approval"
    ]

    result = {
        "schema_version": "aion.marketing_department_pack.v0",
        "business_id": str(business_id or ""),
        "mission_id": str(mission_id or ""),
        "mission_run_id": str(mission_run_id or ""),
        "user_goal": str(user_goal or ""),
        "primary_department": route["primary_department"],
        "supporting_departments": list(route.get("supporting_departments") or []),
        "business_context": business_context or {},
        "safe_artifact_templates": MARKETING_SAFE_ARTIFACTS,
        "supporting_artifact_templates": MARKETING_SUPPORTING_ARTIFACTS,
        "blocked_live_action_capabilities": MARKETING_BLOCKED_LIVE_ACTIONS,
        "department_route": route,
        "department_queue": department_queue,
        "tool_execution_queue": tool_queue,
        "tool_execution_summary": summarize_tool_execution_queue(tool_queue),
        "marketing_item_count": len(marketing_items),
        "supporting_item_count": len(supporting_items),
        "blocked_live_item_count": len(blocked_live_items),
        "safe_or_staged_first": all(
            item.get("status") in {"ready", "staged"}
            for item in tool_queue["tool_execution_items"]
            if item.get("department_id") in {"marketing", "finance", "sales", "operations"}
            and item.get("live_external_side_effect") is not True
        ),
        "live_external_side_effects_performed": False,
        "pack_hash": "",
    }

    result["pack_hash"] = stable_hash({k: v for k, v in result.items() if k != "pack_hash"})
    return result


def create_home_fixed_marketing_fixture_pack(
    *,
    mission_id: str = "home_fixed_marketing_mission",
    mission_run_id: str = "run_001",
    evaluation_time: int = 0,
) -> dict[str, Any]:
    return create_marketing_department_pack(
        user_goal="Create a marketing campaign for Home Fixed with Facebook posts, Google Business Profile drafts, adverts, lead capture, sales follow-up and fulfilment readiness",
        business_id="home-fixed",
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        business_context={
            "business_name": "Home Fixed",
            "vertical": "home repair and property improvement",
            "service_area": "Almería and Murcia",
            "service_summary": "Outdoor living, repairs, maintenance, painting, pergolas, carports and property improvements",
        },
        include_blocked_live_actions=True,
        evaluation_time=evaluation_time,
    )
