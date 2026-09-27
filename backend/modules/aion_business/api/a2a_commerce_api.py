from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.aion_flow_session_authority import AionFlowSessionAuthority, VerifiedAionFlowSession
from backend.modules.aion_business.runtime.a2a_commerce_service import A2ACommerceService

public_router = APIRouter(tags=["agent-commerce-public"])
internal_router = APIRouter(prefix="/api/aion/business/a2a", tags=["agent-commerce-internal"])
_authority = AionFlowSessionAuthority()
_MARKET_PAGE = Path(__file__).resolve().parents[1] / "static" / "tessaris-market.html"

def service() -> A2ACommerceService: return A2ACommerceService()

async def require_session(request: Request) -> VerifiedAionFlowSession:
    try:
        body = await request.body(); target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return _authority.verify(method=request.method, target=target, body=body, headers=request.headers)
    except PermissionError as exc: raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc: raise HTTPException(status_code=503, detail=str(exc)) from exc

async def require_agent(request: Request, x_a2a_agent_id: str = Header(), x_a2a_timestamp: str = Header(),
                        x_a2a_nonce: str = Header(), x_a2a_signature: str = Header()) -> dict:
    try:
        commerce = service()
        commerce.check_rate_limit(bucket="signed_request", subject=x_a2a_agent_id, limit=240, window_seconds=60)
        return commerce.authenticate(agent_id=x_a2a_agent_id, timestamp=x_a2a_timestamp, nonce=x_a2a_nonce,
            signature_base64=x_a2a_signature, method=request.method, path=request.url.path, body=await request.body())
    except PermissionError as exc: raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

class ChallengeInput(BaseModel):
    agent_id: str = Field(min_length=1, max_length=160); agent_name: str = Field(min_length=1, max_length=160); public_key_base64: str = Field(min_length=40, max_length=100)
class VerifyInput(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=160); signature_base64: str = Field(min_length=40, max_length=200)
class TaskInput(BaseModel):
    business_id: str = Field(min_length=1, max_length=160); message: str = Field(min_length=1, max_length=4000)
    intent: dict = Field(default_factory=dict); authority: dict = Field(default_factory=dict); context_id: str | None = Field(default=None, max_length=160)
class MessageInput(BaseModel): text: str = Field(min_length=1, max_length=4000)
class ApproveInput(BaseModel):
    offer_hash: str = Field(min_length=64, max_length=64); human_confirmed: bool = False; confirmation: str = Field(default="", max_length=100)
class ProfileInput(BaseModel):
    business_name: str = Field(min_length=1, max_length=200); description: str = Field(default="", max_length=1000)
    enabled: bool = True; facilitation_fee_bps: int = Field(default=0, ge=0, le=5000); services: list[dict] = Field(default_factory=list)
class OfferInput(BaseModel):
    service_price_minor: int = Field(ge=0); tax_minor: int = Field(default=0, ge=0); currency: str = Field(default="GBP", min_length=3, max_length=3)
    scope: str = Field(default="", max_length=4000); terms: str = Field(default="", max_length=4000); availability: str = Field(default="", max_length=300); expires_at: str | None = None
class MarketSearchInput(BaseModel):
    service: str = Field(min_length=1, max_length=300); service_id: str | None = Field(default=None, max_length=160)
    outcome: str = Field(min_length=1, max_length=4000); location: str = Field(default="", max_length=300)
    requested_window: str = Field(default="", max_length=200); budget_minor: int = Field(default=0, ge=0)
    currency: str = Field(default="GBP", min_length=3, max_length=3); authority: dict = Field(default_factory=dict)
class IntakeTurnInput(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
class IntakeAttachmentInput(BaseModel):
    filename: str = Field(min_length=1, max_length=240); media_type: str = Field(min_length=1, max_length=120)
    data_base64: str = Field(min_length=4, max_length=12_000_000)

@public_router.get("/.well-known/agent-card.json")
def agent_card(business_id: str = Query(..., min_length=1, max_length=160)):
    try: return service().agent_card(business_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@public_router.get("/market", include_in_schema=False)
def market_page():
    return FileResponse(_MARKET_PAGE, media_type="text/html", headers={"Cache-Control": "no-store"})

@public_router.get("/agentmap.json")
@public_router.get("/.well-known/agentmap.json")
def agentmap(business_id: str = Query(..., min_length=1, max_length=160)):
    try: return service().agentmap(business_id)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/agents/challenge")
def challenge(value: ChallengeInput, request: Request):
    try:
        commerce = service(); commerce.check_rate_limit(bucket="challenge", subject=request.client.host if request.client else "unknown", limit=20, window_seconds=600)
        return commerce.issue_challenge(**value.model_dump())
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=429, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/agents/verify")
def verify(value: VerifyInput, request: Request):
    try:
        commerce = service(); commerce.check_rate_limit(bucket="verify", subject=request.client.host if request.client else "unknown", limit=30, window_seconds=600)
        return commerce.verify_challenge(**value.model_dump())
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=401, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/tasks")
def create_task(value: TaskInput, agent: dict = Depends(require_agent), idempotency_key: str = Header(min_length=8, max_length=160)):
    try: return service().create_task(agent_id=agent["agent_id"], payload=value.model_dump(), idempotency_key=idempotency_key)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/market/search")
def search_market(value: MarketSearchInput, agent: dict = Depends(require_agent), idempotency_key: str = Header(min_length=8, max_length=160)):
    try: return service().search_market(agent_id=agent["agent_id"], payload=value.model_dump(), idempotency_key=idempotency_key)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/intake/sessions")
def start_intake(value: IntakeTurnInput, agent: dict = Depends(require_agent), idempotency_key: str = Header(min_length=8, max_length=160)):
    try: return service().start_intake(agent_id=agent["agent_id"], text=value.text, idempotency_key=idempotency_key)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/intake/sessions/{session_id}/turns")
def continue_intake(session_id: str, value: IntakeTurnInput, agent: dict = Depends(require_agent)):
    try: return service().continue_intake(session_id, agent_id=agent["agent_id"], text=value.text)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/intake/sessions/{session_id}/attachments")
def add_intake_attachment(session_id: str, value: IntakeAttachmentInput, agent: dict = Depends(require_agent)):
    try: return service().add_intake_attachment(session_id, agent_id=agent["agent_id"], **value.model_dump())
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@public_router.get("/api/a2a/v1/market/{market_id}")
def market_status(market_id: str, agent: dict = Depends(require_agent)):
    try: return service().get_market(market_id, agent_id=agent["agent_id"])
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc

@public_router.get("/api/a2a/v1/tasks/{task_id}")
def task_status(task_id: str, agent: dict = Depends(require_agent)):
    try: return service().get_task(task_id, agent_id=agent["agent_id"])
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/tasks/{task_id}/messages")
def task_message(task_id: str, value: MessageInput, agent: dict = Depends(require_agent)):
    try: return service().add_message(task_id, agent_id=agent["agent_id"], text=value.text)
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc

@public_router.post("/api/a2a/v1/tasks/{task_id}/approve")
def approve(task_id: str, value: ApproveInput, agent: dict = Depends(require_agent)):
    try: return service().approve(task_id, agent_id=agent["agent_id"], **value.model_dump())
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc

@internal_router.post("/profile")
def configure(value: ProfileInput, session: VerifiedAionFlowSession = Depends(require_session)):
    try: return {"ok": True, "profile": service().configure_business(session.workspace_id, value.model_dump())}
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc

@internal_router.post("/status")
def status(session: VerifiedAionFlowSession = Depends(require_session)):
    return {"ok": True, "status": service().status(session.workspace_id, session.workspace_id)}

@internal_router.post("/inbox")
def inbox(session: VerifiedAionFlowSession = Depends(require_session)):
    return {"ok": True, "tasks": service().inbox(session.workspace_id)}

@internal_router.post("/tasks/{task_id}/offers")
def create_offer(task_id: str, value: OfferInput, session: VerifiedAionFlowSession = Depends(require_session)):
    try: return {"ok": True, "task": service().create_offer(task_id, business_id=session.workspace_id, actor_id=session.person_id, payload=value.model_dump())}
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc: raise HTTPException(status_code=403, detail=str(exc)) from exc
