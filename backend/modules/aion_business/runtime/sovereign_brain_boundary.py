from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
from typing import Any, Dict

from backend.modules.aion_business.contracts.sovereign_brain import (
    CANONICAL_STORE_KINDS,
    build_brain_identity,
)
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


class SovereignBrainBoundary:
    """Minimal provider-free boot boundary for the durable customer brain."""

    def __init__(
        self, root: Path, *, domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
    ) -> None:
        self.root = Path(root)
        self.identity_path = self.root / "brain_identity.json"
        self.stores_dir = self.root / "stores"
        self.domain_store = domain_store
        if domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            self.domain_store = VaultDomainStore(
                runtime.guardian, actor_id="sovereign-brain-boundary"
            )
        self.workspace_id = None
        if self.domain_store is not None:
            resolved = workspace_id or self.domain_store.guardian.business_stable_id
            self.workspace_id = canonical_business_id(resolved)

    @classmethod
    def bootstrap(
        cls, root: Path, *, brain_id: str, owner_id: str, public_key_fingerprint: str,
        domain_store: VaultDomainStore | None = None,
    ) -> "SovereignBrainBoundary":
        boundary = cls(root, domain_store=domain_store, workspace_id=brain_id)
        if boundary.domain_store is not None:
            if boundary._vault_get("identity") is None:
                legacy_identity = (
                    boundary._read(boundary.identity_path)
                    if boundary.identity_path.is_file() else None
                )
                boundary._vault_put(
                    "identity",
                    legacy_identity or build_brain_identity(
                        brain_id=brain_id,
                        owner_id=owner_id,
                        public_key_fingerprint=public_key_fingerprint,
                    ),
                )
                if legacy_identity is not None:
                    boundary._receipt_legacy_copy("identity", legacy_identity)
            for kind in CANONICAL_STORE_KINDS:
                if boundary._vault_get(kind, store_record=True) is None:
                    legacy_path = boundary.stores_dir / f"{kind}.json"
                    legacy_payload = boundary._read(legacy_path) if legacy_path.is_file() else None
                    boundary._vault_put(
                        kind,
                        legacy_payload or {
                            "schema_version": "aion.sovereign_store.v1",
                            "kind": kind,
                            "records": [],
                        },
                        store_record=True,
                    )
                    if legacy_payload is not None:
                        boundary._receipt_legacy_copy(kind, legacy_payload, store_record=True)
            return boundary
        boundary.root.mkdir(parents=True, exist_ok=True)
        boundary.stores_dir.mkdir(parents=True, exist_ok=True)
        if not boundary.identity_path.exists():
            boundary._write(
                boundary.identity_path,
                build_brain_identity(
                    brain_id=brain_id,
                    owner_id=owner_id,
                    public_key_fingerprint=public_key_fingerprint,
                ),
            )
        for kind in CANONICAL_STORE_KINDS:
            path = boundary.stores_dir / f"{kind}.json"
            if not path.exists():
                boundary._write(
                    path,
                    {"schema_version": "aion.sovereign_store.v1", "kind": kind, "records": []},
                )
        return boundary

    def status(self) -> Dict[str, Any]:
        if self.domain_store is not None:
            identity_record = self._vault_get("identity")
            identity = dict(identity_record["payload"]) if identity_record else {}
            present = [
                kind for kind in CANONICAL_STORE_KINDS
                if self._vault_get(kind, store_record=True) is not None
            ]
        else:
            identity = self._read(self.identity_path)
            present = [kind for kind in CANONICAL_STORE_KINDS if (self.stores_dir / f"{kind}.json").exists()]
        return {
            "ok": len(present) == len(CANONICAL_STORE_KINDS),
            "brain_id": identity.get("brain_id"),
            "canonical_stores": present,
            "provider_keys_required": False,
            "providers_connected": [],
        }

    def store(self, kind: str) -> Dict[str, Any]:
        if kind not in CANONICAL_STORE_KINDS:
            raise ValueError("Unknown sovereign store")
        if self.domain_store is not None:
            record = self._vault_get(kind, store_record=True)
            if record is None:
                raise FileNotFoundError("sovereign_store_not_found")
            return dict(record["payload"])
        return self._read(self.stores_dir / f"{kind}.json")

    def upsert_store_record(self, kind: str, record: Dict[str, Any], *, record_id: str) -> Dict[str, Any]:
        """Register authoritative data without copying it into a parallel store."""
        if not str(record_id or "").strip():
            raise ValueError("record_id_required")
        payload = self.store(kind)
        records = [
            item for item in payload.get("records", [])
            if isinstance(item, dict) and item.get("record_id") != record_id
        ]
        records.append({**record, "record_id": record_id})
        payload["records"] = records
        if self.domain_store is not None:
            current = self._vault_get(kind, store_record=True)
            self._vault_put(
                kind, payload, store_record=True,
                expected_version=int(current["version"]) if current else None,
            )
        else:
            self._write(self.stores_dir / f"{kind}.json", payload)
        return payload

    @staticmethod
    def _domain(kind: str, *, store_record: bool) -> str:
        if not store_record:
            return "business.identity"
        if kind == "business_map":
            return "business.map"
        if kind == "receipt":
            return "business.knowledge_audit"
        return "business.knowledge"

    @staticmethod
    def _entity(kind: str, *, store_record: bool) -> str:
        return f"sovereign-brain/{'stores/' if store_record else ''}{kind}"

    def _vault_get(self, kind: str, *, store_record: bool = False) -> Dict[str, Any] | None:
        assert self.domain_store is not None and self.workspace_id is not None
        return self.domain_store.get_optional(
            self._domain(kind, store_record=store_record),
            workspace_id=self.workspace_id,
            entity_id=self._entity(kind, store_record=store_record),
        )

    def _vault_put(
        self, kind: str, payload: Dict[str, Any], *, store_record: bool = False,
        expected_version: int | None = None,
    ) -> None:
        assert self.domain_store is not None and self.workspace_id is not None
        self.domain_store.put(
            self._domain(kind, store_record=store_record),
            workspace_id=self.workspace_id,
            entity_id=self._entity(kind, store_record=store_record),
            payload=payload,
            expected_version=expected_version,
        )

    @staticmethod
    def _payload_hash(payload: Dict[str, Any]) -> str:
        raw = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _receipt_legacy_copy(
        self, kind: str, payload: Dict[str, Any], *, store_record: bool = False,
    ) -> None:
        assert self.domain_store is not None and self.workspace_id is not None
        copied = self._vault_get(kind, store_record=store_record)
        if copied is None or dict(copied["payload"]) != payload:
            raise RuntimeError("sovereign_brain_legacy_copy_verification_failed")
        content_hash = self._payload_hash(payload)
        self.domain_store.put(
            "vault.migration_receipts",
            workspace_id=self.workspace_id,
            entity_id=f"sovereign-brain/{kind}/{content_hash}",
            payload={
                "schema_version": "tessaris.sovereign-brain-migration-receipt.v1",
                "source_kind": kind,
                "plaintext_sha256": content_hash,
                "target_domain": self._domain(kind, store_record=store_record),
                "target_entity": self._entity(kind, store_record=store_record),
                "verified": True,
                "source_retained": True,
            },
            expected_version=None,
            idempotency_key=f"sovereign-brain-copy-{kind}-{content_hash}",
        )

    @staticmethod
    def _read(path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, payload: Dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
