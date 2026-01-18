cd /workspaces/COMDEX

mkdir -p backend/modules/identity
touch backend/modules/identity/__init__.py

cat > backend/modules/identity/avatar_registry.py <<'PY'
"""
Avatar Identity Registry (shim)

This repo imports:
  from backend.modules.identity.avatar_registry import get_avatar_identity

But the module doesn't exist in git history. This shim keeps boot stable
and provides a minimal identity object for holograms/signing systems.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Optional persistence (works in dev; safe if missing in prod)
DATA_PATH = Path(os.getenv("AVATAR_IDENTITY_DB", "data/identity/avatars.json"))

_cache: Dict[str, Dict[str, Any]] = {}

def _load_db() -> Dict[str, Dict[str, Any]]:
    if not DATA_PATH.exists():
        return {}
    try:
        with DATA_PATH.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            return {str(k): (v if isinstance(v, dict) else {"id": str(k)}) for k, v in raw.items()}
    except Exception:
        pass
    return {}

def _save_db(db: Dict[str, Dict[str, Any]]) -> None:
    try:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DATA_PATH.open("w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, sort_keys=True)
    except Exception:
        # Never crash the app because persistence failed
        pass

def register_avatar_identity(avatar_id: str, identity: Dict[str, Any], persist: bool = True) -> Dict[str, Any]:
    """Register/override an identity for an avatar id."""
    aid = str(avatar_id).strip() or "UNKNOWN"
    obj = {"id": aid, **(identity or {})}
    _cache[aid] = obj

    if persist:
        db = _load_db()
        db[aid] = obj
        _save_db(db)

    return obj

def get_avatar_identity(avatar_id: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Return a stable identity dict.
    Must never throw during import-time usage.
    """
    aid = str(avatar_id).strip() or "UNKNOWN"

    if aid in _cache:
        return _cache[aid]

    db = _load_db()
    if aid in db:
        _cache[aid] = db[aid]
        return db[aid]

    # Safe default identity (works everywhere)
    ident = {
        "id": aid,
        "name": os.getenv("AION_AVATAR_NAME", "AION"),
        "role": os.getenv("AION_ROLE", "primary"),
        "namespace": os.getenv("AION_NAMESPACE", "tessaris"),
        "pubkey": os.getenv("AION_AVATAR_PUBKEY", ""),   # optional
        "meta": {"source": "shim"},
    }

    if default:
        ident.update(default)

    _cache[aid] = ident
    return ident
PY