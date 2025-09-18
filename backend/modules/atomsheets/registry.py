# ===============================
# 📁 backend/modules/atomsheets/registry.py
# ===============================
from __future__ import annotations
from typing import Optional, Dict, Tuple, List
import os
import json
import hashlib

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


class AtomSheetRegistry:
    """
    Persistent registry of AtomSheets.
    - Maps sheet_id -> absolute file path to .sqs.json
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

        self._registry: Dict[str, str] = {}  # sheet_id -> absolute path
        self._qfc_map: Dict[str, str] = {}   # qfc_id -> sheet_id

        if autoload:
            self.load(silent=True)

    # ------------- core persistence -------------
    def save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        payload = {
            "version": REGISTRY_VERSION,
            "saved_at": now_utc_iso(),
            "registry": self._registry,
            "qfc_map": self._qfc_map,
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load(self, silent: bool = False) -> bool:
        if not os.path.exists(self._path):
            return False
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._registry.update(data.get("registry", {}))
            self._qfc_map.update(data.get("qfc_map", {}))
            return True
        except Exception as e:
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
    def register(self, path: str, qfc_id: Optional[str] = None, *, sheet_id: Optional[str] = None) -> str:
        """
        Register a .sqs.json file path. Optionally bind it to a QFC container id.
        Returns the sheet_id.
        """
        if not path:
            raise ValueError("path is required")
        ap = os.path.abspath(path)
        sid = sheet_id or self._sheet_id_for_path(ap)
        self._registry[sid] = ap
        if qfc_id:
            self._qfc_map[qfc_id] = sid
        self.save()
        return sid

    def resolve(self, id_or_path: str) -> Optional[str]:
        """
        Resolve a sheet ID or path to an absolute file path.
        - If id_or_path matches a known sheet_id → return mapped path
        - Else if id_or_path is an existing path → return its absolute path
        - Else None
        """
        if not id_or_path:
            return None
        if id_or_path in self._registry:
            return self._registry[id_or_path]
        if os.path.exists(id_or_path):
            return os.path.abspath(id_or_path)
        return None

    def get_qfc_sheet(self, qfc_id: str) -> Optional[str]:
        """Return the sheet path for a QFC container id, if linked."""
        sid = self._qfc_map.get(qfc_id)
        return self.resolve(sid) if sid else None

    # ------------- optional utilities -------------
    def list_sheets(self) -> Dict[str, str]:
        return dict(self._registry)

    def list_links(self) -> Dict[str, str]:
        return dict(self._qfc_map)

    def unlink(self, qfc_id: str) -> bool:
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
        # resolve to id
        sid = None
        if sheet_id_or_path in self._registry:
            sid = sheet_id_or_path
        else:
            ap = os.path.abspath(sheet_id_or_path)
            # find by path
            for k, v in list(self._registry.items()):
                if v == ap:
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
        self._registry.clear()
        self._qfc_map.clear()
        self.save()

    # quick dunder for debug
    def __repr__(self) -> str:
        return f"AtomSheetRegistry(path={self._path!r}, sheets={len(self._registry)}, links={len(self._qfc_map)})"