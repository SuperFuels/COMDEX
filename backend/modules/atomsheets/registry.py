# ===============================
# 📁 backend/modules/atomsheets/registry.py
# ===============================
from __future__ import annotations
from typing import Optional, Dict, List, Any
import os
import json
import hashlib
import threading

try:
    # Optional helper for timestamps (nice to have)
    from backend.modules.utils.time_utils import now_utc_iso
except Exception:
    from datetime import datetime, timezone
    def now_utc_iso() -> str:  # fallback
        return datetime.now(timezone.utc).isoformat()

REGISTRY_ENV_VAR = "ATOMSHEET_REGISTRY_PATH"
DEFAULT_REGISTRY_FILENAME = ".atomsheet_registry.json"
REGISTRY_VERSION = 1


def _normalize_atom_path(p: str) -> str:
    """
    Accept canonical `.atom` and legacy `.sqs.json`. If no extension, default to `.atom`.
    """
    if p.endswith(".atom") or p.endswith(".sqs.json"):
        return p
    return f"{p}.atom"


class AtomSheetRegistry:
    """
    Persistent registry of AtomSheets.
    - Maps sheet_id -> absolute file path to .atom/.sqs.json (with metadata)
    - Maps qfc_id   -> sheet_id
    - Saves/loads to a single JSON file (path configurable via env or constructor)

    API (stable):
      - register(path: str, qfc_id: Optional[str] = None) -> str
      - resolve(id_or_path: str) -> Optional[str]
      - get_qfc_sheet(qfc_id: str) -> Optional[str]

    Extras:
      - list_sheets(), list_links()
      - forget(sheet_id_or_path), unlink(qfc_id), clear()
      - save(), load()
    """

    def __init__(self, path: Optional[str] = None, autoload: bool = True):
        # choose registry path:
        # 1) explicit arg
        # 2) env var ATOMSHEET_REGISTRY_PATH
        # 3) default to CWD + .atomsheet_registry.json
        self._path = (
            path
            or os.environ.get(REGISTRY_ENV_VAR)
            or os.path.join(os.getcwd(), DEFAULT_REGISTRY_FILENAME)
        )

        # NEW: thread-safety
        self._lock = threading.Lock()

        # Registry:
        #   _registry[sheet_id] = str (legacy) OR {"path": str, "registered_at": str}
        self._registry: Dict[str, Any] = {}
        self._qfc_map: Dict[str, str] = {}   # qfc_id -> sheet_id

        if autoload:
            self.load(silent=True)

    # ------------- core persistence -------------
    def save(self) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)

            # Normalize registry values to {"path": "...", "registered_at": "..."}
            normalized: Dict[str, Dict[str, str]] = {}
            for sid, val in self._registry.items():
                if isinstance(val, str):
                    # legacy in-memory shape → upgrade on save
                    normalized[sid] = {"path": os.path.abspath(val), "registered_at": now_utc_iso()}
                elif isinstance(val, dict) and "path" in val:
                    p = os.path.abspath(val["path"])
                    ra = val.get("registered_at") or now_utc_iso()
                    normalized[sid] = {"path": p, "registered_at": ra}
                else:
                    # unknown shape; skip
                    continue

            payload = {
                "version": REGISTRY_VERSION,
                "saved_at": now_utc_iso(),
                "registry": normalized,
                "qfc_map": self._qfc_map,
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

    def load(self, silent: bool = False) -> bool:
        if not os.path.exists(self._path):
            return False
        try:
            with self._lock, open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)

            reg = data.get("registry", {})
            # Back-compat: values may be str (old) or dict (new)
            for sid, val in reg.items():
                if isinstance(val, str):
                    self._registry[sid] = os.path.abspath(val)
                elif isinstance(val, dict) and "path" in val:
                    self._registry[sid] = {
                        "path": os.path.abspath(val["path"]),
                        "registered_at": val.get("registered_at") or now_utc_iso(),
                    }

            qfc_map = data.get("qfc_map", {})
            if isinstance(qfc_map, dict):
                self._qfc_map.update(qfc_map)

            return True
        except Exception:
            if not silent:
                raise
            return False

    # ------------- helpers -------------
    @staticmethod
    def _sheet_id_for_path(path: str) -> str:
        # stable id based on absolute path; avoids collisions across cwd changes
        ap = os.path.abspath(path)
        return hashlib.md5(ap.encode("utf-8")).hexdigest()

    # ------------- public API -------------
    def register(self, path: str, qfc_id: Optional[str] = None) -> str:
        """
        Register a sheet path (canonical .atom or legacy .sqs.json) and return its sheet_id.
        Validates path existence, prevents duplicate/conflicting entries, and persists metadata.
        """
        norm = _normalize_atom_path(path)
        ap = os.path.abspath(norm)
        if not os.path.exists(ap):
            raise ValueError(f"AtomSheet path does not exist: {ap}")

        sheet_id = self._sheet_id_for_path(ap)

        with self._lock:
            # Duplicate sheet_id pointing to a different path → error
            existing = self._registry.get(sheet_id)
            if isinstance(existing, str) and os.path.abspath(existing) != ap:
                raise ValueError(f"Duplicate sheet_id mapped to different path: {sheet_id}")
            if isinstance(existing, dict) and os.path.abspath(existing.get("path", "")) != ap:
                raise ValueError(f"Duplicate sheet_id mapped to different path: {sheet_id}")

            # Register/upgrade metadata shape
            self._registry[sheet_id] = {
                "path": ap,
                "registered_at": now_utc_iso(),
            }

            # QFC mapping (no collisions)
            if qfc_id:
                if qfc_id in self._qfc_map and self._qfc_map[qfc_id] != sheet_id:
                    raise ValueError(f"QFC id already linked to a different sheet: {qfc_id}")
                self._qfc_map[qfc_id] = sheet_id

            self.save()
            return sheet_id

    def resolve(self, id_or_path: str) -> Optional[str]:
        """
        Resolve a sheet ID or path to an absolute file path.
        - If id_or_path matches a known sheet_id → return mapped path
        - Else if id_or_path is an existing path → return its absolute path
        - Else None
        """
        if not id_or_path:
            return None

        with self._lock:
            # If it's a known sheet_id
            if id_or_path in self._registry:
                val = self._registry[id_or_path]
                if isinstance(val, str):
                    return os.path.abspath(val)
                if isinstance(val, dict) and "path" in val:
                    return os.path.abspath(val["path"])

            # Else if it's a path on disk
            if os.path.exists(id_or_path):
                return os.path.abspath(id_or_path)

        return None

    def get_qfc_sheet(self, qfc_id: str) -> Optional[str]:
        """Return the sheet path for a QFC container id, if linked."""
        with self._lock:
            sid = self._qfc_map.get(qfc_id)
        return self.resolve(sid) if sid else None

    # ------------- optional utilities -------------
    def list_sheets(self) -> Dict[str, str]:
        """Return a simple mapping of sheet_id -> absolute path (metadata stripped)."""
        with self._lock:
            out: Dict[str, str] = {}
            for sid, val in self._registry.items():
                if isinstance(val, str):
                    out[sid] = os.path.abspath(val)
                elif isinstance(val, dict) and "path" in val:
                    out[sid] = os.path.abspath(val["path"])
            return out

    def list_links(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._qfc_map)

    def unlink(self, qfc_id: str) -> bool:
        with self._lock:
            if qfc_id in self._qfc_map:
                del self._qfc_map[qfc_id]
                self.save()
                return True
        return False

    def forget(self, sheet_id_or_path: str) -> bool:
        """
        Remove a sheet from the registry by id or path.
        Also removes any QFC links pointing to that sheet.
        """
        with self._lock:
            # resolve to id
            sid = None
            if sheet_id_or_path in self._registry:
                sid = sheet_id_or_path
            else:
                ap = os.path.abspath(sheet_id_or_path)
                # find by path
                for k, v in list(self._registry.items()):
                    vpath = v if isinstance(v, str) else v.get("path")
                    if os.path.abspath(vpath or "") == ap:
                        sid = k
                        break
            if not sid:
                return False

            # delete id and any links
            del self._registry[sid]
            for qfc, linked_sid in list(self._qfc_map.items()):
                if linked_sid == sid:
                    del self._qfc_map[qfc]
            self.save()
            return True

    def clear(self) -> None:
        with self._lock:
            self._registry.clear()
            self._qfc_map.clear()
            self.save()

    # quick dunder for debug
    def __repr__(self) -> str:
        with self._lock:
            return f"AtomSheetRegistry(path={self._path!r}, sheets={len(self._registry)}, links={len(self._qfc_map)})"


# -----------------------------------------------------------------------------
# Back-compat shim for atomsheet_engine.load_atom
# Exposes register_sheet() so older callers keep working.
# Also caches loaded AtomSheet objects in-memory for quick lookups.
# -----------------------------------------------------------------------------
try:
    from .models import AtomSheet  # real type
except Exception:
    class AtomSheet:  # fallback type hint only
        id: str  # pragma: no cover


# In-memory map: sheet_id -> AtomSheet object
_SHEET_OBJECTS: Dict[str, AtomSheet] = {}


def register_sheet(sheet: AtomSheet, path: Optional[str] = None, qfc_id: Optional[str] = None) -> str:
    """
    Register an AtomSheet object for in-memory access.
    Optionally persist a path and QFC mapping using AtomSheetRegistry if provided.
    """
    _SHEET_OBJECTS[sheet.id] = sheet

    # If a path/QFC id is provided, also persist that mapping using the class registry.
    try:
        if path:
            reg = AtomSheetRegistry()
            reg.load()
            reg.register(path, qfc_id)
            reg.save()
    except Exception:
        # stay ultra-defensive; in-memory registration is enough for most flows
        pass

    return sheet.id


def get_registered_sheet(sheet_id: str) -> Optional[AtomSheet]:
    """Fetch a previously registered AtomSheet object from memory."""
    return _SHEET_OBJECTS.get(sheet_id)


# Optional: make symbols explicit
__all__ = [
    "AtomSheetRegistry",
    "register_sheet",
    "get_registered_sheet",
]