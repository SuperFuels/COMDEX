from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from backend.modules.connectors.connector_registry import get_connector_registry


@dataclass(frozen=True, slots=True)
class ArchitectNodeDefinition:
    node_type: str
    label: str
    required_config: List[str] = field(default_factory=list)
    connector: Optional[str] = None
    risk_tier: str = "low"
    external_write: bool = False
    requires_approval: bool = False
    produces: List[str] = field(default_factory=list)
    placeholder_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArchitectNodeRegistry:
    """
    Approved Meccano set for Aion Workflow Architect.

    External AI providers may only use node types in this registry.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, ArchitectNodeDefinition] = {
            # Core Aion workflow primitives.
            "extract_fields": ArchitectNodeDefinition(
                node_type="extract_fields",
                label="Extract Fields",
                required_config=["fields"],
                risk_tier="low",
                produces=["extracted"],
            ),
            "set_variable": ArchitectNodeDefinition(
                node_type="set_variable",
                label="Set Variable",
                required_config=["name", "value"],
                risk_tier="low",
                produces=["variable"],
            ),
            "get_variable": ArchitectNodeDefinition(
                node_type="get_variable",
                label="Get Variable",
                required_config=["name"],
                risk_tier="low",
                produces=["value"],
            ),
            "compose_string": ArchitectNodeDefinition(
                node_type="compose_string",
                label="Compose String",
                required_config=[],
                risk_tier="low",
                produces=["output"],
            ),
            "human_approval": ArchitectNodeDefinition(
                node_type="human_approval",
                label="Human Approval",
                required_config=["reason"],
                risk_tier="medium",
                requires_approval=True,
                produces=["approval"],
            ),
            "hubspot.upsert_contact": ArchitectNodeDefinition(
                node_type="hubspot.upsert_contact",
                label="Create or Update HubSpot Contact",
                required_config=["email"],
                connector="hubspot",
                risk_tier="medium",
                external_write=True,
                requires_approval=True,
                produces=["contact_id"],
            ),
            "router": ArchitectNodeDefinition(
                node_type="router",
                label="Router",
                required_config=["routes"],
                risk_tier="low",
                produces=["route"],
            ),
            "if_else": ArchitectNodeDefinition(
                node_type="if_else",
                label="If / Else",
                required_config=["condition"],
                risk_tier="low",
                produces=["branch"],
            ),
            "missing_connector_placeholder": ArchitectNodeDefinition(
                node_type="missing_connector_placeholder",
                label="Missing Connector Placeholder",
                required_config=["connector", "reason"],
                risk_tier="blocked",
                placeholder_only=True,
                produces=[],
            ),
        }

        self._register_connector_actions()

    def _register_connector_actions(self) -> None:
        """
        Import safe connector actions into the Workflow Architect registry.

        This keeps the Architect provider prompt aligned with the universal
        connector catalogue while still preserving Aion-only workflow primitives.
        """

        registry = get_connector_registry()

        required_config_by_action = {
            "gmail.watch_emails": ["account", "trigger"],
            "gmail.search_emails": ["query"],
            "gmail.get_email": ["message_id"],
            "gmail.list_attachments": ["message_id"],
            "gmail.create_draft": ["to", "body"],
            "gmail.update_labels": ["message_id", "labels"],
            "gmail.mark_read": ["message_id"],
            "gmail.mark_unread": ["message_id"],
            "gmail.copy_email": ["message_id", "destination"],
            "gmail.move_email": ["message_id", "destination"],
            "gmail.delete_email": ["message_id"],
            "gmail.send_email": ["to", "subject", "body"],
            "gmail.reply_email": ["message_id", "body"],
            "gmail.send_draft": ["draft_id"],
            "gmail.api_call": ["method", "path"],
            "http.request": ["method", "url"],
            "webhook.receive": ["path"],
            "automation_bridge.trigger_scenario": ["bridge", "scenario_id"],
        }

        produces_by_action = {
            "gmail.watch_emails": ["message_id", "sender", "subject", "body", "received_at"],
            "gmail.search_emails": ["messages"],
            "gmail.get_email": ["message"],
            "gmail.list_attachments": ["attachments"],
            "gmail.create_draft": ["draft_id"],
            "gmail.update_labels": ["message_id", "labels"],
            "gmail.mark_read": ["message_id"],
            "gmail.mark_unread": ["message_id"],
            "gmail.copy_email": ["message_id"],
            "gmail.move_email": ["message_id"],
            "gmail.delete_email": ["message_id"],
            "gmail.send_email": ["message_id"],
            "gmail.reply_email": ["message_id"],
            "gmail.send_draft": ["message_id"],
            "gmail.api_call": ["response"],
            "http.request": ["response"],
            "webhook.receive": ["payload"],
            "automation_bridge.trigger_scenario": ["bridge_run_id"],
        }

        # Backwards compatibility for older generated specs.
        alias_node_types = {
            "gmail.read": "gmail.get_email",
        }

        for action in registry.list_actions():
            connector_id = str(getattr(action, "connector_id", "") or action.action_id.split(".", 1)[0])
            node_type = str(action.action_id)

            self._nodes[node_type] = ArchitectNodeDefinition(
                node_type=node_type,
                label=str(action.label),
                required_config=required_config_by_action.get(node_type, []),
                connector=connector_id,
                risk_tier=str(action.risk_tier),
                external_write=bool(action.external_write),
                requires_approval=bool(action.requires_approval),
                produces=produces_by_action.get(node_type, []),
                placeholder_only=str(action.permission_mode) == "blocked",
            )

        for alias, target in alias_node_types.items():
            if target in self._nodes and alias not in self._nodes:
                target_node = self._nodes[target]

                # Legacy Architect compatibility:
                # gmail.read historically means "poll/watch/read new Gmail email",
                # not "get a specific message by message_id".
                if alias == "gmail.read":
                    self._nodes[alias] = ArchitectNodeDefinition(
                        node_type=alias,
                        label="Read Gmail",
                        required_config=["account", "trigger"],
                        connector="gmail",
                        risk_tier="low",
                        external_write=False,
                        requires_approval=False,
                        produces=["sender", "subject", "body", "received_at"],
                        placeholder_only=False,
                    )
                    continue

                self._nodes[alias] = ArchitectNodeDefinition(
                    node_type=alias,
                    label=target_node.label,
                    required_config=target_node.required_config,
                    connector=target_node.connector,
                    risk_tier=target_node.risk_tier,
                    external_write=target_node.external_write,
                    requires_approval=target_node.requires_approval,
                    produces=target_node.produces,
                    placeholder_only=target_node.placeholder_only,
                )

    def all(self) -> List[ArchitectNodeDefinition]:
        return list(self._nodes.values())

    def to_dict(self) -> Dict[str, Any]:
        return {key: node.to_dict() for key, node in self._nodes.items()}

    def has(self, node_type: str) -> bool:
        return node_type in self._nodes

    def require(self, node_type: str) -> ArchitectNodeDefinition:
        if node_type not in self._nodes:
            raise KeyError(f"Unknown architect node type: {node_type}")
        return self._nodes[node_type]
