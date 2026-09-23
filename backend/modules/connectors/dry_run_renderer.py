from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.modules.connectors.connector_registry import (
    ConnectorAction,
    get_connector_registry,
)


@dataclass(frozen=True)
class ConnectorDryRunPreview:
    action_id: str
    connector_id: str
    ok: bool
    dry_run: bool = True
    status: str = "previewed"
    title: str = ""
    message: str = ""
    risk_tier: str = "low"
    permission_mode: str = "read"
    requires_approval: bool = False
    external_write: bool = False
    live_execution_enabled: bool = False
    user_facing: bool = True
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "connector_id": self.connector_id,
            "ok": self.ok,
            "dry_run": self.dry_run,
            "status": self.status,
            "title": self.title,
            "message": self.message,
            "risk_tier": self.risk_tier,
            "permission_mode": self.permission_mode,
            "requires_approval": self.requires_approval,
            "external_write": self.external_write,
            "live_execution_enabled": self.live_execution_enabled,
            "user_facing": self.user_facing,
            "debug": dict(self.debug),
        }


class ConnectorDryRunRenderer:
    """
    Converts connector actions into user-facing dry-run previews.

    This is deliberately separate from live connector execution.
    It answers: "What would AION do?" without performing the action.
    """

    def __init__(self) -> None:
        self.registry = get_connector_registry()

    def render(
        self,
        action_id: str,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        approved: bool = False,
        live_execution_requested: bool = False,
    ) -> ConnectorDryRunPreview:
        action = self.registry.get_action(action_id)
        if action is None:
            return ConnectorDryRunPreview(
                action_id=str(action_id or ""),
                connector_id="unknown",
                ok=False,
                status="blocked_unknown_action",
                title="Unknown connector action",
                message="Blocked. This connector action is not registered in AION.",
                risk_tier="blocked",
                permission_mode="blocked",
                requires_approval=True,
                external_write=True,
                live_execution_enabled=False,
                debug={
                    "reason": "unknown_connector_action",
                    "inputs": dict(inputs or {}),
                },
            )

        connector_id = self._connector_id_for_action(action)

        message = self._message_for_action(
            action,
            approved=approved,
            live_execution_requested=live_execution_requested,
        )

        status = self._status_for_action(
            action,
            approved=approved,
            live_execution_requested=live_execution_requested,
        )

        return ConnectorDryRunPreview(
            action_id=action.action_id,
            connector_id=connector_id,
            ok=status not in {"blocked", "blocked_future_only", "blocked_unknown_action"},
            status=status,
            title=action.label,
            message=message,
            risk_tier=action.risk_tier,
            permission_mode=action.permission_mode,
            requires_approval=action.requires_approval,
            external_write=action.external_write,
            live_execution_enabled=action.live_execution_enabled,
            debug={
                "aliases": list(action.aliases),
                "requires_vault": list(action.requires_vault),
                "ui_group": action.ui_group,
                "dry_run_supported": action.dry_run_supported,
                "inputs": dict(inputs or {}),
                "approved": approved,
                "live_execution_requested": live_execution_requested,
            },
        )

    def _connector_id_for_action(self, action: ConnectorAction) -> str:
        for connector in self.registry.list_connectors():
            if any(item.action_id == action.action_id for item in connector.actions):
                return connector.connector_id
        return str(action.action_id).split(".", 1)[0] if "." in action.action_id else "unknown"

    def _status_for_action(
        self,
        action: ConnectorAction,
        *,
        approved: bool,
        live_execution_requested: bool,
    ) -> str:
        if action.permission_mode == "blocked":
            return "blocked"

        if action.permission_mode == "live_write_blocked":
            return "blocked_future_only"

        if action.requires_approval and not approved:
            return "waiting_for_approval"

        if action.external_write and approved:
            return "approved_connector_ready"

        return "previewed"

    def _message_for_action(
        self,
        action: ConnectorAction,
        *,
        approved: bool,
        live_execution_requested: bool,
    ) -> str:
        messages = {
            "gmail.watch_emails": "Would check Gmail for new matching messages.",
            "gmail.search_emails": "Would search Gmail using the configured query.",
            "gmail.get_email": "Would retrieve the selected Gmail email.",
            "gmail.list_attachments": "Would list attachments and media for the selected Gmail email.",
            "gmail.create_draft": (
                "Would create a Gmail draft after approval. No email is sent."
                if not approved
                else "Approved and ready to create a Gmail draft. No email will be sent automatically."
            ),
            "gmail.update_labels": (
                "Would update Gmail labels after approval."
                if not approved
                else "Approved and ready to update Gmail labels."
            ),
            "gmail.mark_read": (
                "Would mark the Gmail email as read after approval."
                if not approved
                else "Approved and ready to mark the Gmail email as read."
            ),
            "gmail.mark_unread": (
                "Would mark the Gmail email as unread after approval."
                if not approved
                else "Approved and ready to mark the Gmail email as unread."
            ),
            "gmail.copy_email": (
                "Would copy the Gmail email or draft after approval."
                if not approved
                else "Approved and ready to copy the Gmail email or draft."
            ),
            "gmail.move_email": (
                "Would move the Gmail email or draft after approval."
                if not approved
                else "Approved and ready to move the Gmail email or draft."
            ),
            "gmail.delete_email": "Blocked. Gmail delete is not enabled in this live-write phase.",
            "gmail.send_email": "Blocked. Live email sending is not enabled.",
            "gmail.reply_email": "Blocked. Live email replies are not enabled.",
            "gmail.send_draft": "Blocked. Sending drafts is not enabled.",
            "gmail.api_call": "Blocked. Custom Gmail API calls require explicit allowlist approval.",
            "http.request": "Would prepare an HTTP request preview. Live HTTP execution is not enabled.",
            "webhook.receive": "Would receive and validate a webhook trigger.",
            "make.trigger_scenario": "Would prepare a Make.com scenario trigger after approval. Live bridge execution is not enabled.",
            "zapier.trigger_zap": "Would prepare a Zapier Zap trigger after approval. Live bridge execution is not enabled.",
            "n8n.trigger_workflow": "Would prepare an n8n workflow trigger after approval. Live bridge execution is not enabled.",
            "automation_bridge.trigger_scenario": "Would prepare a legacy Make/Zapier/n8n bridge call. Prefer explicit Make.com, Zapier, or n8n actions. Live bridge execution is not enabled.",
        }

        return messages.get(
            action.action_id,
            f"Would preview connector action: {action.label}. No live execution is performed.",
        )


def render_connector_dry_run(
    action_id: str,
    *,
    inputs: Optional[Dict[str, Any]] = None,
    approved: bool = False,
    live_execution_requested: bool = False,
) -> Dict[str, Any]:
    return ConnectorDryRunRenderer().render(
        action_id,
        inputs=inputs,
        approved=approved,
        live_execution_requested=live_execution_requested,
    ).to_dict()
