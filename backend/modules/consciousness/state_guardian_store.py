from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path
import time
from typing import Any, Mapping
import uuid

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


AGENT_STATES_ENTITY_ID = "consciousness_agent_states"
RESONANCE_EVENT_TYPE = "state_manager_resonance_sample"
MAX_STATE_BYTES = 2 * 1024 * 1024
MAX_EVENT_BYTES = 64 * 1024
MAX_CONTAINER_BYTES = 8 * 1024 * 1024


class ConsciousnessStateStore:
    """Persistence boundary for customer-derived consciousness state.

    Guardian is the only normal durable store.  A process without Guardian may
    still use StateManager in memory, but it must not create customer-data files
    beside the application.  The old JSON/JSONL paths are available only behind
    an explicit compatibility switch for controlled migration and development.
    """

    def __init__(
        self,
        *,
        vault_store: AionLearningVaultStore | None = None,
        workspace_id: str | None = None,
        allow_legacy_files: bool | None = None,
        legacy_agent_state_path: str | Path = "agent_state.json",
        legacy_resonance_log_path: str | Path = (
            "data/analysis/state_resonance_log.jsonl"
        ),
    ) -> None:
        self.vault_store = vault_store or AionLearningVaultStore(
            workspace_id=workspace_id,
        )
        self.allow_legacy_files = (
            os.getenv("TESSARIS_ALLOW_LEGACY_CONSCIOUSNESS_FILES", "0") == "1"
            if allow_legacy_files is None
            else bool(allow_legacy_files)
        )
        self.legacy_agent_state_path = Path(legacy_agent_state_path)
        self.legacy_resonance_log_path = Path(legacy_resonance_log_path)

    @property
    def guardian_enabled(self) -> bool:
        return self.vault_store.enabled

    @property
    def storage_boundary(self) -> str:
        if self.guardian_enabled:
            return "guardian"
        if self.allow_legacy_files:
            return "legacy-development-file"
        return "memory"

    @staticmethod
    def _canonical_mapping(
        payload: Mapping[str, Any],
        *,
        maximum_bytes: int,
        error_code: str,
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError(f"{error_code}_mapping_required")
        canonical = json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        if len(canonical) > maximum_bytes:
            raise ValueError(f"{error_code}_too_large")
        decoded = json.loads(canonical.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise TypeError(f"{error_code}_mapping_required")
        return decoded

    def load_agent_states(self) -> dict[str, Any]:
        if self.guardian_enabled:
            stored = self.vault_store.get_state(AGENT_STATES_ENTITY_ID, {})
            return self._canonical_mapping(
                stored,
                maximum_bytes=MAX_STATE_BYTES,
                error_code="consciousness_agent_states",
            )
        if self.allow_legacy_files and self.legacy_agent_state_path.exists():
            with self.legacy_agent_state_path.open("r", encoding="utf-8") as handle:
                stored = json.load(handle)
            return self._canonical_mapping(
                stored,
                maximum_bytes=MAX_STATE_BYTES,
                error_code="consciousness_agent_states",
            )
        return {}

    def save_agent_states(self, states: Mapping[str, Any]) -> bool:
        canonical = self._canonical_mapping(
            states,
            maximum_bytes=MAX_STATE_BYTES,
            error_code="consciousness_agent_states",
        )
        if self.guardian_enabled:
            self.vault_store.put_state(AGENT_STATES_ENTITY_ID, canonical)
            return True
        if not self.allow_legacy_files:
            return False
        self.legacy_agent_state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.legacy_agent_state_path.with_suffix(
            self.legacy_agent_state_path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(canonical, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(self.legacy_agent_state_path)
        return True

    def append_resonance_sample(self, sample: Mapping[str, Any]) -> bool:
        canonical = self._canonical_mapping(
            sample,
            maximum_bytes=MAX_EVENT_BYTES,
            error_code="consciousness_resonance_sample",
        )
        event_id = f"state-manager-resonance-{time.time_ns()}-{uuid.uuid4().hex}"
        event = {
            **canonical,
            "event_id": event_id,
            "event_type": RESONANCE_EVENT_TYPE,
            "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "vault_order_ns": time.time_ns(),
        }
        if self.guardian_enabled:
            self.vault_store.append_event(event_id, event)
            return True
        if not self.allow_legacy_files:
            return False
        self.legacy_resonance_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.legacy_resonance_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return True

    @staticmethod
    def _container_entity_id(container_id: str) -> str:
        stable = str(container_id or "").strip()
        if not stable:
            raise ValueError("consciousness_container_id_required")
        return "consciousness_container--" + sha256(stable.encode("utf-8")).hexdigest()[:32]

    def load_container_state(self, base_container: Mapping[str, Any]) -> dict[str, Any]:
        canonical_base = self._canonical_mapping(
            base_container,
            maximum_bytes=MAX_CONTAINER_BYTES,
            error_code="consciousness_container",
        )
        if not self.guardian_enabled:
            return canonical_base
        entity_id = self._container_entity_id(str(canonical_base.get("id") or ""))
        stored = self.vault_store.get_state(entity_id, {})
        if not stored:
            return canonical_base
        stored_container = stored.get("container")
        if not isinstance(stored_container, Mapping):
            raise ValueError("consciousness_container_guardian_payload_invalid")
        return self._canonical_mapping(
            stored_container,
            maximum_bytes=MAX_CONTAINER_BYTES,
            error_code="consciousness_container",
        )

    def save_container_state(
        self,
        container: Mapping[str, Any],
        *,
        legacy_path: str | Path | None = None,
    ) -> bool:
        canonical = self._canonical_mapping(
            container,
            maximum_bytes=MAX_CONTAINER_BYTES,
            error_code="consciousness_container",
        )
        container_id = str(canonical.get("id") or "").strip()
        entity_id = self._container_entity_id(container_id)
        if self.guardian_enabled:
            self.vault_store.put_state(
                entity_id,
                {
                    "record_type": "consciousness_container_overlay",
                    "container_id_hash": sha256(container_id.encode("utf-8")).hexdigest(),
                    "container": canonical,
                },
            )
            return True
        if not self.allow_legacy_files:
            return False
        if legacy_path is None:
            raise ValueError("consciousness_legacy_container_path_required")
        path = Path(legacy_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(canonical, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)
        return True
