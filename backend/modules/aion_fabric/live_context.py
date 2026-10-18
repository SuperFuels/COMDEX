from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore

from .canonical import canonical_bytes, canonical_hash, utc_now_iso


class LiveContextStore:
    """Build a small, evidence-labelled context only after an explicit Pilot request."""

    def __init__(
        self,
        runtime_dir: str | Path,
        *,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
    ) -> None:
        self.path = Path(runtime_dir) / "live" / "latest_context.json"
        self.domain_store = domain_store
        self.workspace_id = str(workspace_id or "").strip()
        if self.domain_store is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        elif not self.workspace_id:
            raise ValueError("aion_fabric_live_context_workspace_required")

    def build(
        self,
        *,
        device_state: Dict[str, Any],
        recent_transcripts: Iterable[str] = (),
        belief: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        transcripts = [" ".join(str(item).split()).strip()[:320] for item in recent_transcripts]
        transcripts = [item for item in transcripts if item and "pilot" not in item.lower()][-4:]
        app_id = str(device_state.get("foreground_app_id") or "unknown")[:160]
        app_title = str(device_state.get("foreground_app_title") or app_id)[:160]
        playback = {
            key: device_state[key]
            for key in ("media_title", "title", "playback_state", "position", "duration")
            if device_state.get(key) is not None
        }
        record = {
            "schema_version": "pilot.live.context.v1",
            "created_at": utc_now_iso(),
            "surface": str((belief or {}).get("surface") or "unknown")[:80],
            "app": {"id": app_id, "title": app_title},
            "playback": playback,
            "recent_statement": transcripts[-1] if transcripts else "",
            "recent_transcripts": transcripts,
            "evidence": [
                {"kind": "webos_state", "detail": f"Foreground application reported as {app_title}"},
                *(
                    [{"kind": "ephemeral_local_transcript", "detail": "Recent television speech was transcribed locally"}]
                    if transcripts else []
                ),
            ],
            "confidence": 0.92 if app_id != "unknown" else 0.55,
            "privacy": {
                "raw_audio_retained": False,
                "rolling_audio_seconds": 30,
                "context_persisted_only_after_explicit_request": True,
            },
        }
        record["context_hash"] = canonical_hash(record)
        if self.domain_store is not None:
            existing = self.domain_store.get_optional(
                "learning.customer_state",
                workspace_id=self.workspace_id,
                entity_id="aion_fabric.latest_live_context",
            )
            self.domain_store.put(
                "learning.customer_state",
                workspace_id=self.workspace_id,
                entity_id="aion_fabric.latest_live_context",
                payload=record,
                expected_version=int(existing["version"]) if existing else None,
            )
            return record
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(record))
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        return record

    def latest(self) -> Dict[str, Any] | None:
        if self.domain_store is not None:
            result = self.domain_store.get_optional(
                "learning.customer_state",
                workspace_id=self.workspace_id,
                entity_id="aion_fabric.latest_live_context",
            )
            return dict(result["payload"]) if result else None
        if not self.path.exists():
            return None
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None


def configured_live_context_store(runtime_dir: str | Path) -> LiveContextStore:
    """Select encrypted explicit-request context and retain verified legacy state."""

    runtime_path = Path(runtime_dir)
    if guardian_mode_requested():
        runtime = configured_business_vault_runtime()
        workspace_id = str(os.environ.get("TESSARIS_BUSINESS_STABLE_ID") or "").strip()
        if not workspace_id:
            raise RuntimeError("aion_fabric_live_context_workspace_required")
        domains = VaultDomainStore(runtime.guardian, actor_id="aion-fabric-live-context")
        selected = LiveContextStore(
            runtime_path, domain_store=domains, workspace_id=workspace_id
        )
        entity_id = "aion_fabric.latest_live_context"
        source = runtime_path / "live" / "latest_context.json"
        if source.exists() and domains.get_optional(
            "learning.customer_state", workspace_id=workspace_id, entity_id=entity_id
        ) is None:
            legacy = LiveContextStore(runtime_path).latest()
            if legacy is None:
                raise RuntimeError("aion_fabric_live_context_migration_source_invalid")
            domains.put(
                "learning.customer_state",
                workspace_id=workspace_id,
                entity_id=entity_id,
                payload=legacy,
            )
            restored = domains.get_optional(
                "learning.customer_state", workspace_id=workspace_id, entity_id=entity_id
            )
            if restored is None or dict(restored["payload"]) != legacy or not source.exists():
                raise RuntimeError("aion_fabric_live_context_migration_verification_failed")
            from hashlib import sha256

            digest = sha256(source.read_bytes()).hexdigest()
            domains.put(
                "learning.audit",
                workspace_id=workspace_id,
                entity_id=f"aion_fabric.live_context_migration.{digest}",
                payload={
                    "schema_version": "aion.live-context-migration.v1",
                    "source_sha256": digest,
                    "source_file_count": 1,
                    "source_retained": True,
                    "copied_and_verified": True,
                    "completed_at": utc_now_iso(),
                },
            )
        return selected
    mode = str(os.environ.get("TESSARIS_RUNTIME_MODE") or "development").lower()
    if mode in {"production", "prod"}:
        raise RuntimeError("aion_fabric_guardian_live_context_required_in_production")
    return LiveContextStore(runtime_path)
