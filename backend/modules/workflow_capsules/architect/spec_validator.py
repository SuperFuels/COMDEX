from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from backend.modules.workflow_capsules.architect.builder_spec import (
    SCHEMA_VERSION,
    WorkflowBuilderSpec,
)
from backend.modules.workflow_capsules.architect.node_registry import ArchitectNodeRegistry


FORBIDDEN_TOKENS = {
    "live_send",
    "gmail_live_send",
    "send_message",
    "users.messages.send",
    "gmail.send_email",
    "gmail.reply_email",
    "gmail.send_draft",
    "gmail.api_call",
    "eval(",
    "exec(",
    "subprocess",
    "os.system",
}


@dataclass(slots=True)
class WorkflowBuilderValidationResult:
    ok: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    audit: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "audit": dict(self.audit),
        }


class WorkflowBuilderSpecValidator:
    def __init__(self, registry: ArchitectNodeRegistry | None = None) -> None:
        self.registry = registry or ArchitectNodeRegistry()

    def validate(
        self,
        spec: WorkflowBuilderSpec,
        *,
        connected_credentials: List[str] | None = None,
    ) -> WorkflowBuilderValidationResult:
        connected = set(connected_credentials or [])
        errors: List[str] = []
        warnings: List[str] = []

        blocked_gmail_actions = {
            "gmail.send_email",
            "gmail.reply_email",
            "gmail.send_draft",
            "gmail.api_call",
        }

        known_connector_action_prefixes = (
            "gmail.",
            "hubspot.",
            "mailchimp.",
            "http.",
            "webhook.",
            "automation_bridge.",
            "make.",
            "zapier.",
            "n8n.",
        )

        raw_text = str(spec.to_dict()).lower()
        for token in FORBIDDEN_TOKENS:
            if token.lower() in raw_text:
                errors.append(f"forbidden_token:{token}")

        if spec.schema_version != SCHEMA_VERSION:
            errors.append("invalid_schema_version")

        if not spec.workflow_name.strip():
            errors.append("missing_workflow_name")

        if not spec.goal.strip():
            errors.append("missing_goal")

        step_ids: Set[str] = set()
        external_write_steps: Set[str] = set()
        approval_steps: Set[str] = set()

        for step in spec.steps:
            if not step.step_id:
                errors.append("step_missing_step_id")
                continue

            if step.step_id in step_ids:
                errors.append(f"duplicate_step_id:{step.step_id}")
            step_ids.add(step.step_id)

            if not self.registry.has(step.node_type):
                errors.append(f"unknown_node_type:{step.node_type}")
                continue

            node = self.registry.require(step.node_type)

            configured_action = str(
                step.config.get("action")
                or (step.config.get("permission") or {}).get("action")
                or step.config.get("connector_action")
                or step.node_type
                or ""
            ).strip()

            if configured_action in blocked_gmail_actions:
                errors.append(f"blocked_gmail_action:{step.step_id}:{configured_action}")

            if (
                "." in configured_action
                and configured_action.startswith(known_connector_action_prefixes)
                and configured_action not in {step.node_type, "gmail.read"}
                and not self.registry.has(configured_action)
            ):
                errors.append(f"unknown_connector_action:{step.step_id}:{configured_action}")

            if step.node_type == "gmail.create_draft" and not step.requires_approval:
                has_local_approval_flag = bool(
                    step.config.get("requires_approval") is True
                    or (step.config.get("permission") or {}).get("requires_approval") is True
                )
                if not has_local_approval_flag:
                    errors.append(f"gmail_create_draft_without_approval:{step.step_id}")

            for field_name in node.required_config:
                if field_name not in step.config or step.config.get(field_name) in (None, ""):
                    errors.append(f"missing_required_config:{step.step_id}:{field_name}")

            connector = step.connector or node.connector
            if connector and connector not in connected:
                if not step.missing_connector and step.node_type != "missing_connector_placeholder":
                    warnings.append(f"connector_not_connected:{step.step_id}:{connector}")

            if node.external_write:
                external_write_steps.add(step.step_id)

            if step.node_type == "human_approval" or step.requires_approval:
                approval_steps.add(step.step_id)

            if step.node_type == "missing_connector_placeholder" and not step.missing_connector:
                warnings.append(f"missing_connector_placeholder_should_be_marked:{step.step_id}")

        for edge in spec.edges:
            if edge.source not in step_ids:
                errors.append(f"edge_unknown_source:{edge.source}")
            if edge.target not in step_ids:
                errors.append(f"edge_unknown_target:{edge.target}")

        if external_write_steps and not approval_steps:
            errors.append("external_write_without_approval_checkpoint")

        return WorkflowBuilderValidationResult(
            ok=not errors,
            errors=errors,
            warnings=warnings,
            audit={
                "step_count": len(spec.steps),
                "edge_count": len(spec.edges),
                "external_write_steps": sorted(external_write_steps),
                "approval_steps": sorted(approval_steps),
                "connected_credentials": sorted(connected),
            },
        )
