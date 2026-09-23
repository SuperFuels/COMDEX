from __future__ import annotations

import asyncio
import hashlib
import json
import re

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Request, HTTPException, APIRouter
from fastapi import File, Query, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from backend.modules.local_node.contracts_local_node import (
    DeploymentMode,
    LocalNodeConfig,
    utc_now_iso,
)
from backend.modules.local_node.local_node_runtime import LocalNodeRuntime
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.workflow_capsules.aion_a2a_commercial_ticket import (
    home_fixed_plumbing_hourly_ticket,
    home_fixed_roof_discovery_ticket,
)


from backend.services.aion_mission_mode.business_foundation_llm_extractor import scan_website_with_openai
from backend.services.aion_mission_mode.website_foundation_extractor import collect_website_evidence, normalise_url
from backend.services.aion_mission_mode.website_scan_usage_gate import website_scan_allowed

router = APIRouter(prefix="/api/local-node", tags=["local-node"])


_RUNTIME: Optional[LocalNodeRuntime] = None
_WORKSPACE_RUNTIMES: Dict[str, LocalNodeRuntime] = {}


def _build_runtime(workspace_id: str | None = None) -> LocalNodeRuntime:
    resolved_workspace = canonical_business_id(workspace_id or "costa-conexion")
    legacy_default = resolved_workspace == "costa-conexion"
    config = LocalNodeConfig(
        node_id="node_mac_local_01" if legacy_default else f"node_mac_{resolved_workspace}",
        workspace_id=resolved_workspace,
        deployment_mode=DeploymentMode.LOCAL_FIRST,
        base_dir=".runtime/local_node" if legacy_default else f".runtime/local_node/workspaces/{resolved_workspace}",
    )
    runtime = LocalNodeRuntime(config)
    runtime.start()
    return runtime


def get_runtime(workspace_id: str | None = None) -> LocalNodeRuntime:
    global _RUNTIME
    if workspace_id:
        resolved_workspace = canonical_business_id(workspace_id)
        if resolved_workspace != "costa-conexion":
            runtime = _WORKSPACE_RUNTIMES.get(resolved_workspace)
            if runtime is None:
                runtime = _build_runtime(resolved_workspace)
                _WORKSPACE_RUNTIMES[resolved_workspace] = runtime
            return runtime
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


class PilotEmailPrepareRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: str = ""
    bcc: str = ""
    requested_by: str = "aion_central_pilot"


class PilotEmailSendRequest(BaseModel):
    payload_hash: str
    executed_by: str = "aion_central_pilot"
    approval_granted: bool = False


class PilotAuthorityUpdateRequest(BaseModel):
    rules: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    updated_by: str = "business_owner"


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
    workspace_id: Optional[str] = None
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
    workspace_id: Optional[str] = None


class RetryMarketingImageRequest(BaseModel):
    workspace_id: str
    provider: str = "openai"


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


@router.post("/pilot/email/prepare")
def prepare_pilot_email_send(
    request: PilotEmailPrepareRequest,
    workspace_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    return get_runtime(workspace_id).prepare_pilot_email_send(
        to=request.to,
        subject=request.subject,
        body=request.body,
        cc=request.cc,
        bcc=request.bcc,
        requested_by=request.requested_by,
    )


@router.get("/pilot/authority")
def get_pilot_authority_policy(
    workspace_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    return get_runtime(workspace_id).get_pilot_authority_policy()


@router.post("/pilot/authority")
def update_pilot_authority_policy(
    request: PilotAuthorityUpdateRequest,
    workspace_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    return get_runtime(workspace_id).update_pilot_authority_policy(request.rules, request.updated_by)


@router.post("/pilot/email/{approval_id}/send")
def execute_pilot_email_send(
    approval_id: str,
    request: PilotEmailSendRequest,
    workspace_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    return get_runtime(workspace_id).execute_pilot_email_send(
        approval_id=approval_id,
        payload_hash=request.payload_hash,
        executed_by=request.executed_by,
        approval_granted=request.approval_granted,
    )


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
    workspace_id: str | None = Query(default=None),
) -> Dict[str, Any]:
    runtime = get_runtime(workspace_id)
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
    runtime = get_runtime(request.workspace_id)

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


@router.post("/marketing/runs/{run_id}/retry-image")
def retry_marketing_run_image(
    run_id: str,
    request: RetryMarketingImageRequest,
) -> Dict[str, Any]:
    """Retry only the failed local creative render; never publish or spend."""
    runtime = get_runtime(request.workspace_id)
    run = runtime.workflow_run_repository.find_one(runtime.config.workspace_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="marketing_run_not_found")
    workflow = runtime.workflow_definition_repository.get(runtime.config.workspace_id, run.workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="marketing_workflow_not_found")
    post_step = next((step for step in workflow.steps if str(step.id) == "post_social"), None)
    if post_step is None:
        raise HTTPException(status_code=409, detail="marketing_image_step_not_found")
    post_package = dict(
        (run.result_payload or {}).get("post_package")
        or (run.context or {}).get("post_package")
        or {}
    )
    if not post_package:
        raise HTTPException(status_code=409, detail="marketing_post_package_missing")
    run_input = dict(run.input_payload or {})
    run_brand = dict(run_input.get("brand_foundation") or {})
    if request.provider != "openai":
        raise HTTPException(status_code=409, detail="unsupported_image_provider")
    try:
        raw_result = runtime.workflow_execution_runtime.image_generation_service.generate_marketing_carousel_cards(
            caption=str(post_package.get("caption") or post_package.get("draft_caption") or ""),
            carousel=list(post_package.get("carousel") or post_package.get("draft_carousel") or []),
            provider=request.provider,
            model=str(post_package.get("selected_image_model") or "gpt-image-1"),
            size="1024x1536",
            background="opaque",
            output_format="png",
            file_stem_prefix=f"{run.id}_{post_step.id}_retry",
            metadata={
                "workspace_id": run.workspace_id,
                "workflow_id": run.workflow_id,
                "workflow_run_id": run.id,
                "step_id": post_step.id,
                "retry": True,
            },
            visual_assets=dict(post_package.get("visual_assets") or {}),
            brand_name=str(post_package.get("brand_name") or post_package.get("business_name") or run_brand.get("business_name") or str(run.workspace_id).replace("-", " ").title() or "Local business"),
            primary_channel=str(post_package.get("primary_channel") or "Facebook"),
            offer=post_package.get("offer"),
            audience=post_package.get("target_audience"),
            persona=post_package.get("persona"),
            objective=post_package.get("objective"),
        )
        cards = list(raw_result.get("cards") or [])
        generated_images = [
            {
                "card_index": card.get("card_index"),
                "card_type": card.get("card_type"),
                "provider": card.get("provider") or raw_result.get("provider"),
                "model": card.get("model") or raw_result.get("model"),
                "status": card.get("status"),
                "url": card.get("asset_url") or card.get("file_path"),
                "asset_url": card.get("asset_url"),
                "asset_id": card.get("asset_id"),
                "file_path": card.get("file_path"),
                "mime_type": card.get("mime_type"),
                "error": card.get("error"),
            }
            for card in cards
        ]
        primary = next((item for item in generated_images if item.get("status") == "completed"), generated_images[0] if generated_images else None)
        result = {
            "provider": (primary or {}).get("provider") or raw_result.get("provider"),
            "model": raw_result.get("model"),
            "status": "completed" if raw_result.get("ok") else "partial",
            "generated_image": primary,
            "generated_images": generated_images,
            "carousel_cards": cards,
            "error": raw_result.get("error"),
        }
    except Exception as exc:
        post_package["image_generation"] = {
            "provider": request.provider,
            "status": "failed",
            "error": str(exc),
        }
        run.context["post_package"] = post_package
        run.result_payload["post_package"] = post_package
        runtime.workflow_run_repository.save(run)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    post_package["generated_image"] = result.get("generated_image")
    post_package["generated_images"] = result.get("generated_images") or []
    post_package["carousel_cards"] = result.get("carousel_cards") or []
    post_package["image_generation"] = {
        "provider": result.get("provider"),
        "model": result.get("model"),
        "status": result.get("status"),
        "asset_url": (result.get("generated_image") or {}).get("asset_url"),
        "error": result.get("error"),
        "cards_generated": len(result.get("carousel_cards") or []),
    }
    run.context["post_package"] = post_package
    run.result_payload["post_package"] = post_package
    runtime.workflow_run_repository.save(run)
    return {
        "ok": result.get("status") in {"completed", "partial"},
        "run_id": run.id,
        "workspace_id": run.workspace_id,
        "post_package": post_package,
        "published": False,
        "spent": False,
    }

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
    compact: bool = Query(default=False),
    workspace_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    payload = get_runtime(workspace_id).list_workflow_runs(
        department_key=department_key,
        limit=limit,
    )
    if not compact:
        return payload

    # Workflow evidence can be several megabytes per run.  List surfaces only
    # need identity and progress metadata; detailed payloads remain available
    # from the normal (non-compact) endpoint for explicit inspection/export.
    compact_items = []
    for item in payload.get("items", []):
        if not isinstance(item, dict):
            continue
        compact_item = {
            key: value
            for key, value in item.items()
            if key not in {"context", "input_payload", "result_payload", "step_runs"}
        }
        compact_item["context"] = {}
        compact_item["input_payload"] = {}
        compact_item["result_payload"] = {}
        compact_item["step_runs"] = [
            {
                key: value
                for key, value in step.items()
                if key
                in {
                    "id",
                    "step_id",
                    "step_name",
                    "status",
                    "started_at",
                    "completed_at",
                    "error_message",
                }
            }
            for step in item.get("step_runs", [])
            if isinstance(step, dict)
        ]
        compact_items.append(compact_item)
    return {**payload, "items": compact_items, "compact": True}


@router.post("/runs/launch")
def launch_run(request: LaunchRunRequest) -> Dict[str, Any]:
    runtime = get_runtime()
    return runtime.enqueue_workflow(
        workflow_id=request.workflow_id,
        operator_id=request.operator_id,
        department_key=request.department_key,
        payload=request.context,
    )


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    workspace_id: Optional[str] = Query(default=None),
    marketing_view: bool = Query(default=False),
) -> Dict[str, Any]:
    runtime = get_runtime(workspace_id)
    run = runtime.workflow_run_repository.find_one(runtime.config.workspace_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="workflow_run_not_found")
    if marketing_view:
        context = dict(run.context or {})
        result_payload = dict(run.result_payload or {})
        source_post = dict(result_payload.get("post_package") or context.get("post_package") or {})
        compact_images = [
            {
                key: image.get(key)
                for key in ("card_index", "card_type", "provider", "model", "status", "url", "asset_url", "asset_id", "file_path", "mime_type", "error")
            }
            for image in list(source_post.get("generated_images") or [])
            if isinstance(image, dict)
        ]
        compact_post = {
            key: source_post.get(key)
            for key in ("caption", "draft_caption", "carousel", "draft_carousel", "primary_channel", "brand_name", "business_name", "offer", "target_audience", "persona", "objective", "image_generation")
        }
        compact_post["generated_images"] = compact_images
        compact_post["generated_image"] = next((image for image in compact_images if image.get("status") == "completed"), compact_images[0] if compact_images else None)
        compact_post["carousel_cards"] = [
            {
                key: card.get(key)
                for key in ("card_index", "card_type", "headline", "body", "visual_direction", "layout_style", "image_url", "asset_url", "asset_id", "file_path", "mime_type", "status", "provider", "model", "error")
            }
            for card in list(source_post.get("carousel_cards") or [])
            if isinstance(card, dict)
        ]
        return {
            "ok": True,
            "item": {
                "id": run.id,
                "workspace_id": run.workspace_id,
                "workflow_id": run.workflow_id,
                "workflow_name": run.workflow_name,
                "department_key": run.department_key,
                "status": run.status,
                "approval_request_id": run.approval_request_id,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "input_payload": {
                    key: (run.input_payload or {}).get(key)
                    for key in ("brief", "objective", "target_audience", "offer", "channels", "brand_foundation")
                },
                "context": {
                    "approval_packet": context.get("approval_packet"),
                    "post_package": compact_post,
                },
                "result_payload": {"post_package": compact_post},
            },
        }
    return {"ok": True, "item": run.model_dump(mode="json")}


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
    workspace_id: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    return get_runtime(workspace_id).list_runtime_approvals(
        department_key=department_key,
        limit=limit,
    )


@router.post("/approvals/{approval_id}/resolve")
def resolve_approval(
    approval_id: str,
    request: ResolveApprovalRequest,
) -> Dict[str, Any]:
    return get_runtime(request.workspace_id).resolve_runtime_approval(
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


# PHASE 18 LOCK: A2A Commercial Ticket Preview API
@router.get("/aion/phase18/a2a-commercial-ticket-preview")
def get_aion_phase18_a2a_commercial_ticket_preview(scenario: str = "home_fixed_plumbing_hourly"):
    scenario_key = str(scenario or "home_fixed_plumbing_hourly").strip().lower()

    if scenario_key in {
        "home_fixed_roof_discovery",
        "roof_discovery",
        "roof_leak",
        "discovery_session",
    }:
        ticket = home_fixed_roof_discovery_ticket()
        resolved_scenario = "roof_discovery"
    else:
        ticket = home_fixed_plumbing_hourly_ticket()
        resolved_scenario = "plumbing_hourly"

    data = ticket.to_dict()
    data["requested_scenario"] = scenario_key
    data["resolved_scenario"] = resolved_scenario

    # PHASE 18 LOCK:
    # Keep raw backend IDs/hashes for Advanced technical trace, but provide
    # a stable customer-facing display_id for normal UI.
    data["display_id"] = "A2A-HF-001" if resolved_scenario in {"roof_discovery", "plumbing_hourly"} else str(data.get("ticket_id", "A2A-PREVIEW")).upper()

    if resolved_scenario == "roof_discovery":
        data.setdefault("route", {})
        data["route"]["label"] = "Discovery / assessment visit"
        data["route"]["pricing_label"] = "Free or paid discovery"
        data.setdefault("service_rule", {})
        data["service_rule"]["resource_type"] = "Roofer / general builder"
    elif resolved_scenario == "plumbing_hourly":
        data.setdefault("route", {})
        data["route"]["label"] = "Hourly service / callout"
        data["route"]["pricing_label"] = "First hour plus hourly rate"
        data.setdefault("service_rule", {})
        data["service_rule"]["resource_type"] = "Plumber"

    # PHASE 18 LOCK:
    # Normalise the safety envelope at the API boundary so frontend/API consumers
    # always receive the same guarded no-side-effect contract, regardless of the
    # internal ticket object's field naming.
    guard_envelope = {
        "preview_only": True,
        "booking_created": False,
        "payment_created": False,
        "escrow_created": False,
        "external_message_sent": False,
        "live_chain_write": False,
        "human_review_required": True,
    }

    existing_guard = (
        data.get("guard_envelope")
        or data.get("guard")
        or data.get("safety")
        or data.get("side_effect_guards")
        or {}
    )

    if isinstance(existing_guard, dict):
        guard_envelope.update(existing_guard)

    # Re-assert hard safety values after merge.
    guard_envelope.update({
        "preview_only": True,
        "booking_created": False,
        "payment_created": False,
        "escrow_created": False,
        "external_message_sent": False,
        "live_chain_write": False,
        "human_review_required": True,
    })

    data["guard_envelope"] = guard_envelope
    data["api_contract"] = {
        "phase": "18",
        "endpoint": "aion_phase18_a2a_commercial_ticket_preview",
        "requested_scenario": scenario_key,
        "resolved_scenario": resolved_scenario,
        **guard_envelope,
    }
    return data




# PHASE 21H LOCK: AION Pilot Artifact Preview Endpoint
@router.post("/aion/pilot/artifact-preview")
async def post_aion_pilot_artifact_preview(request: Request):
    """
    Preview-only local endpoint for creating a Pilot draft artifact inside
    the mission-scoped business container preview path.

    Safety:
    - no email
    - no WhatsApp
    - no payment
    - no booking
    - no escrow
    - no deployment
    - no live chain write
    - no reputation mutation
    """
    from pathlib import Path
    from backend.services.aion_mission_mode.pilot_artifact_builder_runtime import (
        PilotArtifactBuilderRuntime,
        PilotArtifactBuilderViolation,
    )

    body = await request.json()

    business_id = str(body.get("business_id") or "home-fixed")
    mission_id = str(body.get("mission_id") or "pilot_demo_pdf_mission")
    mission_run_id = str(body.get("mission_run_id") or "pilot_demo_run_preview")
    step_id = str(body.get("step_id") or "step-artifact-preview")
    artifact_type = str(body.get("artifact_type") or "document")
    artifact_name = str(body.get("artifact_name") or "aion-pilot-draft-preview.txt")
    title = str(body.get("title") or "AION Pilot Draft Preview")
    content = str(body.get("content") or "")
    metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

    container_root = Path("data/aion_pilot_business_container_preview").resolve()

    try:
        contract = PilotArtifactBuilderRuntime.build_artifact_contract(
            business_id=business_id,
            mission_id=mission_id,
            mission_run_id=mission_run_id,
            step_id=step_id,
            artifact_type=artifact_type,
            artifact_name=artifact_name,
        )

        artifact_card = PilotArtifactBuilderRuntime.create_draft_artifact(
            container_root=str(container_root),
            contract=contract,
            title=title,
            content=content,
            metadata=metadata,
        )
    except PilotArtifactBuilderViolation as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "pilot_artifact_preview_blocked",
                "reason": str(exc),
                "preview_only": True,
                "live_external_side_effects_enabled": False,
            },
        ) from exc

    return {
        "payload_type": "aion_pilot_artifact_preview",
        "status": "draft_preview",
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "container_root": str(container_root),
        "artifact_card": artifact_card,
        "artifact_hash": artifact_card.get("artifact_hash"),
        "receipt_hash": artifact_card.get("artifact_receipt_hash"),
        "business_container_relative_path": artifact_card.get("business_container_relative_path"),
        "content_preview": content,
        "safety": {
            "preview_only": True,
            "live_external_side_effects_enabled": False,
            "would_send_external_message": False,
            "would_create_payment": False,
            "would_create_booking": False,
            "would_create_escrow": False,
            "would_deploy": False,
            "would_write_live_chain": False,
        },
    }
# END PHASE 21H LOCK



# PHASE 23A LOCK: AION Pilot Mission Preview Runtime Bridge

@router.post("/aion/pilot/execute-safe-step")
async def post_aion_pilot_execute_safe_step(request: Request):
    """
    Execute one already-approved safe internal Pilot mission step.

    This endpoint is the OpenClaw safe execution boundary:
    - frontend does not manufacture output
    - model/provider may only generate draft content
    - no raw external tools
    - no live side effects
    - output is persisted as a draft artifact inside the business container
    """
    from backend.services.aion_mission_mode.pilot_safe_step_executor import (
        PilotSafeStepExecutionBlocked,
        execute_pilot_safe_step,
    )

    body = await request.json()

    business_id = str(body.get("business_id") or "home-fixed")
    mission_id = str(body.get("mission_id") or "pilot_mission_preview")
    mission_run_id = str(body.get("mission_run_id") or "pilot_mission_preview_run")
    user_goal = str(body.get("user_goal") or body.get("goal") or "")
    step = body.get("step") if isinstance(body.get("step"), dict) else {}
    step_index = int(body.get("step_index") or 0)
    business_context = body.get("business_context") if isinstance(body.get("business_context"), dict) else {}
    mission_plan = body.get("mission_plan") if isinstance(body.get("mission_plan"), dict) else {}
    tool_execution_item = body.get("tool_execution_item") if isinstance(body.get("tool_execution_item"), dict) else None
    provider = str(body.get("provider") or "gemma4")

    def assistant_fn(prompt: str) -> str:
        runtime = get_runtime()

        # This must bypass the desktop fact shortcut, because that route can
        # return workspace status instead of executing the safe drafting step.
        provider_call = getattr(runtime, "_call_selected_ai_provider", None)

        if callable(provider_call):
            attempts = [
                {"provider": provider, "prompt": prompt},
                {"clean_provider": provider, "prompt": prompt},
                {"prompt": prompt, "provider": provider, "active_tab": "live_agents", "context_mode": "aion_pilot_safe_step_executor"},
                {"prompt": prompt},
            ]

            for kwargs in attempts:
                try:
                    result = provider_call(**kwargs)

                    if hasattr(result, "response"):
                        text = str(getattr(result, "response") or "").strip()
                    elif isinstance(result, dict):
                        text = str(result.get("text") or result.get("response") or result.get("content") or "").strip()
                    else:
                        text = str(result or "").strip()

                    if text and "Current approvals in the business workspace" not in text:
                        return text
                except TypeError:
                    continue
                except Exception:
                    continue

        ollama_call = getattr(runtime, "_call_ollama_chat", None)
        if callable(ollama_call):
            try:
                result = ollama_call(prompt=prompt)
                if hasattr(result, "response"):
                    text = str(getattr(result, "response") or "").strip()
                else:
                    text = str(result or "").strip()

                if text and "Current approvals in the business workspace" not in text:
                    return text
            except Exception:
                pass

        return ""

    try:
        return execute_pilot_safe_step(
            container_root=get_runtime().base_dir,
            business_id=business_id,
            mission_id=mission_id,
            mission_run_id=mission_run_id,
            user_goal=user_goal,
            step=step,
            step_index=step_index,
            business_context={
                **(business_context if isinstance(business_context, dict) else {}),
                "business_context_mission_map": body.get("business_context_mission_map") if isinstance(body.get("business_context_mission_map"), dict) else {},
                "brand_foundation_state": body.get("brand_foundation_state") if isinstance(body.get("brand_foundation_state"), dict) else {},
                "marketing_form": body.get("marketing_form") if isinstance(body.get("marketing_form"), dict) else {},
                "marketing_summary": body.get("marketing_summary") if isinstance(body.get("marketing_summary"), dict) else {},
                "draft_steps": body.get("draft_steps") if isinstance(body.get("draft_steps"), list) else [],
                "approval_stages": body.get("approval_stages") if isinstance(body.get("approval_stages"), list) else [],
                "context_instruction": "Use supplied business, brand, marketing and approval context before asking for clarification.",
            },
            mission_plan=mission_plan,
            assistant_fn=assistant_fn,
            tool_execution_item=tool_execution_item,
        )
    except PilotSafeStepExecutionBlocked as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "pilot_safe_step_execution_blocked",
                "reason": str(exc),
                "live_external_side_effects_performed": False,
            },
        ) from exc


@router.post("/aion/pilot/mission-preview")
async def post_aion_pilot_mission_preview(request: Request):
    """
    Preview-only bridge from the visible Pilot frontend into the locked
    Phase 20/21 Mission Mode backend spine.

    This endpoint compiles a deterministic mission plan, creates the approval
    matrix, runs the preview-safe mission runtime, and emits a read-only
    live mission timeline.

    Safety:
    - no payment
    - no booking
    - no escrow
    - no external message
    - no production deployment
    - no public post
    - no live chain write
    - no reputation mutation
    """
    from backend.services.aion_mission_mode.mission_contract import (
        AionMissionContract,
        MissionCheckpoint,
        MissionMode,
    )
    from backend.services.aion_mission_mode.mission_planner import (
        build_deterministic_mission_plan,
    )
    from backend.services.aion_mission_mode.mission_plan_approval_matrix import (
        create_mission_plan_approval_matrix,
    )
    from backend.services.aion_mission_mode.mission_runtime import (
        MissionRuntimeLimits,
        run_mission_runtime_preview,
    )
    from backend.services.aion_mission_mode.live_mission_timeline import (
        assert_live_timeline_safety,
        compile_live_timeline,
    )
    from backend.services.aion_mission_mode.business_context_mission_map import (
        build_business_context_mission_map,
    )
    from backend.services.aion_mission_mode.marketing_department_pack import (
        create_marketing_department_pack,
    )
    from backend.services.aion_mission_mode.business_function_router import (
        route_business_function,
    )
    from backend.services.aion_mission_mode.department_execution_queue import (
        add_blocked_live_action_cards,
        build_department_execution_queue,
    )
    from backend.services.aion_mission_mode.pilot_tool_execution_queue import (
        build_pilot_tool_execution_queue,
        summarize_tool_execution_queue,
    )

    body = await request.json()

    business_id = str(body.get("business_id") or "home-fixed")
    mission_id = str(body.get("mission_id") or "pilot_mission_preview")
    mission_run_id = str(body.get("mission_run_id") or "pilot_mission_preview_run")
    user_goal = str(body.get("user_goal") or body.get("goal") or "Run AION Pilot mission preview")
    template_id = str(body.get("template_id") or "home_fixed_lead_campaign_v0")
    brand_foundation_state = body.get("brand_foundation_state") if isinstance(body.get("brand_foundation_state"), dict) else {}
    marketing_form = body.get("marketing_form") if isinstance(body.get("marketing_form"), dict) else {}
    marketing_summary = body.get("marketing_summary") if isinstance(body.get("marketing_summary"), dict) else {}
    available_vault_requirements = (
        body.get("available_vault_requirements")
        if isinstance(body.get("available_vault_requirements"), list)
        else []
    )
    plan_text = str(body.get("plan_text") or body.get("generated_output_text") or body.get("current_draft") or "")

    contract = AionMissionContract(
        mission_id=mission_id,
        mission_goal=user_goal,
        business_id=business_id,
        creator_id=str(body.get("creator_id") or "operator"),
        agent_mode=MissionMode.CHECKPOINTED_AUTONOMY,
        allowed_autonomy_lanes=[
            "research",
            "creation",
            "internal_ops",
        ],
        hard_blocked_lanes=[
            "financial_action",
            "legal_action",
            "deployment_action",
        ],
        human_checkpoints=[
            MissionCheckpoint(
                checkpoint_id="checkpoint_external_payload_approval",
                title="Approve exact external payload before live action",
                description="Approve exact payload before publishing, sending, spending, booking, deploying or taking payment.",
                required_before_step_id="step_external_action",
                lane="external_action",
                action_type="external_live_action",
                required_action_type="external_live_action",
            )
        ],
        approval_required_actions=[
            "publish_advert",
            "send_customer_message",
            "spend_money",
            "create_booking",
            "deploy_live_page",
            "take_payment",
            "create_escrow",
            "dispatch_worker",
            "publish_facebook_post",
            "send_whatsapp_message",
            "start_ad_campaign",
            "deploy_to_production",
            "buy_domain",
        ],
        max_runtime_seconds=1800,
        max_tool_calls=int(body.get("max_tool_calls") or 40),
        max_cost=0.0,
        proof_required=True,
        replay_required=True,
        ets_enabled=True,
        data_retention_policy="mission_scoped",
        external_communication_consent_required=True,
        proof_sharing_enabled=False,
    )

    def _pilot_slug(value: object) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower().replace("-", "_")).strip("_")

    def _pilot_hash(payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    frontend_draft_steps = body.get("draft_steps") if isinstance(body.get("draft_steps"), list) else []

    if frontend_draft_steps:
        steps = []
        for index, raw_step in enumerate(frontend_draft_steps, start=1):
            source = raw_step if isinstance(raw_step, dict) else {"title": str(raw_step)}
            title = str(source.get("title") or source.get("label") or f"Step {index}").strip()
            step_id = str(source.get("step_id") or source.get("id") or f"ui_step_{index:02d}_{_pilot_slug(title)}")
            requires_approval = bool(source.get("requires_approval") is True or source.get("requires_checkpoint") is True)
            action_type = _pilot_slug(source.get("action_type") or title or f"safe_step_{index}")

            step = {
                "step_id": step_id,
                "title": title,
                "lane": str(source.get("lane") or "creation"),
                "action_type": action_type or f"safe_step_{index}",
                "decision": "checkpoint_required" if requires_approval else "safe_autonomous",
                "requires_checkpoint": requires_approval,
                "requires_approval": requires_approval,
                "source": "frontend_work_package",
                "safe_draft_work_allowed": not requires_approval,
                "live_external_side_effects_allowed": False,
                "subtasks": source.get("subtasks") if isinstance(source.get("subtasks"), list) else [],
            }
            step["step_hash"] = "sha256:" + _pilot_hash(step)
            steps.append(step)

        plan = {
            "payload_type": "aion_mission_plan",
            "plan_id": f"{mission_id}_frontend_work_package_plan",
            "mission_id": mission_id,
            "business_id": business_id,
            "mission_goal": user_goal,
            "template_id": "frontend_work_package_v0",
            "source": "frontend_visible_work_package",
            "steps": steps,
            "live_external_side_effects_allowed": False,
            "raw_tool_execution_allowed": False,
        }
        plan["plan_hash"] = _pilot_hash(plan)
    else:
        plan = build_deterministic_mission_plan(
            contract=contract,
            template_id=template_id,
        )

        steps = list(plan.get("steps") or [])

    business_context_mission_map = build_business_context_mission_map(
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        user_goal=user_goal,
        plan_steps=steps,
        plan_text=plan_text,
        brand_foundation_state=brand_foundation_state,
        marketing_form=marketing_form,
        marketing_summary=marketing_summary,
        available_vault_requirements=available_vault_requirements,
    )

    approval_matrix = create_mission_plan_approval_matrix(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        plan_id=f"{mission_id}_plan_preview",
        user_goal=user_goal,
        raw_steps=steps,
        change_reason="pilot_mission_preview",
    )

    runtime_steps = [
        step for step in steps
        if str(step.get("decision") or "") == "safe_autonomous"
        and bool(step.get("requires_checkpoint")) is False
    ]

    if not runtime_steps:
        runtime_steps = [
            step for step in steps
            if str(step.get("lane") or "") in {"research", "creation", "internal_ops"}
            and str(step.get("decision") or "") not in {"checkpoint_required", "blocked"}
        ]

    runtime_step_ids = {str(step.get("step_id")) for step in runtime_steps}
    pending_approval_steps = [
        step for step in steps
        if str(step.get("step_id")) not in runtime_step_ids
        and (
            bool(step.get("requires_checkpoint")) is True
            or str(step.get("decision") or "") in {"checkpoint_required", "blocked"}
        )
    ]

    runtime_execution_steps = [
        {
            "step_id": str(step.get("step_id") or f"runtime_step_{index:02d}"),
            "action_type": str(step.get("action_type") or "internal_planning"),
            "title": str(step.get("title") or step.get("action_type") or "Safe preview step"),
        }
        for index, step in enumerate(runtime_steps, start=1)
    ]

    runtime_preview = run_mission_runtime_preview(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        steps=runtime_execution_steps,
        limits=MissionRuntimeLimits(
            max_runtime_seconds=1800,
            max_tool_calls=int(body.get("max_tool_calls") or 40),
            max_cost=0.0,
        ),
    )

    step_titles = {
        str(step.get("step_id")): str(step.get("title") or step.get("action_type") or "Mission step")
        for step in steps
    }

    runtime_state = runtime_preview.get("state", {})
    completed_step_ids = list(runtime_state.get("completed_step_ids") or [])
    paused_step_id = runtime_state.get("paused_step_id")
    blocked_reason = runtime_state.get("blocked_reason")

    if not paused_step_id and pending_approval_steps:
        next_paused_step = pending_approval_steps[0]
        paused_step_id = str(next_paused_step.get("step_id") or "approval_required_step")
        blocked_reason = "pending_payload_or_human_approval_required"

    timeline_events = [
        {
            "mission_id": mission_id,
            "mission_run_id": mission_run_id,
            "business_id": business_id,
            "sequence_number": 0,
            "event_type": "mission_started",
            "step_id": "mission",
            "title": "Mission preview started",
            "summary": user_goal,
            "state_after": "running",
            "source_hash": f"sha256:{plan.get('plan_hash')}",
        }
    ]

    sequence = 1
    for step_id in completed_step_ids:
        timeline_events.append({
            "mission_id": mission_id,
            "mission_run_id": mission_run_id,
            "business_id": business_id,
            "sequence_number": sequence,
            "event_type": "step_completed",
            "step_id": step_id,
            "title": step_titles.get(step_id, step_id),
            "summary": "Safe preview step completed by Mission Runtime.",
            "state_after": "completed",
            "source_hash": runtime_state.get("state_hash") or f"sha256:{plan.get('plan_hash')}",
        })
        sequence += 1

    if paused_step_id:
        timeline_events.append({
            "mission_id": mission_id,
            "mission_run_id": mission_run_id,
            "business_id": business_id,
            "sequence_number": sequence,
            "event_type": "approval_requested",
            "step_id": str(paused_step_id),
            "title": step_titles.get(str(paused_step_id), "Approval required"),
            "summary": str(blocked_reason or "Mission paused before risky or approval-required action."),
            "state_after": "waiting_approval",
            "source_hash": runtime_state.get("state_hash") or f"sha256:{plan.get('plan_hash')}",
        })
        sequence += 1

    if runtime_preview.get("completed") is True and not paused_step_id:
        timeline_events.append({
            "mission_id": mission_id,
            "mission_run_id": mission_run_id,
            "business_id": business_id,
            "sequence_number": sequence,
            "event_type": "mission_completed",
            "step_id": "mission",
            "title": "Mission preview completed",
            "summary": "All safe preview steps completed. No live external side effects occurred.",
            "state_after": "completed",
            "source_hash": runtime_state.get("state_hash") or f"sha256:{plan.get('plan_hash')}",
        })

    timeline = compile_live_timeline(
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        business_id=business_id,
        panel_hash=f"sha256:{plan.get('plan_hash')}",
        events=timeline_events,
    )

    timeline_safety = assert_live_timeline_safety(timeline)

    department_route = route_business_function(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        business_context={
            "brand_foundation_state": brand_foundation_state,
            "marketing_form": marketing_form,
            "marketing_summary": marketing_summary,
            "business_context_mission_map": business_context_mission_map,
        },
    )

    department_queue = build_department_execution_queue(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        routed_plan=department_route,
        business_context={
            "brand_foundation_state": brand_foundation_state,
            "marketing_form": marketing_form,
            "marketing_summary": marketing_summary,
            "business_context_mission_map": business_context_mission_map,
        },
    )

    department_queue_with_blocked_live_actions = add_blocked_live_action_cards(
        queue=department_queue,
    )

    tool_execution_queue = build_pilot_tool_execution_queue(
        user_goal=user_goal,
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
        department_queue=department_queue_with_blocked_live_actions,
        include_blocked_live_actions=False,
        evaluation_time=int(body.get("evaluation_time") or 0),
    )

    marketing_department_pack = None
    if department_route.get("primary_department") == "marketing":
        marketing_department_pack = create_marketing_department_pack(
            user_goal=user_goal,
            business_id=business_id,
            mission_id=mission_id,
            mission_run_id=mission_run_id,
            business_context={
                "brand_foundation_state": brand_foundation_state,
                "marketing_form": marketing_form,
                "marketing_summary": marketing_summary,
                "business_context_mission_map": business_context_mission_map,
            },
            include_blocked_live_actions=True,
            evaluation_time=int(body.get("evaluation_time") or 0),
        )

    return {
        "payload_type": "aion_pilot_mission_preview",
        "status": runtime_state.get("status") or "preview_ready",
        "business_id": business_id,
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "user_goal": user_goal,
        "mission_plan": plan,
        "approval_matrix": approval_matrix,
        "runtime_preview": runtime_preview,
        "business_context_mission_map": business_context_mission_map,
        "department_route": department_route,
        "department_queue": department_queue_with_blocked_live_actions,
        "tool_execution_queue": tool_execution_queue,
        "tool_execution_summary": summarize_tool_execution_queue(tool_execution_queue),
        "marketing_department_pack": marketing_department_pack,
        "task_loop_map": business_context_mission_map.get("task_loop_map", {}),
        "context_task_nodes": business_context_mission_map.get("task_nodes", []),
        "human_task_cards": business_context_mission_map.get("human_task_cards", []),
        "credential_required_cards": business_context_mission_map.get("credential_required_cards", []),
        "timeline": timeline,
        "timeline_safety": timeline_safety,
        "completed_step_ids": completed_step_ids,
        "paused_step_id": paused_step_id,
        "blocked_reason": blocked_reason,
        "safe_outputs": [
            {
                "step_id": step_id,
                "title": step_titles.get(step_id, step_id),
                "status": "completed_preview",
            }
            for step_id in completed_step_ids
        ],
        "safety": {
            "preview_only": True,
            "live_external_side_effects_enabled": False,
            "would_create_booking": False,
            "would_create_payment": False,
            "would_create_escrow": False,
            "would_send_external_message": False,
            "would_publish_public_content": False,
            "would_deploy": False,
            "would_write_live_chain": False,
            "would_mutate_reputation": False,
            "timeline_executes_tools": False,
            "timeline_mutates_provider_state": False,
        },
    }
# END PHASE 23A LOCK

# PHASE 21C LOCK: AION-LRM Pilot Context Preview Endpoint
@router.get("/aion/lrm/pilot-context-preview")
def get_aion_lrm_pilot_context_preview(
    business_id: str = "home-fixed",
    mission_id: str = "pilot_demo_pdf_mission",
    mission_run_id: str = "pilot_demo_run_preview",
) -> Dict[str, Any]:
    """
    Preview-only local endpoint for the Phase 21B AION-LRM Pilot context payload.

    Raw safety contract:
    would_execute_workflow = false
    would_create_booking = false
    would_create_payment = false
    would_create_escrow = false
    would_send_external_message = false
    would_write_live_chain = false

    This endpoint exposes the existing backend adapter for the existing Pilot and
    Boardroom surfaces. It does not create a booking, payment, escrow, external
    message, live chain write, workflow execution, or business-container write.
    """
    from backend.services.aion_mission_mode.lrm_pilot_context_payload_adapter import (
        build_lrm_pilot_context_payload,
    )

    return build_lrm_pilot_context_payload(
        business_id=business_id,
        mission_id=mission_id,
        mission_run_id=mission_run_id,
    )
# END PHASE 21C LOCK


def _compact_website_scan_evidence(evidence: Any) -> Dict[str, Any]:
    """Return only the bounded evidence the renderer needs for provenance."""
    source = evidence if isinstance(evidence, dict) else {}

    def bounded_text(value: Any, limit: int = 2000) -> str:
        return str(value or "").strip()[:limit]

    def bounded_list(value: Any, *, count: int, item_limit: int = 500) -> List[str]:
        if not isinstance(value, list):
            return []
        return [bounded_text(item, item_limit) for item in value[:count] if bounded_text(item, item_limit)]

    def bounded_css_tokens(value: Any) -> List[Dict[str, str]]:
        if not isinstance(value, list):
            return []
        output: List[Dict[str, str]] = []
        for item in value[:40]:
            if not isinstance(item, dict):
                continue
            name = bounded_text(item.get("name"), 100)
            token_value = bounded_text(item.get("value"), 32)
            if name and token_value:
                output.append({"name": name, "value": token_value})
        return output

    font_roles_source = source.get("font_roles") if isinstance(source.get("font_roles"), dict) else {}

    try:
        visible_text_length = max(0, int(source.get("visible_text_length") or 0))
    except (TypeError, ValueError):
        visible_text_length = 0

    return {
        "url": bounded_text(source.get("url"), 2048),
        "domain": bounded_text(source.get("domain"), 255),
        "title": bounded_text(source.get("title"), 1000),
        "headings": bounded_list(source.get("headings"), count=24, item_limit=500),
        "emails": bounded_list(source.get("emails"), count=20, item_limit=320),
        "phones": bounded_list(source.get("phones"), count=20, item_limit=100),
        "social_links": bounded_list(source.get("social_links"), count=24, item_limit=2048),
        "logo_candidates": bounded_list(source.get("logo_candidates"), count=12, item_limit=2048),
        "icon_candidates": bounded_list(source.get("icon_candidates"), count=12, item_limit=2048),
        "social_image_candidates": bounded_list(source.get("social_image_candidates"), count=12, item_limit=2048),
        "colour_candidates": bounded_list(source.get("colour_candidates"), count=24, item_limit=32),
        "font_candidates": bounded_list(source.get("font_candidates"), count=16, item_limit=300),
        "css_custom_properties": bounded_css_tokens(source.get("css_custom_properties")),
        "font_roles": {
            "heading": bounded_text(font_roles_source.get("heading"), 200),
            "body": bounded_text(font_roles_source.get("body"), 200),
            "supporting": bounded_text(font_roles_source.get("supporting"), 200),
        },
        "stylesheet_urls": bounded_list(source.get("stylesheet_urls"), count=24, item_limit=2048),
        "visible_text_length": visible_text_length,
        "live_external_side_effect": False,
    }

@router.post("/api/aion/small-business/website-scan")
async def api_aion_small_business_website_scan(payload: dict):
    payload = payload or {}
    gate = website_scan_allowed(payload)

    if not gate.get("allowed"):
        return {
            "ok": False,
            "usage_gate": gate,
            "extracted_fields": {},
            "source_facts": [],
            "warnings": ["Login or authorised session required before using OpenAI website scan."],
            "live_external_side_effect": False,
        }

    website = str(payload.get("website") or "").strip()

    # Brand Design System discovery only needs objective public-page evidence.
    # Keep that path independent of paid LLM availability and quota: logos,
    # colours and declared fonts come directly from the site and are still
    # suggestions until the user confirms them. The onboarding foundation scan
    # continues to use the model-assisted extraction path below.
    if payload.get("evidence_only") is True:
        try:
            evidence = await asyncio.to_thread(
                collect_website_evidence,
                normalise_url(website),
                timeout_seconds=12,
            )
        except Exception as exc:
            return {
                "ok": False,
                "usage_gate": gate,
                "extracted_fields": {},
                "foundation": {},
                "evidence": {},
                "source_facts": [],
                "warnings": [str(exc) or "Public website evidence scan failed"],
                "error": "website_evidence_scan_failed",
                "provider": "deterministic_public_website",
                "live_external_side_effect": False,
            }

        return {
            "ok": True,
            "url": normalise_url(website),
            "extracted_fields": {},
            "foundation": {},
            "evidence": _compact_website_scan_evidence(evidence),
            "source_facts": [],
            "warnings": [],
            "provider": "deterministic_public_website",
            "live_external_side_effect": False,
            "usage_gate": gate,
        }

    try:
        # This scanner performs synchronous website and OpenAI network calls.
        # Keep them off the asyncio request loop so voice/onboarding remains responsive.
        result = await asyncio.to_thread(scan_website_with_openai, website)
    except Exception as exc:
        return {
            "ok": False,
            "usage_gate": gate,
            "extracted_fields": {},
            "foundation": {},
            "source_facts": [],
            "warnings": [str(exc) or "Website scan failed"],
            "error": "website_scan_failed",
            "provider": "openai",
            "live_external_side_effect": False,
        }

    # The full visible website text is useful server-side for extraction, but it
    # must not be transferred into Electron and duplicated throughout app state.
    result["evidence"] = _compact_website_scan_evidence(result.get("evidence"))
    result["usage_gate"] = gate
    return result


@router.post("/aion/small-business/website-scan")
async def aion_small_business_website_scan(payload: dict):
    return await api_aion_small_business_website_scan(payload or {})
