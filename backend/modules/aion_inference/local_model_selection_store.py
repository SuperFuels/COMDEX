"""Durable per-workspace Vault model choice, isolated from business projections."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _path(workspace_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "", str(workspace_id or ""))[:160]
    if not safe:
        raise ValueError("workspace_id_required")
    root = AIONBusinessPaths.ROOT / "vault_model_selections"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{safe}.json"


def load_local_model_selection(workspace_id: str) -> dict[str, Any]:
    path = _path(workspace_id)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def save_local_model_selection(workspace_id: str, selection: Mapping[str, Any]) -> str:
    path = _path(workspace_id)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(dict(selection), indent=2), encoding="utf-8")
    temporary.replace(path)
    return str(path)
