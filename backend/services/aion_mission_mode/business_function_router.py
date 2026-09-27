"""
AION Phase 23M — Business Function Router

Purpose:
- Routes user business goals into first-class departments.
- Pilot coordinates, departments own functional work.
- Builder handles random build-me-X work.
- The router is deterministic and does not call an LLM.

This module does not execute tools.
It only decides business-function ownership.
"""

from __future__ import annotations

from typing import Any
import re

from backend.services.aion_mission_mode.department_capability_map import (
    DEPARTMENT_DISPLAY_NAMES,
    SUPPORTED_DEPARTMENTS,
    create_department_capability_envelope,
    get_department_capabilities,
    is_removed_placeholder_department,
    is_supported_department,
    normalize_department_id,
    stable_hash,
)


DEPARTMENT_KEYWORDS = {
    "marketing": (
        "marketing",
        "campaign",
        "facebook",
        "meta",
        "advert",
        "ad ",
        "ads",
        "seo",
        "content",
        "post",
        "google business",
        "google business profile",
        "brand",
        "landing page copy",
        "review request",
        "referral",
        "whatsapp lead",
    ),
    "sales": (
        "sales",
        "lead",
        "pipeline",
        "quote follow",
        "follow up",
        "conversion",
        "close",
        "crm",
        "prospect",
        "outreach",
        "sales script",
    ),
    "finance": (
        "finance",
        "forecast",
        "cashflow",
        "cash flow",
        "budget",
        "roi",
        "invoice",
        "iva",
        "vat",
        "pricing",
        "margin",
        "profit",
        "cost",
        "kpi",
    ),
    "operations": (
        "operations",
        "workflow",
        "sop",
        "job card",
        "fulfilment",
        "fulfillment",
        "inspection",
        "evidence",
        "handoff",
        "task card",
        "process",
        "delivery",
    ),
    "support": (
        "support",
        "customer reply",
        "customer message",
        "faq",
        "aftercare",
        "complaint",
        "issue",
        "ticket",
        "review response",
        "helpdesk",
    ),
    "people": (
        "people", "staff", "employee", "holiday", "leave", "absence", "capacity", "cover",
    ),
    "products_services": (
        "product", "service", "offering", "unit cost", "unit economics", "product margin",
    ),
    "builder": (
        "build me",
        "build a",
        "create a file",
        "create an app",
        "webpage",
        "website",
        "calculator",
        "script",
        "code",
        "component",
        "pdf",
        "spreadsheet",
        "document",
        "label",
        "mockup",
        "automation",
    ),
    "pilot": (
        "pilot",
        "route",
        "coordinate",
        "orchestrate",
        "approval",
        "receipt",
        "proof",
        "replay",
        "mission",
        "guardrail",
    ),
}


PRIMARY_PRIORITY = (
    "marketing",
    "sales",
    "finance",
    "operations",
    "support",
    "people",
    "products_services",
    "builder",
    "pilot",
)


DEFAULT_CAPABILITY_BY_DEPARTMENT = {
    "marketing": "campaign.plan",
    "sales": "pipeline.plan",
    "finance": "forecast.create",
    "operations": "workflow.create",
    "support": "customer_reply.draft",
    "people": "capacity.summary",
    "products_services": "offering.performance.review",
    "builder": "document.create",
    "pilot": "mission.route",
}


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _score_department(text: str, department_id: str) -> int:
    score = 0
    for keyword in DEPARTMENT_KEYWORDS.get(department_id, ()):
        if keyword in text:
            score += 1
    return score


def _choose_primary_department(text: str) -> tuple[str, dict[str, int]]:
    scores = {department_id: _score_department(text, department_id) for department_id in SUPPORTED_DEPARTMENTS}

    # Builder is useful, but should not steal clearly functional business work.
    if scores["builder"] > 0:
        functional_scores = {
            key: value
            for key, value in scores.items()
            if key not in {"builder", "pilot"}
        }
        if max(functional_scores.values() or [0]) == 0:
            return "builder", scores

    for department_id in PRIMARY_PRIORITY:
        if scores[department_id] == max(scores.values()) and scores[department_id] > 0:
            return department_id, scores

    return "pilot", scores


def _supporting_departments(primary_department: str, text: str) -> list[str]:
    supporting: list[str] = []

    if primary_department == "marketing":
        # Marketing execution usually needs budget, lead handling and fulfilment readiness.
        supporting.extend(["finance", "sales", "operations"])

    if primary_department == "sales" and any(word in text for word in ("campaign", "advert", "content", "post")):
        supporting.append("marketing")

    if primary_department == "operations" and any(word in text for word in ("customer", "reply", "aftercare")):
        supporting.append("support")

    if primary_department == "builder" and any(word in text for word in ("marketing", "campaign", "facebook", "advert")):
        supporting.append("marketing")

    return [item for item in supporting if item != primary_department]


def route_business_function(
    *,
    user_goal: str,
    business_id: str = "",
    mission_id: str = "",
    mission_run_id: str = "",
    requested_department: str | None = None,
    business_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context_text = " ".join(
        [
            str(user_goal or ""),
            str((business_context or {}).get("business_name") or ""),
            str((business_context or {}).get("vertical") or ""),
            str((business_context or {}).get("service_summary") or ""),
        ]
    )
    text = _normalize_text(context_text)

    rejected_department = None

    if requested_department:
        requested = normalize_department_id(requested_department)
        if is_removed_placeholder_department(requested):
            rejected_department = requested
            primary_department, scores = _choose_primary_department(text)
        elif is_supported_department(requested):
            primary_department = requested
            scores = {department_id: _score_department(text, department_id) for department_id in SUPPORTED_DEPARTMENTS}
        else:
            rejected_department = requested
            primary_department, scores = _choose_primary_department(text)
    else:
        primary_department, scores = _choose_primary_department(text)

    supporting_departments = _supporting_departments(primary_department, text)

    primary_capability = DEFAULT_CAPABILITY_BY_DEPARTMENT[primary_department]

    primary_route = create_department_capability_envelope(
        department_id=primary_department,
        capability=primary_capability,
        task_id=f"{primary_department}_primary_task",
        task_type=f"{primary_department}_work",
        title=f"{DEPARTMENT_DISPLAY_NAMES[primary_department]} primary work",
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        business_id=business_id,
    )

    supporting_routes = []
    for department_id in supporting_departments:
        capability = DEFAULT_CAPABILITY_BY_DEPARTMENT[department_id]
        supporting_routes.append(
            create_department_capability_envelope(
                department_id=department_id,
                capability=capability,
                task_id=f"{department_id}_support_task",
                task_type=f"{department_id}_support_work",
                title=f"{DEPARTMENT_DISPLAY_NAMES[department_id]} support work",
                mission_id=mission_id,
                mission_run_id=mission_run_id,
                business_id=business_id,
            )
        )

    result = {
        "schema_version": "aion.business_function_route.v0",
        "business_id": str(business_id or ""),
        "mission_id": str(mission_id or ""),
        "mission_run_id": str(mission_run_id or ""),
        "user_goal": str(user_goal or ""),
        "primary_department": primary_department,
        "primary_department_display_name": DEPARTMENT_DISPLAY_NAMES[primary_department],
        "supporting_departments": supporting_departments,
        "department_scores": scores,
        "requested_department": normalize_department_id(requested_department) if requested_department else None,
        "rejected_department": rejected_department,
        "department_routes": [primary_route, *supporting_routes],
        "department_route_hash": "",
    }
    result["department_route_hash"] = stable_hash(
        {k: v for k, v in result.items() if k != "department_route_hash"}
    )
    return result


def summarize_department_route(route: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "schema_version": "aion.business_function_route_summary.v0",
        "primary_department": route.get("primary_department"),
        "supporting_departments": list(route.get("supporting_departments") or []),
        "department_route_hash": route.get("department_route_hash"),
        "route_count": len(route.get("department_routes") or []),
        "summary_hash": "",
    }
    summary["summary_hash"] = stable_hash({k: v for k, v in summary.items() if k != "summary_hash"})
    return summary
