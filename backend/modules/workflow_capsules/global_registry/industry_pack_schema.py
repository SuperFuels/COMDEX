from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


INDUSTRY_PACK_SCHEMA_VERSION = "aion.global_workflow_industry_pack.v1"

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
class GlobalWorkflowPattern:
    """
    Reusable global workflow pattern.

    This is not bound to one business.
    It may declare required connectors and vault handles, but MUST NOT store credentials.
    """

    pattern_key: str
    display_name: str
    industry: str
    meaning: str

    workflow_canonical_key: str
    display_glyph: Optional[str] = None

    required_connectors: List[str] = field(default_factory=list)
    required_vault_handles: List[str] = field(default_factory=list)
    local_binding_slots: List[str] = field(default_factory=list)

    template: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        meta = data.setdefault("meta", {})
        meta.setdefault("schema_version", "aion.global_workflow_pattern.v1")
        meta.setdefault("created_at", _utc_now_iso())
        meta.setdefault("version", "1.0")
        return data

    def validate(self) -> None:
        data = self.to_dict()

        if _contains_secret_field(data):
            raise ValueError("global_workflow_pattern_must_not_contain_secret_fields")

        if not str(self.pattern_key or "").startswith("global.workflow."):
            raise ValueError("pattern_key_must_start_with_global.workflow")

        if not str(self.workflow_canonical_key or "").startswith("workflow:"):
            raise ValueError("workflow_canonical_key_must_start_with_workflow_prefix")

        for handle in self.required_vault_handles:
            if not str(handle or "").startswith("vault."):
                raise ValueError(f"invalid_vault_handle:{handle}")

    def finalize(self) -> "GlobalWorkflowPattern":
        self.validate()
        meta = self.meta
        meta.setdefault("schema_version", "aion.global_workflow_pattern.v1")
        meta.setdefault("created_at", _utc_now_iso())
        meta.setdefault("version", "1.0")
        stable = self.to_dict()
        stable_meta = dict(stable.get("meta") or {})
        stable_meta.pop("checksum", None)
        stable["meta"] = stable_meta
        meta["checksum"] = _stable_hash(stable)
        return self


@dataclass
class IndustryWorkflowPack:
    """
    Global reusable industry pack.

    Example:
      Electrician pack
        -> receptionist workflow
        -> quote workflow
        -> invoice workflow
        -> Xero reconciliation workflow

    The pack is global pattern memory only.
    Local businesses bind connector accounts/vault handles separately.
    """

    pack_key: str
    industry: str
    display_name: str
    meaning: str

    patterns: List[GlobalWorkflowPattern] = field(default_factory=list)
    required_connectors: List[str] = field(default_factory=list)
    required_vault_handles: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["patterns"] = [pattern.to_dict() for pattern in self.patterns]
        meta = data.setdefault("meta", {})
        meta.setdefault("schema_version", INDUSTRY_PACK_SCHEMA_VERSION)
        meta.setdefault("created_at", _utc_now_iso())
        meta.setdefault("version", "1.0")
        return data

    def validate(self) -> None:
        data = self.to_dict()

        if _contains_secret_field(data):
            raise ValueError("industry_pack_must_not_contain_secret_fields")

        if not str(self.pack_key or "").startswith("industry."):
            raise ValueError("pack_key_must_start_with_industry")

        for pattern in self.patterns:
            pattern.validate()

        for handle in self.required_vault_handles:
            if not str(handle or "").startswith("vault."):
                raise ValueError(f"invalid_vault_handle:{handle}")

    def finalize(self) -> "IndustryWorkflowPack":
        self.validate()

        for pattern in self.patterns:
            pattern.finalize()

        self.meta.setdefault("schema_version", INDUSTRY_PACK_SCHEMA_VERSION)
        self.meta.setdefault("created_at", _utc_now_iso())
        self.meta.setdefault("version", "1.0")

        stable = self.to_dict()
        stable_meta = dict(stable.get("meta") or {})
        stable_meta.pop("checksum", None)
        stable["meta"] = stable_meta
        self.meta["checksum"] = _stable_hash(stable)
        return self


def make_electrician_gmail_pack() -> IndustryWorkflowPack:
    receptionist = GlobalWorkflowPattern(
        pattern_key="global.workflow.electrician.gmail_receptionist.v1",
        display_name="Electrician Gmail Receptionist",
        industry="electrician",
        meaning=(
            "Reusable electrician workflow pattern for reading customer Gmail enquiries, "
            "drafting replies, and stopping for human approval."
        ),
        workflow_canonical_key="workflow:electrician.gmail_receptionist.v1",
        display_glyph="EL-001",
        required_connectors=["gmail"],
        required_vault_handles=["vault.gmail.credentials"],
        local_binding_slots=[
            "workspace_id",
            "business_profile",
            "gmail_account",
            "reply_tone",
            "service_area",
        ],
        template={
            "steps": [
                {
                    "id": "read",
                    "kind": "read_email",
                    "connector": "gmail",
                    "requires": ["vault.gmail.credentials"],
                    "output_ref": "read",
                },
                {
                    "id": "draft",
                    "kind": "draft_content",
                    "purpose": "customer_reply",
                    "input_refs": ["read"],
                    "output_ref": "draft",
                },
                {
                    "id": "approval",
                    "kind": "approval_checkpoint",
                    "reason": "Human approval required before customer contact.",
                    "input_refs": ["draft"],
                    "output_ref": "approval",
                    "requires_approval": True,
                },
                {
                    "id": "send",
                    "kind": "send_email",
                    "connector": "gmail",
                    "input_refs": ["approval"],
                    "requires": ["vault.gmail.credentials"],
                    "requires_approval": True,
                    "external_write": True,
                    "guard": {
                        "requires_approval_ref": "approval",
                        "reason": "Final Gmail send must only resume after approval.",
                    },
                    "approval": {
                        "reason": "Send drafted Gmail reply to customer.",
                    },
                    "output_ref": "send",
                },
            ],
            "external_writes_allowed": False,
            "dry_run_first": True,
        },
        tags=["electrician", "gmail", "receptionist", "enquiry", "approval"],
    )

    pack = IndustryWorkflowPack(
        pack_key="industry.electrician.core.v1",
        industry="electrician",
        display_name="Electrician Core Workflow Pack",
        meaning=(
            "Reusable global workflow pack for an electrician business. "
            "The global pack stores patterns only; each business binds its own connectors and vault handles locally."
        ),
        patterns=[receptionist],
        required_connectors=["gmail"],
        required_vault_handles=["vault.gmail.credentials"],
        tags=["electrician", "trade", "gmail", "quotes", "receptionist"],
    )

    return pack.finalize()
