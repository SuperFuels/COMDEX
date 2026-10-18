from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Iterable

from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
    _CONTAINER_FILE_MAP,
)
from backend.modules.aion_business.runtime.guardian_business_container_repository import (
    GuardianBusinessContainerRepository,
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class GuardianContainerMigrationError(ValueError):
    pass


class GuardianContainerMigration:
    """Copy-and-verify migration; legacy authority is never deleted by this service."""

    def __init__(
        self,
        *,
        legacy: BusinessContainerRepository,
        guardian: GuardianBusinessContainerRepository,
    ) -> None:
        self.legacy = legacy
        self.guardian = guardian

    def migrate_workspace(
        self,
        workspace_id: str,
        *,
        kinds: Iterable[str] | None = None,
        actor_id: str,
        execute: bool = False,
    ) -> dict[str, Any]:
        selected = list(kinds or _CONTAINER_FILE_MAP.keys())
        candidates: list[dict[str, Any]] = []
        migrated = 0
        verified = 0
        for kind in selected:
            if kind not in _CONTAINER_FILE_MAP:
                raise GuardianContainerMigrationError(f"migration_kind_invalid:{kind}")
            if not self.legacy.exists(workspace_id, kind):
                continue
            source = self.legacy.load_dict(workspace_id, kind)
            source_hash = _hash(source)
            target = self.guardian.load_optional_dict(workspace_id, kind)
            if target is not None and _hash(target) != source_hash:
                raise GuardianContainerMigrationError(f"migration_target_conflict:{kind}")
            state = "already_verified" if target is not None else "ready"
            if execute and target is None:
                idempotency = f"migration-{workspace_id}-{kind}-{source_hash[:24]}"
                uri = self.guardian.save_dict(
                    workspace_id,
                    kind,
                    source,
                    actor_id=actor_id,
                    idempotency_key=idempotency,
                    expected_version=None,
                )
                copied = self.guardian.load_dict(workspace_id, kind)
                if _hash(copied) != source_hash:
                    raise RuntimeError(f"migration_verification_failed:{kind}")
                self.guardian.guardian.put_record(
                    collection="migration_receipts",
                    record_id=f"{workspace_id}--{kind}",
                    payload={
                        "schema_version": "tessaris.guardian-container-migration-receipt.v1",
                        "workspace_id": workspace_id,
                        "kind": kind,
                        "source_sha256": source_hash,
                        "target_uri": uri,
                        "source_retained": True,
                    },
                    expected_version=None,
                    idempotency_key=f"receipt-{idempotency}",
                    actor_id=actor_id,
                    recorded_at=_now(),
                )
                target = copied
                state = "migrated_verified"
                migrated += 1
            if target is not None:
                verified += 1
            candidates.append(
                {
                    "kind": kind,
                    "source_sha256": source_hash,
                    "state": state,
                    "legacy_source_retained": True,
                }
            )
        return {
            "schema_version": "tessaris.guardian-container-migration.v1",
            "workspace_id": workspace_id,
            "mode": "execute" if execute else "dry_run",
            "candidate_count": len(candidates),
            "migrated_count": migrated,
            "verified_count": verified,
            "legacy_sources_deleted": 0,
            "authority_switch_allowed": bool(candidates) and verified == len(candidates),
            "candidates": candidates,
        }
