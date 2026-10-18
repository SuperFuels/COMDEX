"""HTTP API for governed lead-to-revenue completion."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.sales_completion_service import SalesCompletionService

router = APIRouter(prefix="/api/aion/sales-completion", tags=["aion-sales-completion"])
service = SalesCompletionService()


def _workspace(value: str) -> str: return canonical_business_id(value)
def _call(method, *args, **kwargs):
    try: return method(*args, **kwargs)
    except FileNotFoundError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


class AvailabilityRequest(BaseModel):
    person_id: str
    timezone: str = "Europe/Madrid"
    weekly_hours: dict[str, list[list[str]]] = Field(default_factory=dict)
    buffer_minutes: int = Field(default=15, ge=0, le=180)
    changed_by_person_id: str

class BookingRequest(BaseModel):
    starts_at: str; duration_minutes: int = Field(default=30, ge=10, le=480)
    assigned_person_id: str; channel: str = "Phone"; prepared_by_person_id: str

class ExactApprovalRequest(BaseModel):
    expected_hash: str; approved_by_person_id: str

class QuoteRequest(BaseModel):
    lines: list[dict[str, Any]]; valid_days: int = Field(default=14, ge=1, le=180)
    terms: str = "Scope changes require a revised written quote."
    prepared_by_person_id: str

class AcceptanceRequest(BaseModel):
    evidence_reference: str; recorded_by_person_id: str

class HandoffRequest(BaseModel):
    operations_owner_person_id: str; created_by_person_id: str

class MessageRequest(BaseModel):
    channel: str; purpose: str = "follow_up"; subject: str | None = None
    body: str; prepared_by_person_id: str

class ContactFallbackRequest(BaseModel):
    call_draft_id: str
    provider_call_id: str = ""
    provider_status: str
    disconnection_reason: str | None = None
    prepared_by_person_id: str

class WrittenContinuationRequest(BaseModel):
    call_draft_id: str
    confirmed_fields: dict[str, Any] = Field(default_factory=dict)
    channel: str = "email"
    prepared_by_person_id: str

class CampaignRequest(BaseModel):
    name: str; channel: str; contacts: list[dict[str, Any]]
    variant: str = "control"; created_by_person_id: str

class OutcomeRequest(BaseModel):
    disposition: str; value: float = 0; reason: str = ""; variant: str = "control"
    authority_reference: str; recorded_by_person_id: str

class ExperimentRequest(BaseModel):
    control_variant: str = "control"; challenger_variant: str = "challenger"
    minimum_samples: int = Field(default=20, ge=1, le=10000); evaluated_by_person_id: str


@router.get("/{workspace_id}")
def workspace(workspace_id: str): return {"ok": True, **_call(service.workspace, _workspace(workspace_id))}

@router.put("/{workspace_id}/availability")
def availability(workspace_id: str, request: AvailabilityRequest):
    return {"ok": True, "availability": _call(service.set_availability, _workspace(workspace_id), **request.model_dump())}

@router.post("/{workspace_id}/opportunities/{opportunity_id}/bookings")
def prepare_booking(workspace_id: str, opportunity_id: str, request: BookingRequest):
    return {"ok": True, "booking": _call(service.prepare_booking, _workspace(workspace_id), opportunity_id, **request.model_dump())}

@router.post("/{workspace_id}/bookings/{booking_id}/approve")
def approve_booking(workspace_id: str, booking_id: str, request: ExactApprovalRequest):
    return {"ok": True, "booking": _call(service.approve_booking, _workspace(workspace_id), booking_id,
            expected_booking_hash=request.expected_hash, approved_by_person_id=request.approved_by_person_id)}

@router.post("/{workspace_id}/bookings/{booking_id}/execute")
def execute_booking(workspace_id: str, booking_id: str, request: ExactApprovalRequest):
    return {"ok": True, "booking": _call(service.execute_booking, _workspace(workspace_id), booking_id,
            expected_booking_hash=request.expected_hash, executed_by_person_id=request.approved_by_person_id)}

@router.post("/{workspace_id}/opportunities/{opportunity_id}/quotes")
def prepare_quote(workspace_id: str, opportunity_id: str, request: QuoteRequest):
    return {"ok": True, "quote": _call(service.prepare_quote, _workspace(workspace_id), opportunity_id, **request.model_dump())}

@router.post("/{workspace_id}/quotes/{quote_id}/approve")
def approve_quote(workspace_id: str, quote_id: str, request: ExactApprovalRequest):
    return {"ok": True, "quote": _call(service.approve_quote, _workspace(workspace_id), quote_id,
            expected_quote_hash=request.expected_hash, approved_by_person_id=request.approved_by_person_id)}

@router.post("/{workspace_id}/quotes/{quote_id}/acceptance")
def acceptance(workspace_id: str, quote_id: str, request: AcceptanceRequest):
    return {"ok": True, "quote": _call(service.record_quote_acceptance, _workspace(workspace_id), quote_id, **request.model_dump())}

@router.post("/{workspace_id}/quotes/{quote_id}/handoffs")
def handoffs(workspace_id: str, quote_id: str, request: HandoffRequest):
    return {"ok": True, **_call(service.create_handoffs, _workspace(workspace_id), quote_id, **request.model_dump())}

@router.post("/{workspace_id}/opportunities/{opportunity_id}/messages")
def message(workspace_id: str, opportunity_id: str, request: MessageRequest):
    return {"ok": True, "message": _call(service.prepare_message, _workspace(workspace_id), opportunity_id, **request.model_dump())}

@router.post("/{workspace_id}/opportunities/{opportunity_id}/contact-fallback")
def contact_fallback(workspace_id: str, opportunity_id: str, request: ContactFallbackRequest):
    return {"ok": True, "contact_step": _call(
        service.prepare_contact_fallback, _workspace(workspace_id), opportunity_id,
        **request.model_dump())}

@router.post("/{workspace_id}/opportunities/{opportunity_id}/written-continuation")
def written_continuation(workspace_id: str, opportunity_id: str,
                         request: WrittenContinuationRequest):
    return {"ok": True, "continuation": _call(
        service.prepare_written_goal_continuation, _workspace(workspace_id), opportunity_id,
        **request.model_dump())}

@router.post("/{workspace_id}/messages/{message_id}/approve")
def approve_message(workspace_id: str, message_id: str, request: ExactApprovalRequest):
    return {"ok": True, "message": _call(service.approve_message, _workspace(workspace_id), message_id,
            expected_message_hash=request.expected_hash, approved_by_person_id=request.approved_by_person_id)}

@router.post("/{workspace_id}/messages/{message_id}/execute")
def execute_message(workspace_id: str, message_id: str, request: ExactApprovalRequest):
    return {"ok": True, "message": _call(service.execute_message, _workspace(workspace_id), message_id,
            expected_message_hash=request.expected_hash, executed_by_person_id=request.approved_by_person_id)}

@router.post("/{workspace_id}/campaigns")
def campaign(workspace_id: str, request: CampaignRequest):
    return {"ok": True, "campaign": _call(service.create_campaign, _workspace(workspace_id), **request.model_dump())}

@router.post("/{workspace_id}/opportunities/{opportunity_id}/outcomes")
def outcome(workspace_id: str, opportunity_id: str, request: OutcomeRequest):
    return {"ok": True, "outcome": _call(service.record_outcome, _workspace(workspace_id), opportunity_id, **request.model_dump())}

@router.post("/{workspace_id}/experiments/evaluate")
def experiment(workspace_id: str, request: ExperimentRequest):
    return {"ok": True, "experiment": _call(service.evaluate_experiment, _workspace(workspace_id), **request.model_dump())}
