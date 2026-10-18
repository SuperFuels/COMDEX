from __future__ import annotations

from typing import Dict, List, Optional

from backend.modules.vault.credential_schema import VaultCredential


class InMemoryVaultCredentialStore:
    """
    Minimal local/dev credential metadata store.

    This stores credential metadata only. It must never store raw OAuth tokens,
    passwords, refresh tokens, API keys, or secrets.
    """

    def __init__(self) -> None:
        self._records: Dict[str, VaultCredential] = {}

    def upsert(self, credential: VaultCredential) -> VaultCredential:
        self._records[credential.credential_id] = credential
        return credential

    def get(self, credential_id: str) -> Optional[VaultCredential]:
        return self._records.get(credential_id)

    def list_for_workspace(self, *, business_id: str, workspace_id: str) -> List[VaultCredential]:
        return [
            credential
            for credential in self._records.values()
            if credential.scope.business_id == business_id
            and credential.scope.workspace_id == workspace_id
        ]

    def find_connector_credential(
        self,
        *,
        business_id: str,
        workspace_id: str,
        owner_user_id: str,
        connector_id: str,
        credential_key: str,
    ) -> Optional[VaultCredential]:
        for credential in self._records.values():
            if (
                credential.scope.business_id == business_id
                and credential.scope.workspace_id == workspace_id
                and credential.scope.owner_user_id == owner_user_id
                and credential.connector_id == connector_id
                and credential.credential_key == credential_key
            ):
                return credential

        return None

    def has_connected_credential(
        self,
        *,
        business_id: str,
        workspace_id: str,
        owner_user_id: str,
        connector_id: str,
        credential_key: str,
    ) -> bool:
        credential = self.find_connector_credential(
            business_id=business_id,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            connector_id=connector_id,
            credential_key=credential_key,
        )
        return bool(credential and credential.is_connected())
