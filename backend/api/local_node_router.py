from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter
from fastapi import File, Query, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.modules.local_node.contracts_local_node import (
    DeploymentMode,
    LocalNodeConfig,
    utc_now_iso,
)
from backend.modules.local_node.local_node_runtime import LocalNodeRuntime


router = APIRouter(prefix="/api/local-node", tags=["local-node"])


_RUNTIME: Optional[LocalNodeRuntime] = None


def _build_runtime() -> LocalNodeRuntime:
    config = LocalNodeConfig(
        node_id="node_mac_local_01",
        workspace_id="costa-conexion",
        deployment_mode=DeploymentMode.LOCAL_FIRST,
    )
    runtime = LocalNodeRuntime(config)
    runtime.start()
    return runtime


def get_runtime() -> LocalNodeRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = _build_runtime()
    return _RUNTIME


def reset_runtime() -> LocalNodeRuntime:
    global _RUNTIME
    try:
        if _RUNTIME is not None:
            _RUNTIME.stop()
    except Exception:
        pass

    _RUNTIME = _build_runtime()
    return _RUNTIME


def _safe_filename(value: str) -> str:
    raw = Path(value or "upload").name.strip()
    if not raw:
        raw = "upload"

    safe = "".join(
        char if char.isalnum() or char in {".", "-", "_"} else "-"
        for char in raw
    ).strip(".-_")

    return safe or "upload"


def _runtime_upload_dir(runtime: LocalNodeRuntime) -> Path:
    path = Path(runtime.base_dir) / "uploads" / "marketing_assets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _runtime_asset_paths(runtime: LocalNodeRuntime, file_name: str) -> Dict[str, str]:
    file_path = _runtime_upload_dir(runtime) / file_name

    try:
        relative = file_path.relative_to(Path(runtime.base_dir))
        runtime_url = f"/runtime/{relative.as_posix()}"
    except Exception:
        runtime_url = f"/runtime/uploads/marketing_assets/{file_name}"

    return {
        "file_path": str(file_path),
        "url": runtime_url,
    }


class TrainTaskTestRunRequest(BaseModel):
    sample_email: Optional[Dict[str, Any]] = None


class TrainTaskWorkflowSaveRequest(BaseModel):
    workflow: Dict[str, Any]


class ToggleTrainTaskWorkflowRequest(BaseModel):
    enabled: bool


class ResolveTrainTaskApprovalRequest(BaseModel):
    approve: bool
    resolved_by: str = "operations_agents_desktop"
    resolution_note: Optional[str] = None


class HubSpotMcpReadonlyToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


class GenericWorkflowValidationRequest(BaseModel):
    workflow: Dict[str, Any]


class GenericWorkflowTestRunRequest(BaseModel):
    workflow: Dict[str, Any]
    trigger_payload: Dict[str, Any] = {}
    workspace_context: Dict[str, Any] = {}


class GenericWorkflowSaveRequest(BaseModel):
    workflow: Dict[str, Any]
    publish: bool = False
    saved_by: str = "operations_agents_desktop"


class GenericWorkflowRunByIdRequest(BaseModel):
    workflow_id: str
    trigger_payload: Dict[str, Any] = {}
    workspace_context: Dict[str, Any] = {}
    executed_by: str = "operations_agents_desktop"


class ExecuteTrainTaskApprovalRequest(BaseModel):
    executed_by: str = "operations_agents_desktop"


class ExternalToolDryRunRequest(BaseModel):
    tool_id: str
    payload: Dict[str, Any] = {}
    workflow_id: Optional[str] = None
    run_id: Optional[str] = None


class ExternalToolWorkflowTestRequest(BaseModel):
    workflow_id: Optional[str] = None
    tool_id: str = "tool.stackone.crm.contact_upsert.v1"
    payload: Dict[str, Any] = {}


class GmailDryRunMessageRequest(BaseModel):
    id: Optional[str] = None
    message_id: Optional[str] = None
    from_: Optional[str] = Field(default=None, alias="from")
    sender: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    snippet: Optional[str] = None

    class Config:
        populate_by_name = True


class GmailPollDryRunRequest(BaseModel):
    messages: List[GmailDryRunMessageRequest] = Field(default_factory=list)


class HubSpotConnectorConfigUpdateRequest(BaseModel):
    account_id: Optional[str] = None
    auth_status: Optional[str] = None
    connector_health: Optional[str] = None
    scopes: Optional[List[str]] = None
    portal_id: Optional[str] = None
    portal_name: Optional[str] = None
    dry_run_only: Optional[bool] = None
    external_writes_enabled: Optional[bool] = None
    last_error: Optional[str] = None


class GmailConnectorConfigUpdateRequest(BaseModel):
    account_id: Optional[str] = None
    auth_status: Optional[str] = None
    polling_enabled: Optional[bool] = None
    search_scope: Optional[str] = None
    unread_only: Optional[bool] = None
    labels: List[str] = Field(default_factory=list)
    folders: List[str] = Field(default_factory=list)


class CreativeAsset(BaseModel):
    id: Optional[str] = None
    type: str = "product"
    label: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    notes: Optional[str] = None


class CreativeDirection(BaseModel):
    asset_intent: Optional[str] = None
    product_name: Optional[str] = None
    offer_price: Optional[str] = None
    offer_details: Optional[str] = None
    usage_notes: Optional[str] = None
    style_direction: Optional[str] = None
    creative_direction: Optional[str] = None


class LaunchRunRequest(BaseModel):
    workflow_id: str
    operator_id: str
    department_key: str
    context: Dict[str, Any] = Field(default_factory=dict)


class LaunchWorkflowRequest(BaseModel):
    workflow_definition_id: str
    agent_definition_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class LaunchMarketingSuggestionRequest(BaseModel):
    brief: str = "Draft a Facebook post and simple carousel for spring telecom upgrade offer."

    objective: Optional[str] = None
    funnel_goal: Optional[str] = None
    target_audience: Optional[str] = None
    persona: Optional[str] = None
    offer: Optional[str] = None

    channels: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    hard_rules: List[str] = Field(default_factory=list)
    guidance_notes: List[str] = Field(default_factory=list)
    campaign_notes: List[str] = Field(default_factory=list)

    creative_assets: List[CreativeAsset] = Field(default_factory=list)
    creative_direction: CreativeDirection = Field(default_factory=CreativeDirection)

    brand_foundation: Optional[Dict[str, Any]] = None
    brandFoundationState: Optional[Dict[str, Any]] = None
    brand_foundation_state: Optional[Dict[str, Any]] = None
    brand_map: Optional[Dict[str, Any]] = None
    brandMap: Optional[Dict[str, Any]] = None


class DesktopAssistantAskRequest(BaseModel):
    provider: str = "gemma4"
    prompt: str

    active_tab: Optional[str] = None
    context_mode: Optional[str] = None
    mode: Optional[str] = None
    instruction: Optional[str] = None
    target_path: Optional[str] = None

    selected_live_run_id: Optional[str] = None
    selected_seat_id: Optional[str] = None
    selected_inspector_target: Optional[Dict[str, Any]] = None

    marketing_form: Dict[str, Any] = Field(default_factory=dict)
    brand_foundation_state: Dict[str, Any] = Field(default_factory=dict)
    dashboard_summary: Dict[str, Any] = Field(default_factory=dict)
    boardroom_snapshot: Dict[str, Any] = Field(default_factory=dict)
    operations_flow_snapshot: Dict[str, Any] = Field(default_factory=dict)
    live_agents_snapshot: Dict[str, Any] = Field(default_factory=dict)
    workspace_context: Dict[str, Any] = Field(default_factory=dict)

    runs: List[Dict[str, Any]] = Field(default_factory=list)
    approvals: List[Dict[str, Any]] = Field(default_factory=list)
    audit: List[Dict[str, Any]] = Field(default_factory=list)
    scheduler: Dict[str, Any] = Field(default_factory=dict)
    status: Dict[str, Any] = Field(default_factory=dict)


class ResolveApprovalRequest(BaseModel):
    approve: bool
    resolved_by: str
    resolution_note: Optional[str] = None


class CancelRunRequest(BaseModel):
    reason: str = "cancelled"


class MarkSyncRequest(BaseModel):
    ack_token: Optional[str] = None


class ApplyCommandsRequest(BaseModel):
    commands: List[Dict[str, Any]] = Field(default_factory=list)


def _merge_aion_workspace_payload(request: DesktopAssistantAskRequest) -> Dict[str, Any]:
    payload = request.model_dump(mode="json")

    workspace_context = payload.get("workspace_context") or {}
    if isinstance(workspace_context, dict):
        payload["dashboard_summary"] = (
            payload.get("dashboard_summary")
            or workspace_context.get("dashboard_summary")
            or {}
        )
        payload["boardroom_snapshot"] = (
            payload.get("boardroom_snapshot")
            or workspace_context.get("boardroom_snapshot")
            or {}
        )
        payload["brand_foundation_state"] = (
            payload.get("brand_foundation_state")
            or workspace_context.get("brand_foundation_state")
            or {}
        )
        payload["marketing_form"] = (
            payload.get("marketing_form")
            or workspace_context.get("marketing_form")
            or {}
        )
        payload["operations_flow_snapshot"] = (
            payload.get("operations_flow_snapshot")
            or workspace_context.get("operations_flow_snapshot")
            or {}
        )
        payload["live_agents_snapshot"] = (
            payload.get("live_agents_snapshot")
            or workspace_context.get("live_agents_snapshot")
            or {}
        )
        payload["scheduler"] = (
            payload.get("scheduler")
            or workspace_context.get("scheduler")
            or {}
        )
        payload["status"] = (
            payload.get("status")
            or workspace_context.get("status")
            or {}
        )
        payload["runs"] = payload.get("runs") or workspace_context.get("runs") or []
        payload["approvals"] = (
            payload.get("approvals")
            or workspace_context.get("approvals")
            or []
        )
        payload["audit"] = payload.get("audit") or workspace_context.get("audit") or []

    payload["active_tab"] = payload.get("active_tab") or "aion_chat"
    payload["context_mode"] = (
        payload.get("context_mode")
        or payload.get("mode")
        or "business_workspace"
    )

    return payload


@router.get("/status")
def get_status() -> Dict[str, Any]:
    return get_runtime().status()


@router.post("/runtime/reset")
def reset_local_runtime() -> Dict[str, Any]:
    runtime = reset_runtime()
    return {
        "ok": True,
        "detail": "Local node runtime reset",
        "status": runtime.status(),
    }


@router.get("/health")
def get_health() -> Dict[str, Any]:
    runtime = get_runtime()
    return {
        "ok": True,
        "health": runtime.health.get_status(),
    }


@router.get("/recovery")
def get_recovery_payload() -> Dict[str, Any]:
    return get_runtime().recovery_payload()


@router.get("/dashboard/summary")
def get_dashboard_summary() -> Dict[str, Any]:
    return get_runtime().dashboard_summary()


@router.get("/marketing/stream")
def get_marketing_stream() -> Dict[str, Any]:
    return get_runtime().marketing_stream_summary()


@router.post("/assistant/ask")
def ask_desktop_assistant(request: DesktopAssistantAskRequest) -> Dict[str, Any]:
    payload = _merge_aion_workspace_payload(request)
    return get_runtime().ask_desktop_assistant(**payload)


@router.post("/aion/chat")
def aion_chat(request: DesktopAssistantAskRequest) -> Dict[str, Any]:
    payload = _merge_aion_workspace_payload(request)
    payload["active_tab"] = "aion_chat"
    payload["context_mode"] = payload.get("context_mode") or "business_workspace"
    return get_runtime().ask_desktop_assistant(**payload)


@router.post("/train-tasks/seed/customer-onboarding")
def seed_customer_onboarding_train_task() -> Dict[str, Any]:
    return get_runtime().seed_customer_onboarding_train_task()


@router.get("/tools")
def list_aion_tools() -> Dict[str, Any]:
    return get_runtime().list_tools()


@router.get("/tools/external")
def list_external_aion_tools() -> Dict[str, Any]:
    return get_runtime().list_external_tools()


@router.post("/tools/external/dry-run")
def dry_run_external_aion_tool(
    request: ExternalToolDryRunRequest,
) -> Dict[str, Any]:
    return get_runtime().dry_run_external_tool(
        tool_id=request.tool_id,
        payload=request.payload,
        workflow_id=request.workflow_id or "",
        run_id=request.run_id or "",
    )


@router.post("/tools/external/workflow-test")
def run_external_tool_workflow_test(
    request: ExternalToolWorkflowTestRequest,
) -> Dict[str, Any]:
    return get_runtime().run_external_tool_workflow_test(
        workflow_id=request.workflow_id or "workflow_phase5_stackone_tool_reference_test",
        tool_id=request.tool_id,
        payload=request.payload or None,
    )


@router.get("/connectors/hubspot/health")
def get_hubspot_connector_health() -> Dict[str, Any]:
    return get_runtime().get_hubspot_connector_health()


@router.get("/connectors/hubspot/mcp/connect-url")
def get_hubspot_mcp_connect_url() -> Dict[str, Any]:
    return get_runtime().get_hubspot_mcp_connect_url()


@router.get("/connectors/hubspot/mcp/oauth/callback")
def handle_hubspot_mcp_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    return get_runtime().handle_hubspot_mcp_oauth_callback(
        code=code or "",
        state=state or "",
        error=error or "",
    )


@router.post("/connectors/hubspot/config")
def update_hubspot_connector_config(
    request: HubSpotConnectorConfigUpdateRequest,
) -> Dict[str, Any]:
    return get_runtime().update_hubspot_connector_config(
        updates=request.model_dump(mode="json", exclude_none=True),
    )


@router.post("/connectors/hubspot/disconnect")
def disconnect_hubspot_connector() -> Dict[str, Any]:
    return get_runtime().disconnect_hubspot_connector()


@router.get("/connectors/gmail/health")
def get_gmail_connector_health() -> Dict[str, Any]:
    return get_runtime().get_gmail_connector_health()


@router.get("/connectors/gmail/connect-url")
def get_gmail_connect_url() -> Dict[str, Any]:
    return get_runtime().get_gmail_connect_url()


@router.get("/connectors/gmail/oauth/callback", response_class=HTMLResponse)
def handle_gmail_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
) -> HTMLResponse:
    result = get_runtime().handle_gmail_oauth_callback(
        code=code or "",
        state=state or "",
        error=error or "",
    )

    ok = bool(result.get("ok"))
    title = "Gmail connected" if ok else "Gmail connection failed"
    message = (
        "Gmail has been connected to the Tessaris Vault. You can close this window and return to Tessaris, then click Refresh Gmail Status."
        if ok
        else str(result.get("message") or result.get("reason") or "Gmail could not be connected.")
    )
    status = "CONNECTED" if ok else "FAILED"


    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #fbf2e7;
      color: #191919;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .card {{
      width: min(620px, calc(100vw - 48px));
      border: 1px solid #d7cbbb;
      background: #fffaf3;
      padding: 34px;
      box-shadow: 0 18px 50px rgba(0,0,0,.12);
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: .18em;
      font-weight: 800;
      color: #1398a6;
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 30px;
    }}
    p {{
      margin: 0 0 22px;
      font-size: 16px;
      line-height: 1.45;
      color: #555;
    }}
    .status {{
      display: inline-block;
      border: 1px solid #191919;
      padding: 8px 12px;
      font-weight: 800;
      letter-spacing: .12em;
      font-size: 12px;
      margin-bottom: 18px;
    }}
    button {{
      margin-top: 18px;
      width: 100%;
      padding: 14px 18px;
      border: 1px solid #191919;
      background: #191919;
      color: white;
      font-weight: 800;
      letter-spacing: .08em;
      cursor: pointer;
    }}
  </style>
</head>
<body>
  <main class="card">
    <div class="eyebrow">TESSARIS VAULT</div>
    <h1>{title}</h1>
    <p>
      Gmail has been connected to the Tessaris Vault.
      Return to the Tessaris app. The Vault will refresh automatically.
    </p>
    <span class="status">{status}</span>
    <button onclick="window.close()">Close window</button>
  </main>

  <script>
    try {{
      if (window.opener && window.opener.postMessage) {{
        window.opener.postMessage({{
          type: "aion:gmail_oauth_connected",
          ok: true,
          status: "connected"
        }}, "*");
      }}
    }} catch (error) {{}}
  </script>
</body>
</html>"""

    return HTMLResponse(html)


@router.post("/connectors/gmail/disconnect")
def disconnect_gmail_connector() -> Dict[str, Any]:
    return get_runtime().disconnect_gmail_connector()


@router.post("/connectors/gmail/config")
def update_gmail_connector_config(
    request: GmailConnectorConfigUpdateRequest,
) -> Dict[str, Any]:
    return get_runtime().update_gmail_connector_config(
        updates=request.model_dump(mode="json", exclude_none=True),
    )


@router.get("/train-tasks/workflows")
def list_train_task_workflows() -> Dict[str, Any]:
    return get_runtime().list_train_task_workflows()


@router.post("/train-tasks/workflows")
def save_train_task_workflow(
    request: TrainTaskWorkflowSaveRequest,
) -> Dict[str, Any]:
    return get_runtime().save_train_task_workflow(
        workflow=request.workflow,
    )


@router.post("/train-tasks/workflows/{workflow_id}/test-run")
def run_train_task_workflow_test(
    workflow_id: str,
    request: TrainTaskTestRunRequest,
) -> Dict[str, Any]:
    return get_runtime().run_train_task_workflow_test(
        workflow_id=workflow_id,
        sample_email=request.sample_email,
    )


@router.post("/train-tasks/workflows/{workflow_id}/toggle")
def toggle_train_task_workflow(
    workflow_id: str,
    request: ToggleTrainTaskWorkflowRequest,
) -> Dict[str, Any]:
    return get_runtime().toggle_train_task_workflow(
        workflow_id=workflow_id,
        enabled=request.enabled,
    )


@router.post("/train-tasks/gmail/poll-dry-run")
def poll_train_task_gmail_dry_run(
    request: GmailPollDryRunRequest,
) -> Dict[str, Any]:
    messages = [
        item.model_dump(mode="json", by_alias=True, exclude_none=True)
        for item in request.messages
    ]
    return get_runtime().poll_train_task_gmail_dry_run(messages=messages)


@router.post("/train-tasks/gmail/poll-now")
def poll_train_task_gmail_now() -> Dict[str, Any]:
    return get_runtime().poll_train_task_gmail_now()


@router.get("/train-tasks/runs")
def list_train_task_runs(
    limit: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    return get_runtime().list_train_task_runs(limit=limit)


@router.get("/train-tasks/approvals")
def list_train_task_approvals(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    return get_runtime().list_train_task_approvals(
        status=status,
        limit=limit,
    )


@router.post("/train-tasks/approvals/{approval_id}/resolve")
def resolve_train_task_approval(
    approval_id: str,
    request: ResolveTrainTaskApprovalRequest,
) -> Dict[str, Any]:
    return get_runtime().resolve_train_task_approval(
        approval_id=approval_id,
        approve=request.approve,
        resolved_by=request.resolved_by,
        resolution_note=request.resolution_note or "",
    )


@router.post("/train-tasks/approvals/{approval_id}/execute-gmail-draft")
def execute_train_task_approval_gmail_draft(
    approval_id: str,
    request: ExecuteTrainTaskApprovalRequest,
) -> Dict[str, Any]:
    return get_runtime().execute_train_task_approval_gmail_draft(
        approval_id=approval_id,
        executed_by=request.executed_by,
    )


@router.post("/train-tasks/approvals/{approval_id}/execute-hubspot-write")
def execute_train_task_approval_hubspot_write(
    approval_id: str,
    request: ExecuteTrainTaskApprovalRequest,
) -> Dict[str, Any]:
    return get_runtime().execute_train_task_approval_hubspot_write(
        approval_id=approval_id,
        executed_by=request.executed_by,
    )


@router.post("/train-tasks/approvals/{approval_id}/hubspot-mcp-dry-run")
def dry_run_train_task_approval_hubspot_mcp(
    approval_id: str,
    request: ExecuteTrainTaskApprovalRequest,
) -> Dict[str, Any]:
    return get_runtime().dry_run_train_task_approval_hubspot_mcp(
        approval_id=approval_id,
        executed_by=request.executed_by,
    )


@router.post("/train-tasks/approvals/{approval_id}/execute-hubspot-mcp-write")
def execute_train_task_approval_hubspot_mcp_write(
    approval_id: str,
    request: ExecuteTrainTaskApprovalRequest,
) -> Dict[str, Any]:
    return get_runtime().execute_train_task_approval_hubspot_mcp_write(
        approval_id=approval_id,
        executed_by=request.executed_by,
    )


@router.get("/connectors/hubspot/mcp/tools")
def list_hubspot_mcp_remote_tools() -> Dict[str, Any]:
    return get_runtime().list_hubspot_mcp_remote_tools()


@router.post("/connectors/hubspot/mcp/tools/read-only-call")
def call_hubspot_mcp_tool_readonly_test(
    request: HubSpotMcpReadonlyToolCallRequest,
) -> Dict[str, Any]:
    return get_runtime().call_hubspot_mcp_tool_readonly_test(
        tool_name=request.tool_name,
        arguments=request.arguments,
    )


@router.post("/train-tasks/workflows/validate")
def validate_train_task_workflow_definition(
    request: GenericWorkflowValidationRequest,
) -> Dict[str, Any]:
    return get_runtime().validate_train_task_workflow_definition(
        workflow=request.workflow,
    )


@router.post("/train-tasks/workflows/generic-test-run")
def run_generic_train_task_workflow_test(
    request: GenericWorkflowTestRunRequest,
) -> Dict[str, Any]:
    return get_runtime().run_generic_train_task_workflow_test(
        workflow=request.workflow,
        trigger_payload=request.trigger_payload,
        workspace_context=request.workspace_context,
    )


@router.post("/train-tasks/workflows/generic-save")
def save_generic_train_task_workflow(
    request: GenericWorkflowSaveRequest,
) -> Dict[str, Any]:
    return get_runtime().save_generic_train_task_workflow(
        workflow=request.workflow,
        publish=request.publish,
        saved_by=request.saved_by,
    )


@router.get("/train-tasks/workflows/generic-saved")
def list_generic_train_task_workflows() -> Dict[str, Any]:
    return get_runtime().list_generic_train_task_workflows()


@router.post("/train-tasks/workflows/generic-run")
def run_published_generic_train_task_workflow(
    request: GenericWorkflowRunByIdRequest,
) -> Dict[str, Any]:
    return get_runtime().run_published_generic_train_task_workflow(
        workflow_id=request.workflow_id,
        trigger_payload=request.trigger_payload,
        workspace_context=request.workspace_context,
        executed_by=request.executed_by,
    )


@router.post("/marketing/assets/upload")
async def upload_marketing_assets(
    files: List[UploadFile] = File(...),
) -> Dict[str, Any]:
    runtime = get_runtime()
    upload_dir = _runtime_upload_dir(runtime)
    items: List[Dict[str, Any]] = []

    for file in files:
        original_name = _safe_filename(file.filename or "asset")
        suffix = Path(original_name).suffix.lower()
        stem = Path(original_name).stem or "asset"
        asset_id = f"asset_{uuid4().hex[:12]}"
        stored_name = f"{asset_id}_{_safe_filename(stem)}{suffix}"

        file_path = upload_dir / stored_name
        content = await file.read()
        file_path.write_bytes(content)

        paths = _runtime_asset_paths(runtime, stored_name)

        items.append(
            {
                "id": asset_id,
                "type": "product",
                "label": original_name,
                "url": paths["url"],
                "file_path": paths["file_path"],
                "mime_type": file.content_type,
                "size_bytes": len(content),
                "notes": "",
                "uploaded_at": utc_now_iso(),
            }
        )

    try:
        runtime._append_audit(
            event_type="local_node.marketing_assets_uploaded",
            message="Marketing creative assets uploaded",
            payload={
                "count": len(items),
                "asset_ids": [item.get("id") for item in items],
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "items": items,
        "at": utc_now_iso(),
    }


@router.post("/marketing/launch")
def launch_marketing_suggestion(
    request: LaunchMarketingSuggestionRequest,
) -> Dict[str, Any]:
    runtime = get_runtime()

    brand_foundation_state = (
        request.brandFoundationState
        or request.brand_foundation_state
        or None
    )

    brand_map = request.brandMap or request.brand_map or None

    return runtime.launch_marketing_suggestion(
        brief=request.brief,
        objective=request.objective,
        funnel_goal=request.funnel_goal,
        target_audience=request.target_audience,
        persona=request.persona,
        offer=request.offer,
        channels=request.channels,
        hashtags=request.hashtags,
        keywords=request.keywords,
        hard_rules=request.hard_rules,
        guidance_notes=request.guidance_notes,
        campaign_notes=request.campaign_notes,
        creative_assets=[
            item.model_dump(mode="json", exclude_none=True)
            for item in request.creative_assets
        ],
        creative_direction=request.creative_direction.model_dump(
            mode="json",
            exclude_none=True,
        ),
        brand_foundation=request.brand_foundation,
        brand_foundation_state=brand_foundation_state,
        brand_map=brand_map,
    )


@router.post("/workflows/launch")
def launch_workflow(request: LaunchWorkflowRequest) -> Dict[str, Any]:
    runtime = get_runtime()
    return runtime.manual_launch_workflow(
        workflow_definition_id=request.workflow_definition_id,
        agent_definition_id=request.agent_definition_id,
        context=request.context,
    )


@router.post("/heartbeat")
def heartbeat() -> Dict[str, Any]:
    return get_runtime().heartbeat()


@router.post("/control/pause")
def pause_node() -> Dict[str, Any]:
    return get_runtime().pause()


@router.post("/control/resume")
def resume_node() -> Dict[str, Any]:
    return get_runtime().resume()


@router.post("/control/stop")
def stop_node() -> Dict[str, Any]:
    return get_runtime().stop()


@router.post("/control/start")
def start_node() -> Dict[str, Any]:
    return get_runtime().start()


@router.post("/scheduler/start")
def scheduler_start() -> Dict[str, Any]:
    return get_runtime().scheduler_start()


@router.post("/scheduler/stop")
def scheduler_stop() -> Dict[str, Any]:
    return get_runtime().scheduler_stop()


@router.post("/scheduler/tick")
def scheduler_tick() -> Dict[str, Any]:
    return get_runtime().scheduler_tick()


@router.get("/scheduler/status")
def scheduler_status() -> Dict[str, Any]:
    return get_runtime().scheduler_status()


@router.get("/queue")
def list_queue_items() -> Dict[str, Any]:
    return get_runtime().list_queue_items()


@router.get("/runs")
def list_runs(
    department_key: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
) -> Dict[str, Any]:
    return get_runtime().list_workflow_runs(
        department_key=department_key,
        limit=limit,
    )


@router.post("/runs/launch")
def launch_run(request: LaunchRunRequest) -> Dict[str, Any]:
    runtime = get_runtime()
    return runtime.enqueue_workflow(
        workflow_id=request.workflow_id,
        operator_id=request.operator_id,
        department_key=request.department_key,
        payload=request.context,
    )


@router.post("/runs/run-next")
def run_next() -> Dict[str, Any]:
    return get_runtime().run_next()


@router.post("/runs/execute-next")
def execute_next() -> Dict[str, Any]:
    return get_runtime().run_next()


@router.post("/runs/{queue_item_id}/cancel")
def cancel_run(queue_item_id: str, request: CancelRunRequest) -> Dict[str, Any]:
    return get_runtime().cancel_run(queue_item_id, reason=request.reason)


@router.post("/runs/{queue_item_id}/resume-approval")
def resume_approval(queue_item_id: str) -> Dict[str, Any]:
    return get_runtime().resume_approval(queue_item_id)


@router.get("/approvals")
def list_approvals(
    department_key: Optional[str] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
) -> Dict[str, Any]:
    return get_runtime().list_runtime_approvals(
        department_key=department_key,
        limit=limit,
    )


@router.post("/approvals/{approval_id}/resolve")
def resolve_approval(
    approval_id: str,
    request: ResolveApprovalRequest,
) -> Dict[str, Any]:
    return get_runtime().resolve_runtime_approval(
        approval_id,
        approve=request.approve,
        resolved_by=request.resolved_by,
        resolution_note=request.resolution_note,
    )


@router.get("/audit")
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=1000),
) -> Dict[str, Any]:
    return get_runtime().list_audit_events(limit=limit)


@router.get("/triggers")
def list_triggers() -> Dict[str, Any]:
    return get_runtime().list_triggers()


@router.get("/agents")
def list_agent_definitions() -> Dict[str, Any]:
    return get_runtime().list_agent_definitions()


@router.get("/workflow-definitions")
def list_workflow_definitions() -> Dict[str, Any]:
    return get_runtime().list_workflow_definitions()


@router.get("/debug/agent-runtime")
def debug_agent_runtime() -> Dict[str, Any]:
    runtime = get_runtime()
    return {
        "ok": True,
        "workspace_id": runtime.config.workspace_id,
        "base_dir": runtime.base_dir,
        "workflow_definitions": runtime.list_workflow_definitions(),
        "agent_definitions": runtime.list_agent_definitions(),
        "triggers": runtime.list_triggers(),
        "status": runtime.status(),
    }


@router.get("/sync/push-payload")
def get_sync_push_payload() -> Dict[str, Any]:
    runtime = get_runtime()
    return {
        "ok": True,
        "payload": runtime.build_sync_push_request(),
    }


@router.post("/sync/push-success")
def mark_sync_push(request: MarkSyncRequest) -> Dict[str, Any]:
    return get_runtime().mark_sync_push_success(ack_token=request.ack_token)


@router.post("/sync/pull-success")
def mark_sync_pull(request: MarkSyncRequest) -> Dict[str, Any]:
    return get_runtime().mark_sync_pull_success(ack_token=request.ack_token)


@router.post("/sync/apply-commands")
def apply_sync_commands(request: ApplyCommandsRequest) -> Dict[str, Any]:
    return get_runtime().apply_remote_commands(request.commands)