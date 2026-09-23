from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
from threading import RLock
from typing import Any, Dict

from backend.modules.aion_business.runtime.canonical_business_identity import canonical_business_id
from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


class FoundationSessionRevisionConflict(ValueError):
    def __init__(self, *, expected: int, current: int) -> None:
        super().__init__("foundation_session_revision_conflict")
        self.expected = expected
        self.current = current


class FoundationOnboardingSessionService:
    """Mother-authoritative progress for the existing Boardroom foundation interview."""

    SCHEMA_VERSION = "aion.business_foundation_onboarding_session.v1"
    MAX_PACKET_BYTES = 1_000_000
    MAX_TRANSCRIPT_TURNS = 500
    _SENSITIVE_KEYS = {
        "password", "passphrase", "secret", "api_key", "apikey", "access_token",
        "refresh_token", "private_key", "cvv", "pin", "card_number",
    }

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else AIONBusinessPaths.ROOT / "foundation_onboarding"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat()

    @staticmethod
    def _hash(value: Any) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()

    def _path(self, workspace_id: str) -> Path:
        return self.base_dir / f"{canonical_business_id(workspace_id)}.json"

    def _receipt_path(self, workspace_id: str) -> Path:
        return self.base_dir / f"{canonical_business_id(workspace_id)}.receipts.jsonl"

    def _empty(self, workspace_id: str) -> Dict[str, Any]:
        workspace_id = canonical_business_id(workspace_id)
        return {
            "schema_version": self.SCHEMA_VERSION,
            "workspace_id": workspace_id,
            "revision": 0,
            "status": "not_started",
            "packet": None,
            "packet_hash": None,
            "created_at": None,
            "updated_at": None,
            "updated_by": None,
            "last_device_id": None,
            "completed_at": None,
            "resume": {"next_question": None, "readiness": None},
            "authoritative_store": "mother_brain",
            "browser_storage_role": "migration_cache_only",
            "external_actions_allowed": False,
        }

    def get(self, workspace_id: str) -> Dict[str, Any]:
        workspace_id = canonical_business_id(workspace_id)
        path = self._path(workspace_id)
        with self._lock:
            if not path.exists():
                return self._empty(workspace_id)
            payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("unsupported_foundation_session_schema")
        return deepcopy(payload)

    def save(
        self,
        workspace_id: str,
        *,
        packet: Dict[str, Any],
        expected_revision: int | None,
        actor_id: str,
        device_id: str,
        complete: bool = False,
    ) -> Dict[str, Any]:
        workspace_id = canonical_business_id(workspace_id)
        clean_packet = deepcopy(packet)
        self._validate_packet(clean_packet)
        now = self._now()

        with self._lock:
            current = self.get(workspace_id)
            current_revision = int(current.get("revision") or 0)
            if expected_revision is not None and int(expected_revision) != current_revision:
                raise FoundationSessionRevisionConflict(
                    expected=int(expected_revision), current=current_revision
                )

            is_complete = bool(
                complete
                or clean_packet.get("status") == "foundation_ready_for_finance_handoff"
                or (clean_packet.get("next_question") or {}).get("reason") == "finance_handoff_ready"
                or (clean_packet.get("next_question") or {}).get("action") == "route_finance_live_agent"
            )
            revision = current_revision + 1
            record = {
                "schema_version": self.SCHEMA_VERSION,
                "workspace_id": workspace_id,
                "revision": revision,
                "status": "completed_pending_commit" if is_complete else "in_progress",
                "packet": clean_packet,
                "packet_hash": self._hash(clean_packet),
                "created_at": current.get("created_at") or now,
                "updated_at": now,
                "updated_by": str(actor_id or "local_owner")[:160],
                "last_device_id": str(device_id or "unknown_device")[:160],
                "completed_at": current.get("completed_at") or (now if is_complete else None),
                "resume": {
                    "next_question": deepcopy(clean_packet.get("next_question")),
                    "readiness": deepcopy(clean_packet.get("readiness")),
                },
                "authoritative_store": "mother_brain",
                "browser_storage_role": "migration_cache_only",
                "external_actions_allowed": False,
            }
            self._atomic_write(self._path(workspace_id), record)
            self._append_receipt(
                workspace_id,
                {
                    "schema_version": "aion.business_foundation_onboarding_receipt.v1",
                    "workspace_id": workspace_id,
                    "revision": revision,
                    "action": "complete_progress" if is_complete else "save_progress",
                    "packet_hash": record["packet_hash"],
                    "actor_id": record["updated_by"],
                    "device_id": record["last_device_id"],
                    "created_at": now,
                    "canonical_business_map_mutated": False,
                },
            )
        return deepcopy(record)

    def reset(
        self,
        workspace_id: str,
        *,
        expected_revision: int | None,
        actor_id: str,
        confirm_reset: bool,
    ) -> Dict[str, Any]:
        if not confirm_reset:
            raise ValueError("explicit_foundation_session_reset_confirmation_required")
        workspace_id = canonical_business_id(workspace_id)
        now = self._now()
        with self._lock:
            current = self.get(workspace_id)
            current_revision = int(current.get("revision") or 0)
            if expected_revision is not None and int(expected_revision) != current_revision:
                raise FoundationSessionRevisionConflict(
                    expected=int(expected_revision), current=current_revision
                )
            record = self._empty(workspace_id)
            record.update({
                "revision": current_revision + 1,
                "status": "reset",
                "created_at": current.get("created_at") or now,
                "updated_at": now,
                "updated_by": str(actor_id or "local_owner")[:160],
            })
            self._atomic_write(self._path(workspace_id), record)
            self._append_receipt(
                workspace_id,
                {
                    "schema_version": "aion.business_foundation_onboarding_receipt.v1",
                    "workspace_id": workspace_id,
                    "revision": record["revision"],
                    "action": "reset_progress",
                    "previous_packet_hash": current.get("packet_hash"),
                    "actor_id": record["updated_by"],
                    "created_at": now,
                    "canonical_business_map_mutated": False,
                },
            )
        return deepcopy(record)

    def _validate_packet(self, packet: Dict[str, Any]) -> None:
        if not isinstance(packet, dict):
            raise ValueError("foundation_packet_object_required")
        encoded = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self.MAX_PACKET_BYTES:
            raise ValueError("foundation_packet_too_large")
        transcript = packet.get("transcript") or []
        if not isinstance(transcript, list):
            raise ValueError("foundation_transcript_must_be_a_list")
        if len(transcript) > self.MAX_TRANSCRIPT_TURNS:
            raise ValueError("foundation_transcript_too_long")
        self._reject_secrets(packet)

    def _reject_secrets(self, value: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).strip().lower().replace("-", "_")
                if normalized in self._SENSITIVE_KEYS and child not in (None, "", [], {}):
                    raise ValueError(f"secret_not_allowed_in_foundation_session:{'.'.join(path + (normalized,))}")
                self._reject_secrets(child, path + (normalized,))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self._reject_secrets(child, path + (str(index),))

    @staticmethod
    def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    def _append_receipt(self, workspace_id: str, receipt: Dict[str, Any]) -> None:
        path = self._receipt_path(workspace_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
