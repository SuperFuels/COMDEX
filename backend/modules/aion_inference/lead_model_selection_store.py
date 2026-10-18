"""Durable per-workspace lead model choice made explicitly in Connections."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _path(workspace_id: str, *, create_parent: bool = False) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "", str(workspace_id or ""))[:160]
    if not safe:
        raise ValueError("workspace_id_required")
    root = AIONBusinessPaths.ROOT / "lead_model_selections"
    if create_parent:
        root.mkdir(parents=True, exist_ok=True)
    return root / f"{safe}.json"


def _guardian_store():
    from backend.modules.aion_business.runtime.business_vault_runtime import (
        configured_business_vault_runtime,
        guardian_mode_requested,
    )
    from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore

    if not guardian_mode_requested():
        return None
    return VaultDomainStore(
        configured_business_vault_runtime().guardian,
        actor_id="boardroom-lead-model-selection",
    )


def load_lead_model_selection(workspace_id: str) -> dict[str, Any]:
    store = _guardian_store()
    if store is not None:
        record = store.get_optional(
            "provider.model_selections",
            workspace_id=str(workspace_id),
            entity_id="boardroom-lead-model",
        )
        return dict((record or {}).get("payload") or {})
    try:
        value = json.loads(_path(workspace_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def save_lead_model_selection(
    workspace_id: str,
    *,
    provider_id: str,
    model_id: str,
) -> dict[str, Any]:
    record = {
        "workspace_id": str(workspace_id),
        "provider_id": str(provider_id),
        "model_id": str(model_id),
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "selection_source": "connections",
    }
    store = _guardian_store()
    if store is not None:
        current = store.get_optional(
            "provider.model_selections",
            workspace_id=str(workspace_id),
            entity_id="boardroom-lead-model",
        )
        store.put(
            "provider.model_selections",
            workspace_id=str(workspace_id),
            entity_id="boardroom-lead-model",
            payload=record,
            expected_version=int(current["version"]) if current else None,
        )
        return record
    path = _path(workspace_id, create_parent=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2), encoding="utf-8")
    temporary.replace(path)
    return record
