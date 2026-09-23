from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional


VaultCredentialType = Literal[
    "oauth_token",
    "api_key",
    "webhook_secret",
    "basic_auth",
    "service_account",
]

VaultCredentialStatus = Literal[
    "connected",
    "missing",
    "expired",
    "revoked",
    "error",
]

CredentialVisibility = Literal[
    "owner_only",
    "department",
    "workspace_admin",
    "business_admin",
    "senior_management",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class CredentialScope:
    business_id: str
    workspace_id: str
    owner_user_id: str
    department_id: Optional[str] = None
    function_id: Optional[str] = None
    role_id: Optional[str] = None
    visibility: CredentialVisibility = "owner_only"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VaultCredential:
    """
    Metadata envelope for connector credentials.

    Secret values are NOT stored in this object. The actual secret/token must live
    behind `secret_ref` in the platform secret store / encrypted vault backend.
    """

    credential_id: str
    connector_id: str
    credential_key: str
    credential_type: VaultCredentialType
    scope: CredentialScope
    status: VaultCredentialStatus = "missing"
    secret_ref: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    live_send_enabled: bool = False
    live_write_enabled: bool = False
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_tested_at: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_connected(self) -> bool:
        return self.status == "connected" and bool(self.secret_ref)

    def requires_reconnect(self) -> bool:
        return self.status in {"missing", "expired", "revoked", "error"} or not self.secret_ref

    def safe_public_dict(self) -> Dict[str, Any]:
        """
        User/UI-safe representation.

        Never include secret values. Only expose whether a secret reference exists.
        """
        return {
            "credential_id": self.credential_id,
            "connector_id": self.connector_id,
            "credential_key": self.credential_key,
            "credential_type": self.credential_type,
            "scope": self.scope.to_dict(),
            "status": self.status,
            "connected": self.is_connected(),
            "has_secret_ref": bool(self.secret_ref),
            "scopes": list(self.scopes),
            "live_send_enabled": bool(self.live_send_enabled),
            "live_write_enabled": bool(self.live_write_enabled),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_tested_at": self.last_tested_at,
            "expires_at": self.expires_at,
            "metadata": dict(self.metadata),
        }

    def to_private_record(self) -> Dict[str, Any]:
        """
        Internal vault record.

        This still stores only secret_ref, never raw tokens/passwords.
        """
        data = self.safe_public_dict()
        data["secret_ref"] = self.secret_ref
        return data


def gmail_oauth_credential(
    *,
    business_id: str,
    workspace_id: str,
    owner_user_id: str,
    department_id: Optional[str] = None,
    secret_ref: Optional[str] = None,
    status: VaultCredentialStatus = "missing",
) -> VaultCredential:
    return VaultCredential(
        credential_id=f"cred_gmail_{business_id}_{owner_user_id}".replace(" ", "_"),
        connector_id="gmail",
        credential_key="vault.gmail.credentials",
        credential_type="oauth_token",
        scope=CredentialScope(
            business_id=business_id,
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            department_id=department_id,
            visibility="owner_only",
        ),
        status=status,
        secret_ref=secret_ref,
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
        ],
        live_send_enabled=False,
        live_write_enabled=False,
    )
