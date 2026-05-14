from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from backend.modules.vault.credential_store import InMemoryVaultCredentialStore


@dataclass(frozen=True, slots=True)
class ConnectorReadinessResult:
    ok: bool
    connector_id: str
    credential_key: str
    status: str
    ready: bool
    reason: str
    required_scopes: List[str]
    granted_scopes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConnectorReadinessService:
    """
    Checks whether a connector has usable Vault credentials for a given
    business/workspace/user context.

    This service does not execute connectors and does not read raw secrets.
    """

    def __init__(self, store: InMemoryVaultCredentialStore) -> None:
        self.store = store

    def check(
        self,
        *,
        business_id: str,
        workspace_id: str,
        owner_user_id: str,
        connector_id: str,
        credential_key: str,
        required_scopes: Optional[List[str]] = None,
    ) -> ConnectorReadinessResult:
        required = list(required_scopes or [])

        credential = self.store.find_connector_credential(
            business_id=business_id,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            connector_id=connector_id,
            credential_key=credential_key,
        )

        if credential is None:
            return ConnectorReadinessResult(
                ok=False,
                connector_id=connector_id,
                credential_key=credential_key,
                status="missing",
                ready=False,
                reason="credential_missing",
                required_scopes=required,
                granted_scopes=[],
            )

        granted = list(credential.scopes)

        if not credential.is_connected():
            return ConnectorReadinessResult(
                ok=False,
                connector_id=connector_id,
                credential_key=credential_key,
                status=credential.status,
                ready=False,
                reason="credential_not_connected",
                required_scopes=required,
                granted_scopes=granted,
            )

        missing_scopes = [scope for scope in required if scope not in granted]
        if missing_scopes:
            return ConnectorReadinessResult(
                ok=False,
                connector_id=connector_id,
                credential_key=credential_key,
                status=credential.status,
                ready=False,
                reason="missing_required_scopes",
                required_scopes=required,
                granted_scopes=granted,
            )

        return ConnectorReadinessResult(
            ok=True,
            connector_id=connector_id,
            credential_key=credential_key,
            status=credential.status,
            ready=True,
            reason="connector_ready",
            required_scopes=required,
            granted_scopes=granted,
        )
