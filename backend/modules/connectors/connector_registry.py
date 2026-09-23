from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Literal, Optional


RiskTier = Literal["low", "medium", "high", "blocked"]
PermissionMode = Literal[
    "read",
    "draft_write",
    "approval_write",
    "live_write_blocked",
    "blocked",
]
ActionKind = Literal["trigger", "read", "write", "draft", "delete", "custom_api", "utility"]


@dataclass(frozen=True)
class ConnectorAction:
    action_id: str
    label: str
    kind: ActionKind
    risk_tier: RiskTier
    permission_mode: PermissionMode
    connector_id: str = ""
    requires_approval: bool = False
    external_write: bool = False
    live_execution_enabled: bool = False
    dry_run_supported: bool = True
    requires_vault: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    ui_icon: str = ""
    ui_group: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "connector_id": self.connector_id,
            "label": self.label,
            "kind": self.kind,
            "risk_tier": self.risk_tier,
            "permission_mode": self.permission_mode,
            "requires_approval": self.requires_approval,
            "external_write": self.external_write,
            "live_execution_enabled": self.live_execution_enabled,
            "dry_run_supported": self.dry_run_supported,
            "requires_vault": list(self.requires_vault),
            "aliases": list(self.aliases),
            "description": self.description,
            "ui_icon": self.ui_icon,
            "ui_group": self.ui_group,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ConnectorDefinition:
    connector_id: str
    label: str
    category: str
    actions: List[ConnectorAction]
    description: str = ""
    native_status: str = "planned"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connector_id": self.connector_id,
            "label": self.label,
            "category": self.category,
            "description": self.description,
            "native_status": self.native_status,
            "actions": [action.to_dict() for action in self.actions],
        }


class ConnectorRegistry:
    def __init__(self, *, seed_defaults: bool = True) -> None:
        self._connectors: Dict[str, ConnectorDefinition] = {}

        if seed_defaults:
            self.register(_gmail_connector())
            self.register(_http_connector())
            self.register(_make_connector())
            self.register(_zapier_connector())
            self.register(_n8n_connector())
            self.register(_automation_bridge_connector())

    def register(self, connector: ConnectorDefinition) -> None:
        stamped_actions = [
            action if action.connector_id else replace(action, connector_id=connector.connector_id)
            for action in connector.actions
        ]
        self._connectors[connector.connector_id] = replace(connector, actions=stamped_actions)

    def list_connectors(self) -> List[ConnectorDefinition]:
        return list(self._connectors.values())

    def get_connector(self, connector_id: str) -> Optional[ConnectorDefinition]:
        return self._connectors.get(connector_id)

    def list_actions(self) -> List[ConnectorAction]:
        actions: List[ConnectorAction] = []
        for connector in self._connectors.values():
            actions.extend(connector.actions)
        return actions

    def get_action(self, action_id: str) -> Optional[ConnectorAction]:
        wanted = str(action_id or "").strip()
        if not wanted:
            return None

        for action in self.list_actions():
            if action.action_id == wanted or wanted in action.aliases:
                return action
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": "aion.connector_registry.v1",
            "connectors": [connector.to_dict() for connector in self.list_connectors()],
        }


def _gmail_connector() -> ConnectorDefinition:
    vault = ["vault.gmail.credentials"]

    return ConnectorDefinition(
        connector_id="gmail",
        label="Gmail",
        category="email",
        native_status="reference_connector",
        description="Reference native connector for safe email workflow execution.",
        actions=[
            ConnectorAction(
                action_id="gmail.watch_emails",
                label="Watch emails",
                kind="trigger",
                risk_tier="low",
                permission_mode="read",
                requires_vault=vault,
                aliases=["gmail.watch", "gmail.new_email", "gmail.poll"],
                description="Triggers when new matching emails are found.",
                ui_icon="✉",
                ui_group="Triggers",
            ),
            ConnectorAction(
                action_id="gmail.search_emails",
                label="Search emails",
                kind="read",
                risk_tier="low",
                permission_mode="read",
                requires_vault=vault,
                aliases=["gmail.search", "gmail.query"],
                description="Searches Gmail using a safe query.",
                ui_icon="⌕",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.get_email",
                label="Get an email",
                kind="read",
                risk_tier="low",
                permission_mode="read",
                requires_vault=vault,
                aliases=["gmail.read", "gmail.read_email", "gmail.get"],
                description="Reads one email message and metadata.",
                ui_icon="▣",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.list_attachments",
                label="List email attachments",
                kind="read",
                risk_tier="low",
                permission_mode="read",
                requires_vault=vault,
                aliases=["gmail.attachments", "gmail.list_email_attachments"],
                description="Lists attachments for an email.",
                ui_icon="⌘",
                ui_group="Attachment",
            ),
            ConnectorAction(
                action_id="gmail.create_draft",
                label="Create draft email",
                kind="draft",
                risk_tier="medium",
                permission_mode="draft_write",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail_create_draft", "gmail.draft", "gmail.create_draft_email"],
                description="Creates a Gmail draft after approval. Does not send.",
                ui_icon="✎",
                ui_group="Draft",
            ),
            ConnectorAction(
                action_id="gmail.update_labels",
                label="Update email labels",
                kind="write",
                risk_tier="medium",
                permission_mode="approval_write",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.labels", "gmail.update_email_labels"],
                description="Updates labels after approval.",
                ui_icon="🏷",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.mark_read",
                label="Mark email as read",
                kind="write",
                risk_tier="medium",
                permission_mode="approval_write",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.mark_as_read"],
                description="Marks an email as read after approval.",
                ui_icon="✓",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.mark_unread",
                label="Mark email as unread",
                kind="write",
                risk_tier="medium",
                permission_mode="approval_write",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.mark_as_unread"],
                description="Marks an email as unread after approval.",
                ui_icon="●",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.copy_email",
                label="Copy email",
                kind="write",
                risk_tier="medium",
                permission_mode="approval_write",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.copy"],
                description="Copies an email or draft after approval.",
                ui_icon="⧉",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.move_email",
                label="Move email",
                kind="write",
                risk_tier="medium",
                permission_mode="approval_write",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.move"],
                description="Moves an email or draft after approval.",
                ui_icon="⇥",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.delete_email",
                label="Delete email",
                kind="delete",
                risk_tier="high",
                permission_mode="live_write_blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.delete", "gmail.trash"],
                description="Blocked until a future explicit live-write phase.",
                ui_icon="⌫",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.send_email",
                label="Send email",
                kind="write",
                risk_tier="high",
                permission_mode="live_write_blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.send"],
                description="Visible but blocked until live Gmail send is explicitly enabled.",
                ui_icon="↗",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.reply_email",
                label="Reply to email",
                kind="write",
                risk_tier="high",
                permission_mode="live_write_blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.reply"],
                description="Visible but blocked until live Gmail replies are explicitly enabled.",
                ui_icon="↩",
                ui_group="Email",
            ),
            ConnectorAction(
                action_id="gmail.send_draft",
                label="Send draft email",
                kind="write",
                risk_tier="high",
                permission_mode="live_write_blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.send_draft_email"],
                description="Visible but blocked until live Gmail draft sending is explicitly enabled.",
                ui_icon="➤",
                ui_group="Draft",
            ),
            ConnectorAction(
                action_id="gmail.api_call",
                label="Make Gmail API call",
                kind="custom_api",
                risk_tier="blocked",
                permission_mode="blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                requires_vault=vault,
                aliases=["gmail.custom_api", "gmail.make_api_call"],
                description="Blocked unless explicitly allowlisted in a later connector policy.",
                ui_icon="{ }",
                ui_group="Other",
            ),
        ],
    )


def _http_connector() -> ConnectorDefinition:
    return ConnectorDefinition(
        connector_id="http",
        label="HTTP / Webhook",
        category="universal",
        native_status="planned",
        description="Generic webhook and API bridge for long-tail integrations.",
        actions=[
            ConnectorAction(
                action_id="http.request",
                label="HTTP request",
                kind="custom_api",
                risk_tier="high",
                permission_mode="live_write_blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                description="Generic HTTP request. Dry-run only until endpoint policy is configured.",
                ui_icon="↯",
                ui_group="Universal",
            ),
            ConnectorAction(
                action_id="webhook.receive",
                label="Receive webhook",
                kind="trigger",
                risk_tier="low",
                permission_mode="read",
                description="Receives an inbound webhook trigger.",
                ui_icon="⑂",
                ui_group="Universal",
            ),
        ],
    )


def _bridge_action(
    *,
    action_id: str,
    label: str,
    connector_id: str,
    aliases: List[str],
    description: str,
    ui_icon: str,
) -> ConnectorAction:
    return ConnectorAction(
        action_id=action_id,
        connector_id=connector_id,
        label=label,
        kind="write",
        risk_tier="high",
        permission_mode="live_write_blocked",
        requires_approval=True,
        external_write=True,
        live_execution_enabled=False,
        dry_run_supported=True,
        requires_vault=[f"vault.{connector_id}.credentials"],
        aliases=aliases,
        description=description,
        ui_icon=ui_icon,
        ui_group="Automation bridge",
        metadata={
            "bridge_connector": True,
            "permission_gated": True,
            "live_execution_policy": "future_only",
            "dry_run_first": True,
        },
    )


def _make_connector() -> ConnectorDefinition:
    return ConnectorDefinition(
        connector_id="make",
        label="Make.com",
        category="bridge",
        native_status="bridge_connector",
        description="Bridge connector for Make.com scenarios. Future-only live execution.",
        actions=[
            _bridge_action(
                action_id="make.trigger_scenario",
                connector_id="make",
                label="Trigger Make.com scenario",
                aliases=[
                    "make.com.trigger_scenario",
                    "make.trigger",
                    "make.run_scenario",
                    "automation_bridge.make",
                ],
                description="Prepares a Make.com scenario trigger after approval. Live execution remains disabled.",
                ui_icon="M",
            )
        ],
    )


def _zapier_connector() -> ConnectorDefinition:
    return ConnectorDefinition(
        connector_id="zapier",
        label="Zapier",
        category="bridge",
        native_status="bridge_connector",
        description="Bridge connector for Zapier Zaps. Future-only live execution.",
        actions=[
            _bridge_action(
                action_id="zapier.trigger_zap",
                connector_id="zapier",
                label="Trigger Zapier Zap",
                aliases=[
                    "zapier.trigger",
                    "zapier.run_zap",
                    "automation_bridge.zapier",
                ],
                description="Prepares a Zapier Zap trigger after approval. Live execution remains disabled.",
                ui_icon="Z",
            )
        ],
    )


def _n8n_connector() -> ConnectorDefinition:
    return ConnectorDefinition(
        connector_id="n8n",
        label="n8n",
        category="bridge",
        native_status="bridge_connector",
        description="Bridge connector for n8n workflows. Future-only live execution.",
        actions=[
            _bridge_action(
                action_id="n8n.trigger_workflow",
                connector_id="n8n",
                label="Trigger n8n workflow",
                aliases=[
                    "n8n.trigger",
                    "n8n.run_workflow",
                    "automation_bridge.n8n",
                ],
                description="Prepares an n8n workflow trigger after approval. Live execution remains disabled.",
                ui_icon="n8n",
            )
        ],
    )


def _automation_bridge_connector() -> ConnectorDefinition:
    return ConnectorDefinition(
        connector_id="automation_bridge",
        label="Legacy automation bridge",
        category="bridge",
        native_status="legacy_alias",
        description="Legacy bridge alias retained for backwards compatibility. Prefer explicit Make.com, Zapier, or n8n actions.",
        actions=[
            ConnectorAction(
                action_id="automation_bridge.trigger_scenario",
                label="Trigger legacy automation bridge",
                kind="write",
                risk_tier="high",
                permission_mode="live_write_blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                dry_run_supported=True,
                requires_vault=["vault.automation_bridge.credentials"],
                aliases=[
                    "automation_bridge.trigger",
                    "automation_bridge.run",
                    "make_zapier_n8n.trigger",
                ],
                description="Legacy Make/Zapier/n8n bridge placeholder. Live execution remains disabled.",
                ui_icon="↯",
                ui_group="Automation bridge",
                metadata={
                    "bridge_connector": True,
                    "legacy_alias": True,
                    "permission_gated": True,
                    "live_execution_policy": "future_only",
                    "dry_run_first": True,
                    "prefer_actions": [
                        "make.trigger_scenario",
                        "zapier.trigger_zap",
                        "n8n.trigger_workflow",
                    ],
                },
            )
        ],
    )



_CONNECTOR_REGISTRY: Optional[ConnectorRegistry] = None


def get_connector_registry() -> ConnectorRegistry:
    global _CONNECTOR_REGISTRY

    if _CONNECTOR_REGISTRY is None:
        _CONNECTOR_REGISTRY = ConnectorRegistry()

    return _CONNECTOR_REGISTRY
