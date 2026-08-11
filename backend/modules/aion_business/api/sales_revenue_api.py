"""HTTP API for the canonical Tessaris Sales revenue spine."""

from __future__ import annotations

from typing import Any
import os

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.sales_revenue_service import SalesRevenueService


router = APIRouter(prefix="/api/aion/sales", tags=["aion-sales"])
sales = SalesRevenueService()


class EnquiryCreateRequest(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    enquiry: str
    source: str = "manual"
    source_reference: str | None = None
    attribution: dict[str, Any] = Field(default_factory=dict)
    consent: dict[str, Any] = Field(default_factory=dict)
    created_by_person_id: str


class QualificationRequest(BaseModel):
    answers: dict[str, Any]
    notes: str | None = None
    qualified_by_person_id: str


class AppointmentRequest(BaseModel):
    starts_at: str
    duration_minutes: int = Field(default=30, ge=5, le=480)
    assigned_person_id: str
    location_or_channel: str = "Phone"
    notes: str | None = None
    prepared_by_person_id: str


class HandoffRequest(BaseModel):
    assigned_person_id: str
    reason: str
    urgency: str = "normal"
    handed_off_by_person_id: str


class StageRequest(BaseModel):
    stage: str
    reason: str
    changed_by_person_id: str


class SessionStartRequest(BaseModel):
    channel: str = "manual"
    provider: str = "native"
    ai_disclosure: bool = True
    recording_consent: str = "not_recorded"
    started_by_person_id: str


class SessionCompleteRequest(BaseModel):
    disposition: str
    summary: str
    next_action: str | None = None
    human_takeover: bool = False
    completed_by_person_id: str


class IntakeEndpointRequest(BaseModel):
    name: str = "Website enquiry form"
    created_by_person_id: str


class WebsiteIntakeRequest(BaseModel):
    event_id: str
    name: str
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    enquiry: str
    website: str | None = None
    marketing_permission: str = "unknown"
    campaign_id: str | None = None
    campaign_name: str | None = None
    channel: str | None = None
    content_id: str | None = None
    landing_page: str | None = None
    referrer: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    requesting_agent_id: str | None = None
    agent_request_id: str | None = None
    customer_authority_reference: str | None = None
    requested_service: str | None = None
    requested_window: str | None = None
    max_fiat_price_minor: int | None = None
    currency: str = "EUR"


class GmailImportRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    imported_by_person_id: str


class GmailPollRequest(BaseModel):
    imported_by_person_id: str
    query: str = "in:inbox (subject:enquiry OR subject:quote OR subject:booking OR subject:estimate)"
    max_results: int = Field(default=10, ge=1, le=25)


class HomeFixedQueuePollRequest(BaseModel):
    imported_by_person_id: str


class SimulationRunRequest(BaseModel):
    run_by_person_id: str


class PlaybookPromotionRequest(BaseModel):
    expected_playbook_hash: str
    promoted_by_person_id: str


class SalesAgentConfigureRequest(BaseModel):
    setup: dict[str, Any]
    expected_playbook_hash: str
    configured_by_person_id: str


class CallPrepareRequest(BaseModel):
    reason: str = "Respond to customer enquiry"
    prepared_by_person_id: str
    goals: dict[str, Any] | None = None


class CallApprovalRequest(BaseModel):
    expected_draft_hash: str
    approved_by_person_id: str


class CallExecutionRequest(BaseModel):
    expected_draft_hash: str
    executed_by_person_id: str


class RetellHistorySyncRequest(BaseModel):
    synced_by_person_id: str
    limit: int = Field(default=100, ge=1, le=250)


def _workspace(value: str) -> str:
    return canonical_business_id(value)


def _call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{workspace_id}")
def workspace(workspace_id: str) -> dict[str, Any]:
    payload = _call(sales.workspace, _workspace(workspace_id))
    try:
        from backend.api.local_node_router import get_runtime
        health = get_runtime().get_gmail_connector_health()
        gmail = payload.setdefault("intake", {}).setdefault("gmail", {})
        auth_status = str(health.get("auth_status") or "not_connected")
        gmail["connector_health"] = health.get("connector_health")
        gmail["auth_status"] = auth_status
        gmail["status"] = "real_readonly_import_ready" if auth_status == "connected" else auth_status
    except Exception:
        pass
    return {"ok": True, **payload}


@router.post("/{workspace_id}/enquiries")
def create_enquiry(workspace_id: str, request: EnquiryCreateRequest) -> dict[str, Any]:
    result = _call(sales.create_enquiry, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, **result, "external_action_performed": False}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/qualification")
def qualify(workspace_id: str, opportunity_id: str, request: QualificationRequest) -> dict[str, Any]:
    record = _call(sales.qualify, _workspace(workspace_id), opportunity_id, **request.model_dump())
    return {"ok": True, "opportunity": record, "external_action_performed": False}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/appointments/prepare")
def prepare_appointment(workspace_id: str, opportunity_id: str,
                        request: AppointmentRequest) -> dict[str, Any]:
    record = _call(sales.prepare_appointment, _workspace(workspace_id), opportunity_id,
                   **request.model_dump())
    return {"ok": True, "opportunity": record, "calendar_write_performed": False,
            "customer_notification_sent": False}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/handoff")
def handoff(workspace_id: str, opportunity_id: str, request: HandoffRequest) -> dict[str, Any]:
    record = _call(sales.handoff, _workspace(workspace_id), opportunity_id, **request.model_dump())
    return {"ok": True, "opportunity": record, "external_action_performed": False}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/stage")
def update_stage(workspace_id: str, opportunity_id: str, request: StageRequest) -> dict[str, Any]:
    record = _call(sales.update_stage, _workspace(workspace_id), opportunity_id, **request.model_dump())
    return {"ok": True, "opportunity": record, "external_action_performed": False}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/sessions")
def start_session(workspace_id: str, opportunity_id: str,
                  request: SessionStartRequest) -> dict[str, Any]:
    record = _call(sales.start_session, _workspace(workspace_id), opportunity_id, **request.model_dump())
    return {"ok": True, "opportunity": record, "external_transport_started": False}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/sessions/{session_id}/complete")
def complete_session(workspace_id: str, opportunity_id: str, session_id: str,
                     request: SessionCompleteRequest) -> dict[str, Any]:
    record = _call(sales.complete_session, _workspace(workspace_id), opportunity_id, session_id,
                   **request.model_dump())
    return {"ok": True, "opportunity": record, "external_action_performed": False}


@router.post("/{workspace_id}/intake-endpoints")
def create_intake_endpoint(workspace_id: str, request: IntakeEndpointRequest) -> dict[str, Any]:
    endpoint = _call(sales.create_intake_endpoint, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, "endpoint": endpoint, "external_action_performed": False}


@router.get("/{workspace_id}/intake-endpoints")
def list_intake_endpoints(workspace_id: str) -> dict[str, Any]:
    return {"ok": True, "items": _call(sales.list_intake_endpoints, _workspace(workspace_id))}


@router.post("/public-intake/{workspace_id}/{endpoint_id}")
def ingest_website_enquiry(workspace_id: str, endpoint_id: str, request: WebsiteIntakeRequest,
                           x_tessaris_intake_key: str = Header(default=""),
                           x_forwarded_for: str = Header(default="")) -> dict[str, Any]:
    result = _call(sales.ingest_website_enquiry, _workspace(workspace_id), endpoint_id,
                   token=x_tessaris_intake_key, payload=request.model_dump(),
                   remote_reference=x_forwarded_for)
    return {"ok": True, **result, "external_action_performed": False}


@router.get("/public-a2a-status/{workspace_id}/{endpoint_id}/{agent_request_id}")
def external_agent_status(workspace_id: str, endpoint_id: str, agent_request_id: str,
                          requesting_agent_id: str,
                          x_tessaris_intake_key: str = Header(default="")) -> dict[str, Any]:
    result = _call(sales.external_agent_status, _workspace(workspace_id), endpoint_id,
                   token=x_tessaris_intake_key, requesting_agent_id=requesting_agent_id,
                   agent_request_id=agent_request_id)
    return {"ok": True, **result}


@router.post("/{workspace_id}/gmail/import")
def import_gmail_messages(workspace_id: str, request: GmailImportRequest) -> dict[str, Any]:
    result = _call(sales.import_gmail_messages, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, **result}


@router.post("/{workspace_id}/gmail/poll")
def poll_gmail_enquiries(workspace_id: str, request: GmailPollRequest) -> dict[str, Any]:
    try:
        from backend.api.local_node_router import get_runtime
        messages = get_runtime().fetch_gmail_messages_readonly(query=request.query, max_results=request.max_results)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"gmail_readonly_fetch_failed:{exc}") from exc
    result = _call(sales.import_gmail_messages, _workspace(workspace_id), messages=messages,
                   imported_by_person_id=request.imported_by_person_id)
    return {"ok": True, **result, "messages_read": len(messages)}


@router.post("/{workspace_id}/homefixed-queue/poll")
def poll_homefixed_public_queue(workspace_id: str,
                                request: HomeFixedQueuePollRequest) -> dict[str, Any]:
    result = _call(
        sales.poll_homefixed_public_queue, _workspace(workspace_id),
        imported_by_person_id=request.imported_by_person_id,
        queue_url=os.getenv("HOMEFIXED_PUBLIC_QUEUE_URL", ""),
        queue_key=os.getenv("HOMEFIXED_PUBLIC_QUEUE_KEY", ""),
        endpoint_id=os.getenv("HOMEFIXED_INTAKE_ENDPOINT_ID", ""),
        intake_token=os.getenv("HOMEFIXED_INTAKE_TOKEN", ""),
    )
    return {"ok": True, **result}


@router.post("/{workspace_id}/playbooks/inbound-enquiry/simulations")
def run_playbook_simulations(workspace_id: str, request: SimulationRunRequest) -> dict[str, Any]:
    result = _call(sales.run_playbook_simulations, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, **result, "external_action_performed": False}


@router.post("/{workspace_id}/playbooks/inbound-enquiry/promote")
def promote_playbook(workspace_id: str, request: PlaybookPromotionRequest) -> dict[str, Any]:
    playbook = _call(sales.promote_playbook, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, "playbook": playbook, "external_deployment_performed": False}


@router.put("/{workspace_id}/playbooks/inbound-enquiry/agent-setup")
def configure_sales_agent(workspace_id: str, request: SalesAgentConfigureRequest) -> dict[str, Any]:
    playbook = _call(sales.configure_sales_agent, _workspace(workspace_id), **request.model_dump())
    return {"ok": True, "playbook": playbook, "external_deployment_performed": False,
            "simulation_required": True}


@router.post("/{workspace_id}/opportunities/{opportunity_id}/calls/prepare")
def prepare_call(workspace_id: str, opportunity_id: str, request: CallPrepareRequest) -> dict[str, Any]:
    draft = _call(sales.prepare_outbound_call, _workspace(workspace_id), opportunity_id, **request.model_dump())
    return {"ok": True, "draft": draft, "external_call_started": False}


@router.post("/{workspace_id}/calls/{draft_id}/approve")
def approve_call(workspace_id: str, draft_id: str, request: CallApprovalRequest) -> dict[str, Any]:
    draft = _call(sales.approve_outbound_call, _workspace(workspace_id), draft_id, **request.model_dump())
    return {"ok": True, "draft": draft, "external_call_started": False}


@router.post("/{workspace_id}/calls/{draft_id}/execute")
def execute_call(workspace_id: str, draft_id: str, request: CallExecutionRequest) -> dict[str, Any]:
    result = _call(sales.execute_outbound_call, _workspace(workspace_id), draft_id, **request.model_dump())
    return {"ok": True, **result, "external_call_started": True}


@router.post("/{workspace_id}/telephony/retell/webhook")
async def retell_webhook(workspace_id: str, request: Request,
                         x_retell_signature: str = Header(default="")) -> dict[str, Any]:
    raw_body = await request.body()
    event = _call(sales.record_retell_webhook, _workspace(workspace_id), raw_body=raw_body,
                  signature=x_retell_signature)
    return {"ok": True, "event": event}


@router.post("/{workspace_id}/telephony/retell/sync")
def sync_retell_call_history(workspace_id: str,
                             request: RetellHistorySyncRequest) -> dict[str, Any]:
    result = _call(sales.sync_retell_call_history, _workspace(workspace_id),
                   **request.model_dump())
    return {"ok": True, **result}
