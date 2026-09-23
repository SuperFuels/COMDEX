from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.modules.workflow_capsules.architect.builder_spec import SCHEMA_VERSION
from backend.modules.workflow_capsules.architect.node_registry import ArchitectNodeRegistry
from backend.modules.connectors.connector_registry import get_connector_registry


@dataclass(slots=True)
class WorkflowBuildPack:
    business_context: Dict[str, Any]
    user_task: Dict[str, Any]
    credentials: Dict[str, Any]
    node_registry: Dict[str, Any]
    connector_catalogue: Dict[str, Any]
    connector_build_rules: Dict[str, Any]
    canvas_build_rules: Dict[str, Any]
    permission_runtime_rules: Dict[str, Any]
    required_output_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorkflowBuildPackAssembler:
    """
    Builds the context/instruction pack sent to external AI providers.

    This is the only thing provider models should receive for workflow building.
    """

    def assemble(
        self,
        *,
        workflow_goal: str,
        user_steps: Optional[List[Dict[str, Any]]] = None,
        business_context: Optional[Dict[str, Any]] = None,
        connected_credentials: Optional[List[str]] = None,
        missing_credentials: Optional[List[str]] = None,
        must_not_do: Optional[List[str]] = None,
    ) -> WorkflowBuildPack:
        registry = ArchitectNodeRegistry()
        connector_registry = get_connector_registry()

        return WorkflowBuildPack(
            business_context=business_context
            or {
                "business_name": "",
                "industry": "",
                "services": [],
                "tone_of_voice": "",
                "contacts_departments": [],
                "business_rules": [],
                "approval_preferences": {
                    "external_writes_require_approval": True,
                    "live_send_enabled": False,
                },
                "sops_templates": [],
            },
            user_task={
                "workflow_goal": workflow_goal,
                "user_steps": list(user_steps or []),
                "desired_outcome": workflow_goal,
                "must_not_do": list(must_not_do or ["do not send live emails"]),
            },
            credentials={
                "connected": list(connected_credentials or []),
                "missing": list(missing_credentials or []),
            },
            node_registry=registry.to_dict(),
            connector_catalogue=connector_registry.to_dict(),
            connector_build_rules={
                "gmail_reference_connector": True,
                "gmail_catalogue_source": "Aion connector registry, based on common automation-platform Gmail modules.",
                "gmail_preferred_draft_action": "gmail.create_draft",
                "gmail_send_future_only": True,
                "gmail_create_draft": {
                    "allowed": True,
                    "requires_approval": True,
                    "live_execution_enabled": False,
                    "rule": "Use gmail.create_draft when preparing an email. It creates a draft only after approval. It must not send.",
                },
                "gmail_send_email": {
                    "allowed_in_ui_as_locked_capability": True,
                    "provider_should_not_generate_by_default": True,
                    "live_execution_enabled": False,
                    "rule": "Do not use gmail.send_email unless the user explicitly requests live send. Even then mark future-only/blocked.",
                },
                "gmail_reply_email": {
                    "allowed_in_ui_as_locked_capability": True,
                    "provider_should_not_generate_by_default": True,
                    "live_execution_enabled": False,
                    "rule": "Do not use gmail.reply_email unless the user explicitly requests live reply. Even then mark future-only/blocked.",
                },
                "gmail_send_draft": {
                    "allowed_in_ui_as_locked_capability": True,
                    "provider_should_not_generate_by_default": True,
                    "live_execution_enabled": False,
                    "rule": "Do not use gmail.send_draft. Sending drafts is a future live-send phase.",
                },
                "gmail_api_call": {
                    "allowed": False,
                    "rule": "Custom Gmail API calls are blocked unless allowlisted in a future connector policy.",
                },
                "long_tail_integrations": {
                    "native_for_high_value_apps_only": True,
                    "generic_http_connector": "Use http.request/webhook.receive for controlled generic API coverage after policy configuration.",
                    "automation_bridge": "Use Make/Zapier/n8n bridge for long-tail app coverage instead of building 3000 native connectors.",
                },
            },
            canvas_build_rules={
                "node_ids": "Use stable snake_case step_id values.",
                "edges": "Edges must reference existing step_id values.",
                "routers": "Use router or if_else nodes only from the registry.",
                "variables": "Use set_variable/get_variable nodes for reusable values.",
                "compose": "Use compose_string for generated text.",
                "approval": "Insert human_approval before external writes.",
                "missing_connectors": "Use missing_connector_placeholder for unavailable integrations.",
            },
            permission_runtime_rules={
                "dry_run_first": True,
                "approval_before_external_write": True,
                "live_send_disabled": True,
                "no_branch_bypass_permission_evaluator": True,
                "missing_credentials_placeholder_only": True,
                "providers_are_untrusted_proposers": True,
            },
            required_output_schema={
                "schema_version": SCHEMA_VERSION,
                "strict_json_only": True,
                "no_markdown": True,
                "no_invented_node_types": True,
                "no_freeform_code": True,
                "required_top_level_fields": [
                    "schema_version",
                    "workflow_name",
                    "goal",
                    "requires_clarification",
                    "connectors_required",
                    "missing_connectors",
                    "steps",
                    "edges",
                ],
            },
        )
