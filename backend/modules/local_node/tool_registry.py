from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.modules.local_node.contracts_local_node import utc_now_iso


class ToolProviderType(str, Enum):
    NATIVE_LOCAL = "native_local"
    DIRECT_API = "direct_api"
    MCP = "mcp"
    STACKONE = "stackone"
    GOOGLE_ADK_BRIDGE = "google_adk_bridge"
    BROWSER_CONTROL = "browser_control"
    N8N = "n8n"
    MANUAL_STUB = "manual_stub"


class ToolRiskLevel(str, Enum):
    READ_ONLY = "read_only"
    DRAFT_ONLY = "draft_only"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"
    FINANCIAL = "financial"
    BROWSER_CONTROL = "browser_control"


class ToolPermissionMode(str, Enum):
    DRY_RUN_ONLY = "dry_run_only"
    APPROVAL_REQUIRED = "approval_required"
    ALLOWED_AFTER_APPROVAL = "allowed_after_approval"
    BLOCKED = "blocked"


class ConnectorHealth(str, Enum):
    AVAILABLE = "available"
    NOT_CONNECTED = "not_connected"
    DISABLED = "disabled"
    PLACEHOLDER = "placeholder"
    ERROR = "error"


class AionToolDefinition(BaseModel):
    tool_id: str
    name: str
    provider: ToolProviderType
    action_type: str
    description: str = ""

    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)

    risk_level: ToolRiskLevel = ToolRiskLevel.READ_ONLY
    permission_mode: ToolPermissionMode = ToolPermissionMode.DRY_RUN_ONLY

    dry_run_supported: bool = True
    requires_approval: bool = False
    external_write: bool = False
    enabled: bool = True
    connector_health: ConnectorHealth = ConnectorHealth.AVAILABLE

    metadata: Dict[str, Any] = Field(default_factory=dict)


def build_default_tool_registry() -> List[AionToolDefinition]:
    return [
        AionToolDefinition(
            tool_id="tool.gmail.search_match.v1",
            name="Gmail search/match",
            provider=ToolProviderType.NATIVE_LOCAL,
            action_type="gmail_message_match",
            description="Match Gmail-like messages against a workflow query. Current implementation is dry-run/local sample input only.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "message": {"type": "object"},
                },
                "required": ["query", "message"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "matched": {"type": "boolean"},
                    "message_id": {"type": "string"},
                },
            },
            risk_level=ToolRiskLevel.READ_ONLY,
            permission_mode=ToolPermissionMode.DRY_RUN_ONLY,
            dry_run_supported=True,
            requires_approval=False,
            external_write=False,
            connector_health=ConnectorHealth.AVAILABLE,
        ),
        AionToolDefinition(
            tool_id="tool.gmail.poll_dry_run.v1",
            name="Gmail dry-run poll",
            provider=ToolProviderType.NATIVE_LOCAL,
            action_type="gmail_poll_dry_run",
            description="Simulate Gmail polling using supplied sample messages. Does not connect to real Gmail.",
            input_schema={
                "type": "object",
                "properties": {
                    "messages": {"type": "array", "items": {"type": "object"}},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "matched": {"type": "integer"},
                    "skipped": {"type": "integer"},
                    "deduped": {"type": "integer"},
                    "runs": {"type": "array"},
                },
            },
            risk_level=ToolRiskLevel.READ_ONLY,
            permission_mode=ToolPermissionMode.DRY_RUN_ONLY,
            dry_run_supported=True,
            requires_approval=False,
            external_write=False,
            connector_health=ConnectorHealth.AVAILABLE,
        ),
        AionToolDefinition(
            tool_id="tool.gmail.draft_preview.v1",
            name="Gmail draft preview",
            provider=ToolProviderType.NATIVE_LOCAL,
            action_type="gmail_draft_preview",
            description="Prepare an email draft preview in replay output only. Does not create a real Gmail draft.",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                    "dry_run": {"type": "boolean"},
                },
            },
            risk_level=ToolRiskLevel.DRAFT_ONLY,
            permission_mode=ToolPermissionMode.DRY_RUN_ONLY,
            dry_run_supported=True,
            requires_approval=True,
            external_write=False,
            connector_health=ConnectorHealth.AVAILABLE,
        ),
        AionToolDefinition(
            tool_id="tool.gmail.create_draft.v1",
            name="Gmail create draft",
            provider=ToolProviderType.DIRECT_API,
            action_type="gmail_create_draft",
            description="Future connector action for creating a real Gmail draft after approval.",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "draft_id": {"type": "string"},
                    "url": {"type": "string"},
                },
            },
            risk_level=ToolRiskLevel.EXTERNAL_WRITE,
            permission_mode=ToolPermissionMode.APPROVAL_REQUIRED,
            dry_run_supported=True,
            requires_approval=True,
            external_write=True,
            enabled=False,
            connector_health=ConnectorHealth.NOT_CONNECTED,
            metadata={"placeholder": True},
        ),
        AionToolDefinition(
            tool_id="tool.hubspot.contact_upsert_dry_run.v1",
            name="HubSpot create/update contact dry-run",
            provider=ToolProviderType.NATIVE_LOCAL,
            action_type="hubspot_create_or_update_contact",
            description="Prepare a HubSpot contact create/update payload without writing to HubSpot.",
            input_schema={
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "firstname": {"type": "string"},
                    "phone": {"type": "string"},
                    "company": {"type": "string"},
                    "message": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "would_create_or_update_contact": {"type": "boolean"},
                    "field_mapping": {"type": "object"},
                    "dry_run": {"type": "boolean"},
                },
            },
            risk_level=ToolRiskLevel.EXTERNAL_WRITE,
            permission_mode=ToolPermissionMode.DRY_RUN_ONLY,
            dry_run_supported=True,
            requires_approval=True,
            external_write=True,
            connector_health=ConnectorHealth.AVAILABLE,
        ),
        AionToolDefinition(
            tool_id="tool.notify_user.v1",
            name="Notify user",
            provider=ToolProviderType.NATIVE_LOCAL,
            action_type="notify_user",
            description="Prepare a local user notification.",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            risk_level=ToolRiskLevel.READ_ONLY,
            permission_mode=ToolPermissionMode.DRY_RUN_ONLY,
            dry_run_supported=True,
            requires_approval=False,
            external_write=False,
            connector_health=ConnectorHealth.AVAILABLE,
        ),
        AionToolDefinition(
            tool_id="tool.approval.checkpoint.v1",
            name="Manual approval checkpoint",
            provider=ToolProviderType.MANUAL_STUB,
            action_type="approval_checkpoint",
            description="Stop workflow execution and require human approval before external action.",
            input_schema={"type": "object"},
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "require_human": {"type": "boolean"},
                },
            },
            risk_level=ToolRiskLevel.READ_ONLY,
            permission_mode=ToolPermissionMode.APPROVAL_REQUIRED,
            dry_run_supported=True,
            requires_approval=True,
            external_write=False,
            connector_health=ConnectorHealth.AVAILABLE,
        ),
        AionToolDefinition(
            tool_id="tool.stackone.crm.contact_upsert.v1",
            name="StackOne CRM contact create/update",
            provider=ToolProviderType.STACKONE,
            action_type="crm_contact_upsert",
            description="Future StackOne-backed CRM contact create/update tool.",
            risk_level=ToolRiskLevel.EXTERNAL_WRITE,
            permission_mode=ToolPermissionMode.APPROVAL_REQUIRED,
            dry_run_supported=True,
            requires_approval=True,
            external_write=True,
            enabled=False,
            connector_health=ConnectorHealth.PLACEHOLDER,
            metadata={"placeholder": True},
        ),
        AionToolDefinition(
            tool_id="tool.google.search.v1",
            name="Google Search",
            provider=ToolProviderType.GOOGLE_ADK_BRIDGE,
            action_type="google_search",
            description="Future Google ADK-backed grounded search tool.",
            risk_level=ToolRiskLevel.READ_ONLY,
            permission_mode=ToolPermissionMode.DRY_RUN_ONLY,
            dry_run_supported=True,
            requires_approval=False,
            external_write=False,
            enabled=False,
            connector_health=ConnectorHealth.PLACEHOLDER,
            metadata={"placeholder": True},
        ),
        AionToolDefinition(
            tool_id="tool.google_cloud.api_registry_mcp.v1",
            name="Google Cloud API Registry MCP tool",
            provider=ToolProviderType.MCP,
            action_type="google_cloud_api_registry_mcp",
            description="Future MCP bridge for Google Cloud API Registry tools.",
            risk_level=ToolRiskLevel.EXTERNAL_WRITE,
            permission_mode=ToolPermissionMode.APPROVAL_REQUIRED,
            dry_run_supported=True,
            requires_approval=True,
            external_write=True,
            enabled=False,
            connector_health=ConnectorHealth.PLACEHOLDER,
            metadata={"placeholder": True},
        ),
        AionToolDefinition(
            tool_id="tool.browser.computer_use.v1",
            name="Browser / computer-use action",
            provider=ToolProviderType.BROWSER_CONTROL,
            action_type="browser_control",
            description="Future controlled browser/computer-use action. High risk; blocked by default.",
            risk_level=ToolRiskLevel.BROWSER_CONTROL,
            permission_mode=ToolPermissionMode.BLOCKED,
            dry_run_supported=True,
            requires_approval=True,
            external_write=True,
            enabled=False,
            connector_health=ConnectorHealth.PLACEHOLDER,
            metadata={"placeholder": True},
        ),
        AionToolDefinition(
            tool_id="tool.n8n.workflow_trigger.v1",
            name="n8n workflow trigger",
            provider=ToolProviderType.N8N,
            action_type="n8n_workflow_trigger",
            description="Future n8n workflow trigger integration.",
            risk_level=ToolRiskLevel.EXTERNAL_WRITE,
            permission_mode=ToolPermissionMode.APPROVAL_REQUIRED,
            dry_run_supported=True,
            requires_approval=True,
            external_write=True,
            enabled=False,
            connector_health=ConnectorHealth.PLACEHOLDER,
            metadata={"placeholder": True},
        ),
    ]


class ToolRegistryStore:
    def __init__(self, base_dir: str) -> None:
        self.base_path = Path(base_dir) / "tool_registry"
        self.registry_path = self.base_path / "tools.json"
        self.base_path.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            self.save_tools(build_default_tool_registry())

    def save_tools(self, tools: List[AionToolDefinition]) -> None:
        self.registry_path.write_text(
            json.dumps(
                [tool.model_dump(mode="json") for tool in tools],
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    def list_tools(self) -> List[Dict[str, Any]]:
        try:
            data = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            data = []

        if not isinstance(data, list) or not data:
            tools = build_default_tool_registry()
            self.save_tools(tools)
            return [tool.model_dump(mode="json") for tool in tools]

        return [item for item in data if isinstance(item, dict)]

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        for tool in self.list_tools():
            if tool.get("tool_id") == tool_id:
                return tool
        return None

    def find_by_action_type(self, action_type: str) -> Optional[Dict[str, Any]]:
        for tool in self.list_tools():
            if tool.get("action_type") == action_type:
                return tool
        return None
