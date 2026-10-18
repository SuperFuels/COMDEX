from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import json
import re


SCHEMA_VERSION = "aion.workflow_glyph_store.v1"
DEFAULT_SIGNER = "Tessaris-Core"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha3_256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.:-]+", ".", str(value or "").strip()).strip(".")
    return slug or "workflow_glyph.untitled"


def _clean_code(value: str) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9-]+", "-", text).strip("-")
    return text or "WD-0000"


def stable_glyph_code(seed: str, *, prefix: str = "WD") -> str:
    clean_prefix = re.sub(r"[^A-Z0-9]+", "", str(prefix or "WD").upper())[:4] or "WD"
    digest = hashlib.sha3_256(str(seed or "").encode("utf-8")).hexdigest()
    number = int(digest[:8], 16) % 10000
    return f"{clean_prefix}-{number:04d}"


@dataclass
class WorkflowGlyph:
    """
    Canonical reusable Workflow Glyph contract.

    A WorkflowGlyph is a stable, shareable, versioned wrapper around a compiled
    workflow runtime plan. It is the backend contract behind the Master Glyph
    Library / marketplace surface.
    """

    glyph_id: str
    glyph_code: str
    name: str

    workflow_id: str
    workflow_version: str = "v1"
    glyph_version: str = "v1"

    scope: str = "my"  # my | universal
    callable: bool = False

    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    required_connectors: List[str] = field(default_factory=list)

    risk_tier: str = "low"
    approval_policy: Dict[str, Any] = field(default_factory=dict)
    runtime_plan: Dict[str, Any] = field(default_factory=dict)

    tags: List[str] = field(default_factory=list)
    description: str = ""
    source_glyph_code: Optional[str] = None

    meta: Dict[str, Any] = field(default_factory=dict)

    def normalised(self) -> "WorkflowGlyph":
        self.glyph_id = _safe_slug(self.glyph_id)
        self.glyph_code = _clean_code(self.glyph_code)
        self.workflow_id = _safe_slug(self.workflow_id)
        self.workflow_version = str(self.workflow_version or "v1")
        self.glyph_version = str(self.glyph_version or "v1")
        self.scope = "universal" if str(self.scope).lower() == "universal" else "my"
        self.risk_tier = str(self.risk_tier or "low").lower()
        self.required_connectors = [str(x) for x in list(self.required_connectors or []) if str(x).strip()]
        self.tags = sorted(set(str(x).lower() for x in list(self.tags or []) if str(x).strip()))
        self.callable = bool(self.callable)
        return self

    def stable_dict(self) -> Dict[str, Any]:
        """
        Hash-safe canonical payload.

        Important:
          - MUST NOT call to_dict(), checksum(), or version_hash().
          - Those methods depend on this one.
          - Keep volatile/generated fields out of the stable hash.
        """
        self.normalised()
        data = asdict(self)

        meta = dict(data.get("meta") or {})
        meta.pop("checksum", None)
        meta.pop("version_hash", None)
        meta.pop("updated_at", None)
        data["meta"] = meta

        data.pop("version_hash", None)
        return data

    def checksum(self) -> str:
        return _stable_hash(self.stable_dict())

    def version_hash(self) -> str:
        return self.checksum()[:16]

    def to_dict(self) -> Dict[str, Any]:
        self.normalised()
        data = asdict(self)
        meta = data.setdefault("meta", {})
        meta.setdefault("schema_version", SCHEMA_VERSION)
        meta.setdefault("signed_by", DEFAULT_SIGNER)
        meta.setdefault("created_at", _utc_now_iso())
        meta.setdefault("updated_at", _utc_now_iso())
        meta.setdefault("version", self.glyph_version)

        checksum = meta.get("checksum") or self.checksum()
        version_hash = meta.get("version_hash") or checksum[:16]

        meta["checksum"] = checksum
        meta["version_hash"] = version_hash
        data["version_hash"] = version_hash
        return data

    def finalize(self) -> "WorkflowGlyph":
        self.normalised()
        self.meta.setdefault("schema_version", SCHEMA_VERSION)
        self.meta.setdefault("signed_by", DEFAULT_SIGNER)
        self.meta.setdefault("created_at", _utc_now_iso())
        self.meta["updated_at"] = _utc_now_iso()
        self.meta.setdefault("version", self.glyph_version)

        checksum = self.checksum()
        self.meta["checksum"] = checksum
        self.meta["version_hash"] = checksum[:16]
        return self

    def save(self, path: str | Path) -> Path:
        self.finalize()
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowGlyph":
        glyph = cls(
            glyph_id=str(data.get("glyph_id") or data.get("id") or ""),
            glyph_code=str(data.get("glyph_code") or data.get("code") or ""),
            name=str(data.get("name") or data.get("display_name") or "Untitled workflow glyph"),
            workflow_id=str(data.get("workflow_id") or ""),
            workflow_version=str(data.get("workflow_version") or "v1"),
            glyph_version=str(data.get("glyph_version") or data.get("version") or "v1"),
            scope=str(data.get("scope") or data.get("glyph_scope") or "my"),
            callable=bool(data.get("callable") is True),
            input_schema=dict(data.get("input_schema") or data.get("inputs_schema") or {}),
            output_schema=dict(data.get("output_schema") or data.get("outputs_schema") or {}),
            required_connectors=list(data.get("required_connectors") or data.get("connectors") or []),
            risk_tier=str(data.get("risk_tier") or "low"),
            approval_policy=dict(data.get("approval_policy") or {}),
            runtime_plan=dict(data.get("runtime_plan") or {}),
            tags=list(data.get("tags") or []),
            description=str(data.get("description") or ""),
            source_glyph_code=data.get("source_glyph_code"),
            meta=dict(data.get("meta") or {}),
        )
        if not glyph.glyph_code:
            glyph.glyph_code = stable_glyph_code(f"{glyph.scope}:{glyph.workflow_id}:{glyph.name}")
        if not glyph.glyph_id:
            glyph.glyph_id = _safe_slug(f"glyph.{glyph.glyph_code.lower()}.{glyph.glyph_version}")
        return glyph.finalize()

    @classmethod
    def load(cls, path: str | Path) -> "WorkflowGlyph":
        p = Path(path)
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
