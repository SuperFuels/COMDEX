from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from backend.modules.aion_business.contracts.sovereign_brain import (
    CANONICAL_STORE_KINDS,
    build_brain_identity,
)


class SovereignBrainBoundary:
    """Minimal provider-free boot boundary for the durable customer brain."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.identity_path = self.root / "brain_identity.json"
        self.stores_dir = self.root / "stores"

    @classmethod
    def bootstrap(
        cls, root: Path, *, brain_id: str, owner_id: str, public_key_fingerprint: str
    ) -> "SovereignBrainBoundary":
        boundary = cls(root)
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
        self._write(self.stores_dir / f"{kind}.json", payload)
        return payload

    @staticmethod
    def _read(path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write(path: Path, payload: Dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, path)
