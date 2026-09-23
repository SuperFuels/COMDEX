"""HTTP API for the shared Work & Schedule workspace."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
import json
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.work_schedule_service import WorkScheduleService
from backend.modules.aion_business.runtime.work_notification_delivery import WorkNotificationDeliveryService


router = APIRouter(prefix="/api/aion/business/work-schedule", tags=["aion-business-work-schedule"])


class SaveRequest(BaseModel):
    model: dict[str, Any] = Field(default_factory=dict)
    expected_revision: int | None = None
    changed_by: str = "desktop_user"


class ActionRequest(BaseModel):
    operation: str
    fields: dict[str, Any] = Field(default_factory=dict)
    actor_id: str = "desktop_user"


class IntakeRequest(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    channel: str = "website"


class UploadRequest(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    data_base64: str
    actor_id: str = "desktop_user"


class DocumentRequest(BaseModel):
    kind: str
    actor_id: str = "desktop_user"
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    tax_rate: str = "0"


class InterpretRequest(BaseModel):
    text: str


class PortalAccessRequest(BaseModel):
    actor_id: str = "desktop_user"
    expires_days: int = 30


class PortalActionRequest(BaseModel):
    operation: str
    fields: dict[str, Any] = Field(default_factory=dict)


class ReminderDeliveryRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=160)


def _workspace(value: str) -> str:
    try:
        return canonical_business_id(value)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _error(error: Exception) -> HTTPException:
    code = str(error)
    if isinstance(error, LookupError):
        return HTTPException(status_code=404, detail=code)
    if code == "work_schedule_revision_conflict":
        return HTTPException(status_code=409, detail=code)
    return HTTPException(status_code=422, detail=code)


@router.get("/{workspace_id}")
def get_schedule(workspace_id: str) -> dict[str, Any]:
    key = _workspace(workspace_id)
    return {"ok": True, "workspace_id": key, "model": WorkScheduleService().get(key)}


@router.put("/{workspace_id}")
def save_schedule(workspace_id: str, request: SaveRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        model = WorkScheduleService().save(
            key, request.model, expected_revision=request.expected_revision, changed_by=request.changed_by,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/actions")
def schedule_action(workspace_id: str, request: ActionRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        model = WorkScheduleService().action(key, request.operation, request.fields, actor_id=request.actor_id)
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/intake")
def create_intake(workspace_id: str, request: IntakeRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        model = WorkScheduleService().create_intake(key, request.fields, channel=request.channel)
    except ValueError as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, "model": model}


@router.post("/{workspace_id}/items/{item_id}/files")
def upload_file(workspace_id: str, item_id: str, request: UploadRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkScheduleService().upload(
            key, item_id, filename=request.filename, content_type=request.content_type,
            data_base64=request.data_base64, actor_id=request.actor_id,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}


@router.post("/{workspace_id}/items/{item_id}/documents")
def generate_document(workspace_id: str, item_id: str, request: DocumentRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkScheduleService().generate_document(
            key, item_id, request.kind, actor_id=request.actor_id,
            line_items=request.line_items, tax_rate=request.tax_rate,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}


@router.get("/{workspace_id}/items/{item_id}/files/{document_id}")
def download_file(workspace_id: str, item_id: str, document_id: str) -> FileResponse:
    key = _workspace(workspace_id)
    try:
        path, document = WorkScheduleService().file_path(key, item_id, document_id)
    except LookupError as error:
        raise _error(error) from error
    return FileResponse(path, filename=document.get("name") or path.name, media_type=document.get("content_type"))


@router.post("/{workspace_id}/interpret")
def interpret_instruction(workspace_id: str, request: InterpretRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    return {"ok": True, "workspace_id": key, "interpretation": WorkScheduleService().interpret(request.text)}


@router.post("/{workspace_id}/items/{item_id}/portal-access")
def issue_portal_access(workspace_id: str, item_id: str, request: PortalAccessRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkScheduleService().issue_portal_access(
            key, item_id, actor_id=request.actor_id, expires_days=request.expires_days,
        )
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}


@router.post("/{workspace_id}/reminders/{reminder_id}/approve-and-send")
def approve_and_send_reminder(
    workspace_id: str,
    reminder_id: str,
    request: ReminderDeliveryRequest,
) -> dict[str, Any]:
    key = _workspace(workspace_id)
    try:
        result = WorkNotificationDeliveryService().send_approved(
            key,
            reminder_id,
            approved_by=request.approved_by,
        )
    except (ValueError, LookupError, PermissionError) as error:
        raise _error(error) from error
    return {"ok": True, "workspace_id": key, **result}



@router.get("/portal/{token}")
def customer_portal_view(token: str) -> dict[str, Any]:
    try:
        return {"ok": True, **WorkScheduleService().portal_view(token)}
    except (ValueError, LookupError) as error:
        raise _error(error) from error


@router.post("/portal/{token}/actions")
def customer_portal_action(token: str, request: PortalActionRequest) -> dict[str, Any]:
    try:
        return {"ok": True, **WorkScheduleService().portal_action(token, request.operation, request.fields)}
    except (ValueError, LookupError) as error:
        raise _error(error) from error


@router.get("/portal/{token}/page", response_class=HTMLResponse)
def customer_portal_page(token: str) -> HTMLResponse:
    try:
        payload = WorkScheduleService().portal_view(token)
    except (ValueError, LookupError) as error:
        raise _error(error) from error
    data = json.dumps(payload.get("item") or {}).replace("</", "<\\/")
    safe_token = json.dumps(token)
    return HTMLResponse(f"""<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Your booking</title><style>
body{{margin:0;background:#f4f8fb;color:#102a43;font:16px system-ui}}main{{max-width:720px;margin:40px auto;padding:0 18px}}header,section{{background:#fff;border:1px solid #ccd8e4;padding:24px;margin-bottom:14px}}header{{border-top:5px solid #0f766e}}small{{color:#0f766e;font-weight:800;letter-spacing:.14em}}h1{{margin:8px 0}}dl{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}dl div{{background:#f7fafc;padding:12px}}dt{{font-size:11px;color:#64748b}}dd{{margin:4px 0 0;font-weight:700}}button,input,textarea{{font:inherit;padding:11px;border:1px solid #9eb0bf}}button{{font-weight:800;background:#fff;cursor:pointer}}button.primary{{background:#0f766e;color:#fff;border-color:#0f766e}}form{{display:grid;gap:10px}}.actions{{display:flex;flex-wrap:wrap;gap:8px}}#message{{color:#0f766e;font-weight:700}}@media(max-width:520px){{dl{{grid-template-columns:1fr}}main{{margin:14px auto}}}}
</style></head><body><main><header><small>CUSTOMER PORTAL</small><h1 id=\"title\"></h1><p id=\"customer\"></p></header><section><dl><div><dt>Status</dt><dd id=\"status\"></dd></div><div><dt>Date and time</dt><dd id=\"date\"></dd></div><div><dt>Assigned to</dt><dd id=\"assignee\"></dd></div><div><dt>Location</dt><dd id=\"location\"></dd></div></dl></section><section><h2>Quote</h2><p id=\"quote\"></p><div class=\"actions\"><button class=\"primary\" data-action=\"approve_quote\">Approve quote</button><button data-action=\"decline_quote\">Decline quote</button></div></section><section><h2>Need to change the booking?</h2><form id=\"change\"><input name=\"date\" type=\"date\"><input name=\"time\" type=\"time\"><textarea name=\"note\" placeholder=\"Tell us what you need\"></textarea><div class=\"actions\"><button class=\"primary\" type=\"submit\">Request another time</button><button type=\"button\" data-action=\"request_cancellation\">Request cancellation</button></div></form><p id=\"message\"></p></section></main><script>
const item={data},token={safe_token};const text=(id,value)=>document.getElementById(id).textContent=value||'Not recorded';text('title',item.title);text('customer',item.customer);text('status',String(item.status||'').replaceAll('_',' '));text('date',[item.date,item.time].filter(Boolean).join(' · '));text('assignee',item.assignee);text('location',item.location);text('quote',item.quote?.number?`${{item.quote.number}} · £${{item.quote.total||item.quote.amount||'0.00'}} · ${{String(item.quote.status||'draft').replaceAll('_',' ')}}`:'No quote is ready yet.');async function act(operation,fields={{}}){{const response=await fetch(`/api/aion/business/work-schedule/portal/${{encodeURIComponent(token)}}/actions`,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{operation,fields}})}});const result=await response.json();if(!response.ok)throw new Error(result.detail||'Request failed');text('message','Your request has been recorded. The business can now review it.');}}document.addEventListener('click',event=>{{const button=event.target.closest('[data-action]');if(button)act(button.dataset.action).catch(error=>text('message',error.message));}});document.getElementById('change').addEventListener('submit',event=>{{event.preventDefault();act('request_reschedule',Object.fromEntries(new FormData(event.target))).catch(error=>text('message',error.message));}});
</script></body></html>""")


# A website can post a booking request without gaining access to the schedule.
# A deployment should place its usual CSRF/rate-limit layer in front of this route.
@router.post("/public/{workspace_id}/booking")
def public_booking(workspace_id: str, request: IntakeRequest) -> dict[str, Any]:
    key = _workspace(workspace_id)
    model = WorkScheduleService().create_intake(key, request.fields, channel="website")
    created = model.get("intake", [])[-1]
    return {"ok": True, "booking_reference": created.get("id"), "state": created.get("state")}
