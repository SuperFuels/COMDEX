from __future__ import annotations

from backend.modules.workflow_capsules.connectors.providers.gmail_connector import (
    GMAIL_VAULT_HANDLE,
    LIVE_GMAIL_ENV_GUARD,
    GmailWorkflowConnector,
)
from backend.modules.workflow_capsules.connectors.vault.connector_vault_resolver import (
    ConnectorVaultResolver,
)


def test_connector_vault_resolver_never_exposes_raw_credentials() -> None:
    resolver = ConnectorVaultResolver()

    blocked = resolver.resolve(
        vault_handle=GMAIL_VAULT_HANDLE,
        available_vault_requirements=[],
        workspace_id="pytest-workspace",
        connector="gmail",
    )

    assert blocked.ok is False
    assert blocked.status == "blocked_missing_vault"
    assert blocked.errors == [f"missing_vault_requirement:{GMAIL_VAULT_HANDLE}"]

    resolved = resolver.resolve(
        vault_handle=GMAIL_VAULT_HANDLE,
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        workspace_id="pytest-workspace",
        connector="gmail",
    )

    data = resolved.to_dict()

    assert resolved.ok is True
    assert resolved.status == "resolved_reference_only"
    assert resolved.credential_ref == GMAIL_VAULT_HANDLE
    assert data["metadata"]["secret_material_exposed"] is False
    assert "password" not in data
    assert "token" not in data
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "client_secret" not in data


def test_gmail_provider_exposes_expected_capabilities() -> None:
    connector = GmailWorkflowConnector()

    caps = [c.to_dict() for c in connector.capabilities()]
    actions = {c["action"] for c in caps}

    assert actions == {"read_message", "create_draft", "send_message"}

    send_cap = next(c for c in caps if c["action"] == "send_message")
    assert send_cap["requires_vault"] == [GMAIL_VAULT_HANDLE]
    assert send_cap["requires_approval"] is True
    assert send_cap["env_guards"] == [LIVE_GMAIL_ENV_GUARD]
    assert send_cap["live_supported"] is False


def test_gmail_provider_simulated_read_and_draft_require_vault_handle() -> None:
    connector = GmailWorkflowConnector()

    read_blocked = connector.read_message(
        message_id="msg-001",
        available_vault_requirements=[],
    )

    assert read_blocked.ok is False
    assert read_blocked.status == "blocked_missing_vault"

    read_ready = connector.read_message(
        message_id="msg-001",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
    )

    assert read_ready.ok is True
    assert read_ready.status == "simulated_read"
    assert read_ready.payload["gmail_message_id"] == "msg-001"

    draft_ready = connector.create_draft(
        to="customer@example.com",
        subject="Re: Enquiry",
        body="Draft body",
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
    )

    assert draft_ready.ok is True
    assert draft_ready.status == "simulated_draft_only"
    assert draft_ready.payload["must_not_send"] is True


def test_gmail_provider_live_send_stays_blocked_even_after_vault_and_approval(monkeypatch) -> None:
    monkeypatch.setenv(LIVE_GMAIL_ENV_GUARD, "1")

    connector = GmailWorkflowConnector()

    result = connector.send_message(
        to="customer@example.com",
        subject="Re: Enquiry",
        body="Body",
        approval={"status": "approved"},
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        live=True,
    )

    assert result.ok is False
    assert result.status == "blocked_live_connector_not_implemented"
    assert "gmail_live_send_not_implemented" in result.errors

def test_connector_vault_resolver_live_client_is_blocked_until_glyphvault_bridge_exists() -> None:
    resolver = ConnectorVaultResolver()

    result = resolver.resolve(
        vault_handle=GMAIL_VAULT_HANDLE,
        available_vault_requirements=[GMAIL_VAULT_HANDLE],
        workspace_id="pytest-workspace",
        business_id="pytest-business",
        connector="gmail",
        purpose="gmail_live_read",
        require_live_client=True,
    )

    data = result.to_dict()

    assert result.ok is False
    assert result.status == "blocked_live_vault_client_not_implemented"
    assert result.credential_ref == GMAIL_VAULT_HANDLE
    assert "live_vault_client_resolution_not_implemented" in result.errors
    assert data["metadata"]["secret_material_exposed"] is False
    assert "GlyphVault" in data["metadata"]["intended_security_stack"]
    assert "symbolic_key_deriver" in data["metadata"]["intended_security_stack"]
    assert "QKD" in data["metadata"]["intended_security_stack"]
    assert "SoulLaw" in data["metadata"]["intended_security_stack"]

