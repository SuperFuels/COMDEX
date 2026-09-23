from __future__ import annotations

from typing import Any, Dict, List

from backend.modules.local_node.contracts_local_node import utc_now_iso


class ExternalToolDiscoveryService:
    """
    Phase 5 connector discovery stub.

    This does not call StackOne or MCP yet.
    It defines the normalized shape Aion expects when external connector
    tools are discovered later.
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def list_stackone_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "tool_id": "tool.stackone.crm.contact_upsert.v1",
                "name": "StackOne CRM contact create/update",
                "provider": "stackone",
                "provider_category": "crm",
                "connected_account": None,
                "connection_id": None,
                "action_type": "crm_contact_upsert",
                "description": "Placeholder StackOne CRM contact create/update action. External write remains blocked until connector and approval policy are enabled.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "firstname": {"type": "string"},
                        "lastname": {"type": "string"},
                        "phone": {"type": "string"},
                        "company": {"type": "string"},
                    },
                    "required": ["email"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "dry_run": {"type": "boolean"},
                        "would_create_or_update_contact": {"type": "boolean"},
                        "external_write_blocked": {"type": "boolean"},
                    },
                },
                "risk_level": "external_write",
                "permission_mode": "dry_run_only",
                "dry_run_supported": True,
                "requires_approval": True,
                "external_write": True,
                "enabled": False,
                "connector_health": "placeholder",
                "tool_discovery_status": "stubbed",
                "metadata": {
                    "phase": "phase_5_stackone_mcp_pilot",
                    "adapter": "stackone_stub",
                },
            },
            {
                "tool_id": "tool.stackone.hris.employee_lookup.v1",
                "name": "StackOne HRIS employee lookup",
                "provider": "stackone",
                "provider_category": "hris",
                "connected_account": None,
                "connection_id": None,
                "action_type": "hris_employee_lookup",
                "description": "Placeholder StackOne HRIS read-only lookup action.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "employee_id": {"type": "string"},
                    },
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "matched": {"type": "boolean"},
                        "employee": {"type": "object"},
                    },
                },
                "risk_level": "read_only",
                "permission_mode": "dry_run_only",
                "dry_run_supported": True,
                "requires_approval": False,
                "external_write": False,
                "enabled": False,
                "connector_health": "placeholder",
                "tool_discovery_status": "stubbed",
                "metadata": {
                    "phase": "phase_5_stackone_mcp_pilot",
                    "adapter": "stackone_stub",
                },
            },
            {
                "tool_id": "tool.stackone.ats.candidate_action.v1",
                "name": "StackOne ATS candidate action",
                "provider": "stackone",
                "provider_category": "ats",
                "connected_account": None,
                "connection_id": None,
                "action_type": "ats_candidate_action",
                "description": "Placeholder StackOne ATS candidate action. External write remains blocked.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "candidate_email": {"type": "string"},
                        "action": {"type": "string"},
                        "note": {"type": "string"},
                    },
                    "required": ["candidate_email", "action"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "dry_run": {"type": "boolean"},
                        "external_write_blocked": {"type": "boolean"},
                    },
                },
                "risk_level": "external_write",
                "permission_mode": "dry_run_only",
                "dry_run_supported": True,
                "requires_approval": True,
                "external_write": True,
                "enabled": False,
                "connector_health": "placeholder",
                "tool_discovery_status": "stubbed",
                "metadata": {
                    "phase": "phase_5_stackone_mcp_pilot",
                    "adapter": "stackone_stub",
                },
            },
        ]

    def list_mcp_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "tool_id": "tool.mcp.hubspot.contact_upsert.v1",
                "name": "HubSpot MCP contact create/update",
                "provider": "mcp",
                "server_id": "mcp.hubspot.remote",
                "tool_name": "hubspot_contact_upsert",
                "action_type": "hubspot_contact_upsert",
                "description": "HubSpot MCP contact create/update action. Phase 6D maps workflow CRM payloads to this tool but keeps execution dry-run only.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "firstname": {"type": "string"},
                        "lastname": {"type": "string"},
                        "phone": {"type": "string"},
                        "company": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["email"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "dry_run": {"type": "boolean"},
                        "would_create_or_update_contact": {"type": "boolean"},
                        "external_write_blocked": {"type": "boolean"},
                    },
                },
                "permissions": {
                    "mode": "dry_run_only",
                    "requires_approval": True,
                    "external_write": True,
                },
                "risk_level": "external_write",
                "permission_mode": "dry_run_only",
                "dry_run_supported": True,
                "requires_approval": True,
                "external_write": True,
                "enabled": False,
                "connector_health": "available_if_hubspot_mcp_connected",
                "tool_discovery_status": "mapped_stub",
                "metadata": {
                    "phase": "phase_6_hubspot_mcp_mapping",
                    "adapter": "hubspot_mcp",
                    "real_write_enabled": False,
                },
            },
            {
                "tool_id": "tool.mcp.google_cloud.api_registry.v1",
                "name": "Google Cloud API Registry MCP tool",
                "provider": "mcp",
                "server_id": "mcp.google_cloud.local_stub",
                "tool_name": "google_cloud_api_registry",
                "action_type": "google_cloud_api_registry",
                "description": "Placeholder MCP tool for Google Cloud API Registry style operations. Writes remain blocked.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "service": {"type": "string"},
                        "operation": {"type": "string"},
                    },
                    "required": ["project_id", "operation"],
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "dry_run": {"type": "boolean"},
                        "planned_operation": {"type": "object"},
                        "external_write_blocked": {"type": "boolean"},
                    },
                },
                "permissions": {
                    "mode": "dry_run_only",
                    "requires_approval": True,
                    "external_write": True,
                },
                "risk_level": "external_write",
                "permission_mode": "dry_run_only",
                "dry_run_supported": True,
                "requires_approval": True,
                "external_write": True,
                "enabled": False,
                "connector_health": "placeholder",
                "tool_discovery_status": "stubbed",
                "metadata": {
                    "phase": "phase_5_stackone_mcp_pilot",
                    "adapter": "mcp_stub",
                },
            }
        ]

    def list_external_tools(self) -> Dict[str, Any]:
        stackone_tools = self.list_stackone_tools()
        mcp_tools = self.list_mcp_tools()
        items = stackone_tools + mcp_tools

        return {
            "ok": True,
            "items": items,
            "count": len(items),
            "providers": {
                "stackone": {
                    "configured": False,
                    "tool_count": len(stackone_tools),
                    "connection_status": "not_connected",
                    "tool_discovery_status": "stubbed",
                },
                "mcp": {
                    "configured": False,
                    "tool_count": len(mcp_tools),
                    "connection_status": "not_connected",
                    "tool_discovery_status": "stubbed",
                },
            },
            "safety": {
                "external_writes_default": "dry_run_only",
                "approval_required": True,
                "writes_blocked_until_explicit_enablement": True,
            },
            "at": utc_now_iso(),
        }
