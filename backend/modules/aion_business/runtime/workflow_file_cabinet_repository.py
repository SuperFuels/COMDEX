from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowFileCabinetRepository:
    """
    Workspace-scoped persisted workflow file cabinet.

    This stores the desktop workflow tree under the AION Business runtime root.
    It is intentionally separate from workflow execution definitions.
    """

    @staticmethod
    def _safe_id(value: str) -> str:
        value = str(value or "").strip()
        if not value:
            return "default"
        return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "default"

    @classmethod
    def cabinet_dir(cls, workspace_id: str) -> Path:
        workspace_id = cls._safe_id(workspace_id)
        AIONBusinessPaths.ensure_base_dirs()
        path = AIONBusinessPaths.ROOT / "workflow_file_cabinets" / workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @classmethod
    def cabinet_file(cls, workspace_id: str) -> Path:
        return cls.cabinet_dir(workspace_id) / "tree.json"

    @classmethod
    def default_tree(cls, workspace_id: str) -> Dict[str, Any]:
        workspace_id = cls._safe_id(workspace_id)
        now = _now_iso()
        return {
            "version": 1,
            "workspace_id": workspace_id,
            "root": {
                "id": "root",
                "type": "folder",
                "name": "Workflows",
                "children": [],
            },
            "metadata": {
                "created_at": now,
                "updated_at": now,
                "source": "aion_business_workflow_file_cabinet",
            },
        }

    @classmethod
    def load(cls, workspace_id: str) -> Dict[str, Any]:
        workspace_id = cls._safe_id(workspace_id)
        path = cls.cabinet_file(workspace_id)

        if not path.exists():
            payload = cls.default_tree(workspace_id)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            return payload

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            payload = cls.default_tree(workspace_id)

        payload.setdefault("version", 1)
        payload.setdefault("workspace_id", workspace_id)
        payload.setdefault("root", {"id": "root", "type": "folder", "name": "Workflows", "children": []})
        payload.setdefault("metadata", {})
        payload["metadata"].setdefault("created_at", _now_iso())
        payload["metadata"].setdefault("updated_at", _now_iso())
        payload["metadata"].setdefault("source", "aion_business_workflow_file_cabinet")
        return payload

    @classmethod
    def save(cls, workspace_id: str, tree: Dict[str, Any]) -> Dict[str, Any]:
        workspace_id = cls._safe_id(workspace_id)

        if not isinstance(tree, dict):
            raise ValueError("Workflow file cabinet payload must be an object")

        existing_created_at = None
        path = cls.cabinet_file(workspace_id)
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                existing_created_at = (existing.get("metadata") or {}).get("created_at")
            except Exception:
                existing_created_at = None

        payload = dict(tree)
        payload["version"] = int(payload.get("version") or 1)
        payload["workspace_id"] = workspace_id

        root = payload.get("root")

        # Desktop cabinet currently uses the live visible shape:
        # {
        #   schema_version: "aion.workflow_file_cabinet.v1",
        #   business_container: "...",
        #   folders: [...]
        # }
        #
        # Older backend shape uses:
        # {
        #   version: 1,
        #   workspace_id: "...",
        #   root: { id, type, name, children }
        # }
        #
        # Accept both. If root is absent but folders exists, wrap folders into root.children.
        if not isinstance(root, dict):
            folders = payload.get("folders")
            if isinstance(folders, list):
                root = {
                    "id": "root",
                    "type": "folder",
                    "name": "Workflows",
                    "children": folders,
                }
                payload["root"] = root
            else:
                raise ValueError("Workflow file cabinet payload requires root object or folders array")

        root.setdefault("id", "root")
        root.setdefault("type", "folder")
        root.setdefault("name", "Workflows")
        root.setdefault("children", [])

        # Preserve the desktop-native shape too, so both backend and desktop callers can use it.
        if "folders" not in payload and isinstance(root.get("children"), list):
            payload["folders"] = root["children"]
        payload.setdefault("schema_version", "aion.workflow_file_cabinet.v1")
        payload.setdefault("business_container", workspace_id)

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        now = _now_iso()
        metadata["created_at"] = metadata.get("created_at") or existing_created_at or now
        metadata["updated_at"] = now
        metadata["source"] = "aion_business_workflow_file_cabinet"
        payload["metadata"] = metadata

        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return payload
