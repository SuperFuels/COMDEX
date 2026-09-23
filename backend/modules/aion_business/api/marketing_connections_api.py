from __future__ import annotations

from html import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.marketing_connection_service import MarketingConnectionService, PROVIDERS
from backend.modules.aion_business.runtime.organization_authority_service import OrganizationAuthorityService


router = APIRouter(prefix="/api/aion/marketing/connections", tags=["aion-marketing-connections"])
service = MarketingConnectionService()
authority = OrganizationAuthorityService()


class ConnectRequest(BaseModel):
    acting_person_id: str = "desktop_user"
    permission_tier: str = "analytics"


class SelectionRequest(BaseModel):
    acting_person_id: str = "desktop_user"
    selected_accounts: dict[str, str] = Field(default_factory=dict)


class ActorRequest(BaseModel):
    acting_person_id: str = "desktop_user"


def _authorize(workspace_id: str, person_id: str) -> None:
    model = authority.get(workspace_id)
    # Until sign-in is bound to HR identities, an empty single-user workspace has
    # one explicit desktop-owner bootstrap. It disappears as soon as people exist.
    active_people = [x for x in model.get("people", []) if x.get("status") == "active"]
    if not active_people and person_id == "desktop_user":
        return
    decision = authority.access_decision(workspace_id, person_id=person_id,
                                         capability="marketing.connect_accounts",
                                         department_id="department.marketing")
    if not decision.get("allowed"):
        raise HTTPException(status_code=403, detail={"error": "marketing_connection_authority_denied", "decision": decision})


@router.get("/{workspace_id}")
def list_connections(workspace_id: str):
    return {"workspace_id": workspace_id, "connections": service.catalog(workspace_id),
            "permission_tiers": ["analytics", "organic", "advertising"],
            "external_writes_enabled": False}


@router.post("/{workspace_id}/{provider}/connect")
def connect(workspace_id: str, provider: str, payload: ConnectRequest):
    try:
        _authorize(workspace_id, payload.acting_person_id)
        return service.begin(workspace_id, provider, tier=payload.permission_tier,
                             acting_person_id=payload.acting_person_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{provider}/callback", response_class=HTMLResponse)
async def callback(provider: str, state: str = "", code: str = "", error: str = ""):
    if error:
        return HTMLResponse(f"<h2>Connection cancelled</h2><p>{escape(error)}</p><p>You may close this window.</p>", status_code=400)
    try:
        result = await service.complete(provider, state=state, code=code)
        return HTMLResponse(f"<h2>{escape(result['label'])} connected</h2><p>Return to Tessaris to select the account and run the read-only exam.</p>")
    except Exception as exc:
        return HTMLResponse(f"<h2>Connection failed</h2><p>{type(exc).__name__}</p><p>No content was published and no spend occurred.</p>", status_code=400)


@router.post("/{workspace_id}/{provider}/select")
def select(workspace_id: str, provider: str, payload: SelectionRequest):
    try:
        _authorize(workspace_id, payload.acting_person_id)
        return service.select_accounts(workspace_id, provider, payload.selected_accounts,
                                       acting_person_id=payload.acting_person_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{workspace_id}/{provider}/exam")
async def exam(workspace_id: str, provider: str, payload: ActorRequest):
    try:
        _authorize(workspace_id, payload.acting_person_id)
        return await service.exam(workspace_id, provider, acting_person_id=payload.acting_person_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{workspace_id}/{provider}")
def disconnect(workspace_id: str, provider: str, acting_person_id: str = "desktop_user"):
    try:
        _authorize(workspace_id, acting_person_id)
        return service.disconnect(workspace_id, provider, acting_person_id=acting_person_id)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
