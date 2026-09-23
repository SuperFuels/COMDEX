from __future__ import annotations

"""
Connector Vault Resolver - AION Workflow Capsules v1
────────────────────────────────────────────────────

This module is the workflow-connector-facing vault access layer.

Important architecture rule:
  This is NOT a new credential vault.

It is a thin resolver/bridge that sits between workflow connector providers
(Gmail, Xero, HubSpot, WhatsApp, etc.) and the existing Tessaris/GlyphVault
security substrate.

Intended lower security layers:
  - GlyphVault / VaultManager
  - SessionKeyVault / SessionKeyManager
  - symbolic encryption / symbolic key derivation
  - QKD-backed key/session channels where available
  - Vault audit logging
  - SoulLaw / policy validation
  - local node connector registry for OAuth/token payloads where applicable

Workflow capsules must only declare vault handles such as:

  vault.gmail.credentials
  vault.xero.credentials
  vault.hubspot.credentials

They must never store raw credentials, tokens, passwords, refresh tokens,
client secrets, or decrypted connector payloads.

Provider connectors should request access like:

  resolve(vault_handle="vault.gmail.credentials", ...)

and should receive either:
  - a blocked result,
  - a credential reference,
  - or a runtime client/object in future live implementations.

Raw secrets must not be written to traces, approvals, capsules, habits,
registry files, canvas workflow definitions, or compiled glyph bodies.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ConnectorVaultResolution:
    ok: bool
    vault_handle: str
    status: str

    credential_ref: Optional[str] = None
    client: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    schema_version: str = "aion.workflow_connector_vault_resolution.v1"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)

        # Never serialize runtime clients or secret-bearing objects.
        if self.client is not None:
            data["client"] = "<runtime_client>"

        return data


class ConnectorVaultResolver:
    """
    Standard resolver for connector vault handles.

    Current MVP behaviour:
      - checks that the declared vault handle is available to the workflow runtime,
      - returns a reference-only resolution,
      - does not expose raw credentials,
      - records enough metadata for traceability without leaking secrets.

    Future live behaviour:
      - call existing GlyphVault/VaultManager/session-key vault,
      - apply symbolic key derivation/QKD/session unlock if configured,
      - apply SoulLaw/policy checks,
      - record vault audit event,
      - return a safe runtime connector client or reference.
    """

    def resolve(
        self,
        *,
        vault_handle: str,
        available_vault_requirements: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        business_id: Optional[str] = None,
        connector: Optional[str] = None,
        purpose: Optional[str] = None,
        require_live_client: bool = False,
    ) -> ConnectorVaultResolution:
        available = set(available_vault_requirements or [])
        handle = str(vault_handle or "").strip()
        connector_name = str(connector or "").strip() or None

        if not handle:
            return ConnectorVaultResolution(
                ok=False,
                vault_handle="",
                status="missing_vault_handle",
                errors=["missing_vault_handle"],
                metadata={
                    "workspace_id": workspace_id,
                    "business_id": business_id,
                    "connector": connector_name,
                    "purpose": purpose,
                },
            )

        if handle not in available:
            return ConnectorVaultResolution(
                ok=False,
                vault_handle=handle,
                status="blocked_missing_vault",
                errors=[f"missing_vault_requirement:{handle}"],
                metadata={
                    "workspace_id": workspace_id,
                    "business_id": business_id,
                    "connector": connector_name,
                    "purpose": purpose,
                    "secret_material_exposed": False,
                },
            )

        if require_live_client:
            return ConnectorVaultResolution(
                ok=False,
                vault_handle=handle,
                status="blocked_live_vault_client_not_implemented",
                credential_ref=handle,
                errors=["live_vault_client_resolution_not_implemented"],
                warnings=[
                    "ConnectorVaultResolver is currently reference-only; live client binding must bridge to existing GlyphVault/session/QKD stack."
                ],
                metadata={
                    "workspace_id": workspace_id,
                    "business_id": business_id,
                    "connector": connector_name,
                    "purpose": purpose,
                    "secret_material_exposed": False,
                    "intended_security_stack": [
                        "GlyphVault",
                        "VaultManager",
                        "SessionKeyVault",
                        "SessionKeyManager",
                        "symbolic_key_deriver",
                        "QKD",
                        "VaultAudit",
                        "SoulLaw",
                    ],
                },
            )

        return ConnectorVaultResolution(
            ok=True,
            vault_handle=handle,
            status="resolved_reference_only",
            credential_ref=handle,
            metadata={
                "workspace_id": workspace_id,
                "business_id": business_id,
                "connector": connector_name,
                "purpose": purpose,
                "secret_material_exposed": False,
                "note": "MVP resolver proves vault handle availability only; raw credentials are not exposed.",
                "intended_security_stack": [
                    "GlyphVault",
                    "VaultManager",
                    "SessionKeyVault",
                    "SessionKeyManager",
                    "symbolic_key_deriver",
                    "QKD",
                    "VaultAudit",
                    "SoulLaw",
                ],
            },
        )
