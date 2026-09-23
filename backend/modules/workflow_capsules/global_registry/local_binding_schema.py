from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


LOCAL_BINDING_SCHEMA_VERSION = "aion.local_workflow_binding.v1"

_SECRET_FIELD_NAMES = {
    "password",
    "secret",
    "client_secret",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "token",
    "api_key",
    "private_key",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha3_256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key or "").strip().lower()
            if normalized in _SECRET_FIELD_NAMES:
                return True
            if _contains_secret_field(item):
                return True

    if isinstance(value, list):
        return any(_contains_secret_field(item) for item in value)

    return False


@dataclass
class LocalWorkflowBinding:
    """
    Local business binding for a global workflow pattern.

    This maps global reusable pattern identity to a local workspace/business context.
    It may reference vault handles, but never stores raw credentials.
    """

    binding_key: str
    workspace_id: str
    business_id: str
    pattern_key: str
    workflow_canonical_key: str

    connector_bindings: Dict[str, str] = field(default_factory=dict)
    vault_bindings: Dict[str, str] = field(default_factory=dict)
    business_context: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        meta = data.setdefault("meta", {})
        meta.setdefault("schema_version", LOCAL_BINDING_SCHEMA_VERSION)
        meta.setdefault("created_at", _utc_now_iso())
        meta.setdefault("version", "1.0")
        return data

    def validate(self) -> None:
        data = self.to_dict()

        if _contains_secret_field(data):
            raise ValueError("local_workflow_binding_must_not_contain_secret_fields")

        if not str(self.binding_key or "").startswith("binding."):
            raise ValueError("binding_key_must_start_with_binding")

        if not str(self.pattern_key or "").startswith("global.workflow."):
            raise ValueError("pattern_key_must_start_with_global.workflow")

        if not str(self.workflow_canonical_key or "").startswith("workflow:"):
            raise ValueError("workflow_canonical_key_must_start_with_workflow_prefix")

        for logical_name, handle in self.vault_bindings.items():
            if not str(handle or "").startswith("vault."):
                raise ValueError(f"invalid_vault_binding:{logical_name}:{handle}")

    def finalize(self) -> "LocalWorkflowBinding":
        self.validate()
        self.meta.setdefault("schema_version", LOCAL_BINDING_SCHEMA_VERSION)
        self.meta.setdefault("created_at", _utc_now_iso())
        self.meta.setdefault("version", "1.0")

        stable = self.to_dict()
        stable_meta = dict(stable.get("meta") or {})
        stable_meta.pop("checksum", None)
        stable["meta"] = stable_meta
        self.meta["checksum"] = _stable_hash(stable)
        return self


def make_electrician_gmail_local_binding(
    *,
    workspace_id: str,
    business_id: str,
    gmail_connector_id: str = "connector.gmail.default",
) -> LocalWorkflowBinding:
    return LocalWorkflowBinding(
        binding_key=f"binding.{workspace_id}.electrician.gmail_receptionist.v1",
        workspace_id=workspace_id,
        business_id=business_id,
        pattern_key="global.workflow.electrician.gmail_receptionist.v1",
        workflow_canonical_key="workflow:electrician.gmail_receptionist.v1",
        connector_bindings={
            "gmail": gmail_connector_id,
        },
        vault_bindings={
            "gmail_credentials": "vault.gmail.credentials",
        },
        business_context={
            "industry": "electrician",
            "setup_mode": "local_business_binding",
        },
        enabled=False,
    ).finalize()
