"""HTTP boundary for governed Tessaris Support cases."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Header, HTTPException, Request
from urllib.parse import parse_qs
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.support_case_service import SupportCaseService
from backend.modules.aion_business.runtime.support_voice_service import SupportVoiceService

router = APIRouter(prefix="/api/aion/support", tags=["aion-support"])
service = SupportCaseService()
voice = SupportVoiceService()


def _workspace(value: str) -> str: return canonical_business_id(value)
def _call(method, *args, **kwargs):
    try: return method(*args, **kwargs)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


class AgentSetupRequest(BaseModel):
    expected_setup_hash: str
    setup: dict[str, Any] = Field(default_factory=dict)
    configured_by_person_id: str

class KnowledgeRequest(BaseModel):
    title: str; source_type: str; content: str; source_reference: str
    jurisdiction: str | None = None; effective_from: str | None = None
    approved_by_person_id: str

class CaseRequest(BaseModel):
    channel: str = "manual"; subject: str; message: str
    customer_name: str | None = None; email: str | None = None; phone: str | None = None
    provider_thread_id: str | None = None; provider_message_id: str | None = None
    source_reference: str; evidence_references: list[str] = Field(default_factory=list)
    created_by_person_id: str

class ConversationRequest(BaseModel):
    channel: str; direction: str; content: str
    provider_thread_id: str | None = None; provider_message_id: str | None = None
    evidence_references: list[str] = Field(default_factory=list)
    recorded_by_person_id: str

class ResponseRequest(BaseModel):
    proposed_body: str; requested_action: str = "prepare_reply"
    remedy_amount: float | None = Field(default=None, ge=0)
    prepared_by_person_id: str

class ApprovalRequest(BaseModel):
    expected_response_hash: str; approved_by_person_id: str

class EscalationRequest(BaseModel):
    destination: str; reason: str; assigned_person_id: str | None = None
    escalated_by_person_id: str

class ResolutionRequest(BaseModel):
    outcome: str; evidence_reference: str; authority_type: str
    resolved_by_person_id: str

class IntakeEndpointRequest(BaseModel):
    name: str = "Website support"
    created_by_person_id: str

class WebsiteSupportRequest(BaseModel):
    event_id: str | None = None; idempotency_key: str | None = None
    subject: str = "Website support request"; message: str
    name: str | None = None; email: str | None = None; phone: str | None = None
    thread_id: str | None = None; website: str | None = None

class GmailImportRequest(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)
    imported_by_person_id: str

class GmailPollRequest(BaseModel):
    imported_by_person_id: str
    query: str = "in:inbox (subject:support OR subject:help OR subject:complaint OR subject:refund OR subject:problem)"
    max_results: int = Field(default=10, ge=1, le=25)

class PollingConfigRequest(BaseModel):
    expected_polling_hash: str
    enabled: bool = True
    interval_seconds: int = Field(default=300, ge=120, le=86400)
    sources: dict[str, Any] = Field(default_factory=lambda: {"gmail": True, "website_queue": False})
    gmail_query: str
    configured_by_person_id: str

class WhatsAppConfigRequest(BaseModel):
    expected_whatsapp_hash: str
    sender: str | None = None
    sender_verified: bool = False
    live_send_enabled: bool = False
    configured_by_person_id: str

class VoiceDeployRequest(BaseModel):
    deployed_by_person_id: str
    voice_id: str = "retell-Cimo"


@router.get("/{workspace_id}")
def workspace(workspace_id: str):
    return {"ok": True, **_call(service.workspace, _workspace(workspace_id))}

@router.post("/{workspace_id}/intake-endpoints")
def create_intake_endpoint(workspace_id: str, request: IntakeEndpointRequest):
    return {"ok": True, "endpoint": _call(service.create_intake_endpoint,
        _workspace(workspace_id), **request.model_dump())}

@router.post("/public-intake/{workspace_id}/{endpoint_id}")
def public_intake(workspace_id: str, endpoint_id: str, request: WebsiteSupportRequest,
                  x_tessaris_intake_key: str = Header(default=""),
                  x_forwarded_for: str = Header(default="")):
    return {"ok": True, **_call(service.ingest_website_case, _workspace(workspace_id), endpoint_id,
        token=x_tessaris_intake_key, payload=request.model_dump(), remote_reference=x_forwarded_for)}

@router.post("/{workspace_id}/gmail/import")
def import_gmail(workspace_id: str, request: GmailImportRequest):
    return {"ok": True, **_call(service.import_gmail_messages,
        _workspace(workspace_id), **request.model_dump())}

@router.post("/{workspace_id}/gmail/poll")
def poll_gmail(workspace_id: str, request: GmailPollRequest):
    try:
        from backend.api.local_node_router import get_runtime
        messages = get_runtime().fetch_gmail_messages_readonly(
            query=request.query, max_results=request.max_results)
    except Exception as exc:
        raise HTTPException(status_code=409, detail=f"gmail_readonly_fetch_failed:{exc}") from exc
    result = _call(service.import_gmail_messages, _workspace(workspace_id),
                   messages=messages, imported_by_person_id=request.imported_by_person_id)
    return {"ok": True, **result, "messages_read": len(messages)}

@router.put("/{workspace_id}/polling")
def configure_polling(workspace_id: str, request: PollingConfigRequest):
    return {"ok": True, "polling": _call(service.configure_polling,
        _workspace(workspace_id), **request.model_dump())}

@router.post("/{workspace_id}/polling/run")
def run_polling(workspace_id: str):
    return {"ok": True, **_call(service.poll_sources, _workspace(workspace_id), force=True)}

@router.put("/{workspace_id}/whatsapp")
def configure_whatsapp(workspace_id: str, request: WhatsAppConfigRequest):
    return {"ok": True, "whatsapp": _call(service.configure_whatsapp,
        _workspace(workspace_id), **request.model_dump())}

@router.post("/whatsapp/{workspace_id}/{endpoint_id}")
async def whatsapp_webhook(workspace_id: str, endpoint_id: str, request: Request,
                           token: str = ""):
    raw = (await request.body()).decode("utf-8", errors="replace")
    payload = {key: values[-1] for key, values in parse_qs(raw, keep_blank_values=True).items()}
    result = _call(service.ingest_whatsapp_webhook, _workspace(workspace_id), endpoint_id,
                   token=token, payload=payload)
    return {"ok": True, **result}

@router.put("/{workspace_id}/agent-setup")
def configure_agent(workspace_id: str, request: AgentSetupRequest):
    return {"ok": True, "setup": _call(service.configure_agent, _workspace(workspace_id), **request.model_dump())}

@router.post("/{workspace_id}/knowledge")
def add_knowledge(workspace_id: str, request: KnowledgeRequest):
    return {"ok": True, "knowledge": _call(service.add_knowledge, _workspace(workspace_id), **request.model_dump())}

@router.post("/{workspace_id}/cases")
def create_case(workspace_id: str, request: CaseRequest):
    return {"ok": True, **_call(service.create_case, _workspace(workspace_id), **request.model_dump())}

@router.post("/{workspace_id}/cases/{case_id}/conversation")
def append_conversation(workspace_id: str, case_id: str, request: ConversationRequest):
    return {"ok": True, "case": _call(service.append_conversation, _workspace(workspace_id), case_id, **request.model_dump())}

@router.post("/{workspace_id}/cases/{case_id}/responses")
def prepare_response(workspace_id: str, case_id: str, request: ResponseRequest):
    return {"ok": True, "response": _call(service.prepare_response, _workspace(workspace_id), case_id, **request.model_dump())}

@router.post("/{workspace_id}/responses/{response_id}/approve")
def approve_response(workspace_id: str, response_id: str, request: ApprovalRequest):
    return {"ok": True, "response": _call(service.approve_response, _workspace(workspace_id), response_id, **request.model_dump())}

@router.post("/{workspace_id}/responses/{response_id}/gmail-draft")
def execute_response_draft(workspace_id: str, response_id: str, request: ApprovalRequest):
    return {"ok": True, "response": _call(service.execute_response_draft,
        _workspace(workspace_id), response_id,
        expected_response_hash=request.expected_response_hash,
        executed_by_person_id=request.approved_by_person_id)}

@router.post("/{workspace_id}/responses/{response_id}/whatsapp-send")
def execute_whatsapp_response(workspace_id: str, response_id: str, request: ApprovalRequest):
    return {"ok": True, "response": _call(service.execute_whatsapp_response,
        _workspace(workspace_id), response_id,
        expected_response_hash=request.expected_response_hash,
        executed_by_person_id=request.approved_by_person_id)}

@router.get("/{workspace_id}/voice")
def voice_status(workspace_id: str):
    return {"ok": True, **_call(voice.status, _workspace(workspace_id))}

@router.post("/{workspace_id}/voice/deploy")
def deploy_voice(workspace_id: str, request: VoiceDeployRequest):
    return {"ok": True, **_call(voice.deploy, _workspace(workspace_id), **request.model_dump())}

@router.get("/{workspace_id}/voice/verify")
def verify_voice(workspace_id: str):
    return {"ok": True, **_call(voice.verify, _workspace(workspace_id))}

@router.post("/{workspace_id}/voice/webhook")
async def voice_webhook(workspace_id: str, request: Request,
                        x_retell_signature: str = Header(default="")):
    raw = await request.body()
    return {"ok": True, "event": _call(voice.record_webhook, _workspace(workspace_id),
        raw_body=raw, signature=x_retell_signature)}

@router.post("/{workspace_id}/cases/{case_id}/escalate")
def escalate(workspace_id: str, case_id: str, request: EscalationRequest):
    return {"ok": True, **_call(service.escalate, _workspace(workspace_id), case_id, **request.model_dump())}

@router.post("/{workspace_id}/cases/{case_id}/resolve")
def resolve(workspace_id: str, case_id: str, request: ResolutionRequest):
    return {"ok": True, "case": _call(service.resolve, _workspace(workspace_id), case_id, **request.model_dump())}
