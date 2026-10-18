"""Durable per-workspace Vault model choice, isolated from business projections."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _path(workspace_id: str, *, create_parent: bool = False) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "", str(workspace_id or ""))[:160]
    if not safe:
        raise ValueError("workspace_id_required")
    root = AIONBusinessPaths.ROOT / "vault_model_selections"
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
        actor_id="local-model-selection",
    )


def load_local_model_selection(workspace_id: str) -> dict[str, Any]:
    store = _guardian_store()
    if store is not None:
        record = store.get_optional(
            "provider.model_selections",
            workspace_id=str(workspace_id),
            entity_id="local-model",
        )
        return dict((record or {}).get("payload") or {})
    path = _path(workspace_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def save_local_model_selection(workspace_id: str, selection: Mapping[str, Any]) -> str:
    store = _guardian_store()
    if store is not None:
        current = store.get_optional(
            "provider.model_selections",
            workspace_id=str(workspace_id),
            entity_id="local-model",
        )
        store.put(
            "provider.model_selections",
            workspace_id=str(workspace_id),
            entity_id="local-model",
            payload=dict(selection),
            expected_version=int(current["version"]) if current else None,
        )
        return f"guardian://provider.model_selections/{workspace_id}/local-model"
    path = _path(workspace_id, create_parent=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(dict(selection), indent=2), encoding="utf-8")
    temporary.replace(path)
    return str(path)
