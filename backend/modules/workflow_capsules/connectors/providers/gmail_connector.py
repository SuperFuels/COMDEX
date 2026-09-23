from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

from backend.modules.workflow_capsules.connectors.providers.gmail_local_node_bridge import (
    LocalNodeGmailClientBridge,
)
from backend.modules.workflow_capsules.connectors.contracts import (
    ConnectorCapability,
    ProviderConnectorResult,
)
from backend.modules.workflow_capsules.connectors.vault.connector_vault_resolver import (
    ConnectorVaultResolver,
)


GMAIL_VAULT_HANDLE = "vault.gmail.credentials"
LIVE_GMAIL_ENV_GUARD = "AION_WORKFLOW_GMAIL_ALLOW_LIVE_SEND"


class GmailWorkflowConnector:
    """
    Gmail provider connector for Workflow Capsules.

    Current status:
      - real Gmail API calls are not implemented here yet
      - read/draft/send remain guard-first provider operations
      - live send stays blocked until a real Gmail client is integrated
    """

    connector = "gmail"

    def __init__(
        self,
        *,
        vault_resolver: Optional[ConnectorVaultResolver] = None,
        gmail_client: Optional[LocalNodeGmailClientBridge] = None,
    ) -> None:
        self.vault_resolver = vault_resolver or ConnectorVaultResolver()
        self.gmail_client = gmail_client

    def capabilities(self) -> List[ConnectorCapability]:
        return [
            ConnectorCapability(
                connector="gmail",
                action="read_message",
                live_supported=True,
                requires_vault=[GMAIL_VAULT_HANDLE],
            ),
            ConnectorCapability(
                connector="gmail",
                action="create_draft",
                live_supported=True,
                requires_vault=[GMAIL_VAULT_HANDLE],
                requires_approval=True,
            ),
            ConnectorCapability(
                connector="gmail",
                action="send_message",
                live_supported=False,
                requires_vault=[GMAIL_VAULT_HANDLE],
                requires_approval=True,
                env_guards=[LIVE_GMAIL_ENV_GUARD],
            ),
        ]

    def read_message(
        self,
        *,
        message_id: str,
        available_vault_requirements: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        live: bool = False,
    ) -> ProviderConnectorResult:
        vault = self.vault_resolver.resolve(
            vault_handle=GMAIL_VAULT_HANDLE,
            available_vault_requirements=available_vault_requirements,
            workspace_id=workspace_id,
            connector="gmail",
        )

        if not vault.ok:
            return ProviderConnectorResult(
                ok=False,
                connector="gmail",
                action="read_message",
                status=vault.status,
                errors=list(vault.errors),
            )

        if live:
            if self.gmail_client is None:
                return ProviderConnectorResult(
                    ok=False,
                    connector="gmail",
                    action="read_message",
                    status="blocked_live_read_client_missing",
                    errors=["gmail_live_read_client_missing"],
                    payload={
                        "message_id": message_id,
                        "vault": vault.to_dict(),
                    },
                )

            query = f"rfc822msgid:{message_id}" if message_id else "in:inbox is:unread"
            bridge_result = self.gmail_client.read_messages(
                query=query,
                max_results=1,
            ).to_dict()

            return ProviderConnectorResult(
                ok=bool(bridge_result.get("ok")),
                connector="gmail",
                action="read_message",
                status=str(bridge_result.get("status") or "gmail_read_result"),
                payload={
                    "message_id": message_id,
                    "vault": vault.to_dict(),
                    "bridge_result": bridge_result,
                },
                errors=list(bridge_result.get("errors") or []),
                warnings=list(bridge_result.get("warnings") or []),
            )

        return ProviderConnectorResult(
            ok=True,
            connector="gmail",
            action="read_message",
            status="simulated_read",
            payload={
                "gmail_message_id": message_id,
                "subject": "Simulated Gmail enquiry",
                "from": "customer@example.com",
                "body": "Simulated enquiry body for workflow capsule provider.",
                "vault": vault.to_dict(),
            },
        )

    def create_draft(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        available_vault_requirements: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        live: bool = False,
    ) -> ProviderConnectorResult:
        vault = self.vault_resolver.resolve(
            vault_handle=GMAIL_VAULT_HANDLE,
            available_vault_requirements=available_vault_requirements,
            workspace_id=workspace_id,
            connector="gmail",
        )

        if not vault.ok:
            return ProviderConnectorResult(
                ok=False,
                connector="gmail",
                action="create_draft",
                status=vault.status,
                errors=list(vault.errors),
            )

        if live:
            if self.gmail_client is None:
                return ProviderConnectorResult(
                    ok=False,
                    connector="gmail",
                    action="create_draft",
                    status="blocked_live_draft_client_missing",
                    errors=["gmail_live_draft_client_missing"],
                    payload={"vault": vault.to_dict()},
                )

            bridge_result = self.gmail_client.create_draft(
                to=to,
                subject=subject,
                body=body,
            ).to_dict()

            payload = {
                "vault": vault.to_dict(),
                "bridge_result": bridge_result,
                "sent": False,
                "must_not_send": True,
            }

            return ProviderConnectorResult(
                ok=bool(bridge_result.get("ok")),
                connector="gmail",
                action="create_draft",
                status=str(bridge_result.get("status") or "gmail_draft_result"),
                payload=payload,
                errors=list(bridge_result.get("errors") or []),
                warnings=list(bridge_result.get("warnings") or []),
            )

        return ProviderConnectorResult(
            ok=True,
            connector="gmail",
            action="create_draft",
            status="simulated_draft_only",
            payload={
                "to": to,
                "subject": subject,
                "body": body,
                "must_not_send": True,
                "sent": False,
                "vault": vault.to_dict(),
            },
        )

    def send_message(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        approval: Dict[str, Any],
        available_vault_requirements: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        live: bool = False,
    ) -> ProviderConnectorResult:
        vault = self.vault_resolver.resolve(
            vault_handle=GMAIL_VAULT_HANDLE,
            available_vault_requirements=available_vault_requirements,
            workspace_id=workspace_id,
            connector="gmail",
        )

        if not vault.ok:
            return ProviderConnectorResult(
                ok=False,
                connector="gmail",
                action="send_message",
                status=vault.status,
                errors=list(vault.errors),
            )

        if approval.get("status") != "approved":
            return ProviderConnectorResult(
                ok=False,
                connector="gmail",
                action="send_message",
                status="blocked_missing_approval",
                errors=["approval_not_approved"],
            )

        if not live:
            return ProviderConnectorResult(
                ok=True,
                connector="gmail",
                action="send_message",
                status="simulated_external_write_ready",
                payload={
                    "ready": True,
                    "external_write": "gmail.send",
                    "must_not_send": True,
                    "vault": vault.to_dict(),
                },
            )

        if os.getenv(LIVE_GMAIL_ENV_GUARD) != "1":
            return ProviderConnectorResult(
                ok=False,
                connector="gmail",
                action="send_message",
                status="blocked_live_env_guard",
                errors=[f"missing_env_guard:{LIVE_GMAIL_ENV_GUARD}=1"],
            )

        return ProviderConnectorResult(
            ok=False,
            connector="gmail",
            action="send_message",
            status="blocked_live_connector_not_implemented",
            errors=["gmail_live_send_not_implemented"],
            payload={
                "message": "Live Gmail send guard passed, but real Gmail send is not implemented yet.",
                "vault": vault.to_dict(),
            },
        )
